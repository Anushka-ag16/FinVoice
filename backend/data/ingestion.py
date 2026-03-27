"""
FinVoice — Data Ingestion Service
Pulls market data from free sources: yfinance, MFAPI, BSE India, RBI.
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Top Nifty 50 stocks
NIFTY50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "TITAN.NS", "NESTLEIND.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "ULTRACEMCO.NS",
    "WIPRO.NS", "BAJAJFINSV.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS",
    "M&M.NS", "TATASTEEL.NS", "ADANIENT.NS", "COALINDIA.NS", "HCLTECH.NS",
    "DRREDDY.NS", "TECHM.NS", "INDUSINDBK.NS", "DIVISLAB.NS", "CIPLA.NS",
    "GRASIM.NS", "JSWSTEEL.NS", "BPCL.NS", "EICHERMOT.NS", "BRITANNIA.NS",
    "HEROMOTOCO.NS", "APOLLOHOSP.NS", "TATACONSUM.NS", "SBILIFE.NS", "BAJAJ-AUTO.NS",
    "HINDALCO.NS", "HDFCLIFE.NS", "UPL.NS", "ADANIPORTS.NS", "LTIM.NS",
]

# Index tracking
INDEX_SYMBOLS = ["^NSEI", "^BSESN"]  # Nifty 50, Sensex


class DataIngestionService:
    """Unified data ingestion from free APIs."""

    def __init__(self, start_date: str = None, end_date: str = None):
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        self.start_date = start_date or (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

    def fetch_equity_data(
        self, symbols: list[str] = None, save_parquet: bool = True
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for Indian equities via yfinance.
        Returns dict of {symbol: DataFrame}.
        """
        symbols = symbols or NIFTY50_SYMBOLS
        data = {}

        for symbol in symbols:
            try:
                logger.info(f"Fetching {symbol}...")
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=self.start_date, end=self.end_date)

                if df.empty:
                    logger.warning(f"No data for {symbol}")
                    continue

                df = df.reset_index()
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]

                # Validate data quality
                if not self._validate_ohlcv(df, symbol):
                    continue

                data[symbol] = df

                if save_parquet:
                    path = RAW_DATA_DIR / f"{symbol.replace('.', '_')}.parquet"
                    df.to_parquet(path, index=False)
                    logger.info(f"Saved {symbol} → {path}")

            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")

        return data

    def fetch_index_data(self) -> dict[str, pd.DataFrame]:
        """Fetch Nifty 50 and Sensex index data."""
        return self.fetch_equity_data(INDEX_SYMBOLS)

    def fetch_mutual_fund_data(self, scheme_codes: list[int] = None) -> dict[int, pd.DataFrame]:
        """
        Fetch mutual fund NAV data from MFAPI.in.
        Default: top 10 large cap funds.
        """
        import requests

        default_codes = [
            119551,  # PPFAS Flexi Cap
            120505,  # Axis Bluechip
            122639,  # Mirae Asset Large Cap
            120503,  # ICICI Prudential Bluechip
            119597,  # SBI Bluechip
            120465,  # Kotak Bluechip
            118989,  # HDFC Top 100
            120716,  # UTI Nifty 50 Index
            135781,  # Nippon India Index Fund
            120847,  # DSP Top 100
        ]
        codes = scheme_codes or default_codes
        data = {}

        for code in codes:
            try:
                url = f"https://api.mfapi.in/mf/{code}"
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                result = resp.json()

                nav_data = result.get("data", [])
                if not nav_data:
                    continue

                df = pd.DataFrame(nav_data)
                df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
                df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
                df = df.dropna().sort_values("date")

                data[code] = df

                path = RAW_DATA_DIR / f"mf_{code}.parquet"
                df.to_parquet(path, index=False)

            except Exception as e:
                logger.error(f"Error fetching MF {code}: {e}")

        return data

    def _validate_ohlcv(self, df: pd.DataFrame, symbol: str) -> bool:
        """Validate OHLCV data quality."""
        issues = []

        if df.empty:
            issues.append("Empty dataframe")

        if "close" in df.columns:
            if (df["close"] <= 0).any():
                issues.append("Negative or zero close prices")
            if df["close"].isna().sum() > len(df) * 0.05:
                issues.append(f"{df['close'].isna().sum()} missing close values")

        if "volume" in df.columns:
            if (df["volume"] < 0).any():
                issues.append("Negative volume")

        # Check for duplicate dates
        if "date" in df.columns and df["date"].duplicated().any():
            issues.append("Duplicate dates found")

        if issues:
            logger.warning(f"Data quality issues for {symbol}: {', '.join(issues)}")
            return len(issues) <= 1  # Allow 1 minor issue

        return True

    def run_full_ingestion(self) -> dict:
        """Run full data ingestion pipeline."""
        results = {
            "equities": 0,
            "indices": 0,
            "mutual_funds": 0,
            "errors": [],
        }

        try:
            equity_data = self.fetch_equity_data()
            results["equities"] = len(equity_data)
        except Exception as e:
            results["errors"].append(f"Equity ingestion failed: {e}")

        try:
            index_data = self.fetch_index_data()
            results["indices"] = len(index_data)
        except Exception as e:
            results["errors"].append(f"Index ingestion failed: {e}")

        try:
            mf_data = self.fetch_mutual_fund_data()
            results["mutual_funds"] = len(mf_data)
        except Exception as e:
            results["errors"].append(f"MF ingestion failed: {e}")

        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = DataIngestionService()

    print("Starting full data ingestion...")
    results = service.run_full_ingestion()
    print(f"Results: {results}")
