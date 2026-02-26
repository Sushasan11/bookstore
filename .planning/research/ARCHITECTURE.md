# Architecture Research

**Domain:** Bookstore API v2.1 — Admin Dashboard & Analytics
**Researched:** 2026-02-27
**Confidence:** HIGH (existing codebase inspected directly; all integration points derived from actual source files, not assumptions)

---

## Context: Integration Problem, Not Greenfield

v2.1 adds analytics and review moderation endpoints to an existing, working v2.0 codebase with 12,010 LOC and 240 passing tests. The architecture pattern is locked: every domain module follows the same five-file structure. All three feature groups (sales analytics, inventory analytics, review moderation) are **read-heavy, admin-only** — they do not change any existing write path, do not add new tables, and do not modify any existing router.

This document answers one question: how do analytics and review moderation endpoints plug into what already exists?

**Established module pattern (all domains follow this):**

```
app/{domain}/
    models.py      # SQLAlchemy mapped classes inheriting Base
    schemas.py     # Pydantic request/response models
    repository.py  # AsyncSession + select() queries
    service.py     # Business rules, raises AppError
    router.py      # APIRouter, DI via Depends(), registered in main.py
```

**Shared infrastructure unchanged for v2.1:**

```python
# app/core/deps.py
DbSession = Annotated[AsyncSession, Depends(get_db)]   # per-request session, commit/rollback
AdminUser = Annotated[dict, Depends(require_admin)]    # JWT role=admin + is_active check

# app/core/exceptions.py
class AppError(Exception):
    def __init__(self, status_code, detail, code, field=None): ...
```

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          HTTP Clients (Admin Only)                   │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────┐
│                        FastAPI Application                           │
│                                                                      │
│  EXISTING ROUTERS (unchanged)     NEW ADMIN ROUTERS (v2.1)           │
│  ┌──────────┐ ┌──────────┐        ┌─────────────────────────────┐    │
│  │ /books   │ │ /orders  │        │ /admin/analytics/sales      │    │
│  │ /reviews │ │ /admin/  │        │ /admin/analytics/inventory  │    │
│  │ /users   │ │  users   │        │ /admin/reviews              │    │
│  └──────────┘ └──────────┘        └──────────────┬──────────────┘    │
│                                                  │                   │
│                          ┌───────────────────────▼──────────────┐    │
│                          │      AdminAnalyticsService (NEW)     │    │
│                          │  - revenue summary / period compare  │    │
│                          │  - top sellers by revenue + volume   │    │
│                          │  - average order value               │    │
│                          │  - low stock query                   │    │
│                          │  - stock turnover rate               │    │
│                          │  - pre-booking demand                │    │
│                          │  - admin review list (sort/filter)   │    │
│                          │  - bulk delete reviews               │    │
│                          └───────────────────────┬──────────────┘    │
│                                                  │                   │
│    ┌─────────────────────────────────────────────▼──────────────┐    │
│    │                    Repository Layer                         │    │
│    │  AnalyticsRepository (NEW)    ReviewRepository (MODIFIED)  │    │
│    │  reads: Order, OrderItem,     add: list_all_admin() +       │    │
│    │  Book, PreBooking             bulk_delete()                 │    │
│    └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────┐
│                  PostgreSQL (no schema changes for v2.1)             │
│                                                                      │
│   orders      order_items    books        pre_bookings   reviews     │
│  (existing)   (existing)    (existing)    (existing)    (existing)   │
│                                                                      │
│  All analytics are read-only aggregate queries across these tables.  │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Status | Responsibility | File |
|-----------|--------|----------------|------|
| AnalyticsRepository | NEW | All aggregate SQL for sales, inventory, pre-booking demand | app/admin/analytics_repository.py |
| AdminAnalyticsService | NEW | Orchestrate multi-query results, apply business thresholds | app/admin/analytics_service.py |
| Analytics router | NEW | GET endpoints under /admin/analytics/; AdminUser dep | app/admin/analytics_router.py |
| Analytics schemas | NEW | Response schemas for each analytics endpoint | app/admin/analytics_schemas.py |
| ReviewRepository | MODIFIED | Add list_all_admin() (sort/filter/paginate) + bulk_delete() | app/reviews/repository.py |
| admin/router.py | MODIFIED | Wire in analytics_router via include_router or direct registration | app/admin/router.py OR main.py |
| main.py | MODIFIED | include_router(analytics_router) | app/main.py |

