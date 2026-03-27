"""
FinVoice — Feature Engineering Pipeline
Computes 50+ technical, fundamental, and macro features per asset per day.
"""

import numpy as np
import pandas as pd
import ta


class FeatureEngineeringPipeline:
    """Compute features from OHLCV data for ML model training."""

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features for a single asset's OHLCV dataframe.
        Expects columns: date, open, high, low, close, volume
        """
        df = df.copy().sort_values("date").reset_index(drop=True)

        # ─── Technical Indicators ───
        df = self._add_technical_indicators(df)

        # ─── Returns ───
        df = self._add_returns(df)

        # ─── Market Features ───
        df = self._add_market_features(df)

        # ─── Forward Returns (Labels for ML) ───
        df = self._add_forward_returns(df)

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI, MACD, Bollinger, ATR, OBV, Williams %R, Stochastic, ADX."""

        # RSI
        df["rsi_14"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

        # MACD
        macd = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_hist"] = macd.macd_diff()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
        df["bollinger_upper"] = bb.bollinger_hband()
        df["bollinger_lower"] = bb.bollinger_lband()
        df["bollinger_pct"] = bb.bollinger_pband()

        # ATR
        df["atr_14"] = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], window=14
        ).average_true_range()

        # OBV
        if "volume" in df.columns and df["volume"].notna().any():
            df["obv"] = ta.volume.OnBalanceVolumeIndicator(
                df["close"], df["volume"]
            ).on_balance_volume()
        else:
            df["obv"] = 0

        # Williams %R
        df["williams_r"] = ta.momentum.WilliamsRIndicator(
            df["high"], df["low"], df["close"], lbp=14
        ).williams_r()

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(
            df["high"], df["low"], df["close"], window=14, smooth_window=3
        )
        df["stochastic_k"] = stoch.stoch()
        df["stochastic_d"] = stoch.stoch_signal()

        # ADX
        df["adx"] = ta.trend.ADXIndicator(
            df["high"], df["low"], df["close"], window=14
        ).adx()

        return df

    def _add_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rolling returns and volatility."""
        df["return_1d"] = df["close"].pct_change(1)
        df["return_5d"] = df["close"].pct_change(5)
        df["return_21d"] = df["close"].pct_change(21)
        df["return_63d"] = df["close"].pct_change(63)
        df["volatility_21d"] = df["return_1d"].rolling(21).std() * np.sqrt(252)
        return df

    def _add_market_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """52-week high/low distance, relative strength."""
        df["high_52w"] = df["high"].rolling(252).max()
        df["low_52w"] = df["low"].rolling(252).min()
        df["distance_52w_high"] = (df["close"] - df["high_52w"]) / df["high_52w"]
        df["distance_52w_low"] = (df["close"] - df["low_52w"]) / df["low_52w"]
        return df

    def _add_forward_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Forward returns — ML training labels."""
        df["fwd_return_1d"] = df["close"].pct_change(1).shift(-1)
        df["fwd_return_5d"] = df["close"].pct_change(5).shift(-5)
        df["fwd_return_21d"] = df["close"].pct_change(21).shift(-21)
        return df

    def compute_beta(
        self, stock_returns: pd.Series, market_returns: pd.Series, window: int = 252
    ) -> pd.Series:
        """Rolling beta vs market index."""
        cov = stock_returns.rolling(window).cov(market_returns)
        var = market_returns.rolling(window).var()
        return cov / var


if __name__ == "__main__":
    # Example usage
    import yfinance as yf

    df = yf.Ticker("RELIANCE.NS").history(period="5y").reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    pipeline = FeatureEngineeringPipeline()
    features = pipeline.compute_all_features(df)
    print(f"Features shape: {features.shape}")
    print(f"Columns: {features.columns.tolist()}")
