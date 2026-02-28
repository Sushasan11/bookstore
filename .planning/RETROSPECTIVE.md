# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Pre-booking, Notifications & Admin

**Shipped:** 2026-02-26
**Phases:** 4 | **Plans:** 8 | **Sessions:** 1

### What Was Built
- Async email infrastructure with fastapi-mail, Jinja2 templates, plain-text fallback, BackgroundTasks dispatch
- Admin user management: paginated list with role/active filtering, deactivate/reactivate with immediate lockout
- Pre-booking system: reserve/view/cancel out-of-stock books, atomic restock broadcast notification
- Transactional emails: order confirmation after checkout, restock alerts to all waiting pre-bookers

### What Worked
- Wave-based parallel execution kept orchestrator context lean while subagents got fresh 200k each
- Phase verification after each execute-phase caught issues early (e.g., multipart email structure fix)
- Explicit interfaces in PLANs (exact signatures, import paths) eliminated guesswork for executors
- Batch email lookup pattern (single IN query) avoided N+1 from the start — no retrofit needed

### What Was Inefficient
- ROADMAP.md plan checkboxes not updated by executors (still showed `[ ]` after completion) — manual fix needed at milestone close
- 11-01 SUMMARY showed `requirements-completed: []` (empty) despite completing all PRBK requirements — frontmatter inconsistency caught by audit cross-reference
- Phase 12 `book_id` passed in restock email context but never rendered in template — dead-weight context key

### Patterns Established
- Email enqueue AFTER service call: structural guarantee that no email fires on failure paths
- Local imports inside function bodies for cross-module repository access (avoids circular imports)
- `get_email_service.cache_clear()` in test teardown for lru_cache-decorated singletons
- `fm.record_messages()` is a sync context manager in fastapi-mail 1.6.2 (not async)
- Partial unique index for "one active per user" constraints (pre-booking)

### Key Lessons
1. JWT payloads should stay minimal (sub + role only) — fetch user details from DB when needed for emails
2. Pydantic `@computed_field` values are only available on the schema, not the ORM model — build response before constructing email context
3. fastapi-mail wraps multipart/alternative in multipart/mixed — recursive traversal needed for HTML body extraction in tests

### Cost Observations
- Model mix: ~10% opus (orchestrator), ~90% sonnet (executors, verifiers, checkers)
- Sessions: 1 (entire milestone in single context)
- Notable: 4 phases executed, verified, and audited in one session

---

## Milestone: v2.0 — Reviews & Ratings

**Shipped:** 2026-02-27
**Phases:** 3 | **Plans:** 5 | **Sessions:** 1

### What Was Built
- Review model with unique/check constraints, full repository (7 async methods), and purchase verification gate
- Complete review CRUD endpoints: create with purchase gate + duplicate 409, list (paginated), get, update (PATCH), delete (soft-delete)
- Ownership enforcement + admin moderation bypass on update/delete
- Live avg_rating and review_count aggregates on book detail endpoint
- 62 integration tests across 3 test files covering all 10 requirements

### What Worked
- Interfaces block in PLANs (exact code snippets from codebase) gave executors zero-ambiguity context
- Phase 14 verification caught missing `selectinload(Review.book)` in list_for_book — fixed before Phase 15 started
- 3-source requirements cross-reference (VERIFICATION + SUMMARY frontmatter + traceability table) caught no gaps — clean milestone
- Single-session execution: plan + execute + verify + audit for all 3 phases without /clear

### What Was Inefficient
- ROADMAP.md Progress table formatting drifted (Phase 13-14 rows had misaligned columns) — needs standardization
- `summary-extract --fields one_liner` returned null for all summaries — extractor doesn't parse bold header lines, required manual grep
- Phase 14 VERIFICATION body said "gaps_found" but frontmatter was updated to "passed" after fix — body/frontmatter inconsistency

### Patterns Established
- `_UNSET` sentinel for PATCH endpoints: distinguishes "not provided" from explicit null via `model_fields_set`
- Cross-domain repo injection in router: ReviewRepository in books router, OrderRepository in ReviewService — avoids circular imports
- Dict-merge `model_validate({**orm_attrs, **computed})` when ORM object lacks fields needed by response schema
- DuplicateReviewError registered before AppError — specific exception handlers must precede general ones
- Re-fetch after update via `get_by_id()` instead of `session.refresh()` when selectinload is needed

