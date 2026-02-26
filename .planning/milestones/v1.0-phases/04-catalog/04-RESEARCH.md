# Phase 4: Catalog - Research

**Researched:** 2026-02-25
**Domain:** FastAPI + SQLAlchemy 2.0 async CRUD — admin book and genre management
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Required fields on creation: title, author, price
- Optional fields: ISBN, genre, description, cover image URL, publish date
- ISBN validated for ISBN-10 or ISBN-13 format with checksum when provided; rejected on invalid format
- Price must be > 0, stored as Numeric(10,2) — no free books
- ISBN has a unique constraint (when provided); titles are not unique — different editions of the same book are valid
- Cover image stored as URL string, not file upload

### Claude's Discretion
- Genre taxonomy design (flat vs hierarchical, single vs multi-genre per book)
- Stock management approach (absolute set vs increment/decrement on PATCH endpoint)
- Deletion strategy (hard delete vs soft delete, handling of referenced books)
- Response payload structure and pagination for admin list endpoints
- Validation error message format (consistent with existing auth error patterns)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CATL-01 | Admin can add a book with title, author, price, ISBN, genre, description, cover image URL, publish date | SQLAlchemy Numeric(10,2) for price; Pydantic custom validator for ISBN-10/13 checksum; `POST /books` returns 201 with book record |
| CATL-02 | Admin can edit book details | `PUT /books/{id}` full replacement or `PATCH /books/{id}` partial; BookRepository.update(); 404 AppError on missing book |
| CATL-03 | Admin can delete a book | `DELETE /books/{id}` returns 204; hard delete is sufficient here (downstream phases introduce FK constraints that make soft delete necessary only if books can be in orders — Phase 4 is pre-order) |
| CATL-04 | Admin can update book stock quantity | `PATCH /books/{id}/stock` with absolute integer value; DB CHECK CONSTRAINT stock_quantity >= 0; Phase 9 wires notifications here |
| CATL-05 | Admin can manage genre taxonomy (add/list genres) | `POST /genres` (201), `GET /genres` (200 list); flat Genre table; book.genre_id FK to genres |
</phase_requirements>

---

## Summary

Phase 4 builds the admin-only CRUD surface for the book catalog. It introduces two new tables — `books` and `genres` — following the exact same patterns already established in Phases 1–3: SQLAlchemy 2.0 mapped columns, async repository classes, a thin service layer, Pydantic schemas for validation, and the `require_admin` dependency for authorization. No new libraries are required; the entire phase is implemented with the existing stack.

The primary design decisions left to Claude's discretion are: (1) genre structure — a flat, FK-linked Genre table per book is the right choice for v1 given Phase 5 requires genre-based filtering and Phase 9 implicitly depends on clean genre relationships; (2) stock management — an absolute-set PATCH is simpler and avoids race conditions that an increment/decrement approach would introduce at this phase; (3) deletion — hard delete is appropriate since no other tables reference books yet (cart, orders, wishlist come later; Phase 7 will need to guard against deleting books with active orders, but that is handled then).

**Primary recommendation:** Mirror the `app/users/` module structure exactly — create `app/books/` with models, repository, service, schemas, and router. One Alembic migration creates both `genres` and `books` tables with the stock `CHECK CONSTRAINT`.

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ^2.0.47 | ORM models, async queries | Already in project; `Mapped`/`mapped_column` typed API |
| Alembic | ^1.18.4 | Schema migrations | Already in project; `autogenerate` detects new models |
| Pydantic | ^2.12.5 | Request/response validation | Already in project; custom `@field_validator` for ISBN |
| FastAPI | ^0.133.0 | HTTP routing, dependency injection | Already in project; `require_admin` dep already exists |
| asyncpg | ^0.31.0 | PostgreSQL async driver | Already in project |

### No New Libraries Required

All catalog CRUD functionality is covered by the existing stack. Do NOT add new packages.

**ISBN validation** is implemented as a pure-Python Pydantic `@field_validator` — no external `isbnlib` or similar package. The checksum algorithms (ISBN-10: sum of digits weighted 1–10 mod 11; ISBN-13: alternating 1/3 weights mod 10) are 10–15 lines of code and carry no dependency.

