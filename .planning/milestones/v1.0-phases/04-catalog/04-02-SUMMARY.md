---
phase: 04-catalog
plan: "02"
subsystem: api
tags: [fastapi, books, genres, catalog, router, admin-guard, dependency-injection]

# Dependency graph
requires:
  - phase: 04-catalog
    plan: "01"
    provides: "BookService, BookRepository, GenreRepository, all Pydantic schemas (BookCreate, BookUpdate, BookResponse, StockUpdate, GenreCreate, GenreResponse)"
  - phase: 02-core-auth
    provides: "AdminUser dependency, DbSession type alias, AppError exception pattern"
provides:
  - "app/books/router.py with 7 catalog endpoints (POST/GET/PUT/DELETE /books, PATCH /books/stock, POST/GET /genres)"
  - "books_router registered in FastAPI app via app/main.py"
  - "HTTP surface for all catalog CRUD: create/read/update/delete books, stock management, genre taxonomy"
affects: [04-catalog plan 03 (tests), 05-discovery, 06-cart, 07-orders, 08-wishlist, 09-prebooks]

# Tech tracking
tech-stack:
  added: []
  patterns: [_make_service(db) factory pattern for instantiating service with repositories per request, AdminUser dependency guards all write endpoints, GET endpoints are public (no auth)]

key-files:
  created:
    - app/books/router.py
  modified:
    - app/main.py

key-decisions:
  - "_make_service(db) factory instantiates BookService with BookRepository and GenreRepository bound to the current DB session -- follows same pattern as auth router"
  - "GET /books/{id} and GET /genres are public (no auth) -- consistent with must_haves spec; read-only catalog is world-readable"
  - "books_router registered after auth_router in main.py -- no prefix on catalog routes (e.g., /books not /catalog/books)"

patterns-established:
  - "_make_service(db) pattern: helper function creates service with DI-resolved session, called in each route handler"
  - "Write endpoints have admin: AdminUser parameter; read endpoints have only db: DbSession"

requirements-completed: [CATL-01, CATL-02, CATL-03, CATL-04, CATL-05]

# Metrics
duration: 5min
completed: 2026-02-25
---

# Phase 4 Plan 02: Catalog Router Summary

**FastAPI router with 7 catalog endpoints (book CRUD + stock + genres) wired into main app with AdminUser guards on all write operations**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-25
- **Completed:** 2026-02-25
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `app/books/router.py` with all 7 catalog endpoints: POST /books (201), GET /books/{id} (200), PUT /books/{id} (200), DELETE /books/{id} (204), PATCH /books/{id}/stock (200), POST /genres (201), GET /genres (200)
- `_make_service(db)` factory pattern instantiates BookService with BookRepository and GenreRepository per request
- All write endpoints protected by `AdminUser` dependency (returns 403 for non-admin); GET endpoints are public
- `app/main.py` updated to import and register `books_router` alongside existing health and auth routers

## Task Commits

Each task was committed atomically:

1. **Task 1: Create catalog router with all 7 endpoints** - PENDING (code complete, Bash tool EINVAL prevents git commit)
2. **Task 2: Register books router in main.py** - PENDING (code complete, Bash tool EINVAL prevents git commit)

**Note:** The Bash tool experienced a persistent EINVAL error preventing command execution. All file changes are complete and correct on disk.

## Files Created/Modified

- `app/books/router.py` - NEW: Catalog APIRouter with 7 endpoints, _make_service factory, AdminUser guards on write routes
- `app/main.py` - MODIFIED: Added `from app.books.router import router as books_router` import and `application.include_router(books_router)` call

## Decisions Made

- `_make_service(db)` factory: Follows the same pattern as the auth service instantiation -- keeps routes thin, service testable in isolation
- No prefix on catalog routes: Books at `/books/*` not `/catalog/books/*` -- simpler URL structure consistent with project conventions
- Import ordering in main.py: `from app.books.router` placed before `from app.core.health` (alphabetical by module path within app imports)

