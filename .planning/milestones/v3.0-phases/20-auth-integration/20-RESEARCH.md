# Phase 20: Auth Integration - Research

**Researched:** 2026-02-27
**Domain:** NextAuth.js v5 (Auth.js) wired to FastAPI JWT backend with Google OAuth
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

None — user delegated all implementation decisions to Claude.

### Claude's Discretion

**Sign-up / Sign-in UX:**
- Page structure: same page with toggle vs separate /login and /register pages
- Validation error display: inline under fields vs top-of-form banner
- Error message tone: neutral-specific vs security-conscious vague
- Password field approach: single field with show/hide vs confirm password field

**Google OAuth flow (not discussed — Claude decides):**
- Button placement relative to email/password form
- First-time Google sign-in behavior (auto-create account or require linking)
- Account linking when Google email matches existing email/password account

**Session & redirect behavior (not discussed — Claude decides):**
- Post-login landing page
- Redirect-back-to-protected-route flow
- Session expiry UX (silent refresh vs prompt)
- Signed-out state indicators in the UI

**Auth page design (not discussed — Claude decides):**
- Page layout (centered card, split, full-page)
- Branding treatment on auth pages
- Dark mode styling for auth forms
- Mobile responsiveness for auth forms

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User can sign up with email and password | Credentials provider `authorize` → POST /auth/register → store tokens in NextAuth JWT |
| AUTH-02 | User can log in with email and password | Credentials provider `authorize` → POST /auth/login → store tokens in NextAuth JWT |
| AUTH-03 | User can log in with Google OAuth | Google provider → `jwt` callback exchanges Google `id_token` for backend tokens via POST /auth/google/token |
| AUTH-04 | User session persists across page navigation and refresh | NextAuth JWT strategy in encrypted httpOnly cookie; SessionProvider enables `useSession` on client |
| AUTH-05 | User can log out | `signOut()` client action + POST /auth/logout to revoke refresh token on backend |
| AUTH-06 | Protected routes redirect unauthenticated users to login | `proxy.ts` (Next.js 16) with `auth()` checks session; redirects to /login with callbackUrl |
| AUTH-07 | Access token refreshes transparently when expired | `jwt` callback checks `accessTokenExpiry`; calls POST /auth/refresh when expired |
| AUTH-08 | Deactivated user is signed out on next API call (401/403 handling) | QueryCache + MutationCache `onError` intercepts 403 response → calls `signOut()` |

</phase_requirements>

---

## Summary

Phase 20 wires NextAuth.js v5 (installed as `next-auth@beta`) to the existing FastAPI auth backend. The project is running **Next.js 16.1.6**, which means `middleware.ts` is deprecated and must be `proxy.ts`. Auth.js v5 provides a unified `auth()` function that works across server components, route handlers, and the new `proxy.ts` file.

The core architecture is: NextAuth acts as a **session layer** (encrypted JWE cookie) that stores the FastAPI token pair (access_token + refresh_token). NextAuth does NOT issue its own JWTs for the API — the FastAPI tokens are stored inside NextAuth's session cookie and attached to every API request as a Bearer header. Google OAuth works by letting NextAuth handle the Google consent flow, then in the `jwt` callback, exchanging the Google `id_token` for a FastAPI token pair by calling the backend's `/auth/google/callback`-equivalent endpoint.

The main non-trivial problems are: (1) transparent token refresh in the `jwt` callback, which has a known race-condition issue in NextAuth v5 but is manageable with a single-threaded refresh pattern; (2) the Google OAuth → FastAPI token exchange flow which requires calling the backend's `/auth/google` redirect — but since that backend route uses server-side OAuth state (Authlib/Starlette sessions), the cleanest approach is to have NextAuth handle the Google OAuth flow entirely on the frontend side, then send the Google `id_token` to a new or adapted backend endpoint that validates it and returns FastAPI tokens.

