"""
Regime Detector Module — Market Regime Classification for NSE/Nifty 50.

Uses a Gaussian Mixture Model (GMM) as the primary classifier and a Gaussian
Hidden Markov Model (HMM) as a stability cross-check.  Regimes are labelled by
their mean return in ascending order: 0 = bear, 1 = sideways, 2 = bull.

If the regime flip rate exceeds 5 %, rolling-mode smoothing is applied
automatically to reduce noise.
"""

from __future__ import annotations

import logging
import pickle
import tempfile
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
try:
    from hmmlearn.hmm import GaussianHMM
    HAS_HMM = True
except ImportError:
    HAS_HMM = False
from scipy import stats as sp_stats
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# GMM Training
# ──────────────────────────────────────────────────────────────────────────────
def train_gmm(
    nifty_df: pd.DataFrame,
    n_components: int = 3,
) -> tuple[GaussianMixture, StandardScaler]:
    """Train a Gaussian Mixture Model for market-regime classification.

    Features used for clustering:
      - 20-day rolling return
      - 20-day rolling volatility (annualised)
      - 20-day rolling volume change %

    Components are relabelled so that 0 = bear, 1 = sideways, 2 = bull based
    on the mean daily return within each cluster (ascending order).

    Args:
        nifty_df: DataFrame with at least ``Close`` and ``Volume`` columns,
            indexed by date.
        n_components: Number of Gaussian components (default 3).

    Returns:
        Tuple of ``(GaussianMixture, StandardScaler)`` fitted on the training
        data.

    Raises:
        ValueError: If ``nifty_df`` does not contain required columns.
    """
    required = {"Close", "Volume"}
    if isinstance(nifty_df.columns, pd.MultiIndex):
        nifty_df.columns = nifty_df.columns.get_level_values(0)
    missing = required - set(nifty_df.columns)
    if missing:
        raise ValueError(f"nifty_df is missing columns: {missing}")

    close = nifty_df["Close"].squeeze()
    volume = nifty_df["Volume"].squeeze()

    roll_ret = close.pct_change(periods=20)
    roll_vol = np.log(close / close.shift(1)).rolling(20).std() * np.sqrt(252)
    vol_chg = volume.pct_change(periods=20)

    features = pd.DataFrame(
        {"roll_ret": roll_ret, "roll_vol": roll_vol, "vol_chg": vol_chg},
    )
    features.replace([np.inf, -np.inf], np.nan, inplace=True)
    features.dropna(inplace=True)

    scaler = StandardScaler()
    X = scaler.fit_transform(features.values)

    gmm = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        n_init=10,
        random_state=42,
        max_iter=300,
    )
    gmm.fit(X)

    # Relabel by mean return: bear=0, sideways=1, bull=2
    labels_raw = gmm.predict(X)

    # Safer approach: use features index
    regime_returns = pd.Series(labels_raw, index=features.index)
    mean_returns = {}
    for lbl in range(n_components):
        mask = regime_returns == lbl
        mean_returns[lbl] = float(features.loc[mask, "roll_ret"].mean()) if mask.any() else 0.0

    sorted_labels = sorted(mean_returns, key=lambda k: mean_returns[k])
    label_map = {old: new for new, old in enumerate(sorted_labels)}

    # Store the label map on the GMM object for later use
    gmm._label_map = label_map  # type: ignore[attr-defined]

    logger.info(
        "GMM trained: BIC=%.2f, AIC=%.2f, label_map=%s",
        gmm.bic(X), gmm.aic(X), label_map,
    )
    return gmm, scaler


# ──────────────────────────────────────────────────────────────────────────────
# Prediction
# ──────────────────────────────────────────────────────────────────────────────
def predict_regime(
    gmm: GaussianMixture,
    scaler: StandardScaler,
    features_df: pd.DataFrame,
) -> pd.Series:
    """Predict market regime for a features DataFrame.

    Args:
        gmm: Fitted ``GaussianMixture`` (with ``._label_map`` attribute).
        scaler: Fitted ``StandardScaler`` matching the GMM training features.
        features_df: DataFrame with columns ``[roll_ret, roll_vol, vol_chg]``.

    Returns:
        Integer regime series: 0 = bear, 1 = sideways, 2 = bull.
    """
    features_clean = features_df[["roll_ret", "roll_vol", "vol_chg"]].copy()
    features_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
    features_clean.fillna(0, inplace=True)  # Safe fallback
    X = scaler.transform(features_clean.values)
    raw_labels = gmm.predict(X)

    label_map = getattr(gmm, "_label_map", {0: 0, 1: 1, 2: 2})
    mapped = pd.Series(
        [label_map.get(l, l) for l in raw_labels],
        index=features_df.index,
        name="regime",
    )
    return mapped


