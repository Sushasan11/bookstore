# Architecture Research

**Domain:** Bookstore API v2.0 — Reviews & Ratings
**Researched:** 2026-02-26
**Confidence:** HIGH (existing codebase inspected directly; all integration points derived from actual source files, not assumptions)

---

## Context: Integration Problem, Not Greenfield

v2.0 adds reviews & ratings to an existing, working v1.1 codebase with 9,473 LOC and 179 passing tests.
The architecture pattern is locked in: every domain module follows the same five-file structure.
This document answers one question: how does `app/reviews/` plug into what already exists?

**Existing module pattern (all domains follow this):**

```
app/{domain}/
    models.py      # SQLAlchemy mapped classes inheriting Base
    schemas.py     # Pydantic request/response models
    repository.py  # AsyncSession + select() queries
    service.py     # Business rules, raises AppError
    router.py      # APIRouter, DI via Depends(), registered in main.py
```

**Existing shared infrastructure (unchanged for v2.0):**

```python
# app/core/deps.py
DbSession   = Annotated[AsyncSession, Depends(get_db)]  # per-request session with commit/rollback
CurrentUser = Annotated[dict, Depends(get_current_user)]  # JWT payload (sub, role)
ActiveUser  = Annotated[dict, Depends(get_active_user)]  # JWT + DB is_active check
AdminUser   = Annotated[dict, Depends(require_admin)]  # JWT role=admin + is_active check

# app/core/exceptions.py
class AppError(Exception):
    def __init__(self, status_code, detail, code, field=None): ...
```

---

## System Overview: v2.0 Integration Points

