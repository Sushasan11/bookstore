"""Integration tests for email notifications wiring (Phase 12).

Tests cover:
  - EMAL-02: Order confirmation email sent after successful checkout
  - EMAL-03: Restock alert email sent when pre-booked book is restocked

All tests use SUPPRESS_SEND=1 — no real SMTP connections are made.
Email capture uses a patched _send method on EmailService to collect
MIMEMultipart messages into an outbox list.

Uses unique email prefixes (enotif_admin@, enotif_user@, enotif_user2@)
to avoid cross-test DB contamination.
"""

from email.mime.multipart import MIMEMultipart
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import hash_password
from app.email.service import EmailService, get_email_service
from app.main import app
from app.users.repository import UserRepository


# ---------------------------------------------------------------------------
# Key fixture: email_client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def email_client(db_session, mail_config):
    """AsyncClient with controlled EmailService for outbox capture.

    Overrides get_email_service to inject a test-controlled EmailService instance
    with _send patched to capture messages into an outbox list.
    Also overrides get_db to use the test session.
    """
    controlled_svc = EmailService(config=mail_config)
    outbox: list[MIMEMultipart] = []

    # Patch _send to capture messages
    async def capture_send(message: MIMEMultipart, to: str) -> None:
        outbox.append(message)

    controlled_svc._send = capture_send  # type: ignore[assignment]

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = lambda: controlled_svc

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, outbox

    app.dependency_overrides.clear()
    get_email_service.cache_clear()


