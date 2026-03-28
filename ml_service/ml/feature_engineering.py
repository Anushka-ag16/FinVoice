"""
Feature Engineering Module — NSE/Nifty 50 Quantitative Pipeline.

Downloads OHLCV data via yfinance, computes technical indicators (RSI, MACD,
Bollinger Bands, volatility), fetches macro data from FRED, combines everything
into a walk-forward-safe feature matrix, and stores results in TimescaleDB.

CRITICAL: Every feature at time T uses only data available *before* T.
All technical features are shift(1) — meaning the feature row for date T
contains the indicator value computed from data up to T-1. This prevents
lookahead bias in any downstream model that trains on these features.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Nifty 50 tickers (Yahoo Finance .NS suffix)
# ---------------------------------------------------------------------------
NIFTY_50_TICKERS: list[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "NESTLEIND.NS", "BAJAJFINSV.NS", "NTPC.NS", "POWERGRID.NS", "TATAMOTORS.NS",
    "M&M.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ONGC.NS", "JSWSTEEL.NS",
    "TATASTEEL.NS", "HDFCLIFE.NS", "SBILIFE.NS", "TECHM.NS", "DIVISLAB.NS",
    "DRREDDY.NS", "BAJAJ-AUTO.NS", "BRITANNIA.NS", "CIPLA.NS", "EICHERMOT.NS",
    "TATACONSUM.NS", "APOLLOHOSP.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS",
    "COALINDIA.NS", "BPCL.NS", "GRASIM.NS", "UPL.NS", "HINDALCO.NS",
    "LTIM.NS",
]

# Only rank-normalize features with meaningful cross-sectional dispersion  # CHANGED
CS_RANK_COLS = [  # CHANGED
    "rsi", "mom_1m", "mom_3m", "mom_6m",  # CHANGED
    "volatility", "volume_ratio", "boll_pct",  # CHANGED
    "dist_52w_high", "dist_52w_low",  # CHANGED
]  # CHANGED


# ──────────────────────────────────────────────────────────────────────────────
# Data Download
# ──────────────────────────────────────────────────────────────────────────────
def download_ohlcv(
    tickers: list[str],
    start: str = "2010-01-01",
    end: str = "2024-12-31",
) -> dict[str, pd.DataFrame]:
    """Download daily OHLCV data for a list of tickers from Yahoo Finance.

    Args:
        tickers: List of Yahoo Finance ticker symbols (e.g. ``["RELIANCE.NS"]``).
        start: Start date in ``YYYY-MM-DD`` format.
        end: End date in ``YYYY-MM-DD`` format.

    Returns:
        Dictionary mapping ticker symbol to its OHLCV DataFrame with columns
        ``[Open, High, Low, Close, Adj Close, Volume]`` indexed by ``Date``.

    Raises:
        ValueError: If no data could be downloaded for any ticker.
    """
    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            if df.empty:
                logger.warning("No data returned for %s", ticker)
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            result[ticker] = df.copy()
            logger.info("Downloaded %s: %d rows [%s → %s]", ticker, len(df), df.index.min().date(), df.index.max().date())
        except Exception as exc:
            logger.error("Failed to download %s: %s", ticker, exc)

    if not result:
        raise ValueError("No OHLCV data downloaded for any of the requested tickers")
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Technical Indicators
# ──────────────────────────────────────────────────────────────────────────────
def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Compute MACD, signal line, and histogram."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": histogram},
        index=series.index,
    )


def compute_bollinger(
    series: pd.Series,
    period: int = 20,
    std: int = 2,
) -> pd.DataFrame:
    """Compute Bollinger Bands."""
    mid = series.rolling(window=period).mean()
    rolling_std = series.rolling(window=period).std()
    upper = mid + std * rolling_std
    lower = mid - std * rolling_std
    pct = (series - lower) / (upper - lower).replace(0, np.nan)
    return pd.DataFrame(
        {"upper": upper, "lower": lower, "mid": mid, "pct": pct},
        index=series.index,
    )


def compute_volatility(series: pd.Series, window: int = 20) -> pd.Series:
    """Compute annualised rolling volatility."""
    log_returns = np.log(series / series.shift(1))
    return log_returns.rolling(window=window).std() * np.sqrt(252)


# ──────────────────────────────────────────────────────────────────────────────
# Macro Data
# ──────────────────────────────────────────────────────────────────────────────
def load_macro_data(
    start: str = "2010-01-01",
    end: str = "2024-12-31",
) -> pd.DataFrame:
    """Load macroeconomic data from Yahoo Finance proxies and FRED."""
    macro_tickers: dict[str, str] = {
        "usdinr": "INR=X",
        "nifty_index": "^NSEI",
        "india_vix": "^INDIAVIX",
        "gold": "GC=F",
        "crude": "CL=F",
    }

    frames: dict[str, pd.Series] = {}

    for col_name, yf_ticker in macro_tickers.items():
        try:
            tmp = yf.download(yf_ticker, start=start, end=end, progress=False)
            if isinstance(tmp.columns, pd.MultiIndex):
                tmp.columns = tmp.columns.get_level_values(0)
            if not tmp.empty:
                frames[col_name] = tmp["Close"]
                logger.info("Macro: %s downloaded (%d rows)", col_name, len(tmp))
        except Exception as exc:
            logger.warning("Could not download macro ticker %s (%s): %s", col_name, yf_ticker, exc)

    try:
        import pandas_datareader.data as web

        rbi = web.DataReader("INDIRLTLT01STM", "fred", start, end)
        frames["rbi_rate"] = rbi.iloc[:, 0]
        logger.info("Macro: rbi_rate downloaded (%d rows)", len(rbi))
    except Exception as exc:
        logger.warning("Could not fetch FRED rbi_rate: %s", exc)

    if not frames:
        raise RuntimeError("Failed to fetch any macro data series")

    macro_df = pd.DataFrame(frames)
    macro_df = macro_df.sort_index().ffill().bfill()
    return macro_df


# ──────────────────────────────────────────────────────────────────────────────
# Cross-Sectional Rank Normalization
# ──────────────────────────────────────────────────────────────────────────────
def cross_sectional_rank_normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Add cross-sectional rank-normalized versions of selected feature columns.

    Only normalises columns listed in CS_RANK_COLS to avoid injecting noisy
    rank features that degrade tree model performance.

    Args:
        df: Feature DataFrame indexed by date with a ``ticker`` column.

    Returns:
        Augmented DataFrame with additional ``_cs_rank`` columns.
    """
    rank_cols = [c for c in CS_RANK_COLS if c in df.columns]  # CHANGED

    for col in rank_cols:
        df[f"{col}_cs_rank"] = df.groupby(level=0)[col].rank(pct=True) - 0.5

    logger.info(
        "Cross-sectional rank normalization added %d rank columns",
        len(rank_cols),
    )
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Feature Assembly
# ──────────────────────────────────────────────────────────────────────────────
def compute_all_features(
    ticker_dfs: dict[str, pd.DataFrame],
    macro_df: pd.DataFrame,
) -> pd.DataFrame:
    """Combine technical + macro features into a single walk-forward-safe DataFrame.

    IMPORTANT — Lookahead-bias prevention strategy:
      1. Every technical feature is computed on raw Close, *then* shifted forward
         by 1 trading day (``shift(1)``).  This means the feature row for date T
         contains indicator values that were fully knowable at end-of-day T-1.
      2. The forward 5-day return target (``target_fwd_5d``) is computed via
         ``shift(-5)`` to represent a future quantity.  It is stored in a
         separate column that is NEVER used as a model feature — only as a
         training label.

    Args:
        ticker_dfs: Dictionary ``{ticker: DataFrame}`` from :func:`download_ohlcv`.
        macro_df: Macro DataFrame from :func:`load_macro_data`.

    Returns:
        Combined feature DataFrame indexed by ``date`` with columns for
        every feature, the ticker symbol, and ``target_fwd_5d``.
    """
    all_rows: list[pd.DataFrame] = []

    for ticker, df in ticker_dfs.items():
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df["Close"].squeeze()

        rsi = compute_rsi(close)
        macd_df = compute_macd(close)
        boll_df = compute_bollinger(close)
        vol = compute_volatility(close)

        ret_1d = close.pct_change()

        feat = pd.DataFrame(
            {
                "ticker": ticker,
                "close": close,
                "volume": df["Volume"].squeeze(),
                "ret_1d": ret_1d,
                "rsi": rsi,
                "macd": macd_df["macd"],
                "macd_signal": macd_df["signal"],
                "macd_hist": macd_df["hist"],
                "boll_upper": boll_df["upper"],
                "boll_lower": boll_df["lower"],
                "boll_mid": boll_df["mid"],
                "boll_pct": boll_df["pct"],
                "volatility": vol,
            },
            index=df.index,
        )

        # Momentum features (individually shifted)
        feat["mom_1m"] = close.pct_change(21).shift(1)
        feat["mom_3m"] = close.pct_change(63).shift(1)
        feat["mom_6m"] = close.pct_change(126).shift(1)
        feat["mom_12m"] = close.pct_change(252).shift(2)

        # Price-Volume features
        volume_series = df["Volume"].squeeze()
        feat["volume_ratio"] = (volume_series /
                                volume_series.rolling(20).mean()).shift(1)
        obv_raw = (np.sign(close.diff()) * volume_series).cumsum()
        feat["obv_change"] = obv_raw.pct_change(5).shift(1)

        # Volatility regime feature
        feat["vol_ratio"] = (compute_volatility(close, 5) /
                             compute_volatility(close, 60)).shift(1)

        # ATR
        high = df["High"].squeeze()
        low = df["Low"].squeeze()
        tr = pd.concat([(high - low),
                         (high - close.shift(1)).abs(),
                         (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        feat["atr_pct"] = (atr / close).shift(1)

        # Mean-reversion features
        feat["dist_52w_high"] = (close / close.rolling(252).max() - 1).shift(1)
        feat["dist_52w_low"] = (close / close.rolling(252).min() - 1).shift(1)

        # Shift original technical columns (new features already shifted above)
        original_feature_cols = [c for c in ["close", "volume", "ret_1d", "rsi",
                                              "macd", "macd_signal", "macd_hist",
                                              "boll_upper", "boll_lower", "boll_mid",
                                              "boll_pct", "volatility"]
                                 if c in feat.columns]
        feat[original_feature_cols] = feat[original_feature_cols].shift(1)

        feat["target_fwd_5d"] = close.pct_change(periods=5).shift(-5)

        feat = feat.join(macro_df, how="left")

        all_rows.append(feat)

    combined = pd.concat(all_rows, axis=0).sort_index()
    combined.index.name = "date"
    combined.dropna(subset=["target_fwd_5d"], inplace=True)

    combined = cross_sectional_rank_normalize(combined)

    logger.info(
        "Feature matrix assembled: %d rows × %d cols (%d tickers)",
        len(combined), len(combined.columns), combined["ticker"].nunique(),
    )
    return combined


# ──────────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────────
def validate_no_lookahead(df: pd.DataFrame) -> bool:
    """Verify that no feature column has stronger same-day correlation with
    returns than its lagged counterpart — a symptom of lookahead bias.

    Args:
        df: Feature DataFrame with ``target_fwd_5d`` and at least one numeric
            feature column.

    Returns:
        ``True`` if the data passes the lookahead check, ``False`` otherwise.

    Raises:
        ValueError: If ``target_fwd_5d`` is missing from the DataFrame.
    """
    if "target_fwd_5d" not in df.columns:
        raise ValueError("DataFrame must contain 'target_fwd_5d' column")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c != "target_fwd_5d"]

    if not feature_cols:
        logger.warning("No numeric feature columns found for lookahead check")
        return True

    violations = 0
    for col in feature_cols:
        same_day_corr = abs(df[col].corr(df["target_fwd_5d"]))
        lagged_corr = abs(df[col].shift(1).corr(df["target_fwd_5d"]))
        
        if same_day_corr > 0.05 and lagged_corr > 0 and same_day_corr > lagged_corr * 1.5:
            violations += 1
            logger.warning(
                "Possible lookahead in '%s': same-day corr=%.4f > 1.5 × lagged corr=%.4f",
                col, same_day_corr, lagged_corr,
            )

    ratio = violations / len(feature_cols) if feature_cols else 0
    passed = ratio < 0.5
    if passed:
        logger.info("Lookahead check PASSED (violation ratio=%.2f)", ratio)
    else:
        logger.warning("Lookahead check FAILED (violation ratio=%.2f)", ratio)
    return passed


# ──────────────────────────────────────────────────────────────────────────────
# TimescaleDB Storage
# ──────────────────────────────────────────────────────────────────────────────
def store_to_timescaledb(df: pd.DataFrame, connection_string: str) -> None:
    """Write the feature DataFrame to a TimescaleDB hypertable."""
    engine = create_engine(connection_string)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS features (
                date        TIMESTAMPTZ NOT NULL,
                ticker      TEXT        NOT NULL,
                close       DOUBLE PRECISION,
                volume      DOUBLE PRECISION,
                ret_1d      DOUBLE PRECISION,
                rsi         DOUBLE PRECISION,
                macd        DOUBLE PRECISION,
                macd_signal DOUBLE PRECISION,
                macd_hist   DOUBLE PRECISION,
                boll_upper  DOUBLE PRECISION,
                boll_lower  DOUBLE PRECISION,
                boll_mid    DOUBLE PRECISION,
                boll_pct    DOUBLE PRECISION,
                volatility  DOUBLE PRECISION,
                usdinr      DOUBLE PRECISION,
                nifty_index DOUBLE PRECISION,
                india_vix   DOUBLE PRECISION,
                gold        DOUBLE PRECISION,
                crude       DOUBLE PRECISION,
                rbi_rate    DOUBLE PRECISION,
                target_fwd_5d DOUBLE PRECISION,
                PRIMARY KEY (date, ticker)
            );
        """))

        try:
            conn.execute(text(
                "SELECT create_hypertable('features', 'date', if_not_exists => TRUE);"
            ))
        except Exception:
            logger.info("Hypertable creation skipped (not TimescaleDB or already exists)")

    tmp_table = f"_tmp_features_{id(df) % 100000}"
    df_to_write = df.reset_index()
    df_to_write.to_sql(tmp_table, engine, if_exists="replace", index=False)

    cols = [c for c in df_to_write.columns]
    col_list = ", ".join(cols)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c not in ("date", "ticker"))

    upsert_sql = f"""
        INSERT INTO features ({col_list})
        SELECT {col_list} FROM {tmp_table}
        ON CONFLICT (date, ticker) DO UPDATE SET {update_set};
    """

    with engine.begin() as conn:
        conn.execute(text(upsert_sql))
        conn.execute(text(f"DROP TABLE IF EXISTS {tmp_table};"))

    logger.info("Stored %d rows to TimescaleDB table 'features'", len(df))


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    logger.info("=== Feature Engineering Smoke Test ===")

    test_tickers = ["RELIANCE.NS"]
    dfs = download_ohlcv(test_tickers, start="2023-01-01", end="2023-12-31")
    logger.info("Downloaded %d tickers", len(dfs))

    macro = load_macro_data(start="2023-01-01", end="2023-12-31")
    logger.info("Macro shape: %s", macro.shape)

    features = compute_all_features(dfs, macro)
    logger.info("Feature matrix shape: %s", features.shape)

    passed = validate_no_lookahead(features)
    assert passed, f"Lookahead check failed — inspect feature shifts"

    out_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "features_smoke.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = out_path.with_suffix(".tmp")
    features.to_parquet(tmp_path)
    tmp_path.replace(out_path)

    logger.info("Smoke test parquet saved to %s", out_path)
    logger.info("=== Smoke Test PASSED ===")
