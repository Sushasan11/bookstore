"""create_genres_and_books

Revision ID: c3d4e5f6a7b8
Revises: 7b2f3a8c4d1e
Create Date: 2026-02-25 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "7b2f3a8c4d1e"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Create genres first (books references genres via FK)
    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_genres_name", "genres", ["name"], unique=True)

    # Create books (FK to genres)
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("isbn", sa.String(17), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(2048), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column(
            "stock_quantity",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("genre_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_books_stock_non_negative"),
        sa.CheckConstraint("price > 0", name="ck_books_price_positive"),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_books_title", "books", ["title"])
    op.create_index("ix_books_author", "books", ["author"])
    op.create_index("ix_books_isbn", "books", ["isbn"], unique=True)
    op.create_index("ix_books_genre_id", "books", ["genre_id"])


def downgrade() -> None:
    op.drop_table("books")
    op.drop_table("genres")
