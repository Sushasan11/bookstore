"""Create pre_bookings table with PreBookStatus enum.

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-02-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

prebookstatus = postgresql.ENUM("waiting", "notified", "cancelled", name="prebookstatus", create_type=False)


def upgrade() -> None:
    op.execute(sa.text("CREATE TYPE prebookstatus AS ENUM ('waiting', 'notified', 'cancelled')"))
    op.create_table(
        "pre_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            prebookstatus,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pre_bookings_user_id", "pre_bookings", ["user_id"])
    op.create_index("ix_pre_bookings_book_id", "pre_bookings", ["book_id"])
    op.create_index(
        "uq_pre_bookings_user_book_waiting",
        "pre_bookings",
        ["user_id", "book_id"],
        unique=True,
        postgresql_where=sa.text("status = 'waiting'"),
    )


def downgrade() -> None:
    op.drop_index("uq_pre_bookings_user_book_waiting", table_name="pre_bookings")
    op.drop_index("ix_pre_bookings_book_id", table_name="pre_bookings")
    op.drop_index("ix_pre_bookings_user_id", table_name="pre_bookings")
    op.drop_table("pre_bookings")
    op.execute(sa.text("DROP TYPE prebookstatus"))
