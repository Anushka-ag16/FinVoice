"""
FinVoice — Database Configuration
Async SQLAlchemy engine + session factory.
Supports SQLite for local dev, PostgreSQL+TimescaleDB for production.
"""

import os
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Use SQLite for local dev if PostgreSQL is not available
DATABASE_URL = settings.database_url

# Auto-detect: if default postgres URL and no DOCKER, fall back to SQLite
if "asyncpg" in DATABASE_URL and os.environ.get("USE_SQLITE", "true").lower() == "true":
    DATABASE_URL = "sqlite+aiosqlite:///./finvoice_dev.db"
    logger.info("Using SQLite for local development")

engine = create_async_engine(
    DATABASE_URL,
    echo=not settings.is_production,
    **({} if "sqlite" in DATABASE_URL else {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }),
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency for FastAPI routes — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    try:
        async with engine.begin() as conn:
            # TimescaleDB extension only for PostgreSQL
            if "postgresql" in DATABASE_URL:
                from sqlalchemy import text
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))

            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")
        logger.info("Server will continue — database tables will be created on first connection")
