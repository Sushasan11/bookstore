# Pitfalls Research

**Domain:** FastAPI bookstore v2.1 — adding admin analytics (sales, inventory) and review moderation dashboard to an existing system with Orders/OrderItems/Reviews/PreBookings tables, soft-deleted reviews, and established AdminUser auth dependency
**Researched:** 2026-02-27
**Confidence:** HIGH (codebase verified against actual models/repositories, cross-referenced with official SQLAlchemy 2.0 docs, PostgreSQL docs, and community post-mortems)

> This file covers pitfalls specific to adding analytics endpoints and admin review moderation (v2.1 milestone) to a system that already has: `Order`/`OrderItem` with `SET NULL book_id`, `Review` with soft-delete (`deleted_at`), `PreBooking` with `status` enum, `AdminUser` auth dependency, 240 passing tests, and the five-file module pattern. Pitfalls are ordered by severity.

---

## Critical Pitfalls

### Pitfall 1: Revenue Analytics Include Soft-Deleted Reviews and NULL book_id Order Items — Revenue Is Overstated or Understated

**What goes wrong:**
Two separate NULL-poisoning bugs can affect revenue/sales analytics:

**Bug A — NULL book_id in revenue queries.** When a book is deleted, `OrderItem.book_id` is set to `NULL` (the existing `SET NULL` FK pattern). A revenue query that joins `order_items` to `books` with an `INNER JOIN` silently drops all sales of deleted books. A query using `SUM(order_items.unit_price * order_items.quantity)` on a `LEFT JOIN` correctly includes deleted-book revenue — but the join to `books` for "top sellers by book title" will return `NULL` for the title, potentially crashing the response serializer or producing `None` values in the JSON.

**Bug B — PAYMENT_FAILED orders counted.** Revenue queries that sum `order_items.unit_price * order_items.quantity` without filtering `orders.status = 'confirmed'` include failed payment orders. The `orders` table has `status: confirmed | payment_failed` — unfiltered `SUM` will overstate revenue significantly.

**Why it happens:**
Both bugs stem from the same root: analytics queries join across `orders` and `order_items` but don't fully replicate the purchase-gate filters that the review system already handles correctly. The existing `OrderRepository.has_user_purchased_book()` uses `Order.status == OrderStatus.CONFIRMED` — but developers writing new analytics queries start from scratch and forget this filter. The `SET NULL` FK on `order_items.book_id` is obvious in the model (`book_id: Mapped[int | None]`) but is easy to forget in aggregate queries.

Specifically in this codebase:
- `Order.status` is `OrderStatus.CONFIRMED | OrderStatus.PAYMENT_FAILED`
- `OrderItem.book_id` is nullable (`int | None`) with `ondelete="SET NULL"` — deleted books leave `NULL` book_id rows
- Revenue query WITHOUT `orders.status = 'confirmed'` filter includes failed orders

**How to avoid:**
Every revenue/sales query MUST:
1. Filter `Order.status == OrderStatus.CONFIRMED` (import from `app.orders.models`)
2. Use `SUM(OrderItem.unit_price * OrderItem.quantity)` — this column is non-nullable, so NULL book_id rows are still counted correctly for revenue
3. When joining to `books` for title/author, use `LEFT JOIN` (not INNER) — handle NULL book title in response schema with a fallback like `"[Deleted Book]"`

```python
# CORRECT revenue query — always filter by CONFIRMED status
from app.orders.models import Order, OrderItem, OrderStatus

stmt = (
    select(
        func.sum(OrderItem.unit_price * OrderItem.quantity).label("revenue"),
        func.count(Order.id.distinct()).label("order_count"),
    )
    .join(Order, OrderItem.order_id == Order.id)
    .where(
        Order.status == OrderStatus.CONFIRMED,  # MUST include
        Order.created_at >= period_start,
        Order.created_at < period_end,
    )
)
```

**Warning signs:**
- Analytics query joins `order_items` without `WHERE orders.status = 'confirmed'`
- Analytics query uses `INNER JOIN books ON order_items.book_id = books.id` — this drops deleted-book revenue
- `top_sellers` response has fewer entries than expected (deleted books silently excluded)
- Revenue numbers are higher than checkout totals (PAYMENT_FAILED orders included)

**Phase to address:** Sales analytics phase (first analytics phase). The revenue query is the foundation — every downstream metric (top sellers, AOV, period comparison) is derived from it. Wrong filter = wrong foundation for all analytics.

---

### Pitfall 2: Period-over-Period Revenue Comparison Uses Server Timezone, Not UTC — Day Boundary Is Wrong

