"""Catalog HTTP endpoints: book CRUD, stock management, genre taxonomy."""

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.books.repository import BookRepository, GenreRepository
from app.reviews.repository import ReviewRepository
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
from app.email.service import EmailSvc

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
    min_price: Decimal | None = Query(None, ge=0, description="Minimum price filter (inclusive)"),
    max_price: Decimal | None = Query(None, ge=0, description="Maximum price filter (inclusive)"),
    sort: Literal["title", "price", "date", "created_at", "avg_rating"] = Query(
        "title", description="Sort order: title (A-Z), price, date (publish_date), created_at (newest first), avg_rating (highest rated first)"
    ),
    sort_dir: Literal["asc", "desc"] = Query("asc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
) -> BookListResponse:
    """Browse the book catalog. Public -- no auth required.

    Supports pagination (page/size), sorting (sort + sort_dir), full-text search (q),
    and filtering by genre (genre_id), author, and price range (min_price/max_price).
    Filters combine with AND.

    When q is present, results are sorted by relevance (ts_rank) regardless of sort param.
    sort=avg_rating uses a left-join subquery on reviews; books with no reviews sort last.
    """
    service = _make_service(db)
    books, total = await service.list_books(
        q=q,
        genre_id=genre_id,
        author=author,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        sort_dir=sort_dir,
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
    """Get book by ID including stock status and rating aggregates. Public -- no auth required.

    Returns in_stock boolean (true when stock_quantity > 0).
    Returns avg_rating (float | None) rounded to 1 decimal place.
    Returns review_count (int), 0 when no reviews exist.
    404 if book not found.
    """
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
    book_id: int,
    body: StockUpdate,
    db: DbSession,
    admin: AdminUser,
    background_tasks: BackgroundTasks,
    email_svc: EmailSvc,
) -> BookResponse:
    """Set absolute stock quantity. Admin only.

    When stock transitions from 0 to >0, all waiting pre-bookings are atomically
    notified (status set to 'notified' with notified_at timestamp).
    Enqueues restock alert emails for all notified users via BackgroundTasks.

    quantity >= 0 enforced by Pydantic (ge=0) and DB CHECK CONSTRAINT.
    404 if book not found.
    """
    from app.prebooks.repository import (
        PreBookRepository,  # avoid circular at module level
    )
    from app.users.repository import UserRepository

    service = _make_service(db)
    prebook_repo = PreBookRepository(db)
    book, notified_user_ids = await service.set_stock_and_notify(
        book_id, body.quantity, prebook_repo
    )

    # Enqueue restock alert emails for all notified users (EMAL-03)
    if notified_user_ids:
        user_repo = UserRepository(db)
        email_map = await user_repo.get_emails_by_ids(notified_user_ids)
        for uid, email_addr in email_map.items():
            email_svc.enqueue(
                background_tasks,
                to=email_addr,
                template_name="restock_alert.html",
                subject=f"'{book.title}' is back in stock",
                context={"book_title": book.title, "book_id": book.id},
            )

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
