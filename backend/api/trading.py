"""
FinVoice — Trading API
Paper trading (free), live trading (paid), order management, broker sync.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from api.auth import get_current_user, require_paid_tier, require_onboarding_complete
from services.trading_engine import TradingEngine, TradingEngineError
from services.risk_controls import RiskControlError
from services.paper_trader import PaperTrader

router = APIRouter()

SEBI_DISCLAIMER = (
    "FinVoice is a decision-support tool. Invest at your own risk. "
    "Consult a SEBI-registered advisor for personalized advice. "
    "Past performance does not guarantee future results."
)


# ─── Request/Response Schemas ───


class SingleTradeRequest(BaseModel):
    portfolio_id: int
    symbol: str = Field(..., description="Stock symbol, e.g. RELIANCE")
    side: str = Field(..., pattern="^(buy|sell)$", description="buy or sell")
    amount_inr: float = Field(0, ge=0, description="Trade amount in INR (auto-calculates quantity)")
    quantity: int = Field(0, ge=0, description="Explicit share quantity (overrides amount_inr)")
    order_type: str = Field("market", pattern="^(market|limit)$")
    limit_price: Optional[float] = Field(None, ge=0, description="Required for limit orders")


class RebalanceRequest(BaseModel):
    portfolio_id: int
    trades: list[dict] = Field(
        ...,
        description="List of trades from optimizer: [{symbol, action, amount_inr}]",
        min_length=1,
    )


class CancelOrderRequest(BaseModel):
    order_id: int


# ─── Paper Trading Endpoints ───


@router.post("/paper/execute")
async def paper_execute_trade(
    request: SingleTradeRequest,
    current_user: User = Depends(require_onboarding_complete),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a single paper trade.
    Available to all users (free + paid). Uses virtual ₹10L balance.
    """
    engine = TradingEngine(db, current_user)

    try:
        result = await engine.execute_single_trade(
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            side=request.side,
            amount_inr=request.amount_inr,
            quantity=request.quantity,
            mode="paper",
            order_type=request.order_type,
            limit_price=request.limit_price,
        )
        return {**result, "disclaimer": SEBI_DISCLAIMER}

    except RiskControlError as e:
        raise HTTPException(
            status_code=422,
            detail={"rule": e.rule, "message": e.message},
        )
    except TradingEngineError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/paper/rebalance")
async def paper_rebalance(
    request: RebalanceRequest,
    current_user: User = Depends(require_onboarding_complete),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a batch of paper trades from optimizer output.
    Runs all rebalancing trades in paper mode.
    """
    engine = TradingEngine(db, current_user)

    try:
        result = await engine.execute_rebalance(
            portfolio_id=request.portfolio_id,
            trades=request.trades,
            mode="paper",
        )
        return {**result, "disclaimer": SEBI_DISCLAIMER}

    except TradingEngineError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/paper/balance")
async def get_paper_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paper trading account balance and stats."""
    trader = PaperTrader(db)
    return await trader.get_balance(current_user.id)


@router.post("/paper/reset")
async def reset_paper_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset paper trading account to initial ₹10L balance."""
    trader = PaperTrader(db)
    return await trader.reset_account(current_user.id)


# ─── Live Trading Endpoints (Paid Tier Only) ───


@router.post("/live/execute")
async def live_execute_trade(
    request: SingleTradeRequest,
    current_user: User = Depends(require_paid_tier),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a real trade via Angel One SmartAPI.
    PAID TIER ONLY. Requires Angel One credentials in .env.
    """
    engine = TradingEngine(db, current_user)

    try:
        result = await engine.execute_single_trade(
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            side=request.side,
            amount_inr=request.amount_inr,
            quantity=request.quantity,
            mode="live",
            order_type=request.order_type,
            limit_price=request.limit_price,
        )
        return {**result, "disclaimer": SEBI_DISCLAIMER}

    except RiskControlError as e:
        raise HTTPException(
            status_code=422,
            detail={"rule": e.rule, "message": e.message},
        )
    except TradingEngineError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/live/rebalance")
async def live_rebalance(
    request: RebalanceRequest,
    current_user: User = Depends(require_paid_tier),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute batch rebalancing via Angel One.
    PAID TIER ONLY. Passes optimizer trades directly to broker.
    """
    engine = TradingEngine(db, current_user)

    try:
        result = await engine.execute_rebalance(
            portfolio_id=request.portfolio_id,
            trades=request.trades,
            mode="live",
        )
        return {**result, "disclaimer": SEBI_DISCLAIMER}

    except TradingEngineError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Order Management ───


@router.get("/orders")
async def get_orders(
    portfolio_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trade order history for a portfolio."""
    engine = TradingEngine(db, current_user)
    orders = await engine.get_order_history(portfolio_id, limit)
    return {"orders": orders, "count": len(orders)}


@router.get("/orders/{order_id}")
async def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific trade order."""
    from sqlalchemy import select
    from models.trading import TradeOrder

    result = await db.execute(
        select(TradeOrder).where(
            TradeOrder.id == order_id,
            TradeOrder.user_id == current_user.id,
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": order.id,
        "symbol": order.symbol,
        "side": order.side.value,
        "quantity": order.quantity,
        "price": order.filled_price or order.price,
        "total_value": order.total_value or 0,
        "status": order.status.value,
        "mode": order.mode.value,
        "order_type": order.order_type.value,
        "broker_order_id": order.broker_order_id,
        "brokerage_fee": order.brokerage_fee or 0,
        "stt_charges": order.stt_charges or 0,
        "slippage_pct": order.slippage_pct or 0,
        "error": order.error_message,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "executed_at": order.executed_at.isoformat() if order.executed_at else None,
    }


# ─── Broker Sync (Paid Only) ───


@router.post("/sync-holdings")
async def sync_broker_holdings(
    portfolio_id: int,
    current_user: User = Depends(require_paid_tier),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync holdings from Angel One broker account into FinVoice.
    Imports your real broker holdings so FinVoice can analyze them.
    """
    from services.broker_client import AngelOneBroker, BrokerAuthError

    try:
        broker = AngelOneBroker()
        await broker.login()
        holdings = await broker.get_holdings()
        await broker.logout()

        return {
            "synced_holdings": len(holdings),
            "holdings": holdings,
            "message": f"Successfully synced {len(holdings)} holdings from Angel One",
        }

    except BrokerAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
