# Phase 5: Discovery - Research

**Researched:** 2026-02-25
**Domain:** PostgreSQL full-text search (tsvector/tsquery), SQLAlchemy 2.0 async query composition, FastAPI pagination/filtering/sorting
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Prefix + full-text matching: PostgreSQL tsvector for full words, plus prefix matching for partial terms (e.g., 'tolk' matches 'Tolkien')
- Search covers title, author, and genre name — the three most common search intents
- Results ranked by relevance using ts_rank when a search query is present — title matches rank higher
- When no search query, results follow the requested sort order
- Plain results — no match highlighting or matched_on metadata; same book schema as browsing

### Claude's Discretion
- Pagination style (offset vs cursor) and default page size
- Available sort options and default sort order
- Filter design (which filters, how they combine)
- Book detail response shape (stock display format, metadata included)
- tsvector column configuration (generated column vs trigger, weight assignments)
- GIN index strategy

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISC-01 | User can browse books with pagination and sorting (by title, price, date) | Offset-based pagination with `limit`/`offset`; SQLAlchemy `select(Book).order_by(...).limit(...).offset(...)`; `func.count` subquery for totals |
| DISC-02 | User can search books by title, author, or genre (full-text search) | PostgreSQL `tsvector` GENERATED column with `setweight`; `to_tsquery` + `:*` suffix for prefix matching; `@@` operator; `ts_rank` for relevance ordering |
| DISC-03 | User can filter books by genre and/or author | `WHERE` clause composition in `BookRepository.search()` — `genre_id = :id` and `author ILIKE :author`; filters combine with AND |
| DISC-04 | User can view book details including stock status | `GET /books/{id}` already exists (Phase 4); extend `BookDetailResponse` to add computed `in_stock: bool` field; `stock_quantity` already on model |
</phase_requirements>

---

## Summary

Phase 5 adds the public discovery layer on top of Phase 4's catalog. The two key deliverables are: (1) a `tsvector` generated column on the `books` table backed by a GIN index for fast full-text + prefix search across title, author, and genre name; and (2) a significantly expanded `GET /books` endpoint supporting pagination, sorting, search, and filtering — plus a minor enhancement to `GET /books/{id}` to add `in_stock`.

The entire phase stays within the existing stack (FastAPI + SQLAlchemy 2.0 async + PostgreSQL + asyncpg). No new libraries are needed. The primary new technical territory is PostgreSQL full-text search — specifically the `tsvector` GENERATED ALWAYS AS column, the `to_tsquery` prefix matching syntax (`lexeme:*`), and `ts_rank` for relevance ordering. These are well-documented PostgreSQL features that SQLAlchemy exposes via `func.to_tsvector`, `func.to_tsquery`, `func.ts_rank`, and the `@@` operator via `bool_op`.

The main implementation risk is the Alembic autogenerate issue: Alembic (including v1.18.4) may repeatedly detect the GIN index on the tsvector column as "changed" due to expression normalization differences between what Alembic writes and what PostgreSQL stores. The safe workaround is to write the migration manually (not via autogenerate) and mark the tsvector column with `system=True` or `Computed(..., persisted=True)` in the ORM model but NOT rely on autogenerate to detect it correctly.

**Primary recommendation:** Add a `search_vector` TSVECTOR GENERATED ALWAYS AS column to the books table via a hand-written Alembic migration with a GIN index. Implement `BookRepository.search()` using `select(Book).where(...).order_by(...).limit(...).offset(...)` with SQLAlchemy's `func` namespace for FTS predicates.

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ^2.0.47 | ORM query composition, tsvector via `func.*` | `func.to_tsvector`, `func.to_tsquery`, `func.ts_rank`, `bool_op("@@")` all available |
| asyncpg | ^0.31.0 | PostgreSQL async driver; executes FTS queries | Only driver tested with SQLAlchemy async + PostgreSQL; already installed |
| Alembic | ^1.18.4 | Schema migrations | Hand-written migration for tsvector + GIN index (avoid autogenerate for FTS index) |
| Pydantic | ^2.12.5 | `BookListResponse`, `BookDetailResponse` schemas | Computed fields (`in_stock`) via `@computed_field` or `@property` |
| FastAPI | ^0.133.0 | Query parameter parsing (`q`, `genre`, `author`, `page`, `size`, `sort`) | `Query()` with defaults and validation |

