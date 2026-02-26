# Phase 3: OAuth - Research

**Researched:** 2026-02-25
**Domain:** OAuth 2.0 social login (Google + GitHub) integrated into existing JWT auth layer
**Confidence:** HIGH

## Summary

Phase 3 adds Google and GitHub OAuth login to the existing email/password auth system. The goal is straightforward: users click "Login with Google/GitHub," complete the OAuth flow, and receive the same JWT access + refresh token pair they would get from email/password login. If the OAuth email matches an existing account, the login links to that account rather than creating a duplicate.

The recommended approach uses **Authlib** (v1.6.8) as the OAuth client library. Authlib provides a mature, well-maintained Starlette/FastAPI integration with async support via HTTPX backends. It handles the OAuth 2.0 authorization code flow, CSRF state management (via Starlette SessionMiddleware), and token exchange. Google supports OpenID Connect (userinfo comes directly from the token response), while GitHub requires a separate API call to `api.github.com/user` and `api.github.com/user/emails` to retrieve the user's email.

The key architectural changes are: (1) a new `oauth_accounts` table to track provider+provider_id linkages, (2) making `hashed_password` nullable on the User model so OAuth-only users can exist without a password, (3) adding SessionMiddleware for OAuth state management, and (4) new OAuth config settings (client IDs, secrets, callback URLs). The existing `create_access_token` and `generate_refresh_token` functions are reused without modification -- OAuth is just another way to authenticate, not a different token system.

**Primary recommendation:** Use Authlib v1.6.8 with Starlette integration for OAuth client flows. Create a separate `oauth_accounts` table. Make `hashed_password` nullable. Reuse existing JWT token generation.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-06 | User can log in with Google or GitHub OAuth | Authlib handles OAuth authorization code flow for both providers. Google uses OIDC (userinfo in token). GitHub requires separate API calls for user profile + email. Account linking by email enables seamless integration with existing users. Same JWT token pair returned as email/password login. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| authlib | ^1.6.8 | OAuth 2.0 client for Google + GitHub | Industry-standard Python OAuth library. Async Starlette/FastAPI integration. Handles state, PKCE, token exchange. Active maintenance (Feb 2026 release). |
| itsdangerous | ^2.2.0 | Signed session cookies for OAuth state | Required by Starlette SessionMiddleware. Stores OAuth state parameter between redirect and callback. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | (already installed) | HTTP client for GitHub API calls | Authlib's Starlette integration uses HTTPX internally. Already a dev dependency. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Authlib | httpx-oauth | httpx-oauth is async-native but less mature, fewer docs. Authlib is the ecosystem standard with better Google OIDC support. |
| Authlib | fastapi-users | Full user management framework -- massive overkill when we already have our own auth system. Would require rewriting Phase 2. |
| Authlib | fastapi-sso | Simpler API but less control over the flow, less mature, fewer providers. |
| Separate oauth_accounts table | Columns on User model | Columns break if user links multiple providers. Separate table is standard, queryable, extensible. |

**Installation:**
```bash
poetry add authlib itsdangerous
```

## Architecture Patterns

### Recommended Project Structure
```
app/
  core/
    config.py          # Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
    oauth.py           # NEW: OAuth client registry (authlib OAuth instance, provider registrations)
    security.py        # No changes needed — reuse create_access_token, generate_refresh_token
    deps.py            # No changes needed
  users/
    models.py          # Add OAuthAccount model; make User.hashed_password nullable
    repository.py      # Add OAuthAccountRepository; update UserRepository.create for OAuth users
    service.py         # Add oauth_login() method to AuthService
    schemas.py         # Add OAuthCallbackResponse if needed (same as TokenResponse)
    router.py          # Add GET /auth/google, /auth/google/callback, /auth/github, /auth/github/callback
  db/
    base.py            # Import OAuthAccount for Alembic discovery
```

### Pattern 1: OAuth Client Registry
**What:** Centralized OAuth provider configuration in `app/core/oauth.py`
**When to use:** Always -- single place to register all OAuth providers

