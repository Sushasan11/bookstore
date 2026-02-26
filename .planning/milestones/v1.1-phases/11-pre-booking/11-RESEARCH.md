# Phase 11: Pre-booking - Research

**Researched:** 2026-02-26
**Domain:** SQLAlchemy async ORM, FastAPI service layer, soft-delete status enum, bulk UPDATE, cross-service transaction coordination
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Reservation behavior:**
- Pre-booking is ONLY allowed when book stock_quantity == 0; reject with 409 if stock > 0 ("Book is in stock — add to cart instead")
- Duplicate pre-booking for the same book by the same user is rejected (one active pre-booking per user per book)
- Cancellation is non-permanent: a user who cancels can re-reserve the same book (new pre-booking record) as long as the book is still out of stock
- Status update only on restock — no auto-add to cart; user must manually add to cart after being notified

**Restock notification flow:**
- Notify ALL waiting pre-bookers when stock transitions from 0 to >0 (not limited to stock quantity; first-come-first-served at cart/checkout)
- Restock trigger fires ONLY on 0→>0 transition; adding stock to an already-in-stock book does nothing to pre-bookings
- Status transition (waiting → notified with notified_at timestamp) happens atomically in the SAME DB transaction as the stock update
- Once notified is final: subsequent restocks do NOT re-notify already-notified pre-bookings; only 'waiting' status transitions

**From STATE.md v1.1 planning:**
- Pre-booking cancel: soft delete (status=CANCELLED) for audit trail
- BookService.update_stock() calls PreBookRepository.notify_waiting_by_book() in the same transaction, returns email list to router for background task enqueueing (avoids circular imports)

**From CONTEXT.md specifics:**
- BookService.update_stock() calls PreBookRepository.notify_waiting_by_book() in the same transaction, returns email list to router for background task enqueueing

### Claude's Discretion

- Max pre-bookings per user limit (if any) — Claude picks a reasonable approach
- Pre-booking list sorting and detail level
- Cancellation soft-delete implementation details (status field values, timestamps)
- Whether cancelled pre-bookings appear in the user's list or are filtered out by default

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRBK-01 | User can reserve (pre-book) an out-of-stock book | PreBookService.create() with stock check + duplicate guard; 409 on in-stock book |
| PRBK-02 | User can view their list of pre-booked books | GET /prebooks endpoint, PreBookRepository.list_for_user(), selectinload book relationship |
| PRBK-03 | User can cancel a pre-booking | PATCH /prebooks/{id}/cancel, soft-delete via status=CANCELLED + cancelled_at timestamp |
| PRBK-04 | Pre-booking is rejected with 409 when the book is currently in stock | stock_quantity > 0 guard in service before insert, AppError(409, "PREBOOK_BOOK_IN_STOCK") |
| PRBK-05 | Pre-booking records track status (waiting → notified → cancelled) with notified_at timestamp | PreBookStatus enum + notified_at + cancelled_at columns on model |
| PRBK-06 | When admin restocks a book, all waiting pre-bookers are notified simultaneously (broadcast) | BookService.update_stock() extended: old_qty==0 guard, PreBookRepository.notify_waiting_by_book() bulk UPDATE in same transaction, returns user email list |
</phase_requirements>

---

## Summary

Phase 11 adds the pre-booking feature: a user can reserve an out-of-stock book, view their reservations, and cancel them. The dominant complexity is the restock broadcast (PRBK-06): when an admin sets stock from 0 to any positive value, all pre-bookings in "waiting" status must atomically transition to "notified" inside the same DB transaction, and the resulting email addresses must be returned to the router for background task enqueueing (so emails fire after commit, not inside the transaction).

The data model is a `pre_bookings` table with a status enum (waiting/notified/cancelled), a nullable `notified_at` timestamp, and a nullable `cancelled_at` timestamp. A partial unique index on `(user_id, book_id)` WHERE status = 'waiting' enforces the "one active pre-booking per user per book" rule without blocking re-reservation after cancellation. This is the key design insight: the uniqueness constraint must be conditional, not global.

