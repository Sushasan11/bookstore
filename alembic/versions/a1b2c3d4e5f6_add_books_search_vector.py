"""Add search_vector tsvector generated column and GIN index to books.

Revision ID: a1b2c3d4e5f6
Revises: c3d4e5f6a7b8
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add generated tsvector column: PostgreSQL maintains this automatically.
    # 'simple' dictionary: no stemming — preserves proper names like "Tolkien".
    # setweight A for title (higher rank), B for author.
    op.add_column(
        "books",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('simple', coalesce(author, '')), 'B')",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    # GIN index for fast full-text search (orders of magnitude faster than LIKE).
    op.create_index(
        "ix_books_search_vector",
        "books",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_books_search_vector", table_name="books")
    op.drop_column("books", "search_vector")
