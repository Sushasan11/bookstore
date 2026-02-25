"""Repository layer for Genre and Book database access."""

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
        result = await self.session.execute(select(Genre).where(Genre.name == name))
        return result.scalar_one_or_none()

    async def get_by_id(self, genre_id: int) -> Genre | None:
        result = await self.session.execute(select(Genre).where(Genre.id == genre_id))
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
        result = await self.session.execute(select(Book).where(Book.id == book_id))
        return result.scalar_one_or_none()

    async def get_by_isbn(self, isbn: str) -> Book | None:
        result = await self.session.execute(select(Book).where(Book.isbn == isbn))
        return result.scalar_one_or_none()

    async def create(self, **kwargs: object) -> Book:
        book = Book(**kwargs)
        self.session.add(book)
        await self.session.flush()
        return book

    async def update(self, book: Book, **kwargs: object) -> Book:
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
