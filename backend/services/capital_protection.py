"""
FinVoice — Capital Protection Engine
Manages the "invest ₹1L, risk only ₹20K" strategy.

How it works:
    1. User deposits ₹1,00,000 total
    2. They choose to risk ₹20,000 (the "risk budget")
    3. ₹80,000 is locked as protected capital — NEVER used for trading
    4. The engine trades ONLY with the ₹20,000 risk pool
    5. When trades make profit:
       - 70% of profit goes BACK into the risk pool (compound growth)
       - 30% of profit moves to protected capital (lock in gains)
    6. If risk pool drops below the floor (₹5,000), ALL trading stops
    7. Once target profit is hit, the plan auto-completes

This is inspired by CPPI (Constant Proportion Portfolio Insurance)
but simplified for retail Indian investors.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.smart_plan import SmartInvestmentPlan, PlanStatus

logger = logging.getLogger(__name__)


class CapitalProtectionError(Exception):
    """Raised when a trade violates capital protection rules."""
    pass


class CapitalProtectionEngine:
    """
    Manages the capital split and enforces protection rules.

    Key rules:
    - Protected capital is NEVER used for trades
    - Risk pool starts at user-defined amount
    - Profits compound into risk pool (configurable %)
    - Floor stops all trading if risk pool drops too low
    - Each trade limited to max % of current risk pool
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_plan(
        self,
        user_id: int,
        portfolio_id: int,
        total_investment: float,
        risk_amount: float,
        risk_floor_pct: float = 25.0,
        profit_reinvest_pct: float = 70.0,
        max_single_trade_pct: float = 20.0,
        target_profit: float = None,
        target_multiplier: float = None,
    ) -> SmartInvestmentPlan:
        """
        Create a new capital-protected investment plan.

        Args:
            total_investment: Total money (e.g., ₹1,00,000)
            risk_amount: How much to risk (e.g., ₹20,000)
            risk_floor_pct: Stop if risk capital drops below this % (default 25% = ₹5,000)
            profit_reinvest_pct: % of profits to reinvest (default 70%)
            max_single_trade_pct: Max % of risk pool per trade (default 20%)
            target_profit: Optional profit target to auto-complete
            target_multiplier: Optional (e.g., 2.0 = double the risk capital)
        """
        if risk_amount >= total_investment:
            raise CapitalProtectionError(
                "Risk amount must be less than total investment. "
                "The whole point is to protect some of your money!"
            )

        if risk_amount <= 0:
            raise CapitalProtectionError("Risk amount must be greater than zero.")

        protected = total_investment - risk_amount
        floor = risk_amount * (risk_floor_pct / 100)

        # Calculate target if multiplier given
        if target_multiplier and not target_profit:
            target_profit = risk_amount * (target_multiplier - 1)

        plan = SmartInvestmentPlan(
            user_id=user_id,
            portfolio_id=portfolio_id,
            total_investment=total_investment,
            protected_capital=protected,
            initial_risk_capital=risk_amount,
            current_risk_capital=risk_amount,
            risk_floor=floor,
            risk_floor_pct=risk_floor_pct,
            max_single_trade_pct=max_single_trade_pct,
            profit_reinvest_pct=profit_reinvest_pct,
            target_profit=target_profit,
            target_multiplier=target_multiplier,
            status=PlanStatus.ACTIVE,
        )

        self.db.add(plan)
        await self.db.flush()

        logger.info(
            f"Created Smart Plan for user {user_id}: "
            f"Total ₹{total_investment:,.0f} | "
            f"Protected ₹{protected:,.0f} | "
            f"Risk ₹{risk_amount:,.0f} | "
            f"Floor ₹{floor:,.0f}"
        )

        return plan

    async def get_plan(self, user_id: int, plan_id: int = None) -> Optional[SmartInvestmentPlan]:
        """Get user's active plan (or specific plan by ID)."""
        if plan_id:
            result = await self.db.execute(
                select(SmartInvestmentPlan).where(
                    SmartInvestmentPlan.id == plan_id,
                    SmartInvestmentPlan.user_id == user_id,
                )
            )
        else:
            result = await self.db.execute(
                select(SmartInvestmentPlan).where(
                    SmartInvestmentPlan.user_id == user_id,
                    SmartInvestmentPlan.status == PlanStatus.ACTIVE,
                ).order_by(SmartInvestmentPlan.created_at.desc())
            )
        return result.scalar_one_or_none()

    async def validate_trade(self, plan: SmartInvestmentPlan, trade_amount: float) -> dict:
        """
        Check if a trade is allowed under the capital protection rules.

        Returns: {allowed: bool, reason: str, available: float}
        """
        # Check if plan is active
        if plan.status != PlanStatus.ACTIVE:
            return {
                "allowed": False,
                "reason": f"Your investment plan is {plan.status.value}. "
                          f"{'Reason: ' + plan.halt_reason if plan.halt_reason else ''}",
                "available": 0,
            }

        # Check floor
        if plan.current_risk_capital <= plan.risk_floor:
            plan.status = PlanStatus.STOPPED
            plan.halt_reason = (
                f"Risk capital ₹{plan.current_risk_capital:,.0f} hit the safety floor "
                f"of ₹{plan.risk_floor:,.0f}. Trading stopped to protect your money."
            )
            await self.db.flush()

            return {
                "allowed": False,
                "reason": (
                    f"🛑 Safety floor triggered! Your risk pool has dropped to "
                    f"₹{plan.current_risk_capital:,.0f}, which is at or below your safety floor "
                    f"of ₹{plan.risk_floor:,.0f}. Trading has been automatically stopped "
                    f"to prevent further losses. Your ₹{plan.protected_capital:,.0f} "
                    f"protected capital is completely safe."
                ),
                "available": 0,
            }

        # Check max trade size
        max_trade = plan.current_risk_capital * (plan.max_single_trade_pct / 100)
        if trade_amount > max_trade:
            return {
                "allowed": False,
                "reason": (
                    f"This trade (₹{trade_amount:,.0f}) is too large. "
                    f"Your risk pool is ₹{plan.current_risk_capital:,.0f} and each trade "
                    f"can use at most {plan.max_single_trade_pct:.0f}% of it "
                    f"(= ₹{max_trade:,.0f}). This prevents one bad trade from wiping out "
                    f"your entire risk budget."
                ),
                "available": max_trade,
            }

        # Check if enough capital
        if trade_amount > plan.current_risk_capital:
            return {
                "allowed": False,
                "reason": (
                    f"Not enough risk capital. You have ₹{plan.current_risk_capital:,.0f} "
                    f"available for trading but this trade needs ₹{trade_amount:,.0f}. "
                    f"Your ₹{plan.protected_capital:,.0f} protected capital cannot be used."
                ),
                "available": plan.current_risk_capital,
            }

        return {
            "allowed": True,
            "reason": "Trade approved within risk budget.",
            "available": plan.current_risk_capital,
            "max_trade_size": max_trade,
            "remaining_after": plan.current_risk_capital - trade_amount,
            "floor_distance": plan.current_risk_capital - plan.risk_floor,
        }

    async def record_trade_result(
        self, plan: SmartInvestmentPlan, pnl: float, trade_amount: float
    ) -> dict:
        """
        Update the plan after a trade completes.

        Args:
            plan: The SmartInvestmentPlan
            pnl: Profit/loss from this trade (positive = profit, negative = loss)
            trade_amount: How much was used for this trade

        Returns:
            dict with updated balances and explanation
        """
        plan.total_trades += 1
        plan.last_trade_at = datetime.now()

        if pnl > 0:
            # ─── PROFIT: Split between risk pool and protected ───
            plan.winning_trades += 1
            reinvest_amount = pnl * (plan.profit_reinvest_pct / 100)
            protect_amount = pnl - reinvest_amount

            plan.current_risk_capital += reinvest_amount
            plan.protected_capital += protect_amount
            plan.total_profit += pnl
            plan.profit_reinvested += reinvest_amount

            explanation = (
                f"✅ Trade made a profit of ₹{pnl:,.0f}! Here's how we split it:\n"
                f"• ₹{reinvest_amount:,.0f} ({plan.profit_reinvest_pct:.0f}%) → "
                f"added to your trading pool (now ₹{plan.current_risk_capital:,.0f})\n"
                f"• ₹{protect_amount:,.0f} ({100 - plan.profit_reinvest_pct:.0f}%) → "
                f"moved to protected capital (now ₹{plan.protected_capital:,.0f})\n"
                f"Your trading power is growing while we lock in gains!"
            )

        elif pnl < 0:
            # ─── LOSS: Deduct from risk pool only ───
            plan.losing_trades += 1
            plan.current_risk_capital += pnl  # pnl is negative

            explanation = (
                f"📉 Trade had a loss of ₹{abs(pnl):,.0f}. "
                f"This comes from your risk pool only.\n"
                f"• Risk pool: ₹{plan.current_risk_capital:,.0f} "
                f"(₹{plan.current_risk_capital - plan.risk_floor:,.0f} above safety floor)\n"
                f"• Protected capital: ₹{plan.protected_capital:,.0f} — completely untouched ✓\n"
                f"Your protected money is safe."
            )

            # Check if we hit the floor
            if plan.current_risk_capital <= plan.risk_floor:
                plan.status = PlanStatus.STOPPED
                plan.halt_reason = (
                    f"Risk capital ₹{plan.current_risk_capital:,.0f} dropped to safety floor."
                )
                explanation += (
                    f"\n\n🛑 Safety floor reached! Trading is now paused. "
                    f"Your ₹{plan.protected_capital:,.0f} protected capital is safe."
                )

        else:
            explanation = "Trade broke even. No change to your balances."

        # Check if target reached
        if plan.target_profit and plan.total_profit >= plan.target_profit:
            plan.status = PlanStatus.COMPLETED
            explanation += (
                f"\n\n🎉 Congratulations! You've hit your profit target of "
                f"₹{plan.target_profit:,.0f}! Total profit: ₹{plan.total_profit:,.0f}."
            )

        await self.db.flush()

        return {
            "pnl": round(pnl, 2),
            "explanation": explanation,
            "risk_capital": round(plan.current_risk_capital, 2),
            "protected_capital": round(plan.protected_capital, 2),
            "total_value": round(plan.current_risk_capital + plan.protected_capital, 2),
            "total_profit": round(plan.total_profit, 2),
            "win_rate": round(
                plan.winning_trades / max(plan.total_trades, 1) * 100, 1
            ),
            "status": plan.status.value,
        }

    async def get_plan_summary(self, plan: SmartInvestmentPlan) -> dict:
        """Get a comprehensive summary of the plan's current state."""
        initial_total = plan.total_investment
        current_total = plan.current_risk_capital + plan.protected_capital
        overall_return = ((current_total - initial_total) / initial_total * 100) if initial_total > 0 else 0

        risk_used_pct = (
            (plan.initial_risk_capital - plan.current_risk_capital) / plan.initial_risk_capital * 100
        ) if plan.initial_risk_capital > 0 else 0

        risk_growth = (
            (plan.current_risk_capital - plan.initial_risk_capital) / plan.initial_risk_capital * 100
        ) if plan.initial_risk_capital > 0 else 0

        floor_distance = plan.current_risk_capital - plan.risk_floor
        floor_distance_pct = (floor_distance / plan.initial_risk_capital * 100) if plan.initial_risk_capital > 0 else 0

        # Progress towards target
        target_progress = None
        if plan.target_profit and plan.target_profit > 0:
            target_progress = round(plan.total_profit / plan.target_profit * 100, 1)

        return {
            "plan_id": plan.id,
            "status": plan.status.value,

            # Capital overview
            "total_investment": round(plan.total_investment, 2),
            "current_total_value": round(current_total, 2),
            "overall_return_pct": round(overall_return, 2),

            # Protected capital (safe money)
            "protected_capital": {
                "amount": round(plan.protected_capital, 2),
                "original": round(plan.total_investment - plan.initial_risk_capital, 2),
                "gains_locked": round(
                    plan.protected_capital - (plan.total_investment - plan.initial_risk_capital), 2
                ),
                "description": (
                    f"₹{plan.protected_capital:,.0f} is fully protected and never used for trading. "
                    f"This includes your original ₹{plan.total_investment - plan.initial_risk_capital:,.0f} "
                    f"plus ₹{max(0, plan.protected_capital - (plan.total_investment - plan.initial_risk_capital)):,.0f} "
                    f"in locked profits."
                ),
            },

            # Risk capital (trading pool)
            "risk_capital": {
                "current": round(plan.current_risk_capital, 2),
                "initial": round(plan.initial_risk_capital, 2),
                "growth_pct": round(risk_growth, 2),
                "floor": round(plan.risk_floor, 2),
                "distance_to_floor": round(floor_distance, 2),
                "description": (
                    f"You started with ₹{plan.initial_risk_capital:,.0f} in your trading pool. "
                    f"It's now ₹{plan.current_risk_capital:,.0f} "
                    f"({'up' if risk_growth >= 0 else 'down'} {abs(risk_growth):.1f}%). "
                    f"Trading will pause if it drops below ₹{plan.risk_floor:,.0f}."
                ),
            },

            # Performance
            "performance": {
                "total_profit": round(plan.total_profit, 2),
                "profit_reinvested": round(plan.profit_reinvested, 2),
                "total_trades": plan.total_trades,
                "winning_trades": plan.winning_trades,
                "losing_trades": plan.losing_trades,
                "win_rate": round(
                    plan.winning_trades / max(plan.total_trades, 1) * 100, 1
                ),
            },

            # Target
            "target": {
                "profit_target": plan.target_profit,
                "multiplier": plan.target_multiplier,
                "progress_pct": target_progress,
            } if plan.target_profit else None,

            # Safety
            "safety": {
                "risk_floor": round(plan.risk_floor, 2),
                "floor_distance": round(floor_distance, 2),
                "floor_distance_pct": round(floor_distance_pct, 1),
                "max_trade_size": round(
                    plan.current_risk_capital * (plan.max_single_trade_pct / 100), 2
                ),
                "max_trade_pct": plan.max_single_trade_pct,
                "profit_reinvest_pct": plan.profit_reinvest_pct,
                "halt_reason": plan.halt_reason,
            },
        }

    async def pause_plan(self, plan: SmartInvestmentPlan) -> dict:
        """Pause trading on this plan."""
        plan.status = PlanStatus.PAUSED
        plan.halt_reason = "Manually paused by user"
        await self.db.flush()
        return {"status": "paused", "message": "Trading paused. Your capital is preserved."}

    async def resume_plan(self, plan: SmartInvestmentPlan) -> dict:
        """Resume a paused plan."""
        if plan.status == PlanStatus.STOPPED and plan.current_risk_capital <= plan.risk_floor:
            return {
                "status": "stopped",
                "message": (
                    f"Cannot resume — risk capital (₹{plan.current_risk_capital:,.0f}) "
                    f"is at or below the safety floor (₹{plan.risk_floor:,.0f}). "
                    f"You would need to add more risk capital first."
                ),
            }

        plan.status = PlanStatus.ACTIVE
        plan.halt_reason = None
        await self.db.flush()
        return {"status": "active", "message": "Trading resumed!"}

    async def add_risk_capital(self, plan: SmartInvestmentPlan, amount: float) -> dict:
        """Add more money to the risk pool (to resume after floor hit)."""
        plan.current_risk_capital += amount
        plan.total_investment += amount
        if plan.status == PlanStatus.STOPPED:
            plan.status = PlanStatus.ACTIVE
            plan.halt_reason = None
        await self.db.flush()

        return {
            "added": amount,
            "new_risk_capital": round(plan.current_risk_capital, 2),
            "status": plan.status.value,
            "message": f"Added ₹{amount:,.0f} to your trading pool. New balance: ₹{plan.current_risk_capital:,.0f}.",
        }