### Key Lessons
1. Eager-load auditing is critical in async SQLAlchemy — every relationship access must be covered by selectinload or the query will silently work when objects are cached but fail in production
2. Exception handler registration order in FastAPI matters — more specific handlers must be added before general ones
3. Dict-based model_validate is the right pattern when response schemas include fields not present on the ORM model

### Cost Observations
- Model mix: ~10% opus (orchestrator), ~90% sonnet (executors, verifiers, checkers)
- Sessions: 1 (entire milestone in single context)
- Notable: 3 phases + audit + UAT completed in one session (~35 min total execution)

---

## Milestone: v2.1 — Admin Dashboard & Analytics

**Shipped:** 2026-02-27
**Phases:** 3 | **Plans:** 5 | **Sessions:** 1

### What Was Built
- Sales analytics stack: revenue summary with period comparison (today/week/month), AOV, delta percentage, top-selling books by revenue and volume
- Low-stock inventory endpoint with configurable threshold, ascending ordering, and per-item threshold echo
- Admin review moderation: paginated list with AND-combined filters (book/user/rating range), date/rating sort, bulk soft-delete
- 66 integration tests across 3 test files covering all admin analytics and moderation endpoints

### What Worked
- Phase 16 router-level admin guard (`dependencies=[Depends(require_admin)]`) automatically protected all subsequent endpoints added to the same router (Phase 17 got auth for free)
- Pre-building BulkDelete schemas in Plan 18-01 for Plan 18-02 — clean separation, zero schema modifications in second plan
- Audit 3-source cross-reference caught frontmatter gaps (SALES-01/02 and INV-01 missing from `requirements_completed`) — documentation-only issue, code was correct
- Direct repo-to-router pattern for simple aggregates avoided unnecessary service layers in 3 of 5 plans

### What Was Inefficient
- ROADMAP.md Progress table had column alignment issues in Phase 16-18 rows (milestone column missing, dates misplaced) — manual cleanup needed
- STATE.md accumulated 3 duplicate YAML frontmatter blocks from repeated CLI updates — needed full rewrite at milestone close
- Test email collision between `test_sales_analytics.py` and `test_orders.py` (shared `orders_admin@example.com`) — flaky test in full-suite runs, deferred as tech debt

### Patterns Established
- Router-level admin guard at `APIRouter()` constructor: all endpoints on the router inherit protection automatically
- Direct repo endpoint pattern: simple aggregate queries bypass service layer, only use service for computed logic (period bounds, delta %)
- `client.request("DELETE", url, json=...)` for httpx DELETE with JSON body — `client.delete()` doesn't accept `json` kwarg
- Threshold echo pattern: include the request parameter in each response item for self-contained dashboard rendering
- `select(func.count()).select_from(stmt.subquery())` for filter-then-count that shares exact filter constraints with data query

### Key Lessons
1. Service layers should earn their existence — only add when there's actual business logic (period bounds, delta calculation), not for simple query forwarding
2. Pre-building schemas for the next plan reduces cross-plan coupling and enables clean plan boundaries
3. Unique email fixtures per test file are essential — shared emails cause flaky failures that only manifest in full-suite runs

### Cost Observations
- Model mix: ~10% opus (orchestrator), ~90% sonnet (executors, verifiers, checkers)
- Sessions: 1 (entire milestone in single context)
- Notable: 3 phases + audit completed in one session, milestone completion in separate session

---

## Milestone: v3.0 — Customer Storefront

**Shipped:** 2026-02-28
**Phases:** 7 | **Plans:** 22 | **Sessions:** ~4

### What Was Built
- Monorepo restructure (backend/ + frontend/) with CORS, auto-generated TypeScript types, and responsive layout shell with dark mode
- NextAuth.js v5 auth with email/password and Google OAuth, JWT bridge to FastAPI, route protection, 403 auto-signout
- SSR catalog with full-text search, URL-persisted filters, ISR book detail pages, JSON-LD and Open Graph SEO
- Full cart/checkout with optimistic updates via TanStack Query, checkout dialog, order confirmation page
- Order history, account hub, wishlist with instant heart toggle, pre-booking for out-of-stock titles
- Reviews CRUD on book detail page with verified-purchase gate, star rating selector, edit/delete with confirmation