**What goes wrong:**
Revenue summaries for "today", "this week", "this month" are implemented with `date_trunc('day', orders.created_at)` or Python-side `datetime.now()` comparisons. The `orders.created_at` column is stored as `TIMESTAMPTZ` (UTC internally in PostgreSQL), but `date_trunc` uses the database session's timezone if not specified explicitly. In a local dev environment, the session timezone may match local time; in production, it is almost always UTC. The result: "today's revenue" for a business in New York at 10pm EST reports 0 because it's already "tomorrow" in UTC.

Additionally, Python's `datetime.now()` returns a naive datetime (no timezone) in environments where `TZ` is not set. Comparing a naive Python datetime against a `TIMESTAMPTZ` PostgreSQL column raises `TypeError` or produces incorrect results depending on the asyncpg version.

**Why it happens:**
This codebase stores `created_at` as `DateTime(timezone=True)` consistently across all models (`Order`, `Review`, `PreBooking`, `Book`). The pattern for filtering by date is correct in existing code (the pre-booking system filters by status, not date), so there is no established pattern for date-range filtering to copy from. Developers reach for `datetime.today()` or `datetime.now()` without thinking about timezone context, and the bug only surfaces when the production server runs in UTC while the business expects local-time day boundaries.

**How to avoid:**
Always use timezone-aware datetimes in Python and explicit `AT TIME ZONE` in PostgreSQL queries when local-time boundaries matter. For an API that is timezone-agnostic (API-first, no defined locale), use UTC consistently and document that all period boundaries are UTC:

```python
from datetime import datetime, timezone, timedelta

# CORRECT — timezone-aware, UTC-based
def get_period_bounds(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now
```

Never use `datetime.now()` (naive). Always use `datetime.now(timezone.utc)` or `datetime.utcnow().replace(tzinfo=timezone.utc)`.

**Warning signs:**
- Period bounds computed with `datetime.now()` (no timezone argument)
- `date_trunc('day', orders.created_at)` used without `AT TIME ZONE` clause
- "Today's revenue" returns 0 after 8pm in any North American timezone
- Python `datetime.today()` anywhere in the analytics service

**Phase to address:** Sales analytics phase. Date boundary logic must be correct from the start — a wrong period boundary silently returns wrong data with no error, making it hard to detect.

---

### Pitfall 3: Admin Review Moderation List Includes Soft-Deleted Reviews — Deleted Reviews Reappear in Moderation Dashboard

**What goes wrong:**
The existing `ReviewRepository` methods all filter `Review.deleted_at.is_(None)` to exclude soft-deleted reviews. A new admin review listing endpoint built for v2.1 fetches reviews without this filter — soft-deleted reviews appear in the moderation list. Admins see "already deleted" reviews and attempting to bulk-delete them again raises a 404 (since the service checks `deleted_at.is_(None)` before returning the review) while the list shows the record. This creates a confusing UX where the dashboard shows reviews the admin cannot act on.

More seriously: if the bulk-delete endpoint skips the soft-delete filter and calls `hard DELETE` directly on a list of IDs, it will hard-delete records that were previously soft-deleted — reviews that may have been soft-deleted by the user but are still referenced in analytics (e.g., review count). The audit trail is lost.

**Why it happens:**
Developers add a new admin list endpoint (different from the user-facing `GET /books/{id}/reviews`) and copy the query structure but forget to carry over `Review.deleted_at.is_(None)`. The soft-delete filter is applied across 4 methods in `ReviewRepository` — it's easy to miss on a fifth method written independently. The existing `get_by_id`, `get_by_user_and_book`, `list_for_book`, and `get_aggregates` all filter soft-deleted records; a new `list_all_for_admin` written without the existing repository as the reference will omit it.

**How to avoid:**
The admin review listing query MUST include `Review.deleted_at.is_(None)`. Follow the exact pattern from `list_for_book()`:

```python
async def list_all_for_admin(
    self,
    *,
    book_id: int | None = None,
    user_id: int | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    size: int = 20,
) -> tuple[list[Review], int]:
    base_stmt = select(Review).where(
        Review.deleted_at.is_(None),  # ALWAYS include — matches list_for_book pattern
    )
    # ... add optional filters ...
```

For bulk-delete (admin), implement as batch soft-delete (set `deleted_at = NOW()`) NOT a hard `DELETE`. This is consistent with the existing single-review soft-delete pattern and preserves the audit trail.

**Warning signs:**
- Admin review list query does not include `Review.deleted_at.is_(None)`
- Admin dashboard shows reviews with non-null `deleted_at` timestamps
- Bulk-delete endpoint uses `DELETE FROM reviews WHERE id IN (...)` instead of `UPDATE reviews SET deleted_at = NOW() WHERE id IN (...)`
- No test that creates a soft-deleted review and asserts it does NOT appear in the admin list