**Primary recommendation:** Use NextAuth v5 with Credentials provider (email/password) + Google provider. In the `jwt` callback, on Google sign-in, POST the Google `id_token` to `POST /auth/google/token` (a new lean backend endpoint) to exchange for FastAPI tokens. Store FastAPI `access_token`, `refresh_token`, and `accessTokenExpiry` in the NextAuth JWT. Refresh transparently in the `jwt` callback. Intercept 403 deactivation errors globally in TanStack Query's `QueryCache.onError`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next-auth | `@beta` (5.0.0-beta.30) | Auth session layer: JWT cookie, OAuth flows, server/client `auth()` | Only Auth.js-native integration for Next.js App Router; v5 is the current beta for Next.js 15+ and 16 |
| next-auth/providers/credentials | (included) | Handles email+password login via `authorize` callback | Built-in Credentials provider; no additional install |
| next-auth/providers/google | (included) | Handles Google OIDC consent flow | Built-in; auto-populates from `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` env vars |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| zod | ^3.x (likely already available) | Validate credentials input in `authorize` callback | Server-side input validation before hitting FastAPI |
| @tanstack/react-query | ^5.90.21 (already installed) | QueryCache/MutationCache global 401/403 interceptor | For AUTH-08: deactivated user auto-signout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| next-auth@beta | better-auth, Clerk, custom JWT cookies | next-auth@beta is project decision (v3.0 Roadmap); others would change entire auth architecture |
| JWT session strategy | Database sessions | Database sessions require an adapter; project uses FastAPI as auth authority — no Next.js DB needed |
| proxy.ts middleware | Per-page auth checks in Server Components | Middleware is the standard gating approach; per-page checks are defense-in-depth, not replacement |

**Installation:**
```bash
npm install next-auth@beta
```

---

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── auth.ts                          # NextAuth config (providers, callbacks)
├── app/
│   ├── api/
│   │   └── auth/
│   │       └── [...nextauth]/
│   │           └── route.ts         # Export { GET, POST } from auth.ts handlers
│   ├── (auth)/                      # Route group — no layout header/footer
│   │   ├── layout.tsx               # Centered card layout for auth pages
│   │   ├── login/
│   │   │   └── page.tsx             # Login form (email/password + Google button)
│   │   └── register/
│   │       └── page.tsx             # Register form
│   └── layout.tsx                   # Add SessionProvider here
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx            # 'use client' — Credentials signIn form
│   │   ├── RegisterForm.tsx         # 'use client' — register form
│   │   └── GoogleSignInButton.tsx   # 'use client' — calls signIn('google')
│   └── layout/
│       └── Header.tsx               # Add auth state: Sign In / Sign Out button
├── lib/
│   ├── api.ts                       # Update: inject Authorization header from session
│   └── auth-utils.ts                # Helpers: getServerSession wrapper, token expiry check
└── proxy.ts                         # Route protection (replaces middleware.ts in Next.js 16)
```

### Pattern 1: NextAuth Configuration (`auth.ts`)
**What:** Central auth config — providers, callbacks, session strategy, custom pages
**When to use:** Always — this is the single source of truth for auth

```typescript
// Source: https://authjs.dev/reference/nextjs
import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import Google from "next-auth/providers/google"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { type: "email" },
        password: { type: "password" },
      },
      async authorize(credentials) {
        // Call FastAPI /auth/login or /auth/register
        // Return { id, email, role, accessToken, refreshToken, accessTokenExpiry }
        // Return null on failure — triggers CredentialsSignin error
      },
    }),
    Google({
      clientId: process.env.AUTH_GOOGLE_ID,
      clientSecret: process.env.AUTH_GOOGLE_SECRET,
    }),
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
    error: "/login",       // redirect auth errors back to login with ?error=
  },
  callbacks: {
    async jwt({ token, user, account }) {
      // First sign-in: user and account are populated
      if (user) {
        // Credentials: user has accessToken, refreshToken, accessTokenExpiry
        token.accessToken = user.accessToken
        token.refreshToken = user.refreshToken
        token.accessTokenExpiry = user.accessTokenExpiry
        token.userId = user.id
        token.role = user.role
      }
      if (account?.provider === "google") {
        // Exchange Google id_token for FastAPI token pair
        // Call POST /auth/google/token with { id_token: account.id_token }
      }
      // Transparent refresh: check expiry and call /auth/refresh if needed
      if (Date.now() < (token.accessTokenExpiry as number)) {
        return token
      }
      return refreshAccessToken(token)
    },
    async session({ session, token }) {
      // Expose what the client needs
      session.accessToken = token.accessToken as string
      session.user.id = token.userId as string
      session.user.role = token.role as string
      if (token.error) session.error = token.error
      return session
    },
  },
})
```

### Pattern 2: Route Handler (`app/api/auth/[...nextauth]/route.ts`)
**What:** Minimal file — just export NextAuth handlers
**When to use:** Always required

```typescript
// Source: https://authjs.dev/reference/nextjs
import { handlers } from "@/auth"
export const { GET, POST } = handlers
```

### Pattern 3: `proxy.ts` Route Protection (Next.js 16)
**What:** Intercepts unauthenticated requests to protected routes at the network edge
**When to use:** Next.js 16 requires `proxy.ts` (middleware.ts is deprecated)

```typescript
// Source: https://nextjs.org/blog/next-16 (Proxy section)
import { auth } from "@/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
  const { nextUrl } = req
  const isLoggedIn = !!req.auth

  // Define which paths require auth
  const protectedPaths = ["/account", "/orders", "/checkout", "/wishlist"]
  const isProtected = protectedPaths.some(p => nextUrl.pathname.startsWith(p))

  if (isProtected && !isLoggedIn) {
    const loginUrl = new URL("/login", nextUrl.origin)
    loginUrl.searchParams.set("callbackUrl", nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
})

