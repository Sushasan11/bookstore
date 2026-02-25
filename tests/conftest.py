"""Shared test fixtures for async database and HTTP client.

Provides three fixtures used by every test module:
  - test_engine: Session-scoped async engine that creates/drops tables once per session
  - db_session: Function-scoped async session that rolls back after each test
  - client: Function-scoped httpx AsyncClient wired to the FastAPI app with DB override
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_db
from app.db.base import Base
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/bookstore_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create an async engine for the test database.

    Setup: creates all tables from Base.metadata.
    Teardown: drops all tables, then disposes the engine.
    Scoped to the session so tables are created once for the entire test run.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Yield a per-test async session that rolls back after each test.

    Each test gets an isolated session. After the test, the session is
    rolled back so no test data leaks between tests.
    """
    test_session_local = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with test_session_local() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Yield an httpx AsyncClient wired to the FastAPI app.

    Overrides the get_db dependency so routes use the test session
    instead of the production database. Clears overrides on teardown.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
