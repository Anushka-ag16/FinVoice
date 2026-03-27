"""
FinVoice — Model Retraining Task
Runs weekly via Celery Beat.
"""

import logging
from tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.retrain_models.retrain_all")
def retrain_all():
    """
    Weekly model retraining pipeline.
    1. Load latest data from feature store
    2. Retrain XGBoost
    3. Retrain LSTM
    4. Update ensemble weights
    5. Retrain RL agent
    6. Log to MLflow
    """
    logger.info("Starting weekly model retraining...")

    try:
        _retrain_xgboost()
    except Exception as e:
        logger.error(f"XGBoost retraining failed: {e}")

    try:
        _retrain_lstm()
    except Exception as e:
        logger.error(f"LSTM retraining failed: {e}")

    try:
        _retrain_rl_agent()
    except Exception as e:
        logger.error(f"RL agent retraining failed: {e}")

    logger.info("Weekly model retraining complete")


def _retrain_xgboost():
    """Retrain XGBoost on latest features from the feature store."""
    import pandas as pd
    from sqlalchemy import create_engine
    from config import get_settings
    from ml.xgboost_model import XGBoostReturnPredictor

    settings = get_settings()
    engine = create_engine(settings.database_url_sync)

    # Load features from DB
    query = """
        SELECT * FROM features
        WHERE date >= NOW() - INTERVAL '3 years'
        ORDER BY date
    """
    df = pd.read_sql(query, engine)

    if df.empty:
        logger.warning("No feature data available for XGBoost training")
        return

    # Split: last 6 months as validation
    cutoff = df["date"].max() - pd.Timedelta(days=180)
    train_df = df[df["date"] < cutoff]
    val_df = df[df["date"] >= cutoff]

    model = XGBoostReturnPredictor()
    metrics = model.train(train_df, val_df)
    model.save()

    logger.info(f"XGBoost retrained: {metrics}")


def _retrain_lstm():
    """Retrain LSTM on sequential data."""
    logger.info("LSTM retraining — placeholder (requires GPU)")
    # In production: load sequences, train on GPU (Colab Pro),
    # export to ONNX, deploy to ml_service


def _retrain_rl_agent():
    """Retrain RL agent on latest market data."""
    from services.rl_optimizer import RLOptimizerService

    try:
        path = RLOptimizerService.train_agent("PPO", total_timesteps=50000)
        logger.info(f"RL agent retrained: {path}")
    except Exception as e:
        logger.warning(f"RL training skipped: {e}")
