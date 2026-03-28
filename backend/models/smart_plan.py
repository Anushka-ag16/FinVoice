"""
FinVoice — Smart Investment Plan models.
Tracks capital protection plans where users split money into
protected capital (safe) and risk capital (for trading).
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import relationship

from database import Base


class PlanStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"           # User paused trading
    STOPPED = "stopped"         # Circuit breaker tripped
    COMPLETED = "completed"     # Target profit reached
    WITHDRAWN = "withdrawn"     # User withdrew funds


class SmartInvestmentPlan(Base):
    """
    A capital-protected investment plan.

    Example: User invests ₹1,00,000
      - Protected capital: ₹80,000 (never risked)
      - Risk capital:      ₹20,000 (used for active trading)
      - As profits grow, profits join the trading pool
      - If risk capital hits floor (e.g. ₹5,000), trading stops
    """
    __tablename__ = "smart_investment_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)

    # ─── Capital Split ───
    total_investment = Column(Float, nullable=False)         # ₹1,00,000
    protected_capital = Column(Float, nullable=False)        # ₹80,000 (untouched)
    initial_risk_capital = Column(Float, nullable=False)     # ₹20,000 (starting risk pool)
    current_risk_capital = Column(Float, nullable=False)     # Live risk pool (changes with trades)

    # ─── Profit Tracking ───
    total_profit = Column(Float, default=0.0)                # Cumulative realized profit
    profit_reinvested = Column(Float, default=0.0)           # How much profit was added to risk pool
    profit_withdrawn = Column(Float, default=0.0)            # How much profit the user took out

    # ─── Safety Controls ───
    risk_floor = Column(Float, nullable=False)               # Stop trading if risk capital drops below this
    risk_floor_pct = Column(Float, default=25.0)             # Floor as % of initial risk (default: 25% = ₹5,000)
    max_single_trade_pct = Column(Float, default=20.0)       # Max % of risk capital per trade
    profit_reinvest_pct = Column(Float, default=70.0)        # % of profits reinvested (rest goes to protected)

    # ─── Target ───
    target_profit = Column(Float, nullable=True)             # Optional target (e.g., ₹50,000 profit)
    target_multiplier = Column(Float, nullable=True)         # Optional (e.g., 2x = double the money)

    # ─── State ───
    status = Column(Enum(PlanStatus), default=PlanStatus.ACTIVE, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    halt_reason = Column(Text, nullable=True)

    # ─── Timestamps ───
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_trade_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    portfolio = relationship("Portfolio")
