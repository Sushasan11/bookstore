"""Smoke tests for health endpoint, error handling, and database connectivity.

These tests validate the entire infrastructure stack works end-to-end:
  - FastAPI app serves requests via httpx AsyncClient
  - Exception handlers return structured JSON errors
  - Test database is reachable via the async session fixture
"""

from sqlalchemy import text


async def test_health_returns_200(client):
    """GET /health returns 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


async def test_404_returns_structured_error(client):
    """GET /nonexistent returns 404 with structured error JSON."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "code" in data


async def test_db_session_connects(db_session):
    """SELECT 1 against the test database returns 1."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