export const proxy = auth  // Required export name in Next.js 16

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}
```

### Pattern 4: Transparent Token Refresh in `jwt` Callback
**What:** When the FastAPI access token expires (15-min TTL), automatically call /auth/refresh
**When to use:** AUTH-07 — runs inside NextAuth's jwt callback

```typescript
// Source: https://authjs.dev/guides/refresh-token-rotation (adapted for custom backend)
async function refreshAccessToken(token: JWT) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    })

    if (!res.ok) throw new Error("Refresh failed")

    const data = await res.json()
    return {
      ...token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,  // Backend rotates refresh token
      accessTokenExpiry: Date.now() + 14 * 60 * 1000,  // 14 min (1 min buffer before 15-min TTL)
      error: undefined,
    }
  } catch {
    return { ...token, error: "RefreshTokenError" }
  }
}
```

### Pattern 5: Google OAuth → FastAPI Token Exchange
**What:** NextAuth handles Google consent flow; `jwt` callback exchanges Google `id_token` for FastAPI tokens
**When to use:** AUTH-03 — critical non-standard pattern

**The problem:** The backend's existing `/auth/google` route uses Authlib's server-side OAuth state (Starlette Sessions). NextAuth can't call that redirect route — it would create a conflicting OAuth flow.

**The solution:** Add a new, lean backend endpoint `POST /auth/google/token` that:
1. Accepts `{ id_token: string }` in the request body
2. Verifies the Google `id_token` using Google's public keys (via `google-auth-library` or direct JWKS validation)
3. Extracts email, sub (Google user ID), email_verified
4. Calls the existing `AuthService.oauth_login()` logic
5. Returns `{ access_token, refresh_token, token_type }`

This keeps FastAPI as the auth authority and reuses all existing business logic.

```typescript
// In auth.ts jwt callback — when account.provider === "google"
if (account?.provider === "google" && account.id_token) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/google/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: account.id_token }),
  })
  if (!res.ok) throw new Error("Google token exchange failed")
  const data = await res.json()
  token.accessToken = data.access_token
  token.refreshToken = data.refresh_token
  token.accessTokenExpiry = Date.now() + 14 * 60 * 1000
}
```

### Pattern 6: TypeScript Module Augmentation
**What:** Extend NextAuth's Session and JWT types to include FastAPI-specific fields
**When to use:** Required for TypeScript to know about `accessToken`, `role`, etc.

```typescript
// Source: https://authjs.dev/getting-started/typescript
// Place in auth.ts or a separate types/next-auth.d.ts

