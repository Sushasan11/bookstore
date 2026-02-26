# Phase 6: Cart - Research

**Researched:** 2026-02-25
**Domain:** Persistent shopping cart — SQLAlchemy 2.0 async, PostgreSQL schema design, FastAPI service layer, stock availability enforcement
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMM-01 | User can add books to shopping cart | One-cart-per-user enforcement via `carts` table; `POST /cart/items` with `book_id` + `quantity`; stock check before insert; `UNIQUE(cart_id, book_id)` prevents duplicates |
| COMM-02 | User can update cart item quantity or remove items | `PUT /cart/items/{id}` to update quantity (Pydantic-validated ge=1); `DELETE /cart/items/{id}` for removal; 404 on unknown item; 403 if item belongs to different user |
</phase_requirements>

---

## Summary

Phase 6 introduces a persistent shopping cart backed by two new database tables: `carts` (one per user, lazily created on first add) and `cart_items` (line items with `UNIQUE(cart_id, book_id)` to prevent duplicate entries). The entire feature uses the existing stack — no new libraries. The primary design challenge is **one-cart-per-user enforcement**: the service must either `SELECT` an existing cart or `INSERT` a new one atomically, using a `SELECT ... FOR UPDATE` or an `INSERT ... ON CONFLICT DO NOTHING` approach to avoid race conditions.

Stock availability is checked **at add time** (not at checkout). If `stock_quantity == 0`, the service raises `AppError(409, ...)` with error code `CART_BOOK_OUT_OF_STOCK`. This check is advisory — no stock is reserved (decrement happens at checkout in Phase 7). The `PUT /cart/items/{id}` endpoint updates `quantity` but does **not** re-check stock — only the initial add enforces availability. This is consistent with standard e-commerce practice.

The response shape for `GET /cart` must join book data (title, author, price, cover image) to each cart item for a useful client experience. This requires either `selectinload(CartItem.book)` in the repository or explicit columns in the SELECT. Project precedent (Phase 4/5) avoids N+1 by keeping responses lean — return `book_id` and a nested `book` object loaded via `selectinload`. The `User.id` comes from the JWT payload (`current_user["sub"]`) following the existing `get_current_user` dependency pattern established in Phase 2.

**Primary recommendation:** Implement `carts` + `cart_items` tables with `UNIQUE(cart_id, book_id)`, use `INSERT ... ON CONFLICT DO NOTHING` or `get_or_create` pattern for cart creation, load cart items with `selectinload(CartItem.book)` for the GET response, and enforce stock > 0 on add only.

---

## Standard Stack

### Core (no new dependencies required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ^2.0.47 | Cart + CartItem ORM models, async queries, `selectinload` for book eager loading | All prior phases use this; `UniqueConstraint`, `ForeignKey`, `selectinload` all available |
| asyncpg | ^0.31.0 | PostgreSQL driver executing all cart queries | Only driver in project; handles `ON CONFLICT DO NOTHING` via SQLAlchemy dialect |
| Alembic | ^1.18.4 | Migration creating `carts` and `cart_items` tables | Hand-written migration chaining off `a1b2c3d4e5f6` (latest search_vector migration) |
| Pydantic | ^2.12.5 | `CartItemAdd`, `CartItemUpdate`, `CartResponse` schemas with validation | `ge=1` on quantity fields; `from_attributes=True` for ORM-to-schema conversion |
| FastAPI | ^0.133.0 | Router with `CurrentUser` dependency from `app.core.deps` | `CurrentUser = Annotated[dict, Depends(get_current_user)]` is established pattern |

### No New Libraries Required

The entire cart feature is achievable with the current stack. Do NOT add `sqlalchemy-utils` or any cart-specific package. The `ON CONFLICT` behavior is handled cleanly with SQLAlchemy's `insert().on_conflict_do_nothing()` or a simple `get_by_user_id / create` pair in the repository.

**Installation:** None required.

---

## Architecture Patterns

### Recommended Project Structure

