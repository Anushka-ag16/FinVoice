"""
FinVoice — Pydantic schemas for Recommendations & Explanations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    id: int
    recommendation_type: str
    title: str
    summary: str
    detailed_explanation: Optional[str] = None
    suggested_actions: Optional[list[dict]] = None
    confidence_score: Optional[float] = None
    disclaimer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExplanationResponse(BaseModel):
    short_explanation: Optional[str]
    medium_explanation: Optional[str]
    full_explanation: Optional[str]
    top_features: Optional[list[dict]]
    market_regime: Optional[str]
    regime_impact_note: Optional[str]
    factor_attribution: Optional[dict] = None

    model_config = {"from_attributes": True}
