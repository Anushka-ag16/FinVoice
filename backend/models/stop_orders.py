"""
FinVoice — Stop Loss & Take Profit Models
Defines conditional orders that trigger automatically when price conditions are met.

Order Types:
    1. Stop Loss        — Sell when price drops below a fixed level
    2. Take Profit      — Sell when price rises above a target
    3. Trailing Stop    — Dynamic stop that follows price upward
    4. OCO (One-Cancels-Other) — SL + TP together; whichever triggers first cancels the other
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import relationship

from database import Base


class StopOrderType(str, enum.Enum):
    STOP_LOSS = "stop_loss"                     # Fixed price floor
    TAKE_PROFIT = "take_profit"                 # Fixed price ceiling
    TRAILING_STOP = "trailing_stop"             # Moves up with price
    OCO = "oco"                                 # SL + TP combined


class StopOrderStatus(str, enum.Enum):
    ACTIVE = "active"                           # Monitoring price
    TRIGGERED = "triggered"                     # Condition met, selling
    EXECUTED = "executed"                        # Sell order filled
    CANCELLED = "cancelled"                     # User cancelled
    EXPIRED = "expired"                         # Past expiry date
    FAILED = "failed"                           # Execution failed


class StopOrder(Base):
    """
    A conditional order that monitors price and triggers automatically.

    Examples:
        Stop Loss:     Bought RELIANCE at ₹2,580. Set SL at ₹2,450.
                       If price drops to ₹2,450 → auto sell to limit loss.

        Take Profit:   Bought RELIANCE at ₹2,580. Set TP at ₹2,800.
                       If price rises to ₹2,800 → auto sell to lock profit.

        Trailing Stop: Bought at ₹2,580, trail by 3%.
                       Price goes to ₹2,700 → stop moves to ₹2,619 (2700 × 0.97).
                       Price goes to ₹2,800 → stop moves to ₹2,716 (2800 × 0.97).
                       Price drops to ₹2,716 → triggered! Sells at market.

        OCO:           SL at ₹2,450, TP at ₹2,800.
                       Whichever hits first → sell. Other gets cancelled.
    """
    __tablename__ = "stop_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    trade_order_id = Column(Integer, ForeignKey("trade_orders.id"), nullable=True)  # Original buy

    # What to protect
    symbol = Column(String(50), nullable=False)
    quantity = Column(Float, nullable=False)             # How many shares to sell
    entry_price = Column(Float, nullable=False)          # Price at which user bought

    # Order type
    order_type = Column(Enum(StopOrderType), nullable=False)

    # ── Stop Loss fields ──
    stop_price = Column(Float, nullable=True)            # Trigger price (sell when price <= this)
    stop_pct = Column(Float, nullable=True)              # Stop as % below entry (e.g., 5.0 = 5%)

    # ── Take Profit fields ──
    target_price = Column(Float, nullable=True)          # Take profit price (sell when price >= this)
    target_pct = Column(Float, nullable=True)            # Target as % above entry (e.g., 10.0 = 10%)

    # ── Trailing Stop fields ──
    trail_pct = Column(Float, nullable=True)             # Trail percentage (e.g., 3.0 = 3%)
    trail_amount = Column(Float, nullable=True)          # Trail fixed amount (e.g., ₹50)
    highest_price = Column(Float, nullable=True)         # Highest price seen (for trailing calc)
    current_stop = Column(Float, nullable=True)          # Current trailing stop level

    # Execution
    status = Column(Enum(StopOrderStatus), default=StopOrderStatus.ACTIVE, nullable=False)
    triggered_price = Column(Float, nullable=True)       # Actual price when triggered
    filled_price = Column(Float, nullable=True)          # Actual sell execution price
    pnl = Column(Float, nullable=True)                   # Realized P&L from this exit

    # Linked OCO
    linked_order_id = Column(Integer, ForeignKey("stop_orders.id"), nullable=True)

    # Trading mode
    mode = Column(String(10), default="paper")           # "paper" or "live"

    # Timing
    created_at = Column(DateTime, server_default=func.now())
    triggered_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)         # Optional expiry (GTC = no expiry)

    # Reason
    trigger_reason = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")
    portfolio = relationship("Portfolio")
