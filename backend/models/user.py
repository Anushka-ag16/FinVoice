"""
FinVoice — User & Risk Profile models.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, JSON,
    String, Text, func,
)
from sqlalchemy.orm import relationship

from database import Base


class UserTier(str, enum.Enum):
    FREE = "free"
    PAID = "paid"


class InvestorType(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERIENCED = "experienced"


class BehavioralBiasType(str, enum.Enum):
    LOSS_AVERSE = "loss_averse"
    OVERCONFIDENT = "overconfident"
    BALANCED = "balanced"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    supabase_uid = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    tier = Column(Enum(UserTier), default=UserTier.FREE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    onboarding_complete = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    risk_profile = relationship("RiskProfile", back_populates="user", uselist=False)
    portfolios = relationship("Portfolio", back_populates="user")
    behavioral_signals = relationship("BehavioralSignal", back_populates="user")


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Risk Assessment
    risk_score = Column(Float, nullable=False)  # 0-100
    investor_type = Column(Enum(InvestorType), nullable=False)
    behavioral_bias = Column(Enum(BehavioralBiasType), default=BehavioralBiasType.BALANCED)

    # Questionnaire Data
    questionnaire_responses = Column(JSON, nullable=True)
    age = Column(Integer, nullable=True)
    income_range = Column(String(50), nullable=True)
    investment_goal = Column(String(100), nullable=True)
    time_horizon_years = Column(Integer, nullable=True)
    max_acceptable_loss_pct = Column(Float, nullable=True)
    tax_bracket = Column(String(20), nullable=True)

    # Dynamic Scoring
    last_computed = Column(DateTime, server_default=func.now())
    next_refresh_due = Column(DateTime, nullable=True)
    behavioral_adjustment = Column(Float, default=0.0)  # Added/subtracted from base score

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="risk_profile")


class BehavioralSignal(Base):
    __tablename__ = "behavioral_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    signal_type = Column(String(50), nullable=False)  # panic_sell, frequent_check, etc.
    metadata_ = Column("metadata", JSON, nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="behavioral_signals")