### What Worked
- openapi-typescript auto-generation kept TypeScript types in perfect sync with FastAPI Pydantic schemas — zero manual type duplication
- TanStack Query with shared query keys (CART_KEY, WISHLIST_KEY, REVIEWS_KEY) enabled reactive cache invalidation across components (CartBadge, BookCard, ActionButtons all stay in sync)
- Established useEffect/useState mounted guard pattern early (Phase 19 ThemeToggle) — reused in UserMenu, CartBadge across 3 later phases with zero hydration issues
- proxy.ts named export pattern for Next.js 16 route protection — cleaner than middleware, caught early in Phase 20
- React.cache() for SSR request deduplication (generateMetadata + page share one fetch) — applied in Phase 21, replicated in Phase 25

### What Was Inefficient
- BookCard started as server component (Phase 21) then converted to client component (Phase 22) — could have been planned as client from the start given known cart/wishlist interactivity
- ActionButtons started as disabled placeholders (Phase 21) then wired in Phases 22 and 24 — placeholder approach required revisiting the same file 3 times
- ROADMAP.md Progress table formatting drifted significantly (misaligned columns, inconsistent milestone labels) — needed full rewrite at milestone close
- STATE.md accumulated 6 duplicate YAML frontmatter blocks from repeated CLI updates — needed full rewrite at milestone close

### Patterns Established
- useEffect/useState mounted guard for all client components that differ between SSR and CSR (theme, auth, cart badge)
- e.preventDefault() + e.stopPropagation() on interactive elements inside Link components (cart icon, heart icon)
- Optimistic update with rollback via TanStack Query onMutate/onError/onSettled — applied to cart, wishlist, pre-booking
- SSR-seeded initialData with TanStack Query hydration — server component fetches, client component subscribes via same cache key
- Separate useQuery in consumer (not modifying original hook) when initialData pattern differs from hook's default behavior

### Key Lessons
1. Plan components as client from the start if any phase will add interactivity — server-to-client conversion requires touching every consumer
2. URL-persisted search state via useSearchParams needs Suspense boundaries — not caught by TypeScript, only by `npm run build`
3. Named export patterns for Next.js proxy/middleware must be verified against the exact Next.js version — docs lag behind releases
4. TanStack Query cache key design is critical upfront — CART_KEY (global), REVIEWS_KEY(bookId) (parameterized), WISHLIST_KEY (global) each have different invalidation semantics
5. React.cache() is SSR-only and request-scoped — perfect for generateMetadata + page dedup, but irrelevant for client components

### Cost Observations
- Model mix: ~15% opus (orchestrator, milestone ops), ~85% sonnet (executors, verifiers, researchers)
- Sessions: ~4 (spread across 2 days)
- Notable: 7 phases (22 plans) completed in ~2 days — largest milestone by phase count, fastest per-phase due to established frontend patterns

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multiple | 8 | Initial project setup, established patterns |
| v1.1 | 1 | 4 | Wave-based execution, integration audit |
| v2.0 | 1 | 3 | Interfaces block in PLANs, 3-source req cross-reference |
| v2.1 | 1 | 3 | Direct repo pattern for simple aggregates, pre-built schemas across plans |
| v3.0 | ~4 | 7 | Full frontend milestone, SSR+client patterns, TanStack Query cache architecture |

### Cumulative Quality

| Milestone | Tests | LOC | New Tests |
|-----------|-------|-----|-----------|
| v1.0 | 121 | 6,763 | 121 |
| v1.1 | 179 | 9,473 | 58 |
| v2.0 | 240 | 12,010 | 62 |
| v2.1 | ~306 | 13,743 | 66 |
| v3.0 | ~306 | 22,750 (14,728 py + 8,022 ts) | 0 (frontend, no new backend tests) |

### Top Lessons (Verified Across Milestones)

1. Explicit interface contracts in plans (signatures, imports, types) dramatically reduce executor deviations
2. Structural guarantees (ordering, guards) are more reliable than runtime checks for correctness invariants
3. Eager-load auditing is critical in async SQLAlchemy — phase verification catches missing selectinloads before they hit production
4. Service layers should earn their existence — skip for simple aggregates, add only when business logic (period bounds, deltas) is present
5. Establish component patterns (mounted guard, optimistic update, SSR dedup) early — they compound across phases as every new feature reuses them
