"""
FinVoice — Onboarding API (Adaptive Questionnaire + Mandatory Portfolio Import).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas.user import QuestionnaireSubmission, RiskProfileResponse
from services.risk_profiler import RiskProfilerService
from api.auth import get_current_user

router = APIRouter()


@router.post("/questionnaire", response_model=RiskProfileResponse)
async def submit_questionnaire(
    submission: QuestionnaireSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit adaptive questionnaire responses.
    Computes risk score (0-100), investor type, and behavioral bias.
    """
    profiler = RiskProfilerService(db)
    risk_profile = await profiler.compute_risk_profile(current_user, submission)
    return risk_profile


@router.get("/risk-profile", response_model=RiskProfileResponse)
async def get_risk_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's risk profile."""
    profiler = RiskProfilerService(db)
    profile = await profiler.get_profile(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Risk profile not found. Complete the questionnaire first.")
    return profile


@router.post("/refresh-risk", response_model=RiskProfileResponse)
async def refresh_risk_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger risk profile re-evaluation (90-day cycle or behavioral update)."""
    profiler = RiskProfilerService(db)
    profile = await profiler.refresh_profile(current_user)
    return profile
