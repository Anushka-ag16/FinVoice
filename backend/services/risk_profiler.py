"""
FinVoice — Risk Profiler Service
Adaptive questionnaire scoring, risk score computation, and dynamic re-scoring.
"""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import RiskProfile, User, BehavioralSignal, InvestorType, BehavioralBiasType


class RiskProfilerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_risk_profile(self, user: User, submission) -> RiskProfile:
        """Compute risk score from adaptive questionnaire responses."""
        s1 = submission.stage1
        s2 = submission.stage2

        # ─── Base Score (0-100) from Stage 1 ───
        base_score = 50.0

        # Age factor: younger = more risk tolerance
        if s1.age < 30:
            base_score += 15
        elif s1.age < 40:
            base_score += 10
        elif s1.age < 50:
            base_score += 0
        elif s1.age < 60:
            base_score -= 10
        else:
            base_score -= 20

        # Income factor
        income_map = {"0-3L": -10, "3-7L": -5, "7-15L": 5, "15-30L": 10, "30L+": 15}
        base_score += income_map.get(s1.income_range, 0)

        # Goal factor
        goal_map = {"wealth_growth": 10, "retirement": 0, "education": -5, "emergency": -15}
        base_score += goal_map.get(s1.investment_goal, 0)

        # Time horizon
        if s1.time_horizon_years >= 10:
            base_score += 10
        elif s1.time_horizon_years >= 5:
            base_score += 5
        elif s1.time_horizon_years >= 3:
            base_score -= 5
        else:
            base_score -= 15

        # ─── Behavioral Score from Stage 2 ───
        loss_map = {"sell_everything": -20, "sell_partial": -10, "hold": 5, "buy_more": 15}
        base_score += loss_map.get(s2.loss_reaction, 0)

        experience_map = {"none": -10, "<1yr": -5, "1-3yr": 0, "3-5yr": 5, "5yr+": 10}
        base_score += experience_map.get(s2.past_investment_experience, 0)

        # ─── Behavioral Bias Detection ───
        if s2.loss_reaction in ("sell_everything", "sell_partial"):
            bias = BehavioralBiasType.LOSS_AVERSE
        elif s2.loss_reaction == "buy_more" and s2.past_investment_experience in ("none", "<1yr"):
            bias = BehavioralBiasType.OVERCONFIDENT
        else:
            bias = BehavioralBiasType.BALANCED

        # ─── Stage 3 Adjustments ───
        if submission.stage3_experienced:
            s3 = submission.stage3_experienced
            if s3.knows_derivatives:
                base_score += 5
            if s3.uses_leverage:
                base_score += 10
            if s3.sector_concentration_okay:
                base_score += 5
        elif submission.stage3_beginner:
            s3 = submission.stage3_beginner
            if s3.savings_habit == "none":
                base_score -= 10
            if s3.emergency_fund_months < 3:
                base_score -= 10
            if s3.loan_obligations == "high":
                base_score -= 15

        # Clamp to 0-100
        risk_score = max(0.0, min(100.0, base_score))

        # ─── Investor Type Classification ───
        if risk_score < 35:
            investor_type = InvestorType.BEGINNER
        elif risk_score < 65:
            investor_type = InvestorType.INTERMEDIATE
        else:
            investor_type = InvestorType.EXPERIENCED

        # ─── Save/Update Profile ───
        result = await self.db.execute(
            select(RiskProfile).where(RiskProfile.user_id == user.id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            profile.risk_score = risk_score
            profile.investor_type = investor_type
            profile.behavioral_bias = bias
            profile.questionnaire_responses = {
                "stage1": submission.stage1.model_dump(),
                "stage2": submission.stage2.model_dump(),
                "stage3_beginner": submission.stage3_beginner.model_dump() if submission.stage3_beginner else None,
                "stage3_experienced": submission.stage3_experienced.model_dump() if submission.stage3_experienced else None,
            }
            profile.age = s1.age
            profile.income_range = s1.income_range
            profile.investment_goal = s1.investment_goal
            profile.time_horizon_years = s1.time_horizon_years
            if submission.stage3_experienced:
                profile.max_acceptable_loss_pct = submission.stage3_experienced.max_acceptable_loss_pct
                profile.tax_bracket = submission.stage3_experienced.tax_bracket
            profile.last_computed = datetime.utcnow()
            profile.next_refresh_due = datetime.utcnow() + timedelta(days=90)
        else:
            profile = RiskProfile(
                user_id=user.id,
                risk_score=risk_score,
                investor_type=investor_type,
                behavioral_bias=bias,
                questionnaire_responses={
                    "stage1": submission.stage1.model_dump(),
                    "stage2": submission.stage2.model_dump(),
                    "stage3_beginner": submission.stage3_beginner.model_dump() if submission.stage3_beginner else None,
                    "stage3_experienced": submission.stage3_experienced.model_dump() if submission.stage3_experienced else None,
                },
                age=s1.age,
                income_range=s1.income_range,
                investment_goal=s1.investment_goal,
                time_horizon_years=s1.time_horizon_years,
                max_acceptable_loss_pct=(
                    submission.stage3_experienced.max_acceptable_loss_pct
                    if submission.stage3_experienced else None
                ),
                tax_bracket=(
                    submission.stage3_experienced.tax_bracket
                    if submission.stage3_experienced else None
                ),
                next_refresh_due=datetime.utcnow() + timedelta(days=90),
            )
            self.db.add(profile)

        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def get_profile(self, user_id: int) -> RiskProfile | None:
        result = await self.db.execute(
            select(RiskProfile).where(RiskProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def refresh_profile(self, user: User) -> RiskProfile:
        """
        Re-evaluate risk profile using behavioral signals.
        Checks: panic sell attempts, frequent checking, etc.
        """
        profile = await self.get_profile(user.id)
        if not profile:
            raise ValueError("No risk profile found. Complete the questionnaire first.")

        # Count recent behavioral signals (last 90 days)
        cutoff = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(BehavioralSignal).where(
                BehavioralSignal.user_id == user.id,
                BehavioralSignal.timestamp >= cutoff,
            )
        )
        signals = result.scalars().all()

        adjustment = 0.0
        for signal in signals:
            if signal.signal_type == "panic_sell":
                adjustment -= 5.0
            elif signal.signal_type == "frequent_check":
                adjustment -= 2.0
            elif signal.signal_type == "held_during_dip":
                adjustment += 3.0
            elif signal.signal_type == "increased_position_dip":
                adjustment += 5.0

        # Cap adjustment
        adjustment = max(-20.0, min(20.0, adjustment))

        profile.behavioral_adjustment = adjustment
        new_score = max(0.0, min(100.0, profile.risk_score + adjustment))
        profile.risk_score = new_score
        profile.last_computed = datetime.utcnow()
        profile.next_refresh_due = datetime.utcnow() + timedelta(days=90)

        # Re-classify
        if new_score < 35:
            profile.investor_type = InvestorType.BEGINNER
        elif new_score < 65:
            profile.investor_type = InvestorType.INTERMEDIATE
        else:
            profile.investor_type = InvestorType.EXPERIENCED

        await self.db.flush()
        return profile
