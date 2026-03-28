#!/usr/bin/env python3
"""
End-to-End Training Pipeline Orchestrator.

Runs all pipeline stages in order:
  1. Data collection (OHLCV + macro)
  2. Feature engineering
  3. Regime detection (GMM + HMM)
  4. XGBoost + CatBoost training
  5. LSTM training
  6. Ensemble stacking
  7. RL agent (SAC) training

Each step is logged with timestamps. Steps are skipped if --skip-existing
is set and a saved artifact already exists.

Usage:
    python scripts/train_pipeline.py
    python scripts/train_pipeline.py --start-date 2015-01-01 --end-date 2024-12-31
    python scripts/train_pipeline.py --skip-data-collection --models xgboost,catboost
    python scripts/train_pipeline.py --skip-existing
"""

from __future__ import annotations

import argparse
import logging
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # CHANGED
sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # CHANGED
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

TOTAL_STEPS = 7


def timestamp() -> str:
    """Return current time as [HH:MM:SS]."""
    return datetime.now().strftime("[%H:%M:%S]")


def step_banner(step: int, description: str) -> None:
    """Print a timestamped step banner."""
    print(f"\n{timestamp()} Step {step}/{TOTAL_STEPS}: {description}")
    print("-" * 60)


def artifact_exists(path: Path) -> bool:
    """Check if a saved artifact exists."""
    return path.exists()


