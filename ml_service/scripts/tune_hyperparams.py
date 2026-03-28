#!/usr/bin/env python3
"""
Optuna Hyperparameter Tuning — NSE/Nifty 50 Quantitative Pipeline.  # CHANGED: FIX 7 — new file

Runs Bayesian hyperparameter optimisation (TPE sampler) for XGBoost and/or
CatBoost models using purged walk-forward cross-validation (gap=5 to match
the 5-day prediction horizon).

Usage:
    python scripts/tune_hyperparams.py --model both --n-trials 50
    python scripts/tune_hyperparams.py --model xgboost --n-trials 100
    python scripts/tune_hyperparams.py --model catboost --n-trials 30

Results:
    - Best params saved to models/best_params_xgb.json, models/best_params_cb.json
    - All trials logged to MLflow experiment "nse-hyperparameter-tuning"
"""

from __future__ import annotations  # CHANGED: FIX 7

import argparse  # CHANGED: FIX 7
import json  # CHANGED: FIX 7
import logging  # CHANGED: FIX 7
import sys  # CHANGED: FIX 7
from pathlib import Path  # CHANGED: FIX 7
from typing import Any  # CHANGED: FIX 7

import mlflow  # CHANGED: FIX 7
import numpy as np  # CHANGED: FIX 7
import optuna  # CHANGED: FIX 7
import pandas as pd  # CHANGED: FIX 7
from optuna.samplers import TPESampler  # CHANGED: FIX 7
from scipy.stats import spearmanr  # CHANGED: FIX 7
from sklearn.model_selection import TimeSeriesSplit  # CHANGED: FIX 7

# Add project root to path  # CHANGED: FIX 7
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # CHANGED: FIX 7
sys.path.insert(0, str(PROJECT_ROOT))  # CHANGED: FIX 7

logger = logging.getLogger(__name__)  # CHANGED: FIX 7


# ──────────────────────────────────────────────────────────────────────────────
# Helpers  # CHANGED: FIX 7
# ──────────────────────────────────────────────────────────────────────────────
def _ic(y_true: np.ndarray, y_pred: np.ndarray) -> float:  # CHANGED: FIX 7
    """Compute Spearman IC safely."""  # CHANGED: FIX 7
    corr, _ = spearmanr(y_true, y_pred)  # CHANGED: FIX 7
    return float(corr) if not np.isnan(corr) else 0.0  # CHANGED: FIX 7


def _load_training_data() -> tuple[np.ndarray, np.ndarray]:  # CHANGED: FIX 7
    """Load the processed feature matrix for tuning.

    Returns:
        Tuple ``(X, y)`` as float32 arrays.

    Raises:
        FileNotFoundError: If features.parquet does not exist.
    """
    features_path = PROJECT_ROOT / "data" / "processed" / "features.parquet"  # CHANGED: FIX 7
    if not features_path.exists():  # CHANGED: FIX 7
        raise FileNotFoundError(  # CHANGED: FIX 7
            f"Feature file not found at {features_path}. "  # CHANGED: FIX 7
            "Run the training pipeline first (Step 1–3)."  # CHANGED: FIX 7
        )  # CHANGED: FIX 7

    df = pd.read_parquet(features_path)  # CHANGED: FIX 7

    from ml.xgboost_model import get_feature_cols  # CHANGED: FIX 7

    feature_cols = [c for c in get_feature_cols() if c in df.columns]  # CHANGED: FIX 7
    target_col = "target_fwd_5d"  # CHANGED: FIX 7

    # Ensure regime_label exists  # CHANGED: FIX 7
    if "regime_label" not in df.columns:  # CHANGED: FIX 7
        df["regime_label"] = 1  # CHANGED: FIX 7

    train_df = df[feature_cols + [target_col]].dropna()  # CHANGED: FIX 7
    X = train_df[feature_cols].values.astype(np.float32)  # CHANGED: FIX 7
    y = train_df[target_col].values.astype(np.float32)  # CHANGED: FIX 7

    logger.info("Loaded training data: X=%s, y=%s", X.shape, y.shape)  # CHANGED: FIX 7
    return X, y  # CHANGED: FIX 7


# ──────────────────────────────────────────────────────────────────────────────
# GPU Detection  # CHANGED: FIX 7
# ──────────────────────────────────────────────────────────────────────────────
try:  # CHANGED: FIX 7
    import torch  # CHANGED: FIX 7
    HAS_CUDA = torch.cuda.is_available()  # CHANGED: FIX 7
    if HAS_CUDA:  # CHANGED: FIX 7
        cc = torch.cuda.get_device_capability()  # CHANGED: FIX 7
        if cc[0] < 8:  # CHANGED: FIX 7
            HAS_CUDA = False  # CHANGED: FIX 7
