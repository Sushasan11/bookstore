# Phase 15: Book Detail Aggregates - Research

**Researched:** 2026-02-26
**Domain:** FastAPI / SQLAlchemy / Pydantic schema extension — live SQL aggregates on existing endpoint
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGGR-01 | Book detail response includes average rating (rounded to 1 decimal) | `ReviewRepository.get_aggregates()` already implemented; `BookDetailResponse` schema needs `avg_rating: float | None` field; router handler must call aggregates query |
| AGGR-02 | Book detail response includes total review count | Same `get_aggregates()` call returns `review_count: int`; `BookDetailResponse` needs `review_count: int` field |
</phase_requirements>

---

## Summary

Phase 15 is the narrowest phase in the v2.0 milestone. The entire aggregate computation is already implemented in `ReviewRepository.get_aggregates()` (Phase 13), and a `get_aggregates` method is already present in the repository. The remaining work is purely wiring: extend `BookDetailResponse` with two new fields (`avg_rating` and `review_count`), teach the `GET /books/{id}` router handler to fetch those aggregates and merge them into the response, and write integration tests that verify the contract.

No new tables, no migrations, no new services, and no new repositories are needed. The SQL aggregate pattern (`func.avg`, `func.count`, soft-delete filter) is already in production. The key technical questions are: (1) how to pass aggregate data through the existing `BookService._get_book_or_404` + `BookDetailResponse.model_validate(book)` pipeline cleanly, and (2) how to round `avg_rating` to one decimal place in a way that survives Pydantic serialization correctly.

**Primary recommendation:** Extend `BookDetailResponse` with `avg_rating: float | None` and `review_count: int`, fetch aggregates in the `get_book` route handler (not in BookService) using a `ReviewRepository` instance, construct `BookDetailResponse` from both the ORM `book` object and the aggregate dict, and verify with three targeted integration tests covering: reviews-present case, zero-reviews case, and post-submit-reflects-updated-aggregate case.

---

## Standard Stack

### Core (already installed — no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy (async) | installed (project uses it) | `func.avg`, `func.count` aggregate queries | Already in use throughout the project |
| Pydantic v2 | installed | `BookDetailResponse` schema extension | Already in use |
| FastAPI | installed | Router handler modification | Already in use |
| asyncpg | installed | PostgreSQL async driver | Already in use |

### No new dependencies required

This phase requires zero new package installs. The aggregate SQL is already written.

---

## Architecture Patterns

### What Already Exists (do not rebuild)

`ReviewRepository.get_aggregates(book_id)` (at `app/reviews/repository.py` line 141) already:
- Queries `func.avg(Review.rating)` and `func.count(Review.id)` with `deleted_at IS NULL` filter
- Returns `{"avg_rating": float | None, "review_count": int}`
- Handles zero-review case: `avg_rating=None`, `review_count=0`
- Rounds to 1 decimal via `float(round(avg_rating, 1))`

Note from STATE.md: `func.avg().cast(Numeric)` is required for two-argument `ROUND` in PostgreSQL (DOUBLE PRECISION from avg() is incompatible). The existing `get_aggregates()` uses Python-side `round()` instead of SQL-side `ROUND()`, avoiding this type issue entirely. This is already correct — do not change it.

### Pattern 1: BookDetailResponse Schema Extension

**What:** Add two optional-aware fields to the existing `BookDetailResponse` Pydantic model in `app/books/schemas.py`.

**Current `BookDetailResponse`** (lines 106-130 of `app/books/schemas.py`):
```python
class BookDetailResponse(BaseModel):
    id: int
    title: str
    author: str
    price: Decimal
    isbn: str | None
    genre_id: int | None
    description: str | None
    cover_image_url: str | None
    publish_date: date | None
    stock_quantity: int

    @computed_field
    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    model_config = {"from_attributes": True}
```

