# Phase 7: Orders - Research

**Researched:** 2026-02-25
**Domain:** Order management — transactional checkout with `SELECT FOR UPDATE`, stock decrement, price snapshot, order history
**Confidence:** HIGH

## Summary

Phase 7 adds the orders domain on top of the cart already built in Phase 6. The work breaks into three implementation areas: (1) database schema — `orders` and `order_items` tables with a `unit_price` snapshot field, (2) a transactional checkout endpoint that locks book stock rows with `SELECT FOR UPDATE` (ascending ID order to prevent deadlocks), validates stock, applies a mock payment, decrements stock, creates the order, and clears the cart — all within a single database transaction, and (3) read endpoints for user order history and admin order overview.

The project uses SQLAlchemy 2.x async with asyncpg, FastAPI, Pydantic v2, and pytest-asyncio with `asyncio_mode = auto`. All patterns used in earlier phases (repository layer, `_make_service()` factory, `AppError` structured exceptions, `CurrentUser`/`AdminUser` deps, `selectinload` for relationships, hand-written Alembic migrations) apply directly here. No new libraries are needed.

The most technically complex part is the checkout transaction: `SELECT FOR UPDATE` with `with_for_update()` in SQLAlchemy async requires rows be locked inside the same session and transaction that will issue the `UPDATE`. SQLAlchemy 2 async exposes this via `select(Book).where(...).with_for_update()` executed via `session.execute()`. Locking books in ascending primary-key order (sort the cart item book IDs before locking) is the deadlock prevention strategy already decided. Since `get_db()` in `deps.py` wraps the request in a single session and commits/rolls back at the end, the checkout service must work entirely inside that session without issuing intermediate commits.

**Primary recommendation:** Implement checkout as a single orchestrated method in `CheckoutService` (or `OrderService`) that: locks books via `SELECT FOR UPDATE` in ID order, validates stock for all items, calls `MockPaymentService.charge()`, creates the `Order` + `OrderItem` rows, decrements book stock, and deletes the cart — all via `session.flush()` steps with no intermediate commits, letting `get_db()` commit the whole unit at request end.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Single-step checkout: one POST `/orders/checkout` validates cart, processes mock payment, creates order, decrements stock, clears cart — all in one call
- No preview/confirm step — the mock payment context makes a single step sufficient
- Mock payment can succeed or fail (not always-approve); support a mechanism for triggering failure (e.g., random ~10% failure rate or a test-friendly trigger like a special field)
- On payment failure: order is not created, stock is not decremented, cart is preserved
- Order gets a status reflecting the payment result
- Cart must not be empty — reject with clear error if no items
- All cart items must have sufficient stock at checkout time (checked within the transaction after `SELECT FOR UPDATE`)
- If any item has insufficient stock: reject the entire order, return which items are short and available quantity
- No partial fulfillment — user must adjust cart and retry
- `SELECT FOR UPDATE` on book stock rows, locked in ascending ID order to prevent deadlocks
- `unit_price` snapshot field on order items (price at time of purchase)

### Claude's Discretion

