"""Tests for email infrastructure (EMAL-01, EMAL-04, EMAL-05, EMAL-06).

Unit tests validate:
  - EmailService instantiation (EMAL-01)
  - Jinja2 template rendering and HTML stripping (EMAL-04)
  - BackgroundTasks enqueue builds correct MessageSchema (EMAL-05)

Integration tests validate:
  - BackgroundTasks sends email after HTTP response (EMAL-05)
  - No email dispatched when route raises before enqueue (EMAL-06)
  - Response is not delayed by background email send (EMAL-05)

All tests use SUPPRESS_SEND=1 — no real SMTP connections are made.
"""

import time
import unittest.mock
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, FastAPI
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.schemas import MultipartSubtypeEnum
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
        # Default Settings has MAIL_SUPPRESS_SEND=1 — verify it is suppressed
        assert config.SUPPRESS_SEND == 1


# ---------------------------------------------------------------------------
# Unit tests — EMAL-04: Template rendering and HTML stripping
# ---------------------------------------------------------------------------


class TestEmailTemplates:
    """Unit tests proving templates render and plain-text fallback works (EMAL-04)."""

    @pytest.mark.asyncio
    async def test_base_template_renders(self, email_service):
        """base.html renders via FastMail and outbox captures the message (EMAL-04)."""
        message = MessageSchema(
            subject="Test",
            recipients=["user@test.com"],
            template_body={"test_var": "hello"},
            subtype=MessageType.html,
        )
        with email_service.fm.record_messages() as outbox:
            await email_service.fm.send_message(message, template_name="base.html")

        assert len(outbox) == 1
        assert "user@test.com" in outbox[0]["To"]
        assert outbox[0]["subject"] == "Test"

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

    def test_enqueue_includes_plain_text_alternative(self, email_service):
        """enqueue() builds MessageSchema with non-empty alternative_body and
        multipart_subtype=alternative, proving plain-text fallback is wired in (EMAL-04/05).
        """
        background_tasks = BackgroundTasks()

        # Capture the message passed to _send via mock
        captured = {}

        original_send = email_service._send

        async def mock_send(message: MessageSchema, template_name: str) -> None:
            captured["message"] = message
            captured["template_name"] = template_name

        with unittest.mock.patch.object(email_service, "_send", mock_send):
            email_service.enqueue(
                background_tasks, "user@test.com", "base.html", "Test", {}
            )

        # BackgroundTasks stores tasks in .tasks — each task is a BackgroundTask namedtuple/object
        # The task was added via background_tasks.add_task(mock_send, message, template_name)
        # We can find the MessageSchema in the tasks list
        assert len(background_tasks.tasks) == 1
        task = background_tasks.tasks[0]
        # BackgroundTask has .func, .args, .kwargs
        message_arg = task.args[0]

        assert isinstance(message_arg, MessageSchema)
        assert message_arg.alternative_body  # non-empty plain-text fallback
        assert message_arg.multipart_subtype == MultipartSubtypeEnum.alternative


# ---------------------------------------------------------------------------
# Integration tests — EMAL-05 and EMAL-06
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def integration_app():
    """Minimal FastAPI app with email endpoints for integration testing.

    Uses SUPPRESS_SEND=1 to capture outbox without real SMTP connections.
    Returns (test_app, fm) tuple for use in tests.
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

    return test_app, email_service.fm


class TestEmailIntegration:
    """Integration tests proving BackgroundTasks email pattern (EMAL-05, EMAL-06)."""

    @pytest.mark.asyncio
    async def test_background_task_sends_email(self, integration_app):
        """Email is captured in outbox after BackgroundTasks execution (EMAL-05, EMAL-01)."""
        test_app, fm = integration_app
        with fm.record_messages() as outbox:
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as ac:
                response = await ac.post("/test-send-email")

        assert response.status_code == 200
        assert len(outbox) == 1
        assert outbox[0]["subject"] == "Test Subject"
        assert "user@test.com" in outbox[0]["To"]

    @pytest.mark.asyncio
    async def test_no_email_on_route_error(self, integration_app):
        """No email dispatched when route raises before enqueue() (EMAL-06)."""
        test_app, fm = integration_app
        with fm.record_messages() as outbox:
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as ac:
                response = await ac.post("/test-send-email-error")

        assert response.status_code == 500
        assert len(outbox) == 0  # No email sent — exception raised before enqueue

    @pytest.mark.asyncio
    async def test_response_not_delayed_by_email(self, integration_app):
        """HTTP response returns in under 1 second while email runs in background (EMAL-05)."""
        test_app, fm = integration_app
        with fm.record_messages() as outbox:
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as ac:
                start = time.monotonic()
                response = await ac.post("/test-send-email")
                elapsed = time.monotonic() - start

        assert elapsed < 1.0  # Response returns quickly — email is non-blocking
        assert len(outbox) == 1  # Email was still sent
