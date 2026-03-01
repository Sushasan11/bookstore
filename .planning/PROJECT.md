# BookStore

## What This Is

A full-stack online bookstore with a FastAPI backend and Next.js storefront plus admin dashboard. Users can browse an SEO-optimized catalog, search and filter books, sign in with email or Google OAuth, manage a shopping cart with optimistic updates, checkout, review order history, maintain wishlists, pre-book out-of-stock titles, and leave verified-purchase reviews with star ratings. Admins access a protected dashboard at `/admin` with KPI analytics, sales charts, full book catalog CRUD, user management (deactivate/reactivate), and review moderation (single + bulk delete) — all with automatic storefront cache revalidation. Monorepo structure: `backend/` (Python/FastAPI) and `frontend/` (Next.js/TypeScript).

## Core Value

Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## Requirements

### Validated

- ✓ Admin can add, edit, and delete books with full details — v1.0
- ✓ Admin can manage book stock quantities — v1.0
- ✓ Users can sign up, log in (email + Google/GitHub OAuth), and authenticate via JWT — v1.0
- ✓ Users can browse and search/filter books by title, author, or genre (FTS) — v1.0
- ✓ Users can add books to a shopping cart and checkout (mock payment) — v1.0
- ✓ Users can view their order history with price-at-purchase snapshots — v1.0
- ✓ Users can add/remove books from a personal wishlist — v1.0
- ✓ Books have tracked stock quantities with race-condition-safe decrement — v1.0
- ✓ Role-based access: admin manages catalog, users shop — v1.0
- ✓ Async email infrastructure with BackgroundTasks (never blocks API, never sends before commit) — v1.1
- ✓ Order confirmation email after successful checkout — v1.1
- ✓ Restock alert email for pre-booked books — v1.1
- ✓ Jinja2 HTML email templates with plain-text fallback — v1.1
- ✓ Pre-booking for out-of-stock books (reserve, view, cancel) — v1.1
- ✓ Atomic restock notification broadcast to all waiting pre-bookers — v1.1
- ✓ Admin paginated user list with role/active filtering — v1.1
- ✓ Admin deactivate/reactivate users with immediate lockout — v1.1
- ✓ Admin cannot deactivate admin accounts — v1.1
- ✓ Users who purchased a book can leave a 1-5 star rating with optional text review — v2.0
- ✓ One review per user per book (verified purchase required) — v2.0
- ✓ Users can edit their own review — v2.0
- ✓ Users can delete their own review — v2.0
- ✓ Admin can delete any review — v2.0
- ✓ Book detail shows average rating and review count — v2.0
- ✓ Admin can view revenue summary (total revenue, order count, AOV) for today, this week, or this month — v2.1
- ✓ Admin can view period-over-period comparison (delta % vs previous period) alongside revenue summary — v2.1
- ✓ Admin can view top-selling books ranked by revenue with book title, author, units sold, and total revenue — v2.1
- ✓ Admin can view top-selling books ranked by volume (units sold) with book title and author — v2.1
- ✓ Admin can query books with stock at or below a configurable threshold, ordered by stock ascending — v2.1
- ✓ Admin can list all reviews with pagination, sort (by date or rating), and filter (by book, user, or rating range) — v2.1
- ✓ Admin can bulk-delete reviews by providing a list of review IDs — v2.1
- ✓ Monorepo restructured with backend/ and frontend/ directories — v3.0
- ✓ Next.js 15 storefront with SSR catalog, ISR book detail, JSON-LD and Open Graph SEO — v3.0
- ✓ NextAuth.js v5 auth with email/password and Google OAuth, JWT bridge to FastAPI — v3.0
- ✓ Shopping cart with optimistic updates, checkout dialog, order confirmation — v3.0
- ✓ Order history and account hub with navigation — v3.0
- ✓ Wishlist with instant heart toggle and pre-booking for out-of-stock titles — v3.0
- ✓ Reviews CRUD on book detail page with verified-purchase gate and star ratings — v3.0
- ✓ URL-persisted search and filter state (bookmarkable, shareable) — v3.0
- ✓ Responsive mobile-first layout with header, navigation, footer, and dark mode — v3.0
- ✓ Admin dashboard overview with KPI cards, period selector, delta badges, and top-5 best-sellers — v3.1
- ✓ Sales analytics with Recharts revenue comparison chart, top-sellers table with revenue/volume toggle — v3.1
- ✓ Book catalog CRUD with paginated table, search/filter, validated add/edit forms, delete confirmation, stock update modal — v3.1
- ✓ User management with paginated table, role/status filters, deactivate/reactivate with confirmation — v3.1
- ✓ Review moderation with paginated table, 6-control filter bar, single + bulk delete with checkbox selection — v3.1
- ✓ Inventory low-stock alerts with configurable threshold, color-coded badges, shared stock update modal — v3.1
- ✓ Defense-in-depth admin protection (middleware Layer 1 + Server Component Layer 2) — v3.1
- ✓ Admin mutation → storefront cache revalidation via fire-and-forget triggerRevalidation + POST /api/revalidate — v3.1

