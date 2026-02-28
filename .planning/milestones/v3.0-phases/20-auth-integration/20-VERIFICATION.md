---
phase: 20-auth-integration
verified: 2026-02-27T00:00:00Z
status: human_needed
score: 10/11 must-haves verified
re_verification: false
human_verification:
  - test: "Register a new account and verify session established"
    expected: "After submitting /register form, user is redirected to home page and Header shows user email and Sign Out button"
    why_human: "Cannot programmatically drive browser form submission, NextAuth session cookie creation, or Header rendering state"
  - test: "Login with email/password and verify session established"
    expected: "After submitting /login form, user is redirected to callbackUrl (or /), Header shows user email"
    why_human: "Cannot programmatically drive browser sign-in flow or verify live session cookie"
  - test: "Session persistence across page refresh"
    expected: "After F5 refresh while logged in, Header still shows user email (NextAuth encrypted httpOnly cookie survives reload)"
    why_human: "Session cookie behavior across navigation requires a live browser"
  - test: "Logout clears session and Header reverts to Sign In link"
    expected: "Clicking Sign Out button in Header → redirect to /, Header shows Sign In link"
    why_human: "Cannot trigger live signOut() call and observe DOM change programmatically"
  - test: "Route protection redirects unauthenticated user"
    expected: "Visiting http://localhost:3000/account while logged out → redirect to /login?callbackUrl=/account"
    why_human: "proxy.ts route matching and redirect requires running Next.js middleware"
  - test: "Google OAuth sign-in flow (requires Google credentials configured)"
    expected: "Clicking Continue with Google → Google consent → redirect to app with session"
    why_human: "Live browser OAuth consent flow; also requires AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET to be set in .env.local"
  - test: "Transparent token refresh (requires waiting 15+ minutes)"
    expected: "Session remains valid after 15 minutes without manual re-login"
    why_human: "Time-dependent behavior; requires waiting for access token TTL to expire and observing transparent refresh"
  - test: "AUTH-08: Deactivated user auto-signout on next API call"
    expected: "Deactivate user via admin API, then trigger any authenticated API call → user is signed out automatically"
    why_human: "Requires admin access to deactivate a user and making an API call that returns 403; cannot simulate programmatically without running both servers"
---

# Phase 20: Auth Integration Verification Report

**Phase Goal:** Users can securely sign up, sign in (email + Google), and maintain sessions that carry FastAPI tokens
**Verified:** 2026-02-27
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | User can register with email+password via POST /auth/register and receive a NextAuth session | VERIFIED | `RegisterForm.tsx` calls `fetch(/auth/register)` then `signIn('credentials')`. Backend `/auth/register` route exists in `router.py` returning `TokenResponse`. |
| 2  | User can login with email+password via POST /auth/login and receive a NextAuth session | VERIFIED | `auth.ts` Credentials `authorize` callback calls `fetch(${API}/auth/login)` with `{email, password}`. Non-2xx returns `null` (not throw). `LoginForm.tsx` calls `signIn('credentials')`. |
| 3  | User can login with Google OAuth and receive a NextAuth session backed by FastAPI tokens | VERIFIED (code path exists; live test needs human) | `auth.ts` `jwt` callback handles `account.provider === "google"` by posting to `${API}/auth/google/token`. Backend `google_token_exchange` endpoint validates `id_token` via `google-auth` library and calls `oauth_login()`. |
| 4  | Session persists across page refresh (encrypted httpOnly cookie stores FastAPI token pair) | VERIFIED (session strategy confirmed; live test needs human) | `auth.ts` sets `session: { strategy: "jwt" }`. `accessToken`, `refreshToken`, and `accessTokenExpiry` stored in NextAuth-encrypted cookie via `jwt` callback. `SessionProvider` wraps app in `providers.tsx`. |
| 5  | Expired access tokens are refreshed transparently in the jwt callback before API calls fail | VERIFIED | `auth.ts` `jwt` callback: `if (Date.now() < token.accessTokenExpiry) return token; return refreshAccessToken(token)`. `refreshAccessToken` calls `POST /auth/refresh` with concurrent-refresh guard (`refreshPromise`). |
| 6  | User can log out and is redirected to the home page | VERIFIED | `UserMenu.tsx` calls `signOut({ callbackUrl: '/' })`. `AuthGuard` in `providers.tsx` calls `signOut({ callbackUrl: '/login' })` on `session.error === 'RefreshTokenError'`. |
| 7  | Unauthenticated user visiting /account, /orders, /checkout, /wishlist, or /prebook is redirected to /login with callbackUrl | VERIFIED | `proxy.ts` exports named `proxy = auth(req => {...})`. Protected prefixes array matches all 5 routes. Redirect logic: `url.searchParams.set("callbackUrl", pathname)`. |
| 8  | Deactivated user's next API call triggers automatic sign-out via 403 interceptor | VERIFIED | `providers.tsx` `QueryCache.onError` and `MutationCache.onError` check `error instanceof ApiError && error.status === 403` → `signOut({ callbackUrl: '/login' })`. Backend `deps.py` confirms deactivated users receive 403 with `AUTH_ACCOUNT_DEACTIVATED`. |
| 9  | Login page shows email/password form and Google sign-in button | VERIFIED | `frontend/src/app/(auth)/login/page.tsx` renders `<LoginForm>` (in `<Suspense>`) and `<GoogleSignInButton>`. |
| 10 | Register page shows email/password form with validation | VERIFIED | `frontend/src/app/(auth)/register/page.tsx` renders `<RegisterForm>`. `RegisterForm.tsx` has confirm password, 8-char min validation, error banner. |
| 11 | Header shows Sign In link when logged out and user info + Sign Out when logged in | VERIFIED (code; live state needs human) | `Header.tsx` renders `<UserMenu />`. `UserMenu.tsx` uses `useSession()` with mounted guard: shows `<Link href="/login">Sign In</Link>` when unauthenticated, email + `signOut()` button when authenticated. |