```
┌────────────────────────────────────────────────────────────────────┐
│                         HTTP Clients                               │
└──────────────────────┬─────────────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────────────┐
│                     FastAPI Application                            │
│                                                                    │
│  EXISTING ROUTERS              NEW ROUTER (v2.0)                   │
│  ┌────────────┐  ┌──────────┐  ┌────────────────────────────────┐  │
│  │  /books    │  │  /orders │  │  /books/{id}/reviews           │  │
│  │ (MODIFIED: │  │(existing)│  │  POST  — submit review         │  │
│  │  adds avg  │  │          │  │  GET   — list reviews for book │  │
│  │  rating to │  │          │  │  PUT   — user edits own review │  │
│  │  response) │  │          │  │  DELETE — user/admin deletes   │  │
│  └─────┬──────┘  └────┬─────┘  └──────────────┬─────────────────┘  │
│        │               │                      │                    │
│  ┌─────▼──────┐  ┌─────▼─────┐  ┌─────────────▼──────────────────┐ │
│  │ BookService│  │OrderService│  │       ReviewService (NEW)      │ │
│  │ (READ-ONLY │  │ (existing) │  │ - verified purchase check      │ │
│  │  queries   │  │            │  │ - one-per-user-per-book guard  │ │
│  │  for avg   │  │            │  │ - ownership check for edit/del │ │
│  │  rating)   │  │            │  │ - admin delete bypass          │ │
│  └─────┬──────┘  └────┬───────┘  └────────────────┬──────────────┘ │
│        │              │                           │                │
│   ┌────▼──────────────▼───────────────────────────▼──────────┐     │
│   │                  Repository Layer                         │     │
│   │  BookRepo      OrderRepo          ReviewRepo (NEW)        │     │
│   │  (existing)    (existing)         CRUD + agg queries      │     │
│   └────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────────────┐
│                  PostgreSQL (existing schema + 1 new table)        │
│                                                                    │
│  users (existing)     orders (existing)    reviews (NEW TABLE)     │
│  books (existing)     order_items          user_id FK → users      │
│                       (existing)           book_id FK → books      │
│                                            UNIQUE(user_id, book_id)│
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Status | Responsibility | File |
|-----------|--------|----------------|------|
| Review model | NEW | ORM table — user_id, book_id, rating, body, timestamps | app/reviews/models.py |
| ReviewRepository | NEW | CRUD + avg/count aggregate query per book | app/reviews/repository.py |
| ReviewService | NEW | Verified-purchase check, one-per-user guard, ownership check, admin bypass | app/reviews/service.py |
| Reviews router | NEW | POST/GET/PUT/DELETE /books/{id}/reviews; registered in main.py | app/reviews/router.py |
| Review schemas | NEW | ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse | app/reviews/schemas.py |
| Alembic migration | NEW | CREATE TABLE reviews with composite UNIQUE constraint | alembic/versions/ |
| OrderRepository | MODIFIED (read-only query added) | has_user_purchased_book(user_id, book_id) — EXISTS check against order_items | app/orders/repository.py |
| BookDetailResponse | MODIFIED (schema only) | Add avg_rating: float \| None and review_count: int fields | app/books/schemas.py |
| GET /books/{id} | MODIFIED (query augmented) | Join or subquery to compute avg_rating and review_count | app/books/router.py or repository.py |
| main.py | MODIFIED | include_router(reviews_router) | app/main.py |

---

## Recommended Project Structure (v2.0 additions only)

Additions and modifications to the existing tree — unchanged files omitted:

```
app/
├── reviews/                        # NEW module (standard 5-file pattern)
│   ├── __init__.py
│   ├── models.py                   # Review model + CheckConstraint(1 <= rating <= 5)
│   ├── schemas.py                  # ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse
│   ├── repository.py               # CRUD + get_avg_and_count(book_id) aggregate
│   ├── service.py                  # Business rules (purchase check, ownership, one-per-book)
│   └── router.py                   # /books/{book_id}/reviews endpoints
├── orders/
│   └── repository.py               # MODIFIED: add has_user_purchased_book()
├── books/
│   ├── schemas.py                  # MODIFIED: BookDetailResponse gains avg_rating + review_count
│   └── router.py                   # MODIFIED: GET /books/{id} fetches aggregate from ReviewRepo
└── main.py                         # MODIFIED: include reviews router
alembic/versions/
└── XXXXXXXX_create_reviews.py      # NEW migration: CREATE TABLE reviews
```

---

## FK Relationships and Database Schema

### New Table: `reviews`

```python
# app/reviews/models.py (NEW)
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_reviews_user_book"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
    )

    id:         Mapped[int]      = mapped_column(primary_key=True)
    user_id:    Mapped[int]      = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),  # delete reviews when user deleted
        nullable=False,
        index=True,
    )
    book_id:    Mapped[int]      = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),  # delete reviews when book deleted
        nullable=False,
        index=True,
    )
    rating:     Mapped[int]      = mapped_column(Integer, nullable=False)
    body:       Mapped[str|None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships for response serialization
    # book relationship NOT needed — reviews are always queried in book context
    # user relationship for reviewer name display (optional)
```

**FK decisions:**

| FK | ondelete | Rationale |
|----|----------|-----------|
| reviews.user_id → users.id | CASCADE | Reviews are meaningless without the user; same pattern as wishlist_items |
| reviews.book_id → books.id | CASCADE | Reviews are meaningless without the book; same pattern as wishlist_items |

**Constraint decisions:**

| Constraint | Implementation | Why |
|------------|---------------|-----|
| One review per user per book | `UniqueConstraint("user_id", "book_id")` | DB-enforced, no race condition risk; same as wishlist_items approach |
| Rating 1-5 | `CheckConstraint("rating >= 1 AND rating <= 5")` + Pydantic `Field(ge=1, le=5)` | DB as last line of defense; same dual-layer pattern as `ck_books_price_positive` |

---

## Verified Purchase Check

The "verified purchase required" rule is the key integration point with the orders domain.

### Query Pattern

```python
# app/orders/repository.py (MODIFIED — add one method)
async def has_user_purchased_book(self, user_id: int, book_id: int) -> bool:
    """Return True if user has at least one CONFIRMED order containing this book.

    Uses EXISTS subquery — stops scanning at first match, efficient even with
    large order history.
    """
    result = await self.session.execute(
        select(
            exists().where(
                Order.user_id == user_id,
                Order.status == OrderStatus.CONFIRMED,
                Order.id == OrderItem.order_id,
                OrderItem.book_id == book_id,
            )
        )
    )
    return bool(result.scalar())
```

### Where the Check Lives

The purchase check belongs in **ReviewService**, not ReviewRepository. Business rules live in service layer — this is the established pattern. The service is instantiated with both `ReviewRepository` and `OrderRepository`:

```python
# app/reviews/service.py (NEW)
class ReviewService:
    def __init__(
        self,
        review_repo: ReviewRepository,
        order_repo: OrderRepository,  # for verified purchase check
    ) -> None:
        self.review_repo = review_repo
        self.order_repo = order_repo

    async def create_review(self, user_id: int, book_id: int, data: ReviewCreate) -> Review:
        # 1. Verify book exists (could delegate to BookRepository or skip — FK will catch it)
        # 2. Check verified purchase
        purchased = await self.order_repo.has_user_purchased_book(user_id, book_id)
        if not purchased:
            raise AppError(403, "Must purchase book before reviewing", "REVIEW_NOT_PURCHASED")
        # 3. Check for existing review (unique constraint will also catch this, but give better error)
        existing = await self.review_repo.get_by_user_and_book(user_id, book_id)
        if existing:
            raise AppError(409, "You have already reviewed this book", "REVIEW_DUPLICATE")
        # 4. Create
        return await self.review_repo.create(user_id=user_id, book_id=book_id, **data.model_dump())
```

---

## Average Rating on Book Detail

### Integration Strategy

`GET /books/{id}` currently returns `BookDetailResponse` from `BookService._get_book_or_404()`. The avg_rating and review_count are computed from the reviews table — they are NOT stored on the books table.

**Two options:**

**Option A (recommended): Compute in router, pass to response schema**

```python
# app/books/router.py (MODIFIED)
@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: int, db: DbSession) -> BookDetailResponse:
    book_service = _make_service(db)
    review_repo = ReviewRepository(db)  # same session

    book = await book_service._get_book_or_404(book_id)
    avg_rating, review_count = await review_repo.get_avg_and_count(book_id)

    return BookDetailResponse(
        **BookDetailResponse.model_validate(book).model_dump(),
        avg_rating=avg_rating,
        review_count=review_count,
    )
