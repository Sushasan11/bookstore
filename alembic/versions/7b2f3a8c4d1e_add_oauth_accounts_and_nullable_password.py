"""add_oauth_accounts_and_nullable_password

Revision ID: 7b2f3a8c4d1e
Revises: 451f9697aceb
Create Date: 2026-02-25 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b2f3a8c4d1e"
down_revision: str | Sequence[str] | None = "451f9697aceb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make hashed_password nullable and create oauth_accounts table."""
    # Make hashed_password nullable for OAuth-only users
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    # Create oauth_accounts table
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("oauth_provider", sa.String(length=50), nullable=False),
        sa.Column("oauth_account_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "oauth_provider",
            "oauth_account_id",
            name="uq_oauth_provider_account",
        ),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])


def downgrade() -> None:
    """Drop oauth_accounts table and make hashed_password non-nullable."""
    op.drop_index("ix_oauth_accounts_user_id", table_name="oauth_accounts")
    op.drop_table("oauth_accounts")

    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False,
    )
