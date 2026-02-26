# Phase 1: Infrastructure - Research

**Researched:** 2026-02-25
**Domain:** FastAPI async application scaffold — PostgreSQL, SQLAlchemy 2.0, Alembic, Poetry, Docker Compose, pydantic-settings, pytest-asyncio
**Confidence:** HIGH (all stack decisions verified against project-level research with confirmed PyPI versions and official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Project structure:**
- Domain-first layout: app/books/, app/users/, app/orders/, app/cart/, app/wishlist/, app/prebooks/
- Each domain has full file split: models.py, schemas.py, router.py, service.py, repository.py
- Shared code lives in app/core/ (config.py, security.py, deps.py)
- Database setup lives in app/db/ (session.py for engine + session factory, base.py for declarative base + model imports)

**Config & environment:**
- Single DATABASE_URL connection string (postgresql+asyncpg://user:pass@host:port/db)
- Single .env file with environment overrides (ENV=production for prod settings)
- Standard configurable vars: DATABASE_URL, SECRET_KEY, DEBUG, ALLOWED_ORIGINS, ACCESS_TOKEN_EXPIRE_MINUTES
- Commit .env.example with placeholder values; .env itself in .gitignore

**Dev workflow:**
- Docker Compose for PostgreSQL: two services — bookstore_dev (port 5432) and bookstore_test (port 5433)
- Poetry scripts for common commands (poetry run dev, poetry run test, poetry run lint) defined in pyproject.toml
- Separate test database: tests use dedicated test PostgreSQL instance, created/dropped per test session

**Error conventions:**
- Structured JSON error responses: {"detail": "message", "code": "ERROR_CODE", "field": "optional"}
- Validation errors use FastAPI default format: 422 with Pydantic error list
- App-level error code system across all endpoints (e.g., AUTH_INVALID_TOKEN, BOOK_NOT_FOUND, CART_OUT_OF_STOCK)
- Unhandled exceptions always return generic {"detail": "Internal server error"} — never leak stack traces in any environment

### Claude's Discretion
- Exact Poetry script definitions and naming
- Alembic env.py async configuration details
- Test fixture design and conftest.py structure
- Ruff rule selection and configuration
- Health check endpoint implementation details

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

---

## Summary

This phase establishes every structural, configuration, and tooling decision that downstream phases depend on. The project starts from a completely empty directory — no existing code. The full task list for Phase 1 must produce: a working Poetry project with all dependencies pinned, a FastAPI application that starts without error, an async SQLAlchemy engine connecting to PostgreSQL via asyncpg, Alembic initialized with the async template and a correctly configured env.py, Docker Compose with two PostgreSQL containers (dev + test), pydantic-settings config reading from .env, global exception handlers enforcing the structured error response convention, a health check endpoint, and a pytest conftest.py that creates/tears down the test database per session.

The project-level research (STACK.md, ARCHITECTURE.md, PITFALLS.md) has already validated and pinned all library versions. This phase research focuses on the specific implementation patterns for each infrastructure component — the exact code structures that make them work correctly with async FastAPI, and the common mistakes to avoid at this foundational step.

The most critical correctness concern in Phase 1 is the Alembic env.py configuration. If `alembic/env.py` does not import all SQLAlchemy models before referencing `Base.metadata`, autogenerate will produce empty or destructive migrations in every subsequent phase. This is a silent failure with high recovery cost. The second-most critical concern is setting `expire_on_commit=False` on the async session factory — without it, accessing model attributes after commit raises `MissingGreenlet` errors in every subsequent phase.

**Primary recommendation:** Use `alembic init -t async alembic` (the async template), configure `env.py` to import models via `app.db.base`, set `expire_on_commit=False` on `async_sessionmaker`, and verify correctness by running `alembic revision --autogenerate` after adding the first stub model.

---

## Standard Stack

### Core (all versions pre-validated in STACK.md)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13 | Runtime | Latest stable; FastAPI supports 3.10-3.14; 3.12 is now security-only |
| FastAPI | 0.133.0 | Web framework | Async-native, OpenAPI docs, Pydantic v2 integration |
| Uvicorn | 0.41.0 | ASGI server | FastAPI's official recommended server; `[standard]` extra adds watchfiles |
| Pydantic | 2.12.5 | Data validation | Built into FastAPI; v2 is 5-50x faster via Rust core |
| pydantic-settings | 2.13.1 | Config from env | Official companion to Pydantic v2; reads .env with type validation |
| SQLAlchemy | 2.0.47 | ORM (async) | Industry standard; v2.0 adds first-class `AsyncSession`, `create_async_engine` |
| asyncpg | 0.31.0 | PostgreSQL async driver | Fastest async PostgreSQL driver; binary protocol; required for SQLAlchemy async |
| Alembic | 1.18.4 | DB migrations | Official SQLAlchemy migration tool; `--async` template for asyncpg projects |
| Poetry | 2.3.2 | Dependency management | Project-specified; manages virtualenvs, lock files, pyproject.toml as single config |

### Development & Testing Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| pytest | 9.0.2 | Test runner | Standard Python testing |
| pytest-asyncio | 1.3.0 | Async test support | Required for `async def` tests; set `asyncio_mode = "auto"` |
| httpx | 0.28.1 | Async HTTP test client | `AsyncClient` + `ASGITransport` for in-process FastAPI testing |
| ruff | 0.15.2 | Linter + formatter | Replaces black + isort + flake8; written in Rust; configured in pyproject.toml |
| mypy | latest | Static type checking | Optional but recommended; FastAPI's type-hints make it very effective |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncpg (driver) | psycopg3 (async) | psycopg3 is viable; asyncpg is more popular with SQLAlchemy async; asyncpg is the safer default |
| pydantic-settings | python-decouple | pydantic-settings gives type validation, not just string reading; natural fit when already using Pydantic v2 |
| ruff | black + isort + flake8 | Only if existing project already uses those; ruff replaces all three, 10-100x faster |
| alembic async template | manual env.py edit | The `-t async` template generates a pre-configured env.py; saves manual setup and avoids missing steps |

**Installation:**
```bash
# Initialize new Poetry project
poetry new bookstore --name app
cd bookstore

# Add production dependencies
poetry add "fastapi[standard]@^0.133.0" "uvicorn[standard]@^0.41.0"
poetry add "sqlalchemy[asyncio]@^2.0.47" "alembic@^1.18.4" "asyncpg@^0.31.0"
poetry add "pydantic@^2.12.5" "pydantic-settings@^2.13.1"
poetry add python-multipart email-validator python-dotenv

# Add dev dependencies
poetry add --group dev "pytest@^9.0.2" "pytest-asyncio@^1.3.0" "httpx@^0.28.1"
poetry add --group dev "ruff@^0.15.2" mypy
```

---

## Architecture Patterns

### Recommended Project Structure

```
bookstore/                         # Project root (Poetry manages this)
├── pyproject.toml                 # Poetry deps + tool config (pytest, ruff, mypy)
├── poetry.lock
├── .env                           # Local secrets — in .gitignore
├── .env.example                   # Committed placeholder template
├── .gitignore                     # Includes .env, __pycache__, .mypy_cache
├── alembic.ini                    # Alembic entry point (URL overridden by env.py)
├── alembic/                       # Database migrations
│   ├── env.py                     # Imports Base.metadata + all models; async config
│   ├── script.py.mako             # Migration file template
│   └── versions/                  # Migration files (committed to git)
├── docker-compose.yml             # Dev + test PostgreSQL services
├── app/                           # Application package
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory: includes routers, mounts exception handlers
│   ├── core/                      # Cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── config.py              # BaseSettings reading .env; get_settings() with @lru_cache
│   │   ├── security.py            # JWT encode/decode, password hashing (stub in Phase 1)
│   │   ├── deps.py                # get_db dependency (AsyncSession per request)
│   │   └── exceptions.py          # Global exception handlers: HTTPException + generic 500
│   ├── db/                        # Database infrastructure
│   │   ├── __init__.py
│   │   ├── base.py                # DeclarativeBase; imports all models (REQUIRED for Alembic)
│   │   └── session.py             # create_async_engine + async_sessionmaker factory
│   ├── books/                     # Domain stubs (empty __init__.py only in Phase 1)
│   ├── users/
│   ├── orders/
│   ├── cart/
│   ├── wishlist/
│   └── prebooks/
└── tests/
    ├── conftest.py                # Async client, test DB session, engine, app fixtures
    └── test_health.py             # Smoke test: GET /health returns 200
```

**Note:** Domain folders (books/, users/, etc.) are created as empty packages in Phase 1. Individual files (models.py, schemas.py, etc.) are created in their respective feature phases.

### Pattern 1: Async SQLAlchemy Engine and Session Factory

**What:** Creates the async engine with connection pooling, creates a session factory with `expire_on_commit=False` (critical for async), and provides a per-request session via FastAPI `Depends`.

**When to use:** This is the canonical pattern — every database-touching route uses this session.

**Example:**
```python
# app/db/session.py
# Source: ARCHITECTURE.md — verified against SQLAlchemy 2.0 official docs
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://user:pass@host:port/db
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,      # verify connections before use (catches stale connections)
    pool_recycle=1800,       # recycle connections after 30 minutes
    echo=settings.DEBUG,     # log SQL in debug mode only
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # REQUIRED: prevents MissingGreenlet after commit in async context
    autocommit=False,
    autoflush=False,
)


# app/core/deps.py
from typing import AsyncGenerator, Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

DbSession = Annotated[AsyncSession, Depends(get_db)]
```

### Pattern 2: pydantic-settings with @lru_cache

**What:** Single `Settings` class reads from `.env` file and environment variables. `@lru_cache` ensures the file is read only once per process lifetime. `Depends(get_settings)` makes it injectable and overridable in tests.

**When to use:** All configuration access throughout the application.

**Example:**
```python
# app/core/config.py
# Source: FastAPI official docs — https://fastapi.tiangolo.com/advanced/settings/
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bookstore_dev"

    # Security
    SECRET_KEY: str = "changeme-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**`.env` file format (not committed — in .gitignore):**
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bookstore_dev
SECRET_KEY=your-secret-key-here
DEBUG=true
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=["http://localhost:3000"]
```

**`.env.example` (committed):**
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bookstore_dev
SECRET_KEY=changeme
DEBUG=false
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=["http://localhost:3000"]
```

### Pattern 3: Alembic Async Configuration

**What:** Alembic initialized with the async template (`-t async`). The `env.py` uses `asyncio.run()` to run migrations, imports all SQLAlchemy models before setting `target_metadata`, and overrides the database URL from the Settings object (not from `alembic.ini` directly).

**When to use:** Initial Alembic setup — must be done before any models are created.

**Critical setup steps:**
1. `poetry run alembic init -t async alembic` — generates async-ready `env.py`
2. Edit `env.py` to import all models and set URL from settings
3. Edit `alembic.ini` to point `script_location = alembic` (default)
4. Verify with `poetry run alembic revision --autogenerate -m "initial"` — should produce a non-empty migration

**Example env.py pattern:**
```python
# alembic/env.py — key sections (using async template as base)
# Source: Alembic official docs + berkkaraal.com verified pattern
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import get_settings
# CRITICAL: Import app.db.base which imports ALL models
# Without this, autogenerate sees an empty metadata and produces empty/destructive migrations
from app.db.base import Base  # noqa: F401

settings = get_settings()
target_metadata = Base.metadata

def get_url() -> str:
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # detect column type changes
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = context.config.get_section(context.config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations():
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())


run_migrations()
```

**app/db/base.py — the model aggregator (critical for Alembic):**
```python
# app/db/base.py
# This file has TWO purposes:
# 1. Defines the DeclarativeBase all models inherit from
# 2. Imports all models so Alembic can discover them
# Source: ARCHITECTURE.md + PITFALLS.md Pitfall 4 prevention
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Import ALL models here as they are created in later phases
# Each phase adds its import to this file
# Example (added in Phase 2): from app.users.models import User  # noqa: F401
# Example (added in Phase 4): from app.books.models import Book  # noqa: F401
```

### Pattern 4: Docker Compose with Dev and Test Databases

**What:** Two PostgreSQL services — one for development (bookstore_dev on port 5432), one for testing (bookstore_test on port 5433). Both are always available when Docker Compose is running.

**When to use:** Local development. Tests connect to bookstore_test; the app server connects to bookstore_dev.

**Example:**
```yaml
# docker-compose.yml
services:
  bookstore_dev:
    image: postgres:17
    environment:
      POSTGRES_DB: bookstore_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d bookstore_dev"]
      interval: 5s
      timeout: 5s
      retries: 5

  bookstore_test:
    image: postgres:17
    environment:
      POSTGRES_DB: bookstore_test
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"    # host port 5433 → container port 5432
    # No volume — test DB is intentionally ephemeral

volumes:
  postgres_dev_data:
```

**Test DB URL in .env (used by tests only):**
```
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/bookstore_test
```

### Pattern 5: Global Exception Handlers

**What:** Two handlers registered on the FastAPI app — one for `HTTPException` that reformats the response to include an `app_code` field, and one for bare `Exception` (500s) that always returns a generic message regardless of environment.

**When to use:** Registered in `app/main.py` during app factory setup. Applied to every response automatically.

**Design decision:** The `app_code` field in the error response maps to the app-level error code system (AUTH_INVALID_TOKEN, BOOK_NOT_FOUND, etc.). When raising `HTTPException`, callers can pass `app_code` via the headers parameter or a custom exception subclass.

**Recommended approach:** Use a custom `AppHTTPException` that carries the `code` field, then register an exception handler for it that formats the structured JSON response.

**Example:**
```python
# app/core/exceptions.py
# Source: FastAPI official docs (handling-errors) + structured error convention from CONTEXT.md
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Custom application-level exception with structured error code."""
    def __init__(self, status_code: int, detail: str, code: str, field: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.field = field


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = {"detail": exc.detail, "code": exc.code}
    if exc.field:
        body["field"] = exc.field
    return JSONResponse(status_code=exc.status_code, content=body)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Re-format FastAPI's HTTPException to include code field
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": f"HTTP_{exc.status_code}"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the real error; return generic message — NEVER leak internals
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Keep Pydantic 422 format but add code field
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "code": "VALIDATION_ERROR"},
    )


# app/main.py — register handlers
from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import (
    AppError,
    app_error_handler,
    http_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)

def create_app() -> FastAPI:
    app = FastAPI(title="Bookstore API", version="1.0.0")

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include routers (none in Phase 1 except health)
    from app.core.health import router as health_router
    app.include_router(health_router)

    return app

app = create_app()
```

### Pattern 6: Poetry Scripts in pyproject.toml

**What:** Defines shorthand commands so developers run `poetry run dev`, `poetry run test`, `poetry run lint` instead of long uvicorn/pytest/ruff commands.

**Note:** Poetry's `[tool.poetry.scripts]` is for Python entry points (installed scripts), not arbitrary shell commands. For arbitrary commands, use `[tool.taskipy]` or list the commands as custom scripts using Poetry's built-in script support with Python callables. The simplest option is to document the commands or use `taskipy`.

**Recommended approach (taskipy):**
```toml
# pyproject.toml
[tool.poetry.group.dev.dependencies]
taskipy = "*"

[tool.taskipy.tasks]
dev = "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
test = "pytest tests/ -v"
lint = "ruff check . && ruff format --check ."
format = "ruff format . && ruff check --fix ."
migrate = "alembic upgrade head"
makemigration = "alembic revision --autogenerate"

# Usage: poetry run task dev
```

**Alternative (simpler, no extra dep):** Document in README and use `Makefile`:
```makefile
dev:
    poetry run uvicorn app.main:app --reload

test:
    poetry run pytest tests/ -v

lint:
    poetry run ruff check . && poetry run ruff format --check .
```

**Claude's discretion:** Either taskipy or Makefile is acceptable. Taskipy is the Poetry-native option.

### Pattern 7: pytest conftest.py for Async Testing

**What:** Session-scoped engine and table creation against the test DB. Function-scoped session that rolls back after each test for isolation. Override of the `get_db` FastAPI dependency. Async HTTP client that speaks directly to the ASGI app (no real HTTP).

**When to use:** All tests. The conftest.py is the foundation; individual test files import fixtures from it automatically.

**Example:**
```python
# tests/conftest.py
# Source: praciano.com.br pattern + pytest-asyncio 1.3.0 docs
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.config import get_settings
from app.core.deps import get_db
from app.db.base import Base

settings = get_settings()

# Use dedicated test DB URL — set in .env or environment variable
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/bookstore_test"

# Session-scoped engine for the test database
@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    # Create all tables at session start
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Drop all tables at session end
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# Function-scoped session — each test gets a fresh session
@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()  # Roll back after each test for isolation


# Function-scoped async client with get_db override
@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

**pyproject.toml pytest configuration:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"           # All async tests run without explicit decorator
testpaths = ["tests"]
```

### Pattern 8: Health Check Endpoint

**What:** Single `GET /health` route that returns 200 with a status payload. Used by Docker healthchecks and monitoring systems. Does NOT check database connectivity in Phase 1 (that adds coupling; Phase 2+ can upgrade it).

**When to use:** Always included; the minimal smoke test for the application.

**Example:**
```python
# app/core/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
```

### Anti-Patterns to Avoid

- **Missing `expire_on_commit=False`:** The SQLAlchemy async session factory default is `expire_on_commit=True`. After `await session.commit()`, all model attributes expire and accessing them outside the session context raises `MissingGreenlet`. Always set `expire_on_commit=False` on `async_sessionmaker`.

- **Alembic URL in alembic.ini only:** Hardcoding the DATABASE_URL in `alembic.ini` creates a second source of truth. Override the URL from `get_settings()` inside `env.py` so there is always one canonical source.

- **Not importing models in base.py:** If `app/db/base.py` only defines `Base` but does not import models, Alembic's `target_metadata` is empty. Running `alembic revision --autogenerate` produces migrations that drop all existing tables.

- **Using synchronous `postgresql://` URL:** SQLAlchemy async requires the `postgresql+asyncpg://` scheme. Using `postgresql://` silently falls back to synchronous behavior, blocking the event loop.

- **Global `get_settings()` call at module import time:** Calling `get_settings()` at module import level (outside a function or `@lru_cache`) causes `.env` to be re-read on every import, and makes testing overrides impossible. Always wrap in `@lru_cache`.

- **Running `alembic upgrade head` at app startup in production:** Causes all workers to race to migrate simultaneously. Use it in dev only; run migrations as a separate pre-deploy step in production.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .env file parsing | Custom os.environ reader | pydantic-settings BaseSettings | Type validation, Pydantic integration, `lru_cache` caching, dotenv support built-in |
| Database migrations | Manual ALTER TABLE scripts | Alembic | Handles upgrade/downgrade, autogenerate, version history, concurrent migration detection |
| Async session management | Manual session open/close in routes | `get_db` dependency with `async with AsyncSessionLocal()` | Consistent commit/rollback semantics, session lifecycle tied to request lifecycle |
| Connection pooling | Manual connection tracking | SQLAlchemy engine `pool_size`, `max_overflow`, `pool_pre_ping` | Handles connection reuse, stale connection detection, overflow management |
| Test client for FastAPI | Spinning up a real server | `httpx.AsyncClient` with `ASGITransport` | In-process testing, no network overhead, proper async support |
| Command shortcuts | Shell aliases | taskipy or Makefile | Reproducible across team members, documented in project |

**Key insight:** Every component in this infrastructure layer has a battle-tested library that handles edge cases (connection drops, transaction isolation, concurrent migrations) that custom solutions inevitably miss.

---

## Common Pitfalls

### Pitfall 1: Alembic Sees Empty Metadata (Most Critical)

**What goes wrong:** `alembic revision --autogenerate` produces an empty `upgrade()` function even though models exist. Worse: if models were defined against a different `Base` instance, running the migration drops all existing tables.

**Why it happens:** `app/db/base.py` defines `Base` but no model files are imported at the time Alembic runs. SQLAlchemy only knows about tables that have been imported and registered against the `Base` instance.

**How to avoid:**
- Every model file must be imported in `app/db/base.py` before `target_metadata = Base.metadata` is set
- After adding the first model, immediately run `alembic revision --autogenerate -m "initial"` and verify the migration is non-empty
- Add `compare_type=True` to `context.configure()` in `env.py` to also detect column type changes

**Warning signs:**
- Migration file has empty `upgrade()` and `downgrade()` functions
- `alembic current` shows no migrations applied after running `upgrade head`
- Adding a new model column produces an empty migration

### Pitfall 2: expire_on_commit=True (Default) Breaks Async

**What goes wrong:** After `await session.commit()`, SQLAlchemy marks all loaded model attributes as expired. The next access to any attribute triggers a lazy load, which in async context raises `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`.

**Why it happens:** The default `async_sessionmaker` uses `expire_on_commit=True`. This is inherited from sync SQLAlchemy where expired attributes are refreshed synchronously on next access. Async SQLAlchemy cannot do this.

**How to avoid:** Set `expire_on_commit=False` in the `async_sessionmaker` call. This is a one-line fix that must be in `app/db/session.py` from the start.

**Warning signs:**
- `MissingGreenlet` / `greenlet_spawn has not been called` errors
- Routes that work in isolation fail when returning model attributes after commit

### Pitfall 3: Alembic URL Mismatch

**What goes wrong:** `alembic.ini` has a different database URL than the application's `.env`. Migrations run against the wrong database. Schema drifts silently between environments.

**Why it happens:** Developers follow Alembic quickstart docs that set the URL in `alembic.ini` and forget to update it when the environment changes.

**How to avoid:** Override `sqlalchemy.url` in `env.py` using `get_settings().DATABASE_URL`. The `alembic.ini` value becomes a fallback/placeholder that is never actually used.

**Warning signs:**
- Migration runs successfully but the dev database schema does not change
- `alembic current` shows `None` even after running `alembic upgrade head`

### Pitfall 4: Test Isolation — Session vs. Transaction Scope

**What goes wrong:** Tests modify database state and the modifications persist to subsequent tests, causing test order dependencies and flaky failures.

**Why it happens:** The test DB session is not rolled back between tests, or `drop_all`/`create_all` is done per-function (slow) instead of using transaction rollback.

**How to avoid:** The recommended pattern (see Pattern 7) uses a session-scoped engine with `create_all`/`drop_all`, and a function-scoped session that rolls back after each test. This gives isolation without table recreation overhead.

**Warning signs:**
- Tests pass individually but fail when run in suite
- Test failures depend on test execution order
- Test suite becomes slow as number of tests grows

### Pitfall 5: asyncio_mode Not Set

**What goes wrong:** pytest-asyncio 1.x defaults to `strict` mode where every async test must be decorated with `@pytest.mark.asyncio`. Without this decorator, async tests are silently skipped (or fail with a confusing coroutine-not-awaited warning).

**Why it happens:** Developers forget the decorator and pytest runs the coroutine function without awaiting it, returning a coroutine object that is truthy — so the test "passes" without executing.

**How to avoid:** Set `asyncio_mode = "auto"` in `pyproject.toml` under `[tool.pytest.ini_options]`. This makes all `async def` test functions run automatically.

**Warning signs:**
- Tests never fail even when assertions are wrong
- Coverage shows 0% for async test functions
- `RuntimeWarning: coroutine 'test_foo' was never awaited`

### Pitfall 6: Poetry Scripts vs. Entry Points Confusion

**What goes wrong:** Defining `dev = "uvicorn app.main:app --reload"` in `[tool.poetry.scripts]` does not work — Poetry scripts expect Python callable entry points (`module:function`), not shell commands.

**Why it happens:** Developers familiar with npm scripts expect `[tool.poetry.scripts]` to behave like npm's `scripts` section. It does not.

**How to avoid:** Use `taskipy` (`poetry run task dev`) or a `Makefile` for shell command shortcuts. See Pattern 6.

**Warning signs:**
- `poetry run dev` raises `ModuleNotFoundError` or fails to find the entry point
- The script runs but does not pass arguments correctly

---

## Code Examples

### Ruff Configuration in pyproject.toml
```toml
# Source: Ruff official docs — ruff.astral.sh
[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "N",    # pep8-naming
]
ignore = [
    "E501",  # line-length — handled by formatter
]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

### mypy Configuration in pyproject.toml
```toml
# Source: mypy official docs
[tool.mypy]
python_version = "3.13"
strict = false
ignore_missing_imports = true
plugins = ["pydantic.mypy"]
```

### Complete pyproject.toml Structure
```toml
[tool.poetry]
name = "bookstore"
version = "0.1.0"
description = "Bookstore e-commerce API"
authors = ["Your Name <you@example.com>"]
packages = [{include = "app"}]

[tool.poetry.dependencies]
python = "^3.13"
fastapi = {version = "^0.133.0", extras = ["standard"]}
uvicorn = {version = "^0.41.0", extras = ["standard"]}
sqlalchemy = {version = "^2.0.47", extras = ["asyncio"]}
alembic = "^1.18.4"
asyncpg = "^0.31.0"
pydantic = "^2.12.5"
pydantic-settings = "^2.13.1"
python-multipart = "*"
email-validator = "*"
python-dotenv = "*"

[tool.poetry.group.dev.dependencies]
pytest = "^9.0.2"
pytest-asyncio = "^1.3.0"
httpx = "^0.28.1"
ruff = "^0.15.2"
mypy = "*"
taskipy = "*"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.taskipy.tasks]
dev = "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
test = "pytest tests/ -v"
lint = "ruff check . && ruff format --check ."
format = "ruff format . && ruff check --fix ."
migrate = "alembic upgrade head"
makemigration = "alembic revision --autogenerate"

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "N"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.mypy]
python_version = "3.13"
ignore_missing_imports = true
```

### Smoke Test (verify infrastructure works end-to-end)
```python
# tests/test_health.py
# Verifies app starts, routes are registered, and response format is correct
import pytest
from httpx import AsyncClient

async def test_health_returns_200(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


async def test_404_returns_structured_error(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "code" in data


async def test_db_session_connects(db_session):
    # Verify the test database session can execute a query
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| passlib for password hashing | pwdlib[argon2] | 2024 (FastAPI PR #13917) | passlib is unmaintained + Python 3.13 removed `crypt` module; must use pwdlib |
| python-jose for JWT | PyJWT 2.11.0 | 2023-2024 | python-jose abandoned; PyJWT is now FastAPI's official recommendation |
| sync SQLAlchemy with threadpool | `AsyncSession` + `create_async_engine` | SQLAlchemy 2.0 (2023) | True async; avoids threadpool overhead |
| psycopg2 | asyncpg | 2023+ | asyncpg is the standard async PostgreSQL driver for SQLAlchemy 2.0 |
| Alembic manual env.py edits | `alembic init -t async` | Alembic 1.x | Generates async-ready env.py; reduces setup mistakes |
| pytest-asyncio strict mode | `asyncio_mode = "auto"` in pyproject.toml | pytest-asyncio 0.21+ | Removes per-test decorator requirement |

**Deprecated/outdated (do not use in this project):**
- `passlib`: Python 3.13 removed the `crypt` module it depends on. Not just deprecated — it will crash on Python 3.13.
- `python-jose`: Last PyPI release 2022. FastAPI discussions (#9587, #11345) confirmed abandonment.
- `psycopg2` (sync): Blocks the event loop in async FastAPI. Always use `asyncpg` with `postgresql+asyncpg://` URL scheme.
- `SQLAlchemy 1.x` style ORM: `Column()`, `relationship()` without `Mapped[]` type annotations. SQLAlchemy 2.0 style is `Mapped[int] = mapped_column(...)`.

---

## Open Questions

1. **TEST_DATABASE_URL in test configuration**
   - What we know: Tests must connect to port 5433 (bookstore_test container)
   - What's unclear: Should TEST_DATABASE_URL live in `.env` (alongside DATABASE_URL) or in a separate `.env.test` file loaded only during tests?
   - Recommendation: Put `TEST_DATABASE_URL` in the same `.env` (Claude's discretion). In conftest.py, read it via `os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/bookstore_test")` — the hardcoded default matches the docker-compose.yml values, so tests work out of the box without extra setup.

2. **Health check — include DB connectivity check?**
   - What we know: User specified health check implementation details as Claude's Discretion
   - What's unclear: Should `GET /health` check the database connection or be a pure application-level ping?
   - Recommendation: Phase 1 health check should NOT check DB connectivity. A DB health check requires a working migration + model, which creates coupling to Phase 2 work. Add DB health in Phase 2 or later if needed.

3. **app/main.py — application factory vs. module-level app**
   - What we know: The ARCHITECTURE.md shows `app = create_app()` at module level
   - What's unclear: Should this use a factory function or directly create the `app` object?
   - Recommendation: Use `create_app()` factory function. It makes the app importable by tests without creating a global app object at import time, and makes future configuration-driven setup (e.g., different middleware per environment) cleaner.

---

## Sources

### Primary (HIGH confidence)
- STACK.md (project-level research) — all library versions verified against PyPI; pre-validated for this project
- ARCHITECTURE.md (project-level research) — domain-first layout, three-layer pattern, SQLAlchemy patterns
- PITFALLS.md (project-level research) — Alembic autogenerate, MissingGreenlet, async pitfalls
- [FastAPI official docs — Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/) — exception handler patterns
- [FastAPI official docs — Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/) — BaseSettings with lru_cache

### Secondary (MEDIUM confidence)
- [berkkaraal.com — Setup FastAPI with async SQLAlchemy 2, Alembic, PostgreSQL, Docker (2024)](https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/) — Docker Compose pattern, Alembic async template usage
- [praciano.com.br — FastAPI and async SQLAlchemy 2.0 with pytest done right](https://praciano.com.br/fastapi-and-async-sqlalchemy-20-with-pytest-done-right.html) — conftest.py session fixture pattern
- [Poetry official docs — pyproject.toml](https://python-poetry.org/docs/pyproject/) — scripts vs. taskipy
- [Ruff official docs — astral.sh](https://docs.astral.sh/ruff/) — rule selection

### Tertiary (LOW confidence — verified via pattern consistency with official docs)
- WebSearch findings on pytest-asyncio `asyncio_mode = "auto"` — consistent with pytest-asyncio 1.3.0 changelog

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions pre-validated in project-level STACK.md research against PyPI
- Architecture: HIGH — domain-first layout is a locked decision; all structural patterns verified in ARCHITECTURE.md
- Alembic env.py: HIGH — verified against official Alembic docs and consistent with multiple current (2024-2026) guides
- Test conftest.py: MEDIUM-HIGH — the pattern is well-established but pytest-asyncio 1.3.x is very recent; confirm `asyncio_mode = "auto"` works with the exact version in pyproject.toml
- Poetry scripts (taskipy): MEDIUM — taskipy is a real library but adds an extra dependency; Makefile is a zero-dependency alternative
- Error handler structure: HIGH — FastAPI official docs confirm `add_exception_handler` API; `AppError` custom exception class is Claude's design choice

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days; stack is stable, no fast-moving pieces)
