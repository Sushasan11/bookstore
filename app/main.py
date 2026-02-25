"""FastAPI application factory.

Creates and configures the FastAPI application instance with:
  - Global exception handlers (AppError, HTTPException, RequestValidationError, Exception)
  - Health router

Usage:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.books.router import router as books_router
from app.core.health import router as health_router
from app.core.oauth import configure_oauth
from app.users.router import router as auth_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns a fully configured app instance with exception handlers
    and all routers registered.
    """
    application = FastAPI(
        title="Bookstore API",
        version="1.0.0",
        description="Bookstore e-commerce API — browse, purchase, and manage books.",
    )

    # Register exception handlers in precedence order:
    # Most specific (AppError) first, most generic (Exception) last.
    application.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )  # type: ignore[arg-type]
    application.add_exception_handler(Exception, generic_exception_handler)

    # SessionMiddleware required for Authlib OAuth state management (CSRF).
    application.add_middleware(
        SessionMiddleware,
        secret_key=get_settings().SECRET_KEY,
        max_age=600,
    )

    # Register OAuth providers (Google OIDC + GitHub OAuth2).
    configure_oauth()

    # Include routers
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(books_router)

    return application


# Module-level app instance used by uvicorn and tests
app = create_app()
