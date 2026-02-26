# Pitfalls Research

**Domain:** FastAPI bookstore v2.0 — adding reviews & ratings to existing system with JWT auth, order history, and async SQLAlchemy
**Researched:** 2026-02-26
**Confidence:** HIGH (codebase verified against existing models, verified against official SQLAlchemy/FastAPI docs, multiple community sources)

> This file covers pitfalls specific to adding reviews & ratings (v2.0 milestone) to a system that already has: JWT auth with `ActiveUser`/`AdminUser` deps, `OrderItem` model with `book_id SET NULL on delete`, `Book` model with no review relationship yet, `BookDetailResponse` schema without aggregates, 179 passing tests, and SELECT FOR UPDATE stock locking. Pitfalls are ordered by severity and probability of occurrence.

---

## Critical Pitfalls

### Pitfall 1: Verified-Purchase Check Uses Wrong Query — Users Can Review Books They Never Bought

**What goes wrong:**
The "verified purchase" gate is implemented by checking `orders` rather than `order_items`. A query like `SELECT * FROM orders WHERE user_id = :uid AND book_id = :bid` fails because `orders` has no `book_id` column — only `order_items` does. Alternatively, the check queries `order_items` correctly, but does not filter `WHERE orders.status = 'confirmed'` — meaning a user whose order has `status = 'payment_failed'` passes the verified-purchase check and can leave a review.

**Why it happens:**
Developers look at `Order` first (it has `user_id`) and add a `book_id` filter assuming it's on the parent row. The `OrderItem` model has `book_id` as `SET NULL` nullable — so `WHERE order_items.book_id = :bid` silently excludes rows where the book was deleted, which is correct, but developers may not join to `orders` to filter by status, leaving `payment_failed` orders as valid purchase evidence.

Looking at the actual models in this codebase:
- `Order` has: `id`, `user_id`, `status` (`confirmed` | `payment_failed`), `created_at`
- `OrderItem` has: `order_id`, `book_id` (nullable SET NULL), `quantity`, `unit_price`

The correct check is a JOIN across both tables filtering status:
```python
# CORRECT verified-purchase query
result = await session.execute(
    select(OrderItem)
    .join(Order, OrderItem.order_id == Order.id)
    .where(
        Order.user_id == user_id,
        Order.status == OrderStatus.CONFIRMED,
        OrderItem.book_id == book_id,
    )
    .limit(1)
)
has_purchased = result.scalar_one_or_none() is not None
```

**How to avoid:**
Always join `order_items → orders` and filter `orders.status = 'confirmed'`. Import `OrderStatus.CONFIRMED` from `app.orders.models` — do not hardcode the string `"confirmed"`. Add a test that verifies a user with only `payment_failed` orders cannot post a review.

**Warning signs:**
- Verified-purchase check only queries `orders` table with no join
- Check passes for users whose order has `status = 'payment_failed'`
- No test that creates a `payment_failed` order and asserts the user is denied

**Phase to address:** Review creation phase (first phase). The `can_review` gate must be correct before any other review logic is built. Wrong gate = wrong foundation for all downstream tests.

---

### Pitfall 2: Race Condition on Duplicate Review Submission — Application-Level Check Is Not Enough

**What goes wrong:**
The "one review per user per book" constraint is enforced by an application-level existence check: `SELECT * FROM reviews WHERE user_id = :uid AND book_id = :bid` followed by `INSERT`. Under concurrent requests (browser double-click, client retry), two requests both pass the SELECT check simultaneously and both proceed to INSERT, creating two reviews for the same user-book pair. The application now has inconsistent state — one user has two reviews, the average rating calculation is wrong, and future edit/delete operations behave unpredictably.

**Why it happens:**
Developers trust the application-level check because it "always worked in tests." Tests are sequential; two concurrent requests expose the TOCTOU (time-of-check, time-of-use) window. Without a database-level UNIQUE constraint, no enforcement exists between the SELECT and INSERT.

**How to avoid:**
Two layers are required — the database constraint is mandatory, the application check is optional:

1. **Database level (mandatory):** Add a UNIQUE constraint on `(user_id, book_id)` in the Alembic migration for the `reviews` table. This is the actual enforcement mechanism.

2. **Application level (graceful UX):** Catch `sqlalchemy.exc.IntegrityError` with `asyncpg.exceptions.UniqueViolationError` as the cause and convert it to a clean 409 response — do NOT let it bubble as a 500:

```python
from sqlalchemy.exc import IntegrityError
from asyncpg.exceptions import UniqueViolationError

try:
    session.add(review)
    await session.flush()
except IntegrityError as exc:
    if isinstance(exc.orig, UniqueViolationError):
        raise AppError(409, "You have already reviewed this book", "REVIEW_DUPLICATE")
    raise
```

**Warning signs:**
- No `UniqueConstraint("user_id", "book_id")` in the `reviews` Alembic migration
- The existence check is a SELECT followed by INSERT with no IntegrityError handler
- Test suite has no concurrent-submission test (acceptable at this scale) but also no test that submits twice and expects 409 on the second

**Phase to address:** Review model/migration phase (first phase). The unique constraint must be in the migration, not added later. Adding it later requires a data migration to remove any existing duplicates first.

---

### Pitfall 3: Average Rating Is Computed Live on Every Book Detail Request — No Index, Full Scan

**What goes wrong:**
`GET /books/{book_id}` currently returns `BookDetailResponse` with no rating fields. Adding `average_rating` and `review_count` as live-computed aggregates via a subquery on every call is correct for data freshness, but without an index on `reviews(book_id)`, every book detail request does a full table scan of the `reviews` table. At 1k reviews this is unnoticed; at 10k reviews it adds 50-200ms per request.

**Why it happens:**
The aggregate is added as a subquery in the book detail query or as a Python-side `COUNT`/`AVG` call. No index is added because the migration "just adds the table" and the developer assumes PostgreSQL will handle it.

**How to avoid:**
Add a composite index on `(book_id)` at minimum — `(book_id, rating)` is even better since `AVG(rating)` reads the `rating` column:

```python
# In the reviews Alembic migration:
Index("ix_reviews_book_id", "book_id")
# Or composite for covering index:
Index("ix_reviews_book_id_rating", "book_id", "rating")
```

For this project's scale (bookstore, not Amazon), live-computed aggregates via a single indexed query are fine. Do NOT add denormalized `average_rating`/`review_count` columns to the `books` table for v2.0 — the synchronization complexity (trigger or application-level update on every review insert/update/delete) creates more pitfalls than it solves. Compute live with an index.

The correct query pattern for live aggregates:
```python
from sqlalchemy import func, select

result = await session.execute(
    select(
        func.avg(Review.rating).label("average_rating"),
        func.count(Review.id).label("review_count"),
    ).where(Review.book_id == book_id)
)
row = result.one()
avg = float(row.average_rating) if row.average_rating else None
count = row.review_count
```

**Warning signs:**
- No `Index` on `reviews.book_id` in the migration
- `BookDetailResponse` aggregates are computed in Python after loading all reviews into memory via `selectinload`
- EXPLAIN ANALYZE on book detail shows `Seq Scan` on `reviews` table

**Phase to address:** Review model/migration phase. Index must be in the initial migration alongside the table creation.

---

### Pitfall 4: Book Deletion Silences Reviews — SET NULL on book_id Creates Phantom Aggregate Data

**What goes wrong:**
The existing `OrderItem.book_id` uses `ondelete="SET NULL"` to preserve order history when a book is deleted. If `Review.book_id` also uses `SET NULL`, deleted-book reviews persist in the table with `book_id = NULL`. The aggregate query `WHERE book_id = :bid` correctly excludes these (NULL != any value), so ratings for the deleted book are silently dropped. But a different query — `WHERE book_id IS NULL` — could accidentally aggregate all orphaned reviews together, producing meaningless data.

More critically: if `Review.book_id` uses `CASCADE DELETE`, all reviews are deleted when a book is deleted. This is the correct behavior for reviews (unlike orders, reviews have no independent value if the book no longer exists). But developers may copy the `OrderItem` FK pattern and use `SET NULL` without thinking through the review lifecycle.