**After Phase 15:**
```python
class BookDetailResponse(BaseModel):
    id: int
    title: str
    author: str
    price: Decimal
    isbn: str | None
    genre_id: int | None
    description: str | None
    cover_image_url: str | None
    publish_date: date | None
    stock_quantity: int
    avg_rating: float | None    # NEW — None when no reviews exist
    review_count: int           # NEW — 0 when no reviews exist

    @computed_field
    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    model_config = {"from_attributes": True}
```

`from_attributes = True` allows construction from ORM objects. However, because `avg_rating` and `review_count` are NOT ORM attributes on the `Book` model, they cannot be read from the ORM object directly. This means `BookDetailResponse.model_validate(book)` will fail after adding these fields — the construction strategy in the router must change.

### Pattern 2: Router Handler — Construction Strategy

**Current `get_book` handler** (`app/books/router.py` line 84-93):
```python
@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: int, db: DbSession) -> BookDetailResponse:
    service = _make_service(db)
    book = await service._get_book_or_404(book_id)
    return BookDetailResponse.model_validate(book)
```

**Problem:** After adding `avg_rating` and `review_count` to `BookDetailResponse`, `model_validate(book)` will fail because the `Book` ORM model has no `avg_rating` or `review_count` attribute.

**Solution — two construction approaches:**

**Option A: model_validate from dict (recommended pattern)**
Construct a plain dict merging book ORM fields with aggregate data:
```python
@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: int, db: DbSession) -> BookDetailResponse:
    service = _make_service(db)
    book = await service._get_book_or_404(book_id)
    review_repo = ReviewRepository(db)
    aggregates = await review_repo.get_aggregates(book.id)
    return BookDetailResponse.model_validate({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "price": book.price,
        "isbn": book.isbn,
        "genre_id": book.genre_id,
        "description": book.description,
        "cover_image_url": book.cover_image_url,
        "publish_date": book.publish_date,
        "stock_quantity": book.stock_quantity,
        **aggregates,
    })
```

**Option B: model_validate from ORM object + extra keyword args (Pydantic v2)**
Pydantic v2 `model_validate` with `from_attributes=True` only reads ORM attributes. To add non-ORM fields, passing a dict (Option A) or using `model_construct` is cleaner. Option A is preferred — same pattern used by `ReviewService._build_review_data()` which builds a plain dict for `ReviewResponse.model_validate()`.

**Project precedent:** `ReviewService._build_review_data()` already builds a plain dict for `ReviewResponse.model_validate()` when ORM field names differ from schema field names. This is the established pattern in this codebase. Use Option A consistently.

### Pattern 3: ReviewRepository Instantiation in Books Router

The books router must instantiate `ReviewRepository` directly in the `get_book` handler. This is the established pattern in this project — repositories are instantiated directly in routers, not through services. See `app/books/router.py` line 25-30 (`_make_service`) and `app/reviews/router.py` line 20-26 (`_make_service`). Cross-domain repository access without circular imports is documented in STATE.md:

> Cross-domain purchase check: ReviewService injects OrderRepository (not OrderService) — avoids circular import, mirrors BookService/PreBookRepository pattern

Import `ReviewRepository` directly from `app.reviews.repository` at the top of `app/books/router.py`. This is safe — no circular import because `app/reviews/repository.py` only imports from `app/reviews/models.py` and `app/core/exceptions.py`.

### Pattern 4: `get_aggregates()` Soft-Delete Filter

The existing `get_aggregates()` already filters `Review.deleted_at.is_(None)`. This means soft-deleted reviews are correctly excluded from the aggregate. This satisfies Success Criterion 3 (post-submit reflects updated aggregate) automatically when reviews are deleted via soft-delete.

### Anti-Patterns to Avoid