except Exception:  # CHANGED: FIX 7
    HAS_CUDA = False  # CHANGED: FIX 7


# ──────────────────────────────────────────────────────────────────────────────
# XGBoost Objective  # CHANGED: FIX 7
# ──────────────────────────────────────────────────────────────────────────────
def objective_xgb(trial: optuna.Trial) -> float:  # CHANGED: FIX 7
    """Optuna objective for XGBoost: returns mean IC over purged walk-forward CV.

    Args:
        trial: Optuna trial for hyperparameter suggestion.

    Returns:
        Mean IC across 5-fold purged TimeSeriesSplit CV.
    """
    from xgboost import XGBRegressor  # CHANGED: FIX 7

    X, y = _load_training_data()  # CHANGED: FIX 7

    params = dict(  # CHANGED: FIX 7
        max_depth=trial.suggest_int("max_depth", 4, 8),  # CHANGED: FIX 7
        n_estimators=trial.suggest_int("n_estimators", 300, 1500, step=100),  # CHANGED: FIX 7
        learning_rate=trial.suggest_float("learning_rate", 0.01, 0.1, log=True),  # CHANGED: FIX 7
        subsample=trial.suggest_float("subsample", 0.6, 1.0),  # CHANGED: FIX 7
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),  # CHANGED: FIX 7
        min_child_weight=trial.suggest_int("min_child_weight", 3, 20),  # CHANGED: FIX 7
        gamma=trial.suggest_float("gamma", 0.0, 0.5),  # CHANGED: FIX 7
        reg_alpha=trial.suggest_float("reg_alpha", 0.0, 2.0),  # CHANGED: FIX 7
        reg_lambda=trial.suggest_float("reg_lambda", 0.5, 5.0),  # CHANGED: FIX 7
        tree_method="hist",  # CHANGED: FIX 7
        device="cuda" if HAS_CUDA else "cpu",  # CHANGED: FIX 7
        random_state=42,  # CHANGED: FIX 7
        verbosity=0,  # CHANGED: FIX 7
    )  # CHANGED: FIX 7

    # Purged walk-forward CV with gap=5 (matches 5-day prediction horizon)  # CHANGED: FIX 7
    tscv = TimeSeriesSplit(n_splits=5, gap=5)  # CHANGED: FIX 7 — FIX 4
    ic_scores: list[float] = []  # CHANGED: FIX 7

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):  # CHANGED: FIX 7
        model = XGBRegressor(**params)  # CHANGED: FIX 7
        model.fit(  # CHANGED: FIX 7
            X[train_idx], y[train_idx],  # CHANGED: FIX 7
            eval_set=[(X[val_idx], y[val_idx])],  # CHANGED: FIX 7
            verbose=False,  # CHANGED: FIX 7
        )  # CHANGED: FIX 7
        preds = model.predict(X[val_idx])  # CHANGED: FIX 7
        ic_scores.append(_ic(y[val_idx], preds))  # CHANGED: FIX 7

    mean_ic = float(np.mean(ic_scores))  # CHANGED: FIX 7

    # Log to MLflow  # CHANGED: FIX 7
    mlflow.set_experiment("nse-hyperparameter-tuning")  # CHANGED: FIX 7
    with mlflow.start_run(run_name=f"xgb_trial_{trial.number}", nested=True):  # CHANGED: FIX 7
        mlflow.log_params(params)  # CHANGED: FIX 7
        mlflow.log_metric("mean_ic", mean_ic)  # CHANGED: FIX 7
        for i, ic_val in enumerate(ic_scores):  # CHANGED: FIX 7
            mlflow.log_metric(f"ic_fold_{i}", ic_val)  # CHANGED: FIX 7

    return mean_ic  # CHANGED: FIX 7


