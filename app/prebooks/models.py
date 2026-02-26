"""PreBooking model and PreBookStatus enum for the pre-booking feature."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, func, text
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

    __table_args__ = (
        Index(
            "uq_pre_bookings_user_book_waiting",
            "user_id",
            "book_id",
            unique=True,
            postgresql_where=text("status = 'waiting'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
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

    book: Mapped["Book"] = relationship()