**Phase to address:** Review moderation phase. The soft-delete filter must be on the admin list query from day one — if missed, the admin will operate on phantom records.

---

### Pitfall 4: Bulk Delete Uses ORM session.delete() Per Row — N+1 Round-Trips for Large Batches

**What goes wrong:**
The admin bulk-delete endpoint receives a list of review IDs (e.g., 20-50 IDs) and implements deletion by:
```python
for review_id in review_ids:
    review = await review_repo.get_by_id(review_id)  # SELECT per ID
    await review_repo.soft_delete(review)             # UPDATE per ID
```
This is N+1 for both the SELECT phase and the UPDATE phase. A bulk-delete of 50 reviews requires 100 database round-trips (50 SELECTs + 50 UPDATEs). While 50 reviews is small, the test suite will be slow, and real-world admin abuse-moderation scenarios (flagged review spam) may delete hundreds at once.

**Why it happens:**
The existing `soft_delete()` method in `ReviewRepository` operates on a single ORM object — it's the natural pattern to call in a loop. Developers copying the single-delete pattern for bulk operations assume the session batches multiple flushes; it does not.

**How to avoid:**
Use a single `UPDATE` statement for bulk soft-delete using SQLAlchemy 2.0 DML:

```python
from datetime import UTC, datetime
from sqlalchemy import update

async def bulk_soft_delete(self, review_ids: list[int]) -> int:
    """Soft-delete multiple reviews by ID. Returns count of affected rows.

    Uses a single UPDATE statement — not a loop of single deletes.
    synchronize_session="fetch" is required for AsyncSession to keep session state consistent.
    """
    if not review_ids:
        return 0
    stmt = (
        update(Review)
        .where(
            Review.id.in_(review_ids),
            Review.deleted_at.is_(None),  # Only affect non-deleted reviews
        )
        .values(deleted_at=datetime.now(UTC))
        .returning(Review.id)
    )
    result = await self.session.execute(stmt, execution_options={"synchronize_session": "fetch"})
    affected = len(result.scalars().all())
    await self.session.flush()
    return affected
```