- Order status model (e.g., PENDING/CONFIRMED/PAYMENT_FAILED or simpler)
- Order confirmation response structure and fields
- Order history pagination, sorting, and detail level
- Admin orders endpoint — filtering, search, pagination approach
- Mock payment implementation details (random vs deterministic trigger)
- Exact error response shapes for checkout failures

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMM-03 | User can checkout cart with mock payment (creates order, decrements stock) | `SELECT FOR UPDATE` with `with_for_update()` in SQLAlchemy async; single-transaction pattern via `get_db()` session; mock payment service pattern |
| COMM-04 | User can view order confirmation after checkout | POST `/orders/checkout` response includes order ID, line items, and total; `unit_price` snapshot on `order_items` |
| COMM-05 | User can view order history with line items | GET `/orders` (paginated user orders); GET `/orders/{id}` (order detail with items); `selectinload` for `Order.items` → `OrderItem.book` |
| ENGM-06 | Admin can view all placed orders | GET `/admin/orders` protected by `AdminUser` dep; same read pattern as user orders with all-user scope |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ^2.0.47 (project) | Async ORM, `SELECT FOR UPDATE` via `with_for_update()`, `selectinload` for relationships | Already in use; 2.x async API used throughout project |
| asyncpg | ^0.31.0 (project) | PostgreSQL async driver | Already in use; handles `FOR UPDATE` natively |
| FastAPI | ^0.133.0 (project) | HTTP routing, dependency injection | Already in use |
| Pydantic v2 | ^2.12.5 (project) | Schema validation and serialization | `model_validate`, `computed_field` used in cart schemas |
| Alembic | ^1.18.4 (project) | Hand-written migrations | Pattern established; must import Order/OrderItem in `alembic/env.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `decimal.Decimal` | stdlib | `unit_price` and `total_price` computation | `Numeric(10,2)` in DB maps to `Decimal` in Python; use `Decimal` throughout, never `float` |
| `enum.StrEnum` | stdlib | Order status enum | Pattern matches `UserRole` StrEnum; use `CONFIRMED` / `PAYMENT_FAILED` |
| `datetime` (UTC) | stdlib | `created_at` timestamps | Use `DateTime(timezone=True)` and `server_default=func.now()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `SELECT FOR UPDATE` (pessimistic locking) | `UPDATE ... WHERE stock >= qty` (optimistic) | Optimistic is fine for high-throughput but returns vague errors; pessimistic fits the "return which items are short" requirement cleanly since we read stock inside the lock |
| `random.random()` for mock payment failure | header/field trigger | Test-friendliness: a `force_fail` boolean field in request body (or special card number) is deterministic and avoids flaky tests; random with a seed also works. Recommend: optional `force_payment_failure: bool = False` field in `CheckoutRequest` |
| Full pagination on order history | simple list | Order history volume per user is small; simple list is fine for v1 — admin endpoint may warrant pagination if needed |

**Installation:** No new packages required. All needed libraries are already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
app/
└── orders/
    ├── __init__.py          # stub already exists — feature files go here
    ├── models.py            # Order, OrderItem, OrderStatus (StrEnum)
    ├── repository.py        # OrderRepository — create, get_by_id, list_for_user, list_all
    ├── schemas.py           # CheckoutRequest, OrderResponse, OrderItemResponse, OrderListResponse
    ├── service.py           # OrderService + MockPaymentService
    └── router.py            # POST /orders/checkout, GET /orders, GET /orders/{id}, GET /admin/orders

alembic/versions/
└── d4e5f6a7b8c9_create_orders_and_order_items.py  # hand-written, chains off b2c3d4e5f6a7

tests/
└── test_orders.py           # integration tests covering COMM-03/04/05/ENGM-06
```

### Pattern 1: SELECT FOR UPDATE — Pessimistic Stock Locking

**What:** Lock all book rows that appear in the cart within the same transaction before reading stock quantities. This prevents concurrent checkouts from reading stale stock and both succeeding when only one can.

**When to use:** Any time you read-then-update in a concurrent environment where reading stale state leads to data corruption (negative stock).

**Deadlock prevention:** Always lock books in ascending `book_id` order. If two concurrent checkouts share some books, both will acquire locks in the same order and one will simply wait rather than deadlock.

```python
# Source: SQLAlchemy 2.x async docs — with_for_update()
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def lock_books_for_update(
    session: AsyncSession,
    book_ids: list[int],  # MUST be sorted ascending — deadlock prevention
) -> list[Book]:
    result = await session.execute(
        select(Book)
        .where(Book.id.in_(book_ids))
        .order_by(Book.id)
        .with_for_update()
    )
    return list(result.scalars().all())