The restock wiring follows the pattern locked in STATE.md: `BookService.update_stock()` is extended to accept an optional `PreBookRepository` argument and call `notify_waiting_by_book()` atomically. The router receives back the email list and enqueues background tasks using the existing `EmailService.enqueue()` pattern (Phase 9 infrastructure). No new libraries are needed — this phase is pure data model + business logic using the existing stack.

**Primary recommendation:** Implement the partial unique index as a PostgreSQL conditional index (WHERE status = 'waiting') — this is the only clean way to satisfy "one active per user/book" while allowing re-reservation after cancellation.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async ORM | 2.0.47 (project) | Model, repository, bulk UPDATE | Already in use; `update()` with `WHERE` clause handles the atomic broadcast |
| FastAPI | 0.133.0 (project) | Router + dependency injection | Already in use |
| Pydantic v2 | 2.12.5 (project) | Request/response schemas | Already in use |
| Alembic | 1.18.4 (project) | Migration for `pre_bookings` table | Already in use |
| fastapi-mail | >=1.6,<2 (project) | Email dispatch post-commit | Already in use (Phase 9 infrastructure) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `enum.StrEnum` | stdlib | PreBookStatus enum (waiting/notified/cancelled) | Already used for OrderStatus and UserRole |
| SQLAlchemy `update()` core expression | 2.0 | Atomic bulk status transition in notify_waiting_by_book | Needed for broadcast UPDATE without loading all rows |
| SQLAlchemy `returning()` | 2.0 | Return user_ids (or emails via JOIN) from bulk UPDATE | Needed so router gets email list without a second query |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Partial unique index (WHERE status='waiting') | Global unique index on (user_id, book_id) | Global blocks re-reservation after cancellation — does not meet locked decision |
| `update().returning()` for email list | Load rows first, then update | Two round-trips vs one; locking risks; decided to use single bulk UPDATE |
| SAEnum for status | String column with CHECK CONSTRAINT | SAEnum already used for OrderStatus/UserRole — consistent |

**Installation:** No new packages needed. All dependencies are already in pyproject.toml.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── prebooks/
│   ├── __init__.py        # Already exists (stub)
│   ├── models.py          # PreBooking model, PreBookStatus enum
│   ├── repository.py      # PreBookRepository (add, list, cancel, notify_waiting_by_book)
│   ├── schemas.py         # PreBookResponse, PreBookListResponse
│   ├── service.py         # PreBookService (create, list, cancel)
│   └── router.py          # /prebooks endpoints
alembic/versions/
└── {hash}_create_pre_bookings.py   # New migration
```

`BookService` in `app/books/service.py` gets a modified `update_stock()` / new `set_stock_and_notify()` method that calls `PreBookRepository.notify_waiting_by_book()`.

### Pattern 1: PreBooking Model with Status Enum

**What:** SQLAlchemy mapped class using `StrEnum` for status, nullable timestamps for notified_at and cancelled_at. No relationship back to User needed for this phase (only user_id FK needed).

**When to use:** Any feature with a finite status lifecycle and audit timestamps.

```python
# Source: project patterns (app/orders/models.py, app/users/models.py)
import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.books.models import Book