The `synchronize_session="fetch"` execution option is required for `AsyncSession` when using bulk UPDATE/DELETE with the ORM — without it, the in-memory session state becomes inconsistent with the database (SQLAlchemy GitHub issue #6024).

**Warning signs:**
- Bulk-delete implemented as a `for review_id in review_ids: session.delete(...)` loop
- Bulk-delete takes measurable time for batches of 20+ reviews (log shows sequential queries)
- `synchronize_session` not specified on `session.execute(update(...))` calls
- No test that bulk-deletes 10+ reviews in one request and verifies all are soft-deleted

**Phase to address:** Review moderation phase. The bulk-delete implementation must use set-based SQL from the start — the ORM loop pattern is not an acceptable foundation to optimize later.

---

### Pitfall 5: Top-Sellers Query Uses SUM(quantity) But Not SUM(unit_price * quantity) — Volume vs. Revenue Confusion

**What goes wrong:**
The requirements specify two top-seller metrics: "top-selling books by revenue" (highest total revenue) and "top-selling books by volume" (most units sold). A single query is written that uses either `SUM(quantity)` or `SUM(unit_price * quantity)` and reused for both — the two metrics return different book rankings. For example, a $0.99 ebook sold 1000 times ranks #1 by volume but may rank #5 by revenue. If the same query powers both endpoints, one metric is always wrong.

Additionally, when books are deleted (`book_id IS NULL`), a `GROUP BY book_id` query will aggregate all deleted books into a single `NULL` group — a "ghost" entry appears in the top-sellers list with `book_id = NULL` and aggregated metrics from all deleted books combined. This `NULL` entry cannot be linked to a title and will cause a response serialization error if the schema expects a non-null `book_id`.

**Why it happens:**
The requirements look similar ("top-selling by revenue" and "top-selling by volume"), so developers write one query and try to parametrize it by the sort column. The `NULL book_id` issue is a consequence of the existing `SET NULL` FK pattern — it's correct for order history preservation but produces spurious `NULL` groups in analytics aggregations.

**How to avoid:**
Write separate labeled queries for revenue and volume metrics, or parametrize clearly with a `metric: Literal["revenue", "volume"]` enum. Always add `WHERE order_items.book_id IS NOT NULL` to top-sellers queries to exclude orphaned items:

```python
# Top sellers by revenue — SUM(unit_price * quantity)
stmt_revenue = (
    select(
        OrderItem.book_id,
        func.sum(OrderItem.unit_price * OrderItem.quantity).label("total_revenue"),
        func.sum(OrderItem.quantity).label("units_sold"),
    )
    .join(Order, OrderItem.order_id == Order.id)
    .where(
        Order.status == OrderStatus.CONFIRMED,
        OrderItem.book_id.is_not(None),  # REQUIRED: exclude deleted-book items
    )
    .group_by(OrderItem.book_id)
    .order_by(func.sum(OrderItem.unit_price * OrderItem.quantity).desc())
    .limit(limit)
)
```

**Warning signs:**
- Top-sellers endpoint uses `ORDER BY SUM(quantity)` for the "by revenue" variant (should be `SUM(unit_price * quantity)`)
- Top-sellers query lacks `WHERE order_items.book_id IS NOT NULL`
- Top-sellers response includes an entry with `book_id: null` or `title: null`
- "By volume" and "by revenue" return identical rankings (only one metric is actually being computed)

**Phase to address:** Sales analytics phase. The two metrics must be distinguished from initial implementation — confusing them produces silently wrong data.

---

### Pitfall 6: Inventory Analytics Uses Current `stock_quantity` for "Turnover Rate" — Snapshot vs. Live Confusion

**What goes wrong:**
Stock turnover rate (sales velocity per book) is calculated as `units_sold / current_stock_quantity`. If `current_stock_quantity` is 0 (out of stock), division by zero occurs either in Python or in SQL (`SUM(quantity) / books.stock_quantity` raises a `ZeroDivisionError` or PostgreSQL `division by zero` error). Even when stock > 0, using "current stock" to compute historical turnover is conceptually wrong: the current stock reflects post-sale inventory, not the initial stock level. The metric is better expressed as units sold per day/week (sales velocity) rather than as a ratio to current stock.

**Why it happens:**
"Turnover rate" has a standard retail definition (Cost of Goods Sold / Average Inventory), but implementing that correctly requires tracking historical inventory levels, which this system does not do. Developers reach for the available `books.stock_quantity` column and compute a ratio, producing a metric that is undefined when stock = 0 and misleading otherwise.

**How to avoid:**
Express stock turnover as "units sold over the period" (raw velocity) rather than a ratio to current stock. This avoids division-by-zero entirely and is meaningful with available data:

```python
# CORRECT: express as units sold (velocity), not ratio to current stock
stmt = (
    select(
        OrderItem.book_id,
        func.sum(OrderItem.quantity).label("units_sold"),
        Book.stock_quantity.label("current_stock"),
        Book.title.label("title"),
    )
    .join(Order, OrderItem.order_id == Order.id)
    .join(Book, OrderItem.book_id == Book.id)  # INNER JOIN OK here — we want live books only
    .where(
        Order.status == OrderStatus.CONFIRMED,
        OrderItem.book_id.is_not(None),
    )
    .group_by(OrderItem.book_id, Book.stock_quantity, Book.title)
    .order_by(func.sum(OrderItem.quantity).desc())
)
```

If a ratio is needed, use `NULLIF(books.stock_quantity, 0)` to avoid division by zero: `func.sum(OrderItem.quantity) / func.nullif(Book.stock_quantity, 0)`.

**Warning signs:**
- Any `SUM(quantity) / stock_quantity` calculation without `NULLIF`
- Analytics endpoint returns 500 for books with `stock_quantity = 0`
- "Turnover rate" field is `None` or `Infinity` for in-stock books
- No test that runs turnover analytics when any book has `stock_quantity = 0`

**Phase to address:** Inventory analytics phase. Division-by-zero in analytics is a hard crash — it must be handled before the endpoint ships.

---

### Pitfall 7: Pre-Booking Demand Query Counts ALL Statuses, Not Just "Waiting" — Demand Is Overstated

**What goes wrong:**
The "pre-booking demand" metric (most-waited-for out-of-stock books) is implemented as `COUNT(pre_bookings) GROUP BY book_id`. This counts ALL pre-bookings including those with `status = 'notified'` or `status = 'cancelled'`. A book that was out of stock 6 months ago with 50 pre-bookings (all now `notified` — restocked and alerted) shows as having high current demand, when the actual current waitlist (`status = 'waiting'`) may be 0. Admins make restocking decisions based on inflated demand numbers.

**Why it happens:**
The `PreBooking` model has three statuses: `WAITING`, `NOTIFIED`, `CANCELLED`. Developers querying "how many people want this book" naturally write `COUNT(*)` without filtering status. The partial unique index (`uq_pre_bookings_user_book_waiting`) that enforces one-active-per-user only covers `status = 'waiting'` — it's a hint that WAITING is the "active" status, but developers writing analytics queries may not read the index definition.

**How to avoid:**
Filter `PreBooking.status == PreBookStatus.WAITING` to count only active demand:

```python
from app.prebooks.models import PreBooking, PreBookStatus

stmt = (
    select(
        PreBooking.book_id,
        func.count(PreBooking.id).label("waiting_count"),
        Book.title.label("title"),
        Book.stock_quantity.label("current_stock"),
    )
    .join(Book, PreBooking.book_id == Book.id)
    .where(PreBooking.status == PreBookStatus.WAITING)  # MUST filter — only active demand
    .group_by(PreBooking.book_id, Book.title, Book.stock_quantity)
    .order_by(func.count(PreBooking.id).desc())
    .limit(limit)
)
```

**Warning signs:**
- Pre-booking demand query lacks `WHERE pre_bookings.status = 'waiting'`
- Demand count is much higher than expected for books that were recently restocked
- No test that creates `NOTIFIED` and `CANCELLED` pre-bookings and asserts they are excluded from demand count
- Import uses `PreBookStatus` but no `.WAITING` filter in the WHERE clause

**Phase to address:** Inventory analytics phase. Wrong status filter produces misleading restocking signals — a silent data quality error that only becomes apparent after comparing with real-world inventory decisions.

---

### Pitfall 8: Admin Review Moderation List Calls N+1 `has_user_purchased_book()` Checks — Verified Purchase Flag Breaks at Scale

**What goes wrong:**
The existing v2.0 review list endpoint (`GET /books/{id}/reviews`) already has an accepted N+1 tech debt: `has_user_purchased_book()` is called once per review to compute the `verified_purchase` flag. For a page of 20 reviews, this is 20 EXISTS subqueries — accepted for user-facing lists with small page sizes.

The v2.1 admin moderation list may default to larger page sizes (e.g., 50-100 reviews per page for admin efficiency), and the `verified_purchase` flag may not be needed at all for admin moderation purposes (admins moderate based on content quality, not purchase status). If the verified_purchase flag is included in the admin list response, and the page size is large, the N+1 behavior becomes a bottleneck.

**Why it happens:**
The admin review list reuses the same `ReviewResponse` schema as the user-facing list, which includes `verified_purchase`. Developers implementing the admin endpoint call the same service method (`list_for_book`) and get the N+1 for free.

**How to avoid:**
The admin review list should use a different, admin-specific response schema that omits `verified_purchase` or uses a separate schema that includes only moderation-relevant fields. If `verified_purchase` is required in the admin view, implement it as a batch query (single EXISTS JOIN) rather than N individual queries:

```python
# Batch verified-purchase check — one query for all user_ids in the page
async def get_verified_purchase_batch(
    self, user_book_pairs: list[tuple[int, int]]
) -> set[tuple[int, int]]:
    """Return set of (user_id, book_id) pairs that represent confirmed purchases."""
    # Build OR conditions or use a VALUES subquery approach
```

For MVP, omitting `verified_purchase` from the admin moderation view is the correct call — admins moderate content, not purchase status.

**Warning signs:**
- Admin review list response schema includes `verified_purchase` field
- `list_all_for_admin()` calls `has_user_purchased_book()` in a loop
- Admin list endpoint responds significantly slower than user-facing list for same page size
- No explicit decision documented about whether admin view needs `verified_purchase`

**Phase to address:** Review moderation phase. Decide upfront whether the admin schema includes `verified_purchase` and, if so, implement a batch query — do not inherit the N+1 from the user-facing list.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Reusing `ReviewResponse` schema for admin moderation list | No new schema to write | N+1 verified_purchase check; admin concerns mixed with user concerns | Never — create an `AdminReviewResponse` schema that omits user-specific fields |
| Hardcoding `"confirmed"` string in revenue queries instead of `OrderStatus.CONFIRMED` | Fewer imports | If `OrderStatus` enum values change (e.g., renamed), revenue queries silently include wrong orders | Never — always import and use the enum |
| Computing period bounds in the router layer (not service) | Simple to add one-off period logic | Period logic tested only via HTTP tests; harder to unit-test; date boundaries duplicated across endpoints | Acceptable only if there is a single analytics endpoint; not acceptable for multiple period-parameterized endpoints |
| Using `PAYMENT_FAILED` orders as a negative signal in analytics | Provides "failed conversion" insight | If included in revenue sums, overstates revenue; confusing to explain to admins | Never include in revenue sums; may include separately as a "failed orders" count if explicitly labeled |
| Returning raw SQL aggregate results as floats without rounding | Simpler code | `average_order_value` returns `3.141592653589793` instead of `3.14`; poor UX | Never for money values — always round to 2 decimal places using Python `round(float(val), 2)` or SQL `ROUND(val::numeric, 2)` |
| No upper bound on `limit` for top-sellers queries | Flexible for admin | Large limit values load entire `order_items` table for aggregation; unindexed aggregation on large tables | Never without `le=100` cap on the query parameter |
| Omitting `WHERE deleted_at IS NULL` from admin review list | Simpler query | Deleted reviews appear in moderation; admins try to act on phantom records | Never — soft-delete filter is mandatory on all review queries |

---

## Integration Gotchas

Common mistakes when connecting analytics to existing components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Revenue from `order_items` | Not filtering `orders.status = 'confirmed'` | Always join `order_items → orders` and `WHERE orders.status = 'confirmed'`; import `OrderStatus.CONFIRMED` from `app.orders.models` |
| Revenue from `order_items` | Using INNER JOIN to `books` — drops deleted-book items | Use `LEFT JOIN books ON order_items.book_id = books.id`; handle `NULL` title in schema with fallback string |
| Top-sellers | Including `NULL book_id` rows in GROUP BY | Always add `WHERE order_items.book_id IS NOT NULL` to top-sellers aggregations |
| Pre-booking demand | Counting all statuses | Filter `WHERE pre_bookings.status = 'waiting'`; import `PreBookStatus.WAITING` from `app.prebooks.models` |
| Admin review list | Missing soft-delete filter | Always include `Review.deleted_at.is_(None)` — same as all 4 existing `ReviewRepository` methods |
| Admin review list | Reusing user-facing `ReviewResponse` schema | Create `AdminReviewResponse` schema; decide explicitly whether `verified_purchase` is included |
| Bulk soft-delete | Loop over `session.delete()` per review | Use `UPDATE reviews SET deleted_at = NOW() WHERE id IN (...)` with `synchronize_session="fetch"` for `AsyncSession` |
| Period bounds | `datetime.now()` without timezone | Always use `datetime.now(timezone.utc)`; never pass naive datetimes to asyncpg TIMESTAMPTZ columns |
| Average order value | `SUM(revenue) / COUNT(orders)` when COUNT is 0 | Use `NULLIF(COUNT(*), 0)` or check in Python before dividing; return `null` not `0` when no orders in period |
| Admin auth on new analytics endpoints | Forgetting `AdminUser` dependency on new analytics router | Create analytics router with `AdminUser` as a router-level dependency — not per-endpoint — so no individual endpoint can be accidentally unprotected |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No index on `orders.created_at` for period-based revenue queries | Revenue summary takes 200ms+ at 10k orders | Add `Index("ix_orders_created_at", "created_at")` — not in existing migration; add in v2.1 migration if analytics queries need it | At ~10k orders (noticeable latency) / ~100k (problematic) |
| Full table scan on `order_items` for top-sellers with no composite index | Top-sellers query reads all order_items rows; slow at 50k+ items | Composite index `(book_id, order_id)` on `order_items` — check if existing `ix_order_items_book_id` covers analytics queries | At ~50k order_items rows |
| Loading all `Order` objects via `list_all()` then filtering in Python | High memory at 10k orders; analytics becomes a memory OOM | Use SQL-level `WHERE`, `GROUP BY`, and `ORDER BY` — never load ORM objects for analytics | At ~1k orders (memory grows linearly) |
| N+1 `has_user_purchased_book()` in admin review list with large page sizes | Admin list request takes 5+ seconds for page of 100 | Omit `verified_purchase` from admin schema OR batch with a single IN-based EXISTS query | At page_size >= 50 reviews |
| Unparameterized `LIMIT` on top-sellers | Admin requests `limit=10000` — aggregates entire order history | Add `le=100` cap to all analytics query parameters | Any time limit > 1000 is allowed |
| Returning `Decimal` objects from SQLAlchemy aggregate columns as-is | `JSONResponse` serialization fails with `Object of type Decimal is not JSON serializable` | Always convert: `float(row.revenue)` or `round(float(row.aov), 2)` before adding to response schema | Every response with a Decimal aggregate column |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Analytics router missing `AdminUser` dependency | Any authenticated user can view revenue, inventory, and user activity data — business intelligence leak | Create `analytics_router = APIRouter(prefix="/admin", dependencies=[Depends(get_admin_user)])` — dependency at router level, not per-endpoint |
| Bulk-delete endpoint missing ID validation — accepts any list of IDs | Admin can accidentally (or intentionally) delete any review including those they shouldn't access | Validate that IDs in the bulk-delete list belong to soft-deletable reviews; return count of actually-affected rows (not input count) so admin knows partial failures |
| Admin review list exposes full user email addresses in response | PII disclosure — email addresses visible to admin via API response | Include `display_name` (derived from email) only, not raw email field; match the existing `ReviewResponse.display_name` pattern from v2.0 |
| Analytics endpoint accepts unbounded date ranges | Request for `start_date=2000-01-01&end_date=2099-01-01` triggers a full table scan aggregation, causing a DB spike | Cap date ranges to max 1 year or add explicit `ge`/`le` Query validators; return 422 for invalid ranges |
| `PAYMENT_FAILED` order data exposed in analytics | Revenue figures include failed orders — misleading and potentially sensitive | Always filter `Order.status == OrderStatus.CONFIRMED`; never expose PAYMENT_FAILED counts without explicit admin context |

---

## UX Pitfalls

Common user experience mistakes in admin analytics API design.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Revenue summary returns `null` for periods with no orders | Admin interprets `null` as missing data, not as zero revenue | Return `0.00` (not `null`) for revenue/count when no orders exist in period; use `COALESCE(SUM(...), 0)` in SQL |
| Period-over-period comparison returns only current period | Admin cannot assess whether performance improved or declined | Always include `current_period` and `previous_period` in revenue summary response; compute change as `(current - previous) / previous * 100` (with division-by-zero guard) |
| Top-sellers list has no `total_results` field | Admin cannot tell how many books have sales data (e.g., top-10 of 150 vs. top-10 of 12) | Include `total_books_with_sales` count in top-sellers response |
| Low-stock threshold is hardcoded in the query | Admin cannot adjust what "low stock" means for their inventory profile | Accept `threshold` as a Query parameter with a sensible default (`default=10, ge=1`) — same pattern as `per_page` on admin user list |
| Admin review list sort by `rating` with no secondary sort | Reviews with the same rating appear in random order across pages | Always add a secondary sort on `id` or `created_at` for deterministic pagination — same pattern as `list_for_book()` secondary sort by `id.desc()` |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Revenue summary:** Returns correct numbers — verify `PAYMENT_FAILED` orders are NOT included; verify period with no orders returns `0.00` not `null`; verify current vs. previous period both appear in response
- [ ] **Top sellers by revenue vs. volume:** Two endpoints return different rankings — verify a $0.99 high-volume book ranks differently by revenue vs. by volume; verify deleted books (NULL book_id) are excluded from both
- [ ] **Average order value:** Returns correctly rounded value — verify `0` orders in period returns `null` (not division-by-zero crash); verify rounding is 2 decimal places
- [ ] **Low-stock query:** Returns books below threshold — verify `threshold` Query param is respected; verify books with `stock_quantity = 0` are included; verify in-stock books are excluded
- [ ] **Pre-booking demand:** Counts only WAITING status — verify `NOTIFIED` and `CANCELLED` pre-bookings are excluded; verify a book with 10 WAITING and 20 NOTIFIED shows `waiting_count = 10`
- [ ] **Stock turnover:** No division-by-zero — verify endpoint returns 200 when any book has `stock_quantity = 0`; verify metric is labeled as "units sold" not "turnover ratio"
- [ ] **Admin review list:** Excludes soft-deleted reviews — verify soft-deleted reviews (non-null `deleted_at`) do NOT appear; verify sort and filter params work in combination
- [ ] **Admin bulk-delete:** Correctly soft-deletes — verify `deleted_at` is set (not hard DELETE); verify re-listing after bulk-delete excludes the deleted reviews; verify return value is count of actually-deleted records
- [ ] **Admin analytics auth:** All endpoints return 403 for non-admin — verify regular user JWT gets 403 on every analytics endpoint; verify unauthenticated request gets 401
- [ ] **Decimal serialization:** All money fields serialize to JSON — verify `revenue`, `average_order_value` serialize as numbers (not as `"Decimal('3.14')"` strings)
- [ ] **Full regression:** 240 existing tests still pass — run full suite before marking any analytics phase complete; no analytics phase should break review or order functionality

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Revenue overstated (PAYMENT_FAILED orders included) | LOW | Add `WHERE orders.status = 'confirmed'` filter; re-verify numbers against order history; no data corruption |
| Revenue understated (INNER JOIN dropped deleted books) | LOW | Change to LEFT JOIN with NULL title fallback; no data corruption, only missing data in API response |
| Pre-booking demand overstated (all statuses counted) | LOW | Add `WHERE pre_bookings.status = 'waiting'`; no data corruption |
| Admin bulk-delete hard-deleted reviews (not soft) | HIGH | Reviews are permanently gone; if backup exists, restore affected rows; add audit log requirement; fix endpoint to use UPDATE; add regression test |
| Division-by-zero on stock turnover (stock = 0) | LOW | Wrap denominator in NULLIF or add Python guard; add test with zero-stock book |
| Soft-deleted reviews visible in admin list | LOW | Add `deleted_at.is_(None)` filter; no data corruption |
| Period bounds use naive datetime (wrong timezone) | MEDIUM | Fix to `datetime.now(timezone.utc)`; existing historical data is not affected; only current reporting window changes |
| Analytics router missing AdminUser dependency | HIGH | Rotate API keys if external clients accessed analytics data; fix dependency immediately; add integration test asserting 403 for regular user on every analytics endpoint |
| Decimal serialization crash on revenue fields | LOW | Wrap aggregate results with `float(round(val, 2))` in repository; add schema validator `@validator` if needed |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| PAYMENT_FAILED orders in revenue | Sales analytics phase | Test: create PAYMENT_FAILED order; run revenue summary; assert amount does not include failed order |
| NULL book_id dropped from revenue (INNER JOIN) | Sales analytics phase | Test: delete a book; run revenue summary; assert revenue still includes sales of deleted book |
| Wrong timezone in period bounds | Sales analytics phase | Test: create order at known UTC timestamp; run "today" summary; assert it appears with UTC-based boundary |
| Volume vs. revenue metric confusion | Sales analytics phase | Test: submit two orders for same book (high qty, low price); assert "by revenue" and "by volume" rankings differ |
| Division-by-zero on stock turnover | Inventory analytics phase | Test: set book stock_quantity = 0; run turnover analytics; assert 200 response (no crash) |
| WAITING-only pre-booking demand | Inventory analytics phase | Test: create NOTIFIED and CANCELLED pre-bookings; run demand query; assert they are excluded from count |
| Soft-delete filter missing from admin review list | Review moderation phase | Test: soft-delete a review; run admin list; assert soft-deleted review does not appear |
| N+1 bulk soft-delete | Review moderation phase | Test: bulk-delete 20 reviews; assert exactly 1-2 DB queries in repository (not 40) |
| Admin auth missing on analytics | Sales analytics phase (router setup) | Test: call every analytics endpoint with a regular user JWT; assert 403 on all of them |
| Decimal serialization crash | Sales analytics phase | Test: GET revenue summary; assert response is valid JSON with numeric (not string) money fields |
| Pre-booking demand NULL book_id | Inventory analytics phase | (N/A — pre_bookings.book_id uses CASCADE not SET NULL; no NULL risk here) |

---

## Sources

- Existing codebase: `app/orders/models.py` (`OrderStatus`, `OrderItem.book_id SET NULL`), `app/orders/repository.py` (`has_user_purchased_book` with `OrderStatus.CONFIRMED` filter, `list_all()` pattern), `app/reviews/repository.py` (soft-delete filter pattern, `list_for_book`, `get_aggregates`), `app/prebooks/models.py` (`PreBookStatus.WAITING`, partial unique index), `app/admin/router.py` (`AdminUser` dependency pattern), `app/core/deps.py`
- SQLAlchemy 2.0 async bulk DML: [Using UPDATE and DELETE Statements — SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/tutorial/data_update.html), [ORM-Enabled INSERT, UPDATE, and DELETE — SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html)
- SQLAlchemy async bulk delete `synchronize_session`: [DELETE... USING with the Async ORM — SQLAlchemy Discussion #6024](https://github.com/sqlalchemy/sqlalchemy/discussions/6024)
- PostgreSQL date_trunc timezone pitfall: [Timezone-Aware date_trunc — w3tutorials.net](https://www.w3tutorials.net/blog/timezone-aware-date-trunc-function/), [PostgreSQL DATE_TRUNC — Neon Docs](https://neon.com/docs/functions/date_trunc)
- NULL values in aggregate joins: [PostgreSQL NULL Values in Queries — Percona](https://www.percona.com/blog/handling-null-values-in-postgresql/)
- PostgreSQL analytics performance: [Postgres Tuning & Performance for Analytics — Crunchy Data](https://www.crunchydata.com/blog/postgres-tuning-and-performance-for-analytics-data), [Understanding Postgres Performance Limits for Analytics — TigerData](https://www.tigerdata.com/blog/postgres-optimization-treadmill)
- FastAPI router-level dependency for auth: [Enhancing Authentication: Middleware vs. Router-Level Dependencies — Medium](https://medium.com/@anto18671/efficiency-of-using-dependencies-on-router-in-fastapi-c3b288ac408b)
- v2.0 tech debt carry-forward: `v2.0-MILESTONE-AUDIT.md` (N+1 `has_user_purchased_book()` in `list_for_book` — accepted at page_size ≤ 20)

---
*Pitfalls research for: FastAPI bookstore v2.1 — admin analytics dashboard and review moderation*
*Researched: 2026-02-27*
