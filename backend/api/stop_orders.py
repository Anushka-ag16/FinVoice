"""
FinVoice — Stop Loss & Take Profit API
Set automatic exit rules to protect your investments.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from api.auth import get_current_user
from services.stop_loss_engine import StopLossEngine, StopOrderError

router = APIRouter()


# ─── Schemas ───

class StopLossRequest(BaseModel):
    portfolio_id: int
    symbol: str
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0, description="Price at which you bought")
    stop_price: Optional[float] = Field(None, description="Exact price to trigger sell")
    stop_pct: Optional[float] = Field(None, ge=0.5, le=50, description="% below entry to trigger (e.g., 5.0)")
    mode: str = Field("paper", pattern="^(paper|live)$")

    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": 1,
                "symbol": "RELIANCE",
                "quantity": 10,
                "entry_price": 2580,
                "stop_pct": 5.0,
                "mode": "paper",
            }
        }


class TakeProfitRequest(BaseModel):
    portfolio_id: int
    symbol: str
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    target_price: Optional[float] = Field(None, description="Exact price to take profit")
    target_pct: Optional[float] = Field(None, ge=1.0, le=500, description="% above entry (e.g., 10.0)")
    mode: str = Field("paper", pattern="^(paper|live)$")


class TrailingStopRequest(BaseModel):
    portfolio_id: int
    symbol: str
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    trail_pct: Optional[float] = Field(None, ge=0.5, le=20, description="Trail % below peak (e.g., 3.0)")
    trail_amount: Optional[float] = Field(None, gt=0, description="Trail fixed amount below peak")
    mode: str = Field("paper", pattern="^(paper|live)$")


class OCORequest(BaseModel):
    portfolio_id: int
    symbol: str
    quantity: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    stop_price: Optional[float] = None
    stop_pct: Optional[float] = Field(None, ge=0.5, le=50)
    target_price: Optional[float] = None
    target_pct: Optional[float] = Field(None, ge=1.0, le=500)
    mode: str = Field("paper", pattern="^(paper|live)$")

    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": 1,
                "symbol": "RELIANCE",
                "quantity": 10,
                "entry_price": 2580,
                "stop_pct": 5.0,
                "target_pct": 10.0,
                "mode": "paper",
            }
        }


class SimulateRequest(BaseModel):
    entry_price: float = Field(..., gt=0)
    quantity: float = Field(10, gt=0)
    stop_pct: float = Field(5.0, ge=0.5)
    target_pct: float = Field(10.0, ge=1.0)
    trail_pct: Optional[float] = Field(None, ge=0.5)
    price_path: list[float] = Field(
        ...,
        min_length=2,
        description="List of prices to simulate (e.g., [2580, 2600, 2650, 2620, 2500])"
    )


# ─── Endpoints ───

@router.post("/stop-loss")
async def set_stop_loss(
    request: StopLossRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set a stop-loss on a position.
    Automatically sells when price drops to your stop level.

    Example: Bought RELIANCE at ₹2,580. Set 5% stop loss.
    → If price drops to ₹2,451 → auto-sells to limit loss to ₹1,290.
    """
    engine = StopLossEngine(db)
    try:
        order = await engine.create_stop_loss(
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            quantity=request.quantity,
            entry_price=request.entry_price,
            stop_price=request.stop_price,
            stop_pct=request.stop_pct,
            mode=request.mode,
        )
        await db.commit()

        potential_loss = (request.entry_price - order.stop_price) * request.quantity
        return {
            "message": (
                f"✅ Stop Loss set for {request.symbol}! "
                f"If price drops to ₹{order.stop_price:,.2f}, "
                f"your {request.quantity:.0f} shares will automatically sell. "
                f"Maximum loss capped at ₹{potential_loss:,.0f}."
            ),
            "order_id": order.id,
            "symbol": order.symbol,
            "stop_price": order.stop_price,
            "entry_price": order.entry_price,
            "max_loss": round(potential_loss, 2),
        }
    except StopOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/take-profit")