- **Storing avg_rating/review_count on the books table:** Denormalized columns require a trigger or application-level update on every review create/update/delete. STATE.md explicitly decided against this: "Aggregate avg_rating/review_count computed live via SQL AVG/COUNT — not stored on books table."
- **Computing aggregates in BookService:** This introduces a cross-domain import chain. Better to instantiate `ReviewRepository` in the router handler directly (same as how `PreBookRepository` is instantiated in the `update_stock` endpoint of `books/router.py`).
- **Using `model_validate(book)` after adding aggregate fields:** Will fail because `Book` ORM has no `avg_rating` or `review_count` attributes. Use dict construction.
- **SQL-side ROUND with DOUBLE PRECISION:** `func.round(func.avg(...), 1)` fails in PostgreSQL because `AVG()` returns `DOUBLE PRECISION` and `ROUND(double, int)` is not defined. The existing `get_aggregates()` uses Python `round()` correctly — do not change it to SQL-side rounding.
- **N+1 on aggregate:** The `get_aggregates()` executes one SQL query. The full `get_book` handler will now execute two queries (book fetch + aggregate). This is acceptable — no N+1 concern here.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Avg/count SQL | Custom aggregate logic | `ReviewRepository.get_aggregates()` (already exists) | Already implemented, tested, handles edge cases |
| Rounding to 1 decimal | Custom rounding | Python built-in `round(x, 1)` (already in get_aggregates) | Already correct |
| Schema merging | Custom serializer | Pydantic dict-based `model_validate({...})` | Established project pattern (_build_review_data) |

**Key insight:** Everything needed is already built. This phase is purely wiring.

---

## Common Pitfalls

### Pitfall 1: `model_validate(book)` breaks after schema extension
**What goes wrong:** Adding `avg_rating` and `review_count` to `BookDetailResponse` without changing the construction call in the router causes a `ValidationError` because Pydantic cannot find those attributes on the `Book` ORM object.
**Why it happens:** `from_attributes=True` reads ORM attributes, and `avg_rating`/`review_count` are not columns on `books` table.
**How to avoid:** Switch the `get_book` router handler to build a plain dict (Option A above) before calling `model_validate`.
**Warning signs:** Any `ValidationError` at startup or test time mentioning `avg_rating` or `review_count`.

### Pitfall 2: Existing test_catalog.py `test_get_book` may fail
**What goes wrong:** The existing `test_get_book` test in `tests/test_catalog.py` calls `GET /books/{id}` and asserts `resp.json()["title"]`. After adding `avg_rating` and `review_count` to the response schema, the test _should_ still pass because Pydantic will supply `avg_rating=None, review_count=0` for a book with no reviews. The `get_aggregates()` query returns defaults for a book with no reviews. However, if the test's book was created in a clean state with no reviews, it will get `avg_rating=null` and `review_count=0` — acceptable.
**How to avoid:** Run existing tests after schema change. No change to existing test assertions needed.

### Pitfall 3: avg_rating type leakage
**What goes wrong:** PostgreSQL `AVG()` returns a Python `Decimal` or `float`. If `avg_rating` is declared as `float | None` in Pydantic but the query returns a `Decimal`, Pydantic v2 will coerce it (since `float` is compatible with `Decimal` coercion). The existing code does `float(round(avg_rating, 1))` which explicitly converts to Python float — this is correct.
**How to avoid:** Do not change `get_aggregates()`. The existing coercion is correct.

### Pitfall 4: Importing ReviewRepository creates circular import in books router
**What goes wrong:** `app/books/router.py` imports from `app/reviews/repository.py` which imports `app/reviews/models.py`. This could theoretically create circular imports if the review models import from books models.
**Why it won't happen:** `app/reviews/models.py` uses `TYPE_CHECKING` guard for the `Book` import — no runtime circular import. This is safe.

### Pitfall 5: Both existing catalog tests and new aggregate tests needed
**What goes wrong:** Writing only happy-path tests and missing the zero-reviews case or the post-create-reflects case.
**How to avoid:** Three tests are required per ROADMAP success criteria: (1) avg_rating and review_count present with reviews, (2) null avg_rating and zero count with no reviews, (3) post-review-create reflects updated aggregate.

---

## Code Examples