**Installation:** None required.

---

## Architecture Patterns

### Recommended Module Structure

```
app/books/
├── __init__.py
├── models.py        # Genre + Book SQLAlchemy models
├── repository.py    # GenreRepository + BookRepository
├── service.py       # BookService (business rules: uniqueness, not-found)
├── schemas.py       # BookCreate, BookUpdate, BookResponse, GenreCreate, GenreResponse, StockUpdate
└── router.py        # POST/PUT/DELETE /books, PATCH /books/{id}/stock, POST/GET /genres

alembic/versions/
└── XXXX_create_genres_and_books.py   # Single migration for both tables
```

### Pattern 1: SQLAlchemy Model — Genre (flat taxonomy)

**What:** Genres as a simple lookup table; books hold a nullable FK to genres.
**When to use:** v1 with single-genre-per-book and simple filter queries (Phase 5).

```python
# app/books/models.py
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    books: Mapped[list["Book"]] = relationship(back_populates="genre")


class Book(Base):
    __tablename__ = "books"

    __table_args__ = (
        CheckConstraint("stock_quantity >= 0", name="ck_books_stock_non_negative"),
        CheckConstraint("price > 0", name="ck_books_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(17), unique=True, nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    genre_id: Mapped[int | None] = mapped_column(
        ForeignKey("genres.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    genre: Mapped["Genre | None"] = relationship(back_populates="books")
```

**Key decisions encoded in the model:**
- `Numeric(10, 2)` for price — exact decimal arithmetic, no floating-point error
- `stock_quantity` defaults to 0, DB-enforced non-negative via CHECK CONSTRAINT
- `isbn` is nullable + unique — the unique index in PostgreSQL on a nullable column only enforces uniqueness among non-NULL values (correct behavior)
- `genre_id` nullable FK — a book can exist without a genre
- `updated_at` uses `onupdate=func.now()` for automatic timestamp maintenance

### Pattern 2: Pydantic Schema with ISBN Validation

**What:** `@field_validator` for ISBN-10 and ISBN-13 checksum validation.
**When to use:** All create/update operations that accept an ISBN field.

```python
# app/books/schemas.py
import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_config


def _validate_isbn(isbn: str) -> str:
    """Validate ISBN-10 or ISBN-13 with checksum. Raise ValueError on failure."""
    # Strip hyphens and spaces (common formatting)
    cleaned = re.sub(r"[-\s]", "", isbn).upper()

    if len(cleaned) == 10:
        # ISBN-10: digits 1-9 + check digit (0-9 or X)
        if not re.match(r"^\d{9}[\dX]$", cleaned):
            raise ValueError("ISBN-10 must be 9 digits followed by a digit or X")
        total = sum((10 - i) * (int(c) if c != "X" else 10) for i, c in enumerate(cleaned))
        if total % 11 != 0:
            raise ValueError("ISBN-10 checksum invalid")

    elif len(cleaned) == 13:
        # ISBN-13: 13 digits with alternating 1/3 weights
        if not re.match(r"^\d{13}$", cleaned):
            raise ValueError("ISBN-13 must be exactly 13 digits")
        total = sum(
            int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(cleaned)
        )
        if total % 10 != 0:
            raise ValueError("ISBN-13 checksum invalid")

    else:
        raise ValueError("ISBN must be 10 or 13 digits (hyphens ignored)")

    return cleaned


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(gt=0, decimal_places=2)
    isbn: str | None = None
    genre_id: int | None = None
    description: str | None = None
    cover_image_url: str | None = Field(None, max_length=2048)
    publish_date: date | None = None

    @field_validator("isbn", mode="before")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        return _validate_isbn(v)

    model_config = model_config(from_attributes=True)


class BookUpdate(BaseModel):
    """All fields optional for PUT (caller provides all intended fields)."""
    title: str | None = Field(None, min_length=1, max_length=500)
    author: str | None = Field(None, min_length=1, max_length=255)
    price: Decimal | None = Field(None, gt=0, decimal_places=2)
    isbn: str | None = None
    genre_id: int | None = None
    description: str | None = None
    cover_image_url: str | None = Field(None, max_length=2048)
    publish_date: date | None = None

    @field_validator("isbn", mode="before")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        return _validate_isbn(v)


class StockUpdate(BaseModel):
    quantity: int = Field(ge=0, description="Absolute stock quantity to set")


class BookResponse(BaseModel):
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

    model_config = model_config(from_attributes=True)


class GenreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GenreResponse(BaseModel):
    id: int
    name: str

    model_config = model_config(from_attributes=True)
```

