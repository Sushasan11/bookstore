"""SQLAlchemy DeclarativeBase and model aggregator.

This file has TWO purposes:
1. Defines the DeclarativeBase that all models inherit from
2. Imports all models so Alembic can discover them for autogenerate migrations

Without model imports here, Alembic sees an empty metadata and produces
empty or destructive migrations. Add each model import as its phase is added.

Example imports to add in later phases:
    # Phase 2 (Users): from app.users.models import User  # noqa: F401
    # Phase 4 (Books): from app.books.models import Book  # noqa: F401
    # Phase 5 (Cart):  from app.cart.models import CartItem  # noqa: F401
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Model imports — add each model here as phases are implemented
# No models exist yet in Phase 1; imports will be added in subsequent phases
