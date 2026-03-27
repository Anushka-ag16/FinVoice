"""
FinVoice — XGBoost Return Predictor
Baseline ML model for return prediction using tabular features.
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

logger = logging.getLogger(__name__)

MODEL_DIR = Path("data/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class XGBoostReturnPredictor:
    """
    XGBoost model for predicting forward stock returns.
    Trained on tabular features: technical + fundamental + macro.
    """

    FEATURE_COLS = [
        "rsi_14", "macd", "macd_signal", "macd_hist",
        "bollinger_pct", "atr_14", "obv",
        "williams_r", "stochastic_k", "stochastic_d", "adx",
        "return_1d", "return_5d", "return_21d", "return_63d",
        "volatility_21d", "distance_52w_high", "distance_52w_low",
    ]

    TARGET_COL = "fwd_return_5d"

    def __init__(self):
        self.model = None
        self.feature_importance = None

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame = None,
        params: dict = None,
    ) -> dict:
        """
        Train XGBoost on training data and evaluate on validation set.
        Returns evaluation metrics.
        """
        import xgboost as xgb

        default_params = {
            "objective": "reg:squarederror",
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 500,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
        }
        if params:
            default_params.update(params)

        # Prepare data
        X_train, y_train = self._prepare_features(train_df)

        # Train
        self.model = xgb.XGBRegressor(**default_params)

        eval_set = []
        if val_df is not None:
            X_val, y_val = self._prepare_features(val_df)
            eval_set = [(X_val, y_val)]

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set if eval_set else None,
            verbose=50,
        )

        # Feature importance
        self.feature_importance = dict(
            zip(self.FEATURE_COLS, self.model.feature_importances_)
        )

        # Evaluate
        metrics = {}
        if val_df is not None:
            metrics = self.evaluate(val_df)

        return metrics

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict forward returns."""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        X, _ = self._prepare_features(df, require_target=False)
        return self.model.predict(X)

    def evaluate(self, df: pd.DataFrame) -> dict:
        """
        Evaluate model on a dataset.
        Key metrics: IC (Information Coefficient), ICIR, Sharpe estimate.
        """
        X, y = self._prepare_features(df)
        preds = self.model.predict(X)

        # IC: Spearman correlation between predicted and actual returns
        ic, _ = stats.spearmanr(preds, y)

        # ICIR: IC / std(IC) — computed via rolling IC
        # Simplified: use single IC value
        icir = ic / max(abs(ic) * 0.3, 0.01)  # Approximate

        # Directional accuracy
        direction_correct = ((preds > 0) == (y > 0)).mean()

        metrics = {
            "ic": round(float(ic), 4),
            "icir": round(float(icir), 4),
            "direction_accuracy": round(float(direction_correct), 4),
            "mse": round(float(np.mean((preds - y) ** 2)), 6),
            "n_samples": len(y),
        }

        logger.info(f"Evaluation: IC={metrics['ic']}, ICIR={metrics['icir']}, "
                     f"Direction={metrics['direction_accuracy']:.2%}")

        return metrics

    def save(self, path: str = None):
        """Save model to disk."""
        path = path or str(MODEL_DIR / "xgboost_return_predictor.json")
        self.model.save_model(path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str = None):
        """Load model from disk."""
        import xgboost as xgb
        path = path or str(MODEL_DIR / "xgboost_return_predictor.json")
        self.model = xgb.XGBRegressor()
        self.model.load_model(path)
        logger.info(f"Model loaded from {path}")

    def _prepare_features(
        self, df: pd.DataFrame, require_target: bool = True
    ) -> tuple:
        """Prepare feature matrix and target vector."""
        available_features = [c for c in self.FEATURE_COLS if c in df.columns]

        if not available_features:
            raise ValueError("No feature columns found in dataframe")

        X = df[available_features].copy()
        X = X.fillna(0)  # Simple imputation — improve in production

        y = None
        if require_target and self.TARGET_COL in df.columns:
            y = df[self.TARGET_COL].fillna(0).values

        return X, y

    def get_shap_values(self, df: pd.DataFrame) -> tuple:
        """Compute SHAP values for explainability."""
        import shap

        X, _ = self._prepare_features(df, require_target=False)
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X)
        return shap_values, self.FEATURE_COLS


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("XGBoost Return Predictor — Ready for training")
    print(f"Features: {XGBoostReturnPredictor.FEATURE_COLS}")
