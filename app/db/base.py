"""SQLAlchemy DeclarativeBase.

Defines the DeclarativeBase that all models inherit from.
Model imports for Alembic discovery live in alembic/env.py to avoid
circular imports (models import Base from here).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
