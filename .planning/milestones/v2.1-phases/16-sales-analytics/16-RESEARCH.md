# Phase 16: Sales Analytics - Research

**Researched:** 2026-02-27
**Domain:** FastAPI analytics endpoints — SQLAlchemy aggregate queries, period-over-period comparison, admin-protected read-only endpoints
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Period Definitions**
- All periods are UTC-based (no timezone configuration)
- "today" = UTC midnight (00:00) of current day to now
- "week" = ISO week, Monday 00:00 UTC to now; previous week = full Mon-Sun
- "month" = calendar month, 1st of month 00:00 UTC to now; previous month = full prior calendar month
- Period comparison (delta %) compares current partial period against full previous period

**Revenue Calculation**
- Revenue = unit_price × quantity from order_items (price at time of order, not current catalog price)
- No discounts or tax exist in the system — revenue is straightforward sum
- AOV = total revenue / order count (simple division, no exclusions)
- Revenue figures returned as decimals with 2 decimal places (e.g., 149.99), using Decimal type to avoid float issues

**Edge Cases & Zero-data**
- Zero orders in a period → return zeroed response: {revenue: 0.00, order_count: 0, aov: 0.00, delta_percentage: null}
- Previous period has zero revenue, current has revenue → delta_percentage: null (can't calculate % change from zero)
- Top-books: default limit 10, accept ?limit=N up to max 50
- Top-books: all-time rankings only (no period filter) — matches requirements scope

### Claude's Discretion

- Query optimization strategy (raw SQL vs ORM aggregation)
- Response schema field naming conventions
- Error handling for invalid period values
- Test data setup approach

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SALES-01 | Admin can view revenue summary (total revenue, order count, AOV) for today, this week, or this month | `AnalyticsRepository.revenue_summary(period_start, period_end)` using `func.sum(OrderItem.unit_price * OrderItem.quantity)`, `func.count(Order.id.distinct())`, and `func.coalesce(..., 0)` — all patterns verified in existing stack |
| SALES-02 | Admin can view period-over-period comparison (delta % vs previous period) alongside revenue summary | `AdminAnalyticsService` calls repo twice (current + prior bounds), computes `(current - prior) / prior * 100`; prior_revenue = 0 → delta_percentage = null — Python arithmetic pattern, no additional libraries needed |
| SALES-03 | Admin can view top-selling books ranked by revenue with book title, author, units sold, and total revenue | `func.sum(OrderItem.unit_price * OrderItem.quantity).label("total_revenue")` grouped by `book_id`, `LEFT JOIN books` for title/author, `WHERE book_id IS NOT NULL`, ordered by `total_revenue DESC LIMIT N` |
| SALES-04 | Admin can view top-selling books ranked by volume (units sold) with book title and author | `func.sum(OrderItem.quantity).label("units_sold")` grouped by `book_id`, same LEFT JOIN and NULL guard, ordered by `units_sold DESC LIMIT N` — distinct query from SALES-03 to produce different rankings |
</phase_requirements>

## Summary

Phase 16 is a pure read-only analytics phase built entirely on the existing FastAPI + SQLAlchemy 2.0 (asyncio) + PostgreSQL stack. No new packages, no schema migrations, and no new infrastructure are required. The phase creates four net-new files in `app/admin/` (`analytics_repository.py`, `analytics_service.py`, `analytics_router.py`, `analytics_schemas.py`) and one modification to `app/main.py` (one `include_router` line). All data comes from the existing `orders` and `order_items` tables.

The two endpoints cover four requirements: `GET /admin/analytics/sales/summary?period=today|week|month` (SALES-01 + SALES-02) returns revenue, order count, AOV, and delta % vs the prior period; `GET /admin/analytics/sales/top-books?sort_by=revenue|volume&limit=N` (SALES-03 + SALES-04) returns all-time top-selling books in distinct orderings. All queries filter `Order.status == OrderStatus.CONFIRMED` — PAYMENT_FAILED orders are silently excluded. Period-comparison orchestration lives in the service layer; the repository receives only concrete `datetime` objects. The admin auth dependency (`AdminUser`) is set at the `APIRouter` constructor level to protect all endpoints without any per-endpoint declaration.

The primary risk for this phase is silent data-quality errors, not crashes: including PAYMENT_FAILED orders in sums, using INNER JOIN to books (dropping deleted-book revenue), using naive datetimes for period bounds, and week/month boundary miscalculation. All have clear prevention patterns documented below. A secondary risk is Decimal serialization — SQLAlchemy returns `Decimal` objects from aggregate columns; Pydantic v2 serializes them as strings by default unless fields are declared as `float` or annotated with `PlainSerializer(float)`.

**Primary recommendation:** Use `func.coalesce(func.sum(...), Decimal("0"))` for revenue in the repository, compute period bounds with `datetime.now(timezone.utc)` in the service, and declare all money response fields as `float` in Pydantic schemas to avoid JSON serialization issues.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.133.0 | HTTP layer, routing, dependency injection | Existing project framework; locked |
| SQLAlchemy | 2.0.47 (asyncio) | `func.sum()`, `func.count()`, `func.coalesce()`, aggregate queries with GROUP BY | Already installed; all analytics constructs are stable since 2.0.0; verified against official docs |
| asyncpg | 0.31.0 | Async PostgreSQL driver; passes `TIMESTAMPTZ` columns requiring timezone-aware datetimes | Existing driver; locked |
| Pydantic | 2.12.5 | Response schema validation and JSON serialization; `float` fields for money values | Existing; locked |
| PostgreSQL | (docker-compose) | Native `SUM`, `COUNT`, `GROUP BY`, `ORDER BY` — no extensions needed | Existing DB; locked |
| Python stdlib | `datetime`, `decimal`, `timezone` | UTC period bounds, Decimal arithmetic | No install needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `cachetools` | `^7.0` (7.0.1) | Optional TTL in-memory cache for analytics endpoints | Only if admin dashboard response times exceed 200ms under real usage; skip for initial implementation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure SQLAlchemy aggregate queries | Pandas/Polars | Pandas pulls full result sets into Python memory before aggregating — defeats set-based SQL aggregation; 10–100MB dependency; no benefit when PostgreSQL handles the computation natively |
| Manual TTL dict + `time.monotonic()` | `asyncache` bridge | `asyncache` last released 2022; only supports Python 3.8–3.10; incompatible with this project's Python 3.13 target |
| `cachetools` (optional) | Redis + fastapi-cache2 | Redis is out of scope per PROJECT.md; admin endpoints are low-frequency; Python-level TTL sufficient |

**Installation:**
```bash
# No new required packages. Optional caching only:
poetry add "cachetools^7.0"
```

## Architecture Patterns

### Recommended Project Structure

```
app/
├── admin/
│   ├── router.py                   # EXISTING: /admin/users/* — untouched
│   ├── schemas.py                  # EXISTING: AdminUserResponse — untouched
│   ├── service.py                  # EXISTING: AdminUserService — untouched
│   ├── analytics_repository.py     # NEW: revenue_summary(), top_books_by_revenue(), top_books_by_volume()
│   ├── analytics_service.py        # NEW: revenue_with_comparison() — period bounds + delta %
│   ├── analytics_router.py         # NEW: GET /admin/analytics/sales/summary, GET /admin/analytics/sales/top-books
│   └── analytics_schemas.py        # NEW: SalesSummaryResponse, TopBookEntry, TopBooksResponse
└── main.py                         # MODIFIED: add include_router(analytics_router)
```

No new migrations. No changes to `app/orders/`, `app/books/`, or any existing module.

### Pattern 1: AnalyticsRepository — Aggregate SQL with Concrete datetime Parameters

**What:** `AnalyticsRepository` in `app/admin/analytics_repository.py` owns all analytics SQL. It receives concrete `datetime` objects (never string period names like `"week"`). Revenue is aggregated in PostgreSQL using `func.sum()` and `func.count()`. `func.coalesce(..., Decimal("0"))` handles periods with zero orders.

**When to use:** Any read-only aggregate query across `orders`/`order_items`. Repository receives only concrete parameters; business-meaning of "today" or "week" is resolved in the service layer.

**Example — revenue_summary method:**
```python
# Source: ARCHITECTURE.md / direct codebase inspection
# app/admin/analytics_repository.py
from datetime import datetime
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

        Filters to CONFIRMED orders only. Revenue = SUM(quantity * unit_price).
        Returns zeroed dict when no confirmed orders exist in range.
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
                Order.status == OrderStatus.CONFIRMED,  # MUST include
                Order.created_at >= period_start,
                Order.created_at < period_end,
            )
        )
        row = result.one()
        return {"revenue": row.revenue, "order_count": row.order_count}
```

### Pattern 2: Service Layer Owns Period Bounds and Delta Calculation

**What:** `AdminAnalyticsService` in `app/admin/analytics_service.py` computes UTC period bounds and calls the repository twice (current period + prior period). It owns the `delta_percentage` calculation with the guard for prior_revenue = 0.

**When to use:** Any derived metric requiring multi-query orchestration or period-comparison arithmetic. Period bound definitions are locked decisions from CONTEXT.md — implement exactly as specified.

**Example — period bounds and comparison:**
```python
# Source: ARCHITECTURE.md + CONTEXT.md locked decisions
# app/admin/analytics_service.py
from datetime import datetime, timezone, timedelta
from decimal import Decimal


def _period_bounds(now: datetime, period: str) -> tuple[datetime, datetime]:
    """Return (start, end) for the current partial period — all UTC."""
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        # ISO week: Monday 00:00 UTC to now
        days_since_monday = now.weekday()  # Monday=0
        start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Unknown period: {period}")
    return start, now


def _prior_period_bounds(now: datetime, period: str) -> tuple[datetime, datetime]:
    """Return (start, end) for the full prior period — all UTC."""
    if period == "today":
        # Full previous calendar day
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        prior_start = today_start - timedelta(days=1)
        return prior_start, today_start
    elif period == "week":
        # Full previous Mon-Sun ISO week
        days_since_monday = now.weekday()
        this_week_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        prior_week_start = this_week_start - timedelta(weeks=1)
        return prior_week_start, this_week_start
    elif period == "month":
        # Full prior calendar month
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prior_month_end = this_month_start
        prior_month_start = (this_month_start - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return prior_month_start, prior_month_end
    else:
        raise ValueError(f"Unknown period: {period}")


class AdminAnalyticsService:
    def __init__(self, repo: "AnalyticsRepository") -> None:
        self.repo = repo

    async def sales_summary(self, period: str) -> dict:
        now = datetime.now(timezone.utc)
        current_start, current_end = _period_bounds(now, period)
        prior_start, prior_end = _prior_period_bounds(now, period)

        current = await self.repo.revenue_summary(
            period_start=current_start, period_end=current_end
        )
        prior = await self.repo.revenue_summary(
            period_start=prior_start, period_end=prior_end
        )

        current_rev = current["revenue"] or Decimal("0")
        prior_rev = prior["revenue"] or Decimal("0")

        # AOV: null when no orders (locked decision: return null, not 0)
        order_count = current["order_count"]
        aov = float(round(current_rev / order_count, 2)) if order_count > 0 else None

        # Delta: null when prior revenue is 0 (locked decision)
        if prior_rev > 0:
            delta_pct = float(round((current_rev - prior_rev) / prior_rev * 100, 2))
        else:
            delta_pct = None

        return {
            "period": period,
            "revenue": float(round(current_rev, 2)),
            "order_count": order_count,
            "aov": aov,
            "delta_percentage": delta_pct,
        }
```

### Pattern 3: Top-Books — Two Distinct Queries with NULL book_id Guard

**What:** SALES-03 (revenue ranking) and SALES-04 (volume ranking) must be separate SQLAlchemy queries — or clearly parameterized by `sort_by` — because they produce distinct rankings. Both require `WHERE order_items.book_id IS NOT NULL` to exclude orphaned items from deleted books. Both use `LEFT JOIN books` for title/author.

**When to use:** All-time top-book queries. Parametrized by `sort_by: Literal["revenue", "volume"]` and `limit: int`.

**Example — top_books repository method:**
```python
# Source: PITFALLS.md + ARCHITECTURE.md + direct model inspection
# app/admin/analytics_repository.py (continued)
from sqlalchemy import desc, func, select

from app.books.models import Book


async def top_books(
    self,
    *,
    sort_by: str,  # "revenue" | "volume"
    limit: int = 10,
) -> list[dict]:
    """All-time top-selling books by revenue or volume.

    Excludes deleted-book items (book_id IS NOT NULL).
    Uses LEFT JOIN books for title/author — NULL book rows already excluded by WHERE.
    """
    revenue_col = func.sum(OrderItem.unit_price * OrderItem.quantity).label("total_revenue")
    volume_col = func.sum(OrderItem.quantity).label("units_sold")

    order_col = revenue_col if sort_by == "revenue" else volume_col

    stmt = (
        select(
            OrderItem.book_id,
            Book.title,
            Book.author,
            revenue_col,
            volume_col,
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Book, OrderItem.book_id == Book.id)  # INNER JOIN — NULL already filtered below
        .where(
            Order.status == OrderStatus.CONFIRMED,
            OrderItem.book_id.is_not(None),  # REQUIRED: exclude deleted-book items
        )
        .group_by(OrderItem.book_id, Book.title, Book.author)
        .order_by(desc(order_col))
        .limit(limit)
    )
    result = await self.session.execute(stmt)
    return [row._asdict() for row in result.all()]
```

### Pattern 4: Analytics Router — AdminUser Dependency at Constructor Level

**What:** The analytics router sets `dependencies=[Depends(require_admin)]` at `APIRouter` construction, not per-endpoint. This mirrors the existing `app/admin/router.py` pattern where `_admin: AdminUser` is declared per endpoint but the router itself carries the prefix. Setting it at router level is the safest approach — no individual endpoint can accidentally lack the protection.

**Example — router setup:**
```python
# Source: app/admin/router.py (existing pattern) + ARCHITECTURE.md
# app/admin/analytics_router.py
from fastapi import APIRouter, Depends, Query
from app.core.deps import AdminUser, DbSession, require_admin
from app.admin.analytics_repository import AnalyticsRepository
from app.admin.analytics_service import AdminAnalyticsService
from app.admin.analytics_schemas import SalesSummaryResponse, TopBooksResponse

router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin-analytics"],
    dependencies=[Depends(require_admin)],
)


@router.get("/sales/summary", response_model=SalesSummaryResponse)
async def sales_summary(
    db: DbSession,
    _admin: AdminUser,
    period: str = Query("today", pattern="^(today|week|month)$"),
) -> SalesSummaryResponse:
    repo = AnalyticsRepository(db)
    svc = AdminAnalyticsService(repo)
    data = await svc.sales_summary(period)
    return SalesSummaryResponse(**data)


@router.get("/sales/top-books", response_model=TopBooksResponse)
async def top_books(
    db: DbSession,
    _admin: AdminUser,
    sort_by: str = Query("revenue", pattern="^(revenue|volume)$"),
    limit: int = Query(10, ge=1, le=50),
) -> TopBooksResponse:
    repo = AnalyticsRepository(db)
    books = await repo.top_books(sort_by=sort_by, limit=limit)
    return TopBooksResponse(sort_by=sort_by, items=books)
```

### Pattern 5: Pydantic Response Schemas with float Money Fields

**What:** SQLAlchemy aggregate queries return `Decimal` objects. Pydantic v2 serializes `Decimal` as a string (e.g., `"149.99"`) in JSON mode by default. Declare money fields as `float` in response schemas to get numeric JSON output. The `round(float(val), 2)` conversion happens in the service layer before the schema.

**Example — analytics schemas:**
```python
# Source: STACK.md (Pydantic Decimal serialization note)
# app/admin/analytics_schemas.py
from pydantic import BaseModel


class SalesSummaryResponse(BaseModel):
    period: str
    revenue: float          # not Decimal — float serializes as JSON number
    order_count: int
    aov: float | None       # null when no orders in period
    delta_percentage: float | None  # null when prior period revenue = 0


class TopBookEntry(BaseModel):
    book_id: int
    title: str
    author: str
    total_revenue: float
    units_sold: int


class TopBooksResponse(BaseModel):
    sort_by: str
    items: list[TopBookEntry]
```

### Anti-Patterns to Avoid

- **Computing period bounds in the repository:** The repository should receive concrete `datetime` objects only. String period names like `"week"` belong in the service layer, which owns the business-meaning of those strings. Mixing business logic into the repository makes unit testing of period comparison logic require DB fixtures.
- **Using INNER JOIN to books for revenue totals:** `order_items.book_id` is nullable (`int | None`, `ondelete="SET NULL"` — confirmed in `app/orders/models.py`). INNER JOIN silently drops revenue from sales of deleted books. Use INNER JOIN only when querying top-books (where you need title/author and have already filtered `book_id IS NOT NULL`).
- **Extending `OrderRepository` with analytics methods:** `OrderRepository` owns user-facing order lifecycle. Analytics is admin-only and cross-domain. Keep analytics SQL in `AnalyticsRepository` in `app/admin/`.
- **Loading ORM objects for revenue calculation:** `sum(item.unit_price * item.quantity for order in orders for item in order.items)` loads potentially thousands of ORM objects into Python memory. Use `func.sum()` and let PostgreSQL aggregate.
- **Returning `Decimal` objects in response dicts:** Leads to `Object of type Decimal is not JSON serializable` at runtime. Always `float(round(val, 2))` before putting into response.
- **`datetime.now()` without timezone:** Returns naive datetime; asyncpg requires timezone-aware datetimes for `TIMESTAMPTZ` columns; period filtering silently breaks in UTC-offset environments.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Revenue aggregation | Python loop over order items | `func.sum(OrderItem.unit_price * OrderItem.quantity)` | PostgreSQL aggregates in one query; Python loop requires loading all rows into memory |
| Period bounds | Custom date math with `datetime.today()` | `datetime.now(timezone.utc)` + `timedelta` / `.replace()` | Naive datetime causes asyncpg TIMESTAMPTZ mismatch; `timezone.utc` is the only correct approach |
| Zero-revenue periods | Python `None` check after query | `func.coalesce(func.sum(...), Decimal("0"))` | SQL COALESCE handles NULL from SUM on empty set; no Python None guard needed in the repository |
| Delta percentage | Custom division with inline zero-guard | Service-layer guard: `if prior_rev > 0` → compute, else `None` | Locked decision: prior=0 → null, not 0% or error |
| Admin auth protection | Per-endpoint `AdminUser` dependency | Router-level `dependencies=[Depends(require_admin)]` | Eliminates the risk of forgetting auth on any single endpoint |
| Revenue vs volume ordering | Single query parametrized on `ORDER BY` string | Explicit `revenue_col` vs `volume_col` label in SQLAlchemy | Prevents accidental reuse of wrong aggregate as sort key; labels are explicit in Python |

**Key insight:** PostgreSQL set-based aggregation is faster, more correct, and simpler than any Python-level alternative for analytics queries. The entire phase is about expressing SQL correctly, not building new computation infrastructure.

## Common Pitfalls

### Pitfall 1: PAYMENT_FAILED Orders Included in Revenue

**What goes wrong:** Revenue queries join `order_items` to `orders` without filtering `orders.status = 'confirmed'`, including failed payments in all revenue metrics.

**Why it happens:** New analytics queries are written from scratch without referencing the existing `has_user_purchased_book()` pattern in `OrderRepository` which correctly uses `OrderStatus.CONFIRMED`.

**How to avoid:** Every query that touches `orders` + `order_items` MUST include `.where(Order.status == OrderStatus.CONFIRMED)`. Import `OrderStatus` from `app.orders.models` — never hardcode the string `"confirmed"`.

**Warning signs:** Revenue total is higher than the sum of completed checkout orders; summary includes order amounts where payment processing failed.

### Pitfall 2: NULL book_id Silently Drops Revenue or Creates Ghost Groups

**What goes wrong:** `order_items.book_id` is nullable (`int | None`, `ondelete="SET NULL"` confirmed in `app/orders/models.py`). An `INNER JOIN books ON order_items.book_id = books.id` drops all items where the book was deleted — understating revenue. A `GROUP BY book_id` without `WHERE book_id IS NOT NULL` creates a `NULL` group aggregating all deleted-book items into one phantom entry.

**Why it happens:** `OrderItem.book_id` is defined as `Mapped[int | None]` — easy to overlook when writing a join. The top-sellers query naturally wants book title/author, which requires joining books.

**How to avoid:** For revenue-only queries (summary): the `JOIN orderitems` to `Order` doesn't touch books at all — no NULL risk. For top-books queries: add `WHERE order_items.book_id IS NOT NULL` before grouping; then INNER JOIN books is safe (all remaining rows have a non-null book_id).

**Warning signs:** Top-books list has fewer entries than expected; top-books response contains an entry with `book_id: null` or `title: null`; revenue summary differs from the sum of individual confirmed order totals.

### Pitfall 3: Naive datetime for Period Bounds

**What goes wrong:** `datetime.now()` returns a naive datetime (no timezone). asyncpg requires timezone-aware datetimes for `TIMESTAMPTZ` columns (`Order.created_at` is `DateTime(timezone=True)` — confirmed in `app/orders/models.py`). This causes `TypeError` or silently returns wrong data when the server timezone differs from UTC.

**Why it happens:** `datetime.now()` is the first thing developers reach for; naive datetimes work in local dev environments where the DB session timezone matches local time.

**How to avoid:** Always `datetime.now(timezone.utc)`. All period bounds in `_period_bounds()` and `_prior_period_bounds()` must use this. Never use `datetime.today()`, `datetime.utcnow()` (deprecated in Python 3.12+), or `datetime.now()` without `timezone.utc`.

**Warning signs:** "Today's revenue" returns 0 after 8pm EST in any non-UTC environment; period filter tests pass locally but fail in CI.

### Pitfall 4: AOV Division by Zero When No Orders

**What goes wrong:** `total_revenue / order_count` raises `ZeroDivisionError` when `order_count = 0` (locked edge case: zero orders in a period).

**Why it happens:** Dividing two numbers without guarding for zero denominator.

**How to avoid:** Guard in service: `aov = float(round(revenue / order_count, 2)) if order_count > 0 else None`. Locked decision is to return `null` for `aov` when no orders (not `0.00`).

**Warning signs:** 500 error on requests for a period with no orders; test for empty period returns 500 instead of `{revenue: 0.00, order_count: 0, aov: null, delta_percentage: null}`.

### Pitfall 5: Decimal Serialization Crashes JSON Response

**What goes wrong:** SQLAlchemy aggregate functions (`func.sum()`, `func.coalesce()` with `Decimal`) return `decimal.Decimal` objects. Pydantic v2 serializes `Decimal` as a string in JSON mode by default. The response body has `"revenue": "149.99"` (string) instead of `"revenue": 149.99` (number), or raises `Object of type Decimal is not JSON serializable` when using raw `dict` responses.

**Why it happens:** `func.sum(Numeric)` returns a `Decimal` column type in SQLAlchemy. Developers don't always realize Pydantic v2 changed `Decimal` serialization behavior from v1.

**How to avoid:** Declare all money fields as `float` in Pydantic response schemas (not `Decimal`). Convert in the service layer with `float(round(val, 2))` before passing to schema. This produces correct JSON numbers and matches the locked decision ("revenue figures returned as decimals with 2 decimal places").

**Warning signs:** API response shows `"revenue": "149.99"` (quoted string); frontend can't parse revenue as a number; Pydantic validation errors about type mismatch when constructing response schemas.

### Pitfall 6: Week Boundary Miscalculation

**What goes wrong:** "This week" is defined as ISO week (Monday 00:00 UTC to now). Using `timedelta(days=7)` subtracted from `now` instead of subtracting `now.weekday()` days produces a rolling 7-day window, not the current Mon-Sun week. "Previous week" is the full Mon-Sun prior to the current week's Monday — not "7 days ago to 14 days ago".

**Why it happens:** Rolling 7-day windows are simpler to implement and often confused with "this week".

**How to avoid:** Use `now.weekday()` (Monday=0, Sunday=6) to compute the Monday of the current week. Prior week = subtract one more week from that Monday.

**Warning signs:** "This week" revenue changes dramatically at midnight Monday even when few orders arrived; period comparison shows wildly wrong delta when run on different days of the week.

## Code Examples

Verified patterns from existing codebase and research:

### Revenue Summary Query (SALES-01)
```python
# Source: ARCHITECTURE.md — verified against app/orders/models.py
from decimal import Decimal
from sqlalchemy import func, select
from app.orders.models import Order, OrderItem, OrderStatus

stmt = (
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
row = (await session.execute(stmt)).one()
# row.revenue: Decimal | Decimal("0"); row.order_count: int
```

### Period Bounds (SALES-01, SALES-02)
```python
# Source: CONTEXT.md locked decisions + PITFALLS.md
from datetime import datetime, timezone, timedelta

def _period_bounds(now: datetime, period: str) -> tuple[datetime, datetime]:
    """All UTC. 'now' MUST be timezone.utc-aware."""
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        # Monday 00:00 UTC
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now

def _prior_period_bounds(now: datetime, period: str) -> tuple[datetime, datetime]:
    """Full previous period (Mon-Sun week, full calendar month, etc.)."""
    if period == "today":
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return today_start - timedelta(days=1), today_start
    elif period == "week":
        this_week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return this_week_start - timedelta(weeks=1), this_week_start
    elif period == "month":
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_last_day = this_month_start - timedelta(days=1)
        prev_month_start = prev_month_last_day.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return prev_month_start, this_month_start
```

### Top-Books Query (SALES-03, SALES-04)
```python
# Source: PITFALLS.md Pitfall 5 + STACK.md
from sqlalchemy import desc, func, select
from app.books.models import Book
from app.orders.models import Order, OrderItem, OrderStatus

async def top_books(self, *, sort_by: str, limit: int = 10) -> list[dict]:
    revenue_col = func.sum(OrderItem.unit_price * OrderItem.quantity).label("total_revenue")
    volume_col = func.sum(OrderItem.quantity).label("units_sold")
    order_col = revenue_col if sort_by == "revenue" else volume_col

    stmt = (
        select(
            OrderItem.book_id,
            Book.title,
            Book.author,
            revenue_col,
            volume_col,
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Book, OrderItem.book_id == Book.id)  # INNER JOIN safe: NULL filtered below
        .where(
            Order.status == OrderStatus.CONFIRMED,
            OrderItem.book_id.is_not(None),  # REQUIRED: exclude orphaned items
        )
        .group_by(OrderItem.book_id, Book.title, Book.author)
        .order_by(desc(order_col))
        .limit(limit)
    )
    result = await self.session.execute(stmt)
    return [row._asdict() for row in result.all()]
```

### Invalid Period — 422 Handling
```python
# Source: existing admin router pattern (app/admin/router.py)
# Use Query with regex pattern to return 422 automatically:
period: str = Query("today", pattern="^(today|week|month)$")
# FastAPI + Pydantic validates the pattern and returns 422 for invalid values
# No manual AppError needed
```

### main.py Router Registration
```python
# Source: app/main.py (existing include_router pattern)
from app.admin.analytics_router import router as analytics_router
# In create_app():
application.include_router(analytics_router)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` for UTC timestamps | `datetime.now(timezone.utc)` | Python 3.12 (deprecated `utcnow`) | Must use the new form; `utcnow()` returns naive datetime and is deprecated |
| Pydantic v1: `Decimal` serializes as number | Pydantic v2: `Decimal` serializes as string | Pydantic v2.0 | Money fields must be declared as `float` in schemas or annotated with `PlainSerializer(float)` |
| SQLAlchemy 1.x `session.execute(query)` returning `ResultProxy` | SQLAlchemy 2.0 `session.execute(select(...))` returning `Result` | SQLAlchemy 2.0 | Use `.one()`, `.scalars().all()`, `._asdict()` on rows |

**Deprecated/outdated:**
- `datetime.utcnow()`: Deprecated since Python 3.12; returns naive datetime; replace with `datetime.now(timezone.utc)`
- `asyncache`: Last released 2022; Python 3.10 max; incompatible with Python 3.13; do not use

## Open Questions

1. **Invalid `period` query parameter response format**
   - What we know: FastAPI returns 422 with a `detail` array for regex pattern violations via `Query(pattern=...)`
   - What's unclear: Whether the project expects a custom error body matching the `AppError` format (`{detail, code}`) or the standard 422 FastAPI validation response
   - Recommendation: Use `Query(pattern="^(today|week|month)$")` for automatic 422; this is consistent with how other query parameters in the project are validated (e.g., `per_page: int = Query(20, ge=1, le=100)` in admin users router). If custom error codes are needed, raise `AppError(422, ...)` manually in the endpoint.

2. **AOV Response: null vs 0.00 for empty periods**
   - What we know: Locked decision is `{revenue: 0.00, order_count: 0, aov: 0.00, delta_percentage: null}` for zero orders
   - What's unclear: The locked decision says `aov: 0.00` (not null), while standard UX convention would be `null` for undefined average. The service code example above returns `null` when order_count = 0.
   - Recommendation: Follow the CONTEXT.md locked decision verbatim: return `0.00` for `aov` when `order_count = 0`, not `null`. Update the service to return `0.0` (not `None`) when no orders.

3. **`orders.created_at` Index Coverage**
   - What we know: Revenue summary filters `Order.created_at >= period_start AND < period_end`. PITFALLS.md notes no explicit index on `orders.created_at` in the existing migration.
   - What's unclear: Whether the existing schema has an index on `orders.created_at` or if PostgreSQL will use a sequential scan for period-filtered revenue queries.
   - Recommendation: Check existing Alembic migrations. If no index exists, add `Index("ix_orders_created_at", "created_at")` in a new migration — analytics queries on this column will benefit significantly as the orders table grows. No new migration is needed for Phase 16 unless this index is missing and query performance is a concern.

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection — `app/orders/models.py` (confirmed `OrderStatus.CONFIRMED`, `OrderItem.book_id: int | None`, `ondelete="SET NULL"`, `Order.created_at: DateTime(timezone=True)`), `app/orders/repository.py` (confirmed `OrderStatus.CONFIRMED` filter pattern in `has_user_purchased_book`), `app/admin/router.py` (confirmed `AdminUser` dep pattern, `APIRouter(prefix="/admin/users")`), `app/books/models.py` (confirmed `Book.title`, `Book.author`, `Book.stock_quantity`), `app/core/deps.py` (confirmed `AdminUser`, `DbSession`, `require_admin`), `app/main.py` (confirmed `include_router` pattern), `tests/conftest.py` (confirmed test session rollback pattern, `asyncio_mode = "auto"`)
- `.planning/research/STACK.md` — verified SQLAlchemy constructs, cachetools compatibility, Pydantic v2 Decimal serialization — HIGH confidence
- `.planning/research/ARCHITECTURE.md` — verified component structure, data flow diagrams, code patterns for `AnalyticsRepository` and `AdminAnalyticsService` — HIGH confidence
- `.planning/research/PITFALLS.md` — verified all 8 critical pitfalls against actual model definitions — HIGH confidence
- `.planning/research/SUMMARY.md` — executive summary of v2.1 approach, recommended stack, anti-features — HIGH confidence
- SQLAlchemy 2.0 SQL Functions docs (`func.*`, FILTER clause, `over()`) — HIGH confidence
- SQLAlchemy 2.0 ORM DML Guide (bulk UPDATE/DELETE, `synchronize_session`) — HIGH confidence

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` — `Accumulated Context > Decisions` section: confirmed `func.avg().cast(Numeric)` pattern for PostgreSQL ROUND compatibility applies to revenue aggregates; confirmed `datetime.now(timezone.utc)` convention; confirmed `Decimal fields serialized as float in all response schemas`
- Crunchy Data: Window Functions for Data Analysis with PostgreSQL — date_trunc, GROUP BY patterns for analytics — MEDIUM confidence

### Tertiary (LOW confidence)

- asyncache PyPI — version 0.3.1, Python <=3.10 only — rejected as incompatible (confidence in the rejection is HIGH based on PyPI metadata)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing dependencies; no new installs required; versions confirmed from `pyproject.toml`
- Architecture: HIGH — derived from direct inspection of all relevant source files; module pattern confirmed; no assumptions about file structure
- Pitfalls: HIGH — all critical pitfalls verified against actual model definitions (`OrderItem.book_id: int | None`, `ondelete="SET NULL"`, `OrderStatus.CONFIRMED`, `Order.created_at: DateTime(timezone=True)`)
- Period bounds: HIGH — locked decisions from CONTEXT.md define exactly how each period is computed; implementation follows directly

**Research date:** 2026-02-27
**Valid until:** 2026-03-29 (30 days — stable stack, no fast-moving dependencies)