```python
# Source: Authlib docs https://docs.authlib.org/en/latest/client/fastapi.html
from authlib.integrations.starlette_client import OAuth
from app.core.config import get_settings

oauth = OAuth()

def configure_oauth() -> None:
    """Register OAuth providers. Call during app startup."""
    settings = get_settings()

    # Google (OpenID Connect -- userinfo comes from token)
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # GitHub (plain OAuth2 -- no OIDC, must fetch user info separately)
    oauth.register(
        name="github",
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )
```

### Pattern 2: OAuth Account Model (Separate Table)
**What:** Dedicated table linking OAuth provider identities to users
**When to use:** Always -- supports multiple providers per user, clean queries

```python
# OAuthAccount model
class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    oauth_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "google" or "github"
    oauth_account_id: Mapped[str] = mapped_column(String(255), nullable=False)  # provider's user ID
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Unique constraint: one link per provider per user
    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_account_id", name="uq_oauth_provider_account"),
    )

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")
```

### Pattern 3: Account Linking by Email
**What:** When OAuth login provides an email matching an existing user, link to that account
**When to use:** Always -- per the phase success criteria

```python
async def oauth_login(self, provider: str, provider_user_id: str, email: str) -> tuple[str, str]:
    """Authenticate via OAuth. Links to existing account if email matches."""
    # 1. Check if this OAuth identity already exists
    oauth_account = await self.oauth_repo.get_by_provider_and_id(provider, provider_user_id)
    if oauth_account:
        user = await self.user_repo.get_by_id(oauth_account.user_id)
    else:
        # 2. Check if email matches existing user
        user = await self.user_repo.get_by_email(email)
        if not user:
            # 3. Create new user (no password -- OAuth-only)
            user = await self.user_repo.create_oauth_user(email=email)
        # 4. Link OAuth identity to user
        await self.oauth_repo.create(
            user_id=user.id,
            oauth_provider=provider,
            oauth_account_id=provider_user_id,
        )

    # 5. Issue same JWT token pair as email/password login
    access_token = create_access_token(user.id, user.role.value)
    raw_rt = generate_refresh_token()
    await self.rt_repo.create(raw_rt, user.id)
    return access_token, raw_rt
```

### Pattern 4: Provider-Specific User Info Extraction
**What:** Google and GitHub return user info differently
**When to use:** In the callback handlers

```python
# Google (OIDC -- userinfo embedded in token response)
async def google_callback(request: Request, db: DbSession):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]
    email = userinfo["email"]
    provider_user_id = userinfo["sub"]  # Google's unique user ID
    # email_verified = userinfo["email_verified"]  # Can check if needed

# GitHub (plain OAuth2 -- must fetch user info via API)
async def github_callback(request: Request, db: DbSession):
    token = await oauth.github.authorize_access_token(request)
    # Fetch user profile
    resp = await oauth.github.get("user", token=token)
    resp.raise_for_status()
    profile = resp.json()
    provider_user_id = str(profile["id"])  # GitHub's numeric user ID

    # Email may be null if user has private email -- fetch from /user/emails
    email = profile.get("email")
    if not email:
        email_resp = await oauth.github.get("user/emails", token=token)
        email_resp.raise_for_status()
        emails = email_resp.json()
        # Find primary verified email
        primary = next((e for e in emails if e["primary"] and e["verified"]), None)
        if primary:
            email = primary["email"]
```

### Pattern 5: SessionMiddleware for OAuth State
**What:** Authlib stores the OAuth state parameter in the session to prevent CSRF
**When to use:** Must be added to the FastAPI app

```python
# In app/main.py
from starlette.middleware.sessions import SessionMiddleware

def create_app() -> FastAPI:
    application = FastAPI(...)
    # SessionMiddleware required for Authlib OAuth state management
    application.add_middleware(
        SessionMiddleware,
        secret_key=get_settings().SECRET_KEY,
        max_age=600,  # 10 minutes -- enough for OAuth flow
    )
    # ... rest of setup
```

