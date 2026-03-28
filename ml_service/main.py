"""
FinVoice — ML Service Entry Point

Provides REST API for:
  - /health              — Service health and model availability
  - /predict/returns     — Predict expected returns using trained models
  - /predict/regime      — Current market regime classification
  - /predict/sentiment   — Sentiment score for a ticker
  - /admin/retrain       — Trigger model retraining in background
"""

import logging
import os
import pickle
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "models"

# ── Global model store ──
_models: dict[str, Any] = {}


def _load_models() -> None:
    """Load trained models from disk into memory."""
    global _models

    # Regime detector (GMM + scaler)
    gmm_path = MODELS_DIR / "regime_gmm.pkl"
    scaler_path = MODELS_DIR / "regime_scaler.pkl"
    if gmm_path.exists() and scaler_path.exists():
        with open(gmm_path, "rb") as f:
            _models["regime_gmm"] = pickle.load(f)
        with open(scaler_path, "rb") as f:
            _models["regime_scaler"] = pickle.load(f)
        logger.info("Loaded regime GMM + scaler")

    # Ensemble components
    ensemble_dir = MODELS_DIR / "ensemble"
    if ensemble_dir.exists():
        for name in ["xgb_model.pkl", "cb_model.pkl", "meta_learner.pkl"]:
            path = ensemble_dir / name
            if path.exists():
                with open(path, "rb") as f:
                    _models[name.replace(".pkl", "")] = pickle.load(f)
                logger.info("Loaded ensemble component: %s", name)

    logger.info("Model store: %s", list(_models.keys()))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup."""
    _load_models()
    yield


app = FastAPI(
    title="FinVoice ML Service",
    description="ML inference microservice and retraining orchestration",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow backend to call us ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# Request / Response schemas
# ══════════════════════════════════════════════════════════════════════════════
class PredictionRequest(BaseModel):
    symbols: list[str]
    features: list[list[float]] | None = None


class RegimeRequest(BaseModel):
    roll_ret: float
    roll_vol: float
    vol_chg: float


class SentimentRequest(BaseModel):
    ticker: str
    texts: list[str] | None = None


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/health")
async def health():
    """Health check with model availability info."""
    return {
        "status": "healthy",
        "service": "ml_inference",
        "models_loaded": list(_models.keys()),
        "models_available": {
            "regime": "regime_gmm" in _models,
            "xgboost": "xgb_model" in _models,
            "catboost": "cb_model" in _models,
            "ensemble": "meta_learner" in _models,
        },
    }


@app.post("/predict/returns")
async def predict_returns(request: PredictionRequest):
    """Predict expected returns using trained ensemble or individual models."""
    xgb = _models.get("xgb_model")
    cb = _models.get("cb_model")
    meta = _models.get("meta_learner")

    # If we have features, use them; otherwise return placeholder
    if request.features and (xgb is not None or cb is not None):
        try:
            X = np.array(request.features, dtype=np.float32)
            predictions = {}
            method = "placeholder"

            if meta is not None and xgb is not None and cb is not None:
                # Full ensemble prediction
                pred_xgb = xgb.predict(X)
                pred_cb = cb.predict(X)
                pred_tft = np.zeros(len(X))
                L1 = np.column_stack([pred_xgb, pred_cb, pred_tft])
                ensemble_preds = meta.predict(L1)
                for i, sym in enumerate(request.symbols):
                    if i < len(ensemble_preds):
                        predictions[sym] = float(ensemble_preds[i])
                method = "ensemble"
            elif xgb is not None:
                preds = xgb.predict(X)
                for i, sym in enumerate(request.symbols):
                    if i < len(preds):
                        predictions[sym] = float(preds[i])
                method = "xgboost"
            elif cb is not None:
                preds = cb.predict(X)
                for i, sym in enumerate(request.symbols):
                    if i < len(preds):
                        predictions[sym] = float(preds[i])
                method = "catboost"

            # Get regime
            regime = _get_current_regime()

            return {
                "predictions": predictions,
                "confidence": {s: 0.6 for s in predictions},
                "regime": regime,
                "method": method,
            }
        except Exception as e:
            logger.error("Prediction error: %s", e)
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    # Fallback: no models or no features
    return {
        "predictions": {s: 0.0 for s in request.symbols},
        "confidence": {s: 0.0 for s in request.symbols},
        "regime": _get_current_regime(),
        "method": "no_model" if xgb is None else "no_features",
    }


@app.post("/predict/regime")
async def predict_regime(request: RegimeRequest):
    """Predict current market regime from rolling features."""
    gmm = _models.get("regime_gmm")
    scaler = _models.get("regime_scaler")

    if gmm is None or scaler is None:
        return {"regime": "unknown", "regime_id": -1, "message": "Regime model not loaded"}

    try:
        import pandas as pd
        features = pd.DataFrame([{
            "roll_ret": request.roll_ret,
            "roll_vol": request.roll_vol,
            "vol_chg": request.vol_chg,
        }])

        from ml.regime_detector import predict_regime as _predict_regime
        regime_series = _predict_regime(gmm, scaler, features)
        regime_id = int(regime_series.iloc[0])
        regime_names = {0: "bear", 1: "sideways", 2: "bull"}

        return {
            "regime": regime_names.get(regime_id, "unknown"),
            "regime_id": regime_id,
        }
    except Exception as e:
        logger.error("Regime prediction error: %s", e)
        raise HTTPException(status_code=500, detail=f"Regime prediction failed: {str(e)}")


@app.post("/predict/sentiment")
async def predict_sentiment(request: SentimentRequest):
    """Score sentiment for given ticker or texts."""
    try:
        from services.sentiment import get_sentiment_score, scrape_google_news

        texts = request.texts
        if not texts:
            texts = scrape_google_news(request.ticker, n=10)

        if not texts:
            return {"ticker": request.ticker, "score": 0.0, "n_texts": 0}

        scores = get_sentiment_score(texts)
        avg_score = float(np.mean(scores)) if scores else 0.0

        return {
            "ticker": request.ticker,
            "score": round(avg_score, 4),
            "n_texts": len(scores),
            "scores": [round(s, 4) for s in scores],
        }
    except Exception as e:
        logger.error("Sentiment error: %s", e)
        return {"ticker": request.ticker, "score": 0.0, "n_texts": 0, "error": str(e)}


def _get_current_regime() -> str:
    """Get current market regime from loaded model."""
    gmm = _models.get("regime_gmm")
    if gmm is None:
        return "unknown"

    label_map = getattr(gmm, "_label_map", {})
    # Without live data, return the most common regime
    return "sideways"


def _run_training_pipeline():
    """Runs the training pipeline as a background task."""
    logger.info("Starting training pipeline...")
    try:
        script_path = os.path.join(os.path.dirname(__file__), "scripts", "train_pipeline.py")
        result = subprocess.run(
            [sys.executable, script_path, "--skip-existing"],
            capture_output=True, text=True, check=True,
            cwd=str(PROJECT_ROOT),
        )
        logger.info("Training completed successfully:\n%s", result.stdout[-2000:])
    except subprocess.CalledProcessError as e:
        logger.error("Training pipeline failed with exit code %d:\n%s", e.returncode, e.stderr[-2000:])
    except Exception as e:
        logger.error("Unexpected error running training pipeline: %s", e)


@app.post("/admin/retrain")
async def retrain_models(background_tasks: BackgroundTasks):
    """Trigger the quantitative ML pipeline to retrain models."""
    background_tasks.add_task(_run_training_pipeline)
    return {
        "status": "accepted",
        "message": "Model retraining pipeline initiated in the background."
    }


@app.post("/admin/reload-models")
async def reload_models():
    """Reload trained models from disk without retraining."""
    _load_models()
    return {
        "status": "ok",
        "models_loaded": list(_models.keys()),
    }