**Why it happens:**
The existing codebase pattern for `book_id` FKs uses `SET NULL` (correct for order history). Developers copy this pattern without evaluating whether reviews have the same "preserve history" requirement.

**How to avoid:**
Use `ondelete="CASCADE"` on `Review.book_id`, NOT `SET NULL`. Reviews without a book are meaningless — cascade delete is correct:

```python
class Review(Base):
    __tablename__ = "reviews"

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),  # CASCADE, not SET NULL
        nullable=False,
        index=True,
    )
```

If admin deletes a book, its reviews should disappear with it. Document this decision explicitly — it differs from `OrderItem` intentionally.

**Warning signs:**
- `Review.book_id` FK uses `ondelete="SET NULL"` (copied from OrderItem pattern)
- `book_id` column on `Review` model is `Mapped[int | None]` (nullable) — signals SET NULL intention
- No test that deletes a book and verifies its reviews are also deleted

**Phase to address:** Review model/migration phase. FK behavior is a schema decision — cannot be changed without a migration after the fact.

---

### Pitfall 5: Admin Delete Uses Wrong Auth Dependency — Non-Admins Can Delete Any Review

**What goes wrong:**
The admin "delete any review" endpoint is decorated with `ActiveUser` instead of `AdminUser`, or the route handler checks `current_user.get("role") == "admin"` inline without using the existing `require_admin` dependency chain. The inline check is missed in a refactor, or the wrong dependency type alias is imported. Non-authenticated users or regular users can delete any review.

**Why it happens:**
The project has three auth dependency aliases: `CurrentUser` (JWT decode only, no DB check), `ActiveUser` (JWT + is_active DB check), and `AdminUser` (JWT + is_active + role check). Developers building review endpoints use `ActiveUser` for user-facing endpoints and forget to switch to `AdminUser` for the admin delete endpoint. The routes work in tests if tests authenticate as admin — the wrong dependency passes because the test user is active.

Looking at `app/core/deps.py`:
- `CurrentUser` = JWT decode only (no DB check) — wrong for any protected endpoint
- `ActiveUser` = JWT + is_active DB check — correct for user-facing review endpoints
- `AdminUser` = JWT + is_active + admin role check — required for admin review delete

**How to avoid:**
Use `AdminUser` on the admin delete endpoint. Never use `CurrentUser` for any endpoint that modifies data. The pattern from existing admin endpoints in `app/books/router.py` is correct — follow it exactly:

```python
# CORRECT — matches the pattern in books/router.py
@router.delete("/admin/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_review(
    review_id: int,
    db: DbSession,
    admin: AdminUser,  # AdminUser, not ActiveUser
) -> None:
    ...
```

**Warning signs:**
- Admin delete endpoint imports `ActiveUser` instead of `AdminUser`
- Test for admin delete passes when called with a regular user token
- No test that calls admin delete with a regular-user JWT and asserts 403

**Phase to address:** Review admin moderation phase. Auth dependency must be correct on initial implementation — auth bugs discovered late require re-examining all existing tests.

---

### Pitfall 6: BookDetailResponse Schema Not Updated — Average Rating Fields Missing From Response

**What goes wrong:**
`GET /books/{book_id}` uses `BookDetailResponse` in `app/books/schemas.py`. This schema is validated with `model_config = {"from_attributes": True}` and validated via `BookDetailResponse.model_validate(book)`. Adding `average_rating` and `review_count` fields to the response requires either: (a) adding them to the `Book` ORM model (wrong — these are aggregates, not stored columns), or (b) adding them to the schema with data passed separately. Developers add the fields to the schema but forget to pass the computed values, resulting in `None` / `0` being returned silently because the Pydantic model defaults them.

**Why it happens:**
The existing pattern is `BookDetailResponse.model_validate(book)` — the ORM object is passed directly. For computed aggregates (not stored on the book row), `model_validate(book)` will not have the values. Pydantic defaults kick in silently: `average_rating: float | None = None` defaults to `None` without error.

