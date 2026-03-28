"""
FinVoice — Pydantic schemas for User & Risk Profile.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


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

class QuestionnaireSubmission(BaseModel):
    """
    Flat submission: { question_id: selected_option_index } for radio/slider,
    or { question_id: [indices] } for multi-select.
    """
    answers: dict[str, Any]


class RiskProfileResponse(BaseModel):
    risk_score: float
    investor_type: str
    behavioral_bias: str
    investment_goal: Optional[str] = None
    time_horizon_years: Optional[int] = None
    max_acceptable_loss_pct: Optional[float] = None
    recommended_allocation: Optional[dict[str, int]] = None
    last_computed: datetime

    model_config = {"from_attributes": True}
