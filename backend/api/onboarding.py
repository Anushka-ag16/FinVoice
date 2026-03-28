"""
FinVoice — Onboarding API (Adaptive Questionnaire + Risk Profile).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas.user import QuestionnaireSubmission, RiskProfileResponse
from services.risk_profiler import (
    RiskProfilerService,
    QUESTIONS,
    SECTION_LABELS,
    BRANCH_RULES,
    TIER_SEQUENCES,
    UNIVERSAL_SEQUENCE,
    detect_tier,
    simulate_path,
)
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
    Computes risk score (0-100), investor type, behavioral bias, and recommended allocation.
    """
    profiler = RiskProfilerService(db)
    risk_profile = await profiler.compute_risk_profile(current_user, submission.answers)

    # Get allocation for response
    allocation = await profiler.get_allocation(current_user.id)

    return RiskProfileResponse(
        risk_score=risk_profile.risk_score,
        investor_type=risk_profile.investor_type.value if hasattr(risk_profile.investor_type, 'value') else risk_profile.investor_type,
        behavioral_bias=risk_profile.behavioral_bias.value if hasattr(risk_profile.behavioral_bias, 'value') else risk_profile.behavioral_bias,
        investment_goal=risk_profile.investment_goal,
        time_horizon_years=risk_profile.time_horizon_years,
        max_acceptable_loss_pct=risk_profile.max_acceptable_loss_pct,
        recommended_allocation=allocation,
        last_computed=risk_profile.last_computed,
    )


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

    allocation = await profiler.get_allocation(current_user.id)

    return RiskProfileResponse(
        risk_score=profile.risk_score,
        investor_type=profile.investor_type.value if hasattr(profile.investor_type, 'value') else profile.investor_type,
        behavioral_bias=profile.behavioral_bias.value if hasattr(profile.behavioral_bias, 'value') else profile.behavioral_bias,
        investment_goal=profile.investment_goal,
        time_horizon_years=profile.time_horizon_years,
        max_acceptable_loss_pct=profile.max_acceptable_loss_pct,
        recommended_allocation=allocation,
        last_computed=profile.last_computed,
    )


@router.post("/refresh-risk", response_model=RiskProfileResponse)
async def refresh_risk_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger risk profile re-evaluation (90-day cycle or behavioral update)."""
    profiler = RiskProfilerService(db)
    profile = await profiler.refresh_profile(current_user)
    allocation = await profiler.get_allocation(current_user.id)

    return RiskProfileResponse(
        risk_score=profile.risk_score,
        investor_type=profile.investor_type.value if hasattr(profile.investor_type, 'value') else profile.investor_type,
        behavioral_bias=profile.behavioral_bias.value if hasattr(profile.behavioral_bias, 'value') else profile.behavioral_bias,
        investment_goal=profile.investment_goal,
        time_horizon_years=profile.time_horizon_years,
        max_acceptable_loss_pct=profile.max_acceptable_loss_pct,
        recommended_allocation=allocation,
        last_computed=profile.last_computed,
    )


@router.get("/questions")
async def get_questions():
    """
    Return the full question bank, section labels, and branch rules.
    Frontend uses this for initialisation; backend independently re-simulates the path on submit.
    """
    return {
        "questions": QUESTIONS,
        "sections": SECTION_LABELS,
        "branch_rules": BRANCH_RULES,
        "universal_sequence": UNIVERSAL_SEQUENCE,
        "tier_sequences": TIER_SEQUENCES,
    }
