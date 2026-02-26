# Phase 10: Admin User Management - Research

**Researched:** 2026-02-26
**Domain:** FastAPI admin endpoints, SQLAlchemy async queries with filters/pagination, JWT is_active enforcement
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**User list & filtering**
- Offset-based pagination (?page=1&per_page=20) — consistent with existing catalog/order endpoints
- Default sort: newest first (created_at DESC)
- Admin user response includes: id, email, full_name, role, is_active, created_at
- Filters are combinable: ?role=user&is_active=false both optional, omit = all values
- Response includes full page metadata: total_count, page, per_page, total_pages

**Deactivation behavior**
- Immediate lockout: check is_active on every protected request, reject deactivated users instantly (don't wait for token expiry)
- Deactivation revokes all refresh tokens AND blocks current access tokens via is_active check
- Generic 403 error for deactivated users: "Account deactivated. Contact support." — same for login and protected endpoints
- Deactivation only affects authentication — orders, cart, wishlist data remain untouched
- Deactivate is idempotent: deactivating an already-deactivated user returns 200 with user object

**Reactivation behavior**
- Fresh login required after reactivation (is_active flipped but no tokens issued)
- Reactivate is idempotent: reactivating an already-active user returns 200 with user object
- No special restriction on reactivating admin accounts

**Admin self-protection**
- Blanket rule: no admin can deactivate any admin account (self or others) — matches ADMN-05
- 403 Forbidden with message "Cannot deactivate admin accounts" — same response regardless of target
- No superadmin concept

**API design**
- Dedicated admin namespace: /admin/users
- GET /admin/users — paginated list with filters
- PATCH /admin/users/{id}/deactivate — deactivate user
- PATCH /admin/users/{id}/reactivate — reactivate user
- All endpoints return updated AdminUserResponse (full user object with is_active)

### Claude's Discretion
- Exact admin router/module structure
- How to implement is_active check in the auth dependency (middleware vs dependency injection)
- Test organization and fixture design
- Error handling for non-existent user IDs

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMN-01 | Admin can view a paginated list of all users | BookRepository.search() pattern for paginated SQLAlchemy queries with count subquery; `func.count()` + `.limit()/.offset()` |
| ADMN-02 | Admin can filter user list by role and active status | SQLAlchemy `.where()` with optional filter clauses; same combinable filter pattern used in BookRepository |
| ADMN-03 | Admin can deactivate a user account (sets is_active=false, revokes all refresh tokens) | New `revoke_all_for_user()` on RefreshTokenRepository; existing `update(User).where(...).values(is_active=False)` pattern |
| ADMN-04 | Admin can reactivate a previously deactivated user account | Flip `is_active=True`; no token issuance — user must call login after |
| ADMN-05 | Admin cannot deactivate themselves or other admin users | Check `user.role == UserRole.ADMIN` before deactivation; 403 with "Cannot deactivate admin accounts" |
</phase_requirements>

---

## Summary

Phase 10 adds three admin-only endpoints under `/admin/users` and enforces immediate lockout for deactivated users. The codebase already has all the structural primitives: `AdminUser` dependency in `core/deps.py`, `is_active` column on the User model, opaque refresh tokens with bulk-revocation support at the family level. What's missing is: a `revoke_all_for_user()` method on RefreshTokenRepository, a `require_active_user` check in the auth dependency chain, and the admin router itself.

The most architecturally significant work is implementing "immediate lockout." The current `get_current_user()` dependency in `core/deps.py` decodes the JWT without touching the database — so a deactivated user with a valid 15-minute access token can still call protected endpoints. The decision is to add a DB-backed `is_active` check into the auth dependency chain. The cleanest approach (matching existing patterns) is to add an `require_active_user` dependency that fetches the user by ID from the token's `sub` claim and raises 403 if `is_active` is false. This is injected per-route using a new `ActiveUser` type alias, replacing `CurrentUser` on all protected routes — or layered as a dependency on top of `get_current_user`.

One gap from the CONTEXT.md: `AdminUserResponse` is specified to include `full_name`, but the `User` model has no `full_name` column (only `id, email, hashed_password, role, is_active, created_at`). The response schema must omit `full_name` or treat it as `None | str` derived from email. The planner should decide: drop `full_name` from the response entirely (simplest) or add `full_name: str | None` as a nullable field that is always null until a profile phase adds it.

**Primary recommendation:** Create `app/admin/` module with `router.py`, `schemas.py`, `service.py`. Extend `UserRepository` with filter/paginate query, extend `RefreshTokenRepository` with `revoke_all_for_user()`. Add `is_active` DB-check dependency to `core/deps.py`. Register admin router in `main.py` alongside existing `orders_admin_router`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | ^0.133.0 | Router, Query params, Depends | Already in project |
| SQLAlchemy 2.0 | ^2.0.47 | Async ORM queries with filters/pagination | Already in project |
| Pydantic v2 | ^2.12.5 | Response schemas, query param validation | Already in project |
| PyJWT | ^2.11.0 | Decode access token to get user ID for is_active check | Already in project |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | ^1.3.0 | Async integration test fixtures | All test cases |
| httpx | ^0.28.1 | AsyncClient for HTTP-level integration tests | All test cases |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DB lookup in auth dependency | Middleware | Middleware runs for every request (including 404s); dependency injection is more targeted and testable |
| Separate admin module `app/admin/` | Add to `app/users/` | Both work; separate module is cleaner given the admin-specific response schema |
| `update()` statement for is_active | setattr + flush | Both are correct; bulk update statement is more efficient and consistent with `RevocationRepository.revoke()` pattern |

**Installation:** No new packages required. All dependencies already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── admin/
│   ├── __init__.py
│   ├── router.py        # GET /admin/users, PATCH /admin/users/{id}/deactivate|reactivate
│   ├── schemas.py       # AdminUserResponse, UserListResponse (paginated envelope)
│   └── service.py       # AdminUserService — list, deactivate, reactivate business logic
app/
├── core/
│   └── deps.py          # Add require_active_user / ActiveUser dependency
app/
├── users/
│   └── repository.py    # Add: list_paginated(), revoke_all_for_user() to RefreshTokenRepository
app/
└── main.py              # Register admin_users_router
tests/
└── test_admin_users.py  # New test file
```

### Pattern 1: Admin Router (matches existing orders pattern)

**What:** Two routers in one file; admin router has separate prefix and tag.
**When to use:** All admin endpoints for a domain (users in this case).

The existing orders pattern in `app/orders/router.py`:
```python
router = APIRouter(prefix="/orders", tags=["orders"])
admin_router = APIRouter(prefix="/admin/orders", tags=["admin"])
```

For Phase 10, the admin router is the ONLY router in `app/admin/router.py` since there is no user-facing `/users` endpoint:
```python
# app/admin/router.py
from fastapi import APIRouter, Query
from app.core.deps import AdminUser, DbSession
from app.admin.schemas import AdminUserResponse, UserListResponse

router = APIRouter(prefix="/admin/users", tags=["admin"])

@router.get("", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
) -> UserListResponse:
    ...

@router.patch("/{user_id}/deactivate", response_model=AdminUserResponse)
async def deactivate_user(user_id: int, db: DbSession, _: AdminUser) -> AdminUserResponse:
    ...

@router.patch("/{user_id}/reactivate", response_model=AdminUserResponse)
async def reactivate_user(user_id: int, db: DbSession, _: AdminUser) -> AdminUserResponse:
    ...
```

In `main.py`, add alongside `orders_admin_router`:
```python
from app.admin.router import router as admin_users_router
application.include_router(admin_users_router)
```

### Pattern 2: Paginated Repository Query with Optional Filters (HIGH confidence)

**What:** SQLAlchemy 2.0 async paginated query with combinable optional WHERE clauses and total count subquery.
**When to use:** ADMN-01 and ADMN-02.

The existing `BookRepository.search()` establishes this project's pagination idiom:
```python
# Pattern from app/books/repository.py — verified from codebase
stmt = select(User).order_by(User.created_at.desc())

if role is not None:
    stmt = stmt.where(User.role == UserRole(role))
if is_active is not None:
    stmt = stmt.where(User.is_active == is_active)

count_stmt = select(func.count()).select_from(stmt.subquery())
total = await self.session.scalar(count_stmt)

offset = (page - 1) * per_page
stmt = stmt.limit(per_page).offset(offset)

result = await self.session.execute(stmt)
users = list(result.scalars().all())
return users, total or 0
```

The count subquery reuses the same filter conditions — no duplicate filter logic.

### Pattern 3: is_active Lockout in Auth Dependency (Claude's Discretion)

**What:** Add DB lookup after JWT decode to reject deactivated users immediately.
**When to use:** To enforce CONTEXT.md decision "check is_active on every protected request."

The current `get_current_user()` in `core/deps.py` is JWT-only (no DB). The cleanest extension:

```python
# Addition to app/core/deps.py
from app.users.repository import UserRepository

async def get_active_user(
    db: DbSession,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Verify user is still active. DB lookup on every request.

    Called for routes that need immediate deactivation enforcement.
    Admin routes use AdminUser which chains through this.
    """
    user_id = int(current_user["sub"])
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AppError(
            status_code=403,
            detail="Account deactivated. Contact support.",
            code="AUTH_ACCOUNT_DEACTIVATED",
        )
    return current_user

ActiveUser = Annotated[dict, Depends(get_active_user)]
```

**IMPORTANT TRADE-OFF:** Adding `is_active` DB check adds one DB round-trip per protected request. This is acceptable for a bookstore at v1.1 scale and is the decision in CONTEXT.md. The alternative (checking only at refresh) is explicitly rejected.

**Scope decision (Claude's Discretion):** Whether to apply `ActiveUser` to ALL existing protected routes or only new admin routes. Recommendation: apply broadly to all routes that use `CurrentUser` or `AdminUser` (cart, orders, wishlist, admin endpoints) so deactivated users are locked out from all actions. The login endpoint requires a separate check in `AuthService.login()`.

### Pattern 4: Bulk Refresh Token Revocation by User ID

**What:** New method on RefreshTokenRepository to revoke all non-revoked tokens for a user.
**When to use:** ADMN-03 — deactivation must revoke all refresh tokens simultaneously.

```python
# Addition to app/users/repository.py — RefreshTokenRepository
async def revoke_all_for_user(self, user_id: int) -> None:
    """Revoke all non-revoked refresh tokens for a user.

    Called during admin deactivation to prevent any active sessions
    from obtaining new access tokens via /auth/refresh.
    """
    await self.session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
```

This follows the exact same pattern as the existing `revoke_family()` method.

### Pattern 5: Deactivation Business Logic

**What:** Service method that atomically sets `is_active=False` and revokes all refresh tokens.
**When to use:** ADMN-03.

```python
# app/admin/service.py
class AdminUserService:
    def __init__(self, user_repo: UserRepository, rt_repo: RefreshTokenRepository) -> None:
        self.user_repo = user_repo
        self.rt_repo = rt_repo

    async def deactivate_user(self, target_user_id: int) -> User:
        """Deactivate user: set is_active=False and revoke all refresh tokens.

        Returns 403 if target is an admin (ADMN-05).
        Idempotent: already-deactivated user returns 200.
        """
        user = await self._get_user_or_404(target_user_id)
        if user.role == UserRole.ADMIN:
            raise AppError(
                status_code=403,
                detail="Cannot deactivate admin accounts",
                code="ADMN_CANNOT_DEACTIVATE_ADMIN",
            )
        # Idempotent — no error if already deactivated
        if user.is_active:
            user.is_active = False
            await self.session.flush()
            await self.rt_repo.revoke_all_for_user(user.id)
        return user

    async def reactivate_user(self, target_user_id: int) -> User:
        """Reactivate user: set is_active=True. No tokens issued.

        Idempotent: already-active user returns 200.
        """
        user = await self._get_user_or_404(target_user_id)
        if not user.is_active:
            user.is_active = True
            await self.session.flush()
        return user
```

Note: `flush()` is used (not `commit()`) because commit is handled by the `get_db()` dependency on request completion, consistent with all other service methods in the project.

### Pattern 6: AdminUserResponse Schema

**What:** Pydantic response schema for admin user view.
**When to use:** All three admin user endpoints return this schema.

```python
# app/admin/schemas.py
from datetime import datetime
from pydantic import BaseModel

class AdminUserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class UserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total_count: int
    page: int
    per_page: int
    total_pages: int
```

Note: `full_name` is absent from the User model. The CONTEXT.md mentions it but the column does not exist. Do NOT include `full_name` in the response unless a migration is added. Recommendation: omit it from the schema entirely (it was likely aspirational in the discussion).

### Pattern 7: Login is_active Check (Gap to Fix)

**What:** The `login()` method in AuthService does not check `is_active`.
**When to use:** Required — deactivated users must not be able to get new tokens via /auth/login.

Currently `AuthService.login()` only checks if the password matches. If a user is deactivated, they can still call POST /auth/login and get a new token pair. This is the one existing gap.

The fix:
```python
# app/users/service.py — AuthService.login() addition
async def login(self, email: str, password: str) -> tuple[str, str]:
    user = await self.user_repo.get_by_email(email)
    ...  # existing null/password checks

    if not user.is_active:
        raise AppError(
            status_code=403,
            detail="Account deactivated. Contact support.",
            code="AUTH_ACCOUNT_DEACTIVATED",
        )

    access_token = create_access_token(user.id, user.role.value)
    ...
```

This check must come AFTER the password verification (to prevent account status enumeration — a deactivated user with wrong password should still get AUTH_INVALID_CREDENTIALS, not AUTH_ACCOUNT_DEACTIVATED).

### Anti-Patterns to Avoid

- **Committing inside service methods:** The project uses `get_db()` to commit on request completion. Never call `await self.session.commit()` in service or repository code — only `flush()`.
- **Revoking tokens by token string instead of user ID:** The existing `revoke()` and `revoke_family()` methods operate on single tokens or families. Deactivation needs a new `revoke_all_for_user()` that operates on `user_id` — don't loop over individual tokens.
- **Skipping idempotency:** Both deactivate and reactivate must be idempotent (return 200, not 409, if already in the requested state).
- **Importing User model in admin module without registering in base:** The `User` model is already imported in `app/db/base.py`. The admin module doesn't need to create new models, so no change to `base.py` is needed.
- **Role filter as UserRole enum vs string:** The `?role=` query param arrives as a string. Validate before use: `UserRole(role)` raises `ValueError` if invalid. Catch and return 422 (or let Pydantic handle it if using an `Enum` query param type).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination offset/count | Custom SQL string | SQLAlchemy `func.count().select_from(stmt.subquery())` + `.limit()/.offset()` | Already proven in BookRepository; handles edge cases correctly |
| Admin role enforcement | Manual JWT inspection in route | `AdminUser = Annotated[dict, Depends(require_admin)]` already in `core/deps.py` | Pre-built; tested in test_auth.py |
| Bulk token revocation | Loop over tokens and revoke one-by-one | Single `update()` statement with `WHERE user_id = X AND revoked_at IS NULL` | Single round-trip; atomic |
| is_active check | Inline DB query in every route | New `ActiveUser` dependency in `core/deps.py` | Centralizes the check; easy to test in isolation |

**Key insight:** The project's repository + service + router layering is strictly followed. Don't put query logic in routers or business logic in repositories.

---

## Common Pitfalls

### Pitfall 1: Login Endpoint Not Checking is_active
**What goes wrong:** A deactivated user can call POST /auth/login with correct credentials and receive a valid access token, bypassing deactivation.
**Why it happens:** The `AuthService.login()` method currently only checks if the user exists and if the password is correct — it does not check `is_active`. The `is_active` check only exists in `refresh()` and `oauth_login()`.
**How to avoid:** Add `is_active` check to `AuthService.login()` AFTER password verification (see Pattern 7 above).
**Warning signs:** Test "deactivated user cannot log in" would fail without this fix.

### Pitfall 2: Access Token Still Valid After Deactivation
**What goes wrong:** Revoking refresh tokens only prevents NEW token pairs. A currently-held access token (valid for up to 15 minutes) still works on protected endpoints.
**Why it happens:** `get_current_user()` in `core/deps.py` is JWT-only — no DB lookup. The decision in CONTEXT.md is to add a DB-backed `is_active` check to the dependency chain.
**How to avoid:** Implement `ActiveUser` dependency that fetches user from DB and checks `is_active` (Pattern 3).
**Warning signs:** Test "access token rejected immediately after deactivation" fails if dependency not added.

### Pitfall 3: Applying ActiveUser Dependency to All Routes (Scope Creep Risk)
**What goes wrong:** Updating ALL routes from `CurrentUser` to `ActiveUser` touches cart, orders, wishlist, books routers — risk of regressions in other tests.
**Why it happens:** The `is_active` check requires a DB lookup; upgrading all routes is broad.
**How to avoid:** Plan which routes get `ActiveUser` explicitly; run full test suite after each router change. The admin routes themselves always use `AdminUser` (which should also chain through `ActiveUser`).
**Warning signs:** Existing tests for cart/orders/wishlist fail unexpectedly after dependency change.

### Pitfall 4: UserRole Enum Validation for Query Params
**What goes wrong:** Query param `?role=invalid` causes an unhandled ValueError or 500 error.
**Why it happens:** `UserRole("invalid")` raises `ValueError`. If not handled, this propagates as a 500.
**How to avoid:** Use `UserRole | None` as the Query param type (FastAPI/Pydantic handles enum validation automatically and returns 422 for invalid values), or validate explicitly.
**Warning signs:** Test with `?role=garbage` returns 500 instead of 422.

### Pitfall 5: Idempotency — Return Updated User Object
**What goes wrong:** Deactivating an already-deactivated user raises 409 instead of 200.
**Why it happens:** Treating deactivation as a state transition rather than a "set to desired state" operation.
**How to avoid:** Check current state; if already in desired state, skip the update and return the user object as-is. Both deactivate and reactivate must return 200 with the user object regardless.
**Warning signs:** Test "deactivate already-deactivated user returns 200" fails.

### Pitfall 6: Missing full_name Field
**What goes wrong:** Planning assumes `full_name` is in the AdminUserResponse because CONTEXT.md mentions it, but the User model has no such column — `model_validate()` will fail.
**Why it happens:** CONTEXT.md was written with the desired API in mind; the DB schema doesn't have the field yet.
**How to avoid:** Omit `full_name` from the schema entirely in Phase 10. If needed, add a nullable `full_name` column via Alembic migration first.
**Warning signs:** `AdminUserResponse.model_validate(user)` raises `AttributeError: 'User' object has no attribute 'full_name'`.

---

## Code Examples

Verified patterns from project codebase:

### Existing Pagination Pattern (from app/books/repository.py)
```python
# Count total before pagination
count_stmt = select(func.count()).select_from(stmt.subquery())
total = await self.session.scalar(count_stmt)

# Apply pagination
offset = (page - 1) * size
stmt = stmt.limit(size).offset(offset)

result = await self.session.execute(stmt)
books = list(result.scalars().all())
return books, total or 0
```

### Existing Bulk Revoke Pattern (from app/users/repository.py — revoke_family)
```python
async def revoke_family(self, token_family: uuid.UUID) -> None:
    """Revoke all non-revoked tokens in a family (theft detection)."""
    await self.session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_family == token_family,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
```

### Existing Admin Dependency (from app/core/deps.py)
```python
def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Require admin role. Raises AppError(403) if role is not admin."""
    if current_user.get("role") != "admin":
        raise AppError(
            status_code=403,
            detail="Admin access required",
            code="AUTH_FORBIDDEN",
        )
    return current_user

AdminUser = Annotated[dict, Depends(require_admin)]
```

### Existing is_active Check (from app/users/service.py — refresh)
```python
user = await self.user_repo.get_by_id(rt.user_id)
if user is None or not user.is_active:
    raise AppError(
        status_code=401,
        detail="User not found or inactive",
        code="AUTH_USER_INACTIVE",
    )
```

### Existing Router Registration Pattern (from app/main.py)
```python
from app.orders.router import admin_router as orders_admin_router
...
application.include_router(orders_admin_router)
```

### Existing Test Admin Fixture (from tests/test_auth.py and test_catalog.py)
```python
@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="catalog_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "catalog_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Check is_active only at refresh | Check is_active on every protected request | Phase 10 decision | Requires DB lookup per request — acceptable trade-off for immediate lockout |
| No admin user management | /admin/users CRUD endpoints | Phase 10 | Unlocks user lifecycle management |

**Deprecated/outdated:**
- None for this phase.

---

## Open Questions

1. **Should `full_name` be added to the User model?**
   - What we know: CONTEXT.md lists `full_name` in AdminUserResponse but the DB column does not exist.
   - What's unclear: Was `full_name` intentional (requires migration) or a CONTEXT.md error (drop from schema)?
   - Recommendation: Omit `full_name` from Phase 10. If needed, plan a separate migration. The CONTEXT.md list likely carried over from an aspirational spec. The response schema is simpler without it.

2. **Should `ActiveUser` replace `CurrentUser` on ALL existing protected routes?**
   - What we know: The is_active check adds one DB round-trip per request. Cart, orders, wishlist all use `CurrentUser` today.
   - What's unclear: Is it acceptable for a deactivated user to still browse/add-to-cart while their access token lives?
   - Recommendation: Update all routes that perform write operations (cart, orders, wishlist) to use `ActiveUser`. Read-only catalog endpoints (public, no auth required) are unaffected. This is the most consistent interpretation of "immediate lockout."

3. **Is_active check code: 401 vs 403?**
   - The CONTEXT.md says "Generic 403 error for deactivated users." But existing `refresh()` returns 401 for inactive users. There's an inconsistency.
   - Recommendation: Use 403 for the new `ActiveUser` dependency (enforces CONTEXT.md). The existing `refresh()` 401 code can be left as-is (it's a different flow — the refresh endpoint already handles user-not-found/inactive separately).

---

## Validation Architecture

> `workflow.nyquist_validation` not present in `.planning/config.json` — skipping this section.

---

## Sources

### Primary (HIGH confidence)
- Project codebase (`app/users/repository.py`, `app/users/service.py`, `app/users/models.py`) — verified all existing patterns, method signatures, and column names directly
- Project codebase (`app/core/deps.py`) — verified AdminUser, CurrentUser, get_current_user patterns
- Project codebase (`app/books/repository.py`) — verified pagination count-subquery pattern
- Project codebase (`app/orders/router.py`) — verified admin_router split pattern
- Project codebase (`app/main.py`) — verified router registration pattern
- Project codebase (`tests/conftest.py`, `tests/test_auth.py`, `tests/test_catalog.py`) — verified test fixture patterns

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 async docs pattern for `update()` with `where()` — consistent with `revoke_family()` in codebase
- FastAPI Depends chaining — consistent with existing `require_admin -> get_current_user` chain

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all patterns verified in existing codebase
- Architecture: HIGH — patterns directly observed in codebase; admin router, pagination, bulk-revoke all have direct analogues
- Pitfalls: HIGH — login is_active gap verified by reading `AuthService.login()` directly; full_name gap verified by reading User model

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable — no external dependencies changing)