```

**Option B: JOIN in BookRepository query**

Extend `BookRepository.get_by_id()` to LEFT JOIN with a subquery on reviews. Avoids the second round-trip but couples the books module to the reviews table.

**Choose Option A.** Coupling books to reviews via JOIN is a cross-domain dependency in the wrong direction — books shouldn't know about reviews. Option A keeps the books module clean and the second query is one lightweight aggregate (AVG + COUNT on an indexed FK column).

**Schema change:**

```python
# app/books/schemas.py (MODIFIED — BookDetailResponse only)
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
    avg_rating: float | None    # NEW — None when no reviews yet
    review_count: int           # NEW — 0 when no reviews yet

    @computed_field
    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    model_config = {"from_attributes": True}
```

**ReviewRepository aggregate query:**

```python
# app/reviews/repository.py (NEW)
async def get_avg_and_count(self, book_id: int) -> tuple[float | None, int]:
    """Return (avg_rating, count) for a book. avg_rating is None if no reviews."""
    result = await self.session.execute(
        select(
            func.avg(Review.rating).cast(Float),
            func.count(Review.id),
        ).where(Review.book_id == book_id)
    )
    avg, count = result.one()
    return avg, count or 0
```

---

## Architectural Patterns

### Pattern 1: Reviews as Self-contained Module with Cross-domain DI

**What:** The `reviews/` module follows the standard 5-file structure. Cross-domain concerns (purchase verification) are resolved at the service layer through constructor injection — `ReviewService` accepts `OrderRepository` alongside `ReviewRepository`. The router instantiates both repositories from the single shared session.

**When to use:** Any business rule that requires data from another domain's tables. Inject the other domain's *repository* (not service) to avoid circular imports. This is the same pattern used by `BookService` accepting `PreBookRepository` in v1.1.

**Why repository, not service:** Importing OrderService from ReviewService creates coupling at the wrong level and risks circular imports. The repository is the correct boundary for cross-domain reads.

**Example:**

```python
# app/reviews/router.py
from app.orders.repository import OrderRepository
from app.reviews.repository import ReviewRepository
from app.reviews.service import ReviewService

