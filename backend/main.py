"""
FinVoice — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from config import get_settings
from database import init_db

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Startup: initialize database tables
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="FinVoice API",
    description="AI-Powered Portfolio Management for Every Indian Investor",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Middleware ───
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Register API Routers ───
from api.auth import router as auth_router
from api.onboarding import router as onboarding_router
from api.portfolio import router as portfolio_router
from api.investment import router as investment_router
from api.stress_test import router as stress_test_router
from api.recommendations import router as recommendations_router

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(investment_router, prefix="/investment", tags=["Investment"])
app.include_router(stress_test_router, prefix="/stress-test", tags=["Stress Testing"])
app.include_router(recommendations_router, prefix="/recommendations", tags=["Recommendations"])


@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "disclaimer": (
            "FinVoice is a decision-support tool. Invest at your own risk. "
            "Consult a SEBI-registered advisor for personalized advice."
        ),
    }