**How to avoid:**
Do not extend `model_validate(book)` for aggregate fields. Instead, pass aggregates explicitly:

```python
# In the router — fetch book and aggregates separately
book = await service.get_book_or_404(book_id)
avg_rating, review_count = await review_repo.get_aggregates(book_id)

return BookDetailResponse(
    **BookDetailResponse.model_validate(book).model_dump(),
    average_rating=avg_rating,
    review_count=review_count,
)
```

Or use a factory method pattern on the schema that accepts both the ORM object and computed fields. Either way, never rely on `model_validate(orm_object)` to populate fields that are not ORM attributes.

**Warning signs:**
- `BookDetailResponse` has `average_rating: float | None = None` with a default
- The router still calls `BookDetailResponse.model_validate(book)` after adding aggregate fields
- `GET /books/{book_id}` always returns `"average_rating": null` and `"review_count": 0`
- No test asserts non-null values for `average_rating` after reviews are created

**Phase to address:** Book detail aggregate phase. The schema change and the data-passing pattern must be implemented together — not separately by different commits.

---

### Pitfall 7: Review Model Missing From Central Registry — Test Suite Creates Schema Without reviews Table

**What goes wrong:**
The new `Review` model is created in `app/reviews/models.py` but is not imported in `app/db/base.py`. The test suite's `conftest.py` imports `Base` from `app/db/base` and calls `create_all`. The `reviews` table is absent from `Base.metadata`. All review tests fail with `asyncpg.exceptions.UndefinedTableError: relation "reviews" does not exist`. Worse: the error may not appear immediately — it appears when the first test that inserts a review runs, potentially mid-suite, confusing the failure location.

**Why it happens:**
This is the same pitfall as v1.1 Pitfall 6 (pre-booking model). It recurs with every new model. The `app/db/base.py` central registry is easy to forget, especially when a new `app/reviews/` module is created from scratch.

Current registry in `app/db/base.py` must be extended. After adding the Review model:
```python
# app/db/base.py — ADD THIS LINE:
from app.reviews.models import Review  # noqa: F401
```

**How to avoid:**
Treat updating `app/db/base.py` as step 1 of model creation, not step 3. The first thing after creating `app/reviews/models.py` is adding the import to `app/db/base.py`. Immediately run `pytest tests/test_health.py` — if it passes, the schema was created correctly. If it fails with `UndefinedTableError`, the import is missing.

**Warning signs:**
- `app/reviews/models.py` exists but `app/db/base.py` has no import from it
- `alembic revision --autogenerate -m "add reviews"` produces an empty migration (model not in metadata)
- `pytest tests/test_health.py` passes but `pytest tests/reviews/` fails with `UndefinedTableError`

**Phase to address:** Review model/migration phase (first phase). This must be the first step — before writing any service or router code.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Storing `average_rating` / `review_count` on `books` table | Faster reads (no aggregation query) | Must update on every review insert/edit/delete; if update fails, data is stale forever; adds complexity to 4 endpoints | Never for v2.0 — live aggregate with index is simpler and correct at this scale |
| Application-level duplicate check only (no UNIQUE constraint) | Simpler migration | Race condition allows duplicate reviews under concurrent requests; data corruption is silent | Never — always pair with DB constraint |
| Using `SET NULL` on `Review.book_id` (copied from OrderItem pattern) | Consistent with existing FK pattern | Orphaned reviews with `NULL book_id` pollute aggregate queries; reviews without books are meaningless | Never — use CASCADE for reviews |
| Allowing review text as empty string (not NULL) | Simpler validation | Inconsistent empty-vs-null states; harder to query "reviews with text" | Acceptable only if you never need to distinguish "no text provided" from "user explicitly submitted empty" |
| Verified-purchase check inside the route handler (not service layer) | Faster to implement | Authorization logic scattered across handlers; difficult to test in isolation | Acceptable for MVP if placed in a dedicated `_assert_can_review()` helper; not acceptable if duplicated across multiple endpoints |
| No pagination on review list endpoint | Simpler implementation | Books with 500+ reviews return entire list as JSON; slow client parsing | Acceptable only if total review count per book is proven to stay under ~50; add pagination from day one otherwise |
| Including `user_id` in review creation request body | Allows flexibility | Users can impersonate other users by passing any `user_id`; must always derive `user_id` from JWT token, not request body | Never — `user_id` must always come from `current_user["sub"]` |

