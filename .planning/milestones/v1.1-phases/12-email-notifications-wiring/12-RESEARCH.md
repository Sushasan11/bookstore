# Phase 12: Email Notifications Wiring - Research

**Researched:** 2026-02-26
**Domain:** FastAPI BackgroundTasks email dispatch — wiring existing EmailService into checkout and stock-update flows
**Confidence:** HIGH

---

## Summary

Phase 12 is a wiring phase, not an infrastructure phase. All email infrastructure (fastapi-mail, EmailService, Jinja2 templates, BackgroundTasks pattern, SUPPRESS_SEND for tests) was built in Phase 9. Phase 11 built the restock broadcast mechanism and left a clearly marked `# Phase 12 wires email here` comment in `app/books/router.py`. Phase 12's job is to:

1. Create two Jinja2 HTML email templates (`order_confirmation.html`, `restock_alert.html`) that extend `base.html`
2. Wire `EmailService.enqueue()` into the checkout router (`POST /orders/checkout`) using the user's email from a DB lookup
3. Wire `EmailService.enqueue()` into the stock-update router (`PATCH /books/{book_id}/stock`) for each `notified_user_id` returned by `set_stock_and_notify()` — which requires a batch of DB lookups to resolve user emails
4. Write integration tests proving email fires on success and is suppressed on failure/rollback

The critical open question flagged in STATE.md — how to get the user's email at routing time — is the primary architectural decision: the JWT payload contains only `sub` (user_id) and `role`, not the email address. A DB fetch is required. Both the checkout and restock-alert paths need this, each with slightly different mechanics.

**Primary recommendation:** For checkout, fetch the user's email from DB inside the router using the existing `user_id` (already in JWT sub); the get_db session is still open at that point, so no extra dependency is needed. For restock alerts, `notify_waiting_by_book` already returns `list[int]` of user_ids — do a single batch fetch of user emails from those IDs, then enqueue one email per user. This keeps the service layer clean (no email concerns) and the router as the only email-dispatch site.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EMAL-02 | User receives order confirmation email after successful checkout | EmailService.enqueue() call in checkout router after service.checkout() returns the Order object; user email from DB fetch by user_id; Order object carries id, items (with title, quantity, unit_price), and computed total_price |
| EMAL-03 | User receives restock alert email when a pre-booked book is restocked | EmailService.enqueue() call in update_stock router for each user_id in notified_user_ids returned by set_stock_and_notify(); batch DB fetch of emails by user_ids; book title available from Book object already returned |
</phase_requirements>

---

## Standard Stack

### Core (all already installed — no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi-mail | 1.6.2 | Email sending via FastMail | Already integrated in Phase 9 |
| jinja2 | (pinned by fastapi-mail) | Template rendering | Already used by EmailService._jinja_env |
| fastapi BackgroundTasks | built-in | Non-blocking post-commit dispatch | Structural pattern from Phase 9 |
| sqlalchemy (asyncpg) | (project version) | User email DB lookup | Already in every router |

### No New Dependencies

Phase 12 requires zero new package installations. Everything is already wired. The only additions are:
- Two new Jinja2 template files under `app/email/templates/`
- Modifications to two existing router functions
- New tests in `tests/test_orders.py` and `tests/test_catalog.py` (or a new `tests/test_email_notifications.py`)

---

## Architecture Patterns

### Recommended Project Structure

No new directories. Files to add/modify:

```
app/
├── email/
│   └── templates/
│       ├── base.html                        # EXISTS — do not modify
│       ├── order_confirmation.html          # NEW — extends base.html
│       └── restock_alert.html               # NEW — extends base.html
├── orders/
│   └── router.py                            # MODIFY checkout() to enqueue email
├── books/
│   └── router.py                            # MODIFY update_stock() to enqueue emails
└── users/
    └── repository.py                        # POSSIBLY ADD: get_emails_by_ids() method

tests/
└── test_email_notifications.py              # NEW (or extend existing test files)
```

### Pattern 1: Order Confirmation Email Dispatch (Checkout Router)

**What:** After successful checkout, fetch the user's email and enqueue a confirmation email.

**When to use:** Inside `checkout()` route handler, after `service.checkout()` returns the Order object.

