"""
FinVoice — Portfolio API (Import, Analysis, Drift).
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import csv
import io

from database import get_db
from models import User, Portfolio, Holding, Asset
from schemas.portfolio import (
    PortfolioImportRequest, PortfolioResponse, HoldingResponse,
    HoldingsAnalysisResponse, DriftAlertResponse,
)
from services.holdings_analyzer import HoldingsAnalyzerService
from services.drift_detector import DriftDetectorService
from api.auth import get_current_user

router = APIRouter()

SEBI_DISCLAIMER = (
    "FinVoice is a decision-support tool. Invest at your own risk. "
    "Consult a SEBI-registered advisor for personalized advice."
)


@router.post("/import", response_model=PortfolioResponse)
async def import_portfolio(
    request: PortfolioImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mandatory portfolio import — user must provide their current holdings.
    This is required before any analysis or recommendations.
    """
    # Create portfolio
    portfolio = Portfolio(
        user_id=current_user.id,
        name=request.portfolio_name,
    )
    db.add(portfolio)
    await db.flush()

    total_invested = 0.0
    holdings_response = []

    for h in request.holdings:
        # Find or create asset
        result = await db.execute(select(Asset).where(Asset.symbol == h.symbol.upper()))
        asset = result.scalar_one_or_none()

        if not asset:
            # Create basic asset record — details filled by data pipeline later
            asset = Asset(
                symbol=h.symbol.upper(),
                name=h.symbol.upper(),
                asset_class="equity",
                exchange="NSE",
            )
            db.add(asset)
            await db.flush()

        holding = Holding(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            quantity=h.quantity,
            buy_price=h.buy_price,
        )
        db.add(holding)

        invested = h.quantity * h.buy_price
        total_invested += invested

        holdings_response.append(HoldingResponse(
            symbol=asset.symbol,
            name=asset.name,
            asset_class=asset.asset_class.value if hasattr(asset.asset_class, 'value') else str(asset.asset_class),
            sector=asset.sector,
            quantity=h.quantity,
            buy_price=h.buy_price,
            current_price=None,
            current_value=None,
            pnl=None,
            pnl_pct=None,
            weight_pct=round((invested / total_invested * 100) if total_invested > 0 else 0, 2),
        ))

    portfolio.total_invested = total_invested
    current_user.onboarding_complete = True

    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        total_invested=total_invested,
        current_value=total_invested,  # Will be updated by price feed
        total_pnl=0.0,
        total_pnl_pct=0.0,
        holdings=holdings_response,
        created_at=portfolio.created_at,
    )


@router.post("/import-csv")
async def import_portfolio_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import portfolio from CSV file. Columns: symbol, quantity, buy_price."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    holdings = []
    for row in reader:
        holdings.append({
            "symbol": row.get("symbol", "").strip(),
            "quantity": float(row.get("quantity", 0)),
            "buy_price": float(row.get("buy_price", 0)),
        })

    if not holdings:
        raise HTTPException(status_code=400, detail="CSV file is empty or invalid")

    from schemas.portfolio import HoldingInput
    request = PortfolioImportRequest(
        holdings=[HoldingInput(**h) for h in holdings],
        portfolio_name="Imported Portfolio",
    )
    return await import_portfolio(request, current_user, db)


@router.post("/analyze", response_model=HoldingsAnalysisResponse)
async def analyze_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full holdings analysis: exposure, concentration, correlation, beta, rebalancing.
    Free tier: basic asset class breakdown.
    Paid tier: full stock-level analysis with rupee rebalancing.
    """
    # Verify ownership
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    analyzer = HoldingsAnalyzerService(db, current_user.tier)
    analysis = await analyzer.analyze(portfolio)
    return analysis


@router.get("/drift", response_model=list[DriftAlertResponse])
async def get_drift_alerts(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current drift alerts for a portfolio."""
    detector = DriftDetectorService(db)
    alerts = await detector.get_alerts(portfolio_id, current_user.id)
    return alerts