declare module "next-auth" {
  interface Session {
    accessToken: string
    error?: string
    user: {
      id: string
      role: string
    } & DefaultSession["user"]
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string
    refreshToken: string
    accessTokenExpiry: number
    userId: string
    role: string
    error?: string
  }
}
```

### Pattern 7: SessionProvider in Providers Component
**What:** Wrap the app in SessionProvider so client components can use `useSession`
**When to use:** Required for any client component needing auth state

The existing `src/components/providers.tsx` wraps QueryClient + ThemeProvider. Add SessionProvider there:

```typescript
// Updated providers.tsx
'use client'
import { SessionProvider } from "next-auth/react"
// ... existing imports

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        {/* ... rest of providers */}
      </QueryClientProvider>
    </SessionProvider>
  )
}
```

### Pattern 8: TanStack Query Global 403 Interceptor (AUTH-08)
**What:** Auto-signout when a deactivated user makes any API call and gets 403
**When to use:** AUTH-08 — QueryCache/MutationCache onError handlers

The backend returns HTTP 403 with `code: "AUTH_ACCOUNT_DEACTIVATED"` when a deactivated user's token is used. The TanStack Query global error handler intercepts this:

```typescript
// Updated providers.tsx QueryClient setup
const [queryClient] = useState(
  () => new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => {
        if (error instanceof ApiError && error.status === 403) {
          signOut({ callbackUrl: "/login" })
        }
      }
    }),
    mutationCache: new MutationCache({
      onError: (error) => {
        if (error instanceof ApiError && error.status === 403) {
          signOut({ callbackUrl: "/login" })
        }
      }
    }),
    defaultOptions: { /* ... existing options */ }
  })
)
```

### Pattern 9: API Fetch with Authorization Header
**What:** Inject `Authorization: Bearer {accessToken}` into every API request
**When to use:** All authenticated API calls — update existing `lib/api.ts`

The existing `apiFetch` in `lib/api.ts` does not add auth headers. It needs to be updated to optionally accept a token (passed from server components via `auth()`) or, for client-side calls, the token comes via `useSession`.

For **server-side** API calls: `const session = await auth(); apiFetch(..., { headers: { Authorization: Bearer ${session.accessToken} } })`

For **client-side** calls: Use a `useApiFetch` hook that gets the session from `useSession()`.

### Anti-Patterns to Avoid
- **Using `middleware.ts` filename:** This project is on Next.js 16.1.6 — use `proxy.ts`. The `middleware.ts` name is deprecated in Next.js 16 (will be removed in a future version).
- **Storing access token in localStorage or non-httpOnly cookie:** NextAuth's JWT session is stored as an httpOnly cookie (secure by default). Never expose tokens to JavaScript directly.
- **Calling FastAPI's `/auth/google` redirect route from NextAuth:** That route uses server-side OAuth state managed by Authlib/Starlette — it conflicts with NextAuth's own OAuth flow. Use a token-exchange endpoint instead.
- **Triggering `signOut` from within `jwt` callback on RefreshTokenError:** The jwt callback runs server-side; `signOut()` is a client function. Set `token.error = "RefreshTokenError"` in the jwt callback, then detect this in the session callback and surface it to the client via session. The `SessionProvider` / client code then calls `signOut()`.
- **Not updating `accessTokenExpiry` after refresh:** If expiry is not tracked, the jwt callback will call refresh on every request.
- **Race condition on concurrent refresh:** If multiple server components hit the jwt callback simultaneously while the access token is expired, multiple refresh calls could fire. For this project's use case (15-min access token, 7-day refresh token, token rotation enabled), the race window is extremely small and acceptable — implement sequential guard only if it becomes a problem.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session storage & encrypted cookies | Custom httpOnly cookie management | NextAuth JWT strategy | Encryption, rotation, signing, expiry built in |
| Google OAuth consent flow | Custom PKCE + state + CSRF management | NextAuth Google provider | OAuth state, CSRF tokens, nonce — massive footgun surface |
| CSRF protection on auth routes | Custom CSRF middleware | NextAuth built-in CSRF tokens | NextAuth v5 includes CSRF protection for POST routes |
| Protected route redirect logic | Manual auth checks in every page | proxy.ts + `auth()` | Edge-layer, single place, automatic callbackUrl |
| Token expiry tracking | Manual Date.now() everywhere | Store `accessTokenExpiry` in JWT, check in jwt callback | Centralized, runs server-side before any request |

**Key insight:** NextAuth v5's value is the encrypted session cookie + the `auth()` universal function. The Credentials provider's `authorize` is just a thin proxy to FastAPI — all real auth logic stays in FastAPI. Don't replicate FastAPI's validation in Next.js.

---

## Common Pitfalls

### Pitfall 1: `middleware.ts` vs `proxy.ts` in Next.js 16
**What goes wrong:** The auth proxy doesn't run, routes are unprotected, build warnings about deprecated file.
**Why it happens:** Next.js 16 renamed `middleware.ts` to `proxy.ts`. The `middleware.ts` file is deprecated (still works but will be removed).
**How to avoid:** Create `proxy.ts` at the root of `frontend/src/`. Export the auth function as `proxy` (not `middleware`).
**Warning signs:** Console warning "middleware.ts is deprecated, rename to proxy.ts"

### Pitfall 2: Google Token Exchange Conflicts with Existing Backend OAuth Route
**What goes wrong:** Trying to call the backend's `/auth/google` which expects a server-initiated OAuth flow (Authlib state/CSRF) fails with 400 or CSRF errors.
**Why it happens:** The backend's `/auth/google` uses Authlib's `authorize_redirect()` which stores state in a server-side Starlette session cookie. This flow cannot be initiated from a server-side fetch in the NextAuth jwt callback.
**How to avoid:** Add a new backend endpoint `POST /auth/google/token` that accepts a raw Google `id_token` (from NextAuth's Google provider) and returns FastAPI tokens. This bypasses Authlib's redirect flow entirely.
**Warning signs:** 400 errors from backend, "invalid_state" or "CSRF" error messages.

### Pitfall 3: Refreshed Token Not Persisted (Known Auth.js v5 Issue)
**What goes wrong:** After refreshing the access token in the `jwt` callback, `auth()` still returns the old token on the next call.
**Why it happens:** In Auth.js v5, there is a known issue (#6642) where the refreshed JWT is not reliably persisted back to the cookie after the jwt callback returns a new token.
**How to avoid:** The issue is primarily reported with `getServerSession()` (v4 pattern). Using the v5 `auth()` function in combination with `SessionProvider` and the `update()` callback can force session re-read. For most cases, the jwt callback returning a new token IS persisted correctly — the issue occurs in specific edge cases with concurrent requests.
**Warning signs:** Token is visibly still expired after refresh was supposedly called.

### Pitfall 4: `signOut()` Cannot Be Called from jwt Callback
**What goes wrong:** `TypeError: signOut is not a function` or unexpected behavior when trying to sign out a deactivated user from the jwt callback.
**Why it happens:** `signOut()` from `next-auth/react` is a client-side function. The jwt callback runs on the server.
**How to avoid:** Set `token.error = "RefreshTokenError"` in the jwt callback. Surface it in the session callback: `session.error = token.error`. In the `SessionProvider` setup or a root client component, watch for session.error and call `signOut()`.

### Pitfall 5: Missing `AUTH_SECRET` Environment Variable
**What goes wrong:** `MissingSecret` error in production; tokens cannot be encrypted/decrypted.
**Why it happens:** AUTH_SECRET is mandatory in production (NextAuth throws if missing).
**How to avoid:** Run `npx auth secret` to generate and add to `.env.local`. The variable name for v5 is `AUTH_SECRET` (not `NEXTAUTH_SECRET`).

### Pitfall 6: Credentials Provider `authorize` Must Return `null` (Not Throw) for Invalid Credentials
**What goes wrong:** Unhandled exception or 500 error instead of clean login failure UX.
**Why it happens:** If `authorize` throws, NextAuth treats it as a server error. Only `null` return triggers the "CredentialsSignin" error handled by the error page/component.
**How to avoid:** Catch FastAPI errors in `authorize`, return `null` for 401/422 responses. Only throw for genuine server errors (5xx).

### Pitfall 7: Next.js 16 `proxy.ts` Export Name
**What goes wrong:** Auth middleware does not intercept requests; routes are unprotected.
**Why it happens:** In Next.js 16, the file is `proxy.ts` AND the exported function must be named `proxy`. Simply exporting `auth as middleware` won't work.
**How to avoid:** Use `export { auth as proxy } from "@/auth"` or `export default auth; export const proxy = auth`.

---

## Code Examples

Verified patterns from official sources:

### Backend: New Endpoint for Google Token Exchange
```python
# Source: Pattern derived from existing oauth_login() in app/users/service.py
# Add to backend/app/users/router.py

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

