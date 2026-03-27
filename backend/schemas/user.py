"""
FinVoice — Pydantic schemas for User & Risk Profile.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ─── User Schemas ───

class UserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    supabase_uid: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    tier: str
    is_active: bool
    onboarding_complete: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Risk Profile Schemas ───

class QuestionnaireStage1(BaseModel):
    """Universal questions."""
    age: int = Field(..., ge=18, le=100)
    income_range: str  # "0-3L", "3-7L", "7-15L", "15-30L", "30L+"
    investment_goal: str  # wealth_growth, retirement, education, emergency
    time_horizon_years: int = Field(..., ge=1, le=40)


class QuestionnaireStage2(BaseModel):
    """Behavioral assessment."""
    loss_reaction: str  # sell_everything, sell_partial, hold, buy_more
    market_check_frequency: str  # daily, weekly, monthly, rarely
    past_investment_experience: str  # none, <1yr, 1-3yr, 3-5yr, 5yr+


class QuestionnaireStage3Beginner(BaseModel):
    """Beginner-path questions."""
    savings_habit: str  # regular, irregular, none
    emergency_fund_months: int = Field(..., ge=0, le=24)
    loan_obligations: str  # none, low, moderate, high


class QuestionnaireStage3Experienced(BaseModel):
    """Experienced-path questions."""
    knows_derivatives: bool
    uses_leverage: bool
    sector_concentration_okay: bool
    max_acceptable_loss_pct: float = Field(..., ge=0, le=100)
    tax_bracket: str  # "0", "5", "20", "30"


class QuestionnaireSubmission(BaseModel):
    """Full questionnaire submission."""
    stage1: QuestionnaireStage1
    stage2: QuestionnaireStage2
    stage3_beginner: Optional[QuestionnaireStage3Beginner] = None
    stage3_experienced: Optional[QuestionnaireStage3Experienced] = None


class RiskProfileResponse(BaseModel):
    risk_score: float
    investor_type: str
    behavioral_bias: str
    investment_goal: Optional[str]
    time_horizon_years: Optional[int]
    max_acceptable_loss_pct: Optional[float]
    last_computed: datetime

    model_config = {"from_attributes": True}
