"""
FinVoice — FastAPI Application Entry Point
Includes: Security Headers, CORS, Rate Limiting, JWT Auth.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from config import get_settings
from database import init_db

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


# ─── Security Headers Middleware ───

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects industry-standard HTTP security headers on every response.
    Mitigates XSS, clickjacking, MIME sniffing, and enforces HTTPS.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent browsers from MIME-sniffing the response
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking — deny all framing
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS in production
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy — restrict resource loading
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

        # Hide server tech stack
        response.headers["X-Powered-By"] = "FinVoice"
        response.headers["Server"] = "FinVoice"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — disable unused browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    await init_db()
    yield


app = FastAPI(
    title="FinVoice API",
    description="AI-Powered Portfolio Management for Every Indian Investor",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Middleware Stack (order matters: last added = first executed) ───

# 1. Rate limiting
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS
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
from api.trading import router as trading_router
from api.algorithms import router as algorithms_router
from api.smart_invest import router as smart_invest_router
from api.stop_orders import router as stop_orders_router

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(investment_router, prefix="/investment", tags=["Investment"])
app.include_router(stress_test_router, prefix="/stress-test", tags=["Stress Testing"])
app.include_router(recommendations_router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(trading_router, prefix="/trading", tags=["Trading"])
app.include_router(algorithms_router, prefix="/algorithms", tags=["Trading Algorithms"])
app.include_router(smart_invest_router, prefix="/smart-invest", tags=["Smart Investment"])
app.include_router(stop_orders_router, prefix="/stops", tags=["Stop Loss & Take Profit"])


@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "security": "enabled",
        "disclaimer": (
            "FinVoice is a decision-support tool. Invest at your own risk. "
            "Consult a SEBI-registered advisor for personalized advice."
        ),
    }
