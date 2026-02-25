"""Catalog HTTP endpoints: book CRUD, stock management, genre taxonomy."""

from typing import Literal

from fastapi import APIRouter, Query, status

from app.books.repository import BookRepository, GenreRepository
from app.books.schemas import (
    BookCreate,
    BookDetailResponse,
    BookListResponse,
    BookResponse,
    BookUpdate,
    GenreCreate,
    GenreResponse,
    StockUpdate,
)
from app.books.service import BookService
from app.core.deps import AdminUser, DbSession

router = APIRouter(tags=["catalog"])


def _make_service(db: DbSession) -> BookService:
    """Instantiate BookService with repositories bound to the current DB session."""
    return BookService(
        book_repo=BookRepository(db),
        genre_repo=GenreRepository(db),
    )


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    body: BookCreate, db: DbSession, admin: AdminUser
) -> BookResponse:
    """Create a new book. Admin only.

    Required: title, author, price.
    Optional: isbn (validated checksum), genre_id, description, cover_image_url, publish_date.
    409 if ISBN already exists.
    """
    service = _make_service(db)
    book = await service.create_book(body)
    return BookResponse.model_validate(book)


@router.get("/books", response_model=BookListResponse)
async def list_books(
    db: DbSession,
    q: str | None = Query(None, description="Full-text search across title and author"),
    genre_id: int | None = Query(None, description="Filter by genre ID (from GET /genres)"),
    author: str | None = Query(None, description="Filter by author name (case-insensitive partial match)"),
    sort: Literal["title", "price", "date", "created_at"] = Query(
        "title", description="Sort order: title (A-Z), price (asc), date (publish_date asc), created_at (newest first)"
    ),
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
) -> BookListResponse:
    """Browse the book catalog. Public -- no auth required.

    Supports pagination (page/size), sorting (sort), full-text search (q),
    and filtering by genre (genre_id) and author. Filters combine with AND.

    When q is present, results are sorted by relevance (ts_rank) regardless of sort param.
    """
    service = _make_service(db)
    books, total = await service.list_books(
        q=q,
        genre_id=genre_id,
        author=author,
        sort=sort,
        page=page,
        size=size,
    )
    return BookListResponse(
        items=[BookResponse.model_validate(b) for b in books],
        total=total,
        page=page,
        size=size,
    )


@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: int, db: DbSession) -> BookDetailResponse:
    """Get book by ID including stock status. Public -- no auth required.

    Returns in_stock boolean (true when stock_quantity > 0).
    404 if book not found.
    """
    service = _make_service(db)
    book = await service._get_book_or_404(book_id)
    return BookDetailResponse.model_validate(book)


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int, body: BookUpdate, db: DbSession, admin: AdminUser
) -> BookResponse:
    """Update book fields. Admin only.

    All fields optional -- only provided fields are updated.
    404 if book not found. 409 if ISBN conflicts with existing book.
    """
    service = _make_service(db)
    book = await service.update_book(book_id, body)
    return BookResponse.model_validate(book)


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, db: DbSession, admin: AdminUser) -> None:
    """Delete a book permanently. Admin only.

    Hard delete -- Phase 4 has no FK references to books from other tables yet.
    404 if book not found.
    """
    service = _make_service(db)
    await service.delete_book(book_id)


@router.patch("/books/{book_id}/stock", response_model=BookResponse)
async def update_stock(
    book_id: int, body: StockUpdate, db: DbSession, admin: AdminUser
) -> BookResponse:
    """Set absolute stock quantity. Admin only.

    quantity >= 0 enforced by Pydantic (ge=0) and DB CHECK CONSTRAINT.
    Absolute set (not increment/decrement) -- Phase 7 handles stock decrement via SELECT FOR UPDATE.
    404 if book not found.
    """
    service = _make_service(db)
    book = await service.set_stock(book_id, body.quantity)
    return BookResponse.model_validate(book)


@router.post(
    "/genres", response_model=GenreResponse, status_code=status.HTTP_201_CREATED
)
async def create_genre(
    body: GenreCreate, db: DbSession, admin: AdminUser
) -> GenreResponse:
    """Create a new genre. Admin only.

    409 if genre name already exists (case-sensitive).
    """
    service = _make_service(db)
    genre = await service.create_genre(body.name)
    return GenreResponse.model_validate(genre)


@router.get("/genres", response_model=list[GenreResponse])
async def list_genres(db: DbSession) -> list[GenreResponse]:
    """List all genres alphabetically. Public -- no auth required.

    Genres are reference data. Empty list if no genres yet.
    """
    service = _make_service(db)
    genres = await service.list_genres()
    return [GenreResponse.model_validate(g) for g in genres]
