"""
FinVoice — Smart Investment Plan API
Capital-protected auto-trading: invest ₹1L, risk only ₹20K.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from api.auth import get_current_user, require_onboarding_complete
from services.capital_protection import CapitalProtectionEngine, CapitalProtectionError

router = APIRouter()


# ─── Schemas ───

class CreatePlanRequest(BaseModel):
    portfolio_id: int
    total_investment: float = Field(..., gt=0, description="Total amount to invest (e.g., 100000)")
    risk_amount: float = Field(..., gt=0, description="Amount willing to risk (e.g., 20000)")
    risk_floor_pct: float = Field(25.0, ge=5, le=90, description="Stop when risk capital drops below this % (default 25%)")
    profit_reinvest_pct: float = Field(70.0, ge=0, le=100, description="% of profits to reinvest into trading pool (default 70%)")
    max_single_trade_pct: float = Field(20.0, ge=5, le=50, description="Max % of risk pool per trade (default 20%)")
    target_profit: Optional[float] = Field(None, ge=0, description="Optional profit target to auto-complete")
    target_multiplier: Optional[float] = Field(None, ge=1.1, description="Optional target multiplier (e.g., 2.0 = double)")

    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": 1,
                "total_investment": 100000,
                "risk_amount": 20000,
                "risk_floor_pct": 25,
                "profit_reinvest_pct": 70,
                "max_single_trade_pct": 20,
                "target_multiplier": 3.0,
            }
        }


class AddCapitalRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to add to risk pool")


class TradeResultRequest(BaseModel):
    pnl: float = Field(..., description="Profit (positive) or loss (negative) from trade")
    trade_amount: float = Field(..., gt=0, description="How much was used for the trade")


# ─── Endpoints ───

@router.post("/create")
async def create_smart_plan(
    request: CreatePlanRequest,
    current_user: User = Depends(require_onboarding_complete),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a capital-protected investment plan.

    Example: Invest ₹1,00,000, risk only ₹20,000.
    The ₹80,000 is NEVER touched. Trades use only the ₹20,000 risk pool.
    As profits grow, they compound into the risk pool for bigger trades.
    """
    engine = CapitalProtectionEngine(db)

    try:
        plan = await engine.create_plan(
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            total_investment=request.total_investment,
            risk_amount=request.risk_amount,
            risk_floor_pct=request.risk_floor_pct,
            profit_reinvest_pct=request.profit_reinvest_pct,
            max_single_trade_pct=request.max_single_trade_pct,
            target_profit=request.target_profit,
            target_multiplier=request.target_multiplier,
        )
        await db.commit()

        summary = await engine.get_plan_summary(plan)
        return {
            "message": (
                f"Smart investment plan created! "
                f"₹{plan.protected_capital:,.0f} is protected and safe. "
                f"₹{plan.initial_risk_capital:,.0f} will be used for trading. "
                f"If your risk pool drops below ₹{plan.risk_floor:,.0f}, "
                f"trading stops automatically."
            ),
            **summary,
        }

    except CapitalProtectionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active")
async def get_active_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's active investment plan with full summary."""
    engine = CapitalProtectionEngine(db)
    plan = await engine.get_plan(current_user.id)

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="No active investment plan found. Create one first."
        )

    return await engine.get_plan_summary(plan)


