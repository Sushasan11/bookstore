---
phase: 19-monorepo-frontend-foundation
plan: 01
subsystem: infra
tags: [monorepo, fastapi, cors, npm, concurrently, poetry]

# Dependency graph
requires: []
provides:
  - "backend/ directory with all Python code and git history preserved"
  - "CORSMiddleware on FastAPI allowing http://localhost:3000 and http://127.0.0.1:3000"
  - "Root package.json with concurrently for coordinated dev scripts"
  - "Updated .gitignore covering both Python and Node.js patterns"
affects: [20-nextjs-setup, 21-api-types, 22-auth-integration, 23-product-catalog, 24-cart-checkout, 25-reviews]

# Tech tracking
tech-stack:
  added: [concurrently@9.2.1, fastapi.middleware.cors.CORSMiddleware]
  patterns:
    - "Monorepo flat structure: backend/ (Python/Poetry) + frontend/ (Next.js/npm) at root"
    - "CORSMiddleware registered after SessionMiddleware (reverse order = runs first)"
    - "Explicit ALLOWED_ORIGINS list (never wildcard) with allow_credentials=True"
    - "Root package.json with npm workspaces-free concurrently for cross-service dev"

key-files:
  created:
    - "package.json - root monorepo convenience scripts using concurrently"
    - "package-lock.json - concurrently@9.2.1 lockfile"
    - "backend/ - all Python code relocated from flat repo root"
  modified:
    - "backend/app/main.py - added CORSMiddleware with explicit origins"
    - "backend/app/core/config.py - expanded ALLOWED_ORIGINS to include 127.0.0.1:3000"
    - ".gitignore - added Node.js/frontend patterns (node_modules/, .next/, .turbo/)"

key-decisions:
  - "Flat monorepo (no Turborepo) — backend/ + frontend/ at root, no shared JS packages"
  - "CORSMiddleware uses explicit ALLOWED_ORIGINS not wildcard — required for allow_credentials=True (browsers reject wildcard + credentials)"
  - "ALLOWED_ORIGINS includes both localhost:3000 and 127.0.0.1:3000 — browsers treat them as different origins"
  - "CORSMiddleware registered last in add_middleware() calls — FastAPI runs middleware in reverse order so it executes first"

patterns-established:
  - "All backend work done from backend/ directory: cd backend && poetry run ..."
  - "Frontend work done from frontend/ directory: cd frontend && npm run ..."
  - "Root npm scripts (dev, dev:backend, dev:frontend) for dev convenience"

requirements-completed: [FOUND-01, FOUND-03]

# Metrics
duration: 6min
completed: 2026-02-27
---

# Phase 19 Plan 01: Monorepo Frontend Foundation Summary

**Flat Python repo restructured into monorepo with backend/ using git mv (history preserved), CORSMiddleware added for frontend origin access, and root package.json with concurrently@9.2.1 for coordinated dev scripts**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-27T10:16:24Z
- **Completed:** 2026-02-27T10:22:59Z
- **Tasks:** 2
- **Files modified:** 6 (plus 110 renamed files via git mv)

## Accomplishments
- Moved all Python backend code into `backend/` subdirectory with `git mv`, preserving full git history (verified via `git log --follow backend/app/main.py`)
- Added `CORSMiddleware` to FastAPI's `create_app()` with explicit `ALLOWED_ORIGINS` including both `localhost:3000` and `127.0.0.1:3000` variants
- Created root `package.json` with `concurrently` for single-command dev startup; all 301 backend tests pass after restructure

## Task Commits

Each task was committed atomically:

1. **Task 1: Move all backend code into backend/ directory using git mv** - `a926a70` (refactor)
2. **Task 2: Add CORSMiddleware to FastAPI and create root package.json** - `541200b` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/app/main.py` - Added CORSMiddleware import and registration after SessionMiddleware
- `backend/app/core/config.py` - Expanded ALLOWED_ORIGINS default to include http://127.0.0.1:3000
- `package.json` - Root monorepo convenience scripts (dev, dev:backend, dev:frontend) using concurrently
- `package-lock.json` - Lockfile for concurrently@9.2.1
- `.gitignore` - Added Node.js/frontend patterns: node_modules/, .next/, out/, .turbo/
- `backend/` - All Python code moved here from repo root (app/, tests/, alembic/, scripts/, pyproject.toml, poetry.lock, alembic.ini, docker-compose.yml, .env.example)

## Decisions Made
- CORSMiddleware uses explicit ALLOWED_ORIGINS (not `["*"]`) because browsers reject wildcard origins with `allow_credentials=True`
- ALLOWED_ORIGINS includes both `http://localhost:3000` and `http://127.0.0.1:3000` because browsers treat them as distinct origins
- CORSMiddleware registered after SessionMiddleware in code — FastAPI middleware executes in reverse registration order, so CORS runs first (required: OPTIONS preflight must be handled before session processing)
- Flat monorepo layout (no Turborepo/workspace packages) as decided in v3.0 roadmap

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `.env` was not git-tracked (in .gitignore), so `git mv .env backend/.env` failed. Used `cp .env backend/.env && rm .env` instead. No impact on functionality.
- `poetry run alembic current` fails with a DB connection error (Postgres not running in dev) — this is expected environment behavior, not an import error. Plan requirement was "runs without import errors" — confirmed by 301 passing tests that import all modules.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Monorepo structure is ready — Phase 20 can create `frontend/` directory for Next.js setup
- CORSMiddleware is active — frontend at localhost:3000 can make credentialed requests to FastAPI at localhost:8000
- Root `npm run dev:backend` starts uvicorn from `backend/` directory
- All 301 backend tests pass from `cd backend && poetry run pytest`

---
*Phase: 19-monorepo-frontend-foundation*
*Completed: 2026-02-27*
