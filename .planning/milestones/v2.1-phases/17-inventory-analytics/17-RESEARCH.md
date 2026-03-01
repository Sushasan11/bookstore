# Phase 17: Inventory Analytics - Research

**Researched:** 2026-02-27
**Domain:** FastAPI analytics endpoint — SQLAlchemy simple filter-and-sort query against the Book model, admin-protected read-only endpoint extending the Phase 16 analytics infrastructure
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Response data shape**
- Minimal fields per book: book_id, title, author, current_stock, threshold
- No extended fields (price, category, ISBN) — keep it focused on restocking decisions
- Include `total_low_stock` count at the top level for dashboard summary use

**Default threshold**
- Default threshold value: 10 when `?threshold=` parameter is not provided
- Threshold is optional query parameter, not required

**Zero-stock handling**
- No special distinction between out-of-stock (0) and low-stock (>0 but below threshold)
- All books at or below threshold in one flat list, ordered by stock ascending
- Zero-stock books naturally sort to top — no extra flag needed

### Claude's Discretion

- Pagination strategy (if needed based on typical catalog size)
- Response schema naming conventions (match existing analytics patterns from Phase 16)
- Repository query approach (reuse existing book queries or dedicated method)
- Error handling for invalid threshold values

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INV-01 | Admin can query books with stock at or below a configurable threshold, ordered by stock ascending | Simple `SELECT book_id, title, author, stock_quantity FROM books WHERE stock_quantity <= :threshold ORDER BY stock_quantity ASC` — directly against the `Book` model; no joins to orders tables; no aggregation; query pattern is simpler than any Phase 16 query |
</phase_requirements>

## Summary

Phase 17 is a single-endpoint, read-only analytics feature that extends the Phase 16 infrastructure with minimal new code. The endpoint `GET /admin/analytics/inventory/low-stock?threshold=10` queries the existing `books` table for all books at or below the threshold, ordered by `stock_quantity` ascending. No migrations, no new packages, and no new infrastructure are needed.

The implementation adds one new method to `AnalyticsRepository` (`low_stock_books(threshold)`), two new Pydantic schemas (`LowStockBookEntry`, `LowStockResponse`), and one new route function to `analytics_router.py`. No service layer is needed — like the `top_books()` method from Phase 16, this is a direct repository query with no derived-metric orchestration. The `total_low_stock` count at the top level is computed as `len(items)` in the endpoint handler or as a `COUNT` in the same query.

The primary risk for this phase is minimal. Unlike sales analytics, inventory analytics does not touch the `orders` or `order_items` tables, does not require period bound logic, and does not involve nullable foreign keys or aggregate decimal serialization. The only design decision left to Claude's discretion is the threshold validation strategy (FastAPI `Query(ge=0)` is sufficient) and whether pagination is needed (research below concludes it is not needed for this phase given typical catalog sizes and the intent of the endpoint).

**Primary recommendation:** Add `low_stock_books(threshold: int)` to the existing `AnalyticsRepository`, new schemas to `analytics_schemas.py`, and a new route to `analytics_router.py`. No service layer, no new file, no migration.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | ^0.133.0 | HTTP routing, Query param validation with `ge=0`, response_model | Existing project framework; locked |
| SQLAlchemy | ^2.0.47 (asyncio) | `select(Book).where(Book.stock_quantity <= threshold).order_by(asc(Book.stock_quantity))` | Existing; all needed constructs are available; no extensions needed |
| asyncpg | ^0.31.0 | Async PostgreSQL driver | Existing; locked |
| Pydantic | ^2.12.5 | Response schema validation and JSON serialization | Existing; locked |
| PostgreSQL | (docker-compose) | `WHERE stock_quantity <= N ORDER BY stock_quantity ASC` — basic filter/sort | Existing DB; locked |

### Supporting

No additional supporting libraries are needed beyond what Phase 16 already uses.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `len(items)` for total_low_stock in endpoint | SQL `COUNT(*)` sub-query | Since all results are returned (no pagination), `len(items)` is equivalent and avoids a second DB round-trip. If pagination is ever added, switch to `COUNT(*)` sub-query. |
| No pagination (return all matching books) | Keyset or offset pagination | Low-stock books are typically a small subset; the endpoint is for operational restocking decisions where you want to see all books below threshold at once. Pagination complicates the UI use case and is not needed at this scale. |

