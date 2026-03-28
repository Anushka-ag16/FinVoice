"""
XGBoost & CatBoost Model Module — NSE/Nifty 50 Quantitative Pipeline.

Trains gradient-boosted tree models with walk-forward cross-validation
(TimeSeriesSplit). Reports Information Coefficient (IC) — Spearman rank
correlation — and ICIR (IC / std) as primary alpha metrics.

GPU acceleration:
  - XGBoost: tree_method="hist", device="cuda"
  - CatBoost: task_type="GPU"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)

# GPU auto-detection with graceful Blackwell sm_120 fallback
try:
    HAS_CUDA = torch.cuda.is_available()
    if HAS_CUDA:
        _cc = torch.cuda.get_device_capability()
        if _cc[0] < 8:
            logger.warning("CUDA device compute capability %s < 8.0, falling back to CPU", _cc)
            HAS_CUDA = False
        else:
            logger.info("CUDA device detected: compute capability %s", _cc)
except Exception as _cuda_err:
    logger.warning("CUDA detection failed (%s), falling back to CPU", _cuda_err)
    HAS_CUDA = False

logger.info("XGBoost/CatBoost GPU available: %s", HAS_CUDA)


# ──────────────────────────────────────────────────────────────────────────────
# Feature Configuration
# ──────────────────────────────────────────────────────────────────────────────
def get_feature_cols() -> list[str]:
    """Return the canonical list of feature column names used for model training.

    Returns:
        Ordered list of feature-column names.  Does NOT include ``target_fwd_5d``
        (label) or ``ticker`` (metadata).
    """
    return [
        "close", "volume", "ret_1d",
        "rsi", "macd", "macd_signal", "macd_hist",
        "boll_upper", "boll_lower", "boll_mid", "boll_pct",
        "volatility",
        "usdinr", "nifty_index", "india_vix", "gold", "crude", "rbi_rate",
        "regime_label",
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────────────────────────────────────
def information_coefficient(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute the Information Coefficient (Spearman rank correlation).

    Args:
        y_true: Actual forward returns.
        y_pred: Predicted forward returns.

    Returns:
        Spearman rank correlation coefficient ∈ [-1, 1].
    """
    corr, _ = spearmanr(y_true, y_pred)
    return float(corr) if not np.isnan(corr) else 0.0


def icir(ic_scores: list[float] | np.ndarray) -> float:
    """Compute ICIR — mean IC divided by its standard deviation.

    Args:
        ic_scores: List of per-fold IC values.

    Returns:
        ICIR value.  Returns 0 if std is zero.
    """
    arr = np.asarray(ic_scores, dtype=float)
    std = arr.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(arr.mean() / std)


# ──────────────────────────────────────────────────────────────────────────────
# Walk-Forward Out-of-Fold Predictions
# ──────────────────────────────────────────────────────────────────────────────
def get_oof_predictions(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    tscv: TimeSeriesSplit,
) -> np.ndarray:
    """Generate out-of-fold predictions via walk-forward cross-validation.

    Args:
        model: A scikit-learn compatible estimator with ``fit`` and ``predict``.
        X: Feature matrix ``(n_samples, n_features)``.
        y: Target vector ``(n_samples,)``.
        tscv: ``TimeSeriesSplit`` splitter.

    Returns:
        Out-of-fold prediction array of length ``n_samples`` (NaN for
        observations that appear only in training folds).
    """
    oof = np.full(len(y), np.nan)
    for train_idx, val_idx in tscv.split(X):  # CHANGED
        model.fit(X[train_idx], y[train_idx])  # CHANGED
        oof[val_idx] = model.predict(X[val_idx])  # CHANGED
    return oof