**Score:** 11/11 truths code-verified (8 also need human confirmation for live browser behavior)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/auth.ts` | NextAuth config: Credentials + Google, jwt/session callbacks, token refresh | VERIFIED | 233 lines. Exports `{ handlers, auth, signIn, signOut }`. Module augmentation for Session/JWT/User types. `refreshAccessToken` with concurrent guard. `decodeJwtPayload` using jose. |
| `frontend/src/app/api/auth/[...nextauth]/route.ts` | NextAuth route handler exporting GET and POST | VERIFIED | 3 lines. `import { handlers } from "@/auth"` + `export const { GET, POST } = handlers`. Substantive and wired. |
| `frontend/src/proxy.ts` | Route protection middleware (named proxy export) | VERIFIED | 34 lines. Named export `proxy = auth(req => {...})`. Covers 5 protected prefixes. Redirects authenticated users off auth pages. |
| `frontend/src/components/auth/LoginForm.tsx` | Client component for email/password sign-in | VERIFIED | 106 lines. `signIn('credentials', {..., redirect: false})`. callbackUrl from `useSearchParams()`. Error banner. Show/hide password toggle. |
| `frontend/src/components/auth/RegisterForm.tsx` | Client component for email/password registration | VERIFIED | 162 lines. `fetch(/auth/register)` then `signIn('credentials')`. Confirm password validation. Error display. |
| `frontend/src/components/auth/GoogleSignInButton.tsx` | Client component calling signIn('google') | VERIFIED | 45 lines. Calls `signIn('google', { callbackUrl })`. Google G SVG logo. Outline variant button. |
| `frontend/src/components/layout/UserMenu.tsx` | Auth-aware header item with session state | VERIFIED | 57 lines. `useSession()` + mounted guard. Sign In link / email + Sign Out button states. |
| `frontend/src/components/layout/Header.tsx` | Updated header with UserMenu | VERIFIED | Imports and renders `<UserMenu />` between cart and ThemeToggle. |
| `frontend/src/components/providers.tsx` | SessionProvider wrapping app + 403 interceptor + AuthGuard | VERIFIED | `SessionProvider` is outermost wrapper. `QueryCache`/`MutationCache` with 403 interceptors. `AuthGuard` component watching `session.error`. |
| `frontend/src/app/(auth)/login/page.tsx` | Login page with LoginForm and GoogleSignInButton | VERIFIED | Card layout. LoginForm in `<Suspense>`. GoogleSignInButton. Link to /register. |
| `frontend/src/app/(auth)/register/page.tsx` | Register page with RegisterForm | VERIFIED | Card layout. RegisterForm. GoogleSignInButton. Link to /login. |
| `backend/app/users/router.py` | POST /auth/google/token endpoint | VERIFIED | `google_token_exchange` function at line 122. Validates via `google_id_token.verify_oauth2_token`. Calls `oauth_login()`. Returns `TokenResponse`. |
| `backend/app/users/schemas.py` | GoogleTokenRequest schema | VERIFIED | `class GoogleTokenRequest(BaseModel): id_token: str` at line 47. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/auth.ts` | `POST /auth/login` | Credentials `authorize` callback | WIRED | Line 138: `fetch(\`${API}/auth/login\`, { method: "POST", ...})`. Response consumed: `data.access_token` and `data.refresh_token` extracted. |
| `frontend/src/auth.ts` | `POST /auth/google/token` | `jwt` callback when `account.provider === "google"` | WIRED | Lines 192-199: `fetch(\`${API}/auth/google/token\`, { body: JSON.stringify({ id_token: account.id_token }) })`. Response consumed: tokens extracted and set on `token`. |
| `frontend/src/auth.ts` | `POST /auth/refresh` | `refreshAccessToken` called from `jwt` callback on expiry | WIRED | Line 70: `fetch(\`${API}/auth/refresh\`, { body: JSON.stringify({ refresh_token: token.refreshToken }) })`. Response consumed: new tokens returned. Expiry guard at line 216: `if (Date.now() < token.accessTokenExpiry) return token; return refreshAccessToken(token)`. |
| `frontend/src/components/providers.tsx` | `frontend/src/auth.ts` | SessionProvider wrapping app | WIRED | Line 6: `import { SessionProvider, useSession, signOut } from 'next-auth/react'`. Line 61: `<SessionProvider>` is outermost wrapper. |
| `frontend/src/proxy.ts` | `frontend/src/auth.ts` | `auth()` function for session check | WIRED | Line 1: `import { auth } from "@/auth"`. Line 10: `export const proxy = auth((req) => {...})`. |
| `frontend/src/components/auth/LoginForm.tsx` | `frontend/src/auth.ts` | `signIn('credentials', ...)` | WIRED | Line 5: `import { signIn } from 'next-auth/react'`. Line 29: `signIn('credentials', { email, password, redirect: false })`. Result checked lines 35-39. |
| `frontend/src/components/providers.tsx` | `signOut` on 403 | `QueryCache`/`MutationCache` `onError` interceptor | WIRED | Lines 35-50: `if (error instanceof ApiError && error.status === 403) { signOut({ callbackUrl: '/login' }) }` in both caches. |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| AUTH-01 | 20-01, 20-03 | User can sign up with email and password | SATISFIED | `RegisterForm.tsx` → `fetch(/auth/register)` → `signIn('credentials')`. Backend `POST /auth/register` returns `TokenResponse`. |
| AUTH-02 | 20-01, 20-03 | User can log in with email and password | SATISFIED | `LoginForm.tsx` → `signIn('credentials')` → `auth.ts` Credentials `authorize` → `fetch(/auth/login)`. |
| AUTH-03 | 20-01, 20-03 | User can log in with Google OAuth | SATISFIED (code) / NEEDS HUMAN (live) | `GoogleSignInButton` → `signIn('google')` → NextAuth Google provider → `jwt` callback → `POST /auth/google/token` → `oauth_login()`. Requires Google credentials in `.env.local` for live test. |
| AUTH-04 | 20-01, 20-03 | User session persists across page navigation and refresh | SATISFIED (code) / NEEDS HUMAN (live) | `strategy: "jwt"` in auth.ts. NextAuth encrypted cookie. `SessionProvider` ensures session available to all components. |
| AUTH-05 | 20-02, 20-03 | User can log out | SATISFIED | `UserMenu.tsx`: `signOut({ callbackUrl: '/' })`. `AuthGuard`: `signOut({ callbackUrl: '/login' })` on error. |
| AUTH-06 | 20-02, 20-03 | Protected routes redirect unauthenticated users to login | SATISFIED (code) / NEEDS HUMAN (live) | `proxy.ts` checks 5 protected prefixes; redirects to `/login?callbackUrl=`. Named `proxy` export confirmed (not `export default`). |
| AUTH-07 | 20-01, 20-03 | Access token refreshes transparently when expired | SATISFIED (code) / NEEDS HUMAN (live) | `auth.ts` jwt callback checks `Date.now() < token.accessTokenExpiry`; calls `refreshAccessToken()` which hits `POST /auth/refresh`. 14-min expiry buffer before 15-min FastAPI TTL. Concurrent guard via `refreshPromise`. |
| AUTH-08 | 20-02, 20-03 | Deactivated user is signed out on next API call | SATISFIED | `providers.tsx` `QueryCache`/`MutationCache` `onError` intercept `ApiError status 403`. Backend `deps.py` returns 403 for deactivated accounts. Note: REQUIREMENTS.md description says "401 handling" but the actual backend returns 403; implementation is consistent with backend behavior. |

