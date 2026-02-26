# Phase 8: Wishlist - Research

**Researched:** 2026-02-26
**Domain:** FastAPI / SQLAlchemy async — user-scoped join table with uniqueness constraint
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENGM-01 | User can add/remove books from wishlist | `wishlist_items` table with UNIQUE(user_id, book_id); POST /wishlist + DELETE /wishlist/{book_id}; IntegrityError → 409 pattern from cart |
| ENGM-02 | User can view their wishlist | GET /wishlist returns list of items with current book price and stock_quantity via selectinload(WishlistItem.book) |

</phase_requirements>

---

## Summary

Phase 8 introduces a wishlist feature that is architecturally simpler than cart (Phase 6). The wishlist has no intermediate parent-table indirection — there is no "Wishlist" header row; instead, there is a single `wishlist_items` table with `(user_id, book_id)` as a composite unique constraint. Each wishlist item is owned directly by a user, references a book, and carries an `added_at` timestamp. All the supporting infrastructure is already in place: the `AppError` pattern, `CurrentUser` / `DbSession` dependency aliases, `selectinload` for eager loading, the `pg_insert ... ON CONFLICT` technique, and `IntegrityError`-to-409 mapping.

The domain differs from cart in three deliberate ways. First, the wishlist is flat — no outer "wishlist" row, just items. Second, there is no quantity column; a book is either on the wishlist or not. Third, the `DELETE` route is keyed by `book_id` (the natural business key from the user's perspective), not an internal `item_id`. The success criteria for the phase explicitly state: "adding a book that is already on the wishlist returns a 409 rather than creating a duplicate entry," and "a user's wishlist shows the current price and stock status of each saved book."

Because the `wishlist` app package stub already exists at `app/wishlist/__init__.py`, the planner needs only to add the domain files (models, repository, service, schemas, router) and the Alembic migration. The `alembic/env.py` import list must be updated and the router registered in `app/main.py`.

**Primary recommendation:** Model `wishlist_items` as a direct user→book join table (no parent Wishlist row), enforce uniqueness with a DB-level UNIQUE constraint and catch `IntegrityError` → 409 exactly as cart does, and use `selectinload(WishlistItem.book)` for list retrieval to surface current price and stock status.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | ^2.0.47 (project) | ORM + async queries | Already in use across all domains |
| Alembic | ^1.18.4 (project) | Schema migrations | All table creation goes through Alembic |
| FastAPI | ^0.133.0 (project) | HTTP endpoints | Established project framework |
| Pydantic v2 | ^2.12.5 (project) | Request/response schemas | model_config = {"from_attributes": True} pattern in use |
| asyncpg | ^0.31.0 (project) | PostgreSQL async driver | Driver for all DB operations |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy.dialects.postgresql.insert | (bundled) | pg INSERT … ON CONFLICT | Idempotent inserts where racing first-add would cause duplicate |
| sqlalchemy.exc.IntegrityError | (bundled) | Catch unique constraint violations | Map DB-level 23505 to HTTP 409 |
| sqlalchemy.orm.selectinload | (bundled) | Eager-load book relationship | Prevents N+1 + MissingGreenlet when serializing items |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flat wishlist_items table | Cart-style Wishlist + WishlistItem (two tables) | Two-table approach adds indirection with no benefit — wishlist has no cart-level aggregate properties (totals, shared across checkout) |
| IntegrityError → 409 (catch at repository) | Explicit SELECT before INSERT | SELECT-then-INSERT has a race window; IntegrityError catch is the project-established pattern (cart) |
| DELETE by book_id path param | DELETE by item_id | book_id is the natural business key the API consumer knows; item_id is an internal row id the client should not need to track |

**Installation:** No new packages required — all dependencies are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

```
app/wishlist/
├── __init__.py       # Already exists (stub comment)
├── models.py         # WishlistItem SQLAlchemy model
├── repository.py     # WishlistRepository
├── schemas.py        # WishlistAdd, WishlistItemResponse, WishlistResponse
├── service.py        # WishlistService
└── router.py         # POST /wishlist, GET /wishlist, DELETE /wishlist/{book_id}

alembic/versions/
└── e5f6a7b8c9d0_create_wishlist_items.py   # new migration

tests/
└── test_wishlist.py  # integration tests for ENGM-01, ENGM-02
```

### Pattern 1: Flat join table with UNIQUE(user_id, book_id)

**What:** `wishlist_items` has no parent "wishlist" row. `user_id` and `book_id` FKs are both non-nullable, the pair is unique, and `book_id` ondelete=CASCADE preserves wishlist integrity when a book is deleted from the catalog.

**When to use:** When the domain has no aggregate properties on the outer container (no totals, no shared checkout state), a two-table model adds complexity with no benefit.

**Example:**
```python
# Source: project pattern from app/cart/models.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.books.models import Book

class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_wishlist_items_user_book"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    book: Mapped[Book] = relationship()
```

### Pattern 2: Repository with IntegrityError → 409 mapping

**What:** Add inserts via `self.session.add(item)` + `flush()`, catching `IntegrityError` and mapping the unique constraint violation to `AppError(409)`. This matches the `CartItemRepository.add()` established pattern exactly.

**When to use:** Any operation that can violate a DB unique constraint and must return a structured 409 (not a generic 500).

**Example:**
```python
# Source: project pattern from app/cart/repository.py
from sqlalchemy.exc import IntegrityError
from app.core.exceptions import AppError

async def add(self, user_id: int, book_id: int) -> WishlistItem:
    item = WishlistItem(user_id=user_id, book_id=book_id)
    self.session.add(item)
    try:
        await self.session.flush()
    except IntegrityError as e:
        await self.session.rollback()
        orig = str(e.orig).lower() if e.orig else ""
        if "uq_wishlist_items" in orig or "wishlist_items" in orig:
            raise AppError(
                409,
                "This book is already on your wishlist",
                "WISHLIST_ITEM_DUPLICATE",
                "book_id",
            ) from e
        raise
    await self.session.refresh(item, ["book"])
    return item
```

### Pattern 3: GET list with selectinload

**What:** Fetch all wishlist items for a user eagerly loading the book relationship in a single additional query, avoiding N+1.

**When to use:** Any list endpoint that returns child objects with a relationship attribute.

**Example:**
```python
# Source: project pattern from app/cart/repository.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def get_all_for_user(self, user_id: int) -> list[WishlistItem]:
    result = await self.session.execute(
        select(WishlistItem)
        .where(WishlistItem.user_id == user_id)
        .options(selectinload(WishlistItem.book))
        .order_by(WishlistItem.added_at.desc())
    )
    return list(result.scalars().all())
```

### Pattern 4: DELETE by book_id (natural key)

**What:** The DELETE endpoint accepts `book_id` as a path parameter, queries for the row by `(user_id, book_id)`, and returns 404 if not found or 204 on success.

**When to use:** When the client naturally knows the book_id (from browsing) but has no reason to track an internal wishlist item id.

**Example:**
```python
async def get_by_user_and_book(self, user_id: int, book_id: int) -> WishlistItem | None:
    result = await self.session.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == user_id,
            WishlistItem.book_id == book_id,
        )
    )
    return result.scalar_one_or_none()

async def delete(self, item: WishlistItem) -> None:
    await self.session.delete(item)
    await self.session.flush()
```

### Pattern 5: _make_service factory in router

**What:** The project uses a local `_make_service(db)` function in each router to instantiate the service with all repositories. This keeps routes thin and avoids FastAPI dependency injection complexity for service-layer wiring.

**When to use:** Every new router — this is the project convention.

**Example:**
```python
# Source: project pattern from app/cart/router.py and app/orders/router.py
def _make_service(db: DbSession) -> WishlistService:
    return WishlistService(
        wishlist_repo=WishlistRepository(db),
        book_repo=BookRepository(db),
    )
```

### Pattern 6: Alembic hand-written migration

**What:** All table creation migrations in this project are hand-written (not autogenerated). The migration chains `down_revision` to the most recent migration.

**Current head migration:** `d4e5f6a7b8c9` (orders and order_items). The wishlist migration's `down_revision` must be `"d4e5f6a7b8c9"`.

**Example:**
```python
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"

def upgrade() -> None:
    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_wishlist_items_user_book"),
    )
    op.create_index("ix_wishlist_items_user_id", "wishlist_items", ["user_id"])
    op.create_index("ix_wishlist_items_book_id", "wishlist_items", ["book_id"])

def downgrade() -> None:
    op.drop_index("ix_wishlist_items_book_id", table_name="wishlist_items")
    op.drop_index("ix_wishlist_items_user_id", table_name="wishlist_items")
    op.drop_table("wishlist_items")
```

### Anti-Patterns to Avoid

- **Two-table design (Wishlist + WishlistItem):** Adds a parent row that carries no useful data. The wishlist has no aggregate properties — no totals, no sharing, no checkout linkage. Use the flat one-table design.
- **DELETE by item_id:** The API consumer doesn't track internal item IDs for a wishlist. The natural delete key is `book_id`. Using item_id forces the client to store and pass back an opaque integer.
- **Allowing wishlist addition of deleted books:** `book_id` FK with `ondelete="CASCADE"` removes the wishlist item automatically when the admin deletes a book — no cleanup code needed.
- **Skipping `selectinload` on GET:** Accessing `item.book` without eager loading after the session context causes `MissingGreenlet`. Always use `selectinload(WishlistItem.book)` on the list query.
- **SELECT-then-INSERT for uniqueness:** Use IntegrityError catch, not a pre-check SELECT, to avoid the race window.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unique constraint enforcement | Manual SELECT-then-INSERT check | DB UNIQUE constraint + IntegrityError catch | DB enforces it atomically; the project pattern is already established in CartItemRepository |
| Eager relationship loading | Manual second SELECT for book data | `selectinload(WishlistItem.book)` | SQLAlchemy handles IN-clause batching; avoids N+1 and MissingGreenlet |
| Idempotent inserts | Try-except around add() | `pg_insert ... ON CONFLICT DO NOTHING` (if needed) | Race-condition-safe; established in CartRepository.get_or_create() |
| Error response formatting | Custom JSON construction | `AppError(409, ..., "WISHLIST_ITEM_DUPLICATE")` | Consistent structured error format enforced by app_error_handler |

**Key insight:** This domain is not novel — it is a simpler variant of cart (no quantity, no parent table, natural delete key). Every pattern is already proven in the codebase; no new approaches are needed.

---

## Common Pitfalls

### Pitfall 1: MissingGreenlet on relationship access
**What goes wrong:** `item.book.price` raises `MissingGreenlet` when accessed after the async session context without eager loading.
**Why it happens:** SQLAlchemy lazy-loads relationships synchronously by default; in async context, this fails.
**How to avoid:** Always use `selectinload(WishlistItem.book)` on any query whose results will have `.book` accessed. For the single-item `add()` return, use `await self.session.refresh(item, ["book"])` after flush (same as CartItemRepository).
**Warning signs:** `MissingGreenlet` or `greenlet_spawn has not been called` in tracebacks.

### Pitfall 2: IntegrityError string matching fragility
**What goes wrong:** The constraint name check (`"uq_wishlist_items" in orig`) fails if the constraint was named differently, causing the raw IntegrityError to propagate as a 500.
**Why it happens:** asyncpg error messages embed the constraint name in the `orig` string, which must match what was defined in the migration.
**How to avoid:** Name the constraint exactly `uq_wishlist_items_user_book` in both the model's `UniqueConstraint` and the Alembic migration, then check for that exact string in the repository catch block.
**Warning signs:** 500 errors on duplicate-add attempts during tests.

### Pitfall 3: Forgetting to register model in alembic/env.py
**What goes wrong:** `Base.metadata.create_all` in the test engine creates tables from `Base.metadata`, but only if the model has been imported. The test will fail with "table wishlist_items does not exist."
**Why it happens:** `alembic/env.py` has explicit model imports (not `app/db/base.py`). The pattern comment says "all future model imports go in alembic/env.py."
**How to avoid:** Add `from app.wishlist.models import WishlistItem  # noqa: F401` to `alembic/env.py` alongside the other model imports.
**Warning signs:** Test teardown "table does not exist" or INSERT errors in conftest `Base.metadata.create_all`.

### Pitfall 4: Forgetting to register router in app/main.py
**What goes wrong:** Wishlist endpoints return 404 because the router is never mounted.
**Why it happens:** FastAPI requires explicit `application.include_router(wishlist_router)` call.
**How to avoid:** Add the import and `include_router` call after the orders router registration in `app/main.py`.

### Pitfall 5: book_id ondelete policy mismatch
**What goes wrong:** Using `ondelete="SET NULL"` on `book_id` (as orders do) would leave a dangling wishlist item referencing no book, which breaks GET /wishlist serialization.
**Why it happens:** Orders use SET NULL to preserve purchase history. Wishlists have no such archival requirement.
**How to avoid:** Use `ondelete="CASCADE"` on `book_id` so the wishlist item is removed when the catalog book is deleted. This is consistent with the cart's behavior.

### Pitfall 6: Module-level email prefixes in test fixtures
**What goes wrong:** User creation collides with users created in other test modules (same test DB schema, sequential test run), causing unique constraint violations on `users.email`.
**Why it happens:** All test modules share the session-scoped `test_engine` and therefore the same tables. Without unique email prefixes, fixtures from different modules clash.
**How to avoid:** Use `wishlist_` prefix for all test user emails (e.g., `wishlist_user@example.com`, `wishlist_admin@example.com`). The pattern is established in `test_cart.py` with `cart_` prefix.

---

## Code Examples

Verified patterns from the project codebase:

### WishlistItemResponse schema with BookSummary embed
```python
# Pattern: app/cart/schemas.py — BookSummary + CartItemResponse
from decimal import Decimal
from pydantic import BaseModel

class BookSummary(BaseModel):
    id: int
    title: str
    author: str
    price: Decimal
    stock_quantity: int          # wishlist shows stock status (success criteria 3)
    cover_image_url: str | None

    model_config = {"from_attributes": True}

class WishlistItemResponse(BaseModel):
    id: int
    book_id: int
    added_at: datetime
    book: BookSummary

    model_config = {"from_attributes": True}

class WishlistResponse(BaseModel):
    items: list[WishlistItemResponse]
```

Note: `BookSummary` in the wishlist schema should include `stock_quantity` (unlike the cart's BookSummary which omits it) because success criterion 3 requires "the current price and stock status of each saved book."

### POST /wishlist endpoint
```python
# Pattern: app/cart/router.py
@router.post("", response_model=WishlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    body: WishlistAdd, db: DbSession, current_user: CurrentUser
) -> WishlistItemResponse:
    user_id = int(current_user["sub"])
    service = _make_service(db)
    item = await service.add(user_id, body.book_id)
    return WishlistItemResponse.model_validate(item)
```

### DELETE /wishlist/{book_id} endpoint
```python
# Pattern: app/cart/router.py remove_cart_item — adapted to book_id path param
@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    book_id: int, db: DbSession, current_user: CurrentUser
) -> None:
    user_id = int(current_user["sub"])
    service = _make_service(db)
    await service.remove(user_id, book_id)
```

### Test fixture pattern (module-specific email prefix)
```python
# Pattern: tests/test_cart.py
@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="wishlist_user@example.com", hashed_password=hashed)
    await db_session.flush()
    resp = await client.post(
        "/auth/login",
        json={"email": "wishlist_user@example.com", "password": "userpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Autogenerated migrations | Hand-written migrations | Phase 5 (GIN index Alembic bug #1390) | Must write migration SQL manually; autogenerate is not used |
| Lazy relationship loading | selectinload + refresh | Phase 6 (cart) | Mandatory in async context to avoid MissingGreenlet |
| asyncio_mode not set | asyncio_mode = "auto" | Phase 1 | No @pytest.mark.asyncio decorators needed on test functions |

**Deprecated/outdated:**
- `app/db/base.py` for model imports in Alembic: model imports go in `alembic/env.py` to avoid circular imports (established in Phase 4)

---

## Integration Points

### Files to Create
| File | Purpose |
|------|---------|
| `app/wishlist/models.py` | `WishlistItem` model |
| `app/wishlist/repository.py` | `WishlistRepository` |
| `app/wishlist/schemas.py` | `WishlistAdd`, `WishlistItemResponse`, `WishlistResponse` |
| `app/wishlist/service.py` | `WishlistService` |
| `app/wishlist/router.py` | `router = APIRouter(prefix="/wishlist", ...)` |
| `alembic/versions/e5f6a7b8c9d0_create_wishlist_items.py` | migration |
| `tests/test_wishlist.py` | integration tests |

### Files to Modify
| File | Change |
|------|--------|
| `alembic/env.py` | Add `from app.wishlist.models import WishlistItem  # noqa: F401` |
| `app/main.py` | Import and `application.include_router(wishlist_router)` |

### No Changes Needed
- `app/books/repository.py` — `BookRepository.get_by_id()` is already available for book existence validation in WishlistService
- `app/core/deps.py` — `CurrentUser`, `DbSession` already defined
- `app/core/exceptions.py` — `AppError` already defined

---

## Open Questions

1. **Router prefix: `/wishlist` vs `/wishlists`**
   - What we know: Cart uses `/cart` (singular), orders uses `/orders` (plural). The success criteria say `POST /wishlist` and `DELETE /wishlist/{book_id}` — singular.
   - What's unclear: Nothing — the success criteria explicitly name the routes.
   - Recommendation: Use `prefix="/wishlist"` (singular) per the explicit success criteria.

2. **book_id ondelete: CASCADE vs SET NULL**
   - What we know: Orders use SET NULL to preserve order history. Wishlists have no archival requirement — a wishlist item for a deleted book is meaningless.
   - What's unclear: Nothing.
   - Recommendation: `ondelete="CASCADE"` on `book_id`.

3. **Should POST /wishlist validate book existence before insert?**
   - What we know: Cart service calls `book_repo.get_by_id(book_id)` and raises 404 if missing. Wishlist has the same FK constraint, so the DB will also reject a nonexistent book_id (FK violation).
   - What's unclear: Whether to return a clean 404 or let FK violation surface as 500.
   - Recommendation: Do an explicit `BookRepository.get_by_id` check in `WishlistService.add()` and raise `AppError(404, "Book not found", "BOOK_NOT_FOUND", "book_id")` — consistent with the cart pattern and produces a clean 404 message.

---

## Sources

### Primary (HIGH confidence)
- Project codebase — `app/cart/models.py`, `app/cart/repository.py`, `app/cart/router.py`, `app/cart/service.py`, `app/cart/schemas.py` — direct inspection of established patterns
- Project codebase — `alembic/versions/b2c3d4e5f6a7_create_carts_and_cart_items.py` — migration hand-write pattern
- Project codebase — `alembic/env.py` — model import convention
- Project codebase — `app/main.py` — router registration pattern
- Project codebase — `app/core/exceptions.py` — AppError and structured error format
- Project codebase — `app/core/deps.py` — CurrentUser, DbSession type aliases
- Project codebase — `tests/conftest.py`, `tests/test_cart.py` — test infrastructure and fixture patterns
- `.planning/STATE.md` — accumulated decisions (expire_on_commit=False, selectinload mandatory, IntegrityError pattern, module email prefixes)
- `.planning/REQUIREMENTS.md` — ENGM-01, ENGM-02 requirements

### Secondary (MEDIUM confidence)
- Phase success criteria (from task prompt) — defines exact route signatures and 409 behavior

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — patterns directly copied from cart (most analogous domain in the project)
- Pitfalls: HIGH — drawn from project STATE.md accumulated decisions and direct code inspection
- Migration chain: HIGH — verified `d4e5f6a7b8c9` is the current head by inspecting `alembic/versions/`

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable domain — 30 days)