---

## Recommended Project Structure

Additions and modifications to the existing tree — unchanged files omitted:

```
app/
├── admin/
│   ├── router.py                   # EXISTING: /admin/users/* — unchanged
│   ├── schemas.py                  # EXISTING: AdminUserResponse — unchanged
│   ├── service.py                  # EXISTING: AdminUserService — unchanged
│   ├── analytics_repository.py     # NEW: all analytics SQL queries
│   ├── analytics_service.py        # NEW: orchestration, threshold logic
│   ├── analytics_router.py         # NEW: GET /admin/analytics/* endpoints
│   └── analytics_schemas.py        # NEW: response schemas for analytics
├── reviews/
│   └── repository.py               # MODIFIED: add list_all_admin() + bulk_delete()
└── main.py                         # MODIFIED: include analytics_router
```

### Structure Rationale

**Why `app/admin/` for all analytics files, not a new `app/analytics/` module:**
The analytics routers are admin-only and conceptually part of the admin domain. Keeping them inside `app/admin/` avoids creating a top-level module that has no models, no user-facing surface, and no independent lifecycle. The `_analytics` suffix distinguishes the new files from the existing user-management files without any naming collision.

**Why separate `analytics_repository.py` from existing `service.py`:**
The existing `AdminUserService` in `service.py` handles user lifecycle (deactivate/reactivate). Analytics is a completely separate concern — read-only aggregate queries across multiple domains. Separate files keep each file focused and avoid merging unrelated responsibilities into a growing service class.

**Why modify `ReviewRepository` for admin review listing, not create a separate `AdminReviewRepository`:**
`ReviewRepository` already owns all Review database access. The admin list and bulk-delete are operations on the same `reviews` table. A separate class would duplicate the session injection boilerplate. Adding two methods to the existing repository is the correct extension point — consistent with how `OrderRepository.has_user_purchased_book()` was added in v2.0 without creating a separate class.

---

## Architectural Patterns

### Pattern 1: Analytics as Read-Only Multi-Table Aggregates in a Dedicated Repository

**What:** All analytics queries live in `AnalyticsRepository`. Each query method maps to one analytics endpoint concept (revenue summary, top sellers, low stock, etc.). The repository takes only the AsyncSession and executes raw SQLAlchemy `select()` statements with `func.sum()`, `func.avg()`, `func.count()`, and `GROUP BY`.

**When to use:** Any read-only aggregate that spans multiple existing domain tables. The repository layer is the correct place for SQL — not the service layer, which orchestrates business logic, and not the router, which handles HTTP concerns.

**Trade-offs:** A dedicated analytics repository means one more file, but it avoids polluting existing repositories with admin-only queries that have no overlap with user-facing use cases.

**Example — Revenue Summary:**

```python
# app/admin/analytics_repository.py
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.models import Order, OrderItem, OrderStatus


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def revenue_summary(
        self,
        *,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """Total revenue and order count for a date range.

        Filters to CONFIRMED orders only — PAYMENT_FAILED excluded.
        Revenue = SUM(order_items.quantity * order_items.unit_price).
        """
        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(OrderItem.quantity * OrderItem.unit_price),
                    Decimal("0"),
                ).label("revenue"),
                func.count(Order.id.distinct()).label("order_count"),
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.status == OrderStatus.CONFIRMED,
                Order.created_at >= period_start,
                Order.created_at < period_end,
            )
        )
        row = result.one()
        return {"revenue": row.revenue, "order_count": row.order_count}
```

### Pattern 2: Service Layer Computes Period Comparison, Not Repository

**What:** Period-over-period comparison (e.g. "this week vs last week") is computed in `AdminAnalyticsService`, not the repository. The service calls the repository twice with different date ranges and subtracts/divides to produce the delta.

