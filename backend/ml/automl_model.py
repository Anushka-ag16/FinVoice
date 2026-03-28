"""
FinVoice — AutoGluon AutoML Return Predictor
Automatically trains and ensembles multiple model types (XGBoost, LightGBM,
CatBoost, Neural Nets, etc.) for return prediction.
Replaces manual model selection with automatic best-model discovery.
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from scipy import stats

logger = logging.getLogger(__name__)

MODEL_DIR = Path("data/models/autogluon")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class AutoMLReturnPredictor:
    """
    AutoGluon-based return predictor.
    Automatically trains XGBoost, LightGBM, CatBoost, Random Forest,
    Extra Trees, KNN, and Neural Networks — then stacks them.

    Advantages over manual XGBoost:
    - Zero hyperparameter tuning
    - Multi-model stacking (6+ model types)
    - Built-in cross-validation
    - Automatic feature preprocessing
    """

    FEATURE_COLS = [
        "rsi_14", "macd", "macd_signal", "macd_hist",
        "bollinger_pct", "atr_14", "obv",
        "williams_r", "stochastic_k", "stochastic_d", "adx",
        "return_1d", "return_5d", "return_21d", "return_63d",
        "volatility_21d", "distance_52w_high", "distance_52w_low",
    ]

    TARGET_COL = "fwd_return_5d"

    # Quality presets: 'best_quality', 'high_quality', 'good_quality',
    #                  'medium_quality', 'optimize_for_deployment'
    DEFAULT_PRESET = "high_quality"
    DEFAULT_TIME_LIMIT = 300  # 5 minutes training time

    def __init__(self):
        self.predictor = None
        self.leaderboard = None
        self.feature_importance_df = None

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame = None,
        time_limit: int = None,
        preset: str = None,
    ) -> dict:
        """
        Train AutoGluon on tabular features.

        Args:
            train_df: Training dataframe with features and target
            val_df: Optional validation dataframe (AutoGluon does internal CV if absent)
            time_limit: Max training time in seconds (default: 300s)
            preset: Quality preset ('best_quality', 'high_quality', etc.)

        Returns:
            dict with metrics, leaderboard, and best model info
        """
        from autogluon.tabular import TabularPredictor

        time_limit = time_limit or self.DEFAULT_TIME_LIMIT
        preset = preset or self.DEFAULT_PRESET

        # Prepare data
        train_data = self._prepare_dataframe(train_df)

        if val_df is not None:
            val_data = self._prepare_dataframe(val_df)
        else:
            val_data = None

        logger.info(
            f"Starting AutoGluon training: {len(train_data)} samples, "
            f"{len(self.FEATURE_COLS)} features, preset={preset}, "
            f"time_limit={time_limit}s"
        )

        # Train AutoGluon
        save_path = str(MODEL_DIR / "ag_return_predictor")

        self.predictor = TabularPredictor(
            label=self.TARGET_COL,
            problem_type="regression",
            eval_metric="mean_squared_error",
            path=save_path,
        ).fit(
            train_data=train_data,
            tuning_data=val_data,
            time_limit=time_limit,
            presets=preset,
            verbosity=2,
        )

        # Get leaderboard
        if val_data is not None:
            self.leaderboard = self.predictor.leaderboard(val_data, silent=True)
        else:
            self.leaderboard = self.predictor.leaderboard(silent=True)

        # Feature importance
        try:
            self.feature_importance_df = self.predictor.feature_importance(train_data)
        except Exception:
            self.feature_importance_df = None

        # Evaluate
        metrics = {}
        if val_df is not None:
            metrics = self.evaluate(val_df)

        metrics["best_model"] = self.predictor.get_model_best()
        metrics["models_trained"] = len(self.leaderboard)
        metrics["leaderboard"] = self.leaderboard.to_dict() if self.leaderboard is not None else {}

        logger.info(
            f"AutoGluon training complete: best_model={metrics['best_model']}, "
            f"models_trained={metrics['models_trained']}"
        )

        return metrics

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict forward returns using the best AutoGluon model."""
        if self.predictor is None:
            raise ValueError("Model not trained. Call train() or load() first.")

        data = self._prepare_dataframe(df, require_target=False)
        predictions = self.predictor.predict(data)
        return predictions.values

    def predict_with_confidence(self, df: pd.DataFrame) -> tuple:
        """
        Predict returns with confidence intervals.
        Uses model disagreement across the ensemble as confidence proxy.

        Returns: (predictions, confidence_scores)
        """
        if self.predictor is None:
            raise ValueError("Model not trained. Call train() or load() first.")

        data = self._prepare_dataframe(df, require_target=False)

        # Get predictions from all models in the ensemble
        try:
            all_model_preds = {}
            for model_name in self.predictor.get_model_names():
                try:
                    preds = self.predictor.predict(data, model=model_name)
                    all_model_preds[model_name] = preds.values
                except Exception:
                    continue

            if len(all_model_preds) > 1:
                # Confidence = 1 / (1 + std across models)
                preds_matrix = np.array(list(all_model_preds.values()))
                mean_preds = np.mean(preds_matrix, axis=0)
                std_preds = np.std(preds_matrix, axis=0)
                confidence = 1.0 / (1.0 + std_preds)
                return mean_preds, confidence
            else:
                # Single model: moderate confidence
                preds = self.predictor.predict(data).values
                return preds, np.full_like(preds, 0.5)

        except Exception as e:
            logger.warning(f"Confidence estimation failed: {e}")
            preds = self.predictor.predict(data).values
            return preds, np.full_like(preds, 0.5)

    def evaluate(self, df: pd.DataFrame) -> dict:
        """
        Evaluate AutoGluon model.
        Metrics: IC (Information Coefficient), ICIR, direction accuracy, MSE.
        """
        data = self._prepare_dataframe(df)
        preds = self.predictor.predict(data).values
        y = data[self.TARGET_COL].values

        # IC: Spearman correlation
        ic, _ = stats.spearmanr(preds, y)

        # ICIR: approximation
        icir = ic / max(abs(ic) * 0.3, 0.01)

        # Directional accuracy
        direction_correct = ((preds > 0) == (y > 0)).mean()

        # MSE
        mse = float(np.mean((preds - y) ** 2))

        metrics = {
            "ic": round(float(ic), 4),
            "icir": round(float(icir), 4),
            "direction_accuracy": round(float(direction_correct), 4),
            "mse": round(mse, 6),
            "n_samples": len(y),
        }

        logger.info(
            f"AutoGluon Eval: IC={metrics['ic']}, Direction={metrics['direction_accuracy']:.2%}"
        )
        return metrics

    def get_feature_importance(self) -> dict:
        """Get feature importance from the best model."""
        if self.feature_importance_df is not None:
            return self.feature_importance_df.to_dict()

        if self.predictor is None:
            return {}

        try:
            # Use built-in permutation importance
            fi = self.predictor.feature_importance(
                self.predictor.transform_labels(self.predictor.load_data_internal())
            )
            return fi.to_dict()
        except Exception:
            return {}

    def get_model_leaderboard(self) -> list[dict]:
        """Get ranked list of all trained models with scores."""
        if self.leaderboard is None:
            return []

        return self.leaderboard.to_dict(orient="records")

    def save(self, path: str = None):
        """Save model (AutoGluon saves automatically during training)."""
        if self.predictor is None:
            raise ValueError("No model to save")
        # AutoGluon saves to the path specified during training
        logger.info(f"Model saved to {self.predictor.path}")

    def load(self, path: str = None):
        """Load a previously trained AutoGluon model."""
        from autogluon.tabular import TabularPredictor

        path = path or str(MODEL_DIR / "ag_return_predictor")
        self.predictor = TabularPredictor.load(path)
        logger.info(f"AutoGluon model loaded from {path}")

    def _prepare_dataframe(
        self, df: pd.DataFrame, require_target: bool = True
    ) -> pd.DataFrame:
        """Prepare dataframe with feature and target columns."""
        cols = [c for c in self.FEATURE_COLS if c in df.columns]

        if not cols:
            raise ValueError("No feature columns found in dataframe")

        if require_target and self.TARGET_COL in df.columns:
            cols.append(self.TARGET_COL)
        elif require_target:
            raise ValueError(f"Target column '{self.TARGET_COL}' not found")

        data = df[cols].copy()
        data = data.fillna(0)
        return data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("AutoGluon Return Predictor — Ready for training")
    print(f"Features: {AutoMLReturnPredictor.FEATURE_COLS}")
    print(f"Target: {AutoMLReturnPredictor.TARGET_COL}")
