"""
FinVoice — Paper Trading Engine
Simulated trade execution without real money.
Mimics real broker behavior: fills at market price, deducts brokerage, tracks P&L.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Asset
from models.trading import (
    TradeOrder, PaperAccount, OrderSide, OrderType,
    OrderStatus, TradingMode,
)

logger = logging.getLogger(__name__)

# Simulated costs
DEFAULT_BROKERAGE = 20.0          # ₹20 per order (flat)
DEFAULT_SLIPPAGE_PCT = 0.10       # 0.1% slippage on market orders
STT_RATE = 0.001                  # 0.1% Securities Transaction Tax (delivery)


class PaperTradingError(Exception):
    """Raised when paper trade fails."""
    pass


class PaperTrader:
    """
    Simulated trading engine that mimics real broker execution.
    - Fills at current market price + slippage
    - Deducts brokerage fees (₹20/order)
    - Tracks virtual cash balance
    - Logs everything in trade_orders table
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_account(self, user_id: int) -> PaperAccount:
        """Get user's paper account or create one with ₹10L initial balance."""
        result = await self.db.execute(
            select(PaperAccount).where(PaperAccount.user_id == user_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            account = PaperAccount(
                user_id=user_id,
                cash_balance=1000000.0,
                initial_balance=1000000.0,
            )
            self.db.add(account)
            await self.db.flush()
            logger.info(f"Created paper account for user {user_id} with ₹10,00,000")

        return account

    async def execute_order(
        self,
        trade_order: TradeOrder,
        market_price: float,
    ) -> TradeOrder:
        """
        Execute a paper trade.

        Args:
            trade_order: The TradeOrder object (already created in DB).
            market_price: Current market price of the asset.

        Returns:
            Updated TradeOrder with fill details.
        """
        account = await self.get_or_create_account(trade_order.user_id)

        # Simulate slippage on market orders
        if trade_order.order_type == OrderType.MARKET:
            slippage = market_price * DEFAULT_SLIPPAGE_PCT / 100
            if trade_order.side == OrderSide.BUY:
                fill_price = market_price + slippage  # Buy slightly higher
            else:
                fill_price = market_price - slippage  # Sell slightly lower
        else:
            # Limit order: only fill if price is favorable
            if trade_order.side == OrderSide.BUY and market_price > trade_order.price:
                trade_order.status = OrderStatus.REJECTED
                trade_order.error_message = (
                    f"Limit price ₹{trade_order.price:.2f} is below "
                    f"market price ₹{market_price:.2f}"
                )
                return trade_order
            elif trade_order.side == OrderSide.SELL and market_price < trade_order.price:
                trade_order.status = OrderStatus.REJECTED
                trade_order.error_message = (
                    f"Limit price ₹{trade_order.price:.2f} is above "
                    f"market price ₹{market_price:.2f}"
                )
                return trade_order

            fill_price = trade_order.price
            slippage = 0.0

        # Calculate total cost
        total_value = trade_order.quantity * fill_price
        brokerage = DEFAULT_BROKERAGE
        stt = total_value * STT_RATE if trade_order.side == OrderSide.SELL else 0.0
        total_cost = total_value + brokerage + stt

        # Check cash balance for buys
        if trade_order.side == OrderSide.BUY:
            if account.cash_balance < total_cost:
                trade_order.status = OrderStatus.REJECTED
                trade_order.error_message = (
                    f"Insufficient paper balance. "
                    f"Required: ₹{total_cost:,.2f}, Available: ₹{account.cash_balance:,.2f}"
                )
                return trade_order

            account.cash_balance -= total_cost

        elif trade_order.side == OrderSide.SELL:
            # Credit sale proceeds minus charges
            net_proceeds = total_value - brokerage - stt
            account.cash_balance += net_proceeds

        # Update trade order
        trade_order.filled_price = round(fill_price, 2)
        trade_order.total_value = round(total_value, 2)
        trade_order.slippage_pct = round(DEFAULT_SLIPPAGE_PCT if trade_order.order_type == OrderType.MARKET else 0.0, 4)
        trade_order.brokerage_fee = brokerage
        trade_order.stt_charges = round(stt, 2)
        trade_order.status = OrderStatus.FILLED
        trade_order.executed_at = datetime.now()
        trade_order.broker_order_id = f"PAPER-{trade_order.id}-{datetime.now().strftime('%H%M%S')}"

        # Update account stats
        account.total_trades += 1
        pnl_change = -total_cost if trade_order.side == OrderSide.BUY else (total_value - brokerage - stt)
        account.total_pnl += pnl_change

        await self.db.flush()

        logger.info(
            f"Paper trade executed: {trade_order.side.value} {trade_order.quantity} "
            f"{trade_order.symbol} @ ₹{fill_price:.2f} | "
            f"Total: ₹{total_value:,.2f} | Fees: ₹{brokerage + stt:.2f} | "
            f"Balance: ₹{account.cash_balance:,.2f}"
        )

        return trade_order

    async def get_balance(self, user_id: int) -> dict:
        """Get paper trading account summary."""
        account = await self.get_or_create_account(user_id)

        return {
            "cash_balance": round(account.cash_balance, 2),
            "initial_balance": account.initial_balance,
            "total_trades": account.total_trades,
            "total_pnl": round(account.total_pnl, 2),
            "return_pct": round(
                (account.cash_balance - account.initial_balance) / account.initial_balance * 100, 2
            ) if account.initial_balance > 0 else 0.0,
        }

    async def reset_account(self, user_id: int) -> dict:
        """Reset paper account to initial balance."""
        account = await self.get_or_create_account(user_id)
        account.cash_balance = account.initial_balance
        account.total_trades = 0
        account.total_pnl = 0.0
        await self.db.flush()

        logger.info(f"Paper account reset for user {user_id}")
        return await self.get_balance(user_id)
