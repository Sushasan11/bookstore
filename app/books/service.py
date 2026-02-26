"""BookService: business rules for book and genre management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.books.models import Book, Genre
from app.books.repository import BookRepository, GenreRepository
from app.books.schemas import BookCreate, BookUpdate
from app.core.exceptions import AppError

if TYPE_CHECKING:
    from app.prebooks.repository import PreBookRepository


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
            return await self.book_repo.create(**data.model_dump())
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

    async def set_stock_and_notify(
        self,
        book_id: int,
        quantity: int,
        prebook_repo: PreBookRepository,
    ) -> tuple[Book, list[int]]:
        """Set stock and notify waiting pre-bookers if transitioning from 0 to >0.

        Returns (book, notified_user_ids).
        Caller (router) receives user_ids for background task enqueueing (Phase 12).
        Notification fires ONLY on 0-to-positive transition — locked decision per STATE.md.
        Both stock update and notification occur atomically in the same DB transaction.
        """
        book = await self._get_book_or_404(book_id)
        old_qty = book.stock_quantity
        book = await self.book_repo.set_stock(book, quantity)

        notified_user_ids: list[int] = []
        if old_qty == 0 and quantity > 0:
            notified_user_ids = await prebook_repo.notify_waiting_by_book(book_id)

        return book, notified_user_ids

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

    async def list_books(
        self,
        *,
        q: str | None = None,
        genre_id: int | None = None,
        author: str | None = None,
        sort: str = "title",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Book], int]:
        """Browse catalog with optional FTS search, genre/author filters, sort, and pagination.

        Delegates entirely to BookRepository.search() -- no additional business logic.
        Returns (books, total_count) for the route to wrap in BookListResponse.
        """
        return await self.book_repo.search(
            q=q,
            genre_id=genre_id,
            author=author,
            sort=sort,
            page=page,
            size=size,
        )

    async def list_genres(self) -> list[Genre]:
        return await self.genre_repo.get_all()
