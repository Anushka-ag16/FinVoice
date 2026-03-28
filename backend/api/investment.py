"""
FinVoice — Investment API (New Money Advisor + Portfolio Optimizer).
Protected: Requires onboarding. RL optimizer requires paid tier.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, Portfolio, UserTier
from schemas.risk import NewInvestmentRequest, NewInvestmentResponse
from services.new_money_advisor import NewMoneyAdvisorService
from services.portfolio_optimizer import PortfolioOptimizerService
from api.auth import get_current_user, require_onboarding_complete

router = APIRouter()

SEBI_DISCLAIMER = (
    "FinVoice is a decision-support tool. Invest at your own risk. "
    "Consult a SEBI-registered advisor for personalized advice."
)


@router.post("/allocate", response_model=NewInvestmentResponse)
async def new_investment(
    request: NewInvestmentRequest,
    current_user: User = Depends(require_onboarding_complete),
    db: AsyncSession = Depends(get_db),
):
    """
    New Money Advisor: 'I want to invest ₹X'.
    Returns 3 scenarios: Conservative / Balanced / Aggressive.
    Requires portfolio import (onboarding) first.
    """
    advisor = NewMoneyAdvisorService(db, current_user)
    result = await advisor.generate_scenarios(request)
    result.disclaimer = SEBI_DISCLAIMER
    return result


@router.post("/optimize")
async def optimize_portfolio(
    portfolio_id: int,
    current_user: User = Depends(require_onboarding_complete),
    db: AsyncSession = Depends(get_db),
):
    """
    Portfolio optimization.
    Free tier: MPT + Black-Litterman (static).
    Paid tier: RL Agent (PPO/SAC) — dynamic, adaptive.
    Requires portfolio import first.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    optimizer = PortfolioOptimizerService(db, current_user)
    optimization_result = await optimizer.optimize(portfolio)

    return {
        "portfolio_id": portfolio_id,
        "method": "rl_ppo" if current_user.tier == UserTier.PAID else "mpt_black_litterman",
        "current_allocation": optimization_result["current"],
        "target_allocation": optimization_result["target"],
        "rebalancing_trades": optimization_result["trades"],
        "expected_sharpe": optimization_result.get("sharpe"),
        "expected_return": optimization_result.get("expected_return"),
        "expected_risk": optimization_result.get("expected_risk"),
        "explanation": optimization_result.get("explanation"),
        "disclaimer": SEBI_DISCLAIMER,
    }