```
app/cart/
├── __init__.py      # Already exists (stub)
├── models.py        # NEW: Cart + CartItem SQLAlchemy models
├── repository.py    # NEW: CartRepository + CartItemRepository
├── schemas.py       # NEW: CartItemAdd, CartItemUpdate, CartResponse, CartItemResponse
├── service.py       # NEW: CartService with business logic (stock check, get-or-create cart)
└── router.py        # NEW: GET /cart, POST /cart/items, PUT /cart/items/{id}, DELETE /cart/items/{id}

alembic/versions/
└── XXXX_create_carts_and_cart_items.py  # NEW: hand-written migration
```

### Pattern 1: One-Cart-Per-User Enforcement (Get-or-Create)

**What:** Each user has at most one cart. On first `POST /cart/items`, the service creates the cart. Subsequent calls reuse it. This must be race-condition-safe.

**When to use:** Every cart operation starts by resolving the user's cart.

**Approach — two-step get-or-create with INSERT ON CONFLICT:**

The safest async approach uses a dedicated `get_or_create` repository method that inserts and catches `IntegrityError` (from the `UNIQUE(user_id)` constraint on `carts`), or uses PostgreSQL's `INSERT INTO carts (user_id) VALUES (:uid) ON CONFLICT (user_id) DO NOTHING RETURNING id` pattern. The SQLAlchemy dialect supports this:

```python
# Source: SQLAlchemy docs — insert().on_conflict_do_nothing()
# In app/cart/repository.py

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from app.cart.models import Cart

class CartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: int) -> Cart:
        """Return the user's cart, creating it if it does not exist.

        Uses INSERT ON CONFLICT DO NOTHING to avoid a race condition where
        two concurrent requests both see no cart and both try to INSERT.
        """
        # Attempt upsert-style insert (no-op if cart already exists for user)
        stmt = (
            pg_insert(Cart)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Guaranteed to exist now (either existed before or just inserted)
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        return result.scalar_one()
```

**Alternative — simpler two-query approach (acceptable for v1 load):**

```python
async def get_or_create(self, user_id: int) -> Cart:
    result = await self.session.execute(
        select(Cart).where(Cart.user_id == user_id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user_id)
        self.session.add(cart)
        await self.session.flush()
    return cart
```

The two-query approach has a theoretical race condition on concurrent first-adds for the same user. For a bookstore where a user adds items from a single browser session, this is extremely unlikely. The `ON CONFLICT DO NOTHING` approach is correct and not much more complex — use it.

### Pattern 2: CartItem with UNIQUE(cart_id, book_id) Constraint

**What:** Prevents duplicate cart items for the same book. If a user adds a book already in the cart, the service should either raise a 409 or increase the quantity (upsert). Project conventions suggest returning 409 for clean error handling (client should use PUT to update quantity).

**Database constraint:**
```sql
UNIQUE (cart_id, book_id)
```

**SQLAlchemy model:**
```python
# Source: SQLAlchemy docs — UniqueConstraint in __table_args__
# In app/cart/models.py

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Cart(Base):
    __tablename__ = "carts"

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_carts_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint("cart_id", "book_id", name="uq_cart_items_cart_book"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cart: Mapped["Cart"] = relationship(back_populates="items")
    book: Mapped["Book"] = relationship()
```

**Note on FK cascade:** When a book is deleted (Phase 4 delete endpoint), `cart_items` with that `book_id` will violate FK unless `ON DELETE CASCADE` or `ON DELETE RESTRICT` is set. Use `ON DELETE CASCADE` on `cart_items.book_id` — removing a book from the catalog automatically removes it from all carts. This avoids FK errors and is the intuitive behavior.

Similarly, `Cart.user_id` should use `ON DELETE CASCADE` — deleting a user removes their cart.

### Pattern 3: Stock Availability Check at Add Time

**What:** When `POST /cart/items` is called, the service fetches the book and checks `stock_quantity > 0`. If zero, raises `AppError(409, ...)`.