### Anti-Patterns to Avoid
- **Storing OAuth tokens in our DB:** We don't need the provider's access/refresh tokens. We only need the provider's user ID for linking. Our app issues its own JWTs.
- **Building OAuth flow manually with httpx:** Authlib handles state, CSRF, token exchange, and OIDC discovery. Hand-rolling this is error-prone.
- **Adding provider columns to User table:** `oauth_provider` and `oauth_id` columns on User only support one provider per user. Use a separate table.
- **Requiring password for OAuth users:** OAuth-only users should not need a password. Making `hashed_password` nullable is the correct approach.
- **Skipping email verification check for Google:** Google's OIDC returns `email_verified` -- should check it before linking.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth state/CSRF | Custom state parameter generation + validation | Authlib `authorize_redirect` + `authorize_access_token` | Authlib handles state generation, storage in session, and validation on callback. Subtle CSRF bugs if done manually. |
| Google OIDC discovery | Hardcoded Google URLs | Authlib `server_metadata_url` with Google's `.well-known/openid-configuration` | Google's endpoints can change. OIDC discovery is the standard approach. |
| GitHub email retrieval | Single API call assuming email in profile | Two-step: `/user` then `/user/emails` if email is null | GitHub users with private emails return `null` in the profile endpoint. Must check `/user/emails` with `user:email` scope. |
| OAuth token exchange | Manual HTTP POST to token endpoint | Authlib `authorize_access_token` | Handles content-type negotiation, error responses, and token parsing. |

**Key insight:** Authlib abstracts the entire OAuth flow (redirect -> callback -> token exchange -> user info). The only custom code needed is account linking logic and JWT issuance.

## Common Pitfalls

### Pitfall 1: GitHub Email Can Be Null
**What goes wrong:** GitHub user's profile `email` field is `null` when they have private email settings.
**Why it happens:** GitHub respects user privacy settings. The `/user` endpoint only returns email if the user has set it as public.
**How to avoid:** Always check if `email` is null after fetching `/user`. If null, make a second call to `/user/emails` endpoint and find the primary verified email.
**Warning signs:** `IntegrityError` on User creation because email is None.

### Pitfall 2: hashed_password NOT NULL Constraint
**What goes wrong:** Creating an OAuth-only user fails because `hashed_password` column is `NOT NULL`.
**Why it happens:** Phase 2 designed the User model assuming all users have passwords.
**How to avoid:** Add an Alembic migration to make `hashed_password` nullable. OAuth-only users have `hashed_password = None`. Login with password path must check `if user.hashed_password is None: reject`.
**Warning signs:** Database errors on OAuth user creation.

### Pitfall 3: CSRF State Mismatch
**What goes wrong:** Callback returns error: "CSRF Warning! State not equal in request and response"
**Why it happens:** SessionMiddleware not added, or session cookie expired/lost between redirect and callback.
**How to avoid:** Ensure SessionMiddleware is registered in `create_app()` with a reasonable `max_age` (600 seconds). Use the same `SECRET_KEY` for signing.
**Warning signs:** OAuth login works in development but fails in production (different domains, cookie settings).

### Pitfall 4: OAuth Callback URL Mismatch
**What goes wrong:** Provider rejects the callback with "redirect_uri_mismatch" error.
**Why it happens:** The callback URL registered in Google/GitHub developer console doesn't exactly match the URL generated by `request.url_for('callback_name')`.
**How to avoid:** Document the exact callback URLs in config: `http://localhost:8000/auth/google/callback` and `http://localhost:8000/auth/github/callback`. Use environment variables for production URLs.
**Warning signs:** Works locally but fails in deployment.

### Pitfall 5: Duplicate OAuth Account Linking
**What goes wrong:** Same OAuth identity creates multiple OAuthAccount records.
**Why it happens:** Race condition or missing unique constraint.
**How to avoid:** `UNIQUE(oauth_provider, oauth_account_id)` constraint on the `oauth_accounts` table. Check for existing link before creating.
**Warning signs:** Multiple rows for same Google/GitHub user in oauth_accounts.

