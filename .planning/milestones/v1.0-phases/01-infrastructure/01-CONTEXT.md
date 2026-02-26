# Phase 1: Infrastructure - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the async FastAPI application with PostgreSQL, Alembic migrations, and all dev tooling. This is the foundation every subsequent phase builds on. No feature code — just the scaffold, database layer, config, tooling, and conventions.

</domain>

<decisions>
## Implementation Decisions

### Project structure
- Domain-first layout: app/books/, app/users/, app/orders/, app/cart/, app/wishlist/, app/prebooks/
- Each domain has full file split: models.py, schemas.py, router.py, service.py, repository.py
- Shared code lives in app/core/ (config.py, security.py, deps.py)
- Database setup lives in app/db/ (session.py for engine + session factory, base.py for declarative base + model imports)

### Config & environment
- Single DATABASE_URL connection string (postgresql+asyncpg://user:pass@host:port/db)
- Single .env file with environment overrides (ENV=production for prod settings)
- Standard configurable vars: DATABASE_URL, SECRET_KEY, DEBUG, ALLOWED_ORIGINS, ACCESS_TOKEN_EXPIRE_MINUTES
- Commit .env.example with placeholder values; .env itself in .gitignore

### Dev workflow
- Docker Compose for PostgreSQL: two services — bookstore_dev (port 5432) and bookstore_test (port 5433)
- Poetry scripts for common commands (poetry run dev, poetry run test, poetry run lint) defined in pyproject.toml
- Separate test database: tests use dedicated test PostgreSQL instance, created/dropped per test session

### Error conventions
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

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants a clean, well-organized FastAPI project that follows modern Python conventions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-infrastructure*
*Context gathered: 2026-02-25*