# ──────────────────────────────────────────────────────────────────────────────
# CatBoost Objective  # CHANGED: FIX 7
# ──────────────────────────────────────────────────────────────────────────────
def objective_cb(trial: optuna.Trial) -> float:  # CHANGED: FIX 7
    """Optuna objective for CatBoost: returns mean IC over purged walk-forward CV.

    Args:
        trial: Optuna trial for hyperparameter suggestion.

    Returns:
        Mean IC across 5-fold purged TimeSeriesSplit CV.
    """
    from catboost import CatBoostRegressor  # CHANGED: FIX 7

    X, y = _load_training_data()  # CHANGED: FIX 7

    params = dict(  # CHANGED: FIX 7
        depth=trial.suggest_int("depth", 4, 8),  # CHANGED: FIX 7
        iterations=trial.suggest_int("iterations", 300, 1500, step=100),  # CHANGED: FIX 7
        learning_rate=trial.suggest_float("learning_rate", 0.01, 0.1, log=True),  # CHANGED: FIX 7
        subsample=trial.suggest_float("subsample", 0.6, 1.0),  # CHANGED: FIX 7
        l2_leaf_reg=trial.suggest_float("l2_leaf_reg", 0.5, 5.0),  # CHANGED: FIX 7
        min_child_samples=trial.suggest_int("min_child_samples", 3, 20),  # CHANGED: FIX 7
        random_strength=trial.suggest_float("random_strength", 0.0, 2.0),  # CHANGED: FIX 7
        early_stopping_rounds=50,  # CHANGED: FIX 7
        task_type="GPU" if HAS_CUDA else "CPU",  # CHANGED: FIX 7
        random_seed=42,  # CHANGED: FIX 7
        verbose=0,  # CHANGED: FIX 7
        loss_function="RMSE",  # CHANGED: FIX 7
    )  # CHANGED: FIX 7

    # Purged walk-forward CV with gap=5  # CHANGED: FIX 7
    tscv = TimeSeriesSplit(n_splits=5, gap=5)  # CHANGED: FIX 7 — FIX 4
    ic_scores: list[float] = []  # CHANGED: FIX 7

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):  # CHANGED: FIX 7
        model = CatBoostRegressor(**params)  # CHANGED: FIX 7
        model.fit(  # CHANGED: FIX 7
            X[train_idx], y[train_idx],  # CHANGED: FIX 7
            eval_set=(X[val_idx], y[val_idx]),  # CHANGED: FIX 7
            verbose=0,  # CHANGED: FIX 7
        )  # CHANGED: FIX 7
        preds = model.predict(X[val_idx])  # CHANGED: FIX 7
        ic_scores.append(_ic(y[val_idx], preds))  # CHANGED: FIX 7

    mean_ic = float(np.mean(ic_scores))  # CHANGED: FIX 7

    # Log to MLflow  # CHANGED: FIX 7
    mlflow.set_experiment("nse-hyperparameter-tuning")  # CHANGED: FIX 7
    with mlflow.start_run(run_name=f"cb_trial_{trial.number}", nested=True):  # CHANGED: FIX 7
        mlflow.log_params({k: str(v) for k, v in params.items()})  # CHANGED: FIX 7
        mlflow.log_metric("mean_ic", mean_ic)  # CHANGED: FIX 7
        for i, ic_val in enumerate(ic_scores):  # CHANGED: FIX 7
            mlflow.log_metric(f"ic_fold_{i}", ic_val)  # CHANGED: FIX 7

    return mean_ic  # CHANGED: FIX 7


