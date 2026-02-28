---
phase: 20-auth-integration
plan: 01
subsystem: auth
tags: [nextauth, jwt, google-oauth, fastapi, next-auth-v5, jose, session-cookies, token-refresh]

requires:
  - phase: 19-monorepo-frontend-foundation
    provides: Next.js 16 App Router frontend with providers.tsx, TanStack Query, ThemeProvider

provides:
  - NextAuth.js v5 config (auth.ts) with Credentials + Google providers, jwt/session callbacks, transparent token refresh
  - POST /auth/google/token backend endpoint for Google id_token exchange
  - NextAuth route handler at /api/auth/[...nextauth]
  - SessionProvider wrapping the entire Next.js app
  - Encrypted httpOnly cookie storing FastAPI token pair (access + refresh)

affects:
  - 20-02-auth-ui (login/register pages — use signIn, signOut, useSession from this plan)
  - 20-03-route-protection (proxy.ts uses auth() from this plan)
  - Phase 21+ (all authenticated API calls depend on session.accessToken from this plan)

tech-stack:
  added:
    - next-auth@beta (5.0.0-beta.30) — NextAuth.js v5 for Next.js App Router
    - jose — JWT decoding (decodeJwt) to extract sub/role claims without /me API call
    - google-auth ^2.48.0 — Google id_token verification via Google public keys (Python backend)
    - requests ^2.32.5 — HTTP transport required by google-auth (Python backend)
  patterns:
    - NextAuth JWT strategy: FastAPI token pair stored inside encrypted NextAuth session cookie
    - jwt callback handles three cases: Credentials first-signin, Google id_token exchange, token refresh
    - Concurrent-refresh guard: module-level refreshPromise prevents duplicate refresh calls
    - decodeJwt (jose) used to extract userId/role from FastAPI access_token without /me API call
    - Credentials authorize returns null (not throw) on login failure — prevents 500 errors
    - AUTH_ env var prefix (not NEXTAUTH_) — NextAuth v5 convention

key-files:
  created:
    - frontend/src/auth.ts — NextAuth config: exports handlers, auth, signIn, signOut
    - frontend/src/app/api/auth/[...nextauth]/route.ts — NextAuth route handler (GET, POST)
  modified:
    - frontend/src/components/providers.tsx — added SessionProvider as outermost wrapper
    - backend/app/users/router.py — added POST /auth/google/token endpoint
    - backend/app/users/schemas.py — added GoogleTokenRequest schema
    - backend/pyproject.toml — added google-auth, requests dependencies

key-decisions:
  - "POST /auth/google/token new backend endpoint (not calling existing /auth/google): existing Authlib redirect flow conflicts with NextAuth's own OAuth state management"
  - "jose decodeJwt (not verify) for FastAPI JWT claims extraction: verification is FastAPI's responsibility; decoding avoids extra /me API call"
  - "Concurrent-refresh guard with module-level refreshPromise: prevents race condition when multiple server components hit jwt callback simultaneously during token expiry window"
  - "Credentials authorize returns null on 4xx failures (not throw): per NextAuth v5 spec — throw triggers 500, null triggers CredentialsSignin error with clean UX"
  - ".env.local not committed (gitignored): placeholder values documented in plan; user must run npx auth secret and add Google OAuth credentials"

patterns-established:
  - "Token expiry tracked as accessTokenExpiry = Date.now() + 14*60*1000 (14 min buffer before 15-min FastAPI TTL)"
  - "session.error surface pattern: token.error set in jwt callback, surfaced via session callback — client watches and calls signOut()"
  - "API base via NEXT_PUBLIC_API_URL ?? 'http://localhost:8000' — consistent with existing lib/api.ts pattern"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-07]

duration: ~18min
completed: 2026-02-27
---

# Phase 20 Plan 01: Auth Integration Summary

**NextAuth.js v5 wired to FastAPI with Credentials + Google providers, encrypted httpOnly cookie session storing FastAPI token pair, and transparent 14-minute token refresh**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-02-27T11:25:00Z
- **Completed:** 2026-02-27T11:43:00Z
- **Tasks:** 2
- **Files modified:** 7 (+ package-lock.json)

## Accomplishments

