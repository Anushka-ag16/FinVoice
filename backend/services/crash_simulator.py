"""
FinVoice — Crash Simulator Service
Monte Carlo simulation + Historical scenario replay.
"""

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Portfolio, Holding, Asset
from schemas.risk import (
    MonteCarloRequest, MonteCarloResult,
    HistoricalScenarioRequest, HistoricalScenarioResult,
)

# Historical crash data (approximate max drawdown)
HISTORICAL_CRASHES = {
    "2008_crisis": {
        "name": "2008 Global Financial Crisis",
        "nifty_drop": -0.52,  # Nifty dropped ~52%
        "gold_change": 0.25,  # Gold rose ~25%
        "bond_change": -0.05, # Bonds slight drop
        "duration_days": 365,
        "recovery_days": 780,
    },
    "2020_covid": {
        "name": "2020 COVID Crash",
        "nifty_drop": -0.38,  # Nifty dropped ~38%
        "gold_change": 0.28,  # Gold rose ~28%
        "bond_change": 0.02,
        "duration_days": 45,
        "recovery_days": 180,
    },
    "2022_rate_hike": {
        "name": "2022 Rate Hike Cycle",
        "nifty_drop": -0.17,  # Nifty dropped ~17%
        "gold_change": -0.03,
        "bond_change": -0.08,
        "duration_days": 200,
        "recovery_days": 300,
    },
}


class CrashSimulatorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def monte_carlo(
        self, portfolio: Portfolio, request: MonteCarloRequest
    ) -> MonteCarloResult:
        """
        Monte Carlo simulation: generate N portfolio paths using
        Cholesky decomposition of the covariance matrix.
        """
        # Load holdings
        result = await self.db.execute(
            select(Holding, Asset)
            .join(Asset, Holding.asset_id == Asset.id)
            .where(Holding.portfolio_id == portfolio.id)
        )
        rows = result.all()

        if not rows:
            return MonteCarloResult(
                percentile_5th=[], percentile_50th=[], percentile_95th=[],
                max_drawdown=0, probability_of_ruin=0,
            )

        # Calculate portfolio value and weights
        total_value = 0.0
        weights = []
        for holding, asset in rows:
            price = holding.current_price or holding.buy_price
            value = holding.quantity * price
            total_value += value
            weights.append(value)

        weights = np.array(weights) / total_value
        n_assets = len(weights)
        n_sims = request.num_simulations
        n_days = request.horizon_days

        # Use assumed return and volatility parameters
        # In production, these come from the ML model predictions
        daily_return = 0.0004  # ~10% annualized
        daily_vol = 0.015  # ~24% annualized

        # Generate correlated random returns using Cholesky
        # Simplified: assume moderate correlation between assets
        correlation = np.full((n_assets, n_assets), 0.5)
        np.fill_diagonal(correlation, 1.0)
        vol_vec = np.full(n_assets, daily_vol)
        cov = np.outer(vol_vec, vol_vec) * correlation

        try:
            L = np.linalg.cholesky(cov)
        except np.linalg.LinAlgError:
            # If not positive definite, use diagonal
            L = np.diag(vol_vec)

        # Simulate paths
        portfolio_paths = np.zeros((n_sims, n_days))
        portfolio_paths[:, 0] = total_value

        for t in range(1, n_days):
            Z = np.random.standard_normal((n_sims, n_assets))
            correlated_returns = Z @ L.T + daily_return
            portfolio_returns = (correlated_returns * weights).sum(axis=1)
            portfolio_paths[:, t] = portfolio_paths[:, t - 1] * (1 + portfolio_returns)

        # Compute percentiles
        p5 = np.percentile(portfolio_paths, 5, axis=0).tolist()
        p50 = np.percentile(portfolio_paths, 50, axis=0).tolist()
        p95 = np.percentile(portfolio_paths, 95, axis=0).tolist()

        # Max drawdown (across median path)
        median_path = np.percentile(portfolio_paths, 50, axis=0)
        running_max = np.maximum.accumulate(median_path)
        drawdowns = (median_path - running_max) / running_max
        max_drawdown = float(abs(drawdowns.min()))

        # Probability of ruin (portfolio < 50% of initial)
        final_values = portfolio_paths[:, -1]
        ruin_count = (final_values < total_value * 0.5).sum()
        prob_ruin = float(ruin_count / n_sims)

        # Time to recovery (from max drawdown point in median path)
        dd_idx = drawdowns.argmin()
        recovery_days = None
        for i in range(dd_idx, n_days):
            if median_path[i] >= running_max[dd_idx]:
                recovery_days = int(i - dd_idx)
                break

        return MonteCarloResult(
            percentile_5th=[round(v, 2) for v in p5[::max(1, n_days // 50)]],  # Sample 50 points
            percentile_50th=[round(v, 2) for v in p50[::max(1, n_days // 50)]],
            percentile_95th=[round(v, 2) for v in p95[::max(1, n_days // 50)]],
            max_drawdown=round(max_drawdown, 4),
            probability_of_ruin=round(prob_ruin, 4),
            time_to_recovery_days=recovery_days,
        )

    async def historical_replay(
        self, portfolio: Portfolio, request: HistoricalScenarioRequest
    ) -> HistoricalScenarioResult:
        """Apply historical crash returns to user's portfolio."""
        scenario_key = request.scenario

        if scenario_key == "custom" and request.custom_nifty_drop_pct:
            crash_data = {
                "name": f"Custom Scenario: Nifty drops {request.custom_nifty_drop_pct}%",
                "nifty_drop": -abs(request.custom_nifty_drop_pct) / 100,
                "gold_change": 0.10,
                "bond_change": -0.02,
                "duration_days": 90,
                "recovery_days": None,
            }
        elif scenario_key in HISTORICAL_CRASHES:
            crash_data = HISTORICAL_CRASHES[scenario_key]
        else:
            raise ValueError(f"Unknown scenario: {scenario_key}")

        # Load holdings
        result = await self.db.execute(
            select(Holding, Asset)
            .join(Asset, Holding.asset_id == Asset.id)
            .where(Holding.portfolio_id == portfolio.id)
        )
        rows = result.all()

        total_value = 0.0
        asset_impacts = {}

        for holding, asset in rows:
            price = holding.current_price or holding.buy_price
            value = holding.quantity * price
            total_value += value

            # Determine impact based on asset class
            ac = asset.asset_class.value if hasattr(asset.asset_class, 'value') else str(asset.asset_class)
            if ac in ("equity", "etf", "mutual_fund"):
                impact = crash_data["nifty_drop"]
            elif ac == "gold":
                impact = crash_data["gold_change"]
            elif ac in ("bond", "fixed_deposit"):
                impact = crash_data["bond_change"]
            else:
                impact = crash_data["nifty_drop"] * 0.5  # Partial impact

            asset_impacts[asset.symbol] = round(impact * 100, 2)

        # Portfolio impact (weighted)
        portfolio_impact = 0.0
        for holding, asset in rows:
            price = holding.current_price or holding.buy_price
            value = holding.quantity * price
            weight = value / total_value if total_value > 0 else 0
            ac = asset.asset_class.value if hasattr(asset.asset_class, 'value') else str(asset.asset_class)

            if ac in ("equity", "etf", "mutual_fund"):
                portfolio_impact += weight * crash_data["nifty_drop"]
            elif ac == "gold":
                portfolio_impact += weight * crash_data["gold_change"]
            elif ac in ("bond", "fixed_deposit"):
                portfolio_impact += weight * crash_data["bond_change"]
            else:
                portfolio_impact += weight * crash_data["nifty_drop"] * 0.5

        return HistoricalScenarioResult(
            scenario_name=crash_data["name"],
            portfolio_impact_pct=round(portfolio_impact * 100, 2),
            max_drawdown=round(abs(portfolio_impact), 4),
            recovery_days=crash_data.get("recovery_days"),
            asset_impacts=asset_impacts,
        )
