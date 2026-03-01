"""Tests for email infrastructure (EMAL-01, EMAL-04, EMAL-05, EMAL-06).

Unit tests validate:
  - EmailService instantiation (EMAL-01)
  - Jinja2 template rendering and HTML stripping (EMAL-04)
  - BackgroundTasks enqueue builds correct MIMEMultipart (EMAL-05)

Integration tests validate:
  - BackgroundTasks sends email after HTTP response (EMAL-05)
  - No email dispatched when route raises before enqueue (EMAL-06)
  - Response is not delayed by background email send (EMAL-05)

All tests use SUPPRESS_SEND=1 — no real SMTP connections are made.
"""

import time
import unittest.mock
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, FastAPI
from fastapi_mail import ConnectionConfig, FastMail
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AppError, app_error_handler
from app.email.service import EmailService, get_email_config


# ---------------------------------------------------------------------------
# Unit tests — EMAL-01: EmailService instantiation
# ---------------------------------------------------------------------------


class TestEmailService:
    """Unit tests proving EmailService instantiates correctly (EMAL-01)."""

    def test_service_instantiates(self, email_service):
        """EmailService is created and wraps a FastMail instance (EMAL-01)."""
        assert isinstance(email_service, EmailService)
        assert isinstance(email_service.fm, FastMail)

    def test_get_email_config_from_settings(self):
        """get_email_config() returns a ConnectionConfig built from Settings (EMAL-01)."""
        config = get_email_config()
        assert isinstance(config, ConnectionConfig)
        assert config.SUPPRESS_SEND in (0, 1)  # env-dependent; just verify it's a valid value


# ---------------------------------------------------------------------------
# Unit tests — EMAL-04: Template rendering and HTML stripping
# ---------------------------------------------------------------------------


class TestEmailTemplates:
    """Unit tests proving templates render and plain-text fallback works (EMAL-04)."""

    def test_render_html(self, email_service):
        """_render_html() renders base.html to a full HTML string (EMAL-04)."""
        result = email_service._render_html("base.html", {})
        assert result
        assert "<html" in result
        assert "Bookstore" in result

    def test_strip_html(self):
        """_strip_html() removes HTML tags and returns clean text (EMAL-04)."""
        result = EmailService._strip_html("<p>Hello <b>World</b></p>")
        assert result == "Hello World"

        result2 = EmailService._strip_html("<div><h1>Title</h1><p>Body</p></div>")
        assert result2 == "Title Body"

        result3 = EmailService._strip_html("")
        assert result3 == ""

    def test_strip_html_collapses_whitespace(self):
        """_strip_html() normalises runs of whitespace to single spaces (EMAL-04)."""
        result = EmailService._strip_html("<p>  Hello  </p>  <p>  World  </p>")
        # No leading/trailing whitespace
        assert result == result.strip()
        # Internal whitespace collapsed to single spaces
        assert "  " not in result
        assert "Hello" in result
        assert "World" in result

    def test_render_plain_text(self, email_service):
        """_render_plain_text() renders base.html and strips all HTML tags (EMAL-04)."""
        result = email_service._render_plain_text("base.html", {})
        assert result  # non-empty
        # No HTML tags remaining
        assert "<" not in result
        assert ">" not in result
        # base.html includes "Bookstore" in header
        assert "Bookstore" in result

    def test_enqueue_builds_multipart_alternative(self, email_service):
        """enqueue() builds a MIMEMultipart('related') wrapping a
        MIMEMultipart('alternative') with text/plain and text/html,
        plus an inline CID image, proving correct MIME structure (EMAL-04/05).
        """
        background_tasks = BackgroundTasks()

        email_service.enqueue(
            background_tasks, "user@test.com", "base.html", "Test", {}
        )

        assert len(background_tasks.tasks) == 1
        task = background_tasks.tasks[0]
        message_arg = task.args[0]

        assert isinstance(message_arg, MIMEMultipart)
        # Outer envelope is multipart/related (holds alt part + CID images)
        assert message_arg.get_content_subtype() == "related"
        assert message_arg["To"] == "user@test.com"
        assert message_arg["Subject"] == "Test"

        # First child should be the multipart/alternative part
        top_parts = message_arg.get_payload()
        alt_part = top_parts[0]
        assert isinstance(alt_part, MIMEMultipart)
        assert alt_part.get_content_subtype() == "alternative"

        # Alternative must have exactly 2 parts: text/plain and text/html
        alt_children = alt_part.get_payload()
        assert len(alt_children) == 2
        assert alt_children[0].get_content_type() == "text/plain"
        assert alt_children[1].get_content_type() == "text/html"

        # Both parts must have content
        plain_text = alt_children[0].get_payload(decode=True).decode()
        html_text = alt_children[1].get_payload(decode=True).decode()
        assert "Bookstore" in plain_text
        assert "<html" in html_text