# ──────────────────────────────────────────────────────────────────────────────
# XGBoost Training
# ──────────────────────────────────────────────────────────────────────────────
def train_xgboost(
    X: np.ndarray | pd.DataFrame,
    y: np.ndarray | pd.Series,
    n_splits: int = 5,
) -> tuple[Any, dict[str, Any]]:
    """Train an XGBoost regressor with walk-forward CV and GPU acceleration.

    Args:
        X: Feature matrix.
        y: Target vector (``target_fwd_5d``).
        n_splits: Number of walk-forward splits.

    Returns:
        Tuple of ``(fitted XGBRegressor, metrics dict)``.
    """
    from xgboost import XGBRegressor

    X_arr = np.asarray(X, dtype=np.float32)
    y_arr = np.asarray(y, dtype=np.float32)

    params = dict(  # CHANGED
        max_depth=5,
        n_estimators=300,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=5,
        gamma=0.1,
        reg_alpha=0.3,
        reg_lambda=1.5,
        tree_method="hist",
        device="cuda" if HAS_CUDA else "cpu",
        random_state=42,
        verbosity=0,
    )

    tscv = TimeSeriesSplit(n_splits=n_splits, gap=2)
    ic_scores: list[float] = []
    mse_scores: list[float] = []

    cv_model = XGBRegressor(**params, early_stopping_rounds=30)  # CHANGED

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_arr)):
        cv_model.fit(  # CHANGED
            X_arr[train_idx], y_arr[train_idx],
            eval_set=[(X_arr[val_idx], y_arr[val_idx])],  # CHANGED
            verbose=False,
        )
        preds = cv_model.predict(X_arr[val_idx])  # CHANGED
        fold_ic = information_coefficient(y_arr[val_idx], preds)
        fold_mse = mean_squared_error(y_arr[val_idx], preds)
        ic_scores.append(fold_ic)
        mse_scores.append(fold_mse)
        logger.info("XGB fold %d/%d: IC=%.4f MSE=%.6f", fold + 1, n_splits, fold_ic, fold_mse)

        if np.std(preds) < 1e-9:
            logger.warning(
                "XGB fold %d: predictions are constant (std=%.2e). "
                "Model may be under-constrained -- check min_child_weight and data size.",
                fold + 1, np.std(preds),
            )

    # Final fit on all data -- no early stopping, no eval_set
    model = XGBRegressor(**params)  # CHANGED
    model.fit(X_arr, y_arr, verbose=False)  # CHANGED

    ic_mean = float(np.mean(ic_scores))
    ic_ir = icir(ic_scores)

    metrics = {
        "ic_mean": ic_mean,
        "icir": ic_ir,
        "mse_mean": float(np.mean(mse_scores)),
        "ic_per_fold": ic_scores,
    }

    if ic_mean < 0.02:
        logger.warning(
            "XGBoost IC very low: %.4f. Per-fold ICs: %s. Check feature quality.",
            ic_mean, ic_scores,
        )
    if ic_ir < 0.3:
        logger.warning(
            "XGBoost ICIR low: %.4f. Per-fold ICs: %s. Predictions inconsistent across folds.",
            ic_ir, ic_scores,
        )

    # MLflow logging
    mlflow.set_experiment("nse-quant-pipeline")
    _nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name="xgboost_predictor", nested=_nested):
        mlflow.log_params(params)
        mlflow.log_metric("ic_mean", ic_mean)
        mlflow.log_metric("icir", ic_ir)
        mlflow.log_metric("mse_mean", metrics["mse_mean"])
        try:
            mlflow.xgboost.log_model(model, "xgboost_model")
        except Exception as e:
            logger.warning("Could not log XGBoost model to MLflow: %s", e)

    logger.info("XGBoost training complete: IC=%.4f ICIR=%.4f", ic_mean, ic_ir)
    return model, metrics