def _make_service(db: DbSession) -> ReviewService:
    return ReviewService(
        review_repo=ReviewRepository(db),
        order_repo=OrderRepository(db),  # injected for verified purchase check
    )
```

### Pattern 2: Ownership Check — User vs. Admin

**What:** Edit (PUT) and delete (DELETE) endpoints check ownership. Users can only modify their own review. Admins can delete any review. The check is in the service layer, not the router, so it is testable in isolation.

**Pattern:**

```python
# app/reviews/service.py
async def delete_review(self, review_id: int, actor_id: int, actor_role: str) -> None:
    review = await self.review_repo.get_by_id(review_id)
    if not review:
        raise AppError(404, "Review not found", "REVIEW_NOT_FOUND")
    if actor_role != "admin" and review.user_id != actor_id:
        raise AppError(403, "Cannot delete another user's review", "REVIEW_FORBIDDEN")
    await self.review_repo.delete(review)

async def update_review(self, review_id: int, user_id: int, data: ReviewUpdate) -> Review:
    review = await self.review_repo.get_by_id(review_id)
    if not review:
        raise AppError(404, "Review not found", "REVIEW_NOT_FOUND")
    if review.user_id != user_id:
        raise AppError(403, "Cannot edit another user's review", "REVIEW_FORBIDDEN")
    return await self.review_repo.update(review, **data.model_dump(exclude_unset=True))
```

**Router dependency: use `ActiveUser`, not `AdminUser`**, for delete — both users and admins call the same endpoint; the service handles authorization:

```python
# app/reviews/router.py
@router.delete("/books/{book_id}/reviews/{review_id}", status_code=204)
async def delete_review(
    book_id: int,
    review_id: int,
    db: DbSession,
    current_user: ActiveUser,  # not AdminUser — service handles the role check
) -> None:
    svc = _make_service(db)
    await svc.delete_review(
        review_id=review_id,
        actor_id=int(current_user["sub"]),
        actor_role=current_user.get("role", "user"),
    )
```

### Pattern 3: Aggregate Computed at Read Time, Not Stored

**What:** `avg_rating` and `review_count` are computed via `AVG()` / `COUNT()` on the reviews table at request time. They are NOT stored as denormalized columns on the books table.

**When to use:** Correctness is the priority. Storing aggregates requires cache invalidation on every review create/edit/delete — a source of bugs. At this scale, a single aggregate query per book detail view is fast (indexed FK scan).

**Trade-off:** If book list view (GET /books) also needs avg_rating per book, this becomes N aggregate queries. For list view, compute all aggregates in one query using a subquery or GROUP BY, not per-book calls. For v2.0, only book detail requires the aggregate.

---

## Data Flow

### Submit Review Flow

```
POST /books/{book_id}/reviews  { rating: 5, body: "Great book" }
    │  ActiveUser dependency: JWT decoded + DB is_active check
    │
    ▼
reviews/router.py
    user_id = int(current_user["sub"])
    svc = ReviewService(ReviewRepository(db), OrderRepository(db))
    │
    ▼
