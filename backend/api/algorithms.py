"""
FinVoice — Trading Algorithm API
Exposes custom trading strategies and the algorithm orchestrator.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from api.auth import get_current_user, require_onboarding_complete

router = APIRouter()


# ─── Schemas ───

class RunAlgorithmRequest(BaseModel):
    portfolio_id: int
    strategies: list[str] = Field(
        default=["momentum", "mean_reversion", "sentiment_alpha", "ml_ensemble", "smart_rebalance"],
        description="Which strategies to run. Default: all 5.",
    )
    strategy_configs: dict = Field(
        default={},
        description="Per-strategy parameters, e.g. {\"momentum\": {\"buy_threshold_5d\": 0.02}}",
    )


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = "momentum"
    period: str = "1y"
    config: dict = Field(default={})


# ─── Endpoints ───

@router.get("/strategies")
async def list_strategies():
    """
    List all available trading algorithms with descriptions.
    No login required — informational endpoint.
    """
    from services.trading_algorithms import AlgorithmOrchestrator

    return {
        "strategies": AlgorithmOrchestrator.available_strategies(),
        "description": (
            "FinVoice uses 5 custom trading algorithms. Each analyzes your portfolio "
            "from a different angle, then they vote together. When most strategies "
            "agree on a direction, the signal is stronger."
        ),
    }


@router.post("/run")
async def run_algorithms(
    request: RunAlgorithmRequest,
    current_user: User = Depends(require_onboarding_complete),
    db: AsyncSession = Depends(get_db),
):
    """
    Run selected trading algorithms against your portfolio.
    Returns combined buy/sell/hold signals with explanations.
    """
    from sqlalchemy import select
    from models import Portfolio, Holding, Asset
    from services.trading_algorithms import AlgorithmOrchestrator
    import pandas as pd
    import yfinance as yf

    # Verify portfolio
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == request.portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Load holdings
    result = await db.execute(
        select(Holding, Asset)
        .join(Asset, Holding.asset_id == Asset.id)
        .where(Holding.portfolio_id == portfolio.id)
    )
    rows = result.all()
    if not rows:
        raise HTTPException(status_code=400, detail="No holdings in this portfolio")

    # Build portfolio dict and fetch features
    portfolio_dict = {}
    symbols = []
    total_value = 0

    for holding, asset in rows:
        price = holding.current_price or holding.buy_price
        value = holding.quantity * price
        total_value += value
        symbols.append(asset.symbol)
        portfolio_dict[asset.symbol] = {
            "qty": holding.quantity,
            "buy_price": holding.buy_price,
            "current_price": price,
            "value": value,
        }

    # Compute weights
    for sym in portfolio_dict:
        portfolio_dict[sym]["weight_pct"] = (
            portfolio_dict[sym]["value"] / total_value * 100
        ) if total_value > 0 else 0

    # Fetch market data and compute features
    features_list = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="6mo").reset_index()
            if hist.empty:
                continue

            hist.columns = [c.lower().replace(" ", "_") for c in hist.columns]

            from ml.feature_engineering import FeatureEngineeringPipeline
            pipeline = FeatureEngineeringPipeline()
            features = pipeline.compute_all_features(hist)

            if not features.empty:
                latest = features.iloc[-1].to_dict()
                latest["symbol"] = symbol
                features_list.append(latest)

        except Exception as e:
            features_list.append({"symbol": symbol, "close": 0, "rsi_14": 50})

    features_df = pd.DataFrame(features_list)

    # Run the orchestrator
    orchestrator = AlgorithmOrchestrator(
        strategies=request.strategies,
    )

    result = orchestrator.run_all(
        features_df=features_df,
        portfolio=portfolio_dict,
        strategy_configs=request.strategy_configs,
    )

    return {
        "portfolio_id": request.portfolio_id,
        "total_value": round(total_value, 2),
        **result,
    }


@router.post("/backtest")
async def backtest_strategy(
    request: BacktestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Backtest a single strategy against historical data for a stock.
    Shows what the algorithm would have done in the past.
    """
    import yfinance as yf
    import pandas as pd
    from ml.feature_engineering import FeatureEngineeringPipeline
    from services.trading_algorithms import AlgorithmOrchestrator

    # Fetch historical data
    try:
        ticker = yf.Ticker(f"{request.symbol}.NS")
        hist = ticker.history(period=request.period).reset_index()
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {request.symbol}")

        hist.columns = [c.lower().replace(" ", "_") for c in hist.columns]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch data: {str(e)}")

    # Compute features
    pipeline = FeatureEngineeringPipeline()
    features = pipeline.compute_all_features(hist)

    if features.empty:
        raise HTTPException(status_code=400, detail="Not enough data to compute features")

    # Get strategy
    if request.strategy not in AlgorithmOrchestrator.STRATEGY_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy: {request.strategy}. "
                   f"Available: {list(AlgorithmOrchestrator.STRATEGY_MAP.keys())}",
        )

    strategy_cls = AlgorithmOrchestrator.STRATEGY_MAP[request.strategy]
    strategy = strategy_cls()

    # Run strategy at multiple points (monthly snapshots)
    backtest_results = []
    step = max(len(features) // 12, 1)  # ~12 snapshots

    for i in range(step, len(features), step):
        row = features.iloc[i:i + 1].copy()
        row["symbol"] = request.symbol

        signals = strategy.generate_signals(
            features_df=row,
            portfolio={request.symbol: {"weight_pct": 100}},
            config=request.config,
        )

        if signals:
            s = signals[0]
            price = float(row.iloc[0].get("close", 0))
            date_val = hist.iloc[min(i, len(hist) - 1)].get("date", "")

            backtest_results.append({
                "date": str(date_val)[:10] if date_val else f"Day {i}",
                "price": round(price, 2),
                "action": s.action,
                "strength": round(s.strength, 2),
                "reason": s.reason,
            })

    # Calculate hypothetical P&L
    initial_price = float(features.iloc[step].get("close", 100))
    final_price = float(features.iloc[-1].get("close", initial_price))
    buy_hold_return = ((final_price - initial_price) / initial_price * 100) if initial_price > 0 else 0

    buys = sum(1 for r in backtest_results if r["action"] == "buy")
    sells = sum(1 for r in backtest_results if r["action"] == "sell")

    return {
        "symbol": request.symbol,
        "strategy": request.strategy,
        "period": request.period,
        "snapshots": len(backtest_results),
        "buy_signals": buys,
        "sell_signals": sells,
        "hold_signals": len(backtest_results) - buys - sells,
        "buy_and_hold_return": f"{buy_hold_return:+.1f}%",
        "price_start": round(initial_price, 2),
        "price_end": round(final_price, 2),
        "results": backtest_results,
    }
