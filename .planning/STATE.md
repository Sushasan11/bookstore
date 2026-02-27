---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Customer Storefront
status: unknown
last_updated: "2026-02-27T11:07:02.759Z"
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
---

---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Customer Storefront
status: active
last_updated: "2026-02-27"
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** v3.0 Customer Storefront — Phase 20: Auth Integration

## Current Position

Phase: 20 of 25 (Auth Integration — in progress)
Plan: 2 of 3 (20-01 complete, advancing to 20-02)
Status: Active
Last activity: 2026-02-27 — Completed 20-01 (NextAuth.js v5 config, Google token exchange endpoint, SessionProvider)

Progress: [██░░░░░░░░] 14% (1/7 phases complete, 4/7 plans in phase 20)

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: ~10 min
- Total execution time: ~41 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19 (complete) | 3 | ~41 min | ~14 min |

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
- [19-03]: ThemeToggle uses useEffect/useState mounted guard to return null before hydration — prevents SSR/CSR theme flicker (required next-themes pattern)
- [19-03]: MobileNav Sheet open state controlled internally — enables programmatic close on link click
- [19-03]: 404 page must be explicitly themed with shadcn/ui tokens — default Next.js not-found does not inherit ThemeProvider context
- [20-01]: POST /auth/google/token new endpoint (not calling existing /auth/google): existing Authlib redirect flow conflicts with NextAuth's own OAuth state management
- [20-01]: jose decodeJwt (not verify) for FastAPI JWT claims extraction: verification is FastAPI's responsibility; decoding avoids extra /me API call
- [20-01]: Concurrent-refresh guard with module-level refreshPromise: prevents race condition when multiple server components hit jwt callback simultaneously during token expiry window
- [20-01]: Credentials authorize returns null on 4xx failures (not throw): per NextAuth v5 spec — throw triggers 500, null triggers CredentialsSignin error with clean UX

### Blockers/Concerns

- [Phase 20]: Google OAuth requires user to configure Google Cloud Console credentials and run npx auth secret — documented in 20-01-SUMMARY.md User Setup section
- [Phase 25]: Star rating selector not in shadcn/ui — evaluate community extensions vs. small custom component before phase starts

### Pending Todos

None.

## Session Continuity

Last session: 2026-02-27
Stopped at: Completed 20-01-PLAN.md — NextAuth.js v5 session layer established, ready for 20-02 (Auth UI)
Resume file: None