**Installation:**
```bash
# No new packages required — all dependencies already installed.
```

## Architecture Patterns

### Recommended Project Structure

```
app/
├── admin/
│   ├── analytics_repository.py    # MODIFY: add low_stock_books() method
│   ├── analytics_schemas.py       # MODIFY: add LowStockBookEntry, LowStockResponse
│   ├── analytics_router.py        # MODIFY: add GET /inventory/low-stock endpoint
│   ├── analytics_service.py       # UNCHANGED: no service layer needed for this query
│   ├── router.py                  # UNCHANGED
│   ├── schemas.py                 # UNCHANGED
│   └── service.py                 # UNCHANGED
└── main.py                        # UNCHANGED: analytics_router already registered
tests/
└── test_inventory_analytics.py    # NEW: integration tests for INV-01
```

No new files in `app/`, no migrations, no changes to `app/main.py` (analytics router is already registered).

### Pattern 1: Low-Stock Query — Direct Book Filter, No Joins

**What:** `AnalyticsRepository.low_stock_books(threshold)` queries the `books` table directly. No join to orders. No aggregation. Simple `WHERE stock_quantity <= threshold ORDER BY stock_quantity ASC`.

**When to use:** Any inventory-state query that only needs the current value of `Book.stock_quantity`. No need to involve orders or order_items — inventory state is stored directly in `books.stock_quantity`.

**Example:**
```python
# Source: direct Book model inspection (app/books/models.py)
# app/admin/analytics_repository.py — add to existing AnalyticsRepository class

from sqlalchemy import asc, select
from app.books.models import Book


async def low_stock_books(self, *, threshold: int) -> list[dict]:
    """Return all books with stock_quantity <= threshold, ordered by stock ascending.

    Books with zero stock appear first (ORDER BY stock_quantity ASC).
    No join to orders — current inventory state lives on the Book model.

    Args:
        threshold: Maximum stock_quantity to include (inclusive).

    Returns:
        List of dicts with keys: book_id, title, author, current_stock.
    """
    stmt = (
        select(
            Book.id.label("book_id"),
            Book.title,
            Book.author,
            Book.stock_quantity.label("current_stock"),
        )
        .where(Book.stock_quantity <= threshold)
        .order_by(asc(Book.stock_quantity))
    )
    result = await self._db.execute(stmt)
    return [row._asdict() for row in result.all()]
```

### Pattern 2: Response Schema — total_low_stock at Top Level

**What:** The `LowStockResponse` schema includes a `total_low_stock` count at the top level per the locked decision. Since all results are returned (no pagination), `total_low_stock` equals `len(items)` and can be set in the endpoint handler — no second DB query needed.

**Example:**
```python
# Source: Phase 16 schema pattern (app/admin/analytics_schemas.py)
# app/admin/analytics_schemas.py — add after existing schemas

class LowStockBookEntry(BaseModel):
    """Single book entry in the low-stock inventory report."""
    book_id: int
    title: str
    author: str
    current_stock: int
    threshold: int  # echo back the threshold used — locked decision


class LowStockResponse(BaseModel):
    """Response schema for GET /admin/analytics/inventory/low-stock."""
    threshold: int          # echo back threshold for dashboard use
    total_low_stock: int    # count of books at or below threshold
    items: list[LowStockBookEntry]
```

### Pattern 3: Endpoint — Query Validation with ge=0, Default Threshold=10

**What:** The endpoint uses `Query(10, ge=0)` for the threshold parameter. `ge=0` ensures negative thresholds return 422 automatically. Default of `10` applies when the parameter is omitted. The `threshold` value is echoed back in each item (locked decision) and at the top level.

**When to use:** All analytics endpoints. FastAPI `Query()` with validation constraints (`ge`, `le`, `pattern`) is the established pattern in this project — verified in Phase 16 `top_books` endpoint which uses `Query(10, ge=1, le=50)`.