**When to use:** Any derived metric that requires combining multiple repository results. The repository gives raw aggregates; the service gives business-meaningful comparisons.

**Trade-offs:** Two DB round-trips instead of one. At admin dashboard scale (one admin, infrequent calls), this is acceptable. A single complex SQL CTE would also work but is harder to test.

**Example:**

```python
# app/admin/analytics_service.py
class AdminAnalyticsService:
    def __init__(self, analytics_repo: AnalyticsRepository) -> None:
        self.repo = analytics_repo

    async def revenue_with_comparison(
        self, period: str  # "today" | "week" | "month"
    ) -> dict:
        now = datetime.now(UTC)
        current_start, current_end = _period_bounds(now, period)
        prior_start, prior_end = _prior_period_bounds(now, period)

        current = await self.repo.revenue_summary(
            period_start=current_start, period_end=current_end
        )
        prior = await self.repo.revenue_summary(
            period_start=prior_start, period_end=prior_end
        )

        prior_rev = prior["revenue"] or Decimal("0")
        delta_pct = (
            float((current["revenue"] - prior_rev) / prior_rev * 100)
            if prior_rev > 0
            else None
        )
        return {
            "period": period,
            "revenue": current["revenue"],
            "order_count": current["order_count"],
            "prior_revenue": prior_rev,
            "change_pct": delta_pct,
        }
```

### Pattern 3: Admin Review Listing via Extended ReviewRepository

**What:** The existing `ReviewRepository` gains two new methods: `list_all_admin()` (paginated, sortable by date or rating, filterable by book, user, rating range) and `bulk_delete()` (sets `deleted_at` on a list of review IDs in one UPDATE statement). These are added to the existing class rather than creating a new class.

**When to use:** When new functionality targets the same table as an existing repository and shares the same session management. The existing repository is the correct extension point.

**Trade-offs:** The repository file grows slightly. Acceptable: the new methods are logically related (Review table operations) and the file remains focused on one entity.

**Example — Admin List with Filters:**

```python
# app/reviews/repository.py (MODIFIED — add these methods)
async def list_all_admin(
    self,
    *,
    page: int = 1,
    size: int = 20,
    sort_by: str = "created_at",   # "created_at" | "rating"
    sort_dir: str = "desc",        # "asc" | "desc"
    book_id: int | None = None,
    user_id: int | None = None,
    rating_min: int | None = None,
    rating_max: int | None = None,
) -> tuple[list[Review], int]:
    """Return paginated reviews for admin dashboard.

    Excludes soft-deleted records (deleted_at IS NULL).
    Supports sort by created_at or rating, optional filter by book/user/rating range.
    Eager-loads book and user relationships for response serialization.
    """
    base_stmt = select(Review).where(Review.deleted_at.is_(None))

    if book_id is not None:
        base_stmt = base_stmt.where(Review.book_id == book_id)
    if user_id is not None:
        base_stmt = base_stmt.where(Review.user_id == user_id)
    if rating_min is not None:
        base_stmt = base_stmt.where(Review.rating >= rating_min)
    if rating_max is not None:
        base_stmt = base_stmt.where(Review.rating <= rating_max)

    sort_col = Review.created_at if sort_by == "created_at" else Review.rating
    order_expr = sort_col.desc() if sort_dir == "desc" else sort_col.asc()

    count_result = await self.session.execute(
        select(func.count()).select_from(base_stmt.subquery())
    )
    total = count_result.scalar_one()

    result = await self.session.execute(
        base_stmt
        .options(selectinload(Review.user), selectinload(Review.book))
        .order_by(order_expr, Review.id.desc())
        .limit(size)
        .offset((page - 1) * size)
    )
    return list(result.scalars().all()), total


async def bulk_delete(self, review_ids: list[int]) -> int:
    """Soft-delete multiple reviews by setting deleted_at.

    Returns number of reviews actually updated (may be < len(review_ids)
    if some IDs are already deleted or do not exist).
    """
    if not review_ids:
        return 0
    result = await self.session.execute(
        update(Review)
        .where(Review.id.in_(review_ids), Review.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC))
    )
    await self.session.flush()
    return result.rowcount
```