### Active

<!-- Current milestone: v4.1 Clean House -->

- [ ] Extract duplicated DeltaBadge to shared admin component
- [ ] Consolidate StockBadge into single configurable component
- [ ] Fix updateBookStock return type (Promise<void> → Promise<BookResponse>)
- [ ] Make top-sellers table period-aware (respect period selector)
- [ ] Update SUMMARY frontmatter (26-02, 27-01 missing requirement IDs)
- [ ] Validate email improvements end-to-end

## Out of Scope

- Real payment integration (Stripe, etc.) — mock payment sufficient
- Mobile app — API-first, web/API only
- Social features beyond reviews (commenting, following users) — not a social platform
- Multiple storefronts or multi-tenant — single bookstore
- Recommendation engine — ~~needs transaction data first~~ planned for v4.2
- Real-time notifications (WebSocket) — email sufficient for restock alerts
- Celery / Redis task queue — BackgroundTasks sufficient at current volume
- Helpfulness voting on reviews — defer until review volume justifies it
- Pre-moderation queue — reactive admin-delete is correct; pre-moderation suppresses authentic reviews
- Rating sort in search results — deferred, keep focused on core review CRUD
- GitHub OAuth on frontend — email + Google sufficient

## Context

Shipped v3.1 with ~11,300 LOC TypeScript (frontend) + 14,728 LOC Python (backend), ~306 backend tests passing.
Tech stack: FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, Poetry, fastapi-mail (backend); Next.js 15, TypeScript, TanStack Query, Recharts, TanStack Table, shadcn/ui, Tailwind CSS, NextAuth.js v5 (frontend).
30 phases delivered across 6 milestones (v1.0: 8, v1.1: 4, v2.0: 3, v2.1: 3, v3.0: 7, v3.1: 5 phases).
Full customer storefront + admin dashboard surfacing all backend admin endpoints.
v3.1 added ~3,300 LOC across 70 files in 2 days (29 commits). 28 requirements satisfied, 0 gaps.

## Quality Principles

> **These principles are NON-NEGOTIABLE and apply to ALL milestones and phases.**

### 1. Visual & E2E Testing Required
Every phase must include launching the server and visually testing the UI flows — not just running unit/integration tests. Both backend and frontend must be confirmed working together as intended. This is especially critical for complex logic. Plans must account for this: think through test scenarios thoroughly, cover edge cases in actual browser interaction, and verify the full user journey end-to-end.

### 2. Proactive UI/UX Excellence
Always proactively think through and act on excellent UI/UX principles. This means: intuitive menu navigation, clean presentation, logical user flow, and thoughtful interaction design. Don't just implement features — consider how users will actually experience them. Every UI change should be evaluated for clarity, consistency, and ease of use before it ships.

## Constraints