```

**Key constraint:** `with_for_update()` requires the query to run within an active transaction. The project's `get_db()` dependency (in `app/core/deps.py`) opens an `AsyncSession` and commits at the end of the request — so the lock is held for the entire request duration. Do **not** call `session.commit()` mid-request; use `session.flush()` for intermediate persistence steps.

### Pattern 2: Single-Transaction Checkout Orchestration

**What:** The checkout service method orchestrates all steps within one DB session, using `flush()` to persist intermediate state without releasing locks.

```python
# Checkout service — single transaction pattern
async def checkout(self, user_id: int, request: CheckoutRequest) -> Order:
    # 1. Load cart — reject if empty
    cart = await self.cart_repo.get_with_items(user_id)
    if not cart or not cart.items:
        raise AppError(422, "Cart is empty", "ORDER_CART_EMPTY")

    # 2. Lock books in ascending ID order (deadlock prevention)
    book_ids = sorted(item.book_id for item in cart.items)
    books = await self.order_repo.lock_books(book_ids)  # SELECT FOR UPDATE
    book_map = {b.id: b for b in books}

    # 3. Validate stock for ALL items before doing anything
    insufficient = []
    for item in cart.items:
        book = book_map[item.book_id]
        if book.stock_quantity < item.quantity:
            insufficient.append({
                "book_id": item.book_id,
                "requested": item.quantity,
                "available": book.stock_quantity,
            })
    if insufficient:
        raise AppError(
            409,
            "Insufficient stock for one or more items",
            "ORDER_INSUFFICIENT_STOCK",
        )  # attach insufficient list to response — see Schemas section

    # 4. Mock payment
    payment_ok = await self.payment_service.charge(
        force_fail=request.force_payment_failure
    )
    if not payment_ok:
        raise AppError(402, "Payment failed", "ORDER_PAYMENT_FAILED")

    # 5. Create order and items, decrement stock, clear cart — all via flush()
    order = await self.order_repo.create_order(user_id, cart.items, book_map)
    await self.cart_repo.clear_cart(cart)
    return order
```

### Pattern 3: Repository Layer — OrderRepository

Matches project conventions (constructor takes `AsyncSession`, each method is a coroutine, uses `flush()` not `commit()`):

```python
class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_books(self, book_ids: list[int]) -> list[Book]:
        """Lock book rows in ascending ID order — deadlock-safe."""
        result = await self.session.execute(
            select(Book)
            .where(Book.id.in_(book_ids))
            .order_by(Book.id)
            .with_for_update()
        )
        return list(result.scalars().all())

    async def create_order(
        self,
        user_id: int,
        cart_items: list[CartItem],
        book_map: dict[int, Book],
    ) -> Order:
        order = Order(user_id=user_id, status=OrderStatus.CONFIRMED)
        self.session.add(order)
        await self.session.flush()  # get order.id

        for item in cart_items:
            book = book_map[item.book_id]
            oi = OrderItem(
                order_id=order.id,
                book_id=item.book_id,
                quantity=item.quantity,
                unit_price=book.price,  # snapshot at time of purchase
            )
            self.session.add(oi)
            book.stock_quantity -= item.quantity  # decrement stock in-place

        await self.session.flush()
        return order

    async def get_by_id_for_user(
        self, order_id: int, user_id: int
    ) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(selectinload(Order.items).selectinload(OrderItem.book))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .options(selectinload(Order.items).selectinload(OrderItem.book))
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .options(selectinload(Order.items).selectinload(OrderItem.book))
        )
        return list(result.scalars().all())
```

### Pattern 4: Models — Order and OrderItem

```python
# app/orders/models.py
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(enum.StrEnum):
    CONFIRMED = "confirmed"
    PAYMENT_FAILED = "payment_failed"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="orderstatus"),
        nullable=False,
        default=OrderStatus.CONFIRMED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="SET NULL"),  # preserve history if book deleted
        nullable=True,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    book: Mapped["Book | None"] = relationship()  # TYPE_CHECKING guard if circular
```

**Note on `book_id` nullable:** Using `ondelete="SET NULL"` and `nullable=True` for `book_id` on `order_items` means order history is preserved even if the admin later deletes a book from the catalog. The `unit_price` snapshot ensures totals remain accurate. This is the standard e-commerce pattern.

### Pattern 5: Cart Clear on Checkout

The checkout service must delete all cart items and optionally the cart row itself. The simplest approach matching existing patterns:

```python
# In CartRepository (add method) or inline in checkout service
async def clear_cart(self, cart: Cart) -> None:
    """Delete all items in the cart. Cart row itself remains (empty cart)."""
    for item in cart.items:
        await self.session.delete(item)
    await self.session.flush()
