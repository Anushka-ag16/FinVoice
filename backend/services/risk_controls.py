"""
FinVoice — Risk Controls & Circuit Breakers
Safety layer that validates every trade before execution.
Prevents catastrophic losses via position limits, daily caps, and market hours enforcement.
"""

import logging
from datetime import datetime, time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from models.trading import TradeOrder, TradingCircuitBreaker, OrderSide
from models import Portfolio, Holding, Asset
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RiskControlError(Exception):
    """Raised when a trade violates risk controls."""

    def __init__(self, rule: str, message: str):
        self.rule = rule
        self.message = message
        super().__init__(f"[{rule}] {message}")


class RiskControlsService:
    """
    Validates trades against safety rules before execution.
    All checks must pass or the trade is blocked.
    """

    # ─── Configurable Limits ───
    MAX_SINGLE_ORDER_PCT = 25.0       # No single order > 25% of portfolio
    DAILY_LOSS_LIMIT_PCT = 3.0        # Halt if daily P&L < -3%
    MAX_DAILY_TRADES = 20             # No more than 20 trades/day
    MAX_CONCENTRATION_PCT = 30.0      # No single stock > 30% after trade
    MIN_COOLDOWN_SECONDS = 300        # 5 min between same-symbol trades
    MARKET_OPEN = time(9, 15)         # 9:15 AM IST
    MARKET_CLOSE = time(15, 30)       # 3:30 PM IST

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_trade(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        side: str,
        quantity: float,
        estimated_price: float,
        portfolio_value: float,
    ) -> dict:
        """
        Run all risk checks. Returns validation result.
        Raises RiskControlError if any check fails.
        """
        checks_passed = []
        order_value = quantity * estimated_price

        # 1. Market Hours
        self._check_market_hours()
        checks_passed.append("market_hours")

        # 2. Max Single Order Size
        self._check_max_order_size(order_value, portfolio_value)
        checks_passed.append("max_order_size")

        # 3. Daily Loss Limit (circuit breaker)
        await self._check_daily_loss_limit(user_id, portfolio_value)
        checks_passed.append("daily_loss_limit")

        # 4. Max Daily Trades
        await self._check_max_daily_trades(user_id)
        checks_passed.append("max_daily_trades")

        # 5. Concentration Limit
        if side == OrderSide.BUY.value or side == "buy":
            await self._check_concentration_limit(
                portfolio_id, symbol, order_value, portfolio_value
            )
        checks_passed.append("concentration_limit")

        # 6. Cooldown Period
        await self._check_cooldown(user_id, symbol)
        checks_passed.append("cooldown_period")

        logger.info(
            f"Risk controls passed for user {user_id}: "
            f"{symbol} {side} {quantity} @ ₹{estimated_price:.2f}"
        )

        return {
            "approved": True,
            "checks_passed": checks_passed,
            "order_value": order_value,
            "portfolio_value": portfolio_value,
            "order_pct_of_portfolio": round(order_value / portfolio_value * 100, 2) if portfolio_value > 0 else 0,
        }

    def _check_market_hours(self):
        """Orders only between 9:15 AM – 3:30 PM IST."""
        now = datetime.now()
        current_time = now.time()

        # Allow outside market hours in development
        if settings.app_env == "development":
            return

        if current_time < self.MARKET_OPEN or current_time > self.MARKET_CLOSE:
            raise RiskControlError(
                "MARKET_HOURS",
                f"Market is closed. Trading hours: {self.MARKET_OPEN.strftime('%H:%M')} – "
                f"{self.MARKET_CLOSE.strftime('%H:%M')} IST. "
                f"Current time: {current_time.strftime('%H:%M')} IST."
            )

        # Check for weekends
        if now.weekday() >= 5:
            raise RiskControlError(
                "MARKET_HOURS",
                "Market is closed on weekends. Order will be queued for Monday."
            )

    def _check_max_order_size(self, order_value: float, portfolio_value: float):
        """No single order > 25% of portfolio value."""
        if portfolio_value <= 0:
            return

        order_pct = (order_value / portfolio_value) * 100
        if order_pct > self.MAX_SINGLE_ORDER_PCT:
            raise RiskControlError(
                "MAX_ORDER_SIZE",
                f"Order value ₹{order_value:,.0f} is {order_pct:.1f}% of portfolio "
                f"(limit: {self.MAX_SINGLE_ORDER_PCT}%). "
                f"Reduce order size or increase portfolio value."
            )

    async def _check_daily_loss_limit(self, user_id: int, portfolio_value: float):
        """If daily P&L < -3% of portfolio, halt all trading."""
        today = datetime.now().date()

        result = await self.db.execute(
            select(TradingCircuitBreaker)
            .where(
                TradingCircuitBreaker.user_id == user_id,
                sa_func.date(TradingCircuitBreaker.date) == today,
            )
        )
        cb = result.scalar_one_or_none()

        if cb and cb.is_halted:
            raise RiskControlError(
                "CIRCUIT_BREAKER",
                f"Trading halted for today. Reason: {cb.halt_reason}. "
                "Circuit breaker resets at next market open."
            )

        if cb and portfolio_value > 0:
            loss_pct = abs(cb.daily_pnl / portfolio_value * 100) if cb.daily_pnl < 0 else 0
            if loss_pct >= self.DAILY_LOSS_LIMIT_PCT:
                # Trip the circuit breaker
                cb.is_halted = True
                cb.halt_reason = (
                    f"Daily loss of {loss_pct:.1f}% exceeded {self.DAILY_LOSS_LIMIT_PCT}% limit"
                )
                await self.db.flush()

                raise RiskControlError(
                    "DAILY_LOSS_LIMIT",
                    f"Daily loss of ₹{abs(cb.daily_pnl):,.0f} ({loss_pct:.1f}%) "
                    f"exceeds the {self.DAILY_LOSS_LIMIT_PCT}% safety limit. "
                    "All trading halted for today."
                )

    async def _check_max_daily_trades(self, user_id: int):
        """No more than 20 trades per day."""
        today = datetime.now().date()

        result = await self.db.execute(
            select(sa_func.count(TradeOrder.id))
            .where(
                TradeOrder.user_id == user_id,
                sa_func.date(TradeOrder.created_at) == today,
            )
        )
        count = result.scalar() or 0

        if count >= self.MAX_DAILY_TRADES:
            raise RiskControlError(
                "MAX_DAILY_TRADES",
                f"You've placed {count} trades today (limit: {self.MAX_DAILY_TRADES}). "
                "Wait until tomorrow to trade again."
            )

    async def _check_concentration_limit(
        self, portfolio_id: int, symbol: str, order_value: float, portfolio_value: float
    ):
        """No single stock > 30% of portfolio after trade."""
        # Get current holding value for this symbol
        result = await self.db.execute(
            select(Holding, Asset)
            .join(Asset, Holding.asset_id == Asset.id)
            .where(
                Holding.portfolio_id == portfolio_id,
                Asset.symbol == symbol,
            )
        )
        row = result.first()

        current_value = 0.0
        if row:
            holding, asset = row
            price = holding.current_price or holding.buy_price
            current_value = holding.quantity * price

        new_value = current_value + order_value
        new_total = portfolio_value + order_value

        if new_total > 0:
            concentration_pct = (new_value / new_total) * 100
            if concentration_pct > self.MAX_CONCENTRATION_PCT:
                raise RiskControlError(
                    "CONCENTRATION_LIMIT",
                    f"{symbol} would be {concentration_pct:.1f}% of your portfolio "
                    f"(limit: {self.MAX_CONCENTRATION_PCT}%). "
                    f"Diversify by reducing this position."
                )

    async def _check_cooldown(self, user_id: int, symbol: str):
        """Minimum 5 minutes between trades on same symbol."""
        result = await self.db.execute(
            select(TradeOrder)
            .where(
                TradeOrder.user_id == user_id,
                TradeOrder.symbol == symbol,
            )
            .order_by(TradeOrder.created_at.desc())
            .limit(1)
        )
        last_trade = result.scalar_one_or_none()

        if last_trade and last_trade.created_at:
            elapsed = (datetime.now() - last_trade.created_at).total_seconds()
            if elapsed < self.MIN_COOLDOWN_SECONDS:
                remaining = int(self.MIN_COOLDOWN_SECONDS - elapsed)
                raise RiskControlError(
                    "COOLDOWN",
                    f"Cooldown active on {symbol}. Wait {remaining} seconds before "
                    f"trading this symbol again."
                )