class PreBookStatus(enum.StrEnum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    CANCELLED = "cancelled"


class PreBooking(Base):
    __tablename__ = "pre_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[PreBookStatus] = mapped_column(
        SAEnum(PreBookStatus, name="prebookstatus"),
        nullable=False,
        default=PreBookStatus.WAITING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    book: Mapped[Book] = relationship()
```

### Pattern 2: Partial Unique Index (Conditional Uniqueness)

**What:** PostgreSQL conditional index enforcing one active pre-booking per (user, book) without blocking re-reservation after cancellation.

**When to use:** Any "one active record per key" constraint where records can be soft-deleted but the same key can re-appear.

```python
# Source: PostgreSQL partial index docs, SQLAlchemy Index with postgresql_where
from sqlalchemy import Index, text

# In __table_args__:
__table_args__ = (
    Index(
        "uq_pre_bookings_user_book_waiting",
        "user_id",
        "book_id",
        unique=True,
        postgresql_where=text("status = 'waiting'"),
    ),
)
```

This allows:
- User creates pre-booking (status=waiting) → unique index prevents duplicate → PASS
- User cancels (status=cancelled) → index no longer covers this row
- User re-books (new row, status=waiting) → unique index allows it because previous row is excluded

### Pattern 3: Bulk UPDATE with RETURNING for Atomic Broadcast

**What:** `notify_waiting_by_book()` issues a single `UPDATE pre_bookings SET status='notified', notified_at=now() WHERE book_id=X AND status='waiting' RETURNING user_id`. Returns list of user IDs. Router then resolves emails or uses user_id to enqueue.

**When to use:** Broadcast mutation affecting 0..N rows atomically; caller needs to know which rows were updated.

```python
# Source: project patterns (app/users/repository.py revoke_all_for_user), SQLAlchemy 2.0 docs
from datetime import UTC, datetime

from sqlalchemy import update

async def notify_waiting_by_book(self, book_id: int) -> list[int]:
    """Transition all waiting pre-bookings for a book to notified.

    Returns list of user_ids for email dispatch.
    Called inside the same transaction as the stock update.
    """
    result = await self.session.execute(
        update(PreBooking)
        .where(
            PreBooking.book_id == book_id,
            PreBooking.status == PreBookStatus.WAITING,
        )
        .values(
            status=PreBookStatus.NOTIFIED,
            notified_at=datetime.now(UTC),
        )
        .returning(PreBooking.user_id)
    )
    return list(result.scalars().all())
```

**Important:** `update().returning()` in SQLAlchemy 2.0 async requires calling `result.scalars().all()` — the same pattern as a SELECT.

### Pattern 4: BookService.update_stock() Cross-Service Extension

**What:** `BookService.set_stock()` is extended to accept `PreBookRepository` and return email addresses for background dispatch. The 0→>0 transition check happens here.

**When to use:** When one service must call another repository in the same transaction, with a result passed back to the router.

```python
# Source: STATE.md locked decision — BookService.update_stock() calls
# PreBookRepository.notify_waiting_by_book() in same transaction, returns email list

# In BookService:
async def set_stock_and_notify(
    self,
    book_id: int,
    quantity: int,
    prebook_repo: "PreBookRepository",
) -> tuple[Book, list[int]]:
    """Set stock and notify waiting pre-bookers if transitioning 0→>0.

    Returns (book, notified_user_ids).
    Caller (router) resolves user emails and enqueues background tasks.
    """
    book = await self._get_book_or_404(book_id)
    old_qty = book.stock_quantity
    book.stock_quantity = quantity
    await self.book_repo.session.flush()

    notified_user_ids: list[int] = []
    if old_qty == 0 and quantity > 0:
        notified_user_ids = await prebook_repo.notify_waiting_by_book(book_id)

    return book, notified_user_ids
```

**Router wiring (PATCH /books/{id}/stock):**

```python
# Router receives user_ids, fetches emails if needed, enqueues per-user background task
# Phase 12 wires the actual email send — Phase 11 only returns the user_id list
```

**Note on circular imports:** `BookService` does NOT import `PreBookRepository` at module level. The router imports both and passes `PreBookRepository(db)` as an argument. This is the locked pattern from STATE.md.

### Pattern 5: Soft-Delete Cancel

**What:** Cancellation sets `status=CANCELLED` and `cancelled_at=now()`. The pre-booking record is preserved for audit. The partial unique index automatically allows a new pre-booking for the same user/book once the old one is cancelled.

**When to use:** Any "cancel but keep for audit" requirement.

```python
# In PreBookRepository:
async def cancel(self, prebook: PreBooking) -> PreBooking:
    """Soft-delete: set status=CANCELLED with cancelled_at timestamp."""
    prebook.status = PreBookStatus.CANCELLED
    prebook.cancelled_at = datetime.now(UTC)
    await self.session.flush()
    return prebook
```

### Pattern 6: Router Structure

```python
router = APIRouter(prefix="/prebooks", tags=["prebooks"])

# POST /prebooks — PRBK-01, PRBK-04: create pre-booking (rejects in-stock books)
# GET /prebooks — PRBK-02: list user's pre-bookings
# DELETE /prebooks/{id} — PRBK-03: cancel pre-booking (soft-delete to CANCELLED)
```

The `PATCH /books/{id}/stock` endpoint in the books router handles PRBK-06 as a side effect.

### Anti-Patterns to Avoid

- **Global unique index on (user_id, book_id):** Blocks re-reservation after cancellation. Use the partial unique index (WHERE status = 'waiting') instead.
- **Email send inside the DB transaction:** Phase 9 decision — always enqueue via BackgroundTasks after commit. Router receives user_ids from the transaction, then resolves email and enqueues after the session commits.
- **Loading all waiting rows before updating:** Use bulk `UPDATE ... WHERE ... RETURNING user_id` — one round-trip instead of N. Avoids memory issues with large pre-booking lists.
- **Importing PreBookRepository in books/service.py at module level:** Creates circular import. Pass prebook_repo as a parameter from the router.
- **Re-notifying already-notified pre-bookings:** Only `status='waiting'` rows are targeted by the UPDATE. `status='notified'` rows are unaffected on subsequent restocks (locked decision).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conditional uniqueness | Custom pre-insert duplicate check | PostgreSQL partial unique index (WHERE status='waiting') | Race condition in custom check; DB constraint is atomic |
| Atomic bulk transition | Load rows → loop → update each | `UPDATE ... WHERE ... RETURNING` | N+1 writes vs 1; not atomic under concurrent stock updates |
| Post-commit email dispatch | Thread.start() or asyncio.create_task() | BackgroundTasks (already wired, Phase 9) | BackgroundTasks runs after response/commit by FastAPI design |
| Status machine | If/else chains on string columns | Python StrEnum + SAEnum | Type safety, migration-friendly, matches project pattern |

**Key insight:** The partial unique index is the single most important implementation detail in this phase. Without it, re-reservation after cancellation requires either ugly soft-delete workarounds or application-level duplicate logic that has a race window.

---

## Common Pitfalls

### Pitfall 1: Global Unique Constraint Blocks Re-Reservation

**What goes wrong:** If `UNIQUE(user_id, book_id)` is applied globally (no WHERE clause), a user who cancels and tries to re-book the same out-of-stock book gets a 409 on the second attempt because the cancelled row still exists.

**Why it happens:** The uniqueness check sees the old (cancelled) row and rejects the new insert.

**How to avoid:** Use a conditional index: `CREATE UNIQUE INDEX uq_pre_bookings_user_book_waiting ON pre_bookings (user_id, book_id) WHERE status = 'waiting'`. SQLAlchemy exposes this via `Index(..., postgresql_where=text("status = 'waiting'"))`.

**Warning signs:** Test "cancel then re-book" fails with 409 or IntegrityError.

### Pitfall 2: Restock Trigger Fires on Already-In-Stock Books

**What goes wrong:** Admin sets stock from 50 → 100. All waiting pre-bookers get notified even though the book was never out of stock for them.

**Why it happens:** The service checks `quantity > 0` but not the PREVIOUS stock level.

**How to avoid:** Check BOTH `old_qty == 0 AND quantity > 0` before calling `notify_waiting_by_book()`. Load the book BEFORE updating, read `book.stock_quantity`, then set the new value, then conditionally notify.

**Warning signs:** Pre-bookers receive spurious notifications when admin tops up in-stock inventory.

### Pitfall 3: Email Sent Inside DB Transaction

**What goes wrong:** Email fires even if the DB transaction rolls back (e.g., due to a later error). Pre-bookers get "restocked!" emails but the stock update never committed.

**Why it happens:** Calling email send inside the service method rather than returning the email list to the router.

**How to avoid:** Follow the locked STATE.md pattern: service returns `(book, notified_user_ids)`. Router fetches user emails and enqueues `background_tasks.add_task(...)` AFTER the service call returns. BackgroundTasks execute after the response is sent, which is after `get_db` commits.

**Warning signs:** Email tests that inject failures after notify_waiting_by_book still trigger email sends.

### Pitfall 4: Duplicate Pre-booking Detection Race

**What goes wrong:** Two concurrent POST /prebooks requests for the same (user, book) both pass the "is there an existing waiting pre-booking?" service-level check (both see no row), then both insert, causing a duplicate.

**Why it happens:** Read-then-insert without a DB constraint is not atomic.

**How to avoid:** Rely on the partial unique index as the final arbiter. Catch `IntegrityError` in the repository's `add()` method and re-raise as `AppError(409, "PREBOOK_DUPLICATE", ...)` — same pattern as `WishlistRepository.add()`.

**Warning signs:** Concurrent requests create two pre-bookings for the same user/book.

### Pitfall 5: Mixing `update()` and `session.flush()` Without RETURNING

**What goes wrong:** `notify_waiting_by_book()` uses `update()` without `returning()`, then runs a SELECT to get the user_ids. Between the UPDATE and SELECT, the rows have already been modified, but the SELECT returns them correctly. However this is two round-trips and adds no transaction risk since it's within the same session.

**Why it happens:** Developer doesn't know SQLAlchemy 2.0 supports `update().returning()`.

**How to avoid:** Use `.returning(PreBooking.user_id)` on the update statement. One round-trip, same result.

### Pitfall 6: `expire_on_commit=False` Interaction

**What goes wrong:** After `session.flush()` in `notify_waiting_by_book()`, accessing attributes on loaded `PreBooking` objects causes a `MissingGreenlet` error in async context (SQLAlchemy tries to lazy-load).

**Why it happens:** The async session has `expire_on_commit=False` (project-wide decision from Phase 01), but `flush()` does not expire. However, the bulk `update()` does NOT modify loaded objects in the identity map — SQLAlchemy does not reflect bulk UPDATE results back into already-loaded ORM objects.

**How to avoid:** `notify_waiting_by_book()` uses a core `update()` expression (not ORM-level update on individual instances), so identity map staleness is not a concern for the updated rows. The return value comes from `RETURNING`, not from re-reading identity map objects. This is the correct pattern.

---

## Code Examples

Verified patterns from project source and SQLAlchemy 2.0 behavior:

### Alembic Migration for pre_bookings Table

```python
# Source: project pattern (e5f6a7b8c9d0_create_wishlist_items.py)
def upgrade() -> None:
    op.create_table(
        "pre_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("waiting", "notified", "cancelled", name="prebookstatus"),
            nullable=False,
            server_default="waiting",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pre_bookings_user_id", "pre_bookings", ["user_id"])
    op.create_index("ix_pre_bookings_book_id", "pre_bookings", ["book_id"])
    # Conditional unique index — only one WAITING pre-booking per (user, book)
    op.create_index(
        "uq_pre_bookings_user_book_waiting",
        "pre_bookings",
        ["user_id", "book_id"],
        unique=True,
        postgresql_where=sa.text("status = 'waiting'"),
    )
```

### PreBookRepository.add() with IntegrityError Handling

```python
# Source: project pattern (app/wishlist/repository.py WishlistRepository.add())
async def add(self, user_id: int, book_id: int) -> PreBooking:
    prebook = PreBooking(user_id=user_id, book_id=book_id, status=PreBookStatus.WAITING)
    self.session.add(prebook)
    try:
        await self.session.flush()
    except IntegrityError as e:
        await self.session.rollback()
        orig = str(e.orig).lower() if e.orig else ""
        if "uq_pre_bookings_user_book_waiting" in orig or "pre_bookings" in orig:
            raise AppError(
                409,
                "You already have an active pre-booking for this book",
                "PREBOOK_DUPLICATE",
                "book_id",
            ) from e
        raise
    await self.session.refresh(prebook, ["book"])
    return prebook
```

### PreBookService.create() with Stock Guard

```python
# Source: project patterns (app/wishlist/service.py, app/books/service.py)
async def create(self, user_id: int, book_id: int) -> PreBooking:
    """Create a pre-booking. Validates book exists and is out of stock.

    Raises:
        AppError(404) BOOK_NOT_FOUND if book does not exist.
        AppError(409) PREBOOK_BOOK_IN_STOCK if stock_quantity > 0.
        AppError(409) PREBOOK_DUPLICATE if user already has a waiting pre-booking.
    """
    book = await self.book_repo.get_by_id(book_id)
    if book is None:
        raise AppError(404, "Book not found", "BOOK_NOT_FOUND", "book_id")
    if book.stock_quantity > 0:
        raise AppError(
            409,
            "Book is in stock — add to cart instead",
            "PREBOOK_BOOK_IN_STOCK",
            "book_id",
        )
    return await self.prebook_repo.add(user_id, book_id)
```

### Router: PATCH /books/{id}/stock with Notification Side-Effect

```python
# Source: STATE.md locked pattern — router wires prebook_repo, receives user_ids
@router.patch("/books/{book_id}/stock", response_model=BookResponse)
async def update_stock(
    book_id: int,
    body: StockUpdate,
    db: DbSession,
    admin: AdminUser,
    background_tasks: BackgroundTasks,
    # Phase 12 will use email_svc: EmailSvc here
) -> BookResponse:
    from app.prebooks.repository import PreBookRepository  # avoid circular at module level
    book_service = BookService(book_repo=BookRepository(db), genre_repo=GenreRepository(db))
    prebook_repo = PreBookRepository(db)
    book, notified_user_ids = await book_service.set_stock_and_notify(
        book_id, body.quantity, prebook_repo
    )
    # Phase 12 wires email here: for uid in notified_user_ids: email_svc.enqueue(...)
    return BookResponse.model_validate(book)
```

**Note:** For Phase 11, the router signature collects `notified_user_ids` but does not yet enqueue emails (that is Phase 12). The mechanism is validated end-to-end (the user_ids are returned and accessible) but no email send is wired.

### GET /prebooks List — Default Filter

```python
# Claude's discretion: show active pre-bookings by default (waiting + notified),
# exclude cancelled. User can see cancelled by passing ?include_cancelled=true
# or simpler: always return all, let client filter. Recommended: return all,
# sorted by created_at DESC. Status is always visible so client can filter.
async def get_all_for_user(self, user_id: int) -> list[PreBooking]:
    result = await self.session.execute(
        select(PreBooking)
        .where(PreBooking.user_id == user_id)
        .options(selectinload(PreBooking.book))
        .order_by(PreBooking.created_at.desc())
    )
    return list(result.scalars().all())
```

### Cancel by Pre-booking ID with Ownership Check

```python
# Cancel endpoint: DELETE /prebooks/{id} (204 or PATCH with body — use DELETE for REST clarity)
async def cancel(self, user_id: int, prebook_id: int) -> None:
    prebook = await self.prebook_repo.get_by_id(prebook_id)
    if prebook is None or prebook.user_id != user_id:
        raise AppError(404, "Pre-booking not found", "PREBOOK_NOT_FOUND")
    if prebook.status == PreBookStatus.CANCELLED:
        raise AppError(409, "Pre-booking is already cancelled", "PREBOOK_ALREADY_CANCELLED")
    await self.prebook_repo.cancel(prebook)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x `bulk_update_mappings` | SQLAlchemy 2.0 `update().returning()` in async | SQLAlchemy 2.0 (2023) | Clean async bulk update with row-level RETURNING |
| Hard delete for "cancelled" state | Soft-delete with status enum | Project decision (STATE.md v1.1) | Audit trail; enables re-reservation |
| Separate email-fetch query after notification | RETURNING user_id from bulk UPDATE | SQLAlchemy 2.0 | Single round-trip for notification broadcast |

**Deprecated/outdated:**
- `session.execute(update(...))` without `await` — SQLAlchemy 2.0 async requires `await`; always `await self.session.execute(update(...))`

---

## Open Questions

1. **Max pre-bookings per user limit**
   - What we know: CONTEXT.md leaves this to Claude's discretion
   - What's unclear: Whether to enforce a hard limit (e.g., max 10 active waiting pre-bookings per user)
   - Recommendation: No limit for Phase 11. A bookstore user pre-booking many books is normal behavior. A DB-level limit adds complexity without clear benefit at v1.1 scale. If needed, add in a future phase.

2. **Cancelled pre-bookings in GET /prebooks**
   - What we know: CONTEXT.md leaves this to Claude's discretion
   - What's unclear: Whether to filter cancelled records from the default list view
   - Recommendation: Return ALL pre-bookings (waiting, notified, cancelled) sorted by `created_at DESC`. Status is visible in the response — clients can filter. This avoids API versioning issues if the decision changes. Cancelled records are few and the list is bounded per user.

3. **Pre-booking cancel endpoint: DELETE vs PATCH**
   - What we know: CONTEXT.md says "soft delete (status=CANCELLED)" — not a hard delete
   - What's unclear: Whether to use `DELETE /prebooks/{id}` (which implies removal) or `PATCH /prebooks/{id}/cancel`
   - Recommendation: Use `DELETE /prebooks/{id}` returning 204. The soft-delete is an implementation detail; the semantic is "user removes their pre-booking". This matches the wishlist pattern (`DELETE /wishlist/{book_id}` also removes). HTTP DELETE does not mandate hard-delete at the DB level.

4. **Alembic migration: SAEnum type creation**
   - What we know: `OrderStatus` uses `SAEnum(OrderStatus, name="orderstatus")` — Alembic autogenerates `CREATE TYPE orderstatus AS ENUM ...` in the migration
   - What's unclear: Whether manual migration should use `sa.Enum(...)` with explicit `name="prebookstatus"` or rely on autogenerate
   - Recommendation: Use autogenerate (`alembic revision --autogenerate`) after creating the model. Verify the migration creates both the ENUM TYPE and the table. The existing alembic setup handles this correctly.

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — this section is omitted per instructions.

---

## Sources

### Primary (HIGH confidence)

- Project source: `app/wishlist/` — repository `add()` with IntegrityError pattern, soft-delete via `delete()` (adapted to status-based soft-delete)
- Project source: `app/users/repository.py` — `revoke_all_for_user()` — bulk `UPDATE ... WHERE ... .values(...)` with `result.rowcount`
- Project source: `app/orders/models.py` — `OrderStatus(StrEnum)` + `SAEnum` pattern
- Project source: `app/books/service.py` + `app/books/router.py` — `set_stock()` method and `PATCH /books/{id}/stock` endpoint to extend
- Project source: `app/email/service.py` — `enqueue()` BackgroundTasks pattern for post-commit email
- Project source: `app/core/deps.py` — `get_db()` commit-on-success semantics; BackgroundTasks run after commit
- Project source: `alembic/versions/e5f6a7b8c9d0_create_wishlist_items.py` — migration pattern
- Project source: `.planning/STATE.md` — locked decision: BookService calls PreBookRepository in same transaction, returns email list to router

### Secondary (MEDIUM confidence)

- SQLAlchemy 2.0 docs — `update().returning()` supported in async via `await session.execute(update(...).returning(...))`; `result.scalars().all()` retrieves returned values — consistent with `revoke_all_for_user` pattern (which uses `result.rowcount` but not `RETURNING`); the `RETURNING` extension follows logically
- PostgreSQL docs — partial (conditional) unique index `WHERE status = 'waiting'` — standard PostgreSQL feature, supported by SQLAlchemy `Index(..., postgresql_where=text(...))`

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in use; no new packages
- Architecture: HIGH — patterns directly derived from existing project modules (wishlist, users/repository, orders/models, email/service)
- Pitfalls: HIGH — derived from project decisions in STATE.md plus direct analysis of edge cases from CONTEXT.md locked decisions
- Partial unique index behavior: HIGH — standard PostgreSQL feature, SQLAlchemy `postgresql_where` parameter is documented

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable stack — 30 days)
