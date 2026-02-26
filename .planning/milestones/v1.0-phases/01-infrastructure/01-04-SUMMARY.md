---
phase: 01-infrastructure
plan: 04
subsystem: tooling
tags: [pytest, pytest-asyncio, httpx, ruff, smoke-tests, async]

# Dependency graph
requires:
  - phase: 01-02
    provides: Async SQLAlchemy engine, DeclarativeBase (Base), get_db dependency, AsyncSessionLocal
  - phase: 01-03
    provides: Alembic async migration setup (verified DB connectivity)

provides:
  - pytest conftest.py with session-scoped async engine and function-scoped rollback sessions
  - httpx AsyncClient fixture wired to FastAPI app with get_db dependency override
  - 3 smoke tests proving health endpoint, structured errors, and DB connectivity
  - ruff check and ruff format passing with zero violations across all project files

affects: [phase-02-auth, phase-03-oauth, phase-04-catalog, phase-05-search, phase-06-cart, phase-07-orders, phase-08-wishlist, phase-09-prebooks]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Session-scoped test_engine with create_all/drop_all — tables created once per test run"
    - "Function-scoped db_session with rollback — each test gets isolated session state"
    - "httpx AsyncClient with ASGITransport for in-process FastAPI testing (no network)"
    - "app.dependency_overrides[get_db] swaps production DB for test session"
    - "asyncio_default_fixture_loop_scope and asyncio_default_test_loop_scope both set to session — prevents 'Future attached to a different loop' errors with session-scoped async fixtures"

key-files:
  created:
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_health.py
  modified:
    - pyproject.toml
    - app/core/deps.py
    - alembic/env.py

key-decisions:
  - "asyncio_default_test_loop_scope = session required alongside asyncio_default_fixture_loop_scope = session — without both, session-scoped engine creates connections on session loop but function-scoped tests run on different loop, causing asyncpg RuntimeError"
  - "AsyncGenerator imported from collections.abc (not typing) per UP035 — Python 3.13+ standard"
  - "AsyncGenerator[AsyncSession] without None second arg per UP043 — unnecessary default type argument"

patterns-established:
  - "Pattern: All async test fixtures use pytest_asyncio.fixture, not pytest.fixture"
  - "Pattern: test_engine is session-scoped; db_session and client are function-scoped with per-test rollback"
  - "Pattern: Every test module gets client fixture for HTTP tests and db_session fixture for direct DB tests"
  - "Pattern: ruff check + ruff format --check must pass before any commit (enforced in Plan 04, expected in all future plans)"

requirements-completed: [INFRA-TOOLING]

# Metrics
duration: 5min
completed: 2026-02-25
---

# Phase 1 Plan 04: Testing & Tooling Summary

**Async pytest infrastructure with 3 passing smoke tests and zero ruff violations across the entire project**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-25
- **Completed:** 2026-02-25
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 3

## Accomplishments

- Created `tests/conftest.py` with three async fixtures: session-scoped `test_engine` (create_all/drop_all), function-scoped `db_session` (per-test rollback), function-scoped `client` (httpx AsyncClient with get_db override)
- Created 3 smoke tests: `test_health_returns_200`, `test_404_returns_structured_error`, `test_db_session_connects` — all passing
- Fixed event loop mismatch: added `asyncio_default_test_loop_scope = "session"` to pyproject.toml so tests and session-scoped fixtures share one event loop
- Fixed ruff violations: import sorting in alembic/env.py, UP035/UP043 in app/core/deps.py
- Ran `ruff format` across all project files — 7 files reformatted
- All 3 tests pass in 0.14s, ruff check and ruff format --check report zero violations

## Task Commits

1. **Task 1: Create pytest conftest.py with async fixtures** - `d3aa145` (feat)
2. **Task 2: Add smoke tests and verify all tooling** - `41f50bc` (feat)
3. **Fix: Event loop scope + ruff violations** - pending commit

## Files Created/Modified

- `tests/__init__.py` - Makes tests a package
- `tests/conftest.py` - Async test fixtures: test_engine, db_session, client
- `tests/test_health.py` - 3 smoke tests for health, error handling, DB connectivity
- `pyproject.toml` - Added asyncio_default_fixture_loop_scope and asyncio_default_test_loop_scope = "session"
- `app/core/deps.py` - AsyncGenerator from collections.abc, removed unnecessary None type arg
- `alembic/env.py` - Fixed import sorting (alembic before sqlalchemy in third-party group)

## Decisions Made

- `asyncio_default_test_loop_scope = "session"` is required alongside `asyncio_default_fixture_loop_scope = "session"` — without both settings, session-scoped async fixtures (test_engine) create connections on one event loop while function-scoped tests run on a different loop, causing asyncpg `RuntimeError: Future attached to a different loop`
- `AsyncGenerator` imported from `collections.abc` instead of `typing` per ruff UP035 (Python 3.13+ standard)

## Deviations from Plan

- **Event loop fix required:** The plan did not anticipate the pytest-asyncio loop scope mismatch between session-scoped fixtures and function-scoped tests on Python 3.14. Added two pyproject.toml settings to resolve.
- **Ruff violations in earlier plans:** alembic/env.py (Plan 03) and app/core/deps.py (Plan 02) had ruff violations that were caught and fixed in this plan's ruff pass.

## Issues Encountered

- `test_db_session_connects` failed with `RuntimeError: Future attached to a different loop` — resolved by setting both `asyncio_default_fixture_loop_scope` and `asyncio_default_test_loop_scope` to `"session"` in pyproject.toml

## Next Phase Readiness

- All Phase 1 infrastructure is complete: FastAPI app, async DB, Alembic migrations, test fixtures, linting
- Phase 2 (Core Auth) can proceed — conftest.py fixtures are ready for auth endpoint tests
- No open concerns for Phase 2

## Self-Check: PASSED

- FOUND: tests/__init__.py
- FOUND: tests/conftest.py
- FOUND: tests/test_health.py
- VERIFIED: conftest.py contains `test_engine` fixture (session-scoped)
- VERIFIED: conftest.py contains `db_session` fixture with rollback
- VERIFIED: conftest.py contains `client` fixture with dependency override
- VERIFIED: test_health.py contains `test_health_returns_200`
- VERIFIED: test_health.py contains `test_404_returns_structured_error`
- VERIFIED: test_health.py contains `test_db_session_connects`
- VERIFIED: All 3 tests pass
- VERIFIED: ruff check reports zero violations
- VERIFIED: ruff format --check reports zero violations
- COMMITS: Task 1 at `d3aa145`, Task 2 at `41f50bc`

---
*Phase: 01-infrastructure*
*Completed: 2026-02-25*
