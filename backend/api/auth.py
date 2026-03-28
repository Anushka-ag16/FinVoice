"""
FinVoice — Auth API with JWT Validation & Role-Based Access Control.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, UserTier
from schemas.user import UserCreate, UserResponse
from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


# ─── JWT Token Validation ───


def _decode_jwt(token: str) -> dict:
    """
    Decode and validate a JWT token.
    In production: validates against Supabase JWT secret.
    In development: allows plain email as token for testing.
    """
    from jose import jwt, JWTError, ExpiredSignatureError

    # Development mode: allow plain email as token for easy testing
    if settings.app_env == "development" and "@" in token:
        logger.debug(f"Dev mode: using email token '{token}'")
        return {"sub": token, "email": token, "dev_mode": True}

    # Production: decode JWT with Supabase secret
    jwt_secret = settings.supabase_jwt_secret
    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )

    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate JWT from Authorization header.
    Returns the authenticated User object.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    payload = _decode_jwt(token)

    # Extract user identifier from JWT payload
    user_email = payload.get("email") or payload.get("sub")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user identity",
        )

    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please register first.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


# ─── Role-Based Access Control (RBAC) ───


async def require_paid_tier(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that enforces paid-tier access.
    Use on premium endpoints (RL optimizer, Monte Carlo, etc.).
    """
    if current_user.tier != UserTier.PAID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This feature requires a paid subscription (₹299/month). "
                "Upgrade to access RL optimization, crash simulation, and more."
            ),
        )
    return current_user


async def require_onboarding_complete(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that enforces portfolio import before analysis.
    Portfolio import is mandatory in FinVoice.
    """
    if not current_user.onboarding_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You must import your portfolio before accessing this feature. "
                "Use POST /portfolio/import to get started."
            ),
        )
    return current_user


# ─── Endpoints ───


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        supabase_uid=user_data.supabase_uid,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info(f"New user registered: {user.email}")
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user