def main() -> None:
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(description="NSE Quant Pipeline — Full Training Run")
    parser.add_argument("--start-date", default="2010-01-01", help="Start date for data")
    parser.add_argument("--end-date", default="2024-12-31", help="End date for data")
    parser.add_argument("--skip-data-collection", action="store_true",
                        help="Skip the data download step")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip steps that have saved artifacts")
    parser.add_argument("--models", default="xgboost,catboost,lstm,ensemble,sac",
                        help="Comma-separated list of models to train")
    args = parser.parse_args()

    models_to_train = set(args.models.lower().split(","))
    data_dir = PROJECT_ROOT / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    models_dir = PROJECT_ROOT / "models"

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    # MLflow setup — use local file-based tracking (no server required)
    mlflow.set_tracking_uri(f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}")
    mlflow.set_experiment("nse-quant-pipeline")

    print(f"\n{'='*60}")
    print(f"  NSE Quant Pipeline -- Training Run")  # CHANGED
    print(f"  Date range: {args.start_date} -> {args.end_date}")
    print(f"  Models: {args.models}")
    print(f"  Skip existing: {args.skip_existing}")
    print(f"{'='*60}")

    pipeline_start = time.time()
    metrics_summary: dict[str, Any] = {}

    # ── Start a PARENT MLflow run for the entire pipeline ──
    with mlflow.start_run(run_name=f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_param("start_date", args.start_date)
        mlflow.log_param("end_date", args.end_date)
        mlflow.log_param("models", args.models)

        # ──────────────────────────────────────────────────────────────
        # Step 1: Data Collection
        # ──────────────────────────────────────────────────────────────
        step_banner(1, "Data Collection")

        if args.skip_data_collection:
            print(f"{timestamp()} Skipped (--skip-data-collection)")
        elif args.skip_existing and any(raw_dir.glob("*.parquet")):
            print(f"{timestamp()} Skipped (parquet files already exist in {raw_dir})")
        else:
            from scripts.collect_data import main as collect_main
            sys.argv = [
                "collect_data.py",
                "--start", args.start_date,
                "--end", args.end_date,
            ]
            collect_main()

        # ──────────────────────────────────────────────────────────────
        # Step 2: Feature Engineering
        # ──────────────────────────────────────────────────────────────
        step_banner(2, "Feature Engineering")

        features_path = processed_dir / "features.parquet"

        if args.skip_existing and artifact_exists(features_path):
            print(f"{timestamp()} Loading cached features from {features_path}")
            features_df = pd.read_parquet(features_path)
        else:
            from ml.feature_engineering import (
                NIFTY_50_TICKERS, compute_all_features, download_ohlcv,
                load_macro_data, validate_no_lookahead,
            )

            # Try loading from parquet first, download if missing
            ticker_dfs: dict[str, pd.DataFrame] = {}
            for parquet_file in raw_dir.glob("*.parquet"):
                if parquet_file.name == "macro_data.parquet":
                    continue
                ticker_name = parquet_file.stem.replace("IDX_", "^").replace("_EQ_", "=")
                ticker_dfs[ticker_name] = pd.read_parquet(parquet_file)

            if not ticker_dfs:
                print(f"{timestamp()} No cached parquets — downloading from yfinance")
                ticker_dfs = download_ohlcv(NIFTY_50_TICKERS, args.start_date, args.end_date)

            macro_path = raw_dir / "macro_data.parquet"
            if macro_path.exists():
                macro_df = pd.read_parquet(macro_path)
            else:
                macro_df = load_macro_data(args.start_date, args.end_date)

            # CHANGED: FIX 5 — compute_all_features now includes cross_sectional_rank_normalize
            features_df = compute_all_features(ticker_dfs, macro_df)

            # Validate
            passed = validate_no_lookahead(features_df)
            print(f"{timestamp()} Lookahead check: {'PASSED [OK]' if passed else 'FAILED [FAIL]'}")  # CHANGED

            # Save (atomic)
            tmp = features_path.with_suffix(".tmp")
            features_df.to_parquet(tmp)
            tmp.replace(features_path)
            print(f"{timestamp()} Features saved: {features_df.shape}")

        # ──────────────────────────────────────────────────────────────
        # Step 3: Regime Detection
        # ──────────────────────────────────────────────────────────────
        step_banner(3, "Regime Detection (GMM + HMM)")

        gmm_path = models_dir / "regime_gmm.pkl"

        if args.skip_existing and artifact_exists(gmm_path):
            print(f"{timestamp()} Loading cached regime model")
            import pickle
            with open(gmm_path, "rb") as f:
                gmm = pickle.load(f)
            with open(models_dir / "regime_scaler.pkl", "rb") as f:
                scaler = pickle.load(f)
        else:
            from ml.regime_detector import (
                train_gmm, predict_regime, validate_stability,
                smooth_regimes, save_regime_artifacts, log_regime_to_mlflow,
            )

            # Use Nifty index data for regime training
            nifty_data = None
            nifty_parquet = raw_dir / "IDX_NSEI.parquet"
            if nifty_parquet.exists():
                nifty_data = pd.read_parquet(nifty_parquet)
            else:
                import yfinance as yf
                nifty_data = yf.download("^NSEI", start=args.start_date, end=args.end_date, progress=False)

            gmm, scaler = train_gmm(nifty_data, n_components=3)

            # Build regime features for prediction
            if isinstance(nifty_data.columns, pd.MultiIndex):
                nifty_data.columns = nifty_data.columns.get_level_values(0)
            close = nifty_data["Close"].squeeze()
            volume = nifty_data["Volume"].squeeze()

            regime_features = pd.DataFrame({
                "roll_ret": close.pct_change(20),
                "roll_vol": np.log(close / close.shift(1)).rolling(20).std() * np.sqrt(252),
                "vol_chg": volume.pct_change(20),
            }).dropna()

            regimes = predict_regime(gmm, scaler, regime_features)
            stability = validate_stability(regimes)
            print(f"{timestamp()} Regime stability: flip_rate={stability['flip_rate']:.3f}")

            if stability["flip_rate"] > 0.05:
                print(f"{timestamp()} Flip rate > 5% — applying smoothing")
                regimes = smooth_regimes(regimes)

            save_regime_artifacts(gmm, scaler, models_dir)

            # Add regime labels to features
            features_df["regime_label"] = regimes.reindex(features_df.index).ffill().fillna(1).astype(int)

        # Ensure regime_label exists
        if "regime_label" not in features_df.columns:
            features_df["regime_label"] = 1  # default: sideways

        # ──────────────────────────────────────────────────────────────
        # Prepare training data
        # ──────────────────────────────────────────────────────────────
        from ml.xgboost_model import get_feature_cols

        feature_cols = [c for c in get_feature_cols() if c in features_df.columns]
        target_col = "target_fwd_5d"

        # Drop NaN rows
        train_df = features_df[feature_cols + [target_col]].dropna()
        X = train_df[feature_cols].values.astype(np.float32)
        y = train_df[target_col].values.astype(np.float32)

        print(f"\n{timestamp()} Training data: X={X.shape}, y={y.shape}")
        mlflow.log_metric("training_samples", X.shape[0])
        mlflow.log_metric("n_features", X.shape[1])

        n_rows = len(X)  # CHANGED
        if n_rows < 50_000:  # CHANGED
            logger.warning(  # CHANGED
                "Training data has only %d rows. Recommend at least 3 years of data "  # CHANGED
                "(50k+ rows) for stable XGBoost CV. Use --start-date 2021-01-01 or earlier.",  # CHANGED
                n_rows,  # CHANGED
            )  # CHANGED
            print(  # CHANGED
                f"{timestamp()} [WARN] Only {n_rows} training rows. "  # CHANGED
                "XGBoost CV may be unreliable -- use --start-date 2021-01-01 or earlier."  # CHANGED
            )  # CHANGED

        tscv = TimeSeriesSplit(n_splits=5, gap=2)

        xgb_model = None
        cb_model = None
        lstm_model_obj = None

        # ──────────────────────────────────────────────────────────────
        # Step 4: XGBoost + CatBoost
        # ──────────────────────────────────────────────────────────────
        if "xgboost" in models_to_train or "catboost" in models_to_train:
            step_banner(4, "XGBoost + CatBoost Training")

            from ml.xgboost_model import train_xgboost, train_catboost

            if "xgboost" in models_to_train:
                try:
                    xgb_model, xgb_metrics = train_xgboost(X, y)
                    metrics_summary["xgb_ic"] = xgb_metrics["ic_mean"]
                    metrics_summary["xgb_icir"] = xgb_metrics["icir"]
                    print(f"{timestamp()} XGBoost: IC={xgb_metrics['ic_mean']:.4f} ICIR={xgb_metrics['icir']:.4f}")
                except ValueError as e:
                    print(f"{timestamp()} XGBoost quality check failed: {e}")

            if "catboost" in models_to_train:
                try:
                    cb_model, cb_metrics = train_catboost(X, y)
                    metrics_summary["cb_ic"] = cb_metrics["ic_mean"]
                    metrics_summary["cb_icir"] = cb_metrics["icir"]
                    print(f"{timestamp()} CatBoost: IC={cb_metrics['ic_mean']:.4f} ICIR={cb_metrics['icir']:.4f}")
                except ValueError as e:
                    print(f"{timestamp()} CatBoost quality check failed: {e}")
        else:
            step_banner(4, "XGBoost + CatBoost — SKIPPED")

        # ──────────────────────────────────────────────────────────────
        # Step 5: LSTM  # CHANGED: FIX 1 — wrapped in try/except for non-fatal CUDA failure
        # ──────────────────────────────────────────────────────────────
        if "lstm" in models_to_train:
            step_banner(5, "LSTM Training")

            try:  # CHANGED: FIX 1 — non-fatal LSTM wrapper
                from ml.lstm_model import LSTMPredictor, create_sequences, train_lstm  # CHANGED: FIX 1

                X_seq, y_seq = create_sequences(train_df, seq_len=20)  # CHANGED: FIX 6 — seq_len=20
                lstm_net = LSTMPredictor(input_size=X_seq.shape[2])  # CHANGED: FIX 6 — uses new 256/128 defaults
                lstm_model_obj = train_lstm(lstm_net, X_seq, y_seq, epochs=50)  # CHANGED: FIX 6 — epochs=50
                print(f"{timestamp()} LSTM training complete")
            except Exception as e:  # CHANGED: FIX 1 — catch ALL exceptions including CUDA runtime
                logger.warning(  # CHANGED: FIX 1 — log warning instead of crashing
                    "LSTM training failed (non-fatal): %s", e  # CHANGED: FIX 1
                )  # CHANGED: FIX 1
                print(f"{timestamp()} LSTM training failed (non-fatal): {e}")  # CHANGED: FIX 1
                lstm_model_obj = None  # CHANGED: FIX 1 — ensure it's None for ensemble
        else:
            step_banner(5, "LSTM -- SKIPPED")

        # ──────────────────────────────────────────────────────────────
        # Step 6: Ensemble  # CHANGED: FIX 3 — uses NNLS meta-learner
        # ──────────────────────────────────────────────────────────────
        if "ensemble" in models_to_train and xgb_model is not None and cb_model is not None:
            step_banner(6, "Ensemble Stacking")

            from ml.ensemble import (
                collect_oof_predictions, evaluate_ensemble,
                save_ensemble, train_meta_learner,
            )

            try:
                L1 = collect_oof_predictions(xgb_model, cb_model, None, X, y, tscv)
                meta = train_meta_learner(L1, y)  # CHANGED: FIX 3 — returns NNLSMetaLearner

                # Evaluate on last fold
                last_fold_idx = list(tscv.split(X))[-1][1]
                ens_metrics = evaluate_ensemble(meta, L1[last_fold_idx], y[last_fold_idx])
                metrics_summary["ensemble_ic"] = ens_metrics["ic"]

                save_ensemble(xgb_model, cb_model, None, meta, models_dir / "ensemble")
                print(f"{timestamp()} Ensemble IC={ens_metrics['ic']:.4f} (improvement={ens_metrics['improvement_over_best_base']:.4f})")
            except Exception as e:
                print(f"{timestamp()} Ensemble training failed: {e}")
        else:
            step_banner(6, "Ensemble — SKIPPED (missing base models)")

        # ──────────────────────────────────────────────────────────────
        # Step 7: RL Agent (SAC)
        # ──────────────────────────────────────────────────────────────
        if "sac" in models_to_train:
            step_banner(7, "RL Agent (SAC) Training")

            from ml.rl_agent import build_env, train_sac, backtest

            try:
                rl_df = features_df[features_df["ticker"].notna()].copy() if "ticker" in features_df.columns else features_df.copy()
                if "ret_1d" not in rl_df.columns:
                    rl_df["ret_1d"] = 0.0
                if "ticker" not in rl_df.columns:
                    rl_df["ticker"] = "NIFTY"

                # Temporal split: 80% train, 20% test
                unique_dates = sorted(rl_df.index.unique())
                split_date = unique_dates[int(len(unique_dates) * 0.8)]

                env_train = build_env(rl_df[rl_df.index <= split_date])
                env_test = build_env(rl_df[rl_df.index > split_date])

                sac_model = train_sac(env_train, total_timesteps=5_000)  # Reduced for testing
                bt_metrics = backtest(sac_model, env_test)
                metrics_summary["sac_sharpe"] = bt_metrics["sharpe"]

                print(f"{timestamp()} SAC Sharpe={bt_metrics['sharpe']:.2f}, MaxDD={bt_metrics['max_drawdown']:.2%}")
            except Exception as e:
                print(f"{timestamp()} SAC training failed: {e}")
        else:
            step_banner(7, "RL Agent — SKIPPED")

        # ──────────────────────────────────────────────────────────────
        # Final Summary
        # ──────────────────────────────────────────────────────────────
        elapsed = time.time() - pipeline_start

        # Log final summary to MLflow
        for metric, value in metrics_summary.items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(metric, value)

        mlflow.log_metric("pipeline_duration_seconds", elapsed)

    print(f"\n{'='*60}")
    print(f"  TRAINING PIPELINE COMPLETE")
    print(f"  Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    if n_rows < 50_000:  # CHANGED
        print(f"  [WARN] Small dataset: {n_rows} rows (recommend 50k+)")  # CHANGED
    print(f"{'='*60}")
    print(f"\n  {'Metric':<25} {'Value':>10}")
    print(f"  {'-'*36}")

    for metric, value in metrics_summary.items():
        if isinstance(value, float):
            print(f"  {metric:<25} {value:>10.4f}")
        else:
            print(f"  {metric:<25} {str(value):>10}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    main()
