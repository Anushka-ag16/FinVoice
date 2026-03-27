"""
FinVoice — Daily Drift Detection Task
Runs at 11 PM IST every day via Celery Beat.
"""

import logging

from tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.daily_drift.check_all_portfolios")
def check_all_portfolios():
    """
    Check all active portfolios for allocation drift.
    Generates alerts at severity levels: INFO (1-3%), WARN (3-5%), ALERT (>5%).
    """
    import sys
    import os
    # Ensure backend dir is on the path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from config import get_settings
    from models import Portfolio, User

    settings = get_settings()

    # Use sync DB URL — Celery workers are synchronous
    db_url = settings.database_url_sync
    if "asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")

    engine = create_engine(db_url)

    with Session(engine) as session:
        portfolios = (
            session.query(Portfolio)
            .join(User)
            .filter(User.is_active.is_(True))
            .all()
        )

        logger.info(f"Checking drift for {len(portfolios)} portfolios")

        for portfolio in portfolios:
            try:
                _check_single_portfolio(session, portfolio)
            except Exception as e:
                logger.error(f"Drift check failed for portfolio {portfolio.id}: {e}")

        session.commit()

    logger.info("Daily drift detection complete")


def _check_single_portfolio(session, portfolio):
    """Check drift for a single portfolio (sync version for Celery)."""
    from models import Holding, Asset, TargetAllocation, DriftAlert, DriftSeverity

    holdings = (
        session.query(Holding, Asset)
        .join(Asset, Holding.asset_id == Asset.id)
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )

    targets = {
        t.asset_class: t.target_pct
        for t in session.query(TargetAllocation)
        .filter(TargetAllocation.portfolio_id == portfolio.id)
        .all()
    }

    if not targets:
        return

    # Compute actual allocation
    total_value = 0.0
    class_values = {}
    for holding, asset in holdings:
        price = holding.current_price or holding.buy_price
        value = holding.quantity * price
        total_value += value
        ac = asset.asset_class.value if hasattr(asset.asset_class, 'value') else str(asset.asset_class)
        class_values[ac] = class_values.get(ac, 0) + value

    if total_value == 0:
        return

    # Compare with targets
    for asset_class, target_pct in targets.items():
        actual_pct = (class_values.get(asset_class, 0) / total_value * 100)
        drift = abs(actual_pct - target_pct)

        if drift < 1.0:
            continue

        severity = DriftSeverity.INFO
        if drift > 5.0:
            severity = DriftSeverity.ALERT
        elif drift > 3.0:
            severity = DriftSeverity.WARN

        alert = DriftAlert(
            portfolio_id=portfolio.id,
            asset_class=asset_class,
            actual_pct=round(actual_pct, 2),
            target_pct=round(target_pct, 2),
            drift_pct=round(drift, 2),
            severity=severity,
        )
        session.add(alert)

        logger.info(
            f"Portfolio {portfolio.id}: {asset_class} drift {drift:.1f}% ({severity.value})"
        )
