"""
FinVoice — Ensemble Model
Stacking Regressor combining LSTM + XGBoost predictions.
"""

import numpy as np
import logging
from scipy import stats

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """
    Meta-learner that combines LSTM and XGBoost predictions.
    Weights each model's signal by its recent Sharpe contribution (rolling 30-day).
    """

    def __init__(self):
        self.lstm_weight = 0.5
        self.xgb_weight = 0.5
        self.rolling_sharpe_window = 30

    def combine_predictions(
        self,
        lstm_preds: np.ndarray,
        lstm_confidence: np.ndarray,
        xgb_preds: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Combine LSTM and XGBoost predictions.
        Weights adjusted by confidence from LSTM and feature importance from XGBoost.

        Returns: (expected_returns, confidence_scores)
        """
        # Normalize confidence to [0, 1] range
        if lstm_confidence is not None and len(lstm_confidence) > 0:
            conf = 1.0 / (1.0 + lstm_confidence)  # Higher variance = lower confidence
        else:
            conf = np.ones_like(lstm_preds) * 0.5

        # Weighted combination
        combined = (
            self.lstm_weight * lstm_preds * conf +
            self.xgb_weight * xgb_preds * (1 - conf * 0.3)
        ) / (self.lstm_weight + self.xgb_weight)

        # Overall confidence: average of model confidences
        confidence = conf * 0.6 + 0.4  # Floor at 0.4

        return combined, confidence

    def update_weights(
        self,
        lstm_actual_returns: np.ndarray,
        lstm_predicted: np.ndarray,
        xgb_actual_returns: np.ndarray,
        xgb_predicted: np.ndarray,
    ):
        """
        Update model weights based on rolling Sharpe contribution.
        Called after each prediction window.
        """
        # Compute IC for each model
        if len(lstm_predicted) > 5:
            lstm_ic, _ = stats.spearmanr(lstm_predicted, lstm_actual_returns)
        else:
            lstm_ic = 0.0

        if len(xgb_predicted) > 5:
            xgb_ic, _ = stats.spearmanr(xgb_predicted, xgb_actual_returns)
        else:
            xgb_ic = 0.0

        # Normalize to weights (softmax of ICs)
        total = abs(lstm_ic) + abs(xgb_ic) + 1e-6
        self.lstm_weight = max(0.1, abs(lstm_ic) / total)
        self.xgb_weight = max(0.1, abs(xgb_ic) / total)

        # Renormalize
        total_w = self.lstm_weight + self.xgb_weight
        self.lstm_weight /= total_w
        self.xgb_weight /= total_w

        logger.info(
            f"Ensemble weights updated: LSTM={self.lstm_weight:.3f}, XGB={self.xgb_weight:.3f}"
        )

    def compute_expected_returns_and_cov(
        self,
        combined_preds: np.ndarray,
        confidence: np.ndarray,
        symbols: list[str],
    ) -> tuple[dict, np.ndarray]:
        """
        Build Expected Return vector + Covariance Matrix for the optimizer.
        Low confidence = smaller position sizing.
        """
        expected_returns = {}
        for i, sym in enumerate(symbols):
            # Scale return by confidence
            er = float(combined_preds[i]) * float(confidence[i])
            expected_returns[sym] = round(er, 6)

        # Simplified covariance (diagonal + assumed correlation)
        n = len(symbols)
        vol = np.abs(combined_preds) * 2 + 0.01  # Proxy for volatility
        corr = np.full((n, n), 0.3)
        np.fill_diagonal(corr, 1.0)
        cov = np.outer(vol, vol) * corr

        return expected_returns, cov
