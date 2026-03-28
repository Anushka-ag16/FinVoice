"""
Ensemble Module — NNLS Meta-Learner for NSE/Nifty 50 Pipeline.

Collects out-of-fold predictions from XGBoost, CatBoost, and TFT/LSTM base
models, trains a non-negative least squares (NNLS) meta-learner on the stacked
predictions, and evaluates ensemble improvement over individual models.
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from scipy.stats import spearmanr
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)


def _safe_ic(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Information Coefficient (Spearman correlation) safely."""
    corr, _ = spearmanr(y_true, y_pred)
    return float(corr) if not np.isnan(corr) else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# OOF Collection
# ──────────────────────────────────────────────────────────────────────────────
def collect_oof_predictions(
    xgb_model: Any,
    cb_model: Any,
    tft_model: Any,
    X: np.ndarray,
    y: np.ndarray,
    tscv: TimeSeriesSplit,
) -> np.ndarray:
    """Collect out-of-fold predictions from three base models.

    Args:
        xgb_model: Trained XGBoost regressor.
        cb_model: Trained CatBoost regressor.
        tft_model: Trained TFT/LSTM model (may be ``None``).
        X: Feature matrix ``(n_samples, n_features)``.
        y: Target vector ``(n_samples,)``.
        tscv: Walk-forward ``TimeSeriesSplit`` splitter.

    Returns:
        Stacked OOF predictions of shape ``(n_samples, 3)``.
    """
    from ml.xgboost_model import get_oof_predictions

    oof_xgb = get_oof_predictions(xgb_model, X, y, tscv)
    oof_cb = get_oof_predictions(cb_model, X, y, tscv)

    if tft_model is not None:
        try:
            oof_tft = get_oof_predictions(tft_model, X, y, tscv)
        except Exception as exc:
            logger.warning("TFT OOF failed (%s), using zeros as fallback", exc)
            oof_tft = np.zeros(len(y))
    else:
        logger.info("TFT model is None — using zeros for stacking column")
        oof_tft = np.zeros(len(y))

    stacked = np.column_stack([oof_xgb, oof_cb, oof_tft])
    logger.info("OOF predictions collected: shape=%s", stacked.shape)
    return stacked


# ──────────────────────────────────────────────────────────────────────────────
# Meta-Learner
# ──────────────────────────────────────────────────────────────────────────────
class NNLSMetaLearner:
    """Non-negative least squares meta-learner with active column tracking.

    Attributes:
        weights_: Normalised NNLS weights for active columns.
        active_cols_: Boolean mask indicating which input columns are active.
        n_active_: Number of active (non-zero) base model columns.
    """

    def __init__(self) -> None:
        self.weights_: np.ndarray | None = None
        self.active_cols_: np.ndarray | None = None
        self.n_active_: int = 0

    def fit(self, L1: np.ndarray, y: np.ndarray) -> "NNLSMetaLearner":
        """Fit the NNLS meta-learner on stacked Level-1 predictions.

        Args:
            L1: Stacked OOF predictions ``(n_samples, n_base_models)``.
            y: Target vector ``(n_samples,)``.

        Returns:
            Self for method chaining.
        """
        valid_mask = ~np.isnan(L1).any(axis=1)
        L1_valid = L1[valid_mask]
        y_valid = y[valid_mask]

        assert len(L1_valid) > 0, (
            f"No valid OOF rows for meta-learner (all NaN). Total rows: {len(L1)}"
        )

        col_norms = np.abs(L1_valid).sum(axis=0)
        self.active_cols_ = col_norms > 1e-10
        self.n_active_ = int(self.active_cols_.sum())

        logger.info(
            "Meta-learner: %d/%d base model columns are active (non-zero)",
            self.n_active_, L1_valid.shape[1],
        )

        if self.n_active_ == 0:
            logger.warning("All base model columns are zero — using equal weights")
            self.weights_ = np.ones(L1_valid.shape[1]) / L1_valid.shape[1]
            self.active_cols_ = np.ones(L1_valid.shape[1], dtype=bool)
            return self

        if self.n_active_ == 1:
            logger.info("Only 1 active base model — using its predictions directly")
            self.weights_ = np.zeros(L1_valid.shape[1])
            self.weights_[self.active_cols_] = 1.0
            return self

        L1_active = L1_valid[:, self.active_cols_]
        raw_weights, _ = nnls(L1_active, y_valid)

        weight_sum = raw_weights.sum()
        if weight_sum > 1e-10:
            normalised = raw_weights / weight_sum
        else:
            normalised = np.ones(self.n_active_) / self.n_active_
            logger.warning("NNLS returned near-zero weights — using equal weights")

        self.weights_ = np.zeros(L1_valid.shape[1])
        self.weights_[self.active_cols_] = normalised

        logger.info(
            "Meta-learner trained on %d samples. Weights: %s (active_cols: %s)",
            len(L1_valid),
            self.weights_.tolist(),
            self.active_cols_.tolist(),
        )
        return self

    def predict(self, L1: np.ndarray) -> np.ndarray:
        """Generate ensemble predictions using NNLS weights."""
        assert self.weights_ is not None, "Must call fit() before predict()"
        return L1 @ self.weights_


