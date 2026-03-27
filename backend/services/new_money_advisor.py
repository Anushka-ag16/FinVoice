"""
FinVoice — New Money Advisor Service
Generates 3 investment scenarios: Conservative / Balanced / Aggressive.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User, RiskProfile, UserTier
from schemas.risk import (
    NewInvestmentRequest, NewInvestmentResponse,
    InvestmentScenario, ScenarioAllocation,
)

SEBI_DISCLAIMER = (
    "FinVoice is a decision-support tool. Invest at your own risk. "
    "Consult a SEBI-registered advisor for personalized advice."
)

# Asset recommendations by scenario type
ALLOCATION_TEMPLATES = {
    "conservative": {
        "mix": {"equity_etf": 0.20, "debt_mf": 0.35, "gold_sgb": 0.20, "fd": 0.15, "liquid_fund": 0.10},
        "assets": {
            "equity_etf": {"name": "Nifty 50 ETF", "symbol": "NIFTYBEES.NS", "class": "etf"},
            "debt_mf": {"name": "HDFC Short Term Debt Fund", "symbol": "HDFC_DEBT_MF", "class": "mutual_fund"},
            "gold_sgb": {"name": "Sovereign Gold Bond", "symbol": "SGB", "class": "gold"},
            "fd": {"name": "SBI Fixed Deposit (7.1%)", "symbol": "SBI_FD", "class": "fixed_deposit"},
            "liquid_fund": {"name": "Parag Parikh Liquid Fund", "symbol": "PPFAS_LIQUID", "class": "mutual_fund"},
        },
        "expected_return": 8.5,
        "expected_risk": 6.0,
        "sharpe": 0.9,
    },
    "balanced": {
        "mix": {"equity_etf": 0.35, "flexi_mf": 0.25, "gold_sgb": 0.15, "debt_mf": 0.15, "liquid_fund": 0.10},
        "assets": {
            "equity_etf": {"name": "Nifty 50 ETF", "symbol": "NIFTYBEES.NS", "class": "etf"},
            "flexi_mf": {"name": "PPFAS Flexi Cap Fund", "symbol": "PPFAS_FLEXI", "class": "mutual_fund"},
            "gold_sgb": {"name": "Sovereign Gold Bond", "symbol": "SGB", "class": "gold"},
            "debt_mf": {"name": "ICICI Prudential Bond Fund", "symbol": "ICICI_BOND", "class": "mutual_fund"},
            "liquid_fund": {"name": "Kotak Liquid Fund", "symbol": "KOTAK_LIQUID", "class": "mutual_fund"},
        },
        "expected_return": 12.5,
        "expected_risk": 12.0,
        "sharpe": 1.1,
    },
    "aggressive": {
        "mix": {"equity_etf": 0.40, "midcap_mf": 0.25, "flexi_mf": 0.20, "gold_sgb": 0.10, "liquid_fund": 0.05},
        "assets": {
            "equity_etf": {"name": "Nifty Next 50 ETF", "symbol": "NIFTYNXT50.NS", "class": "etf"},
            "midcap_mf": {"name": "Axis Midcap Fund", "symbol": "AXIS_MIDCAP", "class": "mutual_fund"},
            "flexi_mf": {"name": "PPFAS Flexi Cap Fund", "symbol": "PPFAS_FLEXI", "class": "mutual_fund"},
            "gold_sgb": {"name": "Sovereign Gold Bond", "symbol": "SGB", "class": "gold"},
            "liquid_fund": {"name": "HDFC Liquid Fund", "symbol": "HDFC_LIQUID", "class": "mutual_fund"},
        },
        "expected_return": 16.0,
        "expected_risk": 18.0,
        "sharpe": 1.0,
    },
}


class NewMoneyAdvisorService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user

    async def generate_scenarios(self, request: NewInvestmentRequest) -> NewInvestmentResponse:
        """Generate 3 investment scenarios for the given amount."""
        # Load risk profile
        result = await self.db.execute(
            select(RiskProfile).where(RiskProfile.user_id == self.user.id)
        )
        risk_profile = result.scalar_one_or_none()

        scenarios = []
        for scenario_type in ["conservative", "balanced", "aggressive"]:
            template = ALLOCATION_TEMPLATES[scenario_type]

            allocations = []
            for key, weight in template["mix"].items():
                asset_info = template["assets"][key]
                amount = round(request.amount * weight, 2)
                pct = round(weight * 100, 2)

                rationale = self._generate_rationale(
                    scenario_type, key, weight, risk_profile
                )

                allocations.append(ScenarioAllocation(
                    asset_name=asset_info["name"],
                    asset_class=asset_info["class"],
                    symbol=asset_info["symbol"],
                    amount=amount,
                    percentage=pct,
                    rationale=rationale,
                ))

            explanation = self._generate_scenario_explanation(
                scenario_type, request, risk_profile
            )

            scenarios.append(InvestmentScenario(
                scenario_type=scenario_type,
                expected_return_pct=template["expected_return"],
                expected_risk_pct=template["expected_risk"],
                sharpe_ratio=template["sharpe"],
                allocations=allocations,
                explanation=explanation,
            ))

        return NewInvestmentResponse(
            amount=request.amount,
            risk_profile_used=risk_profile.investor_type.value if risk_profile else "unknown",
            scenarios=scenarios,
            disclaimer=SEBI_DISCLAIMER,
        )

    def _generate_rationale(
        self, scenario_type: str, asset_key: str, weight: float, risk_profile
    ) -> str:
        """Generate per-allocation rationale."""
        rationales = {
            "equity_etf": "Broad market exposure with low expense ratio. Tracks top Indian large-cap stocks.",
            "midcap_mf": "Higher growth potential from mid-cap companies. Suitable for longer horizons.",
            "flexi_mf": "Flexible allocation across market caps. Professional fund management.",
            "debt_mf": "Stable returns with lower volatility. Acts as portfolio ballast.",
            "gold_sgb": "Hedge against inflation and currency depreciation. Government-backed, earns 2.5% interest.",
            "fd": "Capital preservation with guaranteed returns. Ideal for emergency reserves.",
            "liquid_fund": "Near-cash flexibility with slightly better returns than savings account.",
        }
        return rationales.get(asset_key, "Diversification across asset classes.")

    def _generate_scenario_explanation(
        self, scenario_type: str, request: NewInvestmentRequest, risk_profile
    ) -> str:
        """Generate a holistic explanation for the scenario."""
        risk_str = f" (risk score: {risk_profile.risk_score:.0f}/100)" if risk_profile else ""

        explanations = {
            "conservative": (
                f"This conservative allocation prioritizes capital preservation{risk_str}. "
                f"With ₹{request.amount:,.0f} spread across debt, gold, and a small equity component, "
                f"the expected return of ~8.5% p.a. comes with minimal downside risk. "
                f"Best suited for goals within {request.horizon_years} years."
            ),
            "balanced": (
                f"A balanced mix of growth and stability{risk_str}. "
                f"₹{request.amount:,.0f} is split between equity (for long-term growth), "
                f"gold (inflation hedge), and debt (stability). "
                f"Expected ~12.5% p.a. with moderate volatility."
            ),
            "aggressive": (
                f"Maximum growth focus{risk_str}. "
                f"₹{request.amount:,.0f} is heavily tilted toward equity and mid-cap funds. "
                f"Expected ~16% p.a. but with higher short-term volatility. "
                f"Recommended only for {request.horizon_years}+ year horizons."
            ),
        }
        return explanations.get(scenario_type, "")
