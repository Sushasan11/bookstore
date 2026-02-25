"""Global exception handlers for structured JSON error responses.

All error responses follow the convention:
  {"detail": "message", "code": "ERROR_CODE", "field": "optional_field"}

AppError: Custom application exception with structured error codes.
Handlers registered in app/main.py via add_exception_handler().
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Custom application-level exception with structured error code.

    Usage:
        raise AppError(
            status_code=404,
            detail="Book not found",
            code="BOOK_NOT_FOUND",
            field="book_id",  # optional
        )
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        field: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.field = field
        super().__init__(detail)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle AppError — returns structured JSON with code and optional field."""
    body: dict = {"detail": exc.detail, "code": exc.code}
    if exc.field:
        body["field"] = exc.field
    return JSONResponse(status_code=exc.status_code, content=body)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle Starlette/FastAPI HTTPException — adds code field to response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": f"HTTP_{exc.status_code}"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions — logs real error, returns generic message.

    Never leaks stack traces or internal details regardless of environment.
    """
    logger.exception(
        "Unhandled exception on %s %s: %s", request.method, request.url, exc
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic RequestValidationError — keeps 422 format, adds code field.

    Pydantic error dicts may contain non-serializable objects (e.g. ValueError
    in ctx.error). Convert them to strings to avoid JSON serialization failures.
    """
    errors = []
    for err in exc.errors():
        err = dict(err)
        ctx = err.get("ctx")
        if isinstance(ctx, dict):
            err["ctx"] = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in ctx.items()}
        errors.append(err)
    return JSONResponse(
        status_code=422,
        content={"detail": errors, "code": "VALIDATION_ERROR"},
    )