### Pattern 3: Repository Layer

**What:** Async repository following the same class-per-model pattern as `UserRepository`.
**When to use:** All DB access goes through repositories, never raw queries in the router.

```python
# app/books/repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.books.models import Book, Genre


class GenreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self) -> list[Genre]:
        result = await self.session.execute(select(Genre).order_by(Genre.name))
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Genre | None:
        result = await self.session.execute(
            select(Genre).where(Genre.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str) -> Genre:
        genre = Genre(name=name)
        self.session.add(genre)
        await self.session.flush()
        return genre


class BookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, book_id: int) -> Book | None:
        result = await self.session.execute(
            select(Book).where(Book.id == book_id)
        )
        return result.scalar_one_or_none()

    async def get_by_isbn(self, isbn: str) -> Book | None:
        result = await self.session.execute(
            select(Book).where(Book.isbn == isbn)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Book:
        book = Book(**kwargs)
        self.session.add(book)
        await self.session.flush()
        return book

    async def update(self, book: Book, **kwargs) -> Book:
        for field, value in kwargs.items():
            setattr(book, field, value)
        await self.session.flush()
        return book

    async def delete(self, book: Book) -> None:
        await self.session.delete(book)
        await self.session.flush()

    async def set_stock(self, book: Book, quantity: int) -> Book:
        book.stock_quantity = quantity
        await self.session.flush()
        return book
```

### Pattern 4: Router with AdminUser Dependency

**What:** All catalog write endpoints are gated by `AdminUser` (imported from `app.core.deps`).
**When to use:** Every route that mutates the catalog.

```python
# app/books/router.py
from fastapi import APIRouter, status
from app.core.deps import AdminUser, DbSession
from app.books.repository import BookRepository, GenreRepository
from app.books.schemas import (
    BookCreate, BookResponse, BookUpdate, GenreCreate, GenreResponse, StockUpdate
)
from app.books.service import BookService
from app.core.exceptions import AppError

router = APIRouter(tags=["books"])


def _make_service(db: DbSession) -> BookService:
    return BookService(
        book_repo=BookRepository(db),
        genre_repo=GenreRepository(db),
    )


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(body: BookCreate, db: DbSession, admin: AdminUser) -> BookResponse:
    service = _make_service(db)
    book = await service.create_book(body)
    return BookResponse.model_validate(book)


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(book_id: int, body: BookUpdate, db: DbSession, admin: AdminUser) -> BookResponse:
    service = _make_service(db)
    book = await service.update_book(book_id, body)
    return BookResponse.model_validate(book)


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, db: DbSession, admin: AdminUser) -> None:
    service = _make_service(db)
    await service.delete_book(book_id)


@router.patch("/books/{book_id}/stock", response_model=BookResponse)
async def update_stock(book_id: int, body: StockUpdate, db: DbSession, admin: AdminUser) -> BookResponse:
    service = _make_service(db)
    book = await service.set_stock(book_id, body.quantity)
    return BookResponse.model_validate(book)


@router.post("/genres", response_model=GenreResponse, status_code=status.HTTP_201_CREATED)
async def create_genre(body: GenreCreate, db: DbSession, admin: AdminUser) -> GenreResponse:
    service = _make_service(db)
    genre = await service.create_genre(body.name)
    return GenreResponse.model_validate(genre)


@router.get("/genres", response_model=list[GenreResponse])
async def list_genres(db: DbSession) -> list[GenreResponse]:
    """Public — no auth required. Genres are reference data."""
    service = _make_service(db)
    genres = await service.list_genres()
    return [GenreResponse.model_validate(g) for g in genres]
```

