# Stack Research

**Domain:** Admin analytics API — sales dashboards, inventory metrics, review moderation
**Researched:** 2026-02-27
**Confidence:** HIGH (all key claims verified against official SQLAlchemy docs and PyPI)

---

## Context: This Is an Additive Milestone

The BookStore API already ships FastAPI, PostgreSQL, SQLAlchemy 2.0 (async), Alembic,
Pydantic v2, and asyncpg. Those are proven and locked. This document covers only what
v2.1 (Admin Dashboard & Analytics) needs on top of that foundation.

**Decision principle:** Do not introduce new infrastructure (Redis, Celery, InfluxDB,
Pandas) for analytics that PostgreSQL + SQLAlchemy already handle natively. The project
explicitly out-of-scoped Celery/Redis. All required aggregation — sums, date bucketing,
period-over-period comparison, conditional sums — is expressible with SQLAlchemy Core +
PostgreSQL built-in functions.

---

## Existing Stack (Validated — Do Not Re-Research)

| Technology | Locked Version | Role |
|------------|---------------|------|
| FastAPI | 0.133.0 | HTTP layer, routing, dependency injection |
| SQLAlchemy | 2.0.47 (asyncio) | ORM, query building, aggregate functions |
| Alembic | 1.18.4 | DB schema migrations |
| Pydantic | 2.12.5 | Schema validation, request/response models |
| PostgreSQL | (docker-compose) | Persistence, native analytics functions |
| asyncpg | 0.31.0 | Async PostgreSQL driver |
| pytest + pytest-asyncio | 9.0.2 / 1.3.0 | Test framework |
| httpx | 0.28.1 | Async test client |

---

## Recommended Stack

### No New Core Technologies Required

All analytics needs (time-series aggregation, period-over-period comparison, inventory
metrics, bulk moderation operations) are covered by the existing stack. PostgreSQL provides
`date_trunc`, `FILTER` clause on aggregates, window functions (`LAG`, `RANK`), and
conditional sums. SQLAlchemy 2.0 exposes all of these through the `func` namespace without
any additional libraries.

| Existing Technology | Analytics Role |
|---------------------|----------------|
| PostgreSQL 14+ | `date_trunc`, `FILTER` clause, `LAG`/`RANK` window functions, conditional sums — all native |
| SQLAlchemy 2.0 (asyncio) | `func.date_trunc()`, `func.sum()`, `func.count()`, `case()`, `.filter()` on aggregates, `over()` for windows, `delete().where().in_()` for bulk ops |
| asyncpg 0.31 | Passes all SQL constructs to PostgreSQL untouched; analytics queries work identically to sync drivers |
| Pydantic v2 | Response schemas for structured analytics payloads (nested structure, Decimal serialization) |

### Supporting Libraries

One addition is justified, and it is optional:

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `cachetools` | `^7.0` (7.0.1 as of Feb 2026) | TTL in-memory cache for analytics endpoints | Revenue summaries and top-seller lists are expensive aggregation queries but tolerate 1-5 min staleness. A TTL cache avoids re-aggregating on every admin page refresh. No Redis or Celery needed. Pure Python, zero runtime dependencies. Supports Python 3.13. |

