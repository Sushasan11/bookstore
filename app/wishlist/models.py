"""WishlistItem SQLAlchemy model for the wishlist feature."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.books.models import Book


class WishlistItem(Base):
    """One WishlistItem per (user, book) pair — enforced by uq_wishlist_items_user_book."""

    __tablename__ = "wishlist_items"

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_wishlist_items_user_book"),
    )

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
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    book: Mapped[Book] = relationship()
