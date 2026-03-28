"""
FinVoice — Stop Loss & Take Profit Engine
Monitors prices and triggers automatic exits when conditions are met.

How it works:
    1. User sets SL/TP when buying a stock (or anytime after)
    2. A background task polls prices every N seconds
    3. When a stop condition triggers → auto-places a sell order
    4. Records the P&L and notifies the user

Supported strategies:
    • Fixed Stop Loss:    "Sell if RELIANCE drops below ₹2,450"
    • Percentage Stop:    "Sell if RELIANCE drops 5% from my buy price"
    • Fixed Take Profit:  "Sell if RELIANCE hits ₹2,800"
    • Trailing Stop:      "Follow price upward, sell if it drops 3% from peak"
    • OCO:                "SL at ₹2,450, TP at ₹2,800 — whichever happens first"
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from models.stop_orders import StopOrder, StopOrderType, StopOrderStatus

logger = logging.getLogger(__name__)


class StopOrderError(Exception):
    pass


class StopLossEngine:
    """
    Creates, monitors, and executes stop-loss and take-profit orders.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─────────────────────────────────────────────
    #  Creating Stop Orders
    # ─────────────────────────────────────────────

    async def create_stop_loss(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        entry_price: float,
        stop_price: float = None,
        stop_pct: float = None,
        mode: str = "paper",
        expires_at: datetime = None,
        trade_order_id: int = None,
    ) -> StopOrder:
        """
        Create a fixed stop-loss order.

        Args:
            stop_price: Exact price to trigger sell (e.g., ₹2,450)
            stop_pct: OR percentage below entry (e.g., 5.0 = sell if drops 5%)
        """
        if not stop_price and not stop_pct:
            raise StopOrderError("Provide either stop_price or stop_pct")

        if stop_pct and not stop_price:
            stop_price = entry_price * (1 - stop_pct / 100)

        if stop_price >= entry_price:
            raise StopOrderError(
                f"Stop loss (₹{stop_price:,.2f}) must be below your buy price "
                f"(₹{entry_price:,.2f}). A stop-loss protects you from drops."
            )

        # Calculate potential loss
        potential_loss = (entry_price - stop_price) * quantity
        loss_pct = (entry_price - stop_price) / entry_price * 100

        order = StopOrder(
            user_id=user_id,
            portfolio_id=portfolio_id,
            trade_order_id=trade_order_id,
            symbol=symbol.upper(),
            quantity=quantity,
            entry_price=entry_price,
            order_type=StopOrderType.STOP_LOSS,
            stop_price=stop_price,
            stop_pct=stop_pct or loss_pct,
            mode=mode,
            expires_at=expires_at,
        )
        self.db.add(order)
        await self.db.flush()

        logger.info(
            f"Stop Loss set: {symbol} — sell {quantity} shares if price drops to "
            f"₹{stop_price:,.2f} (max loss: ₹{potential_loss:,.0f} / {loss_pct:.1f}%)"
        )

        return order

    async def create_take_profit(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        entry_price: float,
        target_price: float = None,
        target_pct: float = None,
        mode: str = "paper",
        expires_at: datetime = None,
        trade_order_id: int = None,
    ) -> StopOrder:
        """
        Create a take-profit order.

        Args:
            target_price: Exact price to take profit (e.g., ₹2,800)
            target_pct: OR percentage above entry (e.g., 10.0 = sell at +10%)
        """
        if not target_price and not target_pct:
            raise StopOrderError("Provide either target_price or target_pct")

        if target_pct and not target_price:
            target_price = entry_price * (1 + target_pct / 100)

        if target_price <= entry_price:
            raise StopOrderError(
                f"Take profit (₹{target_price:,.2f}) must be above your buy price "
                f"(₹{entry_price:,.2f}). A take-profit locks in your gains."
            )

        # Calculate potential gain
        potential_gain = (target_price - entry_price) * quantity
        gain_pct = (target_price - entry_price) / entry_price * 100

        order = StopOrder(
            user_id=user_id,
            portfolio_id=portfolio_id,
            trade_order_id=trade_order_id,
            symbol=symbol.upper(),
            quantity=quantity,
            entry_price=entry_price,
            order_type=StopOrderType.TAKE_PROFIT,
            target_price=target_price,
            target_pct=target_pct or gain_pct,
            mode=mode,
            expires_at=expires_at,
        )
        self.db.add(order)
        await self.db.flush()

        logger.info(
            f"Take Profit set: {symbol} — sell {quantity} shares if price hits "
            f"₹{target_price:,.2f} (profit: ₹{potential_gain:,.0f} / +{gain_pct:.1f}%)"
        )

        return order

    async def create_trailing_stop(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        entry_price: float,
        trail_pct: float = None,
        trail_amount: float = None,
        mode: str = "paper",
        expires_at: datetime = None,
        trade_order_id: int = None,
    ) -> StopOrder:
        """
        Create a trailing stop-loss that follows price upward.

        Examples:
            trail_pct=3.0: Stop trails 3% below the highest price seen.
            trail_amount=50: Stop trails ₹50 below the highest price seen.

        If stock goes 2580→2700→2800, trailing stop (3%) moves:
            2580*0.97=2502 → 2700*0.97=2619 → 2800*0.97=2716
        If price then drops to 2716, it triggers.
        """
        if not trail_pct and not trail_amount:
            raise StopOrderError("Provide either trail_pct or trail_amount")

        if trail_pct:
            initial_stop = entry_price * (1 - trail_pct / 100)
        else:
            initial_stop = entry_price - trail_amount

        order = StopOrder(
            user_id=user_id,
            portfolio_id=portfolio_id,
            trade_order_id=trade_order_id,
            symbol=symbol.upper(),
            quantity=quantity,
            entry_price=entry_price,
            order_type=StopOrderType.TRAILING_STOP,
            trail_pct=trail_pct,
            trail_amount=trail_amount,
            highest_price=entry_price,
            current_stop=initial_stop,
            mode=mode,
            expires_at=expires_at,
        )
        self.db.add(order)
        await self.db.flush()

        logger.info(
            f"Trailing Stop set: {symbol} — trailing {trail_pct or ''}{'%' if trail_pct else ''}"
            f"{('₹' + str(trail_amount)) if trail_amount else ''} below peak. "
            f"Current stop: ₹{initial_stop:,.2f}"
        )

        return order

    async def create_oco(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        entry_price: float,
        stop_price: float = None,
        stop_pct: float = None,
        target_price: float = None,
        target_pct: float = None,
        mode: str = "paper",
        expires_at: datetime = None,
        trade_order_id: int = None,
    ) -> dict:
        """
        Create an OCO (One-Cancels-Other) pair: SL + TP together.
        Whichever triggers first cancels the other.
        """
        # Create stop loss
        sl_order = await self.create_stop_loss(
            user_id=user_id,
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_price=stop_price,
            stop_pct=stop_pct,
            mode=mode,
            expires_at=expires_at,
            trade_order_id=trade_order_id,
        )

        # Create take profit
        tp_order = await self.create_take_profit(
            user_id=user_id,
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            target_price=target_price,
            target_pct=target_pct,
            mode=mode,
            expires_at=expires_at,
            trade_order_id=trade_order_id,
        )

        # Link them
        sl_order.order_type = StopOrderType.OCO
        sl_order.linked_order_id = tp_order.id
        sl_order.target_price = target_price or entry_price * (1 + (target_pct or 10) / 100)
        sl_order.target_pct = target_pct

        tp_order.order_type = StopOrderType.OCO
        tp_order.linked_order_id = sl_order.id
        tp_order.stop_price = stop_price or entry_price * (1 - (stop_pct or 5) / 100)
        tp_order.stop_pct = stop_pct

        await self.db.flush()

        logger.info(
            f"OCO set: {symbol} — SL ₹{sl_order.stop_price:,.2f} / "
            f"TP ₹{tp_order.target_price:,.2f}"
        )

        return {
            "stop_loss": sl_order,
            "take_profit": tp_order,
            "summary": (
                f"Protection set for {quantity:.0f} shares of {symbol}:\n"
                f"• Stop Loss at ₹{sl_order.stop_price:,.2f} "
                f"(max loss: ₹{(entry_price - sl_order.stop_price) * quantity:,.0f})\n"
                f"• Take Profit at ₹{tp_order.target_price:,.2f} "
                f"(target gain: ₹{(tp_order.target_price - entry_price) * quantity:,.0f})\n"
                f"Whichever price is hit first will trigger. The other cancels automatically."
            ),
        }

    # ─────────────────────────────────────────────
    #  Price Monitoring & Trigger Logic
    # ─────────────────────────────────────────────

    async def check_all_stops(self, prices: dict[str, float]) -> list[dict]:
        """
        Check ALL active stop orders against current prices.
        Called periodically by background task.

        Args:
            prices: {symbol: current_price} for all relevant symbols

        Returns:
            List of triggered orders with details.
        """
        result = await self.db.execute(
            select(StopOrder).where(
                StopOrder.status == StopOrderStatus.ACTIVE,
            )
        )
        active_orders = result.scalars().all()

        triggered = []

        for order in active_orders:
            current_price = prices.get(order.symbol)
            if current_price is None:
                continue

            # Check expiry
            if order.expires_at and datetime.now() > order.expires_at:
                order.status = StopOrderStatus.EXPIRED
                continue

            trigger_result = self._check_single_order(order, current_price)

            if trigger_result["triggered"]:
                order.status = StopOrderStatus.TRIGGERED
                order.triggered_price = current_price
                order.triggered_at = datetime.now()
                order.trigger_reason = trigger_result["reason"]

                # Cancel linked OCO order
                if order.linked_order_id:
                    await self._cancel_linked(order.linked_order_id)

                triggered.append({
                    "order_id": order.id,
                    "symbol": order.symbol,
                    "type": order.order_type.value,
                    "quantity": order.quantity,
                    "entry_price": order.entry_price,
                    "trigger_price": current_price,
                    "reason": trigger_result["reason"],
                    "pnl_estimate": (current_price - order.entry_price) * order.quantity,
                    "mode": order.mode,
                })

            elif order.order_type == StopOrderType.TRAILING_STOP:
                # Update trailing stop (even if not triggered)
                self._update_trailing(order, current_price)

        await self.db.flush()
        return triggered

    def _check_single_order(self, order: StopOrder, current_price: float) -> dict:
        """Check if a single stop order should trigger."""

        # ── Stop Loss: triggers when price drops to or below stop ──
        if order.order_type in (StopOrderType.STOP_LOSS, StopOrderType.OCO):
            if order.stop_price and current_price <= order.stop_price:
                loss = (order.entry_price - current_price) * order.quantity
                loss_pct = (order.entry_price - current_price) / order.entry_price * 100
                return {
                    "triggered": True,
                    "reason": (
                        f"🛑 Stop Loss triggered! {order.symbol} dropped to "
                        f"₹{current_price:,.2f} (your stop was ₹{order.stop_price:,.2f}). "
                        f"Selling {order.quantity:.0f} shares to limit your loss to "
                        f"₹{loss:,.0f} ({loss_pct:.1f}%). "
                        f"Without this stop, your loss could have been much larger."
                    ),
                }

        # ── Take Profit: triggers when price rises to or above target ──
        if order.order_type in (StopOrderType.TAKE_PROFIT, StopOrderType.OCO):
            if order.target_price and current_price >= order.target_price:
                gain = (current_price - order.entry_price) * order.quantity
                gain_pct = (current_price - order.entry_price) / order.entry_price * 100
                return {
                    "triggered": True,
                    "reason": (
                        f"🎯 Take Profit triggered! {order.symbol} reached "
                        f"₹{current_price:,.2f} (your target was ₹{order.target_price:,.2f}). "
                        f"Selling {order.quantity:.0f} shares to lock in your profit of "
                        f"₹{gain:,.0f} (+{gain_pct:.1f}%). "
                        f"Smart move — profits are only real when you book them!"
                    ),
                }

        # ── Trailing Stop: triggers when price drops from peak by trail % ──
        if order.order_type == StopOrderType.TRAILING_STOP:
            if order.current_stop and current_price <= order.current_stop:
                gain = (current_price - order.entry_price) * order.quantity
                gain_pct = (current_price - order.entry_price) / order.entry_price * 100
                peak_drop = (order.highest_price - current_price) / order.highest_price * 100
                return {
                    "triggered": True,
                    "reason": (
                        f"📉 Trailing Stop triggered! {order.symbol} dropped "
                        f"{peak_drop:.1f}% from its peak of ₹{order.highest_price:,.2f} "
                        f"to ₹{current_price:,.2f}. "
                        f"Your trailing stop was at ₹{order.current_stop:,.2f}. "
                        f"{'You still made a profit of ₹' + f'{gain:,.0f} (+{gain_pct:.1f}%)!' if gain > 0 else f'Loss limited to ₹{abs(gain):,.0f} ({abs(gain_pct):.1f}%).'} "
                        f"The trailing stop let you ride the uptrend while protecting against reversal."
                    ),
                }

        return {"triggered": False, "reason": ""}

    def _update_trailing(self, order: StopOrder, current_price: float):
        """Update trailing stop if price made a new high."""
        if current_price > (order.highest_price or 0):
            old_stop = order.current_stop
            order.highest_price = current_price

            if order.trail_pct:
                order.current_stop = current_price * (1 - order.trail_pct / 100)
            elif order.trail_amount:
                order.current_stop = current_price - order.trail_amount

            logger.debug(
                f"Trailing stop updated: {order.symbol} new high ₹{current_price:,.2f} "
                f"→ stop moved ₹{old_stop:,.2f} → ₹{order.current_stop:,.2f}"
            )

    async def _cancel_linked(self, linked_id: int):
        """Cancel the other leg of an OCO pair."""
        result = await self.db.execute(
            select(StopOrder).where(StopOrder.id == linked_id)
        )
        linked = result.scalar_one_or_none()
        if linked and linked.status == StopOrderStatus.ACTIVE:
            linked.status = StopOrderStatus.CANCELLED
            linked.trigger_reason = "Cancelled — the other side of your OCO order triggered first."

    async def execute_triggered_orders(self, triggered_orders: list[dict]) -> list[dict]:
        """
        Execute sell orders for all triggered stops.
        Called after check_all_stops returns triggered orders.
        """
        from services.trading_engine import TradingEngine
        from models import User

        results = []

        for triggered in triggered_orders:
            order_result = await self.db.execute(
                select(StopOrder).where(StopOrder.id == triggered["order_id"])
            )
            order = order_result.scalar_one_or_none()
            if not order:
                continue

            user_result = await self.db.execute(
                select(User).where(User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            try:
                engine = TradingEngine(self.db, user)
                trade_result = await engine.execute_single_trade(
                    portfolio_id=order.portfolio_id,
                    symbol=order.symbol,
                    side="sell",
                    quantity=order.quantity,
                    mode=order.mode,
                    market_price=triggered["trigger_price"],
                )

                # Update stop order
                order.status = StopOrderStatus.EXECUTED
                order.filled_price = trade_result.get("price", triggered["trigger_price"])
                order.executed_at = datetime.now()
                order.pnl = (order.filled_price - order.entry_price) * order.quantity

                results.append({
                    **triggered,
                    "execution": trade_result,
                    "pnl_realized": round(order.pnl, 2),
                })

            except Exception as e:
                order.status = StopOrderStatus.FAILED
                order.trigger_reason = f"Execution failed: {str(e)}"
                logger.error(f"Stop order execution failed: {e}")

                results.append({
                    **triggered,
                    "execution": {"status": "failed", "error": str(e)},
                })

        await self.db.flush()
        return results

    # ─────────────────────────────────────────────
    #  Queries
    # ─────────────────────────────────────────────

    async def get_active_stops(self, user_id: int, symbol: str = None) -> list[dict]:
        """Get all active stop orders for a user."""
        query = select(StopOrder).where(
            StopOrder.user_id == user_id,
            StopOrder.status == StopOrderStatus.ACTIVE,
        )
        if symbol:
            query = query.where(StopOrder.symbol == symbol.upper())

        result = await self.db.execute(query.order_by(StopOrder.created_at.desc()))
        orders = result.scalars().all()
        return [self._order_to_dict(o) for o in orders]

    async def get_stop_history(self, user_id: int, limit: int = 50) -> list[dict]:
        """Get triggered/executed stop orders history."""
        result = await self.db.execute(
            select(StopOrder).where(
                StopOrder.user_id == user_id,
                StopOrder.status.in_([
                    StopOrderStatus.EXECUTED,
                    StopOrderStatus.TRIGGERED,
                    StopOrderStatus.CANCELLED,
                ]),
            ).order_by(StopOrder.triggered_at.desc()).limit(limit)
        )
        orders = result.scalars().all()
        return [self._order_to_dict(o) for o in orders]

    async def cancel_stop(self, user_id: int, order_id: int) -> dict:
        """Cancel an active stop order."""
        result = await self.db.execute(
            select(StopOrder).where(
                StopOrder.id == order_id,
                StopOrder.user_id == user_id,
                StopOrder.status == StopOrderStatus.ACTIVE,
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise StopOrderError("Stop order not found or already triggered")

        order.status = StopOrderStatus.CANCELLED
        order.trigger_reason = "Cancelled by user"

        # Cancel linked OCO too
        if order.linked_order_id:
            await self._cancel_linked(order.linked_order_id)

        await self.db.flush()

        return {"message": f"Stop order for {order.symbol} cancelled successfully."}

    def _order_to_dict(self, order: StopOrder) -> dict:
        """Convert a StopOrder to a user-friendly dictionary."""
        # Plain English explanation
        if order.order_type == StopOrderType.STOP_LOSS:
            type_label = "Stop Loss"
            explanation = (
                f"Will automatically sell {order.quantity:.0f} shares of {order.symbol} "
                f"if the price drops to ₹{order.stop_price:,.2f} or below. "
                f"This limits your maximum loss to "
                f"₹{(order.entry_price - order.stop_price) * order.quantity:,.0f}."
            )
        elif order.order_type == StopOrderType.TAKE_PROFIT:
            type_label = "Take Profit"
            explanation = (
                f"Will automatically sell {order.quantity:.0f} shares of {order.symbol} "
                f"when the price reaches ₹{order.target_price:,.2f} or above. "
                f"This locks in a profit of "
                f"₹{(order.target_price - order.entry_price) * order.quantity:,.0f}."
            )
        elif order.order_type == StopOrderType.TRAILING_STOP:
            type_label = "Trailing Stop"
            explanation = (
                f"Following {order.symbol}'s price upward. Currently trailing "
                f"{order.trail_pct or 0:.1f}% below the peak of "
                f"₹{order.highest_price:,.2f}. "
                f"Current stop level: ₹{order.current_stop:,.2f}. "
                f"If price drops to this level, it will sell automatically."
            )
        elif order.order_type == StopOrderType.OCO:
            type_label = "OCO (Stop Loss + Take Profit)"
            explanation = (
                f"Dual protection: Sells if price drops to ₹{order.stop_price:,.2f} "
                f"(loss limit) OR rises to ₹{order.target_price:,.2f} (profit target). "
                f"Whichever happens first triggers the sell."
            )
        else:
            type_label = order.order_type.value
            explanation = ""

        return {
            "id": order.id,
            "symbol": order.symbol,
            "type": type_label,
            "order_type": order.order_type.value,
            "status": order.status.value,
            "quantity": order.quantity,
            "entry_price": order.entry_price,
            "stop_price": order.stop_price,
            "target_price": order.target_price,
            "trail_pct": order.trail_pct,
            "highest_price": order.highest_price,
            "current_stop": order.current_stop,
            "triggered_price": order.triggered_price,
            "filled_price": order.filled_price,
            "pnl": order.pnl,
            "trigger_reason": order.trigger_reason,
            "explanation": explanation,
            "mode": order.mode,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "triggered_at": order.triggered_at.isoformat() if order.triggered_at else None,
            "executed_at": order.executed_at.isoformat() if order.executed_at else None,
            "expires_at": order.expires_at.isoformat() if order.expires_at else None,
        }