```

Since `Cart.items` has `cascade="all, delete-orphan"`, deleting the Cart row itself would also delete items. But keeping the Cart row is cleaner (no need to re-create it on next add-to-cart). Either approach works; keeping the row is consistent with the Phase 6 pattern of `get_or_create`.

### Pattern 6: Mock Payment Service

```python
import random

class MockPaymentService:
    """Mock payment — always called, can succeed or fail."""

    async def charge(self, *, force_fail: bool = False) -> bool:
        """Return True (payment OK) or False (payment declined).

        force_fail=True allows tests to deterministically trigger failure.
        Otherwise, ~10% random failure rate simulates real-world declines.
        """
        if force_fail:
            return False
        return random.random() > 0.10  # 90% success rate
```

### Pattern 7: Router Pattern — matches existing cart/books routers

```python
# app/orders/router.py
router = APIRouter(prefix="/orders", tags=["orders"])

def _make_service(db: DbSession) -> OrderService:
    return OrderService(
        order_repo=OrderRepository(db),
        cart_repo=CartRepository(db),
        payment_service=MockPaymentService(),
    )

@router.post("/checkout", response_model=OrderResponse, status_code=201)
async def checkout(body: CheckoutRequest, db: DbSession, current_user: CurrentUser):
    user_id = int(current_user["sub"])
    service = _make_service(db)
    return await service.checkout(user_id, body)

@router.get("", response_model=list[OrderResponse])
async def list_orders(db: DbSession, current_user: CurrentUser):
    user_id = int(current_user["sub"])
    service = _make_service(db)
    return await service.list_for_user(user_id)

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: DbSession, current_user: CurrentUser):
    user_id = int(current_user["sub"])
    service = _make_service(db)
    return await service.get_order(user_id, order_id)

# Admin endpoint — separate router or prefix trick
admin_router = APIRouter(prefix="/admin/orders", tags=["admin"])

@admin_router.get("", response_model=list[OrderResponse])
async def admin_list_orders(db: DbSession, _: AdminUser):
    service = _make_service(db)
    return await service.list_all()