ReviewService.create_review(user_id, book_id, data)
    1. OrderRepository.has_user_purchased_book(user_id, book_id)
       → EXISTS query on orders JOIN order_items WHERE confirmed + book_id
       → False → raise AppError(403, REVIEW_NOT_PURCHASED)
    2. ReviewRepository.get_by_user_and_book(user_id, book_id)
       → exists → raise AppError(409, REVIEW_DUPLICATE)
    3. ReviewRepository.create(user_id, book_id, rating, body)
       → INSERT reviews; flush()
    │
    ▼
return ReviewResponse (201 Created)
    │
    ▼ (get_db commits session)
```

### Get Book Detail with Ratings Flow

```
GET /books/{book_id}
    │  No auth required (public)
    │
    ▼
books/router.py
    book_service = BookService(BookRepository(db), GenreRepository(db))
    review_repo = ReviewRepository(db)  # same session, zero overhead
    │
    ▼
BookService._get_book_or_404(book_id)
    → SELECT * FROM books WHERE id = ?
    → 404 if not found
    │
    ▼
ReviewRepository.get_avg_and_count(book_id)
    → SELECT AVG(rating)::float, COUNT(id) FROM reviews WHERE book_id = ?
    → (None, 0) if no reviews yet
    │
    ▼
return BookDetailResponse(
    ...book fields...,
    avg_rating=avg,       # float or None
    review_count=count,   # int
)
```

### Edit/Delete Review Flow

```
PUT /books/{book_id}/reviews/{review_id}   { rating: 4 }
    │  ActiveUser dependency
    │
    ▼
reviews/router.py
    user_id = int(current_user["sub"])
    svc = ReviewService(ReviewRepository(db), OrderRepository(db))
    │
    ▼
ReviewService.update_review(review_id, user_id, data)
    1. ReviewRepository.get_by_id(review_id) → 404 if missing
    2. review.user_id != user_id → raise AppError(403, REVIEW_FORBIDDEN)
    3. ReviewRepository.update(review, rating=4) → flush()
    │
    ▼
return ReviewResponse (200 OK)

DELETE /books/{book_id}/reviews/{review_id}
    │  ActiveUser dependency (user OR admin)
    │
    ▼
ReviewService.delete_review(review_id, actor_id, actor_role)
    1. ReviewRepository.get_by_id(review_id) → 404 if missing
    2. actor_role != "admin" AND review.user_id != actor_id → raise AppError(403)
    3. ReviewRepository.delete(review) → flush()
    │
    ▼
return 204 No Content
```

### List Reviews for Book Flow

```
GET /books/{book_id}/reviews?page=1&size=20
    │  No auth required (public)
    │
    ▼
ReviewRepository.list_for_book(book_id, page, size)
    → SELECT * FROM reviews WHERE book_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?
    → SELECT COUNT(*) ... (same filter)
    │
    ▼