@router.get("/{plan_id}")
async def get_plan_details(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific investment plan."""
    engine = CapitalProtectionEngine(db)
    plan = await engine.get_plan(current_user.id, plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return await engine.get_plan_summary(plan)


@router.post("/{plan_id}/validate-trade")
async def validate_trade(
    plan_id: int,
    trade_amount: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a trade is allowed under the capital protection rules.
    Call this BEFORE executing a trade.
    """
    engine = CapitalProtectionEngine(db)
    plan = await engine.get_plan(current_user.id, plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return await engine.validate_trade(plan, trade_amount)


@router.post("/{plan_id}/record-result")
async def record_trade_result(
    plan_id: int,
    request: TradeResultRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record the result of a trade (profit or loss).
    Updates the risk pool, protected capital, and profit tracking.
    """
    engine = CapitalProtectionEngine(db)
    plan = await engine.get_plan(current_user.id, plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = await engine.record_trade_result(plan, request.pnl, request.trade_amount)
    await db.commit()
    return result


@router.post("/{plan_id}/pause")
async def pause_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause trading on this plan. Your capital is preserved."""
    engine = CapitalProtectionEngine(db)
    plan = await engine.get_plan(current_user.id, plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = await engine.pause_plan(plan)
    await db.commit()
    return result


@router.post("/{plan_id}/resume")
async def resume_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused plan."""
    engine = CapitalProtectionEngine(db)
    plan = await engine.get_plan(current_user.id, plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = await engine.resume_plan(plan)
    await db.commit()
    return result


@router.post("/{plan_id}/add-capital")
async def add_risk_capital(
    plan_id: int,
    request: AddCapitalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add more money to the risk pool.
    Useful to resume trading after hitting the safety floor.
    """
    engine = CapitalProtectionEngine(db)
    plan = await engine.get_plan(current_user.id, plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = await engine.add_risk_capital(plan, request.amount)
    await db.commit()
    return result


@router.post("/simulate")
async def simulate_plan(
    total: float = 100000,
    risk: float = 20000,
    avg_trade_profit_pct: float = 2.0,
    avg_trade_loss_pct: float = -1.5,
    win_rate: float = 55.0,
    trades_per_month: int = 10,
    months: int = 12,
):
    """
    Simulate a capital protection plan over time.
    Shows how the risk pool and protected capital grow month by month.
    No login required — educational endpoint.
    """
    import random
    random.seed(42)

    protected = total - risk
    risk_pool = risk
    floor = risk * 0.25
    reinvest_pct = 70
    total_profit = 0
    timeline = []

    for month in range(1, months + 1):
        monthly_pnl = 0

        for _ in range(trades_per_month):
            if risk_pool <= floor:
                break

            trade_size = risk_pool * 0.15  # 15% per trade
            if random.random() * 100 < win_rate:
                pnl = trade_size * (avg_trade_profit_pct / 100)
            else:
                pnl = trade_size * (avg_trade_loss_pct / 100)

            monthly_pnl += pnl

            if pnl > 0:
                risk_pool += pnl * (reinvest_pct / 100)
                protected += pnl * ((100 - reinvest_pct) / 100)
            else:
                risk_pool += pnl  # Loss from risk only

            total_profit += max(pnl, 0)

        timeline.append({
            "month": month,
            "risk_pool": round(risk_pool, 2),
            "protected": round(protected, 2),
            "total_value": round(risk_pool + protected, 2),
            "monthly_pnl": round(monthly_pnl, 2),
            "total_profit": round(total_profit, 2),
            "halted": risk_pool <= floor,
        })

        if risk_pool <= floor:
            break

    final_value = risk_pool + protected
    return {
        "input": {
            "total_investment": total,
            "risk_amount": risk,
            "protected_amount": total - risk,
            "win_rate": win_rate,
            "avg_profit_per_trade": f"{avg_trade_profit_pct}%",
            "avg_loss_per_trade": f"{avg_trade_loss_pct}%",
            "trades_per_month": trades_per_month,
        },
        "result": {
            "final_value": round(final_value, 2),
            "total_return": f"{(final_value - total) / total * 100:+.1f}%",
            "protected_capital": round(protected, 2),
            "risk_pool_final": round(risk_pool, 2),
            "total_profit": round(total_profit, 2),
            "months_traded": len(timeline),
        },
        "timeline": timeline,
        "explanation": (
            f"Starting with ₹{total:,.0f} total (₹{risk:,.0f} at risk), "
            f"after {len(timeline)} months your portfolio would be worth "
            f"₹{final_value:,.0f} ({(final_value - total) / total * 100:+.1f}%). "
            f"Your original ₹{total - risk:,.0f} was never touched."
        ),
    }