```

Register both routers in `app/main.py`:
```python
from app.orders.router import admin_router as orders_admin_router
from app.orders.router import router as orders_router
application.include_router(orders_router)
application.include_router(orders_admin_router)
```

### Anti-Patterns to Avoid

- **Committing mid-checkout:** Never call `session.commit()` inside the checkout service. The `get_db()` dependency owns the commit boundary. Calling commit early releases the `FOR UPDATE` locks before the transaction is complete.
- **Locking in arbitrary order:** Always sort `book_ids` ascending before issuing `SELECT FOR UPDATE`. Two concurrent checkouts with overlapping books will deadlock if one locks book 5 then book 3 while the other locks book 3 then book 5.
- **Floating-point for money:** `unit_price` and `total_price` must use `Decimal`, not `float`. `Numeric(10,2)` in PostgreSQL maps to `Decimal` via SQLAlchemy. Never do `float(price) * quantity`.
- **N+1 on order history:** Always use `selectinload(Order.items).selectinload(OrderItem.book)` when returning orders with items. The project uses `selectinload` consistently for async (not `joinedload`).
- **Forgetting alembic/env.py import:** New `Order` and `OrderItem` models must be imported in `alembic/env.py` alongside existing model imports for Alembic autogenerate to detect them.
- **MissingGreenlet on book relationship in OrderItem:** If the `book` relationship on `OrderItem` is accessed after the session yields, use `selectinload` or `session.refresh(item, ["book"])` immediately after flush — same pattern as `CartItem`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Row-level locking | Custom advisory lock or application-level mutex | `select(...).with_for_update()` | SQLAlchemy wraps `SELECT ... FOR UPDATE` natively; advisory locks add complexity without benefit for row-level contention |
| Price snapshot | Querying current book price at order display time | `unit_price` column on `order_items` | Price can change after purchase; snapshot is the only correct approach for order history accuracy |
| Atomic stock decrement | Separate UPDATE statement after creating order | Inline `book.stock_quantity -= quantity` within the same locked transaction | Inline decrement within the locked session is the safe pattern; a separate UPDATE outside the lock creates a TOCTOU window |
| Cart clear | Complex cascade logic | Delete cart items directly (or delete Cart row which cascades) | SQLAlchemy `cascade="all, delete-orphan"` handles the rest |

**Key insight:** The entire correctness of checkout rests on the `FOR UPDATE` lock being held for the full duration of stock validation + order creation + stock decrement. Never release the lock between steps.

## Common Pitfalls

### Pitfall 1: Deadlock from Unordered Lock Acquisition

**What goes wrong:** Two concurrent checkout requests lock the same books in different orders, causing PostgreSQL deadlock and one request receiving a `DeadlockDetectedError`.

**Why it happens:** Request A processes cart [book 7, book 3] and locks book 7 first. Request B processes cart [book 3, book 7] and locks book 3 first. Both then wait for the other's lock — deadlock.

**How to avoid:** Sort `book_ids` ascending before issuing `SELECT FOR UPDATE`. Both requests will then attempt to lock book 3 first, then book 7. One wins the lock on book 3 and proceeds; the other waits. No deadlock.

**Warning signs:** `asyncpg.exceptions.DeadlockDetectedError` in logs during concurrent checkout load tests.

### Pitfall 2: Stock Check Race Condition Without FOR UPDATE

**What goes wrong:** Two checkout requests for the same book (stock=1) both read stock=1, both pass validation, both create orders, and stock goes to -1 (violating the DB constraint, or silently going negative if constraint is missing).

**Why it happens:** Reading stock without locking allows another transaction to modify it between your read and your write.

**How to avoid:** `SELECT FOR UPDATE` ensures no other transaction can modify the row between your read and your decrement. The DB `CHECK CONSTRAINT ck_books_stock_non_negative` (already exists on `books` table) is a last-resort safety net, but the `FOR UPDATE` is the correct primary defense.

**Warning signs:** Orders created with negative stock quantities, or `CheckConstraintViolation` from asyncpg on the `ck_books_stock_non_negative` constraint.

### Pitfall 3: Accessing Relationships Outside Session Scope

**What goes wrong:** `MissingGreenlet` or `DetachedInstanceError` when accessing `order.items` or `item.book` after the session closes.

**Why it happens:** SQLAlchemy async does not allow lazy loading. Relationships must be eagerly loaded with `selectinload` or explicitly refreshed with `session.refresh(obj, ["attr"])` while the session is open.

**How to avoid:** Always use `selectinload(Order.items).selectinload(OrderItem.book)` when fetching orders for response serialization. For the checkout path (after `create_order`), either use `selectinload` on the create query or `session.refresh(order, ["items"])` after flush.

**Warning signs:** `MissingGreenlet` exception in route handlers that access order relationships.

### Pitfall 4: Payment Failure Leaving Partial State

**What goes wrong:** If payment is called after stock is decremented (wrong order), a payment failure requires rolling back the stock decrement. If this rollback is missed, stock is permanently reduced without an order.

**How to avoid:** Call `MockPaymentService.charge()` BEFORE decrementing stock or creating order rows. If payment fails, raise `AppError` immediately — the `get_db()` dependency's `except` branch rolls back the session, so no state is committed.

**Correct order of operations:**
1. Lock books (`SELECT FOR UPDATE`)
2. Validate stock
3. Call payment — if fails, raise AppError here (session rolled back, nothing committed)
4. Create order + items
5. Decrement stock
6. Clear cart
7. Return (get_db commits)

**Warning signs:** Stock goes negative after payment failures, or orders created without payment.

### Pitfall 5: Forgetting to Register Models in alembic/env.py

**What goes wrong:** `alembic revision --autogenerate` does not detect `orders` or `order_items` tables. Running the migration creates no tables, and the app crashes at runtime with `UndefinedTableError`.

**How to avoid:** Add `from app.orders.models import Order, OrderItem  # noqa: F401` to `alembic/env.py` (line 9-10 area, alongside existing model imports).