**Key facts from codebase:**
- `current_user["sub"]` is a string user_id (cast to int with `int(current_user["sub"])`)
- The `db` (DbSession) session is still open inside the route handler — it commits after `yield` in `get_db()`
- `BackgroundTasks` is a FastAPI dependency injected via function parameter
- `EmailSvc` (from `app.email.service`) is the injection alias: `EmailSvc = Annotated[EmailService, Depends(get_email_service)]`
- The Order object returned by `service.checkout()` already has eagerly-loaded `items` and each `item.book` (via `session.refresh` in `create_order`)

**Example pattern:**

```python
# app/orders/router.py — modified checkout()
from fastapi import APIRouter, BackgroundTasks, status
from app.email.service import EmailSvc
from app.users.repository import UserRepository

@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    body: CheckoutRequest,
    db: DbSession,
    current_user: ActiveUser,
    background_tasks: BackgroundTasks,
    email_svc: EmailSvc,
) -> OrderResponse:
    user_id = int(current_user["sub"])
    service = _make_service(db)
    order = await service.checkout(user_id, body)

    # Fetch user email for confirmation — DB session still open here
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user:
        email_svc.enqueue(
            background_tasks,
            to=user.email,
            template_name="order_confirmation.html",
            subject="Your order is confirmed",
            context={
                "order_id": order.id,
                "items": [
                    {
                        "title": item.book.title if item.book else "Unknown",
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in order.items
                ],
                "total_price": str(order_response.total_price),
            },
        )

    return OrderResponse.model_validate(order)
```

**Critical: EMAL-06 compliance.** BackgroundTasks run post-response, which is post-commit (see `get_db()` in `app/core/deps.py`). This is a structural guarantee: if `service.checkout()` raises (cart empty, insufficient stock, payment fail), the router never reaches the `enqueue()` call. No email is sent on any error path.

### Pattern 2: Restock Alert Email Dispatch (Stock-Update Router)

**What:** After stock update, enqueue one restock-alert email per notified user.

**When to use:** Inside `update_stock()` route handler, replacing the current `_ = notified_user_ids` placeholder.

**Key facts from codebase:**
- `set_stock_and_notify()` already returns `(book, notified_user_ids: list[int])`
- The code at line 144 of `app/books/router.py` is literally `_ = notified_user_ids` — a placeholder left for Phase 12
- The `book` object is available and has `book.title`
- `notified_user_ids` may be empty (no pre-bookers) or contain multiple user IDs
- Need to fetch email addresses for all notified users — a batch query is more efficient than N individual `get_by_id` calls

**Batch email fetch options:**

Option A — Add `get_emails_by_ids()` to UserRepository:
```python
# app/users/repository.py — add method
async def get_emails_by_ids(self, user_ids: list[int]) -> dict[int, str]:
    """Fetch {user_id: email} mapping for a list of user IDs."""
    if not user_ids:
        return {}
    result = await self.session.execute(
        select(User.id, User.email).where(User.id.in_(user_ids))
    )
    return {row.id: row.email for row in result}
```

Option B — Loop `get_by_id()` calls (N queries, acceptable at v1.1 pre-booking volumes since notify_waiting_by_book is already bulk, and user counts per book are low):
```python
for uid in notified_user_ids:
    user = await user_repo.get_by_id(uid)
    if user:
        email_svc.enqueue(...)
```

**Recommendation:** Add `get_emails_by_ids()` method to UserRepository (Option A). Single query regardless of pre-booker count. Cleaner and future-proof.

**Example pattern:**

```python
# app/books/router.py — modified update_stock()
@router.patch("/books/{book_id}/stock", response_model=BookResponse)
async def update_stock(
    book_id: int,
    body: StockUpdate,
    db: DbSession,
    admin: AdminUser,
    background_tasks: BackgroundTasks,
    email_svc: EmailSvc,
) -> BookResponse:
    from app.prebooks.repository import PreBookRepository  # existing local import
    from app.users.repository import UserRepository

    service = _make_service(db)
    prebook_repo = PreBookRepository(db)
    book, notified_user_ids = await service.set_stock_and_notify(
        book_id, body.quantity, prebook_repo
    )

    if notified_user_ids:
        user_repo = UserRepository(db)
        email_map = await user_repo.get_emails_by_ids(notified_user_ids)
        for uid, email in email_map.items():
            email_svc.enqueue(
                background_tasks,
                to=email,
                template_name="restock_alert.html",
                subject=f"{book.title} is back in stock",
                context={"book_title": book.title, "book_id": book.id},
            )

    return BookResponse.model_validate(book)
```

