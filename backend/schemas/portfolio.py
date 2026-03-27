"""
FinVoice — Pydantic schemas for Portfolio operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Portfolio Import ───

class HoldingInput(BaseModel):
    symbol: str
    quantity: float = Field(..., gt=0)
    buy_price: float = Field(..., gt=0)
    buy_date: Optional[str] = None  # ISO date string


class PortfolioImportRequest(BaseModel):
    """Mandatory portfolio import — user must provide current holdings."""
    holdings: list[HoldingInput] = Field(..., min_length=1)
    portfolio_name: str = "My Portfolio"


class HoldingResponse(BaseModel):
    symbol: str
    name: str
    asset_class: str
    sector: Optional[str]
    quantity: float
    buy_price: float
    current_price: Optional[float]
    current_value: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    weight_pct: Optional[float]

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    id: int
    name: str
    total_invested: float
    current_value: float
    total_pnl: float
    total_pnl_pct: float
    holdings: list[HoldingResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Holdings Analysis ───

class ConcentrationAlert(BaseModel):
    alert_type: str  # "single_stock" or "sector"
    name: str
    weight_pct: float
    threshold_pct: float
    severity: str  # "warn" or "alert"


class CorrelationPair(BaseModel):
    stock_a: str
    stock_b: str
    correlation: float
    note: str


class ExposureBreakdown(BaseModel):
    by_sector: dict[str, float]
    by_asset_class: dict[str, float]
    by_market_cap: dict[str, float]


class HoldingsAnalysisResponse(BaseModel):
    portfolio_id: int
    exposure: ExposureBreakdown
    concentration_alerts: list[ConcentrationAlert]
    correlated_pairs: list[CorrelationPair]
    portfolio_beta: float
    beta_alert: Optional[str] = None
    rebalancing_suggestions: list[dict]
    disclaimer: str


# ─── Drift Detection ───

class DriftAlertResponse(BaseModel):
    asset_class: str
    actual_pct: float
    target_pct: float
    drift_pct: float
    severity: str
    created_at: datetime

    model_config = {"from_attributes": True}