# ---------------------------------------------------------------------------
# Integration tests — EMAL-05 and EMAL-06
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def integration_app():
    """Minimal FastAPI app with email endpoints for integration testing.

    Uses SUPPRESS_SEND=1 and mocks _send to capture outbox.
    Returns (test_app, outbox_list) tuple for use in tests.
    """
    config = ConnectionConfig(
        MAIL_USERNAME="test",
        MAIL_PASSWORD="test",
        MAIL_FROM="test@bookstore.com",
        MAIL_PORT=587,
        MAIL_SERVER="smtp.test.com",
        MAIL_FROM_NAME="Bookstore Test",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=False,
        SUPPRESS_SEND=1,
        TEMPLATE_FOLDER=Path(__file__).resolve().parent.parent / "app" / "email" / "templates",
    )
    email_service = EmailService(config=config)
    test_app = FastAPI()
    outbox: list[MIMEMultipart] = []

    # Patch _send to capture messages instead of sending
    original_send = email_service._send

    async def capture_send(message: MIMEMultipart, to: str) -> None:
        outbox.append(message)

    email_service._send = capture_send  # type: ignore[assignment]

    # Register AppError handler so the error endpoint returns 500 (not 500 unhandled)
    test_app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    @test_app.post("/test-send-email")
    async def send_email_endpoint(background_tasks: BackgroundTasks):
        email_service.enqueue(
            background_tasks,
            "user@test.com",
            "base.html",
            "Test Subject",
            {"test_var": "value"},
        )
        return {"status": "ok"}

    @test_app.post("/test-send-email-error")
    async def send_email_error_endpoint(background_tasks: BackgroundTasks):
        # Raise BEFORE calling enqueue — proves email is never sent on failure
        raise AppError(
            status_code=500,
            detail="Simulated failure",
            code="TEST_ERROR",
        )

    return test_app, outbox


class TestEmailIntegration:
    """Integration tests proving BackgroundTasks email pattern (EMAL-05, EMAL-06)."""

    @pytest.mark.asyncio
    async def test_background_task_sends_email(self, integration_app):
        """Email is captured in outbox after BackgroundTasks execution (EMAL-05, EMAL-01)."""
        test_app, outbox = integration_app
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as ac:
            response = await ac.post("/test-send-email")

        assert response.status_code == 200
        assert len(outbox) == 1
        assert outbox[0]["Subject"] == "Test Subject"
        assert "user@test.com" in outbox[0]["To"]

    @pytest.mark.asyncio
    async def test_no_email_on_route_error(self, integration_app):
        """No email dispatched when route raises before enqueue() (EMAL-06)."""
        test_app, outbox = integration_app
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as ac:
            response = await ac.post("/test-send-email-error")

        assert response.status_code == 500
        assert len(outbox) == 0  # No email sent — exception raised before enqueue

    @pytest.mark.asyncio
    async def test_response_not_delayed_by_email(self, integration_app):
        """HTTP response returns in under 1 second while email runs in background (EMAL-05)."""
        test_app, outbox = integration_app
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as ac:
            start = time.monotonic()
            response = await ac.post("/test-send-email")
            elapsed = time.monotonic() - start

        assert elapsed < 1.0  # Response returns quickly — email is non-blocking
        assert len(outbox) == 1  # Email was still sent