**When to use:** Only at add time — `PUT /cart/items/{id}` (quantity update) does NOT re-check stock.

```python
# Source: Project convention (AppError pattern from Phase 1, BookService.set_stock pattern from Phase 4)
# In app/cart/service.py

from app.core.exceptions import AppError
from app.books.repository import BookRepository

class CartService:
    def __init__(
        self,
        cart_repo: CartRepository,
        cart_item_repo: CartItemRepository,
        book_repo: BookRepository,
    ) -> None:
        self.cart_repo = cart_repo
        self.cart_item_repo = cart_item_repo
        self.book_repo = book_repo

    async def add_item(self, user_id: int, book_id: int, quantity: int) -> CartItem:
        # 1. Verify book exists
        book = await self.book_repo.get_by_id(book_id)
        if book is None:
            raise AppError(
                status_code=404,
                detail="Book not found",
                code="BOOK_NOT_FOUND",
                field="book_id",
            )

        # 2. Check stock availability
        if book.stock_quantity == 0:
            raise AppError(
                status_code=409,
                detail="This book is out of stock and cannot be added to cart",
                code="CART_BOOK_OUT_OF_STOCK",
                field="book_id",
            )

        # 3. Get or create cart for user
        cart = await self.cart_repo.get_or_create(user_id)

        # 4. Add item (CartItemRepository handles UNIQUE conflict)
        return await self.cart_item_repo.add(cart.id, book_id, quantity)
```

### Pattern 4: Loading Cart Items with Book Data (Avoiding N+1)

**What:** `GET /cart` must return cart items with book details (title, price, etc.). Loading `item.book` lazily in async context raises `MissingGreenlet`. Use `selectinload`.

```python
# Source: SQLAlchemy 2.0 docs — selectinload for async eager loading
# In app/cart/repository.py

from sqlalchemy.orm import selectinload

class CartRepository:
    async def get_with_items(self, user_id: int) -> Cart | None:
        """Load user's cart with all items and their associated books."""
        result = await self.session.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.book))
        )
        return result.scalar_one_or_none()
```

**Why `selectinload` over `joinedload`:** `joinedload` on a collection (`Cart.items`) produces a JOIN that multiplies rows — with 5 cart items, you get 5 rows per cart. `selectinload` issues a separate `SELECT ... WHERE cart_id IN (...)` for items, then another for books. Two additional queries, but no row multiplication. This is the standard pattern for collection relationships in SQLAlchemy async.

### Pattern 5: Service Factory Pattern (_make_service)

**What:** Following the established pattern from `app/books/router.py`, use a `_make_service(db)` factory function in the cart router.

```python
# Source: app/books/router.py — established project pattern
# In app/cart/router.py

from app.cart.repository import CartRepository, CartItemRepository
from app.books.repository import BookRepository
from app.cart.service import CartService

def _make_service(db: DbSession) -> CartService:
    return CartService(
        cart_repo=CartRepository(db),
        cart_item_repo=CartItemRepository(db),
        book_repo=BookRepository(db),
    )
```

### Pattern 6: Extracting user_id from JWT Payload

**What:** Cart routes require authentication. The `CurrentUser` dependency provides the decoded JWT payload. User ID is in the `"sub"` claim (as a string — must be cast to int).

```python
# Source: app/core/deps.py — CurrentUser type alias, established Phase 2 pattern
# In app/cart/router.py

from app.core.deps import CurrentUser, DbSession

@router.get("/cart", response_model=CartResponse)
async def get_cart(db: DbSession, current_user: CurrentUser) -> CartResponse:
    user_id = int(current_user["sub"])
    service = _make_service(db)
    cart = await service.get_cart(user_id)
    return CartResponse.model_validate(cart)
```

**Important:** `current_user["sub"]` is a string (per JWT spec — subject is always a string). Always cast with `int(current_user["sub"])` before passing to repository methods.

### Pattern 7: Cart Item Ownership Verification

**What:** `PUT /cart/items/{id}` and `DELETE /cart/items/{id}` must verify that the cart item belongs to the requesting user before modifying. Otherwise user A could modify user B's cart.