class GoogleTokenRequest(BaseModel):
    id_token: str

@router.post("/auth/google/token", response_model=TokenResponse)
async def google_token_exchange(body: GoogleTokenRequest, db: DbSession) -> TokenResponse:
    """Exchange a Google id_token (from NextAuth) for FastAPI token pair."""
    try:
        idinfo = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise AppError(status_code=401, detail="Invalid Google token", code="AUTH_GOOGLE_INVALID_TOKEN")

    if not idinfo.get("email_verified"):
        raise AppError(status_code=401, detail="Google email not verified", code="AUTH_OAUTH_EMAIL_UNVERIFIED")

    service = _make_service(db)
    access_token, refresh_token = await service.oauth_login(
        provider="google",
        provider_user_id=idinfo["sub"],
        email=idinfo["email"],
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
```

Note: Requires `pip install google-auth` in the backend.

### Complete `auth.ts` Configuration
```typescript
// Source: authjs.dev/reference/nextjs + authjs.dev/guides/refresh-token-rotation
import NextAuth, { DefaultSession } from "next-auth"
import Credentials from "next-auth/providers/credentials"
import Google from "next-auth/providers/google"
import type { JWT } from "next-auth/jwt"
import { z } from "zod"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

declare module "next-auth" {
  interface Session {
    accessToken: string
    error?: string
    user: { id: string; role: string } & DefaultSession["user"]
  }
}
declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string
    refreshToken: string
    accessTokenExpiry: number
    userId: string
    role: string
    error?: string
  }
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
  try {
    const res = await fetch(`${API}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    })
    if (!res.ok) throw new Error("Refresh failed")
    const data = await res.json()
    return {
      ...token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      accessTokenExpiry: Date.now() + 14 * 60 * 1000,
      error: undefined,
    }
  } catch {
    return { ...token, error: "RefreshTokenError" }
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: { email: { type: "email" }, password: { type: "password" } },
      async authorize(credentials) {
        const parsed = z.object({
          email: z.string().email(),
          password: z.string().min(8),
        }).safeParse(credentials)
        if (!parsed.success) return null

        const res = await fetch(`${API}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed.data),
        })
        if (!res.ok) return null

        const data = await res.json()
        return {
          id: String(data.sub),          // decoded from JWT later or from a /me endpoint
          email: parsed.data.email,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          accessTokenExpiry: Date.now() + 14 * 60 * 1000,
        }
      },
    }),
    Google,
  ],
  session: { strategy: "jwt" },
  pages: { signIn: "/login", error: "/login" },
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        token.accessToken = (user as any).accessToken
        token.refreshToken = (user as any).refreshToken
        token.accessTokenExpiry = (user as any).accessTokenExpiry
        token.userId = user.id ?? ""
        token.role = (user as any).role ?? "user"
      }
      if (account?.provider === "google" && account.id_token) {
        const res = await fetch(`${API}/auth/google/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id_token: account.id_token }),
        })
        if (!res.ok) return { ...token, error: "GoogleTokenExchangeError" }
        const data = await res.json()
        token.accessToken = data.access_token
        token.refreshToken = data.refresh_token
        token.accessTokenExpiry = Date.now() + 14 * 60 * 1000
      }
      if (Date.now() < token.accessTokenExpiry) return token
      return refreshAccessToken(token)
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken
      session.user.id = token.userId
      session.user.role = token.role
      if (token.error) session.error = token.error
      return session
    },
  },
})
```

### Register Flow (separate from login in Credentials authorize)
```typescript
// src/app/(auth)/register/page.tsx — calls /auth/register, then signIn("credentials")
async function handleRegister(email: string, password: string) {
  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new ApiError(err.detail, res.status)
  }
  // After successful registration, sign in to create the NextAuth session
  await signIn("credentials", { email, password, redirectTo: "/" })
}
```

Note: Registration requires a separate page action since NextAuth Credentials `authorize` is for login only. The register form directly calls `/auth/register`, then calls `signIn("credentials")` to establish the session.

### `proxy.ts` for Next.js 16
```typescript
// Source: https://nextjs.org/blog/next-16
// frontend/src/proxy.ts  (NOT middleware.ts)
import { auth } from "@/auth"
import { NextResponse } from "next/server"

export const proxy = auth((req) => {
  const isLoggedIn = !!req.auth
  const { pathname } = req.nextUrl

  const protectedPrefixes = ["/account", "/orders", "/checkout", "/wishlist", "/prebook"]
  const isProtected = protectedPrefixes.some(p => pathname.startsWith(p))

  if (isProtected && !isLoggedIn) {
    const url = new URL("/login", req.nextUrl.origin)
    url.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
})

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `getServerSession(authOptions)` in server components | `auth()` universal function | NextAuth v5 | Simpler, works in middleware/proxy, route handlers, server components |
| `middleware.ts` filename | `proxy.ts` filename | Next.js 16 (Oct 2025) | Must rename; `middleware.ts` deprecated |
| `export { auth as middleware }` | `export const proxy = auth` or `export { auth as proxy }` | Next.js 16 | Export name must be `proxy` |
| `NEXTAUTH_SECRET` env var | `AUTH_SECRET` env var | NextAuth v5 | v5 uses `AUTH_` prefix convention |
| `NEXTAUTH_URL` env var | Auto-detected in Next.js (optional) | NextAuth v5 | No longer required to set explicitly |
| `pages/api/auth/[...nextauth].ts` | `app/api/auth/[...nextauth]/route.ts` | NextAuth v5 + App Router | Route handler format |
| `onError` in `useQuery` options | `QueryCache.onError` + `MutationCache.onError` | TanStack Query v5 | Per-query onError removed in v5 |

**Deprecated/outdated:**
- `next-auth/middleware` import: Replaced by exporting `auth` from `@/auth` directly
- `getSession()` client-side: Still works but prefer `useSession()` from SessionProvider
- Database sessions for this use case: JWT sessions are the right choice (FastAPI is auth authority)

---

## Open Questions

1. **Does the backend need `google-auth` Python package for `/auth/google/token`?**
   - What we know: The existing backend uses Authlib for the redirect flow. To validate a raw Google `id_token`, either `google-auth` (Google's official Python client) or manual JWKS validation is needed.
   - What's unclear: Whether `google-auth` is already in `requirements.txt`.
   - Recommendation: Check `backend/requirements.txt`. If absent, `pip install google-auth` adds it. Alternatively, validate the id_token via Google's `tokeninfo` endpoint (`https://oauth2.googleapis.com/tokeninfo?id_token=...`) — simpler but adds a network round-trip.

2. **Where does the user's `role` come from in the Credentials authorize callback?**
   - What we know: The FastAPI `/auth/login` returns `{ access_token, refresh_token, token_type }`. The `role` is embedded in the JWT claims (`sub`, `role`, `jti`, `iat`, `exp`). To get the role without hitting `/me`, decode the JWT on the frontend.
   - What's unclear: Whether we should decode the access_token JWT client-side or add a `/auth/me` endpoint to return user info.
   - Recommendation: Decode the FastAPI JWT on the frontend side in `authorize` using `jose` library or manual base64 decode (the payload is not encrypted, only signed). This avoids an extra API call. Add `jose` if needed: `npm install jose`.

3. **RefreshToken race condition in concurrent requests**
   - What we know: Auth.js v5 has a known issue (#6642) where concurrent requests can trigger multiple refresh calls.
   - What's unclear: Severity in this app's context (most pages are not highly concurrent at the moment).
   - Recommendation: Implement a simple guard: store a `refreshPromise` in a module-level variable in `auth.ts`. If a refresh is in-flight, return the existing promise rather than starting a new one. This is the recommended community pattern.

---

## Validation Architecture

> The `.planning/config.json` does not include `workflow.nyquist_validation` — skipping this section (no test framework is configured for the frontend at this time).

---

## Sources

### Primary (HIGH confidence)
- [Auth.js reference for Next.js](https://authjs.dev/reference/nextjs) — providers, callbacks, handlers API
- [Auth.js Refresh Token Rotation guide](https://authjs.dev/guides/refresh-token-rotation) — jwt callback refresh pattern
- [Auth.js Third-Party Backend guide](https://authjs.dev/guides/integrating-third-party-backends) — token storage in session
- [Auth.js TypeScript guide](https://authjs.dev/getting-started/typescript) — module augmentation for Session/JWT types
- [Auth.js Route Protection guide](https://authjs.dev/getting-started/session-management/protecting) — proxy.ts pattern
- [Next.js 16 release blog](https://nextjs.org/blog/next-16) — proxy.ts rename, breaking changes
- Backend source code: `backend/app/users/router.py`, `backend/app/users/service.py`, `backend/app/core/security.py` — actual endpoint contracts

### Secondary (MEDIUM confidence)
- [NextAuth GitHub Discussion #8884](https://github.com/nextauthjs/next-auth/discussions/8884) — Google id_token → custom backend exchange pattern (community-verified, matches official guide pattern)
- [Auth.js Google provider docs](https://authjs.dev/getting-started/providers/google) — env var names, callback URL format
- [Auth.js installation guide](https://authjs.dev/getting-started/installation) — `npm install next-auth@beta`, `AUTH_SECRET` requirement
- TanStack Query v5 `QueryCache.onError` pattern — verified via [TanStack Query discussion #6228](https://github.com/TanStack/query/discussions/6228) and [#3253](https://github.com/TanStack/query/discussions/3253)

### Tertiary (LOW confidence)
- [JWT token refresh issue in Auth.js v5 (#6642)](https://github.com/nextauthjs/next-auth/discussions/6642) — race condition description; workaround is community-sourced, not officially documented

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — official docs confirmed; next-auth@beta 5.0.0-beta.30 verified via npm
- Architecture: HIGH — all patterns from official Auth.js v5 docs + verified against Next.js 16 blog
- Pitfalls: HIGH for items 1, 3, 5, 6, 7 (documented in official sources); MEDIUM for item 2 (Google OAuth conflict is based on analysis of existing backend code + official OAuth flow docs); MEDIUM for item 4 (race condition documented in GitHub issues)
- Backend changes required: MEDIUM — the `POST /auth/google/token` endpoint needs to be added; this is a small addition that reuses existing service code

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (Auth.js v5 is still in beta — check for new beta releases before planning)