### Pattern 3: Jinja2 Template Structure

**What:** HTML email templates extending `base.html` using Jinja2 block inheritance.

**Template folder:** `app/email/templates/` (already configured in `EmailService` as `TEMPLATE_FOLDER`)

**base.html blocks available:**
- `{% block title %}` — `<title>` tag content
- `{% block content %}` — main body content area
- `{% block footer %}` — footer text (optional override)

**order_confirmation.html example:**
```html
{% extends "base.html" %}
{% block title %}Order Confirmed — Bookstore{% endblock %}
{% block content %}
<h2 style="color: #1a202c;">Your order is confirmed!</h2>
<p>Order #{{ order_id }}</p>
<table width="100%" style="border-collapse: collapse;">
  <thead>
    <tr>
      <th style="text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0;">Book</th>
      <th style="text-align: right; padding: 8px; border-bottom: 1px solid #e2e8f0;">Qty</th>
      <th style="text-align: right; padding: 8px; border-bottom: 1px solid #e2e8f0;">Price</th>
    </tr>
  </thead>
  <tbody>
    {% for item in items %}
    <tr>
      <td style="padding: 8px; border-bottom: 1px solid #f4f4f4;">{{ item.title }}</td>
      <td style="text-align: right; padding: 8px; border-bottom: 1px solid #f4f4f4;">{{ item.quantity }}</td>
      <td style="text-align: right; padding: 8px; border-bottom: 1px solid #f4f4f4;">${{ item.unit_price }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<p style="text-align: right; font-weight: bold; margin-top: 16px;">Total: ${{ total_price }}</p>
{% endblock %}
```

**restock_alert.html example:**
```html
{% extends "base.html" %}
{% block title %}Back in Stock — {{ book_title }}{% endblock %}
{% block content %}
<h2 style="color: #1a202c;">Good news! Your pre-booked book is back.</h2>
<p><strong>{{ book_title }}</strong> is now back in stock.</p>
<p>Visit the bookstore to add it to your cart before it sells out again.</p>
{% endblock %}
```

### Pattern 4: Test Pattern for Email Integration

**What:** Capture emails in outbox using `fm.record_messages()` while making real HTTP calls through the test client.

**Established pattern (from Phase 9 tests):**
- `record_messages()` is a **sync** context manager — use `with`, not `async with` (confirmed in STATE.md)
- Tests use `SUPPRESS_SEND=1` (default in all test settings)
- The `email_service` fixture in `conftest.py` creates a standalone `EmailService` instance — but for integration tests that go through the real app, the app uses its own `get_email_service()` singleton