- **Backend Stack**: Python 3.11+, FastAPI, Poetry, PostgreSQL, SQLAlchemy + Alembic
- **Frontend Stack**: Next.js 15 (App Router), TypeScript, TanStack Query, shadcn/ui, Tailwind CSS
- **Auth**: JWT tokens (access + refresh), DB is_active check per request; NextAuth.js on frontend
- **Payments**: Mock/simulated only — no real payment gateway
- **Email**: fastapi-mail with SMTP, BackgroundTasks dispatch
- **Repo Structure**: Monorepo — `backend/` (Python) + `frontend/` (Next.js) at repo root
- **Dev Tooling**: Claude Code MCP

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Django/Flask | Async-native, automatic OpenAPI docs, modern Python patterns | ✓ Good |
| PostgreSQL over SQLite | Production-grade, concurrent access, full-text search | ✓ Good |
| SQLAlchemy + Alembic | Industry standard ORM with robust migration support | ✓ Good |
| JWT over sessions | Stateless auth, scales for API-first | ✓ Good |
| Mock payments | Reduces v1 complexity | ✓ Good |
| SELECT FOR UPDATE stock locking | Race-condition-safe checkout, ascending ID order prevents deadlocks | ✓ Good |
| Opaque refresh tokens (not JWT) | Simpler DB revocation, family-based theft detection | ✓ Good |
| CASCADE vs SET NULL on FKs | CASCADE for wishlist (meaningless without book), SET NULL for orders (preserve history) | ✓ Good |
| fastapi-mail + BackgroundTasks | No Celery/Redis overhead at this scale, post-response dispatch | ✓ Good |
| DB is_active check per request | Immediate lockout without JWT blacklisting, 1 extra query acceptable | ✓ Good |
| Pre-booking soft-delete (CANCELLED) | Audit trail, re-reservation after cancel via partial unique index | ✓ Good |
| Batch email lookup (IN query) | N+1-free restock alerts, single query for all notified users | ✓ Good |
| Reviews CASCADE FK | Reviews without a book are meaningless; CASCADE on book deletion | ✓ Good |
| Live SQL aggregates (not stored) | avg_rating/review_count via SQL AVG/COUNT, no denormalized columns on books table | ✓ Good |
| Cross-domain repo injection | ReviewRepository in books router, OrderRepository in ReviewService — avoids circular imports | ✓ Good |
| DuplicateReviewError separate from AppError | 409 body needs existing_review_id which AppError handler can't produce | ✓ Good |
| model_fields_set sentinel for PATCH | Distinguishes "omitted" from explicit null on review text field | ✓ Good |
| Single DELETE endpoint (user + admin) | is_admin flag passed to service; no separate admin route needed | ✓ Good |
| Router-level admin guard for analytics | `dependencies=[Depends(require_admin)]` at APIRouter constructor protects all endpoints automatically | ✓ Good |
| Live SQL aggregates for analytics | Direct queries on orders/order_items/books tables; no materialized views or denormalization needed at current volume | ✓ Good |
| No service layer for simple aggregates | Top-books, low-stock, review-list go directly to repository — service layer only for period/delta logic | ✓ Good |
| Bulk soft-delete via single UPDATE...WHERE IN | O(1) DB round-trips, returns rowcount for best-effort semantics | ✓ Good |
| AOV = 0.0 when no orders, delta = null when prior = 0 | Consistent zero-state semantics, avoids division by zero | ✓ Good |
| Next.js 15 over Vite SPA | SSR for SEO on public catalog pages, App Router for layouts, built-in middleware for auth | ✓ Good |
| openapi-typescript for API types | Auto-generate TypeScript types from FastAPI OpenAPI spec, keeps Pydantic ↔ TS in sync | ✓ Good |
| NextAuth.js v5 as JWT bridge | Frontend auth via encrypted cookie, FastAPI remains auth authority, no BFF proxy needed | ✓ Good |
| TanStack Query for server state | Cache invalidation, optimistic updates, and deduplication — proven pattern for API-driven UIs | ✓ Good |
| proxy.ts over middleware | Next.js 16 named export pattern for route protection, cleaner than middleware matcher | ✓ Good |
| Optimistic updates with rollback | Instant UI feedback for cart/wishlist, automatic rollback on server error via TanStack Query | ✓ Good |
| React.cache() for SSR dedup | generateMetadata and page component share single cached fetch — avoids double data loading | ✓ Good |
| (store)/ route group restructure | Customer routes in route group, admin in separate layout — no accidental Header/Footer leakage | ✓ Good |
| CVE-2025-29927 defense-in-depth | middleware.ts (Layer 1 edge) + admin/layout.tsx Server Component (Layer 2) — independent role checks | ✓ Good |
| Recharts via shadcn chart CLI | `npx shadcn@latest add chart` installs recharts + ChartContainer wrapper; `next/dynamic({ ssr: false })` prevents hydration errors | ✓ Good |
| Generic DataTable + AdminPagination | Reusable across catalog, users, reviews — single implementation with TanStack Table v8 | ✓ Good |
| Self-contained StockUpdateModal | Owns its own useMutation + queryClient — reusable in both catalog and inventory without prop drilling | ✓ Good |
| adminKeys hierarchical query key factory | Single source of query keys in admin.ts — enables scoped cache invalidation per admin section | ✓ Good |
| Fire-and-forget triggerRevalidation | Admin UX not blocked by cache revalidation latency; ISR revalidate=3600 as fallback safety net | ✓ Good |
| Path-based revalidation over tag-based | No need to retrofit `next: { tags }` across existing fetch calls — revalidatePath sufficient | ✓ Good |
| Claude Code MCP for development | AI-assisted development across all phases | Active |

## Current Milestone: v4.1 Clean House

**Goal:** Resolve all tech debt from v3.1 audit and establish a clean slate before feature work in v4.2.

**Target features:**
- Extract duplicated DeltaBadge to shared component
- Consolidate StockBadge into single configurable component
- Fix updateBookStock response type mismatch
- Make top-sellers table period-aware
- Update incomplete SUMMARY frontmatter
- Validate email improvements end-to-end

**Future milestones:**
- v4.2 Customer Experience — Recommendation engine, customer dashboard, search improvements
- v4.3 Quality & Hardening — Frontend tests, performance, accessibility, security

---
*Last updated: 2026-03-02 after v4.1 milestone started*
