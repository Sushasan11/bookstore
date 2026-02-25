"""FastAPI dependency injection functions.

Provides reusable FastAPI dependencies for database session management.
The DbSession type alias allows routes to declare `db: DbSession` instead
of the verbose `db: AsyncSession = Depends(get_db)`.
"""
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-request AsyncSession with commit/rollback semantics.

    - On success: commits the transaction before closing the session.
    - On exception: rolls back the transaction and re-raises the exception.
    - Always: closes the session in the finally block.

    Usage in routes:
        async def my_route(db: DbSession):
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for route parameter declarations — prefer this over the verbose form
DbSession = Annotated[AsyncSession, Depends(get_db)]