### Pattern 5: Alembic Migration

**What:** A single migration that creates `genres` then `books` (FK dependency order).
**When to use:** Phase 4 Plan 1.

```python
# alembic/versions/XXXX_create_genres_and_books.py
import sqlalchemy as sa
from alembic import op

def upgrade() -> None:
    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_genres_name", "genres", ["name"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("isbn", sa.String(17), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(2048), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("genre_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_books_stock_non_negative"),
        sa.CheckConstraint("price > 0", name="ck_books_price_positive"),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_books_title", "books", ["title"])
    op.create_index("ix_books_author", "books", ["author"])
    op.create_index("ix_books_isbn", "books", ["isbn"], unique=True)
    op.create_index("ix_books_genre_id", "books", ["genre_id"])


def downgrade() -> None:
    op.drop_table("books")
    op.drop_table("genres")
```

### Anti-Patterns to Avoid

- **Float for price:** Use `Numeric(10, 2)` not `Float`. Float loses precision on arithmetic (e.g., `0.1 + 0.2 != 0.3`). Python `Decimal` maps correctly.
- **Raw `session.execute(text(...))` in service:** All SQL goes through repository methods. Service layer calls repositories only.
- **Skipping `flush()` after `session.add()`:** Without `flush()`, the ORM does not send the INSERT to the DB within the current transaction, so the returned model has no `id`. Pattern: `session.add(obj); await session.flush(); return obj`.
- **Regex-only ISBN validation:** Regex format alone is insufficient. ISBN-10 and ISBN-13 have checksum digits that catch transcription errors. Must implement the full checksum algorithm.
- **Unique constraint on nullable ISBN with conditional logic in Python:** PostgreSQL's unique index on a nullable column correctly ignores NULLs — no need for application-level workaround. Just declare `unique=True, nullable=True` in the column definition.
- **Returning genre as embedded object vs FK id:** `BookResponse` should return `genre_id` (the FK integer), not the full `Genre` object, unless a `genre` relationship is explicitly loaded. Avoid accidental lazy-load in async context — use `genre_id` only, or eagerly load with `joinedload` when needed (Phase 5 discovery may add this).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request validation | Manual field checks in route handler | Pydantic `Field(gt=0)`, `min_length`, `@field_validator` | Pydantic handles 422 + error formatting automatically |
| Admin authorization | Custom role check per route | `AdminUser = Annotated[dict, Depends(require_admin)]` already in `app.core.deps` | Already built in Phase 2; import and use |
| DB session management | Manual session open/close in routes | `DbSession` type alias from `app.core.deps` | Already wired with commit/rollback semantics |
| ISBN format enforcement at DB level | DB-level CHECK CONSTRAINT for ISBN format | Pydantic `@field_validator` in schema | DB constraints can't implement checksum math; validate at schema layer, rely on unique index only at DB |
| Soft delete infrastructure | `deleted_at` column + filter-everywhere | Hard delete (Phase 4) | No FK references to books exist yet; Phase 7 can guard against deleting books with orders when those tables exist |

**Key insight:** This phase is pure wiring of already-established patterns. The value is correctness (proper ISBN checksum, DB constraints, right FK relationships) not new abstractions.

---

## Common Pitfalls

### Pitfall 1: Alembic Not Discovering New Models

**What goes wrong:** `alembic revision --autogenerate` generates an empty migration because `Book` and `Genre` are not imported into `alembic/env.py`.
**Why it happens:** Alembic discovers models by reading `Base.metadata`, which is only populated when model modules are actually imported.
**How to avoid:** Add imports to `alembic/env.py` alongside the existing user model imports:
```python
from app.books.models import Book, Genre  # noqa: F401
```
**Warning signs:** Autogenerated migration body is empty (`pass`) or only contains a comment.

### Pitfall 2: Decimal Serialization in Pydantic/JSON