### Pattern 4: Configurable Low-Stock Threshold via Query Parameter

**What:** The low-stock inventory endpoint accepts a `threshold` query parameter (default 10). The repository receives the threshold directly — it is not a hardcoded constant. This keeps business-policy values out of the data layer.

**When to use:** Any threshold or limit that an admin might reasonably want to tune. Pass via Query parameter with a sensible default.

**Example:**

```python
# app/admin/analytics_router.py
@router.get("/admin/analytics/inventory/low-stock", response_model=LowStockResponse)
async def low_stock_books(
    db: DbSession,
    _admin: AdminUser,
    threshold: int = Query(10, ge=1, le=1000),
) -> LowStockResponse:
    repo = AnalyticsRepository(db)
    books = await repo.low_stock_books(threshold=threshold)
    return LowStockResponse(threshold=threshold, items=books)

# app/admin/analytics_repository.py
async def low_stock_books(self, *, threshold: int = 10) -> list[dict]:
    result = await self.session.execute(
        select(Book.id, Book.title, Book.author, Book.stock_quantity)
        .where(Book.stock_quantity <= threshold)
        .order_by(Book.stock_quantity.asc(), Book.id.asc())
    )
    return [row._asdict() for row in result.all()]
```

---

## Data Flow

### Request Flow (all analytics endpoints follow this pattern)

```
GET /admin/analytics/sales/revenue?period=week
    │  AdminUser dependency: JWT decoded + DB is_active check + role=admin check
    │
    ▼
analytics_router.py
    svc = AdminAnalyticsService(AnalyticsRepository(db))
    │
    ▼
AdminAnalyticsService.revenue_with_comparison(period="week")
    1. compute current period bounds (e.g. Mon 00:00 → Sun 23:59 this week)
    2. compute prior period bounds (e.g. Mon 00:00 → Sun 23:59 last week)
    3. AnalyticsRepository.revenue_summary(period_start=..., period_end=...)  [x2]
       → SELECT SUM(quantity * unit_price), COUNT(DISTINCT order_id)
         FROM orders JOIN order_items
         WHERE status='confirmed' AND created_at BETWEEN ? AND ?
    4. compute delta_pct from (current - prior) / prior
    │
    ▼
return RevenueSummaryResponse (200 OK)
    │
    ▼ (get_db commits session — analytics are read-only, commit is a no-op)
```

### Admin Review Moderation Flow

```
GET /admin/reviews?book_id=42&rating_min=1&rating_max=2&sort_by=date&page=1
    │  AdminUser dependency
    │
    ▼
analytics_router.py  (or admin/router.py — see integration notes)
    review_repo = ReviewRepository(db)
    │
    ▼
ReviewRepository.list_all_admin(book_id=42, rating_min=1, rating_max=2, ...)
    → SELECT reviews + eager-load user + book WHERE deleted_at IS NULL
      AND book_id=42 AND rating BETWEEN 1 AND 2
      ORDER BY created_at DESC LIMIT 20 OFFSET 0
    + SELECT COUNT(*) ... (same filters)
    │
    ▼
return AdminReviewListResponse(items=[...], total=N, page=1, size=20)

DELETE /admin/reviews/bulk
    body: { "review_ids": [5, 12, 99] }
    │  AdminUser dependency
    │
    ▼
ReviewRepository.bulk_delete([5, 12, 99])
    → UPDATE reviews SET deleted_at = now()
      WHERE id IN (5, 12, 99) AND deleted_at IS NULL
    │
    ▼
return BulkDeleteResponse(deleted_count=3) (200 OK)
    │
    ▼ (get_db commits — deleted_at values persisted)
```

### Stock Turnover Rate Flow

```
GET /admin/analytics/inventory/turnover
    │  AdminUser dependency
    │
    ▼
AnalyticsRepository.stock_turnover(days=30)
    → SELECT
        b.id, b.title, b.author,
        SUM(oi.quantity) AS units_sold,
        b.stock_quantity AS current_stock
      FROM books b
      LEFT JOIN order_items oi ON oi.book_id = b.id
      LEFT JOIN orders o ON o.id = oi.order_id
        AND o.status = 'confirmed'
        AND o.created_at >= NOW() - INTERVAL '30 days'
      GROUP BY b.id, b.title, b.author, b.stock_quantity
      ORDER BY units_sold DESC NULLS LAST
    │
    ▼
return StockTurnoverResponse(items=[...], period_days=30)
```