# ---------------------------------------------------------------------------
# User/admin fixtures (enotif_ prefix for isolation)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def enotif_admin_headers(email_client, db_session):
    """Create admin user and return (headers, email_client_tuple)."""
    ac, outbox = email_client
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="enotif_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await ac.post("/auth/login", json={"email": "enotif_admin@example.com", "password": "adminpass123"})
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def enotif_user_headers(email_client, db_session):
    """Create regular user and return headers."""
    ac, outbox = email_client
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="enotif_user@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await ac.post("/auth/login", json={"email": "enotif_user@example.com", "password": "userpass123"})
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def enotif_user2_headers(email_client, db_session):
    """Create second regular user for multi-user tests."""
    ac, outbox = email_client
    repo = UserRepository(db_session)
    hashed = await hash_password("user2pass123")
    await repo.create(email="enotif_user2@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await ac.post("/auth/login", json={"email": "enotif_user2@example.com", "password": "user2pass123"})
    assert resp.status_code == 200, f"User2 login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_stocked_book(ac, admin_headers, title="Email Test Book", price="14.99", stock=10):
    """Create a book with stock via admin endpoints. Returns book dict."""
    resp = await ac.post("/books", json={"title": title, "author": "Test Author", "price": price}, headers=admin_headers)
    assert resp.status_code == 201
    book = resp.json()
    stock_resp = await ac.patch(f"/books/{book['id']}/stock", json={"quantity": stock}, headers=admin_headers)
    assert stock_resp.status_code == 200
    return stock_resp.json()


async def _create_oos_book(ac, admin_headers, title="OOS Email Book"):
    """Create an out-of-stock book (default stock_quantity=0). Returns book dict."""
    resp = await ac.post("/books", json={"title": title, "author": "Test Author", "price": "19.99"}, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


def _get_email_html(msg):
    """Extract HTML body from a MIMEMultipart('alternative') message.

    The message has two parts: text/plain and text/html. We return the HTML.
    """
    if isinstance(msg, MIMEMultipart):
        for part in msg.get_payload():
            if hasattr(part, 'get_content_type') and part.get_content_type() == "text/html":
                raw = part.get_payload(decode=True)
                if raw:
                    return raw.decode()
    return None


# ---------------------------------------------------------------------------
# EMAL-02: Order confirmation email tests
# ---------------------------------------------------------------------------


class TestOrderConfirmationEmail:
    """Integration tests proving order confirmation emails fire after checkout (EMAL-02)."""

    async def test_checkout_sends_confirmation_email(
        self,
        email_client,
        enotif_admin_headers,
        enotif_user_headers,
    ):
        """Successful checkout sends exactly 1 confirmation email to the user (EMAL-02)."""
        ac, outbox = email_client
        book = await _create_stocked_book(ac, enotif_admin_headers, title="Email Test Book", stock=10)

        # Add to cart
        cart_resp = await ac.post(
            "/cart/items",
            json={"book_id": book["id"], "quantity": 1},
            headers=enotif_user_headers,
        )
        assert cart_resp.status_code == 201

        # Checkout and capture outbox
        outbox.clear()
        with patch("app.orders.service.MockPaymentService.charge", new=AsyncMock(return_value=True)):
            resp = await ac.post(
                "/orders/checkout",
                json={"force_payment_failure": False},
                headers=enotif_user_headers,
            )

        assert resp.status_code == 201, f"Checkout failed: {resp.json()}"
        assert len(outbox) == 1, f"Expected 1 email, got {len(outbox)}"
        assert "confirmed" in outbox[0]["Subject"].lower(), f"Subject was: {outbox[0]['Subject']}"
        assert "enotif_user@example.com" in outbox[0]["To"]

    async def test_confirmation_email_contains_order_details(
        self,
        email_client,
        enotif_admin_headers,
        enotif_user_headers,
    ):
        """Confirmation email body contains order_id, book title, and total price (EMAL-02)."""
        ac, outbox = email_client
        book = await _create_stocked_book(ac, enotif_admin_headers, title="Email Test Book", price="14.99", stock=10)

        # Add to cart
        cart_resp = await ac.post(
            "/cart/items",
            json={"book_id": book["id"], "quantity": 1},
            headers=enotif_user_headers,
        )
        assert cart_resp.status_code == 201

        # Checkout and capture outbox
        outbox.clear()
        with patch("app.orders.service.MockPaymentService.charge", new=AsyncMock(return_value=True)):
            resp = await ac.post(
                "/orders/checkout",
                json={"force_payment_failure": False},
                headers=enotif_user_headers,
            )

        assert resp.status_code == 201
        order_id = str(resp.json()["id"])
        total_price = resp.json()["total_price"]

        assert len(outbox) == 1
        html_body = _get_email_html(outbox[0])
        assert html_body is not None, "No HTML part found in email message"

        # Email body must contain: order ID, book title, and total price
        assert order_id in html_body, f"order_id {order_id!r} not found in email body"
        assert "Email Test Book" in html_body, "Book title not found in email body"
        assert str(total_price) in html_body or "14.99" in html_body, (
            f"Total price not found in email body. total_price={total_price}"
        )

    async def test_no_email_on_checkout_failure_empty_cart(
        self,
        email_client,
        enotif_user_headers,
    ):
        """Checkout with empty cart returns 422 and sends no email (EMAL-02, EMAL-06)."""
        ac, outbox = email_client

        # No items in cart — attempt checkout
        outbox.clear()
        resp = await ac.post(
            "/orders/checkout",
            json={"force_payment_failure": False},
            headers=enotif_user_headers,
        )

        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.json()}"
        assert resp.json()["code"] == "ORDER_CART_EMPTY"
        assert len(outbox) == 0, f"Expected 0 emails on empty cart, got {len(outbox)}"

    async def test_no_email_on_checkout_failure_insufficient_stock(
        self,
        email_client,
        enotif_admin_headers,
        enotif_user_headers,
    ):
        """Checkout with insufficient stock returns 409 and sends no email (EMAL-02, EMAL-06)."""
        ac, outbox = email_client

        # Create book with stock=1
        book = await _create_stocked_book(
            ac, enotif_admin_headers, title="Low Stock Email Book", stock=1
        )

        # Add quantity=5 to cart (more than stock=1)
        cart_resp = await ac.post(
            "/cart/items",
            json={"book_id": book["id"], "quantity": 5},
            headers=enotif_user_headers,
        )
        assert cart_resp.status_code == 201

        # Checkout must fail with 409
        outbox.clear()
        resp = await ac.post(
            "/orders/checkout",
            json={"force_payment_failure": False},
            headers=enotif_user_headers,
        )

        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.json()}"
        assert resp.json()["code"] == "ORDER_INSUFFICIENT_STOCK"
        assert len(outbox) == 0, f"Expected 0 emails on insufficient stock, got {len(outbox)}"


# ---------------------------------------------------------------------------
# EMAL-03: Restock alert email tests
# ---------------------------------------------------------------------------