**Warning signs:** `alembic revision --autogenerate` produces an empty migration body.

### Pitfall 6: `with_for_update()` Outside Transaction Context

**What goes wrong:** `SELECT FOR UPDATE` in PostgreSQL requires an active transaction. In autocommit mode or outside a transaction block, the lock is released immediately after the statement, providing no protection.

**Why it happens:** SQLAlchemy async sessions with `autocommit=False` (the project's setting) already wrap statements in a transaction, so this is a non-issue in normal use. But it becomes a problem if someone uses `with engine.connect()` (autocommit by default in SA2) instead of the session.

**How to avoid:** Always issue `SELECT FOR UPDATE` through the `AsyncSession` (not a raw connection), which is what the repository pattern enforces. The existing `get_db()` session has `autocommit=False`.

## Code Examples

Verified patterns from project codebase and SQLAlchemy 2.x:

### Migration — orders and order_items (hand-written, not autogenerated)

```python
# alembic/versions/d4e5f6a7b8c9_create_orders_and_order_items.py
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "b2c3d4e5f6a7"  # chains off cart migration

def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("confirmed", "payment_failed", name="orderstatus"),
            nullable=False,
            server_default="confirmed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_book_id", "order_items", ["book_id"])

def downgrade() -> None:
    op.drop_index("ix_order_items_book_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_user_id", table_name="orders")
    # Drop enum type manually in PostgreSQL
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.drop_table("orders")
```

**Important:** PostgreSQL creates a named `ENUM` type (`orderstatus`) when using `sa.Enum` with a name. The `downgrade()` must explicitly drop it with `op.execute("DROP TYPE IF EXISTS orderstatus")`.

### SELECT FOR UPDATE — verified SQLAlchemy 2.x async pattern

```python
# Locks book rows for the duration of the current transaction
result = await session.execute(
    select(Book)
    .where(Book.id.in_(sorted_book_ids))
    .order_by(Book.id)          # ascending — deadlock prevention
    .with_for_update()          # issues SELECT ... FOR UPDATE in PostgreSQL
)
books = list(result.scalars().all())
```

### Pydantic Schema — Insufficient Stock Error Body

The `AppError` exception class carries one `detail` string. For rich error bodies (listing which items are short), the service should raise `AppError` with a formatted detail string, or the router can catch a custom exception and return a structured response. The simplest approach matching the project pattern:

```python
# In service — build detail message with items
if insufficient:
    detail_parts = [
        f"book_id={i['book_id']} (requested {i['requested']}, available {i['available']})"
        for i in insufficient
    ]
    raise AppError(
        409,
        f"Insufficient stock: {'; '.join(detail_parts)}",
        "ORDER_INSUFFICIENT_STOCK",
    )
```

Alternatively, encode the list as JSON in the detail string, or create a custom response shape. The planner should decide; the simple string approach is lowest friction with the existing `AppError` pattern.

### Checkout Request Schema

```python
class CheckoutRequest(BaseModel):
    """Request body for POST /orders/checkout.

    force_payment_failure: test-friendly trigger to simulate payment decline.
    """
    force_payment_failure: bool = False
```

### Order Response Schemas

```python
class OrderItemResponse(BaseModel):
    id: int
    book_id: int | None
    quantity: int
    unit_price: Decimal
    book: BookSummary | None  # None if book deleted from catalog

    model_config = {"from_attributes": True}

class OrderResponse(BaseModel):
    id: int
    status: str
    created_at: datetime
    items: list[OrderItemResponse]

    @computed_field
    @property
    def total_price(self) -> Decimal:
        return sum(i.unit_price * i.quantity for i in self.items) or Decimal("0")

    model_config = {"from_attributes": True}
```

### Test Pattern — Concurrent Checkout (Race Condition Verification)

```python
# Success criterion 3: concurrent checkouts don't result in negative stock
import asyncio

async def test_concurrent_checkout_race_condition_safe(client, admin_headers, user_headers, user2_headers):
    # Setup: book with stock=1, both users have it in cart
    ...
    results = await asyncio.gather(
        client.post("/orders/checkout", headers=user_headers, json={}),
        client.post("/orders/checkout", headers=user2_headers, json={}),
        return_exceptions=True,
    )
    statuses = [r.status_code for r in results if hasattr(r, 'status_code')]
    # Exactly one should succeed (201), one should fail (409 or 402)
    assert statuses.count(201) == 1
    assert statuses.count(409) == 1 or statuses.count(402) == 1
    # Book stock must be 0, not negative
    book_resp = await client.get(f"/books/{book_id}")
    assert book_resp.json()["stock_quantity"] == 0
```

**Note:** The existing conftest uses function-scoped `db_session` with rollback. Concurrent tests require two independent HTTP clients or careful fixture design. Consider using `asyncio.gather` with the shared `client` fixture — the underlying DB sessions are managed by FastAPI's `get_db()` dependency (not the test's `db_session`), so concurrent requests DO use separate DB sessions, which is correct for testing the locking behavior.