**Example:**
```python
# Source: Phase 16 analytics_router.py pattern
# app/admin/analytics_router.py — add after existing top-books endpoint

from app.admin.analytics_schemas import LowStockResponse  # add to existing import

@router.get("/inventory/low-stock", response_model=LowStockResponse)
async def get_low_stock_books(
    db: DbSession,
    _admin: AdminUser,
    threshold: int = Query(10, ge=0),
) -> LowStockResponse:
    """Return all books with stock at or below the threshold, ordered by stock ascending.

    Query parameters:
    - threshold: Stock level at or below which a book is considered low-stock (default 10, min 0).

    Books with zero stock appear first. Admin only. threshold < 0 returns 422.
    """
    repo = AnalyticsRepository(db)
    books = await repo.low_stock_books(threshold=threshold)
    # Inject threshold into each item (locked decision: include threshold in each entry)
    items = [{"threshold": threshold, **b} for b in books]
    return LowStockResponse(
        threshold=threshold,
        total_low_stock=len(items),
        items=items,
    )
```

### Pattern 4: Test Fixture — Book Stock Setup Without Orders

**What:** Integration tests for INV-01 create `Book` rows with specific `stock_quantity` values directly in the test DB. No orders needed — the endpoint reads only from the `books` table. Follow the same `admin_headers`/`user_headers` fixture pattern from Phase 16 tests.

**Example:**
```python
# Source: Phase 16 test_sales_analytics.py fixture pattern
# tests/test_inventory_analytics.py

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.books.models import Book, Genre
from app.core.security import hash_password
from app.users.repository import UserRepository

LOW_STOCK_URL = "/admin/analytics/inventory/low-stock"

@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create admin user and return Bearer auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="admin_inventory@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    resp = await client.post(
        "/auth/login",
        json={"email": "admin_inventory@example.com", "password": "adminpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

@pytest_asyncio.fixture
async def stock_books(db_session: AsyncSession) -> list[Book]:
    """Create a Genre and books with specific stock_quantity values for testing."""
    genre = Genre(name="Inventory Test Genre")
    db_session.add(genre)
    await db_session.flush()

    books = [
        Book(title="Zero Stock Book",   author="Author Z", price=Decimal("10.00"), stock_quantity=0,  genre_id=genre.id),
        Book(title="Low Stock Book",    author="Author L", price=Decimal("10.00"), stock_quantity=5,  genre_id=genre.id),
        Book(title="Threshold Book",    author="Author T", price=Decimal("10.00"), stock_quantity=10, genre_id=genre.id),
        Book(title="Above Threshold",   author="Author A", price=Decimal("10.00"), stock_quantity=11, genre_id=genre.id),
        Book(title="Well Stocked Book", author="Author W", price=Decimal("10.00"), stock_quantity=50, genre_id=genre.id),
    ]
    db_session.add_all(books)
    await db_session.flush()
    return books
```

### Anti-Patterns to Avoid

- **Joining to orders to compute low-stock:** `Book.stock_quantity` is the authoritative current stock; it is decremented on confirmed purchase. There is no need to join order tables — that would compute stock from order history, not the live inventory column.
- **Adding low_stock_books() to BookRepository:** This is an admin analytics query, not a user-facing catalog query. It belongs in `AnalyticsRepository` in `app/admin/`, consistent with Phase 16's cross-domain read-only pattern.
- **Creating a service layer for this endpoint:** The Phase 16 pattern establishes that a service layer is only needed when there is multi-query orchestration or period-comparison arithmetic (see `top_books()` which goes directly to repository). A single filter-and-sort query needs no service layer.
- **Registering a new router:** The `analytics_router` is already registered in `app/main.py`. Adding a new route to the existing router avoids any `main.py` change.
- **Using `Book.stock_quantity < threshold` (strict less-than):** The requirement says "at or below" — must use `<=`, not `<`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Threshold validation | Manual `if threshold < 0: raise` | `Query(10, ge=0)` | FastAPI auto-returns 422 with standard error body; no custom exception handler needed |
| total_low_stock count | Second `COUNT(*)` SQL query | `len(items)` | Since no pagination, all results are already in memory; a second query adds latency with no benefit |
| Stock-ascending sort | Python `sorted(items, key=...)` | `ORDER BY stock_quantity ASC` in SQL | DB sorts more efficiently than Python; pushes all computation to PostgreSQL |

**Key insight:** This is the simplest analytics query in the entire project — a single-table filter with no joins, no aggregates, no derived metrics. Complexity would be actively harmful here.

## Common Pitfalls

### Pitfall 1: Using Strict Less-Than Instead of Less-Than-Or-Equal