class TestRestockAlertEmail:
    """Integration tests proving restock alert emails fire when pre-booked book restocked (EMAL-03)."""

    async def test_restock_sends_alert_to_all_prebookers(
        self,
        email_client,
        enotif_admin_headers,
        enotif_user_headers,
        enotif_user2_headers,
    ):
        """Restocking from 0 to >0 sends alert email to all waiting pre-bookers (EMAL-03)."""
        ac, outbox = email_client

        book = await _create_oos_book(ac, enotif_admin_headers, title="Restock Alert Book")

        # Both users pre-book
        prebook1 = await ac.post("/prebooks", json={"book_id": book["id"]}, headers=enotif_user_headers)
        assert prebook1.status_code == 201

        prebook2 = await ac.post("/prebooks", json={"book_id": book["id"]}, headers=enotif_user2_headers)
        assert prebook2.status_code == 201

        # Admin restocks — capture emails
        outbox.clear()
        restock_resp = await ac.patch(
            f"/books/{book['id']}/stock",
            json={"quantity": 5},
            headers=enotif_admin_headers,
        )

        assert restock_resp.status_code == 200
        assert len(outbox) == 2, f"Expected 2 emails (one per pre-booker), got {len(outbox)}"

        recipient_addresses = " ".join(msg["To"] for msg in outbox)
        assert "enotif_user@example.com" in recipient_addresses, (
            "enotif_user not found in outbox recipients"
        )
        assert "enotif_user2@example.com" in recipient_addresses, (
            "enotif_user2 not found in outbox recipients"
        )

        # Subject should mention back in stock
        for msg in outbox:
            assert "back in stock" in msg["Subject"].lower() or "Restock Alert Book" in msg["Subject"], (
                f"Unexpected subject: {msg['Subject']}"
            )

    async def test_no_restock_email_on_positive_to_positive(
        self,
        email_client,
        enotif_admin_headers,
        enotif_user_headers,
    ):
        """Positive-to-positive stock update sends no restock email (EMAL-03, EMAL-06)."""
        ac, outbox = email_client

        book = await _create_oos_book(ac, enotif_admin_headers, title="Positive Stock Book")

        # User pre-books
        prebook = await ac.post("/prebooks", json={"book_id": book["id"]}, headers=enotif_user_headers)
        assert prebook.status_code == 201

        # First restock: 0 -> 5 (triggers notification + emails)
        outbox.clear()
        first_restock = await ac.patch(
            f"/books/{book['id']}/stock",
            json={"quantity": 5},
            headers=enotif_admin_headers,
        )
        assert first_restock.status_code == 200
        assert len(outbox) == 1  # First restock sends 1 email

        # Second restock: 5 -> 10 (positive-to-positive — must NOT send email)
        outbox.clear()
        second_restock = await ac.patch(
            f"/books/{book['id']}/stock",
            json={"quantity": 10},
            headers=enotif_admin_headers,
        )

        assert second_restock.status_code == 200
        assert len(outbox) == 0, (
            f"Expected 0 emails on positive-to-positive restock, got {len(outbox)}"
        )

    async def test_no_restock_email_when_no_prebookers(
        self,
        email_client,
        enotif_admin_headers,
    ):
        """Restocking a book with no pre-bookers sends no email (EMAL-03, EMAL-06)."""
        ac, outbox = email_client

        book = await _create_oos_book(ac, enotif_admin_headers, title="No Prebookers Book")

        # Restock with no pre-bookers — must send no email
        outbox.clear()
        restock_resp = await ac.patch(
            f"/books/{book['id']}/stock",
            json={"quantity": 5},
            headers=enotif_admin_headers,
        )

        assert restock_resp.status_code == 200
        assert len(outbox) == 0, (
            f"Expected 0 emails when no pre-bookers exist, got {len(outbox)}"
        )

    async def test_cancelled_prebookers_not_emailed(
        self,
        email_client,
        enotif_admin_headers,
        enotif_user_headers,
    ):
        """Cancelled pre-bookers do not receive restock alert email (EMAL-03, EMAL-06)."""
        ac, outbox = email_client

        book = await _create_oos_book(ac, enotif_admin_headers, title="Cancelled Prebook Email Book")

        # User pre-books then cancels
        prebook_resp = await ac.post("/prebooks", json={"book_id": book["id"]}, headers=enotif_user_headers)
        assert prebook_resp.status_code == 201
        prebook_id = prebook_resp.json()["id"]

        cancel_resp = await ac.delete(f"/prebooks/{prebook_id}", headers=enotif_user_headers)
        assert cancel_resp.status_code == 204

        # Admin restocks — cancelled user must NOT be emailed
        outbox.clear()
        restock_resp = await ac.patch(
            f"/books/{book['id']}/stock",
            json={"quantity": 5},
            headers=enotif_admin_headers,
        )

        assert restock_resp.status_code == 200
        assert len(outbox) == 0, (
            f"Expected 0 emails for cancelled pre-booker, got {len(outbox)}"
        )
