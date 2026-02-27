# BookStore

## What This Is

An online bookstore API where administrators manage a catalog of books (with details, pricing, and stock) and users can browse, search, purchase books through a cart/checkout flow, maintain wishlists, pre-book out-of-stock titles, leave verified-purchase reviews with ratings, and receive transactional emails. Admins have user lifecycle management, review moderation, and operational analytics (sales, inventory, reviews). Built with FastAPI, PostgreSQL, SQLAlchemy, and managed with Poetry.

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

### Active

<!-- No active milestone — backend complete through v2.1, next milestone TBD -->

(None — all backend milestones shipped. Next: v3.0 Frontend or new backend milestone.)

### Frontend (Planned)

Next.js 15 (App Router) + TypeScript frontend, to be built after backend milestones are complete.

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Server State | TanStack Query |
| UI | shadcn/ui + Tailwind CSS |
| Auth | NextAuth.js (JWT + Google OAuth) |
| Validation | Zod |
| API Types | openapi-typescript (auto-generated from FastAPI OpenAPI spec) |

Backend development uses Claude Code MCP.

## Out of Scope

- Real payment integration (Stripe, etc.) — mock payment sufficient
- Mobile app — API-first, web/API only
- Social features beyond reviews (commenting, following users) — not a social platform
- Multiple storefronts or multi-tenant — single bookstore
- Recommendation engine — needs transaction data first
- Real-time notifications (WebSocket) — email sufficient for restock alerts
- Celery / Redis task queue — BackgroundTasks sufficient at current volume
- Helpfulness voting on reviews — defer until review volume justifies it
- Pre-moderation queue — reactive admin-delete is correct; pre-moderation suppresses authentic reviews
- Rating sort in search results — deferred, keep v2.0 focused on core review CRUD

## Context

Shipped v2.1 with 13,743 LOC Python, ~306 tests passing.
Tech stack: FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, Poetry, fastapi-mail.
18 phases delivered across 4 milestones (v1.0: 8 phases, v1.1: 4 phases, v2.0: 3 phases, v2.1: 3 phases).
Admin analytics: sales summary with period comparison, top-sellers by revenue/volume, low-stock inventory alerts, review moderation with bulk delete.
66 new integration tests for admin analytics and moderation endpoints.

## Constraints

- **Backend Stack**: Python 3.11+, FastAPI, Poetry, PostgreSQL, SQLAlchemy + Alembic
- **Frontend Stack**: Next.js 15, TypeScript, TanStack Query, shadcn/ui, Tailwind CSS
- **Auth**: JWT tokens (access + refresh), DB is_active check per request; NextAuth.js on frontend
- **Payments**: Mock/simulated only — no real payment gateway
- **Email**: fastapi-mail with SMTP, BackgroundTasks dispatch
- **Dev Tooling**: Claude Code MCP for backend development

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
| Next.js over Vite SPA | SSR for SEO on public catalog pages, App Router for layouts, built-in middleware for auth | Planned |
| openapi-typescript for API types | Auto-generate TypeScript types from FastAPI OpenAPI spec, keeps Pydantic ↔ TS in sync | Planned |
| Router-level admin guard for analytics | `dependencies=[Depends(require_admin)]` at APIRouter constructor protects all endpoints automatically | ✓ Good |
| Live SQL aggregates for analytics | Direct queries on orders/order_items/books tables; no materialized views or denormalization needed at current volume | ✓ Good |
| No service layer for simple aggregates | Top-books, low-stock, review-list go directly to repository — service layer only for period/delta logic | ✓ Good |
| Bulk soft-delete via single UPDATE...WHERE IN | O(1) DB round-trips, returns rowcount for best-effort semantics | ✓ Good |
| AOV = 0.0 when no orders, delta = null when prior = 0 | Consistent zero-state semantics, avoids division by zero | ✓ Good |
| Claude Code MCP for backend dev | AI-assisted development for backend phases | Active |

---
*Last updated: 2026-02-27 after v2.1 milestone*