### Get Aggregates (already implemented)
```python
# Source: app/reviews/repository.py, lines 141-163
async def get_aggregates(self, book_id: int) -> dict:
    result = await self.session.execute(
        select(
            func.avg(Review.rating),
            func.count(Review.id),
        ).where(
            Review.book_id == book_id,
            Review.deleted_at.is_(None),
        )
    )
    row = result.one()
    avg_rating = row[0]
    review_count = row[1]

    return {
        "avg_rating": float(round(avg_rating, 1)) if avg_rating is not None else None,
        "review_count": review_count,
    }
```

### Updated BookDetailResponse (target state)
```python
# app/books/schemas.py — add two fields to BookDetailResponse
class BookDetailResponse(BaseModel):
    id: int
    title: str
    author: str
    price: Decimal
    isbn: str | None
    genre_id: int | None
    description: str | None
    cover_image_url: str | None
    publish_date: date | None
    stock_quantity: int
    avg_rating: float | None    # None when no reviews
    review_count: int           # 0 when no reviews

    @computed_field
    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    model_config = {"from_attributes": True}
```

### Updated get_book router handler (target state)
```python
# app/books/router.py — import ReviewRepository, rewrite get_book
from app.reviews.repository import ReviewRepository  # add to imports

@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: int, db: DbSession) -> BookDetailResponse:
    """Get book by ID including stock status and rating aggregates. Public."""
    service = _make_service(db)
    book = await service._get_book_or_404(book_id)
    review_repo = ReviewRepository(db)
    aggregates = await review_repo.get_aggregates(book.id)
    return BookDetailResponse.model_validate({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "price": book.price,
        "isbn": book.isbn,
        "genre_id": book.genre_id,
        "description": book.description,
        "cover_image_url": book.cover_image_url,
        "publish_date": book.publish_date,
        "stock_quantity": book.stock_quantity,
        **aggregates,
    })
```

### Integration test structure (target state)
```python
# tests/test_book_aggregates.py — new file covering AGGR-01 and AGGR-02
class TestBookDetailAggregates:
    """GET /books/{id} returns avg_rating and review_count — AGGR-01 and AGGR-02."""

    async def test_no_reviews_returns_null_avg_and_zero_count(
        self, client, db_session
    ):
        """Book with no reviews: avg_rating=null, review_count=0."""
        book = Book(title="T", author="A", price=Decimal("9.99"), stock_quantity=1)
        db_session.add(book)
        await db_session.flush()

        resp = await client.get(f"/books/{book.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] is None
        assert data["review_count"] == 0

    async def test_with_reviews_returns_rounded_avg_and_count(
        self, client, user_headers, purchased_book
    ):
        """Book with two reviews: avg_rating rounded to 1 decimal, review_count=2."""
        # ... create two reviews via API, then GET /books/{id}
        # e.g. ratings 4 and 5 → avg 4.5

    async def test_after_review_submitted_aggregate_reflects_change(
        self, client, user_headers, purchased_book
    ):
        """After POST /books/{id}/reviews, next GET /books/{id} reflects updated aggregate."""
        # GET before review → avg_rating=null, review_count=0
        # POST review with rating=3
        # GET after review → avg_rating=3.0, review_count=1
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Denormalized avg/count columns on books table | Live SQL AVG/COUNT query per request | Decided in STATE.md — simpler, always current |
| SQL-side ROUND(AVG(...), 1) | Python-side round() | SQL ROUND incompatible with DOUBLE PRECISION in PostgreSQL |
| Storing aggregates in BookService | Direct ReviewRepository use in router | Avoids service layer coupling across domains |

---

## Open Questions

1. **Should `avg_rating` and `review_count` be added to `BookResponse` (list endpoint) as well?**
   - What we know: Phase 15 success criteria only mention `GET /books/{id}` (detail endpoint). REQUIREMENTS.md AGGR-01 and AGGR-02 say "Book detail response" specifically.
   - What's unclear: Whether the client needs aggregates on the list endpoint too. SRCH-01 (future) says "sort/filter books by average rating in search results" but that is Out of Scope for v2.0.
   - Recommendation: Only extend `BookDetailResponse`, not `BookResponse`. List endpoint changes are future scope.

2. **Does `test_catalog.py::test_get_book` need updating?**
   - What we know: It calls `GET /books/{id}` and asserts `resp.json()["title"] == "To Kill a Mockingbird"`. It does not assert on missing keys, so new fields won't break it.
   - What's unclear: Nothing — it will pass as-is since a book with no reviews returns `avg_rating=null, review_count=0`.
   - Recommendation: No change needed to existing catalog tests.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` or inferred from `pyproject.toml` (check project root) |
