"""
FinVoice — Drift Detector Service
Daily portfolio drift check with tiered severity alerts.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import (
    Portfolio, Holding, Asset, TargetAllocation, DriftAlert, DriftSeverity,
)
from schemas.portfolio import DriftAlertResponse


class DriftDetectorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_drift(self, portfolio: Portfolio) -> list[DriftAlert]:
        """
        Compare actual vs target allocation for a portfolio.
        Generates drift alerts with severity levels:
          INFO: 1-3% drift
          WARN: 3-5% drift
          ALERT: >5% drift
        """
        # Load holdings
        result = await self.db.execute(
            select(Holding, Asset)
            .join(Asset, Holding.asset_id == Asset.id)
            .where(Holding.portfolio_id == portfolio.id)
        )
        rows = result.all()

        # Load target allocations
        result = await self.db.execute(
            select(TargetAllocation).where(TargetAllocation.portfolio_id == portfolio.id)
        )
        targets = {t.asset_class: t.target_pct for t in result.scalars().all()}

        if not targets:
            return []

        # Compute actual allocation by asset class
        total_value = 0.0
        class_values = {}
        for holding, asset in rows:
            price = holding.current_price or holding.buy_price
            value = holding.quantity * price
            total_value += value

            ac = asset.asset_class.value if hasattr(asset.asset_class, 'value') else str(asset.asset_class)
            class_values[ac] = class_values.get(ac, 0) + value

        actual_allocation = {}
        for ac, val in class_values.items():
            actual_allocation[ac] = (val / total_value * 100) if total_value > 0 else 0

        # Compare with targets and generate alerts
        alerts = []
        for asset_class, target_pct in targets.items():
            actual_pct = actual_allocation.get(asset_class, 0)
            drift_pct = abs(actual_pct - target_pct)

            if drift_pct < 1.0:
                continue  # No meaningful drift

            if drift_pct > 5.0:
                severity = DriftSeverity.ALERT
            elif drift_pct > 3.0:
                severity = DriftSeverity.WARN
            else:
                severity = DriftSeverity.INFO

            alert = DriftAlert(
                portfolio_id=portfolio.id,
                asset_class=asset_class,
                actual_pct=round(actual_pct, 2),
                target_pct=round(target_pct, 2),
                drift_pct=round(drift_pct, 2),
                severity=severity,
            )
            self.db.add(alert)
            alerts.append(alert)

        await self.db.flush()
        return alerts

    async def get_alerts(
        self, portfolio_id: int, user_id: int
    ) -> list[DriftAlertResponse]:
        """Get current drift alerts for a portfolio."""
        # Verify ownership
        result = await self.db.execute(
            select(Portfolio).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id,
            )
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            return []

        result = await self.db.execute(
            select(DriftAlert)
            .where(DriftAlert.portfolio_id == portfolio_id)
            .order_by(DriftAlert.created_at.desc())
            .limit(20)
        )
        return [
            DriftAlertResponse(
                asset_class=a.asset_class,
                actual_pct=a.actual_pct,
                target_pct=a.target_pct,
                drift_pct=a.drift_pct,
                severity=a.severity.value,
                created_at=a.created_at,
            )
            for a in result.scalars().all()
        ]