---

## Integration Gotchas

Common mistakes when connecting the new review system to existing components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Verified purchase check | Querying `orders.book_id` (column does not exist) | Join `order_items` to `orders`: `WHERE order_items.book_id = :bid AND orders.user_id = :uid AND orders.status = 'confirmed'` |
| Verified purchase check | Not filtering by `orders.status = 'confirmed'` | Import and use `OrderStatus.CONFIRMED` from `app.orders.models` — not the hardcoded string |
| BookDetailResponse | Passing ORM `Book` object to `model_validate()` for aggregate fields | Fetch aggregates separately; construct response with explicit keyword arguments alongside `model_validate(book)` |
| Auth dependency on admin delete | Using `ActiveUser` instead of `AdminUser` | Use `AdminUser` alias from `app.core.deps` — matches the pattern in `app/books/router.py` |
| FK delete behavior | Copying `ondelete="SET NULL"` from `OrderItem.book_id` | Reviews use `ondelete="CASCADE"` — review without a book has no meaning (unlike order history) |
| User identity in review create | Accepting `user_id` from request body | Always extract `user_id` from `int(current_user["sub"])` using `ActiveUser` dependency |
| New model registration | Creating `app/reviews/models.py` without updating `app/db/base.py` | Add `from app.reviews.models import Review  # noqa: F401` to `app/db/base.py` immediately |
| UNIQUE constraint handling | Letting `IntegrityError` bubble as HTTP 500 | Catch `IntegrityError`, check `exc.orig` is `UniqueViolationError`, raise `AppError(409, ...)` |
| Existing 179 tests | New Review model breaks schema creation for existing tests | After adding model import to `app/db/base.py`, run full test suite — not just review tests |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No index on `reviews(book_id)` | Book detail response slows with review count; EXPLAIN shows Seq Scan | Add `Index("ix_reviews_book_id", "book_id")` in migration | At ~1k review rows (noticeable) / ~10k rows (problematic) |
| Loading all reviews via `selectinload` to compute average in Python | High memory use; slow serialization on books with many reviews | Use `func.avg()` and `func.count()` SQL aggregates; never load all Review ORM objects to compute stats | At ~100 reviews per book |
| No pagination on review list | Large JSON response for popular books; slow client parsing | Add `page`/`size` pagination from day one (same pattern as `GET /books`) | At ~50 reviews per book visible in API response |
| Aggregate computed per-request without index | Every `GET /books/{book_id}` triggers full scan of reviews table | Index on `(book_id)` makes this a fast index scan; covering index `(book_id, rating)` eliminates heap fetch | At ~5k total review rows across all books |
| Recalculating aggregates via UPDATE on `books` table | Complex update logic; write amplification on every review action | Compute live from indexed reviews table — simpler, correct, no synchronization needed at this scale | N/A — avoid this pattern entirely for v2.0 |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| `user_id` accepted from request body in review create | User can submit review as any user_id (impersonation) | Always derive `user_id = int(current_user["sub"])` from the `ActiveUser` JWT dependency; never from request body |
| Review text not length-limited | Abusive/spam reviews with multi-MB text content; DB column size unbounded | Enforce `max_length` in Pydantic schema (e.g., 5000 chars) AND column size in DB (`Text` is fine but Pydantic validation is the gate) |
| Admin delete endpoint uses `ActiveUser` instead of `AdminUser` | Any authenticated user can delete any review by calling admin endpoint | Use `AdminUser` dependency; add test asserting regular user gets 403 on admin delete |
| User can delete other users' reviews via `DELETE /reviews/{id}` | Horizontal privilege escalation | Repository query must filter `WHERE id = :review_id AND user_id = :user_id`; return 404 (not 403) if not found to avoid ID enumeration |
| Verified-purchase check bypassed by submitting review for `book_id` of a book in a failed order | Unverified reviews inflate ratings | Filter `orders.status = 'confirmed'` in the purchase verification query — not just `orders.user_id = :uid` |
| Exposing reviewer's full name or email in review response | PII disclosure | Only include `user_id` or a display name in review response; never email address or hashed password |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No `average_rating` / `review_count` on book list (`GET /books`) | Catalog browsing shows no ratings; users must open each book to see rating | Add aggregates to `GET /books` response as well, not just `GET /books/{book_id}` (requires efficient subquery or JOIN) |
| Review edit silently ignores fields not provided | User sends `{"rating": 5}` expecting to keep existing text; text is reset to null | Use explicit partial update: only update fields present in the request body; treat omitted fields as "keep existing" |
| `404` returned when user tries to review a book they own but it was deleted | Confusing — user is certain they bought it | If book was deleted (`book_id SET NULL` on order_items), the purchase verification JOIN on `book_id IS NOT NULL` also fails; return a clear error explaining the book is no longer available |
| No indication whether authenticated user has already reviewed a book | User revisits book page and cannot tell if they already reviewed it | Include `user_review: ReviewResponse | null` in `GET /books/{book_id}` response for authenticated users (requires auth-conditional logic in the endpoint) |
| Review created successfully but returns 200 instead of 201 | Minor but inconsistent with REST conventions and existing endpoints | Return 201 on POST `/reviews`; existing `POST /books` uses `status.HTTP_201_CREATED` — follow same pattern |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Review creation:** POST returns 201 — verify `UNIQUE (user_id, book_id)` constraint exists in migration; submit same review twice and confirm 409, not 500
- [ ] **Verified purchase gate:** Review creation succeeds for confirmed-order user — verify user with only `payment_failed` order gets 422/403; verify user with no orders at all gets 403
- [ ] **Average rating on book detail:** `GET /books/{id}` returns `average_rating` — verify value is `null` (not `0.0`) when no reviews exist; verify it updates correctly after a review is added
- [ ] **Review count:** `review_count` is correct — verify it decrements when a review is deleted (user or admin delete); verify it does not double-count on review edit
- [ ] **User review delete:** DELETE succeeds for own review — verify 404 (not 403) when trying to delete another user's review; verify aggregate on book updates after delete
- [ ] **Admin review delete:** DELETE `/admin/reviews/{id}` works for admin — verify regular user JWT gets 403; verify `review_count` on book updates after admin delete
- [ ] **Review edit:** PATCH updates review — verify only provided fields are updated; verify `updated_at` timestamp changes; verify user cannot edit another user's review
- [ ] **Book deletion cascade:** Admin deletes book — verify all reviews for that book are also deleted; verify no `NULL book_id` review rows remain in `reviews` table
- [ ] **Model registry:** New `Review` model added — verify `alembic revision --autogenerate` produces a non-empty migration; run `pytest tests/test_health.py` immediately after adding model to `app/db/base.py`
- [ ] **Full regression:** 179 existing tests still pass after new schema — run full suite before marking any review phase complete; failure in a non-review test signals missing import in registry

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Duplicate reviews exist (no UNIQUE constraint shipped) | MEDIUM | Audit `reviews` for `(user_id, book_id)` duplicates; keep most recent per pair, delete others; add UNIQUE constraint via new Alembic migration with `CREATE UNIQUE INDEX CONCURRENTLY` to avoid table lock |
| Unverified reviews accepted (payment_failed orders allowed) | MEDIUM | Audit `reviews` table: join to `orders`/`order_items` and flag reviews where no confirmed order exists; notify affected users; add status filter to verification query |
| Average rating wrong (SET NULL left orphaned reviews) | LOW | Identify reviews with `book_id IS NULL`; delete them (they have no associated book); change FK to CASCADE in new migration |
| Admin delete endpoint was `ActiveUser` in production | HIGH | Rotate credentials; audit `reviews` table for unauthorized deletions (look for reviews deleted by non-admin user IDs); fix dependency; add regression test |
| `Book` deleted but reviews remain (SET NULL used instead of CASCADE) | LOW | `DELETE FROM reviews WHERE book_id IS NULL`; add CASCADE FK in migration |
| `BookDetailResponse` returns `null` for `average_rating` (wrong pattern) | LOW | Fix the router to pass computed aggregates alongside `model_validate(book)`; no data corruption, only missing data in API response |
| Review model not in test schema (missing registry import) | LOW | Add `from app.reviews.models import Review` to `app/db/base.py`; re-run full test suite; add CI lint step checking all `app/*/models.py` files are imported in `app/db/base.py` |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Wrong verified-purchase query (no status filter) | Review creation phase | Test: user with `payment_failed` order cannot post review; test: user with `confirmed` order can |
| Duplicate review race condition | Review model/migration phase | Test: POST same review twice; assert second returns 409, not 500; confirm UNIQUE constraint in `\d reviews` |
| No index on `reviews(book_id)` | Review model/migration phase | Check migration for `Index("ix_reviews_book_id", ...)` before merging |
| Wrong FK behavior (SET NULL instead of CASCADE) | Review model/migration phase | Test: delete book; assert reviews are gone; assert `SELECT COUNT(*) FROM reviews WHERE book_id IS NULL` = 0 |
| Admin delete uses wrong auth dep | Review admin moderation phase | Test: call `DELETE /admin/reviews/{id}` with regular-user JWT; assert 403 |
| BookDetailResponse not updated correctly | Book detail aggregate phase | Test: create review; call `GET /books/{id}`; assert `average_rating` is not null and equals submitted rating |
| Review model missing from central registry | Review model/migration phase (step 1) | Run `pytest tests/test_health.py` immediately after model creation; run full 179-test suite after each phase |
| User_id from request body | Review creation phase | Test: submit review with `user_id` of another user in body; assert review is attributed to authenticated user |
| No pagination on review list | Review list phase | Verify `GET /books/{id}/reviews` has `page`/`size` params from day one |