**However**, rollback-based test isolation will roll back after each test. The concurrent test must create all state in a way that survives the concurrent request lifecycle. This may require flushing/committing fixture data to the DB before the concurrent calls — the existing `db_session` rollback approach may not work cleanly for concurrency tests. Recommend using `asyncio.gather` with a `client` fixture that has data committed (not just flushed) before the concurrent requests.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy `session.execute(stmt.with_for_update())` — sync | `await session.execute(stmt.with_for_update())` — async SA2 | SQLAlchemy 2.0 | Direct `await` instead of greenlet magic |
| `joinedload` for async relationships | `selectinload` for async | SA 1.4+ recommendation for async | `selectinload` issues a second SELECT, avoiding join complexity and the "greenlet" async loading issue |
| `Enum` stored as VARCHAR | Named PostgreSQL ENUM type via `sa.Enum(name=...)` | Always | Named ENUM requires explicit `DROP TYPE` in downgrade |

**Deprecated/outdated:**
- `joinedload` in async contexts: still works but `selectinload` is the recommended async pattern in this project (established in Phase 6, cart repository uses `selectinload`)
- Autogenerated migrations: project hand-writes migrations for all new tables (established in Phase 4 onwards)

## Open Questions

1. **Concurrent test isolation with rollback-based fixtures**
   - What we know: `db_session` fixture rolls back after each test; concurrent HTTP requests use FastAPI's own `get_db()` sessions (separate from test fixture session)
   - What's unclear: Can fixture-created data (flushed but not committed) be seen by concurrent HTTP requests? Answer: No — asyncpg uses transaction isolation; flushed-but-not-committed data is invisible to other sessions. The concurrent test will need data committed to DB before testing concurrency.
   - Recommendation: For the race condition test, commit fixture data (not just flush) OR use a test that creates all state via HTTP calls (which do commit via `get_db()`), then `asyncio.gather` the concurrent checkout calls.

2. **Order status enum name conflicts**
   - What we know: `UserRole` uses `SAEnum(UserRole, name="userrole")` — the name must match what's in PostgreSQL
   - What's unclear: If `orderstatus` enum already exists in the DB from a failed migration, re-running upgrade will fail
   - Recommendation: Use `create_type=False` in downgrade after verifying the name; or use `checkfirst=True` in upgrade. Standard hand-written migration with `IF NOT EXISTS` avoids this.

3. **Admin orders endpoint prefix**
   - What we know: Existing routes use `/books`, `/cart`, `/auth` (no `/admin` prefix for most). Admin-only catalog endpoints use `AdminUser` dep but same prefix.
   - What's unclear: Should admin orders be at `/admin/orders` (separate router) or `/orders/admin` (same router with admin dep)?
   - Recommendation: `/admin/orders` matches the CONTEXT.md spec. Use a separate `APIRouter(prefix="/admin/orders")` registered in `main.py` independently, keeping concerns clean.

