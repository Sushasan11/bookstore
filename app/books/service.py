"""BookService: business rules for book and genre management."""

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