**Critical complication for integration tests:** The app-level `EmailService` (injected via `EmailSvc` dependency) is created by `get_email_service()` which is `@lru_cache`. Its internal `FastMail` instance (`email_svc.fm`) is what captures messages. Integration tests must either:
1. Override the `get_email_service` dependency in the test app to inject a known `EmailService` instance whose `fm` reference they control
2. Or mock `email_svc.enqueue` to assert it was called with the right args (simpler, but doesn't test template rendering end-to-end)

**Recommended approach for Phase 12 tests:** Override `get_email_service` dependency in tests to inject a controlled `EmailService` instance (same pattern as the existing `get_db` override in `conftest.py`). This allows `with controlled_fm.record_messages() as outbox` to work:

```python
from app.email.service import get_email_service

@pytest_asyncio.fixture
async def email_client(db_session, mail_config):
    """AsyncClient with email capture wired to the app."""
    controlled_svc = EmailService(config=mail_config)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = lambda: controlled_svc

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, controlled_svc.fm

    app.dependency_overrides.clear()
```

Then in tests:
```python
async def test_checkout_sends_confirmation_email(email_client, ...):
    ac, fm = email_client
    with fm.record_messages() as outbox:
        resp = await ac.post("/orders/checkout", ...)
    assert len(outbox) == 1
    assert "order" in outbox[0]["subject"].lower()
```

### Anti-Patterns to Avoid

- **Sending email inside the service layer:** EmailService must only be called from routers. Services return data; routers decide what side effects to trigger. Never pass EmailService into OrderService or BookService.
- **Sending email before the DB commit:** BackgroundTasks are the structural guarantee. Never `await email_svc._send(...)` directly from a route — always use `enqueue()` which goes through `background_tasks.add_task()`.
- **Sending email in error paths:** Never enqueue before checking for possible failures. The current checkout router already has all errors raised inside `service.checkout()`, so any code after that line is guaranteed to be on the success path.
- **Blocking on user email fetch:** The DB fetch for user email is a fast indexed lookup by primary key. It does not slow the response because the response hasn't been sent yet at that point — but it does add latency. Keep it lightweight (single query for one user ID, or batch query for multiple).
- **Assuming email field is in JWT:** JWT payload has only `sub` (user_id string) and `role`. Never call `current_user["email"]` — it will KeyError. Always do a DB fetch.
- **Using `async with` on `record_messages()`:** Per STATE.md decision from Phase 09-02, `record_messages()` is a sync context manager. Use `with`, not `async with`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML email templates | Inline HTML strings in Python | Jinja2 `.html` files in `app/email/templates/` | Already configured, already used, auto-stripped for plain text |
| Email dispatch mechanism | Any SMTP wrapper | `EmailService.enqueue()` | Phase 9 built this; it handles multipart, plain-text fallback, error logging, and suppression |
| Background task execution | Thread pools, asyncio.create_task | `BackgroundTasks` from FastAPI | Structural post-commit safety guarantee via get_db dependency lifecycle |
| Test email capture | Monkey-patching SMTP | `fm.record_messages()` context manager | Built into fastapi-mail 1.6.2 |
| User lookup | Raw SQL | `UserRepository.get_by_id()` / new `get_emails_by_ids()` | Consistent with all other repository usage across the project |

**Key insight:** The entire Phase 12 implementation is wiring existing pieces. The risk is in the edges: getting the user's email without a second DB roundtrip per email when there are many notified users, and testing that the email actually reaches the outbox through the real HTTP stack.

---

## Common Pitfalls

### Pitfall 1: User Email Not in JWT — KeyError at Runtime

**What goes wrong:** Developer accesses `current_user["email"]` expecting it to be in the JWT payload. It's not. KeyError at runtime.

**Why it happens:** JWT payload contains only `sub` (user_id as string) and `role`. This was a deliberate minimal-JWT design. STATE.md explicitly flags this: "JWT payload contains sub (user_id) and role but not email."

**How to avoid:** Always do `user_repo.get_by_id(int(current_user["sub"]))` to fetch the User object, then use `user.email`. The `get_db` session is still open inside the route handler, so this is a cheap indexed PK lookup.

**Warning signs:** Any code reading `current_user["email"]` or `current_user.get("email")`.

### Pitfall 2: Email Sent When Checkout Fails (EMAL-06 Violation)

**What goes wrong:** `email_svc.enqueue()` is called before or during the checkout logic, meaning it's enqueued even when `service.checkout()` raises an exception.

**Why it happens:** Misunderstanding when BackgroundTasks are executed vs when they are enqueued. Enqueuing happens immediately; execution happens post-response. If you enqueue before the error is raised, the background task runs even though the transaction rolled back.

**How to avoid:** Always call `email_svc.enqueue()` AFTER `await service.checkout()` returns successfully. The current `OrderService.checkout()` raises all errors before returning the Order object. Code after `order = await service.checkout(user_id, body)` is guaranteed to be on the success path.

**Warning signs:** `enqueue()` call appears before `service.checkout()` or inside a try block that might catch the checkout errors and still proceed.

### Pitfall 3: N+1 Email Fetches for Restock Alerts

**What goes wrong:** Looping over `notified_user_ids` and calling `get_by_id()` for each user individually results in N database queries.

**Why it happens:** The convenient `get_by_id` method fetches one user at a time. With 50 pre-bookers, that's 50 queries before the response returns.

**How to avoid:** Add `get_emails_by_ids(user_ids: list[int]) -> dict[int, str]` to `UserRepository` using `User.id.in_(user_ids)`. A single query fetches all emails. Call this before the enqueue loop.

**Warning signs:** `for uid in notified_user_ids: user = await repo.get_by_id(uid)` pattern in a router.

### Pitfall 4: Circular Import from EmailSvc in Service Layer

**What goes wrong:** EmailService is imported into `app/orders/service.py` or `app/books/service.py` to send emails from the service layer. This creates circular imports (service imports email, email imports config, config may import from app).

**Why it happens:** Temptation to "keep the business logic together" in the service layer.

**How to avoid:** Email dispatch always happens in the router. The service layer returns data. Routers call services, then enqueue emails. This is the established pattern in this codebase (confirmed by the Phase 11 design: `set_stock_and_notify()` returns `notified_user_ids`, intentionally leaving email dispatch to the router).

**Warning signs:** Any import of `app.email.service` from `app/orders/service.py` or `app/books/service.py`.

### Pitfall 5: Test Email Capture Fails Due to get_email_service lru_cache

**What goes wrong:** Integration tests use `fm.record_messages()` against the `email_service` fixture's `FastMail` instance, but the app is actually using a different `FastMail` instance (the one created by the cached `get_email_service()` singleton). The outbox stays empty even though emails are being sent.

**Why it happens:** `get_email_service()` is decorated with `@lru_cache`. The first call creates the `EmailService`, and all subsequent calls return the same object. The test fixture's `EmailService` is a different instance.

**How to avoid:** Override `get_email_service` in `app.dependency_overrides` to return the test-controlled `EmailService` instance (same pattern as `get_db` override in `conftest.py`). Call `get_email_service.cache_clear()` in teardown.

**Warning signs:** Tests that use `email_service.fm.record_messages()` without also overriding `get_email_service` in the test app.

### Pitfall 6: total_price Not Available on Order ORM Object

**What goes wrong:** Template context tries to use `order.total_price` — but `total_price` is a `@computed_field` defined on `OrderResponse` (Pydantic schema), not on the `Order` SQLAlchemy model.

**Why it happens:** Confusing schema computed fields with model properties.

**How to avoid:** Build the order response first (`order_response = OrderResponse.model_validate(order)`), then use `order_response.total_price` in the email context. Or compute the total inline: `sum(item.unit_price * item.quantity for item in order.items)`.

---

## Code Examples

### Complete checkout router with email (annotated)

```python
# Source: analysis of app/orders/router.py + app/email/service.py + app/core/deps.py
from fastapi import APIRouter, BackgroundTasks, status
from app.cart.repository import CartRepository
from app.core.deps import ActiveUser, DbSession
from app.email.service import EmailSvc
from app.orders.repository import OrderRepository
from app.orders.schemas import CheckoutRequest, OrderResponse
from app.orders.service import MockPaymentService, OrderService
from app.users.repository import UserRepository

router = APIRouter(prefix="/orders", tags=["orders"])

def _make_service(db: DbSession) -> OrderService:
    return OrderService(
        order_repo=OrderRepository(db),
        cart_repo=CartRepository(db),
        payment_service=MockPaymentService(),
    )

@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    body: CheckoutRequest,
    db: DbSession,
    current_user: ActiveUser,
    background_tasks: BackgroundTasks,
    email_svc: EmailSvc,
) -> OrderResponse:
    user_id = int(current_user["sub"])
    service = _make_service(db)

    # All failure paths raise AppError here — no code below runs on failure
    order = await service.checkout(user_id, body)

    # Build response before email context so total_price is available
    order_response = OrderResponse.model_validate(order)

    # Fetch user email — indexed PK lookup, fast
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user:
        email_svc.enqueue(
            background_tasks,
            to=user.email,
            template_name="order_confirmation.html",
            subject="Your Bookstore order is confirmed",
            context={
                "order_id": order.id,
                "items": [
                    {
                        "title": item.book.title if item.book else "Unknown Book",
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in order.items
                ],
                "total_price": str(order_response.total_price),
            },
        )

    return order_response
```

### Batch user email fetch (new UserRepository method)

```python
# Source: pattern consistent with existing UserRepository methods (app/users/repository.py)
from sqlalchemy import select
from app.users.models import User

async def get_emails_by_ids(self, user_ids: list[int]) -> dict[int, str]:
    """Return {user_id: email} for the given list of user IDs.

    Uses a single IN query regardless of list length.
    Returns empty dict for empty input.
    """
    if not user_ids:
        return {}
    result = await self.session.execute(
        select(User.id, User.email).where(User.id.in_(user_ids))
    )
    return {row.id: row.email for row in result}
```

### update_stock router with email (annotated)

```python
# Source: analysis of app/books/router.py lines 120-145
@router.patch("/books/{book_id}/stock", response_model=BookResponse)
async def update_stock(
    book_id: int,
    body: StockUpdate,
    db: DbSession,
    admin: AdminUser,
    background_tasks: BackgroundTasks,
    email_svc: EmailSvc,
) -> BookResponse:
    from app.prebooks.repository import PreBookRepository  # existing local import pattern
    from app.users.repository import UserRepository

    service = _make_service(db)
    prebook_repo = PreBookRepository(db)
    book, notified_user_ids = await service.set_stock_and_notify(
        book_id, body.quantity, prebook_repo
    )

    # Only runs when stock transitions 0 → positive AND pre-bookers exist
    if notified_user_ids:
        user_repo = UserRepository(db)
        email_map = await user_repo.get_emails_by_ids(notified_user_ids)
        for uid, email in email_map.items():
            email_svc.enqueue(
                background_tasks,
                to=email,
                template_name="restock_alert.html",
                subject=f"'{book.title}' is back in stock",
                context={"book_title": book.title, "book_id": book.id},
            )

    return BookResponse.model_validate(book)
```

### Test fixture for email integration (dependency override pattern)

```python
# Source: pattern from conftest.py (get_db override) + test_email.py (record_messages usage)
import pytest_asyncio
from app.email.service import EmailService, get_email_service
from app.core.deps import get_db
from app.main import app

@pytest_asyncio.fixture
async def email_client(db_session, mail_config):
    """AsyncClient with controlled EmailService for outbox capture."""
    controlled_svc = EmailService(config=mail_config)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = lambda: controlled_svc

    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, controlled_svc.fm

    app.dependency_overrides.clear()
    get_email_service.cache_clear()
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_email_notifications.py -v` |
| Full suite command | `pytest tests/ -v` |
| asyncio_mode | `auto` — no `@pytest.mark.asyncio` decorator needed |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EMAL-02 | Order confirmation email sent after successful checkout | integration | `pytest tests/test_email_notifications.py::test_checkout_sends_confirmation_email -x` | No — Wave 0 |
| EMAL-02 | Email contains order_id, line items, total | integration | `pytest tests/test_email_notifications.py::test_confirmation_email_content -x` | No — Wave 0 |
| EMAL-02 | No email sent when checkout fails (cart empty, stock, payment) | integration | `pytest tests/test_email_notifications.py::test_no_email_on_checkout_failure -x` | No — Wave 0 |
| EMAL-02 | Email does not delay checkout HTTP response | integration | `pytest tests/test_email_notifications.py::test_checkout_email_non_blocking -x` | No — Wave 0 |
| EMAL-03 | Restock alert sent to each user with waiting pre-booking | integration | `pytest tests/test_email_notifications.py::test_restock_sends_alert_to_all_prebookers -x` | No — Wave 0 |
| EMAL-03 | No email when stock update is not a 0→positive transition | integration | `pytest tests/test_email_notifications.py::test_no_restock_email_on_positive_to_positive -x` | No — Wave 0 |
| EMAL-03 | No email when book has no waiting pre-bookers | integration | `pytest tests/test_email_notifications.py::test_no_restock_email_when_no_prebookers -x` | No — Wave 0 |
| EMAL-03 | Cancelled pre-bookings not notified | integration | `pytest tests/test_email_notifications.py::test_cancelled_prebookers_not_emailed -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_email_notifications.py -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- `tests/test_email_notifications.py` — all Phase 12 email notification tests (new file)
- No framework install needed — pytest, pytest-asyncio, httpx, fastapi-mail all installed

---

## Open Questions

1. **Should total_price formatting be Decimal or float in the template context?**
   - What we know: `total_price` on `OrderResponse` is a `Decimal` computed field. Jinja2 will render it as a Decimal string like `"29.98"` if coerced to `str()`.
   - What's unclear: Whether the template should format as `$29.98` using Jinja2 filters or leave formatting to Python before context assembly.
   - Recommendation: Format in Python before context: `"total_price": f"{order_response.total_price:.2f}"`. Simpler than Jinja2 filters.

2. **Should the restock email include a deep link to the book?**
   - What we know: `book.id` is available. There's no frontend URL configured in Settings.
   - What's unclear: Whether a link like `/books/{book_id}` is useful in a test/dev bookstore with no frontend.
   - Recommendation: Include `book_id` in context; omit the hyperlink (no FRONTEND_URL in Settings). The planner can decide if a placeholder URL is added.

3. **Should a failing user email lookup (user not found) silently skip or raise?**
   - What we know: `user_repo.get_by_id()` returns `None` if user not found. For checkout, if the authenticated user isn't in the DB, the `get_active_user` dependency already raises 403 before the route handler runs.
   - What's unclear: Whether there's any edge case where the user doesn't exist by the time we look them up post-checkout.
   - Recommendation: Use `if user:` guard (already shown in examples above) and silently skip. This is defensive — in practice, get_active_user guarantees the user exists.

4. **New test file or extend existing test files?**
   - What we know: Phase 9's email tests are in `tests/test_email.py`. Phase 7's order tests are in `tests/test_orders.py`. Phase 11's pre-booking tests are in `tests/test_prebooks.py`.
   - What's unclear: Whether Phase 12 tests belong alongside existing order/prebook tests or in a new `test_email_notifications.py`.
   - Recommendation: Create a new `tests/test_email_notifications.py`. Phase 12 tests span two endpoints (`/orders/checkout` and `/books/{id}/stock`) and need the shared `email_client` fixture. A dedicated file is cleaner than expanding two existing files and avoids fixture naming collisions.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery + Redis for async email | BackgroundTasks in FastAPI | N/A (never used here) | No queue server needed; simpler at v1.1 scale |
| Separate .txt email templates | `_strip_html()` auto-generation | Phase 9 (2026-02-26) | No duplicated template maintenance |
| Email in service layer | Email dispatch in router only | Phase 9 design decision | Avoids circular imports; clean separation |

**Deprecated/outdated:**
- None in this phase — all patterns are established from Phase 9.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase analysis — `app/email/service.py` (EmailService, enqueue, get_email_service)
- Direct codebase analysis — `app/orders/router.py` (checkout endpoint, existing structure)
- Direct codebase analysis — `app/books/router.py` (update_stock, placeholder comment at line 144)
- Direct codebase analysis — `app/books/service.py` (set_stock_and_notify returns notified_user_ids)
- Direct codebase analysis — `app/users/repository.py` (UserRepository, get_by_id)
- Direct codebase analysis — `app/orders/schemas.py` (OrderResponse.total_price as computed_field)
- Direct codebase analysis — `app/core/deps.py` (get_db lifecycle — commit after yield, confirms BackgroundTasks post-commit safety)
- Direct codebase analysis — `tests/conftest.py` (mail_config, email_service fixtures, get_db override pattern)
- Direct codebase analysis — `tests/test_email.py` (record_messages usage, integration_app pattern)
- `.planning/STATE.md` — locked decisions from Phases 09-01, 09-02, 11-01, 11-02; Phase 12 pre-work blocker

### Secondary (MEDIUM confidence)

- FastAPI docs on BackgroundTasks — execution after response, dependency injection pattern for `BackgroundTasks`
- fastapi-mail 1.6.2 docs — `record_messages()` sync context manager behavior (confirmed via STATE.md Phase 09-02 note)

### Tertiary (LOW confidence)

- None — all findings are HIGH confidence from direct codebase inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all libraries already integrated and tested in Phase 9
- Architecture: HIGH — patterns directly read from existing codebase; two insertion points explicitly marked with `# Phase 12` comments
- Pitfalls: HIGH — JWT-email gap is explicitly documented in STATE.md; lru_cache complication is documented in STATE.md Phase 09-01; all others derived from direct code reading
- Test patterns: HIGH — record_messages sync/async distinction documented in STATE.md Phase 09-02; dependency override pattern read from conftest.py

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable — no external dependencies added; internal codebase only)