**What goes wrong:** `Decimal` fields serialize as strings in JSON (`"19.99"`) instead of numbers (`19.99`), causing client-side type confusion.
**Why it happens:** Python's `json` module does not natively serialize `Decimal`. FastAPI uses `jsonable_encoder` which converts `Decimal` to `str` by default.
**How to avoid:** Annotate the Pydantic field with `Decimal` (Pydantic v2 serializes `Decimal` as a number by default when using `model_dump(mode="json")`). Confirm with a test that the JSON response's `price` field is a number, not a string.

### Pitfall 3: ISBN Unique Index on NULL Values

**What goes wrong:** Developer adds a UNIQUE constraint and then is surprised that two books with `isbn=NULL` can coexist. Or conversely, incorrectly handles this as a bug.
**Why it happens:** PostgreSQL partial unique index semantics — NULL is not equal to NULL for uniqueness purposes.
**How to avoid:** This is the correct behavior. Two books without an ISBN should be allowed. No special handling needed. Document this in code comments.

### Pitfall 4: Stock Going Negative via Concurrent PATCH

**What goes wrong:** Two concurrent PATCH `/books/{id}/stock` requests both read `stock_quantity=5`, and both set it to 0 — this is fine for absolute-set semantics. However, if increment/decrement were used, concurrent decrements could bypass the CHECK CONSTRAINT.
**Why it happens:** Absolute-set avoids this race condition entirely — the last writer wins, which is acceptable for admin stock management.
**How to avoid:** Use absolute-set (the CONTEXT.md discretion recommendation). The CHECK CONSTRAINT provides a final safety net for any non-zero floor.

### Pitfall 5: Missing `updated_at` Server-Side Update

**What goes wrong:** `Book.updated_at` does not update on `PUT /books/{id}` because `onupdate=func.now()` in SQLAlchemy's `mapped_column` is a Python-side ORM hook, not a DB-level trigger.
**Why it happens:** SQLAlchemy `onupdate` sets the column value in the ORM UPDATE statement only when the ORM processes an update. If the update is done via a raw `UPDATE` statement (not going through the ORM mapped object), `onupdate` is not triggered.
**How to avoid:** Always mutate via `setattr(book, field, value)` on the mapped object (as shown in `BookRepository.update()`), never via `session.execute(update(Book).where(...).values(...))`. The ORM will include `updated_at=now()` automatically.

### Pitfall 6: 422 vs AppError for ISBN Conflict

**What goes wrong:** ISBN uniqueness violation comes back as a PostgreSQL `UniqueViolationError` (unhandled), crashing with 500, instead of a clean 409.
**Why it happens:** Pydantic validates format and checksum, but uniqueness is enforced at DB level. The repository `flush()` will raise `sqlalchemy.exc.IntegrityError` wrapping `asyncpg.UniqueViolationError`.
**How to avoid:** In `BookService.create_book()` (and `update_book()`), catch `sqlalchemy.exc.IntegrityError` and raise `AppError(status_code=409, detail="ISBN already exists", code="BOOK_ISBN_CONFLICT", field="isbn")`.

---

## Code Examples

### Service Layer Pattern (with AppError for 404 and 409)

