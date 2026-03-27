"""
FinVoice — Stress Testing API (Monte Carlo + Historical Replay).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, Portfolio, UserTier
from schemas.risk import (
    MonteCarloRequest, HistoricalScenarioRequest, StressTestResponse,
)
from services.crash_simulator import CrashSimulatorService
from api.auth import get_current_user

router = APIRouter()

SEBI_DISCLAIMER = (
    "FinVoice is a decision-support tool. Invest at your own risk. "
    "Consult a SEBI-registered advisor for personalized advice."
)


@router.post("/monte-carlo")
async def monte_carlo_simulation(
    request: MonteCarloRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Monte Carlo simulation: 10,000 portfolio paths.
    Paid tier only.
    """
    if current_user.tier != UserTier.PAID:
        raise HTTPException(
            status_code=403,
            detail="Crash simulation is available for paid tier users only. Upgrade to access this feature."
        )

    result = await db.execute(
        select(Portfolio).where(Portfolio.id == request.portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    simulator = CrashSimulatorService(db)
    mc_result = await simulator.monte_carlo(portfolio, request)

    return {
        "simulation": mc_result,
        "disclaimer": SEBI_DISCLAIMER,
    }


@router.post("/historical")
async def historical_scenario(
    request: HistoricalScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Historical scenario replay: Apply 2008/2020/2022 crash returns to user's portfolio.
    Paid tier only.
    """
    if current_user.tier != UserTier.PAID:
        raise HTTPException(
            status_code=403,
            detail="Historical scenario replay is available for paid tier users only."
        )

    result = await db.execute(
        select(Portfolio).where(Portfolio.id == request.portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    simulator = CrashSimulatorService(db)
    scenario_result = await simulator.historical_replay(portfolio, request)

    return {
        "scenario": scenario_result,
        "disclaimer": SEBI_DISCLAIMER,
    }
