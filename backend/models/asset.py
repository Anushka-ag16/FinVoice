"""
FinVoice — Asset, Price & Feature models.
Prices use TimescaleDB hypertable for efficient time-series queries.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Date, DateTime, Enum, Float, ForeignKey, Integer,
    String, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from database import Base


class AssetClass(str, enum.Enum):
    EQUITY = "equity"
    MUTUAL_FUND = "mutual_fund"
    ETF = "etf"
    BOND = "bond"
    GOLD = "gold"
    SILVER = "silver"
    REIT = "reit"
    FIXED_DEPOSIT = "fixed_deposit"
    CRYPTO = "crypto"
    CASH = "cash"


class MarketCapTier(str, enum.Enum):
    LARGE = "large"
    MID = "mid"
    SMALL = "small"
    MICRO = "micro"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    asset_class = Column(Enum(AssetClass), nullable=False)
    sector = Column(String(100), nullable=True)
    market_cap_tier = Column(Enum(MarketCapTier), nullable=True)
    exchange = Column(String(10), default="NSE")  # NSE, BSE, MCX
    isin = Column(String(20), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    prices = relationship("Price", back_populates="asset")
    features = relationship("Feature", back_populates="asset")


class Price(Base):
    """
    OHLCV price data — designed as TimescaleDB hypertable.
    After table creation, run:
        SELECT create_hypertable('prices', 'date');
    """
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_price_asset_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    adj_close = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    delivery_pct = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="prices")


class Feature(Base):
    """
    Pre-computed features per asset per day — stored in feature store table.
    """
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_feature_asset_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # Technical Indicators
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    bollinger_pct = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)
    obv = Column(Float, nullable=True)
    williams_r = Column(Float, nullable=True)
    stochastic_k = Column(Float, nullable=True)
    stochastic_d = Column(Float, nullable=True)
    adx = Column(Float, nullable=True)

    # Returns
    return_1d = Column(Float, nullable=True)
    return_5d = Column(Float, nullable=True)
    return_21d = Column(Float, nullable=True)
    return_63d = Column(Float, nullable=True)
    volatility_21d = Column(Float, nullable=True)

    # Market / Cross-sectional
    beta_nifty50 = Column(Float, nullable=True)
    distance_52w_high = Column(Float, nullable=True)
    distance_52w_low = Column(Float, nullable=True)
    relative_strength_nifty = Column(Float, nullable=True)
    sector_momentum_rank = Column(Float, nullable=True)

    # Forward returns (labels for ML training)
    fwd_return_1d = Column(Float, nullable=True)
    fwd_return_5d = Column(Float, nullable=True)
    fwd_return_21d = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="features")