# ──────────────────────────────────────────────────────────────────────────────
# Validation & Smoothing
# ──────────────────────────────────────────────────────────────────────────────
def validate_stability(regime_series: pd.Series) -> dict[str, Any]:
    """Compute regime stability diagnostics.

    Args:
        regime_series: Integer regime labels indexed by date.

    Returns:
        Dictionary with keys:
            ``flip_rate``: Fraction of consecutive-day regime changes.
            ``longest_run``: Length of the longest unchanged regime streak.
            ``regime_counts``: Value-counts dictionary.
    """
    changes = (regime_series != regime_series.shift(1)).sum()
    flip_rate = changes / len(regime_series) if len(regime_series) > 0 else 0.0

    # Longest run
    groups = (regime_series != regime_series.shift(1)).cumsum()
    longest_run = int(groups.value_counts().max()) if len(groups) > 0 else 0

    regime_counts = regime_series.value_counts().to_dict()

    return {
        "flip_rate": float(flip_rate),
        "longest_run": longest_run,
        "regime_counts": regime_counts,
    }


def smooth_regimes(regime_series: pd.Series, window: int = 5) -> pd.Series:
    """Apply rolling-mode smoothing to reduce spurious regime flips.

    Args:
        regime_series: Raw integer regime labels.
        window: Rolling window for mode computation.

    Returns:
        Smoothed regime series.
    """
    def _rolling_mode(s: pd.Series) -> int:
        mode_result = sp_stats.mode(s, keepdims=True)
        return int(mode_result.mode[0])

    smoothed = regime_series.rolling(window=window, center=False, min_periods=1).apply(
        _rolling_mode, raw=False,
    ).astype(int)
    smoothed.name = "regime"
    return smoothed


# ──────────────────────────────────────────────────────────────────────────────
# HMM Cross-Check
# ──────────────────────────────────────────────────────────────────────────────
def add_hmm_crosscheck(
    regime_series: pd.Series,
    features_df: pd.DataFrame,
) -> pd.Series:
    """Train a Gaussian HMM as an independent cross-check on GMM regimes.

    Args:
        regime_series: GMM-derived regime labels (for comparison logging only).
        features_df: DataFrame with columns ``[roll_ret, roll_vol, vol_chg]``.

    Returns:
        HMM-derived regime labels (integer, 0/1/2) ordered by mean return.
    """
    X = features_df[["roll_ret", "roll_vol", "vol_chg"]].dropna().values

    if not HAS_HMM:
        logger.warning("hmmlearn not installed. Skipping HMM cross-check.")
        return regime_series

    hmm = GaussianHMM(
        n_components=3,
        covariance_type="full",
        n_iter=200,
        random_state=42,
    )
    hmm.fit(X)
    raw_labels = hmm.predict(X)

    # Relabel by mean return ascending: bear=0, sideways=1, bull=2
    mean_ret = {}
    for lbl in range(3):
        mask = raw_labels == lbl
        mean_ret[lbl] = float(X[mask, 0].mean()) if mask.any() else 0.0

    sorted_labels = sorted(mean_ret, key=lambda k: mean_ret[k])
    label_map = {old: new for new, old in enumerate(sorted_labels)}
    hmm_labels = pd.Series(
        [label_map[l] for l in raw_labels],
        index=features_df.dropna(subset=["roll_ret", "roll_vol", "vol_chg"]).index,
        name="regime_hmm",
    )

    # Agreement metric
    common_idx = regime_series.index.intersection(hmm_labels.index)
    if len(common_idx) > 0:
        agreement = (regime_series.loc[common_idx] == hmm_labels.loc[common_idx]).mean()
        logger.info("GMM–HMM regime agreement: %.2f%%", agreement * 100)
    else:
        logger.warning("No overlapping indices between GMM and HMM series")

    return hmm_labels