**What goes wrong:** `Book.stock_quantity < threshold` excludes books at exactly the threshold value. A book with `stock_quantity = 10` and `threshold = 10` should appear in results (it is "at or below") but is silently excluded.

**Why it happens:** Natural language "below threshold" can be misread as strict `<`. The requirement and locked decision both say "at or below."

**How to avoid:** Always use `Book.stock_quantity <= threshold`. Add a test case with a book at exactly the threshold value and verify it appears in results.

**Warning signs:** `test_book_at_threshold_is_included` fails; book with stock == threshold is missing from response.

### Pitfall 2: Including threshold in Each Item

**What goes wrong:** The locked decision specifies that each `LowStockBookEntry` includes the `threshold` value. Omitting it means the frontend cannot display "5 units (threshold: 10)" without making a second API call to get the threshold context.

**Why it happens:** The threshold is a query parameter that feels redundant to echo in each item when it's already at the top level.

**How to avoid:** Include `threshold: int` in `LowStockBookEntry` and populate it from the query parameter in the endpoint handler. Since the repository method returns `book_id, title, author, current_stock`, the endpoint must inject threshold: `[{"threshold": threshold, **b} for b in books]`.

**Warning signs:** `LowStockBookEntry` schema validation fails because `threshold` is missing from items dict; test assertions on `items[0]["threshold"]` fail.

### Pitfall 3: Wrong Sort Direction

**What goes wrong:** `ORDER BY stock_quantity DESC` puts the most-stocked books first. The requirement and success criteria both require `ORDER BY stock_quantity ASC` so zero-stock books appear at the top.

**Why it happens:** `desc()` is more commonly used in analytics rankings (top-sellers); `asc()` is the correct choice here and could be confused.

**How to avoid:** Import and use `asc` from `sqlalchemy`: `.order_by(asc(Book.stock_quantity))`. Write a test that verifies the first item has the lowest stock.

**Warning signs:** Test for "zero-stock books appear at top" fails; items are in reverse order.

### Pitfall 4: Using a New Router Instead of Extending the Existing One

**What goes wrong:** Creating a new `inventory_router.py` and registering it in `main.py` adds unnecessary files and a `main.py` modification. The existing `analytics_router` already has the `/admin/analytics` prefix and `require_admin` protection.

**Why it happens:** Developers follow the Phase 16 pattern of creating new files, not realizing this phase's endpoint fits cleanly into the existing router.

**How to avoid:** Add the new route directly to `analytics_router.py`. The URL will be `/admin/analytics/inventory/low-stock` automatically.

**Warning signs:** `main.py` requires modification for Phase 17; two analytics router files exist.

### Pitfall 5: Querying via BookRepository Instead of AnalyticsRepository

**What goes wrong:** Adding a `get_low_stock()` method to `BookRepository` (which lives in `app/books/repository.py`) makes the admin-only analytics query visible to user-facing code and breaks the admin/books domain separation established in Phase 16.

**Why it happens:** The query touches the `books` table, which might suggest it belongs in the books domain.

**How to avoid:** Add `low_stock_books()` to `AnalyticsRepository` in `app/admin/analytics_repository.py`. The query is admin-only and read-only — it belongs in the analytics repository regardless of which table it reads.

## Code Examples

Verified patterns from existing codebase:

### Low-Stock Repository Method
```python
# Source: direct Book model inspection (app/books/models.py) + Phase 16 repository pattern
# app/admin/analytics_repository.py

from sqlalchemy import asc, desc, func, select  # add 'asc' to existing import

async def low_stock_books(self, *, threshold: int) -> list[dict]:
    """Return books with stock_quantity at or below threshold, ordered ascending.

    Args:
        threshold: Inclusive upper bound for stock_quantity filter.

    Returns:
        List of dicts: {book_id, title, author, current_stock}.
        Ordered by current_stock ascending (zero-stock books first).
    """
    stmt = (
        select(
            Book.id.label("book_id"),
            Book.title,
            Book.author,
            Book.stock_quantity.label("current_stock"),
        )
        .where(Book.stock_quantity <= threshold)
        .order_by(asc(Book.stock_quantity))
    )
    result = await self._db.execute(stmt)
    return [row._asdict() for row in result.all()]
```