```python
# app/books/service.py
from sqlalchemy.exc import IntegrityError
from app.books.models import Book, Genre
from app.books.repository import BookRepository, GenreRepository
from app.books.schemas import BookCreate, BookUpdate
from app.core.exceptions import AppError


class BookService:
    def __init__(self, book_repo: BookRepository, genre_repo: GenreRepository) -> None:
        self.book_repo = book_repo
        self.genre_repo = genre_repo

    async def _get_book_or_404(self, book_id: int) -> Book:
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise AppError(
                status_code=404,
                detail="Book not found",
                code="BOOK_NOT_FOUND",
                field="book_id",
            )
        return book

    async def create_book(self, data: BookCreate) -> Book:
        try:
            return await self.book_repo.create(**data.model_dump(exclude_none=False))
        except IntegrityError as e:
            if "isbn" in str(e.orig).lower():
                raise AppError(
                    status_code=409,
                    detail="A book with this ISBN already exists",
                    code="BOOK_ISBN_CONFLICT",
                    field="isbn",
                ) from e
            raise

    async def update_book(self, book_id: int, data: BookUpdate) -> Book:
        book = await self._get_book_or_404(book_id)
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
        try:
            return await self.book_repo.update(book, **updates)
        except IntegrityError as e:
            if "isbn" in str(e.orig).lower():
                raise AppError(
                    status_code=409,
                    detail="A book with this ISBN already exists",
                    code="BOOK_ISBN_CONFLICT",
                    field="isbn",
                ) from e
            raise

    async def delete_book(self, book_id: int) -> None:
        book = await self._get_book_or_404(book_id)
        await self.book_repo.delete(book)

    async def set_stock(self, book_id: int, quantity: int) -> Book:
        book = await self._get_book_or_404(book_id)
        return await self.book_repo.set_stock(book, quantity)

    async def create_genre(self, name: str) -> Genre:
        existing = await self.genre_repo.get_by_name(name)
        if existing:
            raise AppError(
                status_code=409,
                detail="Genre already exists",
                code="GENRE_CONFLICT",
                field="name",
            )
        return await self.genre_repo.create(name)

    async def list_genres(self) -> list[Genre]:
        return await self.genre_repo.get_all()
```

### Registering the Router in main.py

```python
# In app/main.py create_app():
from app.books.router import router as books_router
application.include_router(books_router)
```

### Test Fixture Pattern (admin_tokens already established in test_auth.py)

```python
# tests/test_catalog.py
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.users.repository import UserRepository


@pytest_asyncio.fixture
async def admin_tokens(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create admin user and return login tokens (mirrors test_auth.py pattern)."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="catalog_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "catalog_admin@example.com", "password": "adminpass123"},
    )
    return resp.json()


@pytest_asyncio.fixture
async def admin_headers(admin_tokens: dict) -> dict:
    return {"Authorization": f"Bearer {admin_tokens['access_token']}"}
```

---

## Design Recommendations (Claude's Discretion)

### Genre Taxonomy: Flat, Single-Genre per Book

**Decision:** A flat `genres` table with a nullable `genre_id` FK on `books`.

**Rationale:**
- Phase 5 (Discovery) requires `GET /books?genre=fantasy` — a single FK column enables a simple `WHERE books.genre_id = :id` filter
- Phase 9 stock notification has no genre dependency
- Multi-genre (M:M junction table) adds complexity without v1 requirement justification
- Hierarchical genres (parent_id self-reference) adds recursive query complexity — no v1 requirement for subcategories

### Stock Management: Absolute Set

**Decision:** `PATCH /books/{id}/stock` accepts `{"quantity": N}` and sets `stock_quantity = N` absolutely.

**Rationale:**
- Simpler: no race condition between concurrent increments
- Admin use case: typically reconciling inventory from a physical count — absolute value is the right mental model
- Phase 9 (`notify_waiting`) reads stock after the admin sets it — absolute set is transactionally clean (stock = new value in same transaction that triggers notifications)
- Increment/decrement semantics belong in Phase 7 checkout (stock decrement via `SELECT FOR UPDATE`)

### Deletion: Hard Delete

**Decision:** `DELETE /books/{id}` performs a hard delete.

**Rationale:**
- Phase 4 is the first phase that creates books. No cart, order, or wishlist tables exist yet.
- Phase 7 (Orders) stores `unit_price` as a snapshot on `order_items` — historical price is preserved regardless of book deletion.
- If Phase 7 or Phase 6 needs to guard against deleting a book that is in an active cart/order, that guard belongs in those phases (check FK violations, or add a service-layer check before delete).
- Soft delete (`deleted_at`) adds filter complexity to every downstream query. Not worth the overhead at this stage.

### Response Payload: Simple, No Pagination for Admin