| Quick run command | `pytest tests/test_book_aggregates.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGGR-01 | `avg_rating` rounded to 1 decimal returned by `GET /books/{id}` | integration | `pytest tests/test_book_aggregates.py::TestBookDetailAggregates::test_with_reviews_returns_rounded_avg_and_count -x` | No — Wave 0 |
| AGGR-02 | `review_count` integer returned by `GET /books/{id}` | integration | `pytest tests/test_book_aggregates.py::TestBookDetailAggregates::test_no_reviews_returns_null_avg_and_zero_count -x` | No — Wave 0 |
| AGGR-01 + AGGR-02 | Zero-reviews case: `null` avg, `0` count | integration | `pytest tests/test_book_aggregates.py::TestBookDetailAggregates::test_no_reviews_returns_null_avg_and_zero_count -x` | No — Wave 0 |
| AGGR-01 + AGGR-02 | Post-review reflects updated aggregate | integration | `pytest tests/test_book_aggregates.py::TestBookDetailAggregates::test_after_review_submitted_aggregate_reflects_change -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_book_aggregates.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/test_book_aggregates.py` — covers AGGR-01, AGGR-02 (all three success criteria)

*(Existing test infrastructure in `conftest.py` covers all needed fixtures. No new conftest entries needed — reuse `client`, `db_session`, and the `rev_user` / `purchased_book` fixture pattern from `test_reviews.py`.)*

---

## Scope Boundaries (what this phase does NOT touch)

- No Alembic migration — no schema changes on the `books` or `reviews` tables
- No change to `BookResponse` (the list endpoint schema)
- No change to `ReviewRepository.get_aggregates()` — it is already correct
- No change to `BookService` — aggregates fetched directly in router handler
- No caching layer — live query per request (SUCCESS CRITERION 3 requires this)
- No `avg_rating` sort/filter on `GET /books` — deferred to SRCH-01

---

## Sources

### Primary (HIGH confidence)
- Codebase: `app/reviews/repository.py` — `get_aggregates()` already implemented at lines 141-163
- Codebase: `app/books/schemas.py` — `BookDetailResponse` current structure at lines 106-130
- Codebase: `app/books/router.py` — `get_book` handler at lines 84-93
- Codebase: `.planning/STATE.md` — decisions: "Aggregate avg_rating/review_count computed live via SQL AVG/COUNT", "func.avg().cast(Numeric) required for two-argument ROUND in PostgreSQL"
- Codebase: `app/reviews/service.py` — `_build_review_data()` pattern (dict-based model_validate) at lines 183-209
- Codebase: `.planning/ROADMAP.md` — Phase 15 success criteria

### Secondary (MEDIUM confidence)
- Pydantic v2 documentation: `model_validate` with `from_attributes=True` reads ORM attributes; non-ORM fields require dict construction or `model_construct`

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries needed, everything in use
- Architecture: HIGH — get_aggregates() exists, dict-based model_validate is established pattern
- Pitfalls: HIGH — based on direct code inspection of existing types and construction patterns
- Test gaps: HIGH — test infrastructure is fully in place, only new test file needed

**Research date:** 2026-02-26
**Valid until:** Stable (no fast-moving dependencies; valid until codebase changes)