## Validation Architecture

*(nyquist_validation not found in config.json — `workflow` keys are `research`, `plan_check`, `verifier`. Treating as disabled. Skipping automated Nyquist section.)*

However, for planning awareness, the test infrastructure is:

- **Framework:** pytest 9.x + pytest-asyncio 1.3.x, `asyncio_mode = auto`, `testpaths = ["tests"]`
- **Quick run:** `poetry run task test` (runs full suite, ~30s based on history)
- **Test file to create:** `tests/test_orders.py`
- **Existing conftest:** `tests/conftest.py` — provides `test_engine`, `db_session`, `client` fixtures; no changes needed
- **Pattern:** Module-specific email prefixes (e.g., `orders_admin@example.com`, `orders_user@example.com`) to avoid collision with other test modules

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Suggested Test Name |
|--------|----------|-----------|---------------------|
| COMM-03 | Checkout creates order, decrements stock, clears cart | integration | `test_checkout_success_creates_order_and_decrements_stock` |
| COMM-03 | Checkout with empty cart returns 422 | integration | `test_checkout_empty_cart_rejected` |
| COMM-03 | Checkout with insufficient stock returns 409 | integration | `test_checkout_insufficient_stock_rejected` |
| COMM-03 | Payment failure preserves cart, no order created | integration | `test_checkout_payment_failure_preserves_cart` |
| COMM-03 | Concurrent checkout for stock=1 book — only one succeeds | integration | `test_checkout_concurrent_race_condition_safe` |
| COMM-04 | Checkout response includes order ID, line items, total | integration | `test_checkout_response_structure` |
| COMM-04 | unit_price in response matches book price at time of order | integration | `test_checkout_unit_price_snapshot` |
| COMM-05 | User can list their orders | integration | `test_list_orders_for_user` |
| COMM-05 | User cannot see other users' orders | integration | `test_list_orders_user_isolation` |
| COMM-05 | GET /orders/{id} returns order with line items | integration | `test_get_order_detail` |
| COMM-05 | GET /orders/{id} returns 404 for nonexistent or other user's order | integration | `test_get_order_not_found_or_forbidden` |
| ENGM-06 | Admin can view all orders | integration | `test_admin_list_all_orders` |
| ENGM-06 | Non-admin cannot access admin orders endpoint | integration | `test_admin_orders_requires_admin` |

## Sources

### Primary (HIGH confidence)

- Project codebase (`app/cart/`, `app/books/`, `app/core/`, `alembic/`) — direct read; established patterns confirmed
- `pyproject.toml` — exact library versions confirmed
- `tests/conftest.py` — test infrastructure confirmed; `asyncio_mode = auto`, `db_session` rollback pattern
- `.planning/phases/07-orders/07-CONTEXT.md` — locked decisions confirmed
- `.planning/STATE.md` — accumulated architectural decisions confirmed (Phase 06 patterns directly applicable)

### Secondary (MEDIUM confidence)

- SQLAlchemy 2.x async docs — `with_for_update()` usage confirmed via pattern matching with project's existing `select(...).where(...).options(selectinload(...))` style
- PostgreSQL `SELECT FOR UPDATE` behavior (ascending-order deadlock prevention) — established database concurrency theory, widely documented

### Tertiary (LOW confidence)

- Race condition test with `asyncio.gather` against rollback-isolated sessions: behavior depends on asyncpg transaction isolation interaction with the `db_session` fixture. Flagged as Open Question 1.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all patterns already used in project
- Architecture: HIGH — directly mirrors cart and books domain structure
- Pitfalls: HIGH for locking/deadlock (well-established PostgreSQL concurrency); MEDIUM for race condition test isolation (depends on asyncpg/pytest-asyncio interaction not directly verified)

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable stack — SQLAlchemy, FastAPI, asyncpg versions locked in pyproject.toml)