- NextAuth.js v5 configured as the session layer: stores FastAPI access + refresh tokens in encrypted httpOnly cookie; all auth logic stays in FastAPI
- Google OAuth handled end-to-end: NextAuth manages consent flow, backend POST /auth/google/token validates Google id_token and returns FastAPI tokens
- Transparent token refresh in jwt callback: access token silently refreshed at 14-min threshold (1 min before FastAPI's 15-min TTL) with concurrent-refresh guard
- SessionProvider wraps the app, enabling useSession() in all client components for Phase 20 UI work

## Task Commits

Each task was committed atomically:

1. **Task 1: POST /auth/google/token backend endpoint** - `e512743` (feat)
2. **Task 2: NextAuth.js v5 configuration + SessionProvider** - `c293b71` (feat)

**Plan metadata:** (final docs commit below)

## Files Created/Modified

- `frontend/src/auth.ts` — Central NextAuth config: Credentials + Google providers, jwt/session callbacks, refreshAccessToken, decodeJwtPayload; exports handlers/auth/signIn/signOut
- `frontend/src/app/api/auth/[...nextauth]/route.ts` — Minimal NextAuth route handler exporting GET and POST from handlers
- `frontend/src/components/providers.tsx` — Added SessionProvider from next-auth/react as outermost wrapper (outside QueryClientProvider)
- `backend/app/users/router.py` — Added google_token_exchange endpoint: validates Google id_token via google-auth, delegates to existing oauth_login() service
- `backend/app/users/schemas.py` — Added GoogleTokenRequest schema with id_token field
- `backend/pyproject.toml` + `backend/poetry.lock` — Added google-auth ^2.48.0 and requests ^2.32.5 dependencies

## Decisions Made

- **POST /auth/google/token new endpoint (not calling existing /auth/google):** The existing backend `/auth/google` route uses Authlib's server-side OAuth state (Starlette sessions). NextAuth can't initiate that redirect flow from its jwt callback — it would cause CSRF/state conflicts. Solution: new lean endpoint that accepts a raw Google id_token and validates it directly via google-auth library.
- **jose `decodeJwt` for claim extraction:** FastAPI access_token contains userId (sub) and role claims. Using jose's `decodeJwt` (NOT verify) extracts them without an extra `/me` API call. Verification is FastAPI's job; Next.js just needs the values.
- **Concurrent-refresh guard:** Module-level `refreshPromise` variable ensures only one refresh call fires even if multiple server components hit the jwt callback simultaneously while the token is expired.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed requests package required by google-auth transport**
- **Found during:** Task 1 (verifying /auth/google/token route registration)
- **Issue:** `google.auth.transport.requests` module requires the `requests` Python package which was not in pyproject.toml; import failed with `ModuleNotFoundError: No module named 'requests'`
- **Fix:** Ran `poetry add requests` to install requests ^2.32.5
- **Files modified:** backend/pyproject.toml, backend/poetry.lock
- **Verification:** `poetry run python -c "from app.users.router import router"` succeeded
- **Committed in:** e512743 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking dependency)
**Impact on plan:** Necessary dependency gap — google-auth requires requests for its HTTP transport. No scope creep.

## Issues Encountered

- `.env.local` is gitignored (correct security behavior) — placeholder values set locally. User must run `npx auth secret` in `frontend/` and add Google OAuth credentials from Google Cloud Console before Google OAuth will work.

## User Setup Required

Before Google OAuth login will function, the user must:

1. **Generate AUTH_SECRET:** Run `npx auth secret` in `frontend/` directory, copy generated value to `frontend/.env.local`
2. **Create Google OAuth credentials:**
   - Google Cloud Console -> APIs & Services -> Credentials -> Create OAuth 2.0 Client ID (Web application type)
   - Add `http://localhost:3000/api/auth/callback/google` to Authorized redirect URIs
   - Copy Client ID to `AUTH_GOOGLE_ID` in `frontend/.env.local`
   - Copy Client Secret to `AUTH_GOOGLE_SECRET` in `frontend/.env.local`
3. **Set backend Google credentials:** Add `GOOGLE_CLIENT_ID=<same-client-id>` to `backend/.env`

Email/password login (Credentials provider) works without Google credentials.

## Next Phase Readiness

- Session layer complete: auth.ts exports handlers/auth/signIn/signOut ready for Phase 20-02 login/register UI
- Backend /auth/google/token endpoint ready for Google OAuth flow
- SessionProvider installed: all client components can use useSession() from next-auth/react
- Token refresh logic wired: Phase 21+ authenticated API calls will have valid tokens available via session.accessToken
- Blocker for Google OAuth: user must configure Google Cloud Console credentials and AUTH_SECRET before testing

---
*Phase: 20-auth-integration*
*Completed: 2026-02-27*
