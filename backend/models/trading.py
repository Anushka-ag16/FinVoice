"""
FinVoice — Trading Models (TradeOrder, PaperAccount).
Extends the portfolio module with trade execution tracking.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String,
    Text, func,
)
from sqlalchemy.orm import relationship

from database import Base


class TradingMode(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"                # Created, not yet sent
    PLACED = "placed"                  # Sent to broker
    FILLED = "filled"                  # Fully executed
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"            # User cancelled
    REJECTED = "rejected"              # Broker rejected
    FAILED = "failed"                  # System error


class TradeOrder(Base):
    """
    Tracks every trade order from creation to execution.
    Links optimizer output → broker execution → portfolio update.
    """
    __tablename__ = "trade_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Order details
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), default=OrderType.MARKET, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)           # Limit price (None for market)
    filled_price = Column(Float, nullable=True)     # Actual execution price
    total_value = Column(Float, nullable=True)      # quantity * filled_price

    # Execution context
    mode = Column(Enum(TradingMode), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    broker_order_id = Column(String(100), nullable=True)   # Angel One order ID
    symbol = Column(String(50), nullable=False)            # e.g. "RELIANCE"
    exchange = Column(String(10), default="NSE")

    # Costs
    slippage_pct = Column(Float, default=0.0)
    brokerage_fee = Column(Float, default=0.0)
    stt_charges = Column(Float, default=0.0)       # Securities Transaction Tax

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    placed_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    portfolio = relationship("Portfolio")
    asset = relationship("Asset")
    user = relationship("User")


class PaperAccount(Base):
    """
    Virtual trading account for paper trading.
    Each user gets a paper account with simulated cash.
    """
    __tablename__ = "paper_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    cash_balance = Column(Float, default=1000000.0, nullable=False)   # ₹10 lakh default
    initial_balance = Column(Float, default=1000000.0, nullable=False)
    total_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")


class TradingCircuitBreaker(Base):
    """
    Tracks daily trading limits and circuit breaker state per user.
    Reset daily at market open (9:15 AM IST).
    """
    __tablename__ = "trading_circuit_breakers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)                # Trading date
    trades_today = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0.0)                 # Realized P&L today
    is_halted = Column(Boolean, default=False)             # Circuit breaker tripped
    halt_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