# ──────────────────────────────────────────────────────────────────────────────
# Persistence & MLflow
# ──────────────────────────────────────────────────────────────────────────────
def save_regime_artifacts(
    gmm: GaussianMixture,
    scaler: StandardScaler,
    models_dir: Path | str = "models",
) -> None:
    """Persist GMM, scaler, and label map to disk and log to MLflow.

    Args:
        gmm: Fitted GMM.
        scaler: Fitted scaler.
        models_dir: Target directory for saved artifacts.
    """
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    # Atomic write for GMM
    gmm_path = models_dir / "regime_gmm.pkl"
    tmp_gmm = gmm_path.with_suffix(".tmp")
    with open(tmp_gmm, "wb") as f:
        pickle.dump(gmm, f)
    tmp_gmm.replace(gmm_path)

    # Atomic write for scaler
    scaler_path = models_dir / "regime_scaler.pkl"
    tmp_scaler = scaler_path.with_suffix(".tmp")
    with open(tmp_scaler, "wb") as f:
        pickle.dump(scaler, f)
    tmp_scaler.replace(scaler_path)

    # Atomic write for label map
    label_map = getattr(gmm, "_label_map", {})
    map_path = models_dir / "regime_label_map.pkl"
    tmp_map = map_path.with_suffix(".tmp")
    with open(tmp_map, "wb") as f:
        pickle.dump(label_map, f)
    tmp_map.replace(map_path)

    logger.info("Regime artifacts saved to %s", models_dir)


def log_regime_to_mlflow(
    gmm: GaussianMixture,
    scaler: StandardScaler,
    stability: dict[str, Any],
    X_scaled: np.ndarray | None = None,
) -> None:
    """Log regime detector metrics and artifacts to MLflow.

    Args:
        gmm: Fitted GMM.
        scaler: Fitted scaler.
        stability: Output of :func:`validate_stability`.
        X_scaled: Scaled feature matrix for BIC/AIC (optional; recomputed if needed).
    """
    mlflow.set_experiment("nse-quant-pipeline")

    _nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name="regime_detector", nested=_nested):
        mlflow.log_param("n_components", gmm.n_components)
        mlflow.log_param("covariance_type", gmm.covariance_type)

        if X_scaled is not None:
            mlflow.log_metric("bic", gmm.bic(X_scaled))
            mlflow.log_metric("aic", gmm.aic(X_scaled))

        mlflow.log_metric("flip_rate", stability["flip_rate"])
        mlflow.log_metric("longest_run", stability["longest_run"])

        for regime, count in stability["regime_counts"].items():
            mlflow.log_metric(f"regime_{regime}_count", count)

        # Log pickle artifacts
        models_dir = Path("models")
        if (models_dir / "regime_gmm.pkl").exists():
            mlflow.log_artifact(str(models_dir / "regime_gmm.pkl"))
            mlflow.log_artifact(str(models_dir / "regime_scaler.pkl"))

    logger.info("Regime detector metrics logged to MLflow")


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import yfinance as yf

    logger.info("=== Regime Detector Smoke Test ===")

    nifty = yf.download("^NSEI", start="2018-01-01", end="2023-12-31", progress=False)

    gmm, scaler = train_gmm(nifty, n_components=3)
    logger.info("GMM fit complete")

    # Build features for prediction
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)
    close = nifty["Close"].squeeze()
    volume = nifty["Volume"].squeeze()

    regime_features = pd.DataFrame({
        "roll_ret": close.pct_change(20),
        "roll_vol": np.log(close / close.shift(1)).rolling(20).std() * np.sqrt(252),
        "vol_chg": volume.pct_change(20),
    }).dropna()

    regimes = predict_regime(gmm, scaler, regime_features)
    stability = validate_stability(regimes)
    logger.info("Stability: %s", stability)

    if stability["flip_rate"] > 0.05:
        logger.info("Flip rate > 5%%, applying smoothing")
        regimes = smooth_regimes(regimes)
        stability = validate_stability(regimes)
        logger.info("Post-smoothing stability: %s", stability)

    hmm_labels = add_hmm_crosscheck(regimes, regime_features)

    save_regime_artifacts(gmm, scaler, models_dir=Path(__file__).resolve().parent.parent / "models")

    logger.info("=== Smoke Test PASSED ===")