```python
# Source: Security best practice — resource ownership check
# In app/cart/service.py

async def _get_item_for_user(self, item_id: int, user_id: int) -> CartItem:
    """Fetch cart item and verify it belongs to the requesting user."""
    item = await self.cart_item_repo.get_by_id(item_id)
    if item is None:
        raise AppError(
            status_code=404,
            detail="Cart item not found",
            code="CART_ITEM_NOT_FOUND",
            field="item_id",
        )
    # Verify ownership via cart's user_id
    if item.cart.user_id != user_id:
        raise AppError(
            status_code=403,
            detail="Not authorized to modify this cart item",
            code="CART_ITEM_FORBIDDEN",
        )
    return item
```

**Note:** This requires loading `item.cart` — use `selectinload(CartItem.cart)` in `CartItemRepository.get_by_id()` to avoid the async lazy-load problem.

### Anti-Patterns to Avoid

- **Lazy-loading `item.book` or `item.cart` in async context:** Always use `selectinload`. Accessing unloaded relationships in SQLAlchemy async raises `MissingGreenlet` or triggers an implicit detached instance access error.
- **Re-checking stock on PUT /cart/items/{id}:** Stock check is at add time only. Quantity update should not block users with items already in their cart if stock later reaches 0.
- **Storing price in cart_items:** Price belongs in `order_items` (Phase 7) as a snapshot at purchase time — not in cart. Cart always shows the current book price from `books.price`. This is the established project pattern (Phase 7 roadmap explicitly has `unit_price` snapshot on `order_items`).
- **Global cart router prefix conflict:** Use `/cart` as the router prefix. The `GET /books` and `GET /genres` routes have no router-level prefix — the cart router MUST have `prefix="/cart"` to avoid conflicts.
- **Using `autogenerate` for this migration without care:** The `alembic/env.py` has an `include_object` filter from Phase 5 that excludes the GIN index. Cart tables are standard and CAN be autogenerated, but given the project pattern of hand-writing migrations for correctness, hand-write this one too. Chain off `a1b2c3d4e5f6` (the current head migration).
- **Not cascading deletes:** If a book is deleted while in a cart, the FK constraint on `cart_items.book_id` will prevent deletion or orphan items. Add `ON DELETE CASCADE` on `cart_items.book_id`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| One-cart-per-user atomicity | Manual check-then-insert with application-level lock | `INSERT ON CONFLICT DO NOTHING` + `SELECT` | Race-condition-safe; PostgreSQL enforces the UNIQUE constraint atomically |
| Preventing duplicate cart items | Application-level duplicate check before insert | `UNIQUE(cart_id, book_id)` DB constraint + catch `IntegrityError` | DB enforces uniqueness even under concurrent inserts; application check has TOCTOU race |
| Eager loading cart items with books | Multiple separate queries per item (N+1) | `selectinload(Cart.items).selectinload(CartItem.book)` | SQLAlchemy handles this in 2 queries regardless of item count |
| Ownership verification | Session-based cart ownership tracking | FK through `cart_items.cart_id -> carts.user_id` | Ownership is structural (DB FK), not behavioral; just check `item.cart.user_id == user_id` |

**Key insight:** PostgreSQL's unique constraints and foreign key cascades handle most of the cart invariants. The application layer's role is to raise informative errors (AppError) when those constraints fire, not to pre-empt them with complex application logic.

---

## Common Pitfalls

### Pitfall 1: MissingGreenlet on Lazy-Loaded Relationships

**What goes wrong:** `CartItem.book` or `CartItem.cart` accessed outside the eager-load scope raises `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here`.

**Why it happens:** SQLAlchemy async does not support implicit lazy-loading. Any relationship access after the session context is closed (or outside an awaited greenlet) fails.

