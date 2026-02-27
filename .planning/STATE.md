---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Customer Storefront
status: active
last_updated: "2026-02-27"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** v3.0 Customer Storefront — Phase 19: Monorepo + Frontend Foundation

## Current Position

Phase: 19 of 25 (Monorepo + Frontend Foundation)
Plan: 3 of 3
Status: Active
Last activity: 2026-02-27 — In progress 19-03 (layout shell, health check home page — paused at checkpoint Task 3)

Progress: [░░░░░░░░░░] 0% (0/7 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 8 min
- Total execution time: 16 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19 (in progress) | 2 | 16 min | 8 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Recent decisions affecting v3.0 work:

- [v3.0 Roadmap]: Next.js 15 App Router with NextAuth.js v5 as JWT bridge to FastAPI — no BFF proxy, FastAPI is auth authority
- [v3.0 Roadmap]: Flat monorepo (no Turborepo) — `backend/` Python + `frontend/` Next.js, no shared JS packages
- [v3.0 Roadmap]: openapi-typescript v7 + openapi-fetch for zero-runtime-cost typed API client auto-generated from FastAPI `/openapi.json`
- [v3.0 Roadmap]: TanStack Query v5 for server state; Zustand v5 context-provider pattern for cart display state (SSR-safe)
- [19-01]: CORSMiddleware uses explicit ALLOWED_ORIGINS (not wildcard) — required for allow_credentials=True; includes both localhost:3000 and 127.0.0.1:3000
- [19-01]: CORSMiddleware registered last in add_middleware() — FastAPI reverse execution order makes it run first (CORS before session)
- [19-02]: QueryClient created in useState factory pattern — prevents shared state across SSR requests
- [19-02]: openapi-typescript v7 generates types from live FastAPI /openapi.json — backend must be running to regenerate types
- [19-02]: Next.js 16 --yes creates flat layout (no src/) — restructured to src/ and updated tsconfig @/* and components.json paths

### Blockers/Concerns

- [Phase 20]: Google OAuth token exchange (NextAuth → FastAPI) is a non-standard pattern — plan a focused sub-task using PITFALLS.md code patterns
- [Phase 25]: Star rating selector not in shadcn/ui — evaluate community extensions vs. small custom component before phase starts

### Pending Todos

None.

## Session Continuity

Last session: 2026-02-27
Stopped at: 19-03-PLAN.md Task 3 checkpoint — awaiting human verification of responsive layout and backend connectivity
Resume file: None