### Pitfall 6: Password Login After OAuth Registration
**What goes wrong:** User who registered via OAuth tries to log in with email/password and gets a confusing error.
**Why it happens:** `hashed_password` is None for OAuth-only users, so `verify_password(password, None)` crashes or returns unexpected results.
**How to avoid:** In `AuthService.login()`, after finding the user by email, check `if user.hashed_password is None` and return a clear error like "This account uses social login. Please log in with Google/GitHub."
**Warning signs:** 500 errors or cryptic messages when OAuth users try password login.

## Code Examples

### Complete OAuth Callback Handler (Google)
```python
# Source: Authlib docs + project conventions
from authlib.integrations.starlette_client import OAuthError
from starlette.requests import Request

@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google's consent screen."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request, db: DbSession) -> TokenResponse:
    """Handle Google's callback, issue JWT tokens."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        raise AppError(
            status_code=401,
            detail=f"OAuth authentication failed: {e.description}",
            code="AUTH_OAUTH_FAILED",
        )

    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        raise AppError(
            status_code=401,
            detail="Could not retrieve email from Google",
            code="AUTH_OAUTH_NO_EMAIL",
        )

    service = _make_service(db)
    access_token, refresh_token = await service.oauth_login(
        provider="google",
        provider_user_id=userinfo["sub"],
        email=userinfo["email"],
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
```

### Config Settings for OAuth
```python
# In app/core/config.py — add to Settings class
class Settings(BaseSettings):
    # ... existing settings ...

    # OAuth - Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # OAuth - GitHub
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
```