def train_meta_learner(L1: np.ndarray, y: np.ndarray) -> NNLSMetaLearner:
    """Train an NNLS meta-learner on stacked Level-1 predictions.

    Args:
        L1: Stacked OOF predictions ``(n_samples, 3)``.
        y: Target vector ``(n_samples,)``.

    Returns:
        Fitted ``NNLSMetaLearner``.
    """
    meta = NNLSMetaLearner()
    meta.fit(L1, y)
    return meta


# ──────────────────────────────────────────────────────────────────────────────
# Prediction
# ──────────────────────────────────────────────────────────────────────────────
def predict_ensemble(
    xgb: Any,
    cb: Any,
    tft: Any,
    meta: NNLSMetaLearner,
    X_new: np.ndarray,
) -> np.ndarray:
    """Generate ensemble predictions on new data.

    Args:
        xgb: Trained XGBoost model.
        cb: Trained CatBoost model.
        tft: Trained TFT/LSTM model (may be ``None``).
        meta: Trained NNLS meta-learner.
        X_new: New feature matrix ``(n_samples, n_features)``.

    Returns:
        Ensemble prediction array ``(n_samples,)``.
    """
    pred_xgb = xgb.predict(X_new)
    pred_cb = cb.predict(X_new)

    if tft is not None:
        try:
            pred_tft = tft.predict(X_new)
        except Exception:
            pred_tft = np.zeros(len(X_new))
    else:
        pred_tft = np.zeros(len(X_new))

    L1 = np.column_stack([pred_xgb, pred_cb, pred_tft])
    return meta.predict(L1)


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────────────────────────────────────
def evaluate_ensemble(
    meta: NNLSMetaLearner,
    L1_test: np.ndarray,
    y_test: np.ndarray,
) -> dict[str, float]:
    """Evaluate ensemble on test data and compare to individual base models.

    Args:
        meta: Trained NNLS meta-learner.
        L1_test: Stacked base-model predictions on test set ``(n, 3)``.
        y_test: Actual target values ``(n,)``.

    Returns:
        Dictionary with ``ic``, ``icir``, ``improvement_over_best_base``,
        and per-base ICs.
    """
    ensemble_preds = meta.predict(L1_test)
    ensemble_ic = _safe_ic(y_test, ensemble_preds)

    base_names = ["xgb", "catboost", "tft"]
    base_ics: dict[str, float] = {}
    for i, name in enumerate(base_names):
        base_ics[name] = _safe_ic(y_test, L1_test[:, i])

    best_base_ic = max(base_ics.values())
    improvement = ensemble_ic - best_base_ic

    result = {
        "ic": ensemble_ic,
        "icir": ensemble_ic,
        "improvement_over_best_base": improvement,
    }
    result.update({f"ic_{k}": v for k, v in base_ics.items()})

    mlflow.set_experiment("nse-quant-pipeline")
    _nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name="stacking_ensemble", nested=_nested):
        mlflow.log_metric("ensemble_ic", ensemble_ic)
        mlflow.log_metric("improvement_over_best_base", improvement)
        for name, ic_val in base_ics.items():
            mlflow.log_metric(f"base_ic_{name}", ic_val)

        weights = meta.weights_.tolist()
        mlflow.log_param("meta_weights", str(weights))
        mlflow.log_param("meta_type", "NNLS")
        mlflow.log_param("active_cols", str(meta.active_cols_.tolist()))

    if improvement < 0:
        logger.warning(
            "Ensemble IC (%.4f) is LOWER than best base model IC (%.4f, improvement=%.4f). "
            "Consider retraining the meta-learner or checking base model diversity.",
            ensemble_ic, best_base_ic, improvement,
        )
    else:
        logger.info(
            "Ensemble IC=%.4f, improvement over best base=%.4f",
            ensemble_ic, improvement,
        )

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Persistence
# ──────────────────────────────────────────────────────────────────────────────
def save_ensemble(
    xgb: Any,
    cb: Any,
    tft: Any,
    meta: NNLSMetaLearner,
    path: str | Path = "models/ensemble",
) -> None:
    """Persist all ensemble components to disk with atomic writes."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    components = {
        "xgb_model.pkl": xgb,
        "cb_model.pkl": cb,
        "tft_model.pkl": tft,
        "meta_learner.pkl": meta,
    }

    for filename, obj in components.items():
        target = path / filename
        tmp = target.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump(obj, f)
        tmp.replace(target)

    active_cols_path = path / "meta_active_cols.json"
    active_cols_tmp = active_cols_path.with_suffix(".tmp")
    meta_info = {
        "active_cols": meta.active_cols_.tolist() if meta.active_cols_ is not None else None,
        "weights": meta.weights_.tolist() if meta.weights_ is not None else None,
        "n_active": meta.n_active_,
    }
    with open(active_cols_tmp, "w") as f:
        json.dump(meta_info, f, indent=2)
    active_cols_tmp.replace(active_cols_path)

    logger.info("Ensemble components saved to %s", path)


def load_ensemble(path: str | Path = "models/ensemble") -> tuple[Any, Any, Any, NNLSMetaLearner]:
    """Load all ensemble components from disk.

    Raises:
        FileNotFoundError: If any required artifact is missing.
    """
    path = Path(path)

    components: dict[str, Any] = {}
    for filename in ["xgb_model.pkl", "cb_model.pkl", "tft_model.pkl", "meta_learner.pkl"]:
        target = path / filename
        if not target.exists():
            raise FileNotFoundError(f"Ensemble artifact not found: {target}")
        with open(target, "rb") as f:
            components[filename] = pickle.load(f)

    logger.info("Ensemble components loaded from %s", path)

    meta = components["meta_learner.pkl"]
    active_cols_path = path / "meta_active_cols.json"
    if active_cols_path.exists():
        with open(active_cols_path, "r") as f:
            meta_info = json.load(f)
        logger.info(
            "Loaded meta_active_cols: active=%s, weights=%s",
            meta_info.get("active_cols"),
            meta_info.get("weights"),
        )

    return (
        components["xgb_model.pkl"],
        components["cb_model.pkl"],
        components["tft_model.pkl"],
        meta,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    logger.info("=== Ensemble Smoke Test ===")

    np.random.seed(42)
    n = 1000
    y = np.random.randn(n).astype(np.float32) * 0.01

    L1 = np.column_stack([
        y + np.random.randn(n) * 0.005,
        y + np.random.randn(n) * 0.006,
        np.zeros(n),
    ])

    meta = train_meta_learner(L1, y)
    logger.info("Meta weights: %s", meta.weights_)
    logger.info("Active cols: %s", meta.active_cols_)

    assert (meta.weights_ >= 0).all(), f"Negative weights detected: {meta.weights_}"
    assert abs(meta.weights_.sum() - 1.0) < 1e-6, f"Weights don't sum to 1: {meta.weights_.sum()}"

    split = int(n * 0.8)
    result = evaluate_ensemble(meta, L1[split:], y[split:])
    logger.info("Ensemble eval: %s", result)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        save_ensemble(None, None, None, meta, path=tmpdir)
        _, _, _, meta_loaded = load_ensemble(path=tmpdir)
        assert np.allclose(meta.weights_, meta_loaded.weights_), "Meta-learner weights mismatch after load"
        assert np.array_equal(meta.active_cols_, meta_loaded.active_cols_), "Active cols mismatch after load"

    logger.info("=== Smoke Test PASSED ===")