### Pre-Booking Demand Flow

```
GET /admin/analytics/inventory/prebook-demand?limit=20
    │  AdminUser dependency
    │
    ▼
AnalyticsRepository.prebook_demand(limit=20)
    → SELECT
        b.id, b.title, b.author, b.stock_quantity,
        COUNT(pb.id) AS waiting_count
      FROM pre_bookings pb
      JOIN books b ON b.id = pb.book_id
      WHERE pb.status = 'waiting'
      GROUP BY b.id, b.title, b.author, b.stock_quantity
      ORDER BY waiting_count DESC
      LIMIT 20
    │
    ▼
return PreBookDemandResponse(items=[...])
```

---

## Integration Points: New vs Modified

### New (net-new files — no existing files touched)

| What | File | Notes |
|------|------|-------|
| AnalyticsRepository | app/admin/analytics_repository.py | All aggregate SQL; reads Order, OrderItem, Book, PreBooking |
| AdminAnalyticsService | app/admin/analytics_service.py | Period-comparison logic, threshold delegation |
| Analytics router | app/admin/analytics_router.py | GET /admin/analytics/* with AdminUser dep |
| Analytics schemas | app/admin/analytics_schemas.py | RevenueSummaryResponse, TopSellersResponse, LowStockResponse, TurnoverResponse, PreBookDemandResponse, AdminReviewListResponse, BulkDeleteResponse |

### Modified (existing files extended — minimal, targeted changes)

| What | File | Exact Change |
|------|------|-------------|
| ReviewRepository | app/reviews/repository.py | Add `list_all_admin()` (paginated + filtered) and `bulk_delete()` — two new methods, zero existing code changed |
| main.py | app/main.py | `from app.admin.analytics_router import router as analytics_router` + `application.include_router(analytics_router)` |

### What is NOT Modified

| Module | Why untouched |
|--------|---------------|
| app/admin/router.py | Existing user management endpoints unchanged; analytics gets its own router file |
| app/admin/service.py | AdminUserService handles user lifecycle only; analytics has a separate service |
| app/admin/schemas.py | AdminUserResponse and UserListResponse unchanged |
| app/orders/ | All order data is read via AnalyticsRepository directly; OrderRepository not extended |
| app/books/ | Book data read via AnalyticsRepository; BookRepository not extended |
| app/prebooks/ | PreBooking data read via AnalyticsRepository; PreBookRepository not extended |
| app/reviews/service.py | Business rules for user-facing review CRUD unchanged |
| app/reviews/router.py | User-facing review endpoints unchanged |
| All models | No schema changes; v2.1 is query-only analytics |
| alembic/ | No new migrations; v2.1 adds no tables or columns |

---

## Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| analytics_router ↔ AnalyticsRepository | Direct instantiation via `AnalyticsRepository(db)` in router | Same pattern as all other routers; no service layer needed for simple read-through queries |
| analytics_router ↔ AdminAnalyticsService | For period-comparison endpoints only; service calls repo twice | Service layer justified only where multi-query orchestration is needed |
| analytics_router ↔ ReviewRepository | Direct instantiation via `ReviewRepository(db)` for admin review list/delete | ReviewRepository is the correct owner of all Review SQL; no intermediate service needed |
| AnalyticsRepository ↔ orders/order_items | SQLAlchemy JOIN across domain boundary in a single query | Acceptable: analytics is inherently cross-domain; the repository is the correct place for this |
| AnalyticsRepository ↔ books | Read-only; no import of BookRepository or BookService | AnalyticsRepository imports Book, Order, OrderItem, PreBooking models directly |
| AnalyticsRepository ↔ prebooks | Read-only; imports PreBooking model only | No PreBookRepository dependency |
| admin domain ↔ reviews domain | analytics_router imports ReviewRepository from app.reviews.repository | One-way dependency: admin reads reviews data; reviews module has no knowledge of admin |

---

## Build Order for v2.1

Dependencies flow: repository SQL → service orchestration → router wiring → integration tests.

```
Phase 1: Sales Analytics
  app/admin/analytics_schemas.py   — RevenueSummaryResponse, TopSellersResponse, AvgOrderValueResponse
  app/admin/analytics_repository.py — revenue_summary(), top_sellers_by_revenue(),
                                      top_sellers_by_volume(), avg_order_value()
  app/admin/analytics_service.py   — revenue_with_comparison() (period-over-period delta)
  app/admin/analytics_router.py    — GET /admin/analytics/sales/revenue
                                     GET /admin/analytics/sales/top-sellers
                                     GET /admin/analytics/sales/avg-order-value
  app/main.py                      — include analytics_router
  Tests: each endpoint with known fixture data; period comparison delta correctness

Phase 2: Inventory Analytics
  app/admin/analytics_schemas.py   — LowStockResponse, StockTurnoverResponse, PreBookDemandResponse
  app/admin/analytics_repository.py — low_stock_books(), stock_turnover(), prebook_demand()
  app/admin/analytics_router.py    — GET /admin/analytics/inventory/low-stock?threshold=N
                                     GET /admin/analytics/inventory/turnover?days=N
                                     GET /admin/analytics/inventory/prebook-demand?limit=N
  Tests: threshold edge cases (0 stock, at-threshold, above-threshold), turnover with no sales

Phase 3: Review Moderation Dashboard
  app/admin/analytics_schemas.py   — AdminReviewListResponse, AdminReviewItem, BulkDeleteResponse
  app/reviews/repository.py        — Add list_all_admin() + bulk_delete()
  app/admin/analytics_router.py    — GET /admin/reviews (sort/filter/paginate)
                                     DELETE /admin/reviews/bulk (body: {review_ids: [...]})
  Tests: filter combinations, sort direction correctness, bulk delete with mixed valid/invalid IDs
```

**Rationale for this order:**
- Phase 1 first: establishes the analytics infrastructure (repository + service + router + schemas) that Phase 2 extends. Sales analytics are the highest-value and most straightforward — `orders` + `order_items` are well-understood.
- Phase 2 second: extends the same infrastructure. Inventory analytics require `books` and `pre_bookings` in addition to orders — slightly more complex join logic, builds on Phase 1 patterns.
- Phase 3 last: review moderation modifies the existing `ReviewRepository` rather than the analytics repository. Isolated change to a different module. Can be shipped independently if needed.

---

## Architectural Patterns

### Anti-Pattern 1: Extending OrderRepository for Analytics Queries

**What people do:** Add `get_revenue_summary()`, `get_top_sellers()`, etc. to `app/orders/repository.py`.

**Why it is wrong:** `OrderRepository` owns the user-facing order lifecycle (checkout, order history). Analytics queries are admin-only, cross-domain (JOIN books, JOIN order_items), and read-only. Mixing them into OrderRepository couples the user domain to the admin domain, grows an already-responsible class, and forces admin query changes to touch a file the user checkout flow depends on.

**Do this instead:** `AnalyticsRepository` in `app/admin/` owns all analytics SQL. It imports the necessary models (Order, OrderItem, Book, PreBooking) without importing any other repository.

### Anti-Pattern 2: Computing Period Bounds in the Repository

**What people do:** Pass `period="week"` to `AnalyticsRepository.revenue_summary()` and let the repository compute `NOW() - INTERVAL '7 days'`.

**Why it is wrong:** Business-policy decisions (what "week" means, when it starts, how "prior week" is defined) belong in the service layer. The repository's job is to translate date parameters into SQL — not to define what those dates mean. Testing period-comparison logic also requires the service layer; testing it inside the repository complicates fixture setup.

**Do this instead:** `AdminAnalyticsService` computes `period_start` and `period_end` as `datetime` values and passes them to the repository. The repository receives only concrete datetimes.

### Anti-Pattern 3: Separate Router File for Review Moderation vs Admin Users

**What people do:** Create `app/admin/review_moderation_router.py` and register it separately from `app/admin/analytics_router.py` and `app/admin/router.py`.

**Why it is wrong:** Creates three admin router files for what is logically one admin namespace (`/admin/*`). More files with no organizational benefit — review moderation fits naturally alongside other analytics endpoints under a single `analytics_router.py`.

**Do this instead:** All v2.1 admin endpoints live in `app/admin/analytics_router.py`. The existing `app/admin/router.py` (user management) is untouched. Two admin router files total — one for user management, one for analytics + moderation.

### Anti-Pattern 4: Hard-Deleting Reviews in Bulk Delete

**What people do:** `DELETE FROM reviews WHERE id IN (...)` — physical deletion.

**Why it is wrong:** The existing `ReviewRepository.soft_delete()` sets `deleted_at` (soft-delete). Bulk delete must follow the same convention or it creates a two-tier deletion model where individual admin deletes are soft but bulk deletes are hard. Inconsistency in deletion semantics causes subtle bugs (e.g., review count queries that check `deleted_at IS NULL` would behave differently depending on how the review was deleted).

**Do this instead:** `bulk_delete()` uses `UPDATE reviews SET deleted_at = now() WHERE id IN (...)` — the same soft-delete mechanism as individual deletes.

### Anti-Pattern 5: Loading All Order Items Into Python for Revenue Calculation

**What people do:** `orders = await order_repo.list_all()` then `sum(item.unit_price * item.quantity for o in orders for item in o.items)`.

**Why it is wrong:** Loads potentially thousands of ORM objects into memory for arithmetic Python could trivially do in SQL. Revenue calculation is a single `SUM(quantity * unit_price)` aggregate query — let PostgreSQL do it.

**Do this instead:** `AnalyticsRepository.revenue_summary()` uses `func.sum(OrderItem.quantity * OrderItem.unit_price)` — one SQL aggregate, no Python iteration over rows.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Current approach (live aggregate queries per admin request) is more than sufficient. Admin calls are infrequent and non-concurrent. |
| 1k-100k users | Analytics queries may slow as orders table grows. Add `created_at` index on orders if not already present (likely is, given `ORDER BY created_at DESC` usage). Consider a nightly materialized view for top-sellers if query latency becomes noticeable. |
| 100k+ users | Separate analytics read replica. Pre-compute daily aggregates via a scheduled job and store in a summary table. Real-time analytics at this scale requires dedicated tooling (Redshift, BigQuery, ClickHouse). |

**First bottleneck for v2.1:** None at current scale. All queries are indexed FK joins with aggregates on small-to-medium tables. Admin endpoints are called rarely (one admin, occasional dashboard views). Stock turnover query (LEFT JOIN orders per book) is the most complex — still correct at this scale with existing indexes.

---

## Sources

- Direct codebase inspection (HIGH confidence — actual source files read):
  - `app/admin/router.py`, `service.py`, `schemas.py` — existing admin pattern confirmed
  - `app/orders/models.py`, `repository.py` — Order, OrderItem schema and existing query patterns
  - `app/books/models.py`, `repository.py` — Book schema and search patterns
  - `app/prebooks/models.py`, `repository.py` — PreBooking model and status enum
  - `app/reviews/models.py`, `repository.py`, `router.py` — Review model, soft-delete, existing list patterns
  - `app/core/deps.py` — AdminUser, DbSession dependency injection
  - `app/core/exceptions.py` — AppError pattern
  - `app/main.py` — Router registration pattern
- SQLAlchemy 2.0 docs — func.sum, func.avg, func.count, GROUP BY: https://docs.sqlalchemy.org/en/20/core/functions.html — HIGH confidence
- SQLAlchemy 2.0 docs — UPDATE with returning: https://docs.sqlalchemy.org/en/20/tutorial/data_update.html — HIGH confidence
- Previous ARCHITECTURE.md research (v2.0) — cross-domain repository injection pattern confirmed as implemented and working — HIGH confidence

---

*Architecture research for: BookStore API v2.1 — Admin Dashboard & Analytics*
*Researched: 2026-02-27*