---

## Sources

- Existing codebase: `app/orders/models.py` (`OrderStatus`, `OrderItem.book_id SET NULL`), `app/books/schemas.py` (`BookDetailResponse`), `app/core/deps.py` (`CurrentUser`, `ActiveUser`, `AdminUser`), `app/books/router.py` (auth dep patterns)
- SQLAlchemy UNIQUE constraint + IntegrityError handling: [Handling concurrent INSERT with SQLAlchemy](https://rachbelaid.com/handling-race-condition-insert-with-sqlalchemy/), [SQLAlchemy UniqueViolation handling](https://rollbar.com/blog/python-psycopg2-errors-uniqueviolation/)
- PostgreSQL aggregate performance: [PostgreSQL Aggregation Best Practices (TigerData)](https://www.tigerdata.com/learn/postgresql-aggregation-best-practices), [Generated Columns vs Triggers in PostgreSQL](https://ongres.com/blog/generate_columns_vs_triggers/)
- Race conditions in PostgreSQL MVCC: [Handling Race Conditions in PostgreSQL MVCC (Bufisa)](https://bufisa.com/2025/07/17/handling-race-conditions-in-postgresql-mvcc/), [SQLAlchemy and Race Conditions](https://skien.cc/blog/2014/01/15/sqlalchemy-and-race-conditions-implementing-get_one_or_create/)
- Denormalization tradeoffs for ratings: [Denormalization: A Solution for Performance or a Long-Term Trap?](https://rafaelrampineli.medium.com/denormalization-a-solution-for-performance-or-a-long-term-trap-6b9af5b5b831)
- CASCADE vs SET NULL design: [SQL ON DELETE CASCADE (DataCamp)](https://www.datacamp.com/tutorial/sql-on-delete-cascade), [SQLAlchemy Cascading Deletes](https://www.geeksforgeeks.org/python/sqlalchemy-cascading-deletes/)

---
*Pitfalls research for: FastAPI bookstore v2.0 — adding reviews & ratings to existing system*
*Researched: 2026-02-26*
