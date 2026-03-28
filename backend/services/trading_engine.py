"""
FinVoice — Trading Engine (Orchestrator)
Connects Portfolio Optimizer output → Risk Controls → Execution (Paper/Live).
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User, Portfolio, Holding, Asset
from models.trading import (
    TradeOrder, TradingCircuitBreaker, OrderSide, OrderType,
    OrderStatus, TradingMode,
)
from services.risk_controls import RiskControlsService, RiskControlError
from services.paper_trader import PaperTrader
from services.broker_client import AngelOneBroker, BrokerAuthError, BrokerOrderError

logger = logging.getLogger(__name__)


class TradingEngineError(Exception):
    """Raised when the trading engine encounters an error."""
    pass


class TradingEngine:
    """
    Main orchestrator for trade execution.

    Flow:
    1. Receives trade list from optimizer
    2. Validates via Risk Controls
    3. Sizes orders (INR → quantity using LTP)
    4. Executes via Paper Trader or Angel One
    5. Records transactions
    6. Updates portfolio
    """

    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.risk_controls = RiskControlsService(db)
        self.paper_trader = PaperTrader(db)
        self._broker: Optional[AngelOneBroker] = None

    async def _get_broker(self) -> AngelOneBroker:
        """Lazy-initialize and authenticate broker connection."""
        if self._broker is None:
            self._broker = AngelOneBroker()
            await self._broker.login()
        return self._broker

    async def execute_rebalance(
        self,
        portfolio_id: int,
        trades: list[dict],
        mode: str = "paper",
    ) -> dict:
        """
        Execute a batch of rebalancing trades from the optimizer.

        Args:
            portfolio_id: Portfolio to rebalance
            trades: List of dicts from optimizer: [{"symbol": "RELIANCE", "action": "BUY", "amount_inr": 50000}, ...]
            mode: "paper" or "live"

        Returns:
            Execution report with results for each trade.
        """
        # Verify portfolio ownership
        result = await self.db.execute(
            select(Portfolio).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == self.user.id,
            )
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            raise TradingEngineError("Portfolio not found or not owned by user")

        portfolio_value = portfolio.current_value or portfolio.total_invested or 0

        # Get market prices
        symbols = [t["symbol"] for t in trades]
        prices = await self._get_prices(symbols, mode)

        execution_results = []
        total_executed = 0
        total_failed = 0

        for trade in trades:
            try:
                result = await self.execute_single_trade(
                    portfolio_id=portfolio_id,
                    symbol=trade["symbol"],
                    side=trade["action"].lower(),
                    amount_inr=trade.get("amount_inr", 0),
                    mode=mode,
                    market_price=prices.get(trade["symbol"], 0),
                    portfolio_value=portfolio_value,
                )
                execution_results.append(result)
                if result["status"] == "filled":
                    total_executed += 1
                else:
                    total_failed += 1

            except RiskControlError as e:
                execution_results.append({
                    "symbol": trade["symbol"],
                    "status": "blocked",
                    "rule": e.rule,
                    "reason": e.message,
                })
                total_failed += 1

            except Exception as e:
                execution_results.append({
                    "symbol": trade["symbol"],
                    "status": "error",
                    "reason": str(e),
                })
                total_failed += 1

        return {
            "portfolio_id": portfolio_id,
            "mode": mode,
            "total_trades": len(trades),
            "executed": total_executed,
            "failed": total_failed,
            "results": execution_results,
            "timestamp": datetime.now().isoformat(),
        }

    async def execute_single_trade(
        self,
        portfolio_id: int,
        symbol: str,
        side: str,
        amount_inr: float = 0,
        quantity: float = 0,
        mode: str = "paper",
        order_type: str = "market",
        limit_price: float = None,
        market_price: float = None,
        portfolio_value: float = None,
    ) -> dict:
        """
        Execute a single trade with full risk validation.

        Args:
            portfolio_id: Target portfolio
            symbol: Stock symbol (e.g., "RELIANCE")
            side: "buy" or "sell"
            amount_inr: Trade amount in INR (auto-calculates quantity)
            quantity: Explicit quantity (overrides amount_inr)
            mode: "paper" or "live"
            order_type: "market" or "limit"
            limit_price: Price for limit orders
            market_price: Pre-fetched market price (optional)
            portfolio_value: Pre-calculated portfolio value (optional)
        """
        # Get market price if not provided
        if not market_price:
            prices = await self._get_prices([symbol], mode)
            market_price = prices.get(symbol, 0)

        if market_price <= 0:
            raise TradingEngineError(f"Could not get market price for {symbol}")

        # Calculate quantity from INR amount
        if quantity <= 0 and amount_inr > 0:
            quantity = int(amount_inr / market_price)  # Round down to whole shares
            if quantity <= 0:
                raise TradingEngineError(
                    f"Amount ₹{amount_inr:,.0f} is less than 1 share of {symbol} (₹{market_price:.2f})"
                )

        # Get portfolio value if not provided
        if portfolio_value is None:
            port_result = await self.db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            port = port_result.scalar_one_or_none()
            portfolio_value = (port.current_value or port.total_invested or 0) if port else 0

        # ─── Risk Validation ───
        validation = await self.risk_controls.validate_trade(
            user_id=self.user.id,
            portfolio_id=portfolio_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            estimated_price=market_price,
            portfolio_value=portfolio_value,
        )

        # ─── Find or create asset ───
        asset_result = await self.db.execute(
            select(Asset).where(Asset.symbol == symbol.upper())
        )
        asset = asset_result.scalar_one_or_none()
        if not asset:
            asset = Asset(
                symbol=symbol.upper(),
                name=symbol.upper(),
                asset_class="equity",
                exchange="NSE",
            )
            self.db.add(asset)
            await self.db.flush()

        # ─── Create Trade Order ───
        trade_order = TradeOrder(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            user_id=self.user.id,
            side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET if order_type.lower() == "market" else OrderType.LIMIT,
            quantity=quantity,
            price=limit_price if order_type.lower() == "limit" else market_price,
            mode=TradingMode.PAPER if mode.lower() == "paper" else TradingMode.LIVE,
            status=OrderStatus.PENDING,
            symbol=symbol.upper(),
            exchange="NSE",
        )
        self.db.add(trade_order)
        await self.db.flush()

        # ─── Execute ───
        try:
            if mode.lower() == "paper":
                trade_order = await self.paper_trader.execute_order(trade_order, market_price)
            elif mode.lower() == "live":
                trade_order = await self._execute_live(trade_order)
            else:
                raise TradingEngineError(f"Invalid trading mode: {mode}")

        except Exception as e:
            trade_order.status = OrderStatus.FAILED
            trade_order.error_message = str(e)
            logger.error(f"Trade execution failed: {e}")

        # ─── Update Circuit Breaker ───
        await self._update_circuit_breaker(trade_order)

        await self.db.flush()

        return {
            "order_id": trade_order.id,
            "symbol": trade_order.symbol,
            "side": trade_order.side.value,
            "quantity": trade_order.quantity,
            "price": trade_order.filled_price or market_price,
            "total_value": trade_order.total_value or 0,
            "status": trade_order.status.value,
            "mode": trade_order.mode.value,
            "broker_order_id": trade_order.broker_order_id,
            "brokerage_fee": trade_order.brokerage_fee or 0,
            "error": trade_order.error_message,
            "risk_validation": validation,
        }

    async def _execute_live(self, trade_order: TradeOrder) -> TradeOrder:
        """Execute a trade via Angel One SmartAPI."""
        broker = await self._get_broker()

        trade_order.status = OrderStatus.PLACED
        trade_order.placed_at = datetime.now()

        response = await broker.place_order(
            symbol=f"{trade_order.symbol}-EQ",
            quantity=int(trade_order.quantity),
            side=trade_order.side.value.upper(),
            order_type=trade_order.order_type.value.upper(),
            price=trade_order.price if trade_order.order_type == OrderType.LIMIT else None,
        )

        trade_order.broker_order_id = response.get("order_id", "")

        # Check status
        if response.get("status") == "placed":
            status = await broker.get_order_status(trade_order.broker_order_id)
            if status.get("status") == "complete":
                trade_order.status = OrderStatus.FILLED
                trade_order.filled_price = status.get("avg_price", trade_order.price)
                trade_order.total_value = trade_order.quantity * trade_order.filled_price
                trade_order.executed_at = datetime.now()
                trade_order.brokerage_fee = 20.0  # Flat fee
            else:
                trade_order.status = OrderStatus.PLACED

        return trade_order

    async def _get_prices(self, symbols: list[str], mode: str) -> dict:
        """Get current prices for symbols."""
        prices = {}

        if mode == "live":
            try:
                broker = await self._get_broker()
                prices = await broker.get_ltp(symbols)
            except BrokerAuthError:
                logger.warning("Broker not available, falling back to yfinance")

        # Fallback: use yfinance for paper mode or if broker fails
        if not prices:
            try:
                import yfinance as yf
                for symbol in symbols:
                    ticker = yf.Ticker(f"{symbol}.NS")
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        prices[symbol] = float(hist["Close"].iloc[-1])
                    else:
                        prices[symbol] = 0.0
            except Exception as e:
                logger.warning(f"yfinance price fetch failed: {e}")
                # Last resort: placeholder price
                for symbol in symbols:
                    if symbol not in prices:
                        prices[symbol] = 0.0

        return prices

    async def _update_circuit_breaker(self, trade_order: TradeOrder):
        """Update daily trading stats for circuit breaker."""
        from sqlalchemy import func as sa_func

        today = datetime.now().date()

        result = await self.db.execute(
            select(TradingCircuitBreaker).where(
                TradingCircuitBreaker.user_id == self.user.id,
                sa_func.date(TradingCircuitBreaker.date) == today,
            )
        )
        cb = result.scalar_one_or_none()

        if not cb:
            cb = TradingCircuitBreaker(
                user_id=self.user.id,
                date=datetime.now(),
            )
            self.db.add(cb)

        cb.trades_today += 1

        if trade_order.status == OrderStatus.FILLED and trade_order.total_value:
            if trade_order.side == OrderSide.SELL:
                # Approximate P&L (simplified)
                cb.daily_pnl += trade_order.total_value - (trade_order.brokerage_fee or 0)
            else:
                cb.daily_pnl -= trade_order.total_value + (trade_order.brokerage_fee or 0)

    async def get_order_history(
        self,
        portfolio_id: int,
        limit: int = 50,
    ) -> list[dict]:
        """Get trade order history for a portfolio."""
        result = await self.db.execute(
            select(TradeOrder)
            .where(
                TradeOrder.portfolio_id == portfolio_id,
                TradeOrder.user_id == self.user.id,
            )
            .order_by(TradeOrder.created_at.desc())
            .limit(limit)
        )
        orders = result.scalars().all()

        return [
            {
                "id": o.id,
                "symbol": o.symbol,
                "side": o.side.value,
                "quantity": o.quantity,
                "price": o.filled_price or o.price,
                "total_value": o.total_value or 0,
                "status": o.status.value,
                "mode": o.mode.value,
                "broker_order_id": o.broker_order_id,
                "brokerage_fee": o.brokerage_fee or 0,
                "error": o.error_message,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "executed_at": o.executed_at.isoformat() if o.executed_at else None,
            }
            for o in orders
        ]
