"""
FinVoice — Recommendations API.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_db
from models import User, Recommendation, Explanation, UserTier
from schemas.recommendation import RecommendationResponse, ExplanationResponse
from api.auth import get_current_user

router = APIRouter()


@router.get("/latest", response_model=list[RecommendationResponse])
async def get_latest_recommendations(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get latest recommendations for the user."""
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.user_id == current_user.id)
        .order_by(desc(Recommendation.created_at))
        .limit(limit)
    )
    recommendations = result.scalars().all()
    return recommendations


@router.get("/{recommendation_id}/explain", response_model=ExplanationResponse)
async def get_explanation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get XAI explanation for a recommendation.
    Free: short explanation. Paid: full factor attribution.
    """
    result = await db.execute(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.user_id == current_user.id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    result = await db.execute(
        select(Explanation).where(Explanation.recommendation_id == recommendation_id)
    )
    explanation = result.scalar_one_or_none()
    if not explanation:
        raise HTTPException(status_code=404, detail="Explanation not available")

    response = ExplanationResponse(
        short_explanation=explanation.short_explanation,
        medium_explanation=explanation.medium_explanation if current_user.tier == UserTier.PAID else None,
        full_explanation=explanation.full_explanation if current_user.tier == UserTier.PAID else None,
        top_features=explanation.top_features,
        market_regime=explanation.market_regime,
        regime_impact_note=explanation.regime_impact_note,
        factor_attribution={
            "market_beta": explanation.market_beta_contribution,
            "sector_tilt": explanation.sector_tilt_contribution,
            "stock_alpha": explanation.stock_alpha_contribution,
            "unexplained": explanation.unexplained_noise,
        } if current_user.tier == UserTier.PAID else None,
    )
    return response