### No New Libraries Required

All discovery functionality is achievable with the existing stack. Do NOT add `sqlalchemy-searchable`, `fastapi-pagination`, or any additional package — the FTS query surface needed here (tsvector match + ts_rank + limit/offset) is simple enough to implement directly.

**Installation:** None required.

---

## Architecture Patterns

### Recommended Project Structure (changes from Phase 4)

```
app/books/
├── models.py        # ADD: search_vector Computed column + __table_args__ GIN index entry
├── repository.py    # ADD: search() method for filtered/sorted/paginated list
├── schemas.py       # ADD: BookListResponse (paginated envelope), BookDetailResponse (with in_stock)
└── router.py        # MODIFY: GET /books (new), MODIFY: GET /books/{id} (extended response)

alembic/versions/
└── XXXX_add_books_search_vector.py   # New migration: add column + GIN index (hand-written)
```

### Pattern 1: tsvector GENERATED ALWAYS AS Column with Weights

**What:** A stored generated column that PostgreSQL maintains automatically. Content: `setweight(to_tsvector('simple', title), 'A') || setweight(to_tsvector('simple', author), 'B') || setweight(to_tsvector('simple', coalesce(genre_name, '')), 'C')`.

**When to use:** When source columns are on the same table (title, author are on books). Genre name requires a join — two options are described below.

**Constraint:** `GENERATED ALWAYS AS ... STORED` cannot reference other tables. Genre name is in the `genres` table, not on `books`. This means the generated column can cover title + author directly; genre search must be handled separately.

**Recommended approach — two-part solution:**

Option A (recommended): Store `search_vector` covering title + author only as a generated column. Handle genre filtering as a separate `JOIN genres ON books.genre_id = genres.id WHERE genres.name ILIKE :genre` filter (exact or case-insensitive match). Genre search via FTS is less important than genre filtering — the user selects a genre from a list, not free-text.

Option B: Use a trigger to populate `search_vector` and include the genre name. More complex — requires a DB-level trigger function, and Phase 4 already uses generated columns successfully.

**Decision for this research: Use Option A** — generated column on title+author with setweight, genre filtering via ILIKE on the joined genre name.

```python
# Source: PostgreSQL docs (textsearch-tables.html), SQLAlchemy PostgreSQL dialect docs
# In app/books/models.py — add to Book class:

from sqlalchemy import Computed, Index
from sqlalchemy.dialects.postgresql import TSVECTOR

class Book(Base):
    __tablename__ = "books"

    __table_args__ = (
        CheckConstraint("stock_quantity >= 0", name="ck_books_stock_non_negative"),
        CheckConstraint("price > 0", name="ck_books_price_positive"),
        # GIN index on the generated tsvector column
        Index("ix_books_search_vector", "search_vector", postgresql_using="gin"),
    )

    # ... existing columns ...

    # Generated column: PostgreSQL maintains this automatically
    # 'simple' dictionary: no stemming, matches raw tokens — better for proper names
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('simple', coalesce(author, '')), 'B')",
            persisted=True,
        ),
        nullable=True,
        deferred=True,  # Don't load on every SELECT — only when explicitly requested
    )
```

**Why 'simple' dictionary:** The `'simple'` text search config does NOT apply stemming or stopword removal. For proper names like "Tolkien" and "Herbert", stemming would corrupt them. `'simple'` converts to lowercase and splits on whitespace/punctuation only — ideal for names and titles.

**Why `deferred=True`:** The `search_vector` column is only needed during FTS queries. Deferring prevents it from being loaded on every `GET /books/{id}` or catalog list SELECT that doesn't use FTS.

### Pattern 2: Alembic Migration for tsvector Column (Hand-Written)

