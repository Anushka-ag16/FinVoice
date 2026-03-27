"""
FinVoice — ML Service Entry Point
"""

from fastapi import FastAPI

app = FastAPI(
    title="FinVoice ML Service",
    description="ML inference microservice",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ml_inference"}


@app.post("/predict/returns")
async def predict_returns(symbols: list[str], features: list[list[float]]):
    """Predict returns using ensemble model."""
    # Placeholder — import models from backend ml/ modules
    return {
        "predictions": {s: 0.001 for s in symbols},
        "confidence": {s: 0.5 for s in symbols},
        "regime": "sideways",
        "method": "placeholder",
    }
