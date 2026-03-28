"""
FinVoice — Enhanced Ensemble Model
Stacking Regressor combining LSTM + XGBoost + AutoGluon predictions.
Optionally incorporates FinBERT sentiment features.
"""

import numpy as np
import logging
from scipy import stats

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """
    Meta-learner that combines predictions from multiple models:
    - LSTM (sequential patterns)
    - XGBoost (tabular features)
    - AutoGluon (auto-tuned multi-model stack)

    Weights each model by its recent Information Coefficient (rolling 30-day).
    Optionally adjusts predictions using FinBERT sentiment signals.
    """

    def __init__(self):
        self.lstm_weight = 0.30
        self.xgb_weight = 0.30
        self.automl_weight = 0.40   # AutoGluon gets higher default weight
        self.sentiment_boost = 0.10  # Max adjustment from sentiment
        self.rolling_sharpe_window = 30

    def combine_predictions(
        self,
        lstm_preds: np.ndarray,
        lstm_confidence: np.ndarray,
        xgb_preds: np.ndarray,
        automl_preds: np.ndarray = None,
        automl_confidence: np.ndarray = None,
        sentiment_scores: np.ndarray = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Combine predictions from all models.

        Args:
            lstm_preds: LSTM return predictions
            lstm_confidence: LSTM prediction confidence (from variance output)
            xgb_preds: XGBoost return predictions
            automl_preds: Optional AutoGluon predictions
            automl_confidence: Optional AutoGluon confidence (model disagreement)
            sentiment_scores: Optional sentiment scores [-1, 1] per symbol

        Returns: (expected_returns, confidence_scores)
        """
        # Normalize LSTM confidence
        if lstm_confidence is not None and len(lstm_confidence) > 0:
            lstm_conf = 1.0 / (1.0 + lstm_confidence)
        else:
            lstm_conf = np.ones_like(lstm_preds) * 0.5

        # Build weighted combination
        if automl_preds is not None and len(automl_preds) == len(lstm_preds):
            # 3-model ensemble
            automl_conf = automl_confidence if automl_confidence is not None else np.ones_like(automl_preds) * 0.6

            combined = (
                self.lstm_weight * lstm_preds * lstm_conf +
                self.xgb_weight * xgb_preds +
                self.automl_weight * automl_preds * automl_conf
            ) / (self.lstm_weight + self.xgb_weight + self.automl_weight)

            # Combined confidence
            confidence = (
                self.lstm_weight * lstm_conf +
                self.xgb_weight * 0.5 +
                self.automl_weight * automl_conf
            ) / (self.lstm_weight + self.xgb_weight + self.automl_weight)
        else:
            # 2-model ensemble (fallback)
            combined = (
                self.lstm_weight * lstm_preds * lstm_conf +
                self.xgb_weight * xgb_preds
            ) / (self.lstm_weight + self.xgb_weight)

            confidence = lstm_conf * 0.6 + 0.4

        # Apply sentiment adjustment
        if sentiment_scores is not None and len(sentiment_scores) == len(combined):
            # Sentiment boosts/dampens the prediction
            sentiment_adj = sentiment_scores * self.sentiment_boost
            combined = combined + sentiment_adj

            # Increase confidence when sentiment aligns with prediction direction
            alignment = np.sign(combined) * np.sign(sentiment_scores)
            confidence = confidence * (1 + alignment * 0.1)

        # Clip confidence to [0.1, 1.0]
        confidence = np.clip(confidence, 0.1, 1.0)

        return combined, confidence

    def update_weights(
        self,
        lstm_actual: np.ndarray,
        lstm_predicted: np.ndarray,
        xgb_actual: np.ndarray,
        xgb_predicted: np.ndarray,
        automl_actual: np.ndarray = None,
        automl_predicted: np.ndarray = None,
    ):
        """
        Update model weights based on rolling IC.
        Called after each prediction window (e.g., weekly).
        """
        # Compute IC for each model
        lstm_ic = 0.0
        if len(lstm_predicted) > 5:
            lstm_ic, _ = stats.spearmanr(lstm_predicted, lstm_actual)

        xgb_ic = 0.0
        if len(xgb_predicted) > 5:
            xgb_ic, _ = stats.spearmanr(xgb_predicted, xgb_actual)

        automl_ic = 0.0
        if automl_predicted is not None and len(automl_predicted) > 5:
            automl_ic, _ = stats.spearmanr(automl_predicted, automl_actual)

        # Softmax of absolute ICs → weights
        ics = [abs(lstm_ic), abs(xgb_ic), abs(automl_ic)]
        total = sum(ics) + 1e-6

        self.lstm_weight = max(0.1, ics[0] / total)
        self.xgb_weight = max(0.1, ics[1] / total)
        self.automl_weight = max(0.1, ics[2] / total)

        # Renormalize
        total_w = self.lstm_weight + self.xgb_weight + self.automl_weight
        self.lstm_weight /= total_w
        self.xgb_weight /= total_w
        self.automl_weight /= total_w

        logger.info(
            f"Ensemble weights updated: LSTM={self.lstm_weight:.3f}, "
            f"XGB={self.xgb_weight:.3f}, AutoML={self.automl_weight:.3f} | "
            f"ICs: LSTM={lstm_ic:.3f}, XGB={xgb_ic:.3f}, AutoML={automl_ic:.3f}"
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
            er = float(combined_preds[i]) * float(confidence[i])
            expected_returns[sym] = round(er, 6)

        # Covariance matrix (simplified diagonal + correlation)
        n = len(symbols)
        vol = np.abs(combined_preds) * 2 + 0.01
        corr = np.full((n, n), 0.3)
        np.fill_diagonal(corr, 1.0)
        cov = np.outer(vol, vol) * corr

        return expected_returns, cov
