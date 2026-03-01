"""Create reviews table.

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-02-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g2h3i4j5k6l7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_reviews_user_book"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
    )
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
    op.create_index("ix_reviews_book_id", "reviews", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_book_id", table_name="reviews")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_table("reviews")