**How to avoid:** Every repository method that returns `CartItem` objects where the relationship will be accessed MUST use `selectinload`:
- `CartRepository.get_with_items()`: `selectinload(Cart.items).selectinload(CartItem.book)`
- `CartItemRepository.get_by_id()`: `selectinload(CartItem.cart)` (for ownership check)

**Warning signs:** `MissingGreenlet` in test logs; "greenlet" in exception traceback.

### Pitfall 2: sub Claim is a String, Not an Integer

**What goes wrong:** `current_user["sub"]` passed directly to `CartRepository.get_or_create(user_id)` fails because the repository expects `int` but receives `str "123"`.

**Why it happens:** JWT spec defines `sub` as a string. `create_access_token` in `app/core/security.py` encodes it as `str(user_id)`.

**How to avoid:** Always cast: `user_id = int(current_user["sub"])`. Add this at the top of every route handler that uses `current_user`.

**Warning signs:** SQLAlchemy type errors or unexpected query results; `WHERE user_id = '5'` instead of `WHERE user_id = 5`.

### Pitfall 3: IntegrityError on Duplicate Cart Item Not Handled

**What goes wrong:** User POSTs the same `book_id` twice. PostgreSQL raises `UniqueViolationError` wrapping `IntegrityError`. Without handling, the generic exception handler returns a 500.

**Why it happens:** The `UNIQUE(cart_id, book_id)` constraint fires on duplicate insert.

**How to avoid:** In `CartItemRepository.add()`, catch `IntegrityError` and check if the cause is the unique constraint (check `e.orig` string contains `"uq_cart_items_cart_book"` or `"cart_items"`), then raise `AppError(409, "Book already in cart", "CART_ITEM_DUPLICATE", "book_id")`.

Pattern from `BookService.create_book()` (Phase 4):
```python
from sqlalchemy.exc import IntegrityError

async def add(self, cart_id: int, book_id: int, quantity: int) -> CartItem:
    item = CartItem(cart_id=cart_id, book_id=book_id, quantity=quantity)
    self.session.add(item)
    try:
        await self.session.flush()
    except IntegrityError as e:
        if "cart_items" in str(e.orig).lower() or "uq_cart_items" in str(e.orig).lower():
            raise AppError(
                status_code=409,
                detail="This book is already in your cart",
                code="CART_ITEM_DUPLICATE",
                field="book_id",
            ) from e
        raise
    return item
```

**Warning signs:** 500 errors when adding duplicate books; `IntegrityError` in logs.

### Pitfall 4: GET /cart Returns 404 vs Empty Cart for New Users

**What goes wrong:** A user with no cart yet calls `GET /cart`. The service returns `None` and the route raises a 404. But from the user's perspective, an empty cart is valid — it should return an empty items list.

**Why it happens:** The `get_or_create` is only called on `POST /cart/items`. For `GET /cart`, if the cart does not exist, the response should be an empty cart, not an error.

**How to avoid:** In `CartService.get_cart()`, if no cart exists for the user, return a synthetic empty cart response (do NOT create a cart on GET — only create on POST):

```python
async def get_cart(self, user_id: int) -> CartResponse:
    """Return user's cart. Returns empty cart if user has never added an item."""
    cart = await self.cart_repo.get_with_items(user_id)
    if cart is None:
        # Return a virtual empty cart — no DB row created
        return CartResponse(items=[], total_items=0, total_price=Decimal("0.00"))
    return _cart_to_response(cart)
```

**Warning signs:** New users get 404 on `GET /cart` instead of an empty response.

### Pitfall 5: Cart Item ID vs Book ID in PUT/DELETE Routes

**What goes wrong:** `PUT /cart/items/{id}` and `DELETE /cart/items/{id}` — the `{id}` is the `CartItem.id` (primary key of the `cart_items` table), NOT the `book_id`. This is the correct design (allows updating the quantity of any specific item), but tests must create items and use the returned `CartItem.id`, not `book_id`.

**Why it happens:** Route parameter naming can be ambiguous.

**How to avoid:** Name the path parameter `item_id` in the route signature for clarity:
```python
@router.put("/cart/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(item_id: int, ...) -> CartItemResponse:
```

