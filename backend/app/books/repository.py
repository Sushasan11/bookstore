"""Repository layer for Genre and Book database access."""

import re
from decimal import Decimal

from sqlalchemy import func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book, Genre


def _build_tsquery(q: str) -> str:
    """Convert raw user search input to a safe prefix tsquery string.

    Each whitespace-delimited token gets ':*' appended for prefix matching.
    Non-word, non-hyphen characters are stripped to prevent tsquery injection.

    Examples:
      'tolkien' -> 'tolkien:*'
      'lord rings' -> 'lord:* & rings:*'
      'C++ programming' -> 'C:* & programming:*'
      '' -> '' (caller skips FTS when empty)
    """
    tokens = re.split(r"\s+", q.strip())
    clean = [re.sub(r"[^\w-]", "", t, flags=re.UNICODE) for t in tokens if t]
    prefix_tokens = [f"{t}:*" for t in clean if t]
    return " & ".join(prefix_tokens)


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

    async def search(
        self,
        *,
        q: str | None = None,
        genre_id: int | None = None,
        author: str | None = None,
        sort: str = "title",
        sort_dir: str = "asc",
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Book], int]:
        """Return (books, total_count) for the given search/filter/sort/page.

        When q is provided: filters by FTS match AND sorts by ts_rank DESC
          (relevance sort overrides the sort parameter -- locked decision).
        When q is absent: sorts by the sort parameter.

        Sort values: 'title' (A-Z), 'price' (asc), 'date' (publish_date asc),
          'created_at' (desc -- newest first), 'avg_rating' (desc -- highest rated first).
          sort_dir='desc' reverses all sorts except 'avg_rating' (which defaults to desc).
          Tiebreaker: Book.id asc (stable pagination).

        genre_id and author filters combine with AND when both are provided.
        min_price and max_price filter by price range (inclusive).
        """
        stmt = select(Book)

        # FTS filter
        if q:
            tsquery_str = _build_tsquery(q)
            if tsquery_str:
                ts_query = func.to_tsquery("simple", tsquery_str)
                stmt = stmt.where(Book.search_vector.bool_op("@@")(ts_query))

        # Genre filter (exact match by ID -- clients pick from GET /genres list)
        if genre_id is not None:
            stmt = stmt.where(Book.genre_id == genre_id)

        # Author filter (case-insensitive substring -- covers "J.R.R. Tolkien" when searching "tolkien")
        if author:
            stmt = stmt.where(Book.author.ilike(f"%{author}%"))

        # Price range filter (inclusive bounds)
        if min_price is not None:
            stmt = stmt.where(Book.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Book.price <= max_price)

        # Sort order
        if q:
            tsquery_str_for_rank = _build_tsquery(q)
            if tsquery_str_for_rank:
                ts_query_rank = func.to_tsquery("simple", tsquery_str_for_rank)
                stmt = stmt.order_by(
                    func.ts_rank(Book.search_vector, ts_query_rank).desc(),
                    Book.id,
                )
            # If tsquery_str is empty (all special chars stripped), fall through to default sort
            else:
                stmt = stmt.order_by(Book.title, Book.id)
        elif sort == "avg_rating":
            # Left-join subquery against reviews to compute avg rating per book
            from app.reviews.models import Review  # avoid circular at module level

            avg_sub = (
                select(
                    Review.book_id,
                    func.avg(Review.rating).label("avg_rating"),
                )
                .where(Review.deleted_at.is_(None))
                .group_by(Review.book_id)
                .subquery()
            )
            stmt = stmt.outerjoin(avg_sub, Book.id == avg_sub.c.book_id)
            # Default for avg_rating: desc (highest first); sort_dir overrides
            if sort_dir == "asc":
                stmt = stmt.order_by(nulls_last(avg_sub.c.avg_rating.asc()), Book.id)
            else:
                stmt = stmt.order_by(nulls_last(avg_sub.c.avg_rating.desc()), Book.id)
        else:
            # For created_at, default is desc (newest first); sort_dir overrides
            if sort == "created_at":
                if sort_dir == "asc":
                    order_col = Book.created_at.asc()
                else:
                    order_col = Book.created_at.desc()
            else:
                sort_col_map = {
                    "title": Book.title,
                    "price": Book.price,
                    "date": Book.publish_date,
                }
                col = sort_col_map.get(sort, Book.title)
                if sort_dir == "desc":
                    order_col = col.desc()
                else:
                    order_col = col.asc()
            stmt = stmt.order_by(order_col, Book.id)

        # Total count BEFORE pagination (reuses same filters)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        # Apply pagination
        offset = (page - 1) * size
        stmt = stmt.limit(size).offset(offset)

        result = await self.session.execute(stmt)
        books = list(result.scalars().all())

        return books, total or 0
