"""
FinVoice — Recommendation & Explanation models.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey, Integer, JSON,
    String, Text, func,
)
from sqlalchemy.orm import relationship

from database import Base


class RecommendationType(str, enum.Enum):
    REBALANCE = "rebalance"
    NEW_INVESTMENT = "new_investment"
    RISK_ALERT = "risk_alert"
    DRIFT_ALERT = "drift_alert"
    ML_SIGNAL = "ml_signal"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recommendation_type = Column(Enum(RecommendationType), nullable=False)

    # Recommendation content
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)  # Short explanation (free tier)
    detailed_explanation = Column(Text, nullable=True)  # Medium explanation (paid tier)
    full_report_json = Column(JSON, nullable=True)  # Full report data (paid tier)

    # Associated data
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    suggested_actions = Column(JSON, nullable=True)  # List of buy/sell/hold actions
    confidence_score = Column(Float, nullable=True)  # 0-1 model confidence

    # SEBI compliance
    disclaimer = Column(
        Text,
        default="FinVoice is a decision-support tool. Invest at your own risk. "
                "Consult a SEBI-registered advisor for personalized advice.",
    )

    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    explanation = relationship("Explanation", back_populates="recommendation", uselist=False)


class Explanation(Base):
    """
    XAI explanation linked to a recommendation.
    Stores SHAP values, factor attribution, and NLG output.
    """
    __tablename__ = "explanations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )

    # SHAP / Feature Importance
    shap_values = Column(JSON, nullable=True)  # {feature: shap_value}
    top_features = Column(JSON, nullable=True)  # Top 5 features driving the prediction
    feature_importance_chart_url = Column(String(500), nullable=True)

    # Factor Attribution (Barra-style)
    market_beta_contribution = Column(Float, nullable=True)
    sector_tilt_contribution = Column(Float, nullable=True)
    stock_alpha_contribution = Column(Float, nullable=True)
    unexplained_noise = Column(Float, nullable=True)

    # NLG Output
    short_explanation = Column(Text, nullable=True)   # 1 sentence (free)
    medium_explanation = Column(Text, nullable=True)   # 3-4 factors (paid)
    full_explanation = Column(Text, nullable=True)      # Detailed (paid report)

    # Regime context
    market_regime = Column(String(50), nullable=True)  # bull/bear/sideways/high_vol
    regime_impact_note = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    recommendation = relationship("Recommendation", back_populates="explanation")