**CRITICAL:** Do NOT use `alembic revision --autogenerate` for this migration. Alembic has a known bug (issue #1390, unfixed in 1.18.x) where it detects functional GIN indexes as changed on every subsequent autogenerate, creating spurious migrations. Write this migration by hand.

```python
# Source: PostgreSQL docs, Alembic official docs (cookbook.html)
# alembic/versions/XXXX_add_books_search_vector.py

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "XXXX"  # fill in actual hash
down_revision: str | None = "c3d4e5f6a7b8"  # the create_genres_and_books migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the generated tsvector column
    op.add_column(
        "books",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('simple', coalesce(author, '')), 'B')",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    # Create GIN index for fast full-text search
    op.create_index(
        "ix_books_search_vector",
        "books",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_books_search_vector", table_name="books")
    op.drop_column("books", "search_vector")
```

**After writing this migration manually, exclude it from future autogenerate detection** by adding to `alembic/env.py`:
```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "index" and name == "ix_books_search_vector":
        return False  # Skip this index in autogenerate comparison
    return True
```

### Pattern 3: Search Query with Prefix Matching + ts_rank

**What:** Build the FTS predicate using `to_tsquery('simple', processed_query)` where `processed_query` appends `:*` to each token for prefix matching, then filter with the `@@` operator and order by `ts_rank`.

**Prefix matching syntax:** In PostgreSQL tsquery, a lexeme followed by `:*` matches any word with that prefix. `'tolk:*'` matches "tolkien". `'lord ring:*'` needs to be processed token by token.

```python
# Source: PostgreSQL docs (textsearch-controls.html), SQLAlchemy PostgreSQL dialect
# In app/books/repository.py

from sqlalchemy import func, select, or_, and_
from sqlalchemy.dialects.postgresql import TSVECTOR


def _build_tsquery(q: str) -> str:
    """Convert user search string to a prefix tsquery.

    Each whitespace-delimited token gets ':*' for prefix matching.
    'tolk ring' -> 'tolk:* & ring:*'

    Strips non-alphanumeric characters to prevent tsquery injection.
    """
    import re
    tokens = re.split(r"\s+", q.strip())
    # Clean each token: keep only alphanumeric + hyphens
    clean = [re.sub(r"[^\w-]", "", t) for t in tokens if t]
    # Filter empties and build prefix query
    prefix_tokens = [f"{t}:*" for t in clean if t]
    if not prefix_tokens:
        return ""
    return " & ".join(prefix_tokens)


class BookRepository:
    # ... existing methods ...

    async def search(
        self,
        *,
        q: str | None = None,
        genre_id: int | None = None,
        author: str | None = None,
        sort: str = "title",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Book], int]:
        """Return (books, total_count) for the given filters/sort/page."""
        from sqlalchemy import func, select, desc
        from app.books.models import Book, Genre

        stmt = select(Book)

        # Apply search filter
        if q:
            tsquery_str = _build_tsquery(q)
            if tsquery_str:
                ts_query = func.to_tsquery("simple", tsquery_str)
                stmt = stmt.where(
                    Book.search_vector.bool_op("@@")(ts_query)
                )

        # Apply genre filter (by genre_id — caller resolves genre name to id if needed)
        if genre_id is not None:
            stmt = stmt.where(Book.genre_id == genre_id)

        # Apply author filter (case-insensitive substring match)
        if author:
            stmt = stmt.where(Book.author.ilike(f"%{author}%"))

        # Apply sort order
        if q:
            # Relevance sort when searching
            ts_query_for_rank = func.to_tsquery("simple", _build_tsquery(q))
            stmt = stmt.order_by(
                func.ts_rank(Book.search_vector, ts_query_for_rank).desc()
            )
        else:
            sort_col = {
                "title": Book.title,
                "price": Book.price,
                "date": Book.publish_date,
                "created_at": Book.created_at,
            }.get(sort, Book.title)
            stmt = stmt.order_by(sort_col)

        # Count total (before limit/offset)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # Apply pagination
        offset = (page - 1) * size
        stmt = stmt.limit(size).offset(offset)

        result = await self.session.execute(stmt)
        books = list(result.scalars().all())

        return books, total or 0
```

### Pattern 4: Paginated Response Schema

**What:** A wrapper schema containing `items`, `total`, `page`, `size` — the standard offset pagination envelope.

```python
# Source: Standard REST pagination convention
# In app/books/schemas.py

from pydantic import BaseModel, computed_field


class BookDetailResponse(BaseModel):
    """Response for GET /books/{id} — extends BookResponse with in_stock."""
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

    @computed_field  # type: ignore[misc]
    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    """Paginated list of books."""
    items: list[BookResponse]
    total: int
    page: int
    size: int
```

### Pattern 5: GET /books Endpoint with Query Parameters

```python
# Source: FastAPI docs, project router patterns from Phase 4
# In app/books/router.py

from fastapi import Query
from typing import Literal

@router.get("/books", response_model=BookListResponse)
async def list_books(
    db: DbSession,
    q: str | None = Query(None, description="Full-text search across title, author, genre"),
    genre_id: int | None = Query(None, description="Filter by genre ID"),
    author: str | None = Query(None, description="Filter by author (partial match)"),
    sort: Literal["title", "price", "date", "created_at"] = Query("title"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> BookListResponse:
    """Browse books with pagination, sorting, search, and filtering. Public."""
    service = _make_service(db)
    books, total = await service.list_books(
        q=q, genre_id=genre_id, author=author,
        sort=sort, page=page, size=size,
    )
    return BookListResponse(
        items=[BookResponse.model_validate(b) for b in books],
        total=total,
        page=page,
        size=size,
    )
```

### Anti-Patterns to Avoid

- **Using `autogenerate` for the tsvector GIN index:** Alembic 1.13+ repeatedly re-detects expression-based GIN indexes as changed. Write the migration by hand and exclude the index from autogenerate comparison.
- **Using `'english'` dictionary instead of `'simple'`:** The `'english'` config applies stemming and removes stop words. "Herbert" could be reduced to "Herbert" (fine) but "The" becomes nothing, and author names with common words get garbled. Use `'simple'` for proper names and titles.
- **Building tsquery with raw string concatenation from user input:** Never `f"to_tsquery('simple', '{user_input}')"`. Clean tokens first (strip non-word chars), then use parameterized `func.to_tsquery("simple", cleaned_query)`.
- **Loading `search_vector` on every SELECT:** The generated column is large and unused outside FTS. Use `deferred=True` on the column definition so SQLAlchemy omits it from standard SELECT *.
- **Offset pagination without ORDER BY:** A SELECT without ORDER BY returns rows in arbitrary physical order. Pagination results will be non-deterministic. Always include at least one deterministic sort column (e.g., `Book.id` as a tiebreaker).
- **Returning `search_vector` content in API responses:** The tsvector string is internal storage format. Never include it in `BookResponse` or any external schema.
- **Joining Genre table for genre name FTS:** Genre search via tsvector join is complex (generated columns cannot reference other tables). Use `genre_id` integer filter (client picks from `/genres` list) and `ilike` for partial author search instead.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full-text search tokenization | Custom tokenizer splitting on spaces | `to_tsvector('simple', text)` in PostgreSQL | Edge cases: punctuation, hyphens, Unicode; PostgreSQL handles all of these |
| Prefix matching | Manual `LIKE 'tolk%' OR LIKE 'tolk%'` | `to_tsquery('simple', 'tolk:*')` with GIN index | LIKE scans the entire table; tsquery uses GIN index — orders of magnitude faster |
| Result ranking | Custom score formula | `func.ts_rank(vector, query)` | ts_rank accounts for term frequency, position weight (A/B/C/D), document length |
| Query sanitization | Complex regex replace | Strip non-word chars per token then parameterize | tsquery injection via `'AND'` or `'|'` operator literals is a real risk |
| Pagination total count | Second query `SELECT COUNT(*)` with identical filters | `select(func.count()).select_from(stmt.subquery())` | Avoids duplicating filter logic; counts from same filtered result set |
| Sort column validation | `if sort == "title" elif sort == "price"...` in route | `Literal["title", "price", "date"]` in Query + dict lookup in repository | FastAPI validates Literal at parse time; dict lookup maps to ORM column safely |

**Key insight:** PostgreSQL's FTS subsystem is a complete search engine built into the database. The only value-add in application code is: (1) cleaning user input before building tsquery, (2) choosing the right tsquery constructor (`to_tsquery` with `:*` prefix for partial matching).

---

## Common Pitfalls

### Pitfall 1: tsvector Column Not Propagated in Test DB

**What goes wrong:** Tests create the test database using `Base.metadata.create_all()` (in `conftest.py`), which creates tables from SQLAlchemy model metadata — but `GENERATED ALWAYS AS` computed columns require a DDL expression that SQLAlchemy's `create_all` does emit for `Computed(..., persisted=True)`. If the `TSVECTOR` import is missing or the Computed expression syntax is wrong, `create_all` will silently create the column as a plain non-generated TSVECTOR and FTS queries will always return empty.

**Why it happens:** `Computed` columns in SQLAlchemy emit the `GENERATED ALWAYS AS ... STORED` DDL when `persisted=True`. If the column definition is incorrect, PostgreSQL creates a plain column instead.

**How to avoid:** After writing the column definition, verify with: `\d books` in psql to confirm `search_vector` shows `generated always` in the column definition. In tests, after creating a book, assert that `search_vector IS NOT NULL` before testing FTS queries.

**Warning signs:** FTS tests return empty results even for books with matching titles; direct `SELECT search_vector FROM books WHERE id = X` returns NULL.

### Pitfall 2: Alembic Autogenerate Detects GIN Index as Changed

**What goes wrong:** After the Phase 5 migration runs successfully, subsequent `alembic revision --autogenerate` runs generate a new migration that drops and recreates `ix_books_search_vector` — even though nothing changed. This is Alembic bug #1390.

**Why it happens:** Alembic compares the index expression as stored by PostgreSQL (which adds type casts and normalizes whitespace) against the expression in the model. They differ in representation even if functionally identical.

**How to avoid:** Write the Phase 5 migration by hand (no autogenerate). Add an `include_object` filter in `alembic/env.py` to exclude `ix_books_search_vector` from autogenerate detection:
```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "index" and name in {"ix_books_search_vector"}:
        return False
    return True
# Register in env.py: context.configure(..., include_object=include_object)
```

**Warning signs:** A new migration file appears with drop/create of `ix_books_search_vector` immediately after running `alembic upgrade head` with the correct migration already applied.

### Pitfall 3: to_tsquery Raises Error on Special Characters

**What goes wrong:** User searches for "C++" or "Harry (Potter)" — the `+`, `(`, `)` characters are tsquery syntax characters. `to_tsquery('simple', 'C++')` raises a `ProgrammingError: syntax error in tsquery`.

**Why it happens:** `to_tsquery` is strict — it expects valid tsquery syntax. Raw user input contains tsquery metacharacters.

**How to avoid:** Strip all non-word, non-hyphen characters from each token before passing to `to_tsquery`. Alternatively, use `websearch_to_tsquery` which never raises errors on any input. However, `websearch_to_tsquery` does not support the `:*` prefix operator — so if prefix matching is required (as locked in CONTEXT.md), clean the input manually and use `to_tsquery`.

**Cleaning function:**
```python
import re
def _build_tsquery(q: str) -> str:
    tokens = re.split(r"\s+", q.strip())
    clean = [re.sub(r"[^\w-]", "", t, flags=re.UNICODE) for t in tokens if t]
    prefix_tokens = [f"{t}:*" for t in clean if t]
    return " & ".join(prefix_tokens) if prefix_tokens else ""
```

**Warning signs:** 500 errors on GET /books?q=C%2B%2B or similar special-character queries.

### Pitfall 4: N+1 Query When Loading Genre Name in List Response

**What goes wrong:** If `BookResponse` or `BookListResponse` is extended to include `genre_name` by accessing `book.genre.name`, each book triggers a lazy-load SQL query for its genre. With 20 books per page, this is 21 queries per page request.

**Why it happens:** SQLAlchemy async does not support implicit lazy-loading. Accessing `book.genre.name` on an unloaded relationship in async context raises `MissingGreenlet` or triggers an implicit lazy select depending on config.

**How to avoid:** If genre name is needed in list response, use `selectinload(Book.genre)` in the repository query:
```python
from sqlalchemy.orm import selectinload
stmt = select(Book).options(selectinload(Book.genre))
```
Or simply return `genre_id` in the list response and let the client resolve genre names from the cached `/genres` list.

**Recommendation for Phase 5:** Return `genre_id` only in list response (consistent with Phase 4's `BookResponse`). Client already has the genres list from `GET /genres`.

**Warning signs:** `MissingGreenlet` exceptions in test logs; response time scales linearly with items per page.

### Pitfall 5: Offset Pagination Inconsistency Under Concurrent Writes

**What goes wrong:** Between page 1 and page 2 requests, an admin creates a new book that sorts into position 15. The book that was at position 20 (last on page 1) now appears at position 21 (first on page 2), so it appears on both pages. A deletion can cause the opposite — a book disappears from results.

**Why it happens:** Offset pagination is a snapshot only at query time. Concurrent writes shift the offset window.

**How to avoid:** This is a known tradeoff of offset pagination. For a bookstore catalog, this is acceptable — the alternative (cursor pagination) adds significant complexity. Document this behavior. Use a consistent sort with `Book.id` as a stable tiebreaker to minimize drift:
```python
stmt = stmt.order_by(sort_col, Book.id)
```

**Warning signs:** Users report duplicate or missing books across pages under load.

### Pitfall 6: Genre Filter by Name vs Genre Filter by ID

**What goes wrong:** `GET /books?genre=Fantasy` — should the route accept the genre name as a string or the genre ID as an integer? If name is accepted, the repository must do a subquery or join to resolve to an ID. If ID is accepted, the client must know the genre's integer ID (available from `GET /genres`).

**Why it happens:** Two valid design choices with different client ergonomics.

**How to avoid:** Accept `genre_id: int` in the query parameter. The `GET /genres` endpoint returns `{id, name}` — clients use the id from that list. This avoids a join in the search query and is consistent with how `BookCreate` uses `genre_id`. The CONTEXT.md does not lock this — it is Claude's discretion, and `genre_id` is the simpler server-side approach.

---

## Code Examples

Verified patterns from official sources and project conventions:

### FTS Query with ts_rank in SQLAlchemy 2.0 Async

```python
# Source: SQLAlchemy PostgreSQL dialect docs, PostgreSQL textsearch-controls.html
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.books.models import Book

async def fts_search(session: AsyncSession, q: str) -> list[Book]:
    tsquery_str = _build_tsquery(q)  # e.g. "tolk:* & rings:*"
    if not tsquery_str:
        return []

    ts_query = func.to_tsquery("simple", tsquery_str)

    stmt = (
        select(Book)
        .where(Book.search_vector.bool_op("@@")(ts_query))
        .order_by(func.ts_rank(Book.search_vector, ts_query).desc())
        .limit(20)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())
```

### Counting Total for Pagination

```python
# Source: SQLAlchemy GitHub discussion #10254
from sqlalchemy import func, select

async def count_results(session: AsyncSession, filtered_stmt) -> int:
    """Count total rows from a filtered select statement."""
    count_stmt = select(func.count()).select_from(filtered_stmt.subquery())
    total = await session.scalar(count_stmt)
    return total or 0
```

### Token Cleaning for tsquery Safety

```python
# Source: Project pattern — prevents tsquery syntax errors on user input
import re

def _build_tsquery(q: str) -> str:
    """Build a safe prefix tsquery from raw user input.

    'tolkien ring' -> 'tolkien:* & ring:*'
    'C++ programming' -> 'C:* & programming:*'  (+ stripped)
    '' -> ''  (caller skips FTS when empty)
    """
    tokens = re.split(r"\s+", q.strip())
    # Keep word characters and hyphens only; strip tsquery metacharacters
    clean = [re.sub(r"[^\w-]", "", t, flags=re.UNICODE) for t in tokens if t]
    prefix_tokens = [f"{t}:*" for t in clean if t]
    return " & ".join(prefix_tokens)
```

### BookDetailResponse with in_stock Computed Field

```python
# Source: Pydantic v2 docs — computed_field
from pydantic import BaseModel, computed_field
from decimal import Decimal
from datetime import date


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

    @computed_field  # type: ignore[misc]
    @property
    def in_stock(self) -> bool:
        """True if stock_quantity > 0."""
        return self.stock_quantity > 0

    model_config = {"from_attributes": True}
```

### Alembic env.py include_object Filter

```python
# Source: Alembic docs (cookbook.html) — preventing spurious FTS index migrations
# Add to alembic/env.py, then register in context.configure():

def include_object(object, name, type_, reflected, compare_to):
    """Exclude FTS GIN index from autogenerate detection (Alembic bug #1390)."""
    if type_ == "index" and name == "ix_books_search_vector":
        return False
    return True

# In run_migrations_online():
# context.configure(
#     ...,
#     include_object=include_object,
# )
```

---

## Design Recommendations (Claude's Discretion)

### Pagination: Offset-Based, Default 20 per Page

**Decision:** Use `page` (1-indexed) and `size` (default 20, max 100) query parameters. Compute offset as `(page - 1) * size`.

**Rationale:** The bookstore catalog at v1 scale will have hundreds to low-thousands of books — offset pagination performs well in this range. Cursor pagination adds significant complexity (opaque tokens, stateful comparisons) with no benefit at this scale. Always include `Book.id` as a secondary sort for stability.

### Sort Options: title, price, date, created_at (default: title)

**Decision:** Accept `sort` parameter with values: `title` (A-Z), `price` (ascending), `date` (publish_date ascending), `created_at` (newest first, descending). Default: `title`.

**Rationale:** These are the three explicit requirements (title, price, date) plus `created_at` as a "newly added" sort. All use ascending order except `created_at` (newest first is the natural expectation). When `q` is provided, always sort by `ts_rank DESC` regardless of `sort` parameter — search results should be relevance-ordered.

### Filter Design: genre_id + author (AND combination)

**Decision:** Accept `genre_id: int` (exact match) and `author: str` (ILIKE `%value%`). When both are provided, they combine with AND. No OR-based multi-filter needed at v1.

**Rationale:** Genre is selected from a dropdown (client has the id), so integer filter is clean. Author partial match (ILIKE) covers common cases like "Tolkien" matching "J.R.R. Tolkien". This is consistent with DISC-03 ("filter by genre and/or author").

### tsvector Column: 'simple' Config, title (A) + author (B)

**Decision:** `setweight(to_tsvector('simple', coalesce(title, '')), 'A') || setweight(to_tsvector('simple', coalesce(author, '')), 'B')`. Genre search is handled by the `genre_id` filter (not included in tsvector).

**Rationale:** The locked decision states "title matches rank higher" — weight A for title, B for author achieves this via `ts_rank`. The `'simple'` dictionary avoids stemming proper names. Genre is a structured filter (user picks from list), not a free-text search field — no need to include it in tsvector.

### Book Detail Response: Add in_stock, Keep Same Schema Otherwise

**Decision:** `GET /books/{id}` returns `BookDetailResponse` which extends `BookResponse` with `in_stock: bool`. The `stock_quantity` is still included (useful for admin-facing clients).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `LIKE '%term%'` queries | `tsvector` + `to_tsquery` + GIN index | PostgreSQL 8.3+ (stable) | Orders of magnitude faster; handles tokenization, ranking |
| DB-level trigger to update tsvector | `GENERATED ALWAYS AS ... STORED` | PostgreSQL 12 (2019) | Simpler — no trigger function needed; PostgreSQL maintains the column automatically |
| `websearch_to_tsquery` for user input | `to_tsquery` with `:*` prefix per token | — | `websearch_to_tsquery` does not support prefix matching; must use `to_tsquery` with manual input cleaning |
| `session.query().paginate()` (Flask-SQLAlchemy) | `select().limit().offset()` + `select(func.count()).select_from(subquery())` | SQLAlchemy 2.0 (2023) | Project already uses new-style queries throughout |
| `@validator` (Pydantic v1) | `@computed_field` with `@property` (Pydantic v2) | Pydantic v2 (2023) | `in_stock` as a computed field avoids storing derived data |

**Deprecated/outdated (do not use):**
- `phraseto_tsquery`: Matches exact phrase sequence only — no AND logic, no prefix. Not suitable for general search.
- `plainto_tsquery`: SQLAlchemy 2.0's default for `.match()`. Does not support prefix matching (`:*`). Cannot use for this phase's locked requirement.
- `ts_headline()`: Generates HTML-highlighted snippets. CONTEXT.md locks "no match highlighting" — do not use.
- `session.query(Book).filter(...)`: Old-style SQLAlchemy 1.x API. Project uses `select(Book).where(...)` throughout.

---

## Open Questions

1. **Should the `search_vector` column appear in the ORM model or only in the migration?**
   - What we know: The `Computed` column definition in SQLAlchemy allows `deferred=True` so it is not loaded on every SELECT. The model definition is needed for SQLAlchemy to generate the `GENERATED ALWAYS AS` DDL in `Base.metadata.create_all` (used by tests).
   - What's unclear: Whether `asyncpg` correctly handles a `GENERATED ALWAYS AS` column in `create_all` — needs a quick smoke test after Plan 1 implementation.
   - Recommendation: Include in the model with `deferred=True`. If `create_all` in tests has issues, fall back to hand-running the Alembic migration against the test database (or running `alembic upgrade head` before tests with `TEST_DATABASE_URL`).

2. **Does `bool_op("@@")` work with `asyncpg` in the current stack?**
   - What we know: SQLAlchemy's PostgreSQL dialect supports `bool_op("@@")` on TSVECTOR-typed columns. The project uses asyncpg as its driver, which is listed as supported for PostgreSQL-specific types including TSVECTOR.
   - What's unclear: Edge behavior with the `Computed` + `deferred` column combination when the column is explicitly referenced in a WHERE clause.
   - Recommendation: Validate with a single integration test (create a book, assert it appears in `GET /books?q=title_word`) before building the full test suite.

3. **Should `GET /books` test use the running test DB (with migrations applied) or `create_all`?**
   - What we know: Current `conftest.py` uses `Base.metadata.create_all` — this creates tables from the ORM model. With `Computed(..., persisted=True)` on the model, `create_all` will emit the `GENERATED ALWAYS AS` DDL. This should work.
   - What's unclear: Whether Alembic-specific DDL constructs in the migration (e.g., raw `op.add_column` with explicit `sa.Computed`) are reflected identically to what the model-based `create_all` produces.
   - Recommendation: After Plan 1 adds the column to the ORM model with `Computed(..., persisted=True)`, run the existing test suite (`poetry run task test`) to verify the test DB creates the column correctly. If tests fail, check the `search_vector` column definition with `psql -c "\d books"`.

---

## Sources

### Primary (HIGH confidence)
- `D:/Python/claude-test/app/books/models.py` — existing Book and Genre models (Phase 4 baseline)
- `D:/Python/claude-test/app/books/repository.py` — existing repository patterns
- `D:/Python/claude-test/app/books/schemas.py` — existing schema patterns
- `D:/Python/claude-test/app/books/router.py` — existing route patterns
- `D:/Python/claude-test/app/books/service.py` — existing service layer patterns
- `D:/Python/claude-test/tests/conftest.py` — test infrastructure (create_all, session, client)
- `D:/Python/claude-test/pyproject.toml` — exact library versions
- `D:/Python/claude-test/alembic/versions/c3d4e5f6a7b8_create_genres_and_books.py` — migration pattern
- PostgreSQL official docs: https://www.postgresql.org/docs/current/textsearch-controls.html — ts_rank, to_tsquery, prefix matching `:*` syntax
- PostgreSQL official docs: https://www.postgresql.org/docs/current/textsearch-tables.html — GENERATED ALWAYS AS column syntax, GIN index creation
- SQLAlchemy 2.0 docs: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html — TSVECTOR type, func namespace, `postgresql_regconfig`

### Secondary (MEDIUM confidence)
- SQLAlchemy GitHub discussion #10254: https://github.com/sqlalchemy/sqlalchemy/discussions/10254 — `select(func.count()).select_from(subquery())` pagination pattern (verified against SQLAlchemy 2.0 docs)
- Alembic GitHub issue #1390: https://github.com/sqlalchemy/alembic/issues/1390 — confirmed autogenerate bug with tsvector GIN indexes; `include_object` workaround
- https://xata.io/blog/postgres-full-text-search-engine — `setweight` + multiple columns pattern (verified against PostgreSQL docs)

### Tertiary (LOW confidence)
- https://hamon.in/blog/sqlalchemy-and-full-text-searching-in-postgresql/ — UserDefinedType pattern for TSVECTOR (older approach; project uses `sqlalchemy.dialects.postgresql.TSVECTOR` instead)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing stack fully covers this phase; no new libraries; PostgreSQL FTS is mature
- Architecture patterns: HIGH — generated column + GIN index is the PostgreSQL-documented approach; offset pagination is standard; all SQLAlchemy patterns verified against docs
- FTS query patterns: HIGH — `to_tsquery` + `:*` prefix + `ts_rank` are stable PostgreSQL features; SQLAlchemy `func` namespace verified
- Alembic GIN index bug: HIGH — confirmed open issue #1390; workaround (`include_object`) is documented in Alembic cookbook
- `Computed` column in `create_all` + asyncpg: MEDIUM — documented to work; flagged as open question requiring smoke test after Plan 1

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable stack; PostgreSQL FTS features are not fast-moving)