# ──────────────────────────────────────────────────────────────────────────────
# Main  # CHANGED: FIX 7
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:  # CHANGED: FIX 7
    """Run Optuna hyperparameter tuning for the specified model(s)."""  # CHANGED: FIX 7
    parser = argparse.ArgumentParser(  # CHANGED: FIX 7
        description="Optuna hyperparameter tuning for NSE Quant Pipeline"  # CHANGED: FIX 7
    )  # CHANGED: FIX 7
    parser.add_argument(  # CHANGED: FIX 7
        "--model",  # CHANGED: FIX 7
        default="both",  # CHANGED: FIX 7
        choices=["xgboost", "catboost", "both"],  # CHANGED: FIX 7
        help="Which model to tune (default: both)",  # CHANGED: FIX 7
    )  # CHANGED: FIX 7
    parser.add_argument(  # CHANGED: FIX 7
        "--n-trials",  # CHANGED: FIX 7
        type=int,  # CHANGED: FIX 7
        default=50,  # CHANGED: FIX 7
        help="Number of Optuna trials (default: 50)",  # CHANGED: FIX 7
    )  # CHANGED: FIX 7
    args = parser.parse_args()  # CHANGED: FIX 7

    models_dir = PROJECT_ROOT / "models"  # CHANGED: FIX 7
    models_dir.mkdir(parents=True, exist_ok=True)  # CHANGED: FIX 7

    # MLflow setup  # CHANGED: FIX 7
    mlflow.set_tracking_uri(f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}")  # CHANGED: FIX 7
    mlflow.set_experiment("nse-hyperparameter-tuning")  # CHANGED: FIX 7

    print(f"\n{'='*60}")  # CHANGED: FIX 7
    print(f"  Optuna Hyperparameter Tuning")  # CHANGED: FIX 7
    print(f"  Model: {args.model}  |  Trials: {args.n_trials}")  # CHANGED: FIX 7
    print(f"  GPU: {HAS_CUDA}")  # CHANGED: FIX 7
    print(f"{'='*60}\n")  # CHANGED: FIX 7

    results: dict[str, dict[str, Any]] = {}  # CHANGED: FIX 7

    # ── XGBoost ──  # CHANGED: FIX 7
    if args.model in ("xgboost", "both"):  # CHANGED: FIX 7
        print("\n--- XGBoost Tuning ---")  # CHANGED: FIX 7
        study_xgb = optuna.create_study(  # CHANGED: FIX 7
            direction="maximize",  # CHANGED: FIX 7 — maximise IC
            sampler=TPESampler(seed=42),  # CHANGED: FIX 7
            study_name="xgboost_tuning",  # CHANGED: FIX 7
        )  # CHANGED: FIX 7
        study_xgb.optimize(  # CHANGED: FIX 7
            objective_xgb, n_trials=args.n_trials, show_progress_bar=True  # CHANGED: FIX 7
        )  # CHANGED: FIX 7

        best_xgb = study_xgb.best_params  # CHANGED: FIX 7
        best_xgb_ic = study_xgb.best_value  # CHANGED: FIX 7

        # Save best params  # CHANGED: FIX 7
        xgb_params_path = models_dir / "best_params_xgb.json"  # CHANGED: FIX 7
        with open(xgb_params_path, "w") as f:  # CHANGED: FIX 7
            json.dump(  # CHANGED: FIX 7
                {"best_params": best_xgb, "best_ic": best_xgb_ic}, f, indent=2  # CHANGED: FIX 7
            )  # CHANGED: FIX 7
        logger.info("XGBoost best params saved to %s", xgb_params_path)  # CHANGED: FIX 7
        results["XGBoost"] = {"params": best_xgb, "ic": best_xgb_ic}  # CHANGED: FIX 7

    # ── CatBoost ──  # CHANGED: FIX 7
    if args.model in ("catboost", "both"):  # CHANGED: FIX 7
        print("\n--- CatBoost Tuning ---")  # CHANGED: FIX 7
        study_cb = optuna.create_study(  # CHANGED: FIX 7
            direction="maximize",  # CHANGED: FIX 7
            sampler=TPESampler(seed=42),  # CHANGED: FIX 7
            study_name="catboost_tuning",  # CHANGED: FIX 7
        )  # CHANGED: FIX 7
        study_cb.optimize(  # CHANGED: FIX 7
            objective_cb, n_trials=args.n_trials, show_progress_bar=True  # CHANGED: FIX 7
        )  # CHANGED: FIX 7

        best_cb = study_cb.best_params  # CHANGED: FIX 7
        best_cb_ic = study_cb.best_value  # CHANGED: FIX 7

        # Save best params  # CHANGED: FIX 7
        cb_params_path = models_dir / "best_params_cb.json"  # CHANGED: FIX 7
        with open(cb_params_path, "w") as f:  # CHANGED: FIX 7
            json.dump(  # CHANGED: FIX 7
                {"best_params": best_cb, "best_ic": best_cb_ic}, f, indent=2  # CHANGED: FIX 7
            )  # CHANGED: FIX 7
        logger.info("CatBoost best params saved to %s", cb_params_path)  # CHANGED: FIX 7
        results["CatBoost"] = {"params": best_cb, "ic": best_cb_ic}  # CHANGED: FIX 7

    # ── Summary Table ──  # CHANGED: FIX 7
    print(f"\n{'='*60}")  # CHANGED: FIX 7
    print(f"  TUNING RESULTS SUMMARY")  # CHANGED: FIX 7
    print(f"{'='*60}")  # CHANGED: FIX 7

    for model_name, res in results.items():  # CHANGED: FIX 7
        print(f"\n  {model_name}:")  # CHANGED: FIX 7
        print(f"    Best IC: {res['ic']:.6f}")  # CHANGED: FIX 7
        print(f"    {'Parameter':<25} {'Value':>12}")  # CHANGED: FIX 7
        print(f"    {'-'*38}")  # CHANGED: FIX 7
        for param, value in res["params"].items():  # CHANGED: FIX 7
            if isinstance(value, float):  # CHANGED: FIX 7
                print(f"    {param:<25} {value:>12.6f}")  # CHANGED: FIX 7
            else:  # CHANGED: FIX 7
                print(f"    {param:<25} {str(value):>12}")  # CHANGED: FIX 7

    print(f"\n{'='*60}\n")  # CHANGED: FIX 7


if __name__ == "__main__":  # CHANGED: FIX 7
    logging.basicConfig(  # CHANGED: FIX 7
        level=logging.INFO,  # CHANGED: FIX 7
        format="%(asctime)s %(levelname)s %(message)s",  # CHANGED: FIX 7
    )  # CHANGED: FIX 7
    main()  # CHANGED: FIX 7