**Orphaned requirements check:** All 8 AUTH requirements (AUTH-01 through AUTH-08) appear in plan frontmatter. No orphaned requirements.

**Note on AUTH-08 status code discrepancy:** REQUIREMENTS.md describes AUTH-08 as "401 handling" but the backend `deps.py` (line 63) returns HTTP 403 for deactivated users. The frontend implementation correctly intercepts 403. The REQUIREMENTS.md description is misleading but the implementation is internally consistent. This is an informational finding — no code fix needed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/providers.tsx` | 69-71 | `<AuthGuard>` wraps `{children}` but NOT `<Toaster>` and `<ReactQueryDevtools>` | Info | Toaster/Devtools outside AuthGuard is intentional — they don't need auth context. No impact on auth behavior. |
| REQUIREMENTS.md | AUTH-08 entry | Description says "401 handling" but backend sends 403 for deactivated users | Info | Documentation inconsistency only. Code is correct. |

No blocker or warning anti-patterns found. All `return null` instances in `auth.ts` are correct NextAuth Credentials pattern. Form `placeholder` attributes are HTML input attributes, not stub patterns. All handler implementations are substantive.

### Human Verification Required

Plan 20-03 is a `checkpoint:human-verify` plan that documents human approval was given. The SUMMARY confirms "user verified all auth flows, and approved." The following items are flagged for completeness — they were part of that checkpoint and are listed here for traceability:

#### 1. Email Registration Flow

**Test:** Visit http://localhost:3000/register, fill email + password (8+ chars), click Create Account
**Expected:** Redirect to /, Header shows user email and Sign Out button, no console errors
**Why human:** NextAuth session cookie creation and Header DOM state require a live browser

#### 2. Email Login Flow

**Test:** After logout, visit http://localhost:3000/login, enter registered credentials, click Sign In
**Expected:** Redirect to callbackUrl (or /), Header shows user email
**Why human:** Live signIn() call and session establishment require a running app

#### 3. Session Persistence

**Test:** While logged in, press F5; navigate away and back
**Expected:** Still logged in after refresh; Header still shows user state
**Why human:** httpOnly cookie survival across page reloads requires a live browser

#### 4. Logout

**Test:** Click Sign Out in Header while logged in
**Expected:** Redirect to /, Header reverts to Sign In link
**Why human:** Live signOut() and DOM state change require a running app

#### 5. Route Protection

**Test:** While logged out, visit http://localhost:3000/account
**Expected:** Redirect to /login?callbackUrl=/account; after login, redirect back to /account
**Why human:** Next.js middleware (proxy.ts) execution requires a running Next.js server

#### 6. Google OAuth Sign-In (requires configured credentials)

**Test:** Click Continue with Google on /login, complete Google consent
**Expected:** Session established with Google account email shown in Header
**Why human:** Live OAuth redirect flow; requires AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET in .env.local

#### 7. Transparent Token Refresh (AUTH-07)

**Test:** Log in, wait 15+ minutes, perform any navigation
**Expected:** Still logged in without re-authentication prompt
**Why human:** Time-dependent; requires waiting for token TTL expiry

#### 8. Deactivated User Auto-Signout (AUTH-08)

**Test:** Deactivate a user via admin API, then make an authenticated API call from that session
**Expected:** Automatic sign-out triggered by 403 response intercepted by QueryCache
**Why human:** Requires admin access, a deactivated user account, and a live authenticated API call

**Note:** Plan 20-03 SUMMARY documents that the human-verify checkpoint was approved. AUTH-07 and AUTH-08 are acknowledged in that SUMMARY as "difficult to verify manually without special tooling."

### Gaps Summary

No automated gaps found. All code paths are substantive and wired. The phase goal is code-complete.

The `human_needed` status reflects that 8 of the 11 truths involve live browser/server behavior that cannot be verified programmatically. Plan 20-03 records that a human verification checkpoint was passed on 2026-02-27.

---

_Verified: 2026-02-27_
_Verifier: Claude (gsd-verifier)_