**Warning signs:** Tests failing with 404 when passing `book_id` as the path parameter; confusion in test setup.

### Pitfall 6: Model Import Registration in alembic/env.py

**What goes wrong:** New `Cart` and `CartItem` models are not imported in `alembic/env.py`, so `alembic revision --autogenerate` cannot detect them and the hand-written migration references tables that `Base.metadata` does not know about.

**Why it happens:** Phase 4 decision (STATE.md): "Model imports in alembic/env.py (not app/db/base.py) to avoid circular imports". This pattern must be followed for Phase 6 as well.

**How to avoid:** Add `from app.cart.models import Cart, CartItem` to `alembic/env.py` alongside the existing `from app.books.models import ...` import. Also register `Cart` and `CartItem` in `Base.metadata` for `create_all` to work in tests.

**Warning signs:** `alembic upgrade head` succeeds (hand-written migration runs) but `pytest` fails because `create_all` didn't create the cart tables; or vice versa.

---

## Code Examples

Verified patterns from project codebase and official sources:

### Cart + CartItem Models

```python
# Source: project conventions — app/users/models.py (UniqueConstraint pattern),
#         app/books/models.py (DateTime server_default, ForeignKey, relationship)
# File: app/cart/models.py

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Cart(Base):
    __tablename__ = "carts"

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_carts_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint("cart_id", "book_id", name="uq_cart_items_cart_book"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cart: Mapped["Cart"] = relationship(back_populates="items")
    book: Mapped["Book"] = relationship()
```

### Alembic Migration (hand-written, chains off a1b2c3d4e5f6)

```python
# Source: project migration patterns — c3d4e5f6a7b8_create_genres_and_books.py
# File: alembic/versions/XXXX_create_carts_and_cart_items.py

"""create carts and cart_items tables

Revision ID: XXXX
Revises: a1b2c3d4e5f6
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from alembic import op

revision: str = "XXXX"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_carts_user_id"),
    )
    op.create_index("ix_carts_user_id", "carts", ["user_id"])

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["books_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cart_id", "book_id", name="uq_cart_items_cart_book"),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    op.create_index("ix_cart_items_book_id", "cart_items", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_cart_items_book_id", table_name="cart_items")
    op.drop_index("ix_cart_items_cart_id", table_name="cart_items")
    op.drop_table("cart_items")
    op.drop_index("ix_carts_user_id", table_name="carts")
    op.drop_table("carts")
```

### Cart Schemas

```python
# Source: app/books/schemas.py — BookResponse (from_attributes pattern),
#         Pydantic v2 docs (computed_field for total_price)
# File: app/cart/schemas.py

from decimal import Decimal
from pydantic import BaseModel, computed_field, Field


class CartItemAdd(BaseModel):
    """Request body for POST /cart/items."""
    book_id: int
    quantity: int = Field(ge=1, default=1, description="Number of copies to add (min 1)")


class CartItemUpdate(BaseModel):
    """Request body for PUT /cart/items/{item_id}."""
    quantity: int = Field(ge=1, description="New quantity (min 1)")


class BookSummary(BaseModel):
    """Nested book info in cart item response."""
    id: int
    title: str
    author: str
    price: Decimal
    cover_image_url: str | None

    model_config = {"from_attributes": True}


class CartItemResponse(BaseModel):
    """Response schema for a single cart item."""
    id: int
    book_id: int
    quantity: int
    book: BookSummary

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    """Response schema for GET /cart."""
    items: list[CartItemResponse]

    @computed_field  # type: ignore[misc]
    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items)

    @computed_field  # type: ignore[misc]
    @property
    def total_price(self) -> Decimal:
        return sum(item.book.price * item.quantity for item in self.items)
```

### Cart Endpoints