return ReviewListResponse(items=[...], total=N, page=1, size=20)
```

---

## Integration Points: New vs Modified

### New (net-new files, no existing files touched)

| What | File | Notes |
|------|------|-------|
| Review model | app/reviews/models.py | UniqueConstraint(user_id, book_id); CheckConstraint rating 1-5; CASCADE on both FKs |
| Review schemas | app/reviews/schemas.py | ReviewCreate (rating, body), ReviewUpdate (rating?, body?), ReviewResponse, ReviewListResponse |
| ReviewRepository | app/reviews/repository.py | CRUD + get_avg_and_count() + get_by_user_and_book() + list_for_book() |
| ReviewService | app/reviews/service.py | create (purchase check, dup check), update (ownership), delete (ownership+admin), list |
| Reviews router | app/reviews/router.py | POST/GET/PUT/DELETE /books/{book_id}/reviews/{review_id} |
| Alembic migration | alembic/versions/XXXX_create_reviews.py | CREATE TABLE reviews; UniqueConstraint; CheckConstraint; indexes on user_id, book_id |

### Modified (existing files extended — minimal, targeted changes)

| What | File | Exact Change |
|------|------|-------------|
| OrderRepository | app/orders/repository.py | Add `has_user_purchased_book(user_id, book_id) -> bool` — one new method, zero existing code changed |
| BookDetailResponse | app/books/schemas.py | Add `avg_rating: float \| None` and `review_count: int` fields to existing schema class |
| GET /books/{book_id} | app/books/router.py | Instantiate ReviewRepository(db); call get_avg_and_count(); pass to BookDetailResponse constructor |
| main.py | app/main.py | `from app.reviews.router import router as reviews_router` + `application.include_router(reviews_router)` |

### What is NOT Modified

| Module | Why untouched |
|--------|---------------|
| app/users/ | No user model changes needed; user_id FK uses existing users.id |
| app/cart/ | Reviews have no cart interaction |
| app/orders/service.py | Purchase check is a read-only query; service layer not touched |
| app/orders/models.py | No schema changes to orders |
| app/orders/router.py | No endpoint changes to orders |
| app/books/service.py | Business logic for books unchanged; only router and schema touch ratings |
| app/books/repository.py | BookRepository untouched; aggregate lives in ReviewRepository |
| app/prebooks/ | No interaction with reviews |
| app/admin/ | Admin delete goes through reviews router with role check in service |
| app/email/ | No email notifications for reviews in v2.0 |

---

## Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| reviews ↔ orders | ReviewService accepts OrderRepository for purchase check | Read-only cross-domain query; inject repository not service (avoids circular imports) |
| reviews ↔ books | books/router.py instantiates ReviewRepository(db) for aggregate | One-way: books reads from reviews; reviews never imports from books |
| reviews ↔ users | FK only; no runtime import between modules | CASCADE delete handled at DB level |
| admin ↔ reviews | Role check in ReviewService.delete_review() using `actor_role` string | No admin module import in reviews; role propagated from JWT claims |

---

## Build Order for v2.0

Dependencies run: DB schema → repository → service → router → integration.

```
Phase 1: Data layer (foundation)
  app/reviews/models.py          — Review model, constraints, relationships
  alembic/versions/XXXX.py       — CREATE TABLE reviews migration
  app/reviews/repository.py      — CRUD + get_avg_and_count + list_for_book
  app/orders/repository.py       — Add has_user_purchased_book() method
  Test: unit test repository methods with test DB

Phase 2: Service + router (core feature)
  app/reviews/schemas.py         — ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse
  app/reviews/service.py         — create (purchase check, dup), update (ownership), delete (ownership+admin), list
  app/reviews/router.py          — all endpoints; registered in main.py
  app/main.py                    — include reviews_router
  Test: POST submit, GET list, PUT edit, DELETE (user + admin)

Phase 3: Book detail integration (aggregate surface)
  app/books/schemas.py           — Add avg_rating, review_count to BookDetailResponse
  app/books/router.py            — GET /books/{id} fetches aggregate from ReviewRepository
  Test: GET /books/{id} returns correct avg_rating and review_count; 0/None when no reviews