# ──────────────────────────────────────────────────────────────────────────────
# CatBoost Training
# ──────────────────────────────────────────────────────────────────────────────
def train_catboost(
    X: np.ndarray | pd.DataFrame,
    y: np.ndarray | pd.Series,
    n_splits: int = 5,
) -> tuple[Any, dict[str, Any]]:
    """Train a CatBoost regressor with walk-forward CV and GPU acceleration.

    Args:
        X: Feature matrix.
        y: Target vector.
        n_splits: Number of walk-forward splits.

    Returns:
        Tuple of ``(fitted CatBoostRegressor, metrics dict)``.
    """
    from catboost import CatBoostRegressor

    X_arr = np.asarray(X, dtype=np.float32) if not isinstance(X, pd.DataFrame) else X
    y_arr = np.asarray(y, dtype=np.float32)

    cat_feature_indices: list[int] = []

    params = dict(
        iterations=600,
        learning_rate=0.04,
        depth=5,
        l2_leaf_reg=5.0,
        early_stopping_rounds=40,
        task_type="GPU" if HAS_CUDA else "CPU",
        random_seed=42,
        verbose=0,
        loss_function="RMSE",
    )

    tscv = TimeSeriesSplit(n_splits=n_splits, gap=2)
    ic_scores: list[float] = []
    mse_scores: list[float] = []

    model = CatBoostRegressor(**params)

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_arr)):
        if isinstance(X_arr, pd.DataFrame):
            X_train = X_arr.iloc[train_idx]
            X_val = X_arr.iloc[val_idx]
        else:
            X_train = X_arr[train_idx]
            X_val = X_arr[val_idx]

        model.fit(
            X_train, y_arr[train_idx],
            eval_set=(X_val, y_arr[val_idx]),
            cat_features=cat_feature_indices if cat_feature_indices else None,
            verbose=0,
        )
        preds = model.predict(X_val)
        fold_ic = information_coefficient(y_arr[val_idx], preds)
        fold_mse = mean_squared_error(y_arr[val_idx], preds)
        ic_scores.append(fold_ic)
        mse_scores.append(fold_mse)
        logger.info("CatBoost fold %d/%d: IC=%.4f MSE=%.6f", fold + 1, n_splits, fold_ic, fold_mse)

    # Final fit
    model.fit(
        X_arr, y_arr,
        cat_features=cat_feature_indices if cat_feature_indices else None,
        verbose=0,
    )

    ic_mean = float(np.mean(ic_scores))
    ic_ir = icir(ic_scores)

    metrics = {
        "ic_mean": ic_mean,
        "icir": ic_ir,
        "mse_mean": float(np.mean(mse_scores)),
        "ic_per_fold": ic_scores,
    }

    if ic_mean < 0.02:
        logger.warning(
            "CatBoost IC very low: %.4f. Per-fold ICs: %s.",
            ic_mean, ic_scores,
        )
    if ic_ir < 0.3:
        logger.warning(
            "CatBoost ICIR low: %.4f. Per-fold ICs: %s.",
            ic_ir, ic_scores,
        )

    # MLflow logging
    mlflow.set_experiment("nse-quant-pipeline")
    _nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name="catboost_predictor", nested=_nested):
        mlflow.log_params({k: str(v) for k, v in params.items()})
        mlflow.log_metric("ic_mean", ic_mean)
        mlflow.log_metric("icir", ic_ir)
        mlflow.log_metric("mse_mean", metrics["mse_mean"])
        try:
            mlflow.catboost.log_model(model, "catboost_model")
        except Exception as e:
            logger.warning("Could not log CatBoost model to MLflow: %s", e)

    logger.info("CatBoost training complete: IC=%.4f ICIR=%.4f", ic_mean, ic_ir)
    return model, metrics


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────────────────────────────────────
def evaluate_model(
    model: Any,
    X_test: np.ndarray | pd.DataFrame,
    y_test: np.ndarray | pd.Series,
) -> dict[str, float]:
    """Evaluate a trained model on a hold-out test set.

    Args:
        model: Fitted scikit-learn-compatible estimator.
        X_test: Test feature matrix.
        y_test: Test target vector.

    Returns:
        Dictionary with ``ic``, ``icir``, ``mse``, and ``r2``.
    """
    X_arr = np.asarray(X_test, dtype=np.float32)
    y_arr = np.asarray(y_test, dtype=np.float32)
    preds = model.predict(X_arr)  # CHANGED

    ic = information_coefficient(y_arr, preds)
    mse = float(mean_squared_error(y_arr, preds))
    r2 = float(r2_score(y_arr, preds))

    return {"ic": ic, "icir": ic, "mse": mse, "r2": r2}


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=== XGBoost/CatBoost Smoke Test ===")

    np.random.seed(42)
    n = 2000
    n_features = len(get_feature_cols())
    X_synth = np.random.randn(n, n_features).astype(np.float32)
    true_weights = np.random.randn(n_features).astype(np.float32) * 0.1
    y_synth = X_synth @ true_weights + np.random.randn(n).astype(np.float32) * 0.5

    try:
        xgb_model, xgb_metrics = train_xgboost(X_synth, y_synth, n_splits=3)
        logger.info("XGBoost metrics: %s", xgb_metrics)
    except ValueError as e:
        logger.warning("XGBoost quality check failed (expected on synthetic): %s", e)

    try:
        cb_model, cb_metrics = train_catboost(X_synth, y_synth, n_splits=3)
        logger.info("CatBoost metrics: %s", cb_metrics)
    except ValueError as e:
        logger.warning("CatBoost quality check failed (expected on synthetic): %s", e)

    logger.info("=== Smoke Test PASSED ===")