```python
# Source: app/books/router.py — established router pattern with _make_service factory
# File: app/cart/router.py

from fastapi import APIRouter, status
from app.cart.repository import CartRepository, CartItemRepository
from app.books.repository import BookRepository
from app.cart.schemas import CartItemAdd, CartItemUpdate, CartItemResponse, CartResponse
from app.cart.service import CartService
from app.core.deps import CurrentUser, DbSession

router = APIRouter(prefix="/cart", tags=["cart"])


def _make_service(db: DbSession) -> CartService:
    return CartService(
        cart_repo=CartRepository(db),
        cart_item_repo=CartItemRepository(db),
        book_repo=BookRepository(db),
    )


@router.get("", response_model=CartResponse)
async def get_cart(db: DbSession, current_user: CurrentUser) -> CartResponse:
    """Get the authenticated user's cart with all items. Returns empty cart if no items added."""
    user_id = int(current_user["sub"])
    service = _make_service(db)
    return await service.get_cart(user_id)


@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    body: CartItemAdd, db: DbSession, current_user: CurrentUser
) -> CartItemResponse:
    """Add a book to the cart. Creates the cart if it doesn't exist.

    409 if book is out of stock (stock_quantity == 0).
    409 if book is already in cart (use PUT to update quantity).
    404 if book_id does not exist.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    item = await service.add_item(user_id, body.book_id, body.quantity)
    return CartItemResponse.model_validate(item)


@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int, body: CartItemUpdate, db: DbSession, current_user: CurrentUser
) -> CartItemResponse:
    """Update the quantity of a cart item. Does not re-check stock availability.

    404 if item_id not found. 403 if item belongs to a different user.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    item = await service.update_item(user_id, item_id, body.quantity)
    return CartItemResponse.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_item(
    item_id: int, db: DbSession, current_user: CurrentUser
) -> None:
    """Remove an item from the cart.

    404 if item_id not found. 403 if item belongs to a different user.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    await service.remove_item(user_id, item_id)
```

### Router Registration in main.py

```python
# Source: app/main.py — existing include_router pattern
# Add to app/main.py create_app():

from app.cart.router import router as cart_router
application.include_router(cart_router)
```

### Test Fixtures for Cart Phase

