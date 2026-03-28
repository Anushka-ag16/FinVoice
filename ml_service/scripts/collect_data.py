#!/usr/bin/env python3
"""
Data Collection Script — Download Nifty 50 OHLCV + Macro Data.

Downloads all 50 Nifty stocks + Nifty 50 index + macro data via yfinance,
saves per-ticker parquet files to data/raw/, handles rate limiting with
exponential backoff, and prints a summary.

Usage:
    python scripts/collect_data.py
    python scripts/collect_data.py --start 2015-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.feature_engineering import NIFTY_50_TICKERS, load_macro_data

logger = logging.getLogger(__name__)

# Additional tickers beyond the Nifty 50 stocks
INDEX_TICKERS = ["^NSEI"]  # Nifty 50 index


def download_with_backoff(
    ticker: str,
    start: str,
    end: str,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> pd.DataFrame | None:
    """Download OHLCV data with exponential backoff on failure.

    Args:
        ticker: Yahoo Finance ticker symbol.
        start: Start date.
        end: End date.
        max_retries: Maximum retry attempts.
        base_delay: Base delay in seconds (doubled each retry).

    Returns:
        DataFrame on success, ``None`` on failure.
    """
    for attempt in range(max_retries):
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty:
                logger.warning("[%s] Empty response (attempt %d/%d)", ticker, attempt + 1, max_retries)
                time.sleep(base_delay * (2 ** attempt))
                continue
            return df
        except Exception as exc:
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "[%s] Download failed (attempt %d/%d): %s — retrying in %.1fs",
                ticker, attempt + 1, max_retries, exc, delay,
            )
            time.sleep(delay)

    logger.error("[%s] All %d download attempts failed", ticker, max_retries)
    return None


def main() -> None:
    """Main data collection entry point."""
    parser = argparse.ArgumentParser(description="Download Nifty 50 OHLCV + Macro data")
    parser.add_argument("--start", default="2010-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2024-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "data" / "raw"),
                        help="Output directory for parquet files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_tickers = NIFTY_50_TICKERS + INDEX_TICKERS
    total = len(all_tickers)
    success_count = 0
    fail_count = 0
    total_rows = 0
    date_min = None
    date_max = None

    print(f"\n{'='*60}")
    print(f"  Data Collection: {total} tickers")
    print(f"  Date range: {args.start} → {args.end}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")

    for i, ticker in enumerate(all_tickers, 1):
        print(f"[{i:3d}/{total}] Downloading {ticker}...", end=" ", flush=True)

        df = download_with_backoff(ticker, args.start, args.end)

        if df is not None and not df.empty:
            # Save as parquet (atomic write)
            safe_name = ticker.replace("^", "IDX_").replace("=", "_EQ_")
            parquet_path = output_dir / f"{safe_name}.parquet"
            tmp_path = parquet_path.with_suffix(".tmp")
            df.to_parquet(tmp_path)
            tmp_path.replace(parquet_path)

            rows = len(df)
            total_rows += rows
            success_count += 1

            d_min = df.index.min()
            d_max = df.index.max()
            if date_min is None or d_min < date_min:
                date_min = d_min
            if date_max is None or d_max > date_max:
                date_max = d_max

            print(f"OK {rows} rows [{d_min.date()} -> {d_max.date()}]")
        else:
            fail_count += 1
            print("FAILED")

        # Rate limiting: small delay between downloads
        time.sleep(0.5)

    # Download macro data
    print(f"\n[MACRO] Downloading macro indicators...", end=" ", flush=True)
    try:
        macro_df = load_macro_data(start=args.start, end=args.end)
        macro_path = output_dir / "macro_data.parquet"
        tmp_path = macro_path.with_suffix(".tmp")
        macro_df.to_parquet(tmp_path)
        tmp_path.replace(macro_path)
        print(f"OK {len(macro_df)} rows, {len(macro_df.columns)} series")
    except Exception as exc:
        print(f"FAILED: {exc}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Downloaded:  {success_count}/{total} tickers")
    print(f"  Failed:      {fail_count}/{total} tickers")
    print(f"  Total rows:  {total_rows:,}")
    if date_min and date_max:
        print(f"  Date range:  {date_min.date()} → {date_max.date()}")
    print(f"  Output dir:  {output_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    main()