```

**Rationale for this order:**
- Phase 1 first: service and router depend on repository; repository depends on schema. Migration must run before any query. OrderRepository method added here because ReviewService depends on it.
- Phase 2 before Phase 3: the review CRUD is the core feature; book detail integration is a read-only extension that depends on review data existing.
- Phase 3 last: isolated change to two files; can be shipped independently of review submission.

---

## Anti-Patterns

### Anti-Pattern 1: Storing avg_rating on the books Table

**What people do:** Add `avg_rating` and `review_count` columns to the books table, then update them on every review create/edit/delete.

**Why it's wrong:** Creates a cache-invalidation problem. Any review mutation must atomically update the books table — adding complexity to every write path. If any update is missed (bug, rollback), the aggregate drifts and is silently wrong.

**Do this instead:** Compute AVG() and COUNT() from the reviews table at read time. It is fast: the query touches only rows matching `book_id` (indexed FK). The computed value is always correct.

### Anti-Pattern 2: Importing OrderService into ReviewService

**What people do:** `from app.orders.service import OrderService` inside ReviewService to call order lookup logic.

**Why it's wrong:** OrderService imports OrderRepository which imports models from cart, books. If ReviewService imports OrderService, and some other module imports both, circular import risk grows. More fundamentally, ReviewService only needs one read-only query — it does not need the full OrderService orchestration.

**Do this instead:** Inject `OrderRepository` directly. ReviewService calls `order_repo.has_user_purchased_book()`. This is a targeted, read-only, cross-domain repository call — the same pattern used by BookService accepting PreBookRepository in v1.1.

### Anti-Pattern 3: Putting the Ownership Check in the Router

**What people do:** Check `review.user_id == current_user["sub"]` in the route function before calling the service.

**Why it's wrong:** Business rules belong in the service layer. Putting authorization logic in the router bypasses the unit-testable layer and can be accidentally omitted in future endpoints or test scenarios.

**Do this instead:** Pass `actor_id` and `actor_role` to `ReviewService.delete_review()`. The service raises `AppError(403, REVIEW_FORBIDDEN)`. The router only extracts the actor identity from the JWT and delegates.

### Anti-Pattern 4: Using a Separate Admin Endpoint for Review Deletion

**What people do:** Create `DELETE /admin/reviews/{id}` gated by `AdminUser` dependency.

**Why it's wrong:** Splits the same operation across two routes, duplicating handler code. Admin delete is the same operation as user delete with a role bypass — the service handles this with one if-branch.

**Do this instead:** Single `DELETE /books/{book_id}/reviews/{review_id}` endpoint with `ActiveUser` dependency. Service checks `actor_role == "admin"` to bypass ownership requirement. Admin can reach it; user can reach it; the service enforces the difference.

### Anti-Pattern 5: Duplicate Review Check Only at the Service Layer (No DB Constraint)

**What people do:** Skip the `UniqueConstraint("user_id", "book_id")` on the reviews table, relying on the `get_by_user_and_book()` pre-check in the service.

**Why it's wrong:** Under concurrent requests, two simultaneous POST /reviews from the same user for the same book can both pass the pre-check before either commits. Without the DB constraint, both inserts succeed, violating the one-review rule.

**Do this instead:** Always have both: the service pre-check gives a clean `REVIEW_DUPLICATE` error message; the DB UniqueConstraint is the race-condition-safe last line of defense. This is the same dual-layer pattern used for wishlist_items.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Current approach (compute on read) is fine. AVG/COUNT on small table is negligible. |
| 1k-100k users | If GET /books is called heavily, add a materialized view or periodic aggregate refresh for book list views. Book detail (one book) is still fine on read. |
| 100k+ users | Denormalize avg_rating onto books table — accept the cache invalidation complexity at that scale. Or use a read replica with a precomputed analytics table. |

**First bottleneck for v2.0:** None. The aggregate query is one indexed GROUP BY. Reviews will not be the bottleneck before checkout and FTS search become bottlenecks first.

---

## Sources

- Existing codebase inspection — app/books/models.py, schemas.py, router.py, service.py, repository.py; app/orders/models.py, repository.py, service.py; app/wishlist/models.py; app/prebooks/models.py; app/users/models.py; app/core/deps.py, exceptions.py; app/main.py — HIGH confidence (direct source)
- SQLAlchemy 2.0 docs — UniqueConstraint, CheckConstraint, mapped_column: https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html — HIGH confidence
- SQLAlchemy 2.0 docs — EXISTS subquery: https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.exists — HIGH confidence
- FastAPI docs — Dependency Injection: https://fastapi.tiangolo.com/tutorial/dependencies/ — HIGH confidence
- Previous ARCHITECTURE.md research (v1.1) — patterns confirmed as implemented and working — HIGH confidence

---

*Architecture research for: BookStore API v2.0 — Reviews & Ratings*
*Researched: 2026-02-26*
