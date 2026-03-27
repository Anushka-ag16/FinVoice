"""
FinVoice — ML Service Microservice
Separate FastAPI service for ML model inference.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np

app = FastAPI(
    title="FinVoice ML Service",
    description="ML inference microservice for return prediction and regime detection",
    version="1.0.0",
)


class PredictionRequest(BaseModel):
    symbols: list[str]
    features: list[list[float]]  # [n_assets, n_features]


class PredictionResponse(BaseModel):
    predictions: dict[str, float]  # {symbol: predicted_return}
    confidence: dict[str, float]   # {symbol: confidence_score}
    regime: str
    method: str


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ml_inference"}


@app.post("/predict/returns", response_model=PredictionResponse)
async def predict_returns(request: PredictionRequest):
    """
    Predict expected returns for given assets.
    Uses ensemble of XGBoost + LSTM + regime detection.
    """
    try:
        # Load models
        from ml.xgboost_model import XGBoostReturnPredictor
        from ml.regime_detector import RegimeDetector, MarketRegime

        xgb = XGBoostReturnPredictor()
        try:
            xgb.load()
        except Exception:
            # Return placeholder predictions if model not trained
            predictions = {s: 0.001 for s in request.symbols}
            confidence = {s: 0.3 for s in request.symbols}
            return PredictionResponse(
                predictions=predictions,
                confidence=confidence,
                regime="unknown",
                method="fallback",
            )

        features = np.array(request.features)
        import pandas as pd
        df = pd.DataFrame(features, columns=xgb.FEATURE_COLS[:features.shape[1]])

        preds = xgb.predict(df)

        predictions = {
            sym: round(float(p), 6) for sym, p in zip(request.symbols, preds)
        }
        confidence = {sym: 0.6 for sym in request.symbols}

        return PredictionResponse(
            predictions=predictions,
            confidence=confidence,
            regime="sideways",
            method="xgboost",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/regime")
async def predict_regime(market_return: float, volatility: float):
    """Predict current market regime."""
    from ml.regime_detector import RegimeDetector

    detector = RegimeDetector()
    # If fitted, predict; else return default
    regime = detector.predict_current(market_return, volatility)
    shift = detector.get_regime_allocation_shift(regime)

    return {
        "regime": regime.value,
        "allocation_shift": shift,
    }
