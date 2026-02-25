"""Async SQLAlchemy engine and session factory.

Creates the async engine with connection pooling and the session factory
with expire_on_commit=False (required for async to prevent MissingGreenlet errors).
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://user:pass@host:port/db
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # verify connections before use (catches stale connections)
    pool_recycle=1800,  # recycle connections after 30 minutes
    echo=settings.DEBUG,  # log SQL in debug mode only
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # REQUIRED: prevents MissingGreenlet after commit in async context
    autocommit=False,
    autoflush=False,
)
