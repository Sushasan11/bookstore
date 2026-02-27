---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Customer Storefront
status: unknown
last_updated: "2026-02-27T14:27:49.240Z"
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
---

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
**Current focus:** v3.0 Customer Storefront — Phase 21: Catalog and Search

## Current Position

Phase: 21 of 25 (Catalog and Search)
Plan: 3 of 4 complete (21-03 — book detail page with ISR, JSON-LD, Open Graph, sub-components)
Status: Active
Last activity: 2026-02-27 — Completed 21-03 (ISR book detail page at /books/[id] with JSON-LD Book schema, Open Graph metadata, BookDetailHero, BreadcrumbNav, RatingDisplay, ActionButtons, MoreInGenre)

Progress: [████░░░░░░] 35% (2/7 phases complete, 3/4 plans in phase 21 complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: ~8 min
- Total execution time: ~65 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19 (complete) | 3 | ~41 min | ~14 min |
| 20 (complete) | 3 | ~28 min | ~9 min |
| 21 (in progress) | 3/4 | ~38 min | ~13 min |

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
- [20-02]: Suspense boundary required around components using useSearchParams() in Next.js static builds — caught by npm run build, not TypeScript
- [20-02]: proxy.ts uses named export const proxy = auth(...) (not export default): Next.js 16 requires named proxy export per pitfall documentation
- [20-02]: UserMenu as separate 'use client' component with mounted guard: keeps Header as server component, prevents SSR/CSR hydration mismatch
- [20-02]: AuthGuard as child component inside SessionProvider: calls useSession() to watch session.error and trigger signOut on RefreshTokenError
- [21-01]: avg_rating sort uses LEFT JOIN subquery on reviews with nulls_last() — books without reviews sort last in both asc and desc directions
- [21-01]: Price range added as backend params (min_price/max_price) — client-side filtering rejected as unviable at scale
- [21-01]: BookCard is a pure server component (no 'use client') — uses next/link and next/image for SSR performance
- [21-01]: remotePatterns uses https://** (permissive) — covers any future cover image CDN without config changes
- [21-02]: SearchControls and Pagination wrapped in Suspense on catalog page — useSearchParams() requires Suspense boundary for Next.js static build
- [21-02]: Sort encoded as composite key (price_asc, price_desc, avg_rating) in Select, mapped to sort+sort_dir params at update time
- [21-02]: BookGrid as async server component — fetches popular books server-side on empty results without client waterfall
- [21-03]: React.cache() wraps fetchBook so generateMetadata and page component share a single cached request — avoids double fetch
- [21-03]: ActionButtons are disabled placeholders — Phase 22 (cart) and Phase 24 (wishlist) will enable them
- [21-03]: MoreInGenre fetches size=7, filters current book, slices to 6 — avoids separate count query

### Blockers/Concerns

- [Phase 20]: Google OAuth requires user to configure Google Cloud Console credentials and run npx auth secret — documented in 20-01-SUMMARY.md User Setup section
- [Phase 25]: Star rating selector not in shadcn/ui — evaluate community extensions vs. small custom component before phase starts

### Pending Todos

None.

## Session Continuity

Last session: 2026-02-27
Stopped at: Completed 21-03-PLAN.md — ISR book detail page at /books/[id] with JSON-LD Book schema, Open Graph metadata, breadcrumbs, rating display, disabled action buttons, and MoreInGenre section
Resume file: None