**Note on async + cachetools:** `cachetools.TTLCache` is not coroutine-aware by default.
The correct pattern for this project is a manual TTL guard in the service layer using a
module-level `dict` + `time.monotonic()` — this avoids the `asyncache` bridge library
(last released 2022, only declares Python 3.8–3.10 support, incompatible with this
project's Python 3.13 target). See code pattern below.

If admin analytics traffic is low enough that no caching is needed, skip `cachetools`
entirely — the endpoints function correctly without any cache, just slower under load.

---

## SQLAlchemy Functions Used for Analytics

No new installs. All of these are available in the already-installed
`sqlalchemy[asyncio] ^2.0.47`:

| SQLAlchemy Construct | Analytics Use Case |
|----------------------|--------------------|
| `func.date_trunc("day", Order.created_at)` | Bucket orders by day/week/month for time-series |
| `func.sum(OrderItem.unit_price * OrderItem.quantity)` | Revenue aggregation |
| `func.count(Order.id)` | Order volume counts |
| `func.avg(Review.rating)` | Average rating across a filtered set |
| `case((condition, value), else_=0)` | Period-over-period conditional sums in a single query |
| `func.sum(...).filter(Order.created_at >= period_start)` | FILTER clause on aggregates (PostgreSQL 9.4+, confirmed in SQLAlchemy 2.0 via `FunctionFilter`) |
| `func.rank().over(order_by=revenue_col.desc())` | Top-N sellers ranking |
| `delete(Review).where(Review.id.in_(ids))` | Bulk hard-delete by ID list |
| `update(Review).where(Review.id.in_(ids)).values(deleted_at=...)` | Bulk soft-delete (correct for this project's existing soft-delete pattern) |
| `text("...")` | Escape hatch for aggregation that ORM cannot cleanly express |
| `.label("alias")` | Named columns in aggregate result rows, accessible as `row.alias` |

---

## Installation

No new core packages required. The analytics queries build entirely on existing
dependencies. Optionally add the caching library:

```bash
# Optional: add TTL caching for analytics endpoints
poetry add "cachetools^7.0"
```

If cachetools is added, no migration or schema change is needed. It is a pure Python
library used only at the service layer.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Pure SQLAlchemy aggregate queries | Pandas / Polars in-process | Pulls all rows into Python memory before aggregating. PostgreSQL set-based aggregation is orders of magnitude more efficient. Adds 10–100 MB dependency for zero gain when the DB handles it. |
| PostgreSQL native `date_trunc` via `func.date_trunc()` | TimescaleDB / InfluxDB | Overkill. These are for IoT-scale time-series workloads (millions of events/second). A bookstore order table with thousands of rows aggregates instantly in vanilla PostgreSQL. |
| Manual TTL dict + `time.monotonic()` | Redis + fastapi-cache2 | Redis is out of scope per PROJECT.md. Adds infrastructure dependency for endpoints hit by 1–5 admins. Python-level TTL is sufficient. |
| Manual TTL dict | `asyncache` bridge library | `asyncache` last released November 2022, only declares Python 3.8–3.10 support. Incompatible with this project's Python 3.13 requirement. |
| SQLAlchemy `update().where().in_()` for bulk soft-delete | ORM object-by-object soft-delete | Bulk update with WHERE IN emits a single UPDATE statement. Object-by-object requires N SELECT + N UPDATE round trips. For admin bulk review deletion, WHERE IN is the correct approach. |
| Pydantic `BaseModel` schemas for analytics response | Raw `dict` responses | Pydantic enforces response shape, generates OpenAPI docs automatically, handles `Decimal` serialization. Consistent with the rest of the codebase. |
| `func.sum(...).filter(condition)` (FILTER clause) | `SUM(CASE WHEN ... END)` | Both work in PostgreSQL. FILTER clause is cleaner. SQLAlchemy 2.0 supports it via `FunctionFilter.filter()`. Use `case()` as fallback if grouping creates column aliasing issues. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Pandas / Polars** | Pulls entire result sets into Python memory; defeats set-based relational aggregation. Large dependency (10–100 MB) with no benefit when PostgreSQL handles the same computation natively. | SQLAlchemy `func.sum()`, `func.count()`, `func.avg()` with `group_by()` |
| **DuckDB** | Embedded OLAP engine requiring data export from PostgreSQL or a second database. Zero benefit when PostgreSQL already performs the same aggregations natively on the existing data. | PostgreSQL `date_trunc` + GROUP BY via SQLAlchemy |
| **fastapi-cache2 / Redis** | Requires a running Redis server. Explicitly out-of-scope per PROJECT.md. Admins are a low-volume user population. | Manual `dict` + `time.monotonic()` TTL in service layer, or `cachetools` if preferred |
| **asyncache** | Last release 2022; only declares Python 3.8–3.10 support. Incompatible with Python 3.13 as used by this project. | Manual TTL pattern — see code pattern below |
| **SQLModel** | A separate ORM layer on top of SQLAlchemy that this project does not use. Introducing it now would create schema and pattern divergence. | Pure SQLAlchemy 2.0 ORM (already used everywhere) |
| **Celery + periodic tasks** | Explicitly out of scope per PROJECT.md. BackgroundTasks is sufficient at current volume. | On-demand queries with TTL cache |
| **TimescaleDB / InfluxDB** | Purpose-built for high-volume time-series ingestion (sensor data, metrics). A bookstore order table is an OLTP table that aggregates trivially with PostgreSQL's built-in functions. | PostgreSQL `date_trunc` + `GROUP BY` bucket |
| **Separate analytics database / materialized views** | No need at this scale. Admin dashboard is a low-frequency, read-mostly workload. Premature optimization. | On-demand aggregate queries with optional TTL cache |

---

## Stack Patterns by Feature

**Revenue summary (today / week / month with period-over-period comparison):**
- Single query with conditional `func.sum(...).filter(Order.created_at >= period_start)` columns
- Returns two scalars (current period, prior period); compute `change_pct` in Python
- Cache at service layer with 5-minute TTL

**Top-selling books (revenue rank / volume rank):**
- `func.sum(OrderItem.unit_price * OrderItem.quantity).label("revenue")` with `group_by(OrderItem.book_id)` and `order_by(desc("revenue")).limit(N)`
- Explicit JOIN to `books` table for title/author — do not use `selectinload` in analytics queries since aggregation requires explicit GROUP BY

**Average order value over time:**
- `func.date_trunc("month", Order.created_at).label("period")` with `func.avg(total_subquery).label("avg_order_value")`, `group_by("period")`, `order_by("period")`
- Return list of `{ period: datetime, avg_order_value: Decimal }`

**Low-stock books:**
- Simple `select(Book).where(Book.stock_quantity <= threshold).order_by(Book.stock_quantity)` — no aggregation needed. Configurable `threshold` as a Query param.

**Stock turnover (sales velocity per book):**
- `func.sum(OrderItem.quantity).label("units_sold")` grouped by `book_id`, joined to `books` for current stock
- Compute `velocity = units_sold / days_in_period` in Python after fetching rows

**Pre-booking demand (most-waited-for out-of-stock books):**
- `func.count(PreBooking.id).label("waitlist_count")` grouped by `book_id` where `status == PENDING`
- JOIN to `books` for title; order by `waitlist_count DESC`

**Admin review listing with sort / filter:**
- Extend the existing `list_for_book` pattern in `ReviewRepository` with additional `where()` clauses
- Dynamic `order_by()`: switch between `Review.created_at` and `Review.rating` based on query param
- Always apply `Review.deleted_at.is_(None)` (existing soft-delete convention)
- Supports filter by `book_id`, `user_id`, `rating` range (ge/le)

**Bulk review soft-delete:**
- `update(Review).where(Review.id.in_(ids), Review.deleted_at.is_(None)).values(deleted_at=now)` with `synchronize_session=False`
- Use `update()` not `delete()` — reviews use soft-delete to preserve audit trail, consistent with `ReviewRepository.soft_delete()`

---

## Concrete Code Patterns

### Period-over-period revenue in one query

```python
from sqlalchemy import func, select
from datetime import datetime, timedelta, timezone
from app.orders.models import Order, OrderItem, OrderStatus

now = datetime.now(timezone.utc)
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
week_start = today_start - timedelta(days=7)
prev_week_start = week_start - timedelta(days=7)

stmt = (
    select(
        func.sum(OrderItem.unit_price * OrderItem.quantity)
        .filter(Order.created_at >= today_start)
        .label("today_revenue"),
        func.sum(OrderItem.unit_price * OrderItem.quantity)
        .filter(Order.created_at >= week_start, Order.created_at < today_start)
        .label("week_revenue"),
        func.count(Order.id.distinct())
        .filter(Order.created_at >= today_start)
        .label("today_order_count"),
    )
    .join(OrderItem, Order.id == OrderItem.order_id)
    .where(Order.status == OrderStatus.CONFIRMED)
)
row = (await session.execute(stmt)).one()
# row.today_revenue is Decimal | None; coerce None to Decimal("0")
```

### Bulk soft-delete reviews (preserves audit trail)

```python
from sqlalchemy import update
from datetime import datetime, timezone
from app.reviews.models import Review

stmt = (
    update(Review)
    .where(Review.id.in_(review_ids), Review.deleted_at.is_(None))
    .values(deleted_at=datetime.now(timezone.utc))
    .execution_options(synchronize_session=False)
)
await session.execute(stmt)
await session.commit()
```

### Manual TTL cache (no extra library)

```python
import time
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

_analytics_cache: dict[str, tuple[Any, float]] = {}
_ANALYTICS_TTL = 300.0  # 5 minutes

async def get_revenue_summary(session: AsyncSession) -> RevenueSummary:
    key = "revenue_summary"
    if key in _analytics_cache:
        value, expires_at = _analytics_cache[key]
        if time.monotonic() < expires_at:
            return value
    result = await _compute_revenue_summary(session)
    _analytics_cache[key] = (result, time.monotonic() + _ANALYTICS_TTL)
    return result
```

### Dynamic sort / filter for admin review listing

```python
from sqlalchemy import asc, desc, select
from app.reviews.models import Review

def build_admin_review_query(
    book_id: int | None,
    user_id: int | None,
    min_rating: int | None,
    max_rating: int | None,
    sort_by: str,  # "created_at" | "rating"
    sort_dir: str,  # "asc" | "desc"
) -> select:
    stmt = select(Review).where(Review.deleted_at.is_(None))
    if book_id is not None:
        stmt = stmt.where(Review.book_id == book_id)
    if user_id is not None:
        stmt = stmt.where(Review.user_id == user_id)
    if min_rating is not None:
        stmt = stmt.where(Review.rating >= min_rating)
    if max_rating is not None:
        stmt = stmt.where(Review.rating <= max_rating)
    sort_col = Review.created_at if sort_by == "created_at" else Review.rating
    order_fn = desc if sort_dir == "desc" else asc
    return stmt.order_by(order_fn(sort_col), desc(Review.id))  # stable tiebreaker
```

---

## Version Compatibility

| Package | Version in Use | Compatible With | Notes |
|---------|---------------|-----------------|-------|
| `sqlalchemy[asyncio]` | `^2.0.47` | asyncpg `^0.31`, Python 3.13 | All `func.*` constructs used here (date_trunc, sum, count, case, filter, over) are stable since SQLAlchemy 2.0.0 |
| `asyncpg` | `^0.31.0` | SQLAlchemy 2.0+ asyncio dialect | PostgreSQL FILTER clause, date_trunc, window functions all pass through to PostgreSQL natively |
| `cachetools` | `^7.0` (7.0.1) | Python >=3.10, including 3.13 | No SQLAlchemy integration — used only at the service layer via standard Python dict |
| `pydantic` | `^2.12.5` | FastAPI 0.133+, Python 3.13 | `Decimal` fields serialize to `str` by default in Pydantic v2 JSON mode; use `float` or annotate with `Annotated[Decimal, PlainSerializer(float)]` for numeric JSON output |

---

## Sources

- [SQLAlchemy 2.0 SQL Functions](https://docs.sqlalchemy.org/en/20/core/functions.html) — `func.*`, FILTER clause on aggregates, `over()` for window functions — HIGH confidence
- [SQLAlchemy 2.0 ORM DML Guide](https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html) — bulk DELETE/UPDATE patterns, `synchronize_session` strategies — HIGH confidence
- [SQLAlchemy 2.0 Column Elements](https://docs.sqlalchemy.org/en/20/core/sqlelement.html) — `case()`, `label()`, `FunctionFilter` construct — HIGH confidence
- [asyncpg PyPI](https://pypi.org/project/asyncpg/) — version 0.31.0, released Nov 2025; PostgreSQL feature passthrough confirmed — HIGH confidence
- [cachetools PyPI](https://pypi.org/project/cachetools/) — version 7.0.1, released Feb 2026; Python 3.13 compatible; zero dependencies — HIGH confidence (verified directly)
- [asyncache PyPI](https://pypi.org/project/asyncache/) — version 0.3.1, last released Nov 2022; Python <=3.10 only — verified as incompatible with Python 3.13 target
- [Crunchy Data: Window Functions for Data Analysis with PostgreSQL](https://www.crunchydata.com/blog/window-functions-for-data-analysis-with-postgres) — LAG, RANK, date_trunc patterns — MEDIUM confidence
- [Crunchy Data: 4 Ways to Create Date Bins in Postgres](https://www.crunchydata.com/blog/4-ways-to-create-date-bins-in-postgres-interval-date_trunc-extract-and-to_char) — date bucketing approaches — MEDIUM confidence
- [SQLAlchemy 2.0 PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) — confirmed ARRAY, JSONB, Range types; date_trunc available via generic `func` namespace — HIGH confidence

---

*Stack research for: BookStore v2.1 Admin Dashboard & Analytics*
*Researched: 2026-02-27*