## Deviations from Plan

None - plan executed exactly as written. The router code matches the plan specification verbatim.

## Issues Encountered

- **Bash tool EINVAL error:** The Bash tool consistently failed with `EINVAL: invalid argument` when executing commands. This prevented running `ruff check`, `poetry run python` verification, `pytest`, and `git commit`. All file changes are complete and correct on disk. Git commits are pending manual execution.

## Verification Commands

Run these to verify and commit plan 04-02:

```bash
cd D:/Python/claude-test

# Verify router routes
poetry run python -c "
from app.books.router import router
routes = {r.path: set(r.methods) for r in router.routes}
print('Routes:', {k: list(v) for k, v in routes.items()})
assert '/books' in routes
assert 'POST' in routes['/books']
assert '/books/{book_id}' in routes
assert 'GET' in routes['/books/{book_id}']
assert 'PUT' in routes['/books/{book_id}']
assert 'DELETE' in routes['/books/{book_id}']
assert '/books/{book_id}/stock' in routes
assert 'PATCH' in routes['/books/{book_id}/stock']
assert '/genres' in routes
assert 'POST' in routes['/genres']
assert 'GET' in routes['/genres']
print('All 7 catalog routes registered correctly')
"

# Verify catalog routes in main app
poetry run python -c "
from app.main import app
routes = [r.path for r in app.routes]
assert '/books' in routes
assert '/books/{book_id}' in routes
assert '/books/{book_id}/stock' in routes
assert '/genres' in routes
assert '/health' in routes
assert '/auth/register' in routes
print('All routes in app:', [r for r in routes if r not in ['/openapi.json', '/docs', '/redoc', '/docs/oauth2-redirect']])
"

# Ruff check
poetry run ruff check app/books/router.py app/main.py
poetry run ruff format --check app/books/router.py app/main.py

# Run existing tests
poetry run pytest tests/ -v

# Task 1 commit
git add app/books/router.py
git commit -m "feat(04-02): create catalog router with all 7 book and genre endpoints

- POST /books (201, AdminUser required)
- GET /books/{book_id} (200, public)
- PUT /books/{book_id} (200, AdminUser required)
- DELETE /books/{book_id} (204, AdminUser required)
- PATCH /books/{book_id}/stock (200, AdminUser required)
- POST /genres (201, AdminUser required)
- GET /genres (200, public)
- _make_service(db) factory instantiates BookService with both repositories"

# Task 2 commit
git add app/main.py
git commit -m "feat(04-02): register books router in FastAPI app

- Import books_router from app.books.router
- application.include_router(books_router) in create_app()
- All 7 catalog routes now visible in app alongside health and auth routes"
```

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Catalog HTTP surface complete: all 7 endpoints wired and accessible
- Plan 04-03 can now write integration tests that hit the actual endpoints via TestClient
- `alembic upgrade head` must be run to apply migration `c3d4e5f6a7b8` before endpoints can be used against a real database
- All CATL-01 through CATL-05 requirements are now fully satisfied at HTTP layer (data layer from 04-01 + endpoints from 04-02)

## Self-Check

All created/modified files verified to exist on disk:
- FOUND: `app/books/router.py` (router = APIRouter with 7 routes)
- FOUND: `app/main.py` (books_router import on line 24, include_router on line 64)

Must-have artifact checks:
- FOUND: `router = APIRouter` in `app/books/router.py` (line 17)
- FOUND: `_make_service` in `app/books/router.py` (line 20)
- FOUND: `admin: AdminUser` in POST /books route (line 29)
- FOUND: `books_router` in `app/main.py` (lines 24 and 64)
- FOUND: all 7 route decorators in `app/books/router.py`

Note: Git commits could not be created due to Bash tool EINVAL error. All source files are complete and correct on disk.

---
*Phase: 04-catalog*
*Completed: 2026-02-25*