### Pydantic Schemas
```python
# Source: Phase 16 schema pattern (app/admin/analytics_schemas.py)
# app/admin/analytics_schemas.py — add after TopBooksResponse

class LowStockBookEntry(BaseModel):
    """Single book entry in the low-stock inventory report.

    threshold is echoed per-item per locked decision — allows dashboard to show
    "5 units (threshold: 10)" without a second API call.
    """
    book_id: int
    title: str
    author: str
    current_stock: int
    threshold: int


class LowStockResponse(BaseModel):
    """Response schema for GET /admin/analytics/inventory/low-stock."""
    threshold: int
    total_low_stock: int
    items: list[LowStockBookEntry]
```

### Endpoint
```python
# Source: Phase 16 analytics_router.py pattern + app/core/deps.py
# app/admin/analytics_router.py — add to existing router

from app.admin.analytics_schemas import (
    LowStockBookEntry,      # add to existing import
    LowStockResponse,       # add to existing import
    SalesSummaryResponse,
    TopBooksResponse,
)

@router.get("/inventory/low-stock", response_model=LowStockResponse)
async def get_low_stock_books(
    db: DbSession,
    _admin: AdminUser,
    threshold: int = Query(10, ge=0),
) -> LowStockResponse:
    """Return all books with stock at or below the threshold, ordered by stock ascending.

    Query parameters:
    - threshold: Inclusive stock level cutoff (default 10, minimum 0).

    Zero-stock books appear at the top of the list. Admin only. threshold < 0 returns 422.
    """
    repo = AnalyticsRepository(db)
    books = await repo.low_stock_books(threshold=threshold)
    items = [{"threshold": threshold, **b} for b in books]
    return LowStockResponse(
        threshold=threshold,
        total_low_stock=len(items),
        items=items,
    )
```

### Integration Test Structure
```python
# Source: Phase 16 test_sales_analytics.py pattern
# tests/test_inventory_analytics.py

LOW_STOCK_URL = "/admin/analytics/inventory/low-stock"

class TestLowStockAuth:
    async def test_requires_auth(self, client): ...           # 401 without token
    async def test_requires_admin(self, client, user_headers): ...  # 403 for regular user

class TestLowStockBehavior:
    async def test_default_threshold_is_10(self, client, admin_headers, stock_books): ...
    async def test_custom_threshold_filters_correctly(self, client, admin_headers, stock_books): ...
    async def test_book_at_exact_threshold_is_included(self, client, admin_headers, stock_books): ...
    async def test_book_above_threshold_excluded(self, client, admin_headers, stock_books): ...
    async def test_ordered_by_stock_ascending(self, client, admin_headers, stock_books): ...
    async def test_zero_stock_books_appear_first(self, client, admin_headers, stock_books): ...
    async def test_threshold_echoed_in_each_item(self, client, admin_headers, stock_books): ...
    async def test_total_low_stock_count_correct(self, client, admin_headers, stock_books): ...
    async def test_empty_catalog_returns_empty_list(self, client, admin_headers): ...
    async def test_no_books_below_threshold_returns_empty(self, client, admin_headers, stock_books): ...
    async def test_threshold_zero_returns_only_zero_stock(self, client, admin_headers, stock_books): ...
    async def test_negative_threshold_returns_422(self, client, admin_headers): ...
    async def test_response_schema_fields(self, client, admin_headers, stock_books): ...
```

