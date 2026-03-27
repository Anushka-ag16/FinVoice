"""
FinVoice — Holdings Analyzer Service
Exposure engine, concentration risk, correlation, beta, and LP-based rebalancing.
"""

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Portfolio, Holding, Asset, Price, UserTier
from schemas.portfolio import (
    HoldingsAnalysisResponse, ExposureBreakdown, ConcentrationAlert,
    CorrelationPair,
)

SEBI_DISCLAIMER = (
    "FinVoice is a decision-support tool. Invest at your own risk. "
    "Consult a SEBI-registered advisor for personalized advice."
)


class HoldingsAnalyzerService:
    def __init__(self, db: AsyncSession, user_tier: str = "free"):
        self.db = db
        self.user_tier = user_tier

    async def analyze(self, portfolio: Portfolio) -> HoldingsAnalysisResponse:
        """Full holdings analysis."""
        # Load holdings with asset data
        result = await self.db.execute(
            select(Holding, Asset)
            .join(Asset, Holding.asset_id == Asset.id)
            .where(Holding.portfolio_id == portfolio.id)
        )
        rows = result.all()

        if not rows:
            return HoldingsAnalysisResponse(
                portfolio_id=portfolio.id,
                exposure=ExposureBreakdown(by_sector={}, by_asset_class={}, by_market_cap={}),
                concentration_alerts=[],
                correlated_pairs=[],
                portfolio_beta=1.0,
                rebalancing_suggestions=[],
                disclaimer=SEBI_DISCLAIMER,
            )

        holdings_data = []
        total_value = 0.0

        for holding, asset in rows:
            price = holding.current_price or holding.buy_price
            value = holding.quantity * price
            total_value += value
            holdings_data.append({
                "holding": holding,
                "asset": asset,
                "value": value,
                "price": price,
            })

        # ─── Exposure Breakdown ───
        by_sector = {}
        by_asset_class = {}
        by_market_cap = {}

        for item in holdings_data:
            asset = item["asset"]
            weight = (item["value"] / total_value * 100) if total_value > 0 else 0

            sector = asset.sector or "Unknown"
            by_sector[sector] = by_sector.get(sector, 0) + weight

            ac = asset.asset_class.value if hasattr(asset.asset_class, 'value') else str(asset.asset_class)
            by_asset_class[ac] = by_asset_class.get(ac, 0) + weight

            cap = asset.market_cap_tier
            if cap:
                cap_str = cap.value if hasattr(cap, 'value') else str(cap)
                by_market_cap[cap_str] = by_market_cap.get(cap_str, 0) + weight

        exposure = ExposureBreakdown(
            by_sector=by_sector,
            by_asset_class=by_asset_class,
            by_market_cap=by_market_cap,
        )

        # ─── Concentration Risk ───
        concentration_alerts = []

        for item in holdings_data:
            weight = (item["value"] / total_value * 100) if total_value > 0 else 0
            # Single stock > 20%
            if weight > 20:
                concentration_alerts.append(ConcentrationAlert(
                    alert_type="single_stock",
                    name=item["asset"].symbol,
                    weight_pct=round(weight, 2),
                    threshold_pct=20.0,
                    severity="alert",
                ))

        for sector, weight in by_sector.items():
            if weight > 35:
                concentration_alerts.append(ConcentrationAlert(
                    alert_type="sector",
                    name=sector,
                    weight_pct=round(weight, 2),
                    threshold_pct=35.0,
                    severity="alert" if weight > 50 else "warn",
                ))

        # ─── Correlation Analysis (simplified — uses returns if available) ───
        correlated_pairs = []
        # In full implementation, compute 1-year rolling correlations from price data
        # For now, flag same-sector holdings as potentially correlated
        sector_holdings = {}
        for item in holdings_data:
            sector = item["asset"].sector or "Unknown"
            sector_holdings.setdefault(sector, []).append(item["asset"].symbol)

        for sector, symbols in sector_holdings.items():
            if len(symbols) >= 2:
                for i in range(len(symbols)):
                    for j in range(i + 1, len(symbols)):
                        correlated_pairs.append(CorrelationPair(
                            stock_a=symbols[i],
                            stock_b=symbols[j],
                            correlation=0.7,  # Placeholder — compute from actual price data
                            note=f"Same sector ({sector}) — typically correlated. Verify with price data.",
                        ))

        # ─── Portfolio Beta (approximation) ───
        portfolio_beta = 1.0  # Placeholder — compute from weighted asset betas

        beta_alert = None
        # Check if beta is too high for moderate risk user
        if portfolio_beta > 1.3:
            beta_alert = (
                f"Portfolio beta ({portfolio_beta:.2f}) is high for a moderate risk profile. "
                "Consider adding low-beta assets like bonds or gold."
            )

        # ─── Rebalancing Suggestions ───
        rebalancing_suggestions = []
        if self.user_tier == UserTier.PAID or self.user_tier == "paid":
            # For paid users: compute LP-based rupee rebalancing
            # Placeholder: suggest proportional rebalancing
            target_per_asset = total_value / len(holdings_data) if holdings_data else 0
            for item in holdings_data:
                diff = target_per_asset - item["value"]
                if abs(diff) > total_value * 0.02:  # Only suggest if > 2% deviation
                    action = "Buy" if diff > 0 else "Sell"
                    rebalancing_suggestions.append({
                        "symbol": item["asset"].symbol,
                        "action": action,
                        "amount_inr": round(abs(diff), 2),
                        "reason": f"Rebalance to target equal-weight allocation",
                    })
        else:
            # Free tier: general direction only
            for alert in concentration_alerts:
                if alert.alert_type == "single_stock":
                    rebalancing_suggestions.append({
                        "direction": f"Reduce exposure to {alert.name}",
                        "reason": f"{alert.name} is {alert.weight_pct:.1f}% of portfolio (>20% threshold)",
                    })

        return HoldingsAnalysisResponse(
            portfolio_id=portfolio.id,
            exposure=exposure,
            concentration_alerts=concentration_alerts,
            correlated_pairs=correlated_pairs,
            portfolio_beta=portfolio_beta,
            beta_alert=beta_alert,
            rebalancing_suggestions=rebalancing_suggestions,
            disclaimer=SEBI_DISCLAIMER,
        )
