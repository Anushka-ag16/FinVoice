"""
FinVoice — Regime Detector
GMM-based market regime classification: Bull / Bear / Sideways / High-Volatility.
"""

import numpy as np
import pandas as pd
import logging
from enum import Enum
from sklearn.mixture import GaussianMixture

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"


class RegimeDetector:
    """
    Gaussian Mixture Model for market regime classification.
    Uses VIX, market breadth, and momentum as inputs.
    """

    def __init__(self, n_regimes: int = 4):
        self.n_regimes = n_regimes
        self.model = GaussianMixture(
            n_components=n_regimes,
            covariance_type="full",
            random_state=42,
            n_init=5,
        )
        self.regime_labels = {}
        self.is_fitted = False

    def fit(self, features: pd.DataFrame):
        """
        Fit GMM on market features.
        Expected columns: market_return, volatility, vix (optional), breadth (optional)
        """
        X = features[["market_return", "volatility"]].dropna().values

        if len(X) < self.n_regimes * 10:
            logger.warning("Insufficient data for regime detection")
            return

        self.model.fit(X)
        self.is_fitted = True

        # Label regimes based on cluster characteristics
        self._assign_regime_labels(X)

    def predict(self, features: pd.DataFrame) -> list[MarketRegime]:
        """Predict market regime for each row."""
        if not self.is_fitted:
            return [MarketRegime.SIDEWAYS] * len(features)

        X = features[["market_return", "volatility"]].fillna(0).values
        cluster_ids = self.model.predict(X)

        return [self.regime_labels.get(c, MarketRegime.SIDEWAYS) for c in cluster_ids]

    def predict_current(self, market_return: float, volatility: float) -> MarketRegime:
        """Predict regime for a single observation."""
        if not self.is_fitted:
            return MarketRegime.SIDEWAYS

        X = np.array([[market_return, volatility]])
        cluster_id = self.model.predict(X)[0]
        return self.regime_labels.get(cluster_id, MarketRegime.SIDEWAYS)

    def get_regime_allocation_shift(self, regime: MarketRegime) -> dict:
        """
        Return recommended allocation shift based on detected regime.
        These adjustments are applied on top of the base optimization.
        """
        shifts = {
            MarketRegime.BULL: {
                "equity": +10, "bond": -5, "gold": -5, "cash": 0,
                "note": "Bull market — increase equity exposure for momentum.",
            },
            MarketRegime.BEAR: {
                "equity": -15, "bond": +5, "gold": +5, "cash": +5,
                "note": "Bear market — defensive positioning, increase safe assets.",
            },
            MarketRegime.SIDEWAYS: {
                "equity": 0, "bond": 0, "gold": 0, "cash": 0,
                "note": "Sideways market — maintain current allocation.",
            },
            MarketRegime.HIGH_VOLATILITY: {
                "equity": -10, "bond": 0, "gold": +5, "cash": +5,
                "note": "High volatility — reduce risk, increase hedges.",
            },
        }
        return shifts.get(regime, shifts[MarketRegime.SIDEWAYS])

    def _assign_regime_labels(self, X: np.ndarray):
        """Assign meaningful labels to GMM clusters based on cluster centers."""
        means = self.model.means_

        # Sort clusters by return (column 0)
        return_order = means[:, 0].argsort()
        vol_order = means[:, 1].argsort()

        labels = {}
        n = self.n_regimes

        if n >= 4:
            # Highest volatility = HIGH_VOLATILITY
            labels[vol_order[-1]] = MarketRegime.HIGH_VOLATILITY
            # Lowest return (excluding high vol) = BEAR
            for idx in return_order:
                if idx not in labels:
                    labels[idx] = MarketRegime.BEAR
                    break
            # Highest return (excluding assigned) = BULL
            for idx in reversed(return_order):
                if idx not in labels:
                    labels[idx] = MarketRegime.BULL
                    break
            # Remaining = SIDEWAYS
            for i in range(n):
                if i not in labels:
                    labels[i] = MarketRegime.SIDEWAYS
        else:
            for i in range(n):
                labels[i] = list(MarketRegime)[i]

        self.regime_labels = labels
        logger.info(f"Regime labels: {self.regime_labels}")
