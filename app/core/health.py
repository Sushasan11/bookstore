"""Health check endpoint.

Application-level ping only — does NOT check database connectivity.
Database connectivity is verified separately via the test suite (Plan 04).

GET /health → {"status": "ok", "version": "1.0.0"}
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Return application health status.

    This is a lightweight application-level ping.
    It does not check database connectivity, external services, or dependencies.
    """
    return {"status": "ok", "version": "1.0.0"}