### Alembic Migration for hashed_password Nullable + oauth_accounts
```python
# Key migration operations
def upgrade():
    # Make hashed_password nullable for OAuth-only users
    op.alter_column("users", "hashed_password", nullable=True)

    # Create oauth_accounts table
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("oauth_provider", sa.String(50), nullable=False),
        sa.Column("oauth_account_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("oauth_provider", "oauth_account_id", name="uq_oauth_provider_account"),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flask-OAuthlib | Authlib | 2019+ | Authlib is the successor; Flask-OAuthlib is in maintenance mode |
| Manual OAuth state in URL params | SessionMiddleware + Authlib auto-state | Authlib 0.14+ | Authlib handles CSRF state automatically via session |
| Storing provider access tokens | Storing only provider user ID | Current best practice | We issue our own JWTs; provider tokens are useless after getting user info |
| Columns on User model for OAuth | Separate oauth_accounts table | Current best practice | Supports multiple providers, cleaner queries, no schema changes for new providers |

**Deprecated/outdated:**
- `Flask-OAuthlib`: Superseded by Authlib. Do not use.
- `python-social-auth`: Heavy, complex. Authlib is simpler for this use case.

## Open Questions

1. **Frontend redirect after OAuth callback**
   - What we know: The OAuth callback receives the authorization code and exchanges it for tokens. Our API needs to return the JWT pair to the client.
   - What's unclear: In a pure API scenario, the callback endpoint could return JSON. If a frontend exists, it might need to redirect with tokens in URL fragment or set cookies.
   - Recommendation: Return JSON `TokenResponse` directly from callback endpoints (consistent with existing `/auth/login`). Frontend integration can be added later if needed.

2. **Email verification trust for Google vs GitHub**
   - What we know: Google OIDC returns `email_verified` boolean. GitHub verifies emails internally but the field is `verified` in the `/user/emails` response.
   - What's unclear: Should we reject unverified emails from either provider?
   - Recommendation: For Google, check `email_verified == true`. For GitHub, only use emails where `verified == true` from `/user/emails`. This prevents account takeover via unverified email addresses.

3. **OAuth provider credentials in development**
   - What we know: OAuth requires registered apps with Google and GitHub, which provide client_id and client_secret.
   - What's unclear: Whether to require real OAuth credentials for running tests.
   - Recommendation: Mock the Authlib OAuth client in tests. Use empty string defaults for OAuth settings so the app starts without credentials (OAuth endpoints will fail gracefully if not configured).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `poetry run task test` |
| Full suite command | `poetry run pytest tests/ -v` |
| Estimated runtime | ~5 seconds |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-06a | GET /auth/google redirects to Google consent | integration | `poetry run pytest tests/test_oauth.py::TestGoogleOAuth::test_google_login_redirects -x` | No -- Wave 0 gap |
| AUTH-06b | GET /auth/github redirects to GitHub auth | integration | `poetry run pytest tests/test_oauth.py::TestGitHubOAuth::test_github_login_redirects -x` | No -- Wave 0 gap |
| AUTH-06c | Google callback returns JWT token pair | integration | `poetry run pytest tests/test_oauth.py::TestGoogleOAuth::test_google_callback_returns_tokens -x` | No -- Wave 0 gap |
| AUTH-06d | GitHub callback returns JWT token pair | integration | `poetry run pytest tests/test_oauth.py::TestGitHubOAuth::test_github_callback_returns_tokens -x` | No -- Wave 0 gap |
| AUTH-06e | OAuth email matches existing user -- links account | integration | `poetry run pytest tests/test_oauth.py::TestAccountLinking::test_oauth_links_existing_email -x` | No -- Wave 0 gap |
| AUTH-06f | OAuth-only user has no password | integration | `poetry run pytest tests/test_oauth.py::TestAccountLinking::test_oauth_user_no_password -x` | No -- Wave 0 gap |
| AUTH-06g | Duplicate OAuth link is idempotent | integration | `poetry run pytest tests/test_oauth.py::TestAccountLinking::test_duplicate_oauth_login -x` | No -- Wave 0 gap |

### Nyquist Sampling Rate
- **Minimum sample interval:** After every committed task -> run: `poetry run task test`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~5 seconds

### Wave 0 Gaps (must be created before implementation)
- [ ] `tests/test_oauth.py` -- covers AUTH-06 (all OAuth test cases)
- [ ] Mock/fixture for Authlib OAuth client to simulate provider responses without real OAuth credentials
- [ ] Test helper to create OAuth-linked users for integration tests

## Sources

### Primary (HIGH confidence)
- [Authlib PyPI](https://pypi.org/project/Authlib/) - v1.6.8, released Feb 14 2026, Python >=3.9
- [Authlib FastAPI docs](https://docs.authlib.org/en/latest/client/fastapi.html) - OAuth client setup, SessionMiddleware, authorize_redirect/authorize_access_token patterns
- [Authlib Starlette docs](https://docs.authlib.org/en/latest/client/starlette.html) - Provider registration, HTTPX async backend, session requirements
- [Authlib Web OAuth Clients](https://docs.authlib.org/en/latest/client/frameworks.html) - GitHub registration with API base URL, scope, token URLs
- [Authlib demo-oauth-client](https://github.com/authlib/demo-oauth-client/blob/master/fastapi-google-login/app.py) - Complete working Google login example
- [GitHub OAuth Scopes docs](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps) - user:email scope includes user scope
- [GitHub REST API emails endpoint](https://docs.github.com/en/rest/users/emails) - /user/emails returns verified emails
- [Google OIDC docs](https://developers.google.com/identity/openid-connect/openid-connect) - userinfo response fields: sub, email, email_verified

### Secondary (MEDIUM confidence)
- [FastAPI Users OAuth config](https://fastapi-users.github.io/fastapi-users/10.1/configuration/oauth/) - OAuthAccount table design pattern, associate_by_email approach
- [itsdangerous PyPI](https://pypi.org/project/itsdangerous/) - v2.2.0, required for Starlette SessionMiddleware
- [Authlib GitHub issue #425](https://github.com/authlib/authlib/issues/425) - SessionMiddleware is required for OAuth2 state in Starlette
- [Authlib GitHub issue #376](https://github.com/authlib/authlib/issues/376) - CSRF state mismatch debugging

### Tertiary (LOW confidence)
- None -- all findings verified with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Authlib is the de facto Python OAuth library, verified on PyPI and official docs
- Architecture: HIGH - Patterns derived from Authlib official examples and FastAPI Users design (separate OAuth table)
- Pitfalls: HIGH - GitHub email null issue documented in multiple official sources; hashed_password nullable derived from direct codebase analysis

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain, OAuth patterns well-established)
