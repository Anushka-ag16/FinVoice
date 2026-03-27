"""
FinVoice — Pydantic schemas for Risk Assessment outputs.
"""

from typing import Optional

from pydantic import BaseModel, Field


class RiskAssessmentRequest(BaseModel):
    portfolio_id: int


class ScenarioAllocation(BaseModel):
    asset_name: str
    asset_class: str
    symbol: str
    amount: float
    percentage: float
    rationale: str


class InvestmentScenario(BaseModel):
    scenario_type: str  # conservative, balanced, aggressive
    expected_return_pct: float
    expected_risk_pct: float
    sharpe_ratio: float
    allocations: list[ScenarioAllocation]
    explanation: str


class NewInvestmentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in INR to invest")
    goal: str = "growth"  # growth, income, preservation
    horizon_years: int = Field(5, ge=1, le=40)
    max_acceptable_loss_pct: float = Field(20.0, ge=0, le=100)


class NewInvestmentResponse(BaseModel):
    amount: float
    risk_profile_used: str
    scenarios: list[InvestmentScenario]  # Always 3: conservative, balanced, aggressive
    disclaimer: str


# ─── Stress Testing ───

class MonteCarloRequest(BaseModel):
    portfolio_id: int
    num_simulations: int = Field(10000, ge=100, le=50000)
    horizon_days: int = Field(252, ge=30, le=1260)  # Default 1 year


class MonteCarloResult(BaseModel):
    percentile_5th: list[float]  # Value at each time step
    percentile_50th: list[float]
    percentile_95th: list[float]
    max_drawdown: float
    probability_of_ruin: float
    time_to_recovery_days: Optional[int] = None


class HistoricalScenarioRequest(BaseModel):
    portfolio_id: int
    scenario: str  # "2008_crisis", "2020_covid", "2022_rate_hike", "custom"
    custom_nifty_drop_pct: Optional[float] = None


class HistoricalScenarioResult(BaseModel):
    scenario_name: str
    portfolio_impact_pct: float
    max_drawdown: float
    recovery_days: Optional[int] = None
    asset_impacts: dict[str, float]  # {symbol: impact_pct}


class StressTestResponse(BaseModel):
    monte_carlo: Optional[MonteCarloResult] = None
    historical_scenarios: Optional[list[HistoricalScenarioResult]] = None
    disclaimer: str

