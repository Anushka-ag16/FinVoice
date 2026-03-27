"""
FinVoice — Portfolio & Holdings models.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey, Integer, String, func,
)
from sqlalchemy.orm import relationship

from database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), default="My Portfolio", nullable=False)
    total_invested = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    target_allocations = relationship("TargetAllocation", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio")
    drift_alerts = relationship("DriftAlert", back_populates="portfolio")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_date = Column(DateTime, nullable=True)
    current_price = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    asset = relationship("Asset")


class TargetAllocation(Base):
    __tablename__ = "target_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_class = Column(String(50), nullable=False)  # equity, bond, gold, cash, etc.
    target_pct = Column(Float, nullable=False)  # Target allocation percentage
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", back_populates="target_allocations")


class TransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    executed_at = Column(DateTime, server_default=func.now())
    is_paper = Column(Integer, default=0)  # 0 = real, 1 = paper trade

    portfolio = relationship("Portfolio", back_populates="transactions")
    asset = relationship("Asset")


class DriftSeverity(str, enum.Enum):
    INFO = "info"       # 1-3% drift
    WARN = "warn"       # 3-5% drift
    ALERT = "alert"     # >5% drift


class DriftAlert(Base):
    __tablename__ = "drift_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_class = Column(String(50), nullable=False)
    actual_pct = Column(Float, nullable=False)
    target_pct = Column(Float, nullable=False)
    drift_pct = Column(Float, nullable=False)
    severity = Column(Enum(DriftSeverity), nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="drift_alerts")
