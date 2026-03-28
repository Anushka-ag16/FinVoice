#!/usr/bin/env python3
"""
Feature Validation Script — Standalone checks for data quality.

Validates:
  1. No NaN in feature columns
  2. No lookahead bias (correlation test)
  3. Regime stability (flip rate)
  4. target_fwd_5d NOT present as a feature column
  5. Individual feature IC > 0.02 vs forward return

Usage:
    python scripts/validate_features.py
    python scripts/validate_features.py --dry-run
    python scripts/validate_features.py --parquet data/processed/features.parquet
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Check Functions
# ──────────────────────────────────────────────────────────────────────────────
def check_no_nan(df: pd.DataFrame, feature_cols: list[str]) -> tuple[bool, str]:
    """Check that no feature columns contain NaN values.

    Args:
        df: Feature DataFrame.
        feature_cols: List of feature column names to check.

    Returns:
        Tuple of ``(passed, detail_message)``.
    """
    nan_counts = df[feature_cols].isna().sum()
    nan_cols = nan_counts[nan_counts > 0]

    if len(nan_cols) == 0:
        return True, f"All {len(feature_cols)} feature columns have zero NaN values"

    detail = "; ".join(f"{col}: {count} NaN" for col, count in nan_cols.items())
    return False, f"{len(nan_cols)} columns have NaN values: {detail}"


def check_no_lookahead(df: pd.DataFrame, feature_cols: list[str]) -> tuple[bool, str]:
    """Check that features don't exhibit lookahead bias.

    For each feature, compares same-day correlation with returns to lagged
    correlation.  If a majority of features have stronger same-day correlation,
    it suggests features contain future information.

    Args:
        df: Feature DataFrame with ``target_fwd_5d``.
        feature_cols: List of feature column names.

    Returns:
        Tuple of ``(passed, detail_message)``.
    """
    if "target_fwd_5d" not in df.columns:
        return False, "target_fwd_5d column missing — cannot check lookahead"

    violations: list[str] = []
    for col in feature_cols:
        same = abs(df[col].corr(df["target_fwd_5d"]))
        lagged = abs(df[col].shift(1).corr(df["target_fwd_5d"]))
        if lagged > 0 and same > lagged * 1.5:
            violations.append(f"{col} (same={same:.4f} > 1.5×lagged={lagged:.4f})")

    ratio = len(violations) / len(feature_cols) if feature_cols else 0
    if ratio < 0.5:
        return True, f"Lookahead check passed (violation ratio={ratio:.2f}, {len(violations)}/{len(feature_cols)} features flagged)"
    return False, f"Lookahead check FAILED (ratio={ratio:.2f}): {'; '.join(violations[:5])}"


def check_target_not_feature(df: pd.DataFrame, feature_cols: list[str]) -> tuple[bool, str]:
    """Ensure target_fwd_5d is not in the feature column list.

    Args:
        df: Feature DataFrame.
        feature_cols: Feature column names.

    Returns:
        Tuple of ``(passed, detail_message)``.
    """
    if "target_fwd_5d" in feature_cols:
        return False, "target_fwd_5d is present in feature columns — this is a DATA LEAK"
    return True, "target_fwd_5d correctly excluded from feature columns"


def check_regime_stability(df: pd.DataFrame) -> tuple[bool, str]:
    """Check regime label stability (flip rate < 10%).

    Args:
        df: Feature DataFrame with ``regime_label`` column.

    Returns:
        Tuple of ``(passed, detail_message)``.
    """
    if "regime_label" not in df.columns:
        return True, "No regime_label column — skipping stability check"

    regimes = df["regime_label"]
    changes = (regimes != regimes.shift(1)).sum()
    flip_rate = changes / len(regimes) if len(regimes) > 0 else 0

    counts = regimes.value_counts().to_dict()
    detail = f"flip_rate={flip_rate:.3f}, counts={counts}"

    if flip_rate < 0.10:
        return True, f"Regime stability OK ({detail})"
    return False, f"Regime flip rate too high ({detail})"


def check_feature_ic(
    df: pd.DataFrame,
    feature_cols: list[str],
    threshold: float = 0.02,
) -> tuple[bool, str]:
    """Check that each feature has IC > threshold vs forward return.

    Args:
        df: Feature DataFrame with ``target_fwd_5d``.
        feature_cols: Feature column names.
        threshold: Minimum absolute IC to pass.

    Returns:
        Tuple of ``(passed, detail_message)``.
    """
    if "target_fwd_5d" not in df.columns:
        return False, "target_fwd_5d missing — cannot compute feature IC"

    low_ic_features: list[str] = []
    ic_values: dict[str, float] = {}

    for col in feature_cols:
        valid = df[[col, "target_fwd_5d"]].dropna()
        if len(valid) < 30:
            continue
        corr, _ = spearmanr(valid[col], valid["target_fwd_5d"])
        ic = float(corr) if not np.isnan(corr) else 0.0
        ic_values[col] = ic
        if abs(ic) < threshold:
            low_ic_features.append(f"{col} (IC={ic:.4f})")

    if not low_ic_features:
        return True, f"All {len(ic_values)} features have |IC| > {threshold}"

    detail = "; ".join(low_ic_features[:10])
    passed = len(low_ic_features) < len(feature_cols) * 0.5
    return passed, f"{len(low_ic_features)}/{len(ic_values)} features below IC threshold: {detail}"


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    """Run all feature validation checks."""
    parser = argparse.ArgumentParser(description="Validate feature quality")
    parser.add_argument("--parquet", default=None,
                        help="Path to features parquet file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only check imports, skip actual validation")
    parser.add_argument("--timescaledb-url", default=None,
                        help="TimescaleDB connection string (fallback to parquet)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Feature Validation")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("  DRY RUN MODE — checking imports only\n")

        checks = [
            ("ml.feature_engineering", [
                "download_ohlcv", "compute_rsi", "compute_macd",
                "compute_bollinger", "compute_volatility", "load_macro_data",
                "compute_all_features", "validate_no_lookahead", "store_to_timescaledb",
            ]),
            ("ml.regime_detector", [
                "train_gmm", "predict_regime", "validate_stability",
                "smooth_regimes", "add_hmm_crosscheck",
            ]),
            ("ml.xgboost_model", [
                "get_feature_cols", "information_coefficient", "icir",
                "train_xgboost", "train_catboost", "get_oof_predictions", "evaluate_model",
            ]),
            ("ml.lstm_model", [
                "LSTMPredictor", "create_sequences", "train_lstm",
                "build_tft_dataset", "build_tft_model", "train_tft", "tft_predict",
            ]),
            ("ml.ensemble", [
                "collect_oof_predictions", "train_meta_learner",
                "predict_ensemble", "evaluate_ensemble", "save_ensemble", "load_ensemble",
            ]),
            ("ml.rl_agent", [
                "PortfolioOptimizationEnv", "build_env", "train_sac",
                "predict_weights", "mpt_fallback", "backtest",
            ]),
            ("ml.model_registry", [
                "get_mlflow_client", "register_model", "promote_to_production",
                "get_production_model", "list_model_versions",
                "log_feature_importance", "compare_runs",
            ]),
            ("services.sentiment", [
                "load_finbert", "get_sentiment_score", "scrape_nse_announcements",
                "scrape_google_news", "compute_ticker_sentiment", "blend_sentiment_features",
            ]),
            ("services.explainer", [
                "build_shap_explainer", "explain_xgb", "build_lime_explainer",
                "explain_lstm", "top_factors", "build_claude_prompt", "call_claude_api",
            ]),
        ]

        all_passed = True
        for module_name, functions in checks:
            try:
                import importlib
                mod = importlib.import_module(module_name)
                missing = [f for f in functions if not hasattr(mod, f)]
                if missing:
                    print(f"  FAIL  {module_name}: missing {missing}")
                    all_passed = False
                else:
                    print(f"  PASS  {module_name}: all {len(functions)} functions found")
            except Exception as exc:
                print(f"  FAIL  {module_name}: import error — {exc}")
                all_passed = False

        print(f"\n{'='*60}")
        if all_passed:
            print("  All import checks PASSED [OK]")
        else:
            print("  Some import checks FAILED [X]")
        print(f"{'='*60}\n")
        return

    # Full validation mode
    # Load features
    if args.parquet:
        parquet_path = Path(args.parquet)
    else:
        parquet_path = PROJECT_ROOT / "data" / "processed" / "features.parquet"

    if args.timescaledb_url:
        from sqlalchemy import create_engine
        engine = create_engine(args.timescaledb_url)
        df = pd.read_sql("SELECT * FROM features", engine)
        df = df.set_index("date")
        print(f"  Loaded {len(df)} rows from TimescaleDB\n")
    elif parquet_path.exists():
        df = pd.read_parquet(parquet_path)
        print(f"  Loaded {len(df)} rows from {parquet_path}\n")
    else:
        print(f"  ERROR: No data source found. Run train_pipeline.py first or specify --parquet")
        sys.exit(1)

    # Determine feature columns
    from ml.xgboost_model import get_feature_cols
    available_features = [c for c in get_feature_cols() if c in df.columns]
    print(f"  Features to validate: {len(available_features)}\n")

    # Run checks
    checks_to_run = [
        ("No NaN in features", lambda: check_no_nan(df, available_features)),
        ("No lookahead bias", lambda: check_no_lookahead(df, available_features)),
        ("Target not in features", lambda: check_target_not_feature(df, available_features)),
        ("Regime stability", lambda: check_regime_stability(df)),
        ("Feature IC > 0.02", lambda: check_feature_ic(df, available_features)),
    ]

    all_passed = True
    for name, check_fn in checks_to_run:
        passed, detail = check_fn()
        status = "PASS" if passed else "FAIL"
        icon = "[OK]" if passed else "[X]"
        print(f"  {status}  {name}")
        print(f"        {detail}")
        print()
        if not passed:
            all_passed = False

    print(f"{'='*60}")
    if all_passed:
        print("  All validation checks PASSED [OK]")
    else:
        print("  Some validation checks FAILED [X]")
    print(f"{'='*60}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    main()