### Key Test Data Design
```python
# Stock levels that cover all boundary conditions:
# stock=0  → below any positive threshold, zero-stock, must sort first
# stock=5  → below threshold=10, appears in default call
# stock=10 → exactly at threshold=10, MUST be included (at-or-below)
# stock=11 → above threshold=10, MUST be excluded
# stock=50 → well above threshold, always excluded

# Threshold variations to test:
# threshold=10 (default) → includes stock=0,5,10; excludes 11,50
# threshold=5            → includes stock=0,5; excludes 10,11,50
# threshold=0            → includes only stock=0; excludes all others
# threshold=20           → includes stock=0,5,10,11; excludes 50
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 | Not applicable to this phase (no datetime) |
| Pydantic v1 Decimal-as-number | Pydantic v2 Decimal-as-string | Pydantic v2.0 | Not applicable — stock_quantity is `int`, not `Decimal`; no float conversion needed |
| SQLAlchemy 1.x `Query` ORM API | SQLAlchemy 2.0 `select()` + `execute()` | SQLAlchemy 2.0 | Use `select(Book.id, Book.title, ...).where(...).order_by(...)` pattern; `._asdict()` on each row |

**Deprecated/outdated:**
- None applicable to this phase — no period arithmetic, no Decimal money fields, no async special cases beyond what Phase 16 already handles.

## Open Questions

1. **Pagination for low-stock endpoint**
   - What we know: The endpoint returns all books at or below threshold. Typical bookstore catalogs have hundreds to low thousands of books. The threshold filters down to a small subset (books needing restocking).
   - What's unclear: The user decision says pagination is at Claude's discretion. For operational restocking, seeing all low-stock books at once is more useful than paginating through them.
   - Recommendation: No pagination for the initial implementation. The endpoint purpose is "what do I need to restock?" — an admin needs to see the full list. If catalog size ever exceeds practical threshold (10,000+ books with many low-stock), pagination can be added without a breaking schema change (add `page`/`per_page` params later). `len(items)` for `total_low_stock` works correctly with no pagination.

2. **Threshold validation upper bound**
   - What we know: `Query(10, ge=0)` prevents negative thresholds. There is no explicit upper bound in the locked decisions.
   - What's unclear: Whether an extremely large threshold (e.g., threshold=999999) that returns the entire catalog should be rejected or allowed.
   - Recommendation: No upper bound. The endpoint is admin-only; an admin choosing a very high threshold is a valid (if unusual) use case. `ge=0` is the only needed constraint per the requirements.

3. **`Book` import in analytics_repository.py**
   - What we know: The current `analytics_repository.py` imports `Book` from `app.books.models` (it already does this for the `top_books()` method — `from app.books.models import Book`).
   - What's unclear: Nothing — `Book` is already imported.
   - Recommendation: No action needed. `low_stock_books()` can use the existing `Book` import.

## Sources

### Primary (HIGH confidence)

- `app/admin/analytics_repository.py` — confirmed `AnalyticsRepository` class structure, `self._db` session attribute name, `[row._asdict() for row in result.all()]` return pattern, existing `Book` import
- `app/admin/analytics_router.py` — confirmed `APIRouter` prefix `/admin/analytics`, `dependencies=[Depends(require_admin)]` at constructor, `Query()` validation pattern, `DbSession`/`AdminUser` dep pattern
- `app/admin/analytics_schemas.py` — confirmed `BaseModel` schema pattern, `float` for money fields, no `Decimal` usage
- `app/books/models.py` — confirmed `Book.stock_quantity: Mapped[int]`, `Book.id`, `Book.title`, `Book.author` column names; `stock_quantity` is `Integer`, not nullable, with `CheckConstraint("stock_quantity >= 0")`
- `app/core/deps.py` — confirmed `AdminUser`, `DbSession`, `require_admin` type aliases
- `app/main.py` — confirmed `analytics_router` already registered; no `main.py` change needed for Phase 17
- `tests/test_sales_analytics.py` — confirmed admin/user fixture pattern, Genre+Book creation pattern in fixtures, `db_session.flush()` usage, `pytest_asyncio.fixture` decorator
- `tests/conftest.py` — confirmed `asyncio_mode = "auto"`, rollback-per-test session, `client` fixture with `app.dependency_overrides`
- `pyproject.toml` — confirmed `asyncio_mode = "auto"`, Python 3.13, pytest-asyncio ^1.3.0

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` Accumulated Context — confirmed Phase 16 decision "top-books goes directly to repository (no service layer) — no period/delta logic needed" applies identically to this phase's single query

### Tertiary (LOW confidence)

None — all findings verified from primary codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing dependencies; no new installs; versions confirmed from pyproject.toml
- Architecture: HIGH — derived from direct inspection of all relevant source files; `Book.stock_quantity` column type confirmed; session attribute name `self._db` confirmed; router prefix confirmed
- Pitfalls: HIGH — all pitfalls derived from direct model inspection and locked decisions; no assumptions
- Query pattern: HIGH — simpler than any Phase 16 query; single-table filter with no joins or aggregates

**Research date:** 2026-02-27
**Valid until:** 2026-03-29 (30 days — stable stack, no fast-moving dependencies)