```python
# Source: tests/test_catalog.py — admin_headers + user_headers fixture pattern
# tests/test_cart.py

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.users.repository import UserRepository


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="cart_user@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "cart_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="cart_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "cart_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Session-based cart (stored in server session) | DB-persisted cart (one row per user in `carts` table) | Industry shift ~2010 | Cart survives server restarts, works across devices, no session expiry issues |
| Cart stored in Redis/cache | DB-persisted cart (PostgreSQL) | — | For this scale, DB is simpler; cache adds ops burden for marginal benefit |
| `session.query(Cart).filter(...)` | `select(Cart).where(...)` | SQLAlchemy 2.0 (2023) | Project uses new-style 2.0 queries throughout |
| Storing unit_price in cart_items | Storing price only in order_items (Phase 7) | Domain modeling | Cart shows current live price; snapshot happens at checkout |
| `lazy="dynamic"` relationship | `selectinload` in async context | SQLAlchemy asyncio | `lazy="dynamic"` not supported in async SQLAlchemy; use `selectinload` |

**Deprecated/outdated (do not use):**
- `relationship(lazy="dynamic")`: Not supported in SQLAlchemy async. Use `selectinload` in queries.
- `session.query()`: Old 1.x API. Project uses `select(...).where(...)` throughout.
- Storing cart in JWT: Carts need server-side persistence for COMM-01 requirement (cross-session persistence).

---

## Open Questions

1. **Should adding a duplicate book update quantity or return 409?**
   - What we know: Phase 6 success criteria #1 says POST to add and GET to see — says nothing about duplicates. The UNIQUE constraint exists to prevent duplicates. Standard practice varies: some systems upsert (quantity += N), others return 409.
   - What's unclear: There is no CONTEXT.md for Phase 6.
   - Recommendation: Return **409 with `CART_ITEM_DUPLICATE`** error code and guide the client to use `PUT /cart/items/{id}` to update quantity. This is simpler, consistent with the BookService ISBN conflict pattern (Phase 4), and avoids silently mutating state on POST.

2. **Should GET /cart create the cart row or return a virtual empty response?**
   - What we know: Creating a cart row on GET is a side effect on a read-only endpoint — bad practice. But having no row means `POST /cart/items` must do a `get_or_create`.
   - Recommendation: **Do NOT create a cart on GET**. Return a virtual `CartResponse(items=[])` when the user has no cart. Only `POST /cart/items` triggers `get_or_create`.

3. **What quantity validation should PUT /cart/items/{id} enforce?**
   - What we know: `ge=1` is the minimum (removing an item uses DELETE, not quantity=0). There is no maximum defined in requirements.
   - Recommendation: Validate `quantity >= 1` with Pydantic `Field(ge=1)`. No maximum validation — out-of-stock behavior is checked at Phase 7 checkout (stock decrement), not at cart update time.

4. **Should the test for "cart persists across sessions" (success criteria #5) create a new client/token or reuse the same session?**
   - What we know: The test database rolls back after each test. Cross-session means: logout, login again, GET /cart still shows items — this tests that the cart is DB-persisted, not session-stored.
   - Recommendation: In a single test function, POST an item, then login again (new token), then GET /cart — verifies DB persistence without needing a second test transaction.

---

## Sources

### Primary (HIGH confidence)

- `D:/Python/claude-test/app/books/models.py` — UniqueConstraint, ForeignKey, relationship patterns used directly
- `D:/Python/claude-test/app/books/repository.py` — repository method structure, async session patterns
- `D:/Python/claude-test/app/books/service.py` — AppError usage, IntegrityError handling pattern
- `D:/Python/claude-test/app/books/router.py` — _make_service factory, route structure, response_model pattern
- `D:/Python/claude-test/app/books/schemas.py` — computed_field, from_attributes=True pattern
- `D:/Python/claude-test/app/core/deps.py` — CurrentUser alias, get_current_user dependency
- `D:/Python/claude-test/app/core/exceptions.py` — AppError structure, status_code/code/field convention
- `D:/Python/claude-test/app/core/security.py` — JWT sub claim encoding as str(user_id)
- `D:/Python/claude-test/app/main.py` — router registration pattern
- `D:/Python/claude-test/tests/conftest.py` — test infrastructure (create_all, client fixture, dependency override)
- `D:/Python/claude-test/tests/test_catalog.py` — admin_headers/user_headers fixture pattern
- `D:/Python/claude-test/.planning/STATE.md` — "Model imports in alembic/env.py" decision, existing design decisions
- `D:/Python/claude-test/.planning/ROADMAP.md` — Phase 6 success criteria, Phase 7 order_items unit_price context
- `D:/Python/claude-test/alembic/versions/a1b2c3d4e5f6_add_books_search_vector.py` — current head migration (down_revision for new cart migration)
- SQLAlchemy 2.0 docs: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html — selectinload for async eager loading
- SQLAlchemy 2.0 docs: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict — insert().on_conflict_do_nothing()
- PostgreSQL docs: https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT — ON CONFLICT DO NOTHING semantics

### Secondary (MEDIUM confidence)

- SQLAlchemy asyncio docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html — MissingGreenlet behavior with lazy loading; recommendation to use selectinload
- FastAPI docs: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — JWT sub claim handling pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all patterns directly verified in existing codebase (Phases 1-5)
- Architecture patterns: HIGH — models, repositories, service, router all follow established Phase 4 conventions exactly; unique constraints and FK cascades are standard PostgreSQL/SQLAlchemy
- Pitfalls: HIGH — MissingGreenlet, sub-as-string, IntegrityError handling, and import registration are all confirmed from existing project code and SQLAlchemy docs
- ON CONFLICT DO NOTHING pattern: HIGH — SQLAlchemy PostgreSQL dialect docs confirm this API; used in PostgreSQL for upsert patterns broadly

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable stack; SQLAlchemy 2.0 async patterns are not fast-moving)