async def set_take_profit(
    request: TakeProfitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set a take-profit on a position.
    Automatically sells when price reaches your target.

    Example: Bought RELIANCE at ₹2,580. Set 10% take profit.
    → If price hits ₹2,838 → auto-sells to lock in ₹2,580 profit.
    """
    engine = StopLossEngine(db)
    try:
        order = await engine.create_take_profit(
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            quantity=request.quantity,
            entry_price=request.entry_price,
            target_price=request.target_price,
            target_pct=request.target_pct,
            mode=request.mode,
        )
        await db.commit()

        potential_gain = (order.target_price - request.entry_price) * request.quantity
        return {
            "message": (
                f"✅ Take Profit set for {request.symbol}! "
                f"When price reaches ₹{order.target_price:,.2f}, "
                f"your {request.quantity:.0f} shares will sell automatically. "
                f"You'll lock in a profit of ₹{potential_gain:,.0f}."
            ),
            "order_id": order.id,
            "symbol": order.symbol,
            "target_price": order.target_price,
            "entry_price": order.entry_price,
            "expected_profit": round(potential_gain, 2),
        }
    except StopOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/trailing-stop")
async def set_trailing_stop(
    request: TrailingStopRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set a trailing stop that follows price upward.
    Best of both worlds: ride the uptrend while protecting against reversal.

    Example: Bought at ₹2,580, trail 3%.
    Price → ₹2,700: stop moves to ₹2,619
    Price → ₹2,800: stop moves to ₹2,716
    Price → ₹2,716: TRIGGERED! Sells, locking in profit.
    """
    engine = StopLossEngine(db)
    try:
        order = await engine.create_trailing_stop(
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            quantity=request.quantity,
            entry_price=request.entry_price,
            trail_pct=request.trail_pct,
            trail_amount=request.trail_amount,
            mode=request.mode,
        )
        await db.commit()

        return {
            "message": (
                f"✅ Trailing Stop set for {request.symbol}! "
                f"The stop will follow the price upward, always staying "
                f"{request.trail_pct or 0:.1f}% below the highest price. "
                f"Current stop: ₹{order.current_stop:,.2f}."
            ),
            "order_id": order.id,
            "symbol": order.symbol,
            "trail_pct": order.trail_pct,
            "current_stop": order.current_stop,
            "highest_price": order.highest_price,
        }
    except StopOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/oco")
async def set_oco(
    request: OCORequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set OCO (One-Cancels-Other): Stop Loss + Take Profit together.
    Whichever triggers first cancels the other.

    Example: RELIANCE, SL at -5%, TP at +10%.
    → Price drops 5% → sells to limit loss (TP cancelled)
    → Price rises 10% → sells to lock profit (SL cancelled)
    """
    engine = StopLossEngine(db)
    try:
        result = await engine.create_oco(
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            quantity=request.quantity,
            entry_price=request.entry_price,
            stop_price=request.stop_price,
            stop_pct=request.stop_pct,
            target_price=request.target_price,
            target_pct=request.target_pct,
            mode=request.mode,
        )
        await db.commit()

        return {
            "message": result["summary"],
            "stop_loss_order_id": result["stop_loss"].id,
            "take_profit_order_id": result["take_profit"].id,
        }
    except StopOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active")
async def get_active_stops(
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all your active stop-loss and take-profit orders."""
    engine = StopLossEngine(db)
    orders = await engine.get_active_stops(current_user.id, symbol)
    return {"active_orders": orders, "count": len(orders)}


@router.get("/history")
async def get_stop_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get history of triggered/executed stop orders."""
    engine = StopLossEngine(db)
    orders = await engine.get_stop_history(current_user.id, limit)
    return {"history": orders, "count": len(orders)}


@router.delete("/{order_id}")
async def cancel_stop_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active stop order."""
    engine = StopLossEngine(db)
    try:
        result = await engine.cancel_stop(current_user.id, order_id)
        await db.commit()
        return result
    except StopOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/simulate")
async def simulate_stops(request: SimulateRequest):
    """
    Simulate stop-loss / take-profit / trailing stop against a price path.
    No login required — educational tool.

    Pass a list of prices to see exactly when and why each order type triggers.
    """
    results = {
        "entry_price": request.entry_price,
        "quantity": request.quantity,
        "price_path": request.price_path,
    }

    # ── Fixed Stop Loss ──
    sl_price = request.entry_price * (1 - request.stop_pct / 100)
    sl_triggered = False
    for i, price in enumerate(request.price_path):
        if price <= sl_price:
            pnl = (price - request.entry_price) * request.quantity
            results["stop_loss"] = {
                "stop_price": round(sl_price, 2),
                "triggered_at_step": i + 1,
                "trigger_price": price,
                "pnl": round(pnl, 2),
                "explanation": (
                    f"Stop Loss triggered at step {i + 1} when price hit ₹{price:,.2f} "
                    f"(stop was ₹{sl_price:,.2f}). Loss: ₹{abs(pnl):,.0f}."
                ),
            }
            sl_triggered = True
            break
    if not sl_triggered:
        results["stop_loss"] = {
            "stop_price": round(sl_price, 2),
            "triggered": False,
            "explanation": f"Stop loss at ₹{sl_price:,.2f} was never hit.",
        }

    # ── Fixed Take Profit ──
    tp_price = request.entry_price * (1 + request.target_pct / 100)
    tp_triggered = False
    for i, price in enumerate(request.price_path):
        if price >= tp_price:
            pnl = (price - request.entry_price) * request.quantity
            results["take_profit"] = {
                "target_price": round(tp_price, 2),
                "triggered_at_step": i + 1,
                "trigger_price": price,
                "pnl": round(pnl, 2),
                "explanation": (
                    f"Take Profit triggered at step {i + 1} when price hit ₹{price:,.2f} "
                    f"(target was ₹{tp_price:,.2f}). Profit: ₹{pnl:,.0f}!"
                ),
            }
            tp_triggered = True
            break
    if not tp_triggered:
        results["take_profit"] = {
            "target_price": round(tp_price, 2),
            "triggered": False,
            "explanation": f"Take profit at ₹{tp_price:,.2f} was never reached.",
        }

    # ── Trailing Stop ──
    if request.trail_pct:
        highest = request.entry_price
        trail_log = []
        trail_triggered = False

        for i, price in enumerate(request.price_path):
            if price > highest:
                highest = price
            current_stop = highest * (1 - request.trail_pct / 100)

            trail_log.append({
                "step": i + 1,
                "price": price,
                "highest_seen": round(highest, 2),
                "trailing_stop": round(current_stop, 2),
            })

            if price <= current_stop:
                pnl = (price - request.entry_price) * request.quantity
                results["trailing_stop"] = {
                    "trail_pct": request.trail_pct,
                    "triggered_at_step": i + 1,
                    "trigger_price": price,
                    "peak_price": round(highest, 2),
                    "pnl": round(pnl, 2),
                    "trail_log": trail_log,
                    "explanation": (
                        f"Trailing stop ({request.trail_pct}%) triggered at step {i + 1}. "
                        f"Price peaked at ₹{highest:,.2f}, stop was at ₹{current_stop:,.2f}. "
                        f"Sold at ₹{price:,.2f}. "
                        f"{'Profit: ₹' + f'{pnl:,.0f}' if pnl > 0 else 'Loss: ₹' + f'{abs(pnl):,.0f}'}."
                    ),
                }
                trail_triggered = True
                break

        if not trail_triggered:
            results["trailing_stop"] = {
                "trail_pct": request.trail_pct,
                "triggered": False,
                "final_stop": round(highest * (1 - request.trail_pct / 100), 2),
                "peak_price": round(highest, 2),
                "trail_log": trail_log,
                "explanation": f"Trailing stop was never triggered. Peak: ₹{highest:,.2f}.",
            }

    return results