**Decision:** Admin write endpoints return the single book/genre record. `GET /genres` returns a flat list (no pagination needed — genre count is small). No admin `GET /books` list endpoint is required in Phase 4 (Phase 5 handles discovery/listing).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Column()` style ORM | `mapped_column()` with `Mapped[T]` | SQLAlchemy 2.0 (2023) | Type-safe, IDE-friendly; project already uses this |
| `Float` for currency | `Numeric(10, 2)` / `Decimal` | Best practice, always | Exact arithmetic, no rounding errors |
| Pydantic v1 `@validator` | Pydantic v2 `@field_validator` with `mode="before"` | Pydantic v2 (2023) | Project is on Pydantic v2; use v2 syntax |
| `session.query()` ORM API | `select()` / `session.execute()` | SQLAlchemy 2.0 | Project already uses new-style queries |

**Deprecated/outdated (do not use):**
- `session.query(Book).filter(...)` — use `select(Book).where(...)` with `session.execute()`
- `@validator` (Pydantic v1) — use `@field_validator` (Pydantic v2)
- `Column()` without `mapped_column()` — project uses `Mapped[T]` / `mapped_column()` throughout

---

## Open Questions

1. **`GET /books` for admin in Phase 4?**
   - What we know: The success criteria mention POST/PUT/DELETE/PATCH — no admin list endpoint is explicitly required by CATL-01 through CATL-05.
   - What's unclear: Should Phase 4 add a basic `GET /books` (admin list) or defer entirely to Phase 5 (Discovery)?
   - Recommendation: Defer to Phase 5. Phase 5's `GET /books` with pagination/search/filter serves both admin and public use. Adding a stripped-down admin-only version now creates duplication. Tests can verify persistence by using `GET /books/{id}` if needed, or by direct DB query in tests.

2. **`GET /books/{id}` — Phase 4 or Phase 5?**
   - What we know: Success criteria item 2 states "GET the book to confirm the change" — implying a GET endpoint is needed to verify updates.
   - What's unclear: Should this be a minimal Phase 4 endpoint (admin-only or public) or deferred to Phase 5?
   - Recommendation: Add a minimal `GET /books/{id}` in Phase 4 (no auth required — book details are reference data). This enables test verification without requiring Phase 5 to be complete. Phase 5 will expand it with stock status and relationships.

3. **Phase 9 coupling point: stock PATCH triggers pre-booking notifications**
   - What we know: STATE.md documents this as a Phase 9 concern — `BookService.set_stock()` will eventually call `PreBookRepository.notify_waiting(book_id)`.
   - What's unclear: Does Phase 4's `set_stock` need a hook point now?
   - Recommendation: No — Phase 9 will directly modify `BookService.set_stock()` to add the notification call. Keep Phase 4 implementation clean with no forward references to pre-booking.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `app/users/models.py`, `app/users/repository.py`, `app/users/service.py`, `app/users/router.py`, `app/users/schemas.py`, `app/core/deps.py`, `app/core/exceptions.py`, `app/db/base.py`, `app/main.py` — authoritative project patterns
- `pyproject.toml` — exact library versions in use
- `alembic/env.py` and existing migration files — migration pattern and model registration pattern
- `tests/conftest.py`, `tests/test_auth.py` — test fixture and test structure patterns
- `.planning/phases/04-catalog/04-CONTEXT.md` — locked decisions and discretion areas

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 `Numeric` type documentation — Numeric(precision, scale) is the correct type for monetary values; `Float` loses precision
- ISBN-10 and ISBN-13 checksum algorithms — standard mathematical specification, high confidence in correctness
- PostgreSQL unique index on nullable column behavior — NULL != NULL for uniqueness; well-documented behavior

### Tertiary (LOW confidence)
- Pydantic v2 `Decimal` JSON serialization behavior — confirmed from project's use of Pydantic v2 and FastAPI's `jsonable_encoder`; should be verified by running a quick test in the implementation plan

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — entire stack already installed and in use; no new dependencies
- Architecture: HIGH — directly mirrors existing `app/users/` module structure; all patterns verified from codebase
- Pitfalls: HIGH — pitfalls derived from actual code patterns in project plus well-known SQLAlchemy/PostgreSQL behaviors
- ISBN validation: HIGH — ISBN-10 and ISBN-13 checksum algorithms are mathematically defined standards

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable stack; no fast-moving dependencies)
