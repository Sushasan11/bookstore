# Domain Pitfalls

**Domain:** Next.js 15 customer storefront added to an existing FastAPI bookstore backend (v3.0 milestone)
**Researched:** 2026-02-27
**Confidence:** HIGH for integration pitfalls (verified against official Next.js docs, NextAuth.js GitHub discussions, FastAPI CORS docs, TanStack Query docs); MEDIUM for Token refresh race conditions (multiple community sources, no official resolution); LOW where noted

> This file covers pitfalls specific to adding a Next.js 15 (App Router) frontend to an existing FastAPI backend. The backend is production-hardened (v2.1, Python 3.11+, FastAPI, PostgreSQL, JWT access+refresh tokens, `is_active` lockout per request, Google OAuth). The frontend introduces NextAuth.js, openapi-typescript, TanStack Query, shadcn/ui, and a monorepo restructure (`backend/` + `frontend/`). Pitfalls are ordered by severity.

---

## Critical Pitfalls

### Pitfall 1: FastAPI CORS — `allow_credentials=True` with `allow_origins=["*"]` Silently Breaks All Auth

**What goes wrong:**
The FastAPI backend is configured with `CORSMiddleware(allow_origins=["*"], allow_credentials=True)`. This combination is rejected by every browser per the CORS spec: when credentials (cookies, Authorization headers) are included in a cross-origin request, the `Access-Control-Allow-Origin` response header cannot be `*` — it must be the exact requesting origin. The result is that all credentialed requests from the Next.js frontend fail with a CORS error, but the FastAPI server logs show 200 OK. The mismatch between server logs (success) and browser behavior (blocked) makes this hard to diagnose.

**Why it happens:**
Developers start with `allow_origins=["*"]` during initial API development (no CORS issues when testing with curl or Postman, which don't enforce CORS). Adding `allow_credentials=True` for cookie-based auth later seems additive but actually invalidates the wildcard. FastAPI's `CORSMiddleware` does not validate this combination at startup — it silently sets the header value and the browser rejects it at runtime.

**Consequences:**
- Every authenticated request (login, cart, checkout, wishlist, reviews) fails with a CORS error in the browser
- Server logs show 200 OK — the error is browser-side only
- The mistake is often discovered only after the frontend is connected to the backend for the first time

**Prevention:**
Set explicit origins in `CORSMiddleware`, never use `"*"` with `allow_credentials=True`:

```python
# app/main.py — correct CORS for credentialed cross-origin requests
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:3000",      # Next.js dev server
    "https://bookstore.example.com",  # Production frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,         # Required for Authorization header
    allow_methods=["*"],
    allow_headers=["*"],            # Required for Authorization, Content-Type
)
```

The `ALLOWED_ORIGINS` list must come from environment variables, not be hardcoded, so dev/staging/production values differ without code changes.

**Detection:**
- Browser devtools Network tab shows CORS error on credentialed requests
- Server logs show 200 OK for the same request
- `Access-Control-Allow-Origin: *` in response headers with `Authorization` in request

**Phase to address:** Monorepo setup / project scaffold phase. CORS must be correct before any authenticated endpoint is tested through the browser.

---

### Pitfall 2: NextAuth.js Session Does Not Carry FastAPI's `access_token` — All API Calls Return 401

**What goes wrong:**
NextAuth.js is configured with a Credentials provider that calls `/auth/login` (FastAPI) and receives `{ access_token, refresh_token, token_type }`. The `authorize()` callback returns the user object, but the FastAPI `access_token` is not persisted into the NextAuth.js session by default. When the frontend makes API calls to FastAPI, it has no token to include in the `Authorization: Bearer` header — FastAPI returns 401 for every protected endpoint.

**Why it happens:**
NextAuth.js manages its own JWT session (encrypted cookie), separate from the backend JWT. The `authorize()` callback result is stored in the NextAuth session, but only the fields explicitly mapped in the `jwt` callback and `session` callback are available on the client. Developers implement the Credentials provider and assume the `access_token` is automatically available via `useSession()` — it is not.

**Consequences:**
- `session.user` exists but `session.accessToken` is undefined
- Every `fetch()` call with `Authorization: Bearer ${session.accessToken}` sends `Authorization: Bearer undefined`
- FastAPI returns 401; frontend shows as a network error or empty state rather than an auth error

**Prevention:**
Explicitly thread the backend `access_token` through NextAuth.js callbacks in this exact order:

```typescript
// auth.ts (NextAuth.js v5 / Auth.js)
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      async authorize(credentials) {
        const res = await fetch(`${process.env.API_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(credentials),
        });
        if (!res.ok) return null;
        const data = await res.json();
        // Return the FastAPI tokens as part of the user object
        return {
          id: data.user.id,
          email: data.user.email,
          accessToken: data.access_token,    // FastAPI JWT
          refreshToken: data.refresh_token,  // FastAPI opaque refresh token
          accessTokenExpiry: Date.now() + 30 * 60 * 1000, // 30min
        };
      },
    }),
  ],
  callbacks: {
    // 1. jwt callback: persist tokens into the NextAuth session cookie
    async jwt({ token, user }) {
      if (user) {
        // Only on initial sign-in — `user` is populated from authorize()
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.accessTokenExpiry = user.accessTokenExpiry;
      }
      return token;
    },
    // 2. session callback: expose tokens to the client via useSession()
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.refreshToken = token.refreshToken;
      return session;
    },
  },
});
```

**Detection:**
- `console.log(session)` shows `session.accessToken` is `undefined`
- All FastAPI requests return 401
- `Authorization: Bearer undefined` visible in browser Network tab

**Phase to address:** Auth integration phase (the first phase that connects NextAuth.js to the FastAPI backend). This is the most fundamental integration point — nothing else works until this is correct.

---

### Pitfall 3: Deactivated Users Keep Working — `is_active` Lockout Invisible to Next.js Middleware

**What goes wrong:**
The FastAPI backend checks `User.is_active` on every protected request (a design decision documented in PROJECT.md: "DB is_active check per request, 1 extra query acceptable"). When an admin deactivates a user, their next API call to FastAPI returns 401/403 immediately. However, NextAuth.js middleware only checks whether the NextAuth session cookie is valid — it does not re-validate the user's active status. The deactivated user still has a valid NextAuth session and can navigate protected pages freely. Only actual API calls to FastAPI will fail.

**Why it happens:**
NextAuth.js session validity and backend user validity are two separate state systems. The NextAuth session is a cryptographic assertion that the user authenticated at some past point; it knows nothing about the user's current backend state. Developers protect routes with NextAuth middleware and assume this is equivalent to the backend's per-request `is_active` check — it is not.

**Consequences:**
- Deactivated users see the authenticated UI (cart, wishlist, account pages) for the rest of their session lifetime
- API calls will fail with 401 (FastAPI rejects them), but the page itself renders in logged-in state
- The user may be confused by partial failure ("I can see the page but actions fail")

**Prevention:**
Handle 401 responses from FastAPI as a session invalidation signal. In the TanStack Query error handler or a global fetch wrapper, a 401 from FastAPI should trigger `signOut()`:

```typescript
// lib/api-client.ts
import { signOut } from "next-auth/react";

async function apiFetch(url: string, options?: RequestInit) {
  const res = await fetch(url, options);
  if (res.status === 401) {
    // Backend rejected the token — user may be deactivated or token expired
    await signOut({ redirect: true, callbackUrl: "/login" });
    throw new Error("Session invalidated");
  }
  return res;
}
```

Additionally, set a short NextAuth session `maxAge` (e.g., 30 minutes matching the FastAPI access token lifetime) to limit the window where a deactivated user can browse authenticated pages.

**Detection:**
- Admin deactivates a user in the database
- User is still able to view `/account`, `/cart`, `/wishlist` without being redirected
- FastAPI API calls from that user return 401 but page navigation succeeds

**Phase to address:** Auth integration phase. This is a correctness issue matching the backend's security model — not a feature, but a required behavior.

---

### Pitfall 4: NextAuth.js Token Refresh Race Condition — Single-Use Opaque Refresh Token Consumed Twice

**What goes wrong:**
The FastAPI backend uses opaque (non-JWT) refresh tokens with family-based theft detection (documented in PROJECT.md: "Opaque refresh tokens, DB revocation, family-based theft detection"). A refresh token can only be used once — on consumption, a new refresh token is issued and the old one is revoked. NextAuth.js does not serialize concurrent refresh attempts: if two browser tabs trigger the access token refresh simultaneously (e.g., both detect the access token has expired and both call the NextAuth JWT callback), both tabs attempt to exchange the same refresh token. The first request succeeds and rotates the token. The second request sends the now-revoked refresh token — FastAPI's family theft detection treats this as a stolen refresh token and revokes the entire token family. The user is forcibly logged out even though no theft occurred.

**Why it happens:**
NextAuth.js JWT callbacks run per-request, not with a singleton lock. In a tab-per-worker model (Next.js server-side rendering of multiple concurrent requests), multiple callbacks can fire before the first one completes. There is no built-in deduplication for refresh token calls.

**Consequences:**
- Users with multiple open tabs are randomly logged out when their access token expires
- The logout appears instantaneous and unexplained (no error message)
- FastAPI logs show a refresh token reuse attempt — looks like a security event, but is caused by the race condition

**Prevention:**
Implement a time-window buffer: only refresh when the access token is within N seconds of expiry, not the moment it expires. This narrows the race window. Use a server-side cache (e.g., in-memory Map or Redis if available) keyed on refresh token to deduplication refresh calls within a short window:

```typescript
// auth.ts jwt callback with buffer and exponential backoff
async jwt({ token }) {
  const BUFFER_SECONDS = 60; // refresh 60s before expiry, not at expiry
  if (Date.now() < (token.accessTokenExpiry as number) - BUFFER_SECONDS * 1000) {
    return token; // Token still fresh
  }
  // Attempt refresh
  try {
    const res = await fetch(`${process.env.API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    });
    if (!res.ok) {
      // Refresh failed — signal session expiry
      return { ...token, error: "RefreshAccessTokenError" };
    }
    const tokens = await res.json();
    return {
      ...token,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      accessTokenExpiry: Date.now() + 30 * 60 * 1000,
    };
  } catch {
    return { ...token, error: "RefreshAccessTokenError" };
  }
},
```

On the client, check for `session.error === "RefreshAccessTokenError"` and call `signOut()` to force re-login. This prevents the paradox of a "valid" session with invalid tokens.

**Detection:**
- Users with multiple browser tabs are unexpectedly logged out
- FastAPI logs show `refresh_token_reuse_detected` errors (if logging is implemented)
- Users with a single tab never experience the issue

**Phase to address:** Auth integration phase. The race condition is most dangerous in production where multiple tabs are common. Design the refresh flow defensively from the start.

---

### Pitfall 5: API Type Drift — Generated TypeScript Types Go Stale After FastAPI Schema Changes

**What goes wrong:**
`openapi-typescript` generates TypeScript types from the FastAPI OpenAPI spec at build time. After setup, the types are checked in as static files. When FastAPI Pydantic models change (new required field, renamed field, changed enum value), the TypeScript types are not regenerated. Frontend code compiles successfully because the stale types still satisfy TypeScript — but runtime behavior silently breaks. Example: FastAPI adds a `pre_booking_id` field to the order response; the frontend renders without it (no error, just a missing display field). Worse: FastAPI removes the `discount_price` field; the frontend reads `response.discount_price` which TypeScript doesn't flag because the old type still has it.

**Why it happens:**
There is no automated mechanism to enforce type regeneration after backend changes in a Python+TypeScript monorepo. Unlike a TypeScript monorepo where a change in a shared package immediately breaks dependent packages, Python type changes are invisible to the TypeScript compiler.

**Consequences:**
- Silent runtime breakage (undefined field access, missing UI elements)
- TypeScript safety is bypassed — types no longer match the actual API
- New frontend developers trust the generated types and ship bugs based on them

**Prevention:**
Make type regeneration a mandatory step in the development workflow:

```bash
# scripts/generate-types.sh — run after any FastAPI model change
#!/bin/bash
# Start FastAPI (or use a running instance) and generate types
cd backend && uvicorn app.main:app --port 8000 &
API_PID=$!
sleep 2

cd ../frontend
npx openapi-typescript http://localhost:8000/openapi.json \
  --output src/types/api.generated.ts \
  --alphabetize

kill $API_PID
```

Add this to a pre-commit hook (using `husky` or git hooks) that runs whenever `*.py` files in `app/` change. Add a CI check that regenerates types and fails if the result differs from the committed file:

```bash
# CI check: types must be current
npm run generate-types
git diff --exit-code src/types/api.generated.ts || \
  (echo "API types are stale. Run: npm run generate-types" && exit 1)
```

**Detection:**
- Frontend renders blank or partial data for a field that FastAPI returns
- A backend field was renamed or removed but frontend still references the old name without TypeScript error
- `git log --oneline` shows backend model changes without a corresponding `api.generated.ts` update

**Phase to address:** Monorepo setup phase. The type generation script and CI check must be in place before any API integration code is written — it is a workflow contract, not an afterthought.

---

### Pitfall 6: Pydantic v2 + openapi-typescript — `Optional` Fields Generated as `never` Instead of `string | null`

**What goes wrong:**
FastAPI uses Pydantic v2. Pydantic v2 represents `Optional[str]` (equivalent to `str | None`) fields in the OpenAPI schema using `anyOf: [{ type: string }, { type: null }]` instead of the older `{ type: string, nullable: true }` pattern. Some versions of `openapi-typescript` (pre-7.x) do not handle the `anyOf` + `null` pattern correctly and generate the TypeScript type as `never` instead of `string | null`. The result: frontend TypeScript type says a field is `never` (unusable), but FastAPI sends that field as a string or null at runtime. TypeScript allows accessing `.never` properties (it just types the result as `never`), so the code compiles and breaks silently.

**Why it happens:**
This is a known compatibility issue between Pydantic v2's OpenAPI schema output and older openapi-typescript versions. FastAPI's OpenAPI schema changed schema format when Pydantic v2 was adopted. The community widely reports this issue in GitHub discussions. The fix is to use `openapi-typescript` v7+ which handles `anyOf` + null correctly, or to configure FastAPI with `separate_input_output_schemas=False` to reduce schema complexity.

**Prevention:**
Use `openapi-typescript` v7 or later:

```bash
npm install -D openapi-typescript@^7
```

Also configure FastAPI to use simpler schema representation for nullable fields by avoiding `Optional` in favor of `Union`:

```python
# FastAPI/Pydantic v2 — use explicit Union with None or default=None pattern
# PROBLEMATIC — generates anyOf schema in Pydantic v2
class ReviewResponse(BaseModel):
    text: Optional[str]  # Pydantic v2 generates anyOf schema

# BETTER — explicit default makes serialization clearer
class ReviewResponse(BaseModel):
    text: str | None = None  # Clearer intent, same schema output
```

Validate the generated types include no `never` entries after running `generate-types`:

```bash
# Quick check — should return no results
grep -n ": never" src/types/api.generated.ts
```

**Detection:**
- Generated `api.generated.ts` contains `: never` for fields that should be `string | null`
- Runtime values for those fields exist (FastAPI sends them) but TypeScript types claim they are unusable
- `grep -c ": never" src/types/api.generated.ts` returns non-zero

**Phase to address:** Monorepo setup phase, specifically the openapi-typescript integration step. Verify generated types are correct before writing any API client code against them.

---

## Moderate Pitfalls

### Pitfall 7: Server/Client Component Boundary — Importing a Client Component into a Server Component Pushes Everything to the Client Bundle

**What goes wrong:**
A page-level Server Component imports a `shadcn/ui` form component for the book catalog filter. The form component uses `useState` and is marked `"use client"`. This is correct. But the developer then adds an additional `useState`-dependent component (e.g., a cart quantity selector) directly inside the same page file. Since the page now uses a hook, TypeScript errors prompt adding `"use client"` to the page. The entire catalog page — including its data fetching, which should run on the server — is now a Client Component. All book data is fetched client-side, losing SSR SEO benefits for catalog pages.

**Why it happens:**
The Next.js App Router's mental model (Server Components by default; Client Components only where interactivity is needed) requires deliberate component decomposition. Developers familiar with the React SPA model tend to add interactivity at the page level rather than isolating it to leaf components.

**Prevention:**
Apply the "push interactivity to the leaves" rule. Interactive elements must be extracted into small, focused Client Components; pages remain Server Components and import Client Components as children:

```typescript
// app/catalog/page.tsx — stays a Server Component
import { BooksGrid } from "@/components/books-grid"; // Server Component
import { CatalogFilters } from "@/components/catalog-filters"; // 'use client'

export default async function CatalogPage() {
  const books = await getBooks(); // Server-side fetch
  return (
    <>
      <CatalogFilters />       {/* Client Component — filter controls */}
      <BooksGrid books={books} />  {/* Server Component — SSR rendering */}
    </>
  );
}
```

If a Server Component must pass data to a Client Component, the data must be serializable (plain objects, not class instances or functions).

**Detection:**
- A page-level file has `"use client"` at the top
- Server-side `fetch()` calls or `async/await` patterns in a file also using `useState` or `useEffect`
- Bundle analyzer shows catalog or book detail pages have large client-side JavaScript

**Phase to address:** Catalog and search implementation phase. The component boundary decisions made for high-traffic catalog pages directly affect SEO and performance.

---

### Pitfall 8: Hydration Mismatch — `next-themes` / Dark Mode Causes Hydration Error in Next.js 15

**What goes wrong:**
`shadcn/ui` recommends `next-themes` for dark mode support. The ThemeProvider reads the user's preferred theme from `localStorage` or a cookie — this information is unavailable on the server during SSR. The server renders the page with no theme class on the `<html>` element. The client hydrates with the theme class applied. React detects the mismatch and throws a hydration error in development, and causes a flash of unstyled content (FOUC) in production. In Next.js 15, this can additionally cause hydration errors that break the entire page if `suppressHydrationWarning` is not set correctly.

**Why it happens:**
This is a structural limitation of SSR with client-specific state. `next-themes` is designed to handle it, but requires correct setup that is easy to miss (especially the `suppressHydrationWarning` prop on the `<html>` element).

**Prevention:**
Follow the exact `next-themes` setup for Next.js 15:

```typescript
// app/layout.tsx
import { ThemeProvider } from "@/components/theme-provider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>  {/* REQUIRED — not optional */}
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

```typescript
// components/theme-provider.tsx
"use client"; // ThemeProvider must be a Client Component

import { ThemeProvider as NextThemesProvider } from "next-themes";
export function ThemeProvider({ children, ...props }) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

Any component that reads the current theme (e.g., a theme toggle button) must use a `mounted` state check to avoid rendering before hydration:

```typescript
// components/theme-toggle.tsx
"use client";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();
  useEffect(() => setMounted(true), []);
  if (!mounted) return null; // Prevent hydration mismatch
  return <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>Toggle</button>;
}
```

**Detection:**
- Browser console shows React hydration errors mentioning `<html>` class attribute
- Dark mode toggle causes a flash on page load
- GitHub issue shadcn-ui/ui #5552 and #5703 describe this exact problem in Next.js 15+

**Phase to address:** UI foundation phase. Set up ThemeProvider correctly during the initial layout/design system phase before any other components are built.

---

### Pitfall 9: TanStack Query + Server Components — `HydrationBoundary` Pattern Not Used, Initial Data Fetched Twice

**What goes wrong:**
The catalog page uses a Server Component to fetch books from FastAPI. The developer also sets up TanStack Query for client-side filtering/pagination. Without the `HydrationBoundary` pattern, the server-fetched data is passed as `initialData` to `useQuery()`. TanStack Query treats `initialData` as stale immediately by default (`staleTime: 0`), causing a client-side refetch of the same data immediately after hydration. The catalog page makes two requests to FastAPI for the same data: one server-side (correct), one client-side (redundant and wasteful).

**Why it happens:**
TanStack Query's `initialData` approach does not communicate the data's staleness to the query. Without `staleTime` set explicitly, TanStack Query considers all data stale by default and refetches on mount. The `HydrationBoundary` + `dehydrate` pattern avoids this by serializing the server-fetched query cache to the client, so TanStack Query knows the data was just fetched and respects the configured `staleTime`.

**Prevention:**
Use the `HydrationBoundary` pattern for queries prefetched on the server:

```typescript
// app/catalog/page.tsx — Server Component
import { HydrationBoundary, QueryClient, dehydrate } from "@tanstack/react-query";
import { CatalogClient } from "@/components/catalog-client";

export default async function CatalogPage() {
  const queryClient = new QueryClient();
  await queryClient.prefetchQuery({
    queryKey: ["books", { page: 1 }],
    queryFn: () => fetchBooksFromFastAPI({ page: 1 }),
  });
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <CatalogClient />  {/* Client Component that uses useQuery */}
    </HydrationBoundary>
  );
}
```

```typescript
// components/catalog-client.tsx
"use client";
import { useQuery } from "@tanstack/react-query";

export function CatalogClient() {
  const { data } = useQuery({
    queryKey: ["books", { page: 1 }],
    queryFn: fetchBooks,
    staleTime: 60 * 1000,  // Data is fresh for 60s — no double-fetch
  });
  // ...
}
```

**Detection:**
- FastAPI access logs show the same `GET /books` request twice in quick succession (within ~100ms)
- Browser Network tab shows a `GET /books` immediately after page load
- `staleTime` is not set in `useQuery` calls that correspond to server-prefetched queries

**Phase to address:** Catalog and search implementation phase, specifically when setting up the TanStack Query + Server Components pattern for the first time.

---

### Pitfall 10: NEXT_PUBLIC_ Variables Expose Server-Only Config to the Client Bundle

**What goes wrong:**
A developer needs the FastAPI base URL in a client component (e.g., to make a fetch call). They name it `NEXT_PUBLIC_API_URL=http://localhost:8000` and use it in both Server Components and Client Components. This works — but later they add `NEXT_PUBLIC_DATABASE_URL` or `NEXT_PUBLIC_SECRET_KEY` using the same prefix "because it needs to be available everywhere." Variables prefixed with `NEXT_PUBLIC_` are inlined into the JavaScript bundle at build time and are visible to anyone who downloads the page.

**Why it happens:**
The `NEXT_PUBLIC_` naming convention makes variables available universally. Developers use the same variable for server-only config (private API keys, database URLs, secret keys) as for genuinely public config (CDN URLs, public analytics IDs), creating a security exposure.

**Prevention:**
Apply strict naming discipline from the start:

```bash
# frontend/.env.local — naming conventions
# Server-only (no NEXT_PUBLIC_ prefix) — NEVER exposed to browser
API_URL=http://localhost:8000           # Used in Server Components, Route Handlers
NEXTAUTH_SECRET=...                    # NextAuth.js secret — server only
GOOGLE_CLIENT_SECRET=...              # OAuth secret — server only

# Client-accessible (NEXT_PUBLIC_ prefix) — inlined into JS bundle
NEXT_PUBLIC_API_URL=http://localhost:8000   # Only if truly needed client-side
NEXT_PUBLIC_SITE_URL=http://localhost:3000  # For metadata, Open Graph
```

In Server Components and API route handlers, access `process.env.API_URL` (no prefix). This value is never sent to the browser. In Client Components, access `process.env.NEXT_PUBLIC_API_URL` only for values that are safe to expose publicly.

For the FastAPI base URL: Server Components should use the internal API URL (no prefix) and Client Components should route all API calls through Next.js Route Handlers (acting as a BFF proxy), avoiding the need to expose the backend URL to the client at all.

**Detection:**
- Check the built JS bundle: `strings .next/static/**/*.js | grep -i "localhost:8000"` — if the API URL appears in the client bundle, it has been exposed
- Any `NEXT_PUBLIC_*SECRET*` or `NEXT_PUBLIC_*KEY*` variable is a red flag

**Phase to address:** Monorepo setup phase. Establish the environment variable naming convention before any environment variables are added.

---

### Pitfall 11: Next.js 15 Async APIs — `cookies()` and `headers()` Not Awaited, Runtime Error in Middleware

**What goes wrong:**
Next.js 15 changed `cookies()`, `headers()`, and `params` from synchronous to asynchronous APIs (returning Promises). Code from Next.js 14 tutorials that calls `cookies()` synchronously (e.g., `const cookieStore = cookies(); const token = cookieStore.get("token")`) causes a runtime error in Next.js 15. The error appears at runtime, not at compile time, and may only manifest in specific code paths (e.g., in middleware or Route Handlers that read the Authorization cookie).

**Why it happens:**
Many online tutorials, blog posts, and even some official examples predate the Next.js 15 async API change. Developers copy patterns from these sources without knowing they are outdated. TypeScript types do not catch this — calling `cookies()` without `await` is syntactically valid (TypeScript sees a Promise object, not an error).

**Prevention:**
Always `await` dynamic APIs in Next.js 15:

```typescript
// WRONG — Next.js 14 pattern, breaks in Next.js 15
import { cookies } from "next/headers";
export async function GET() {
  const cookieStore = cookies();  // Returns Promise in Next.js 15 — NOT awaited!
  const token = cookieStore.get("token"); // TypeError at runtime
}

// CORRECT — Next.js 15 pattern
import { cookies } from "next/headers";
export async function GET() {
  const cookieStore = await cookies(); // Explicitly awaited
  const token = cookieStore.get("token");
}
```

Use the Next.js codemod to automatically migrate legacy patterns:

```bash
npx @next/codemod@latest next-async-request-api ./src
```

**Detection:**
- `TypeError: Cannot read properties of undefined (reading 'get')` in Route Handlers or middleware
- Code uses `cookies()` or `headers()` without `await` in an async function
- Works in Next.js 14 dev mode but breaks after upgrade to 15

**Phase to address:** Monorepo setup / auth integration phase. The NextAuth.js integration heavily uses cookies; any auth middleware that reads cookies must use the `await cookies()` pattern.

---

### Pitfall 12: Monorepo Restructure Breaks Existing Backend CI/CD — `backend/` Path Changes All References

**What goes wrong:**
The v3.0 milestone restructures the repo from a flat structure (FastAPI at root) to a monorepo (`backend/` + `frontend/`). Python paths in CI configuration, Docker Compose, Alembic config, and pytest configuration that previously referenced `app/` now need to reference `backend/app/`. This affects:
- GitHub Actions workflows that `cd app/` or run `poetry run pytest`
- `docker-compose.yml` build context and volume mounts
- `alembic.ini` `script_location` path
- Any `.env` file references

**Why it happens:**
Monorepo restructuring is treated as "just moving files" but every tool that references path-based configuration needs updating. In a Python project, this includes Poetry workspace configuration, Alembic, and any test infrastructure that assumes the project root is the Python root.

**Prevention:**
Create a restructuring checklist before moving any files:

```
Monorepo restructure checklist:
[ ] poetry.toml / pyproject.toml — update [tool.poetry] section if referencing root paths
[ ] alembic.ini — update script_location = backend/migrations
[ ] docker-compose.yml — update build context: ./backend, volumes: ./backend:/app
[ ] .github/workflows/ — update all `cd` commands and pytest invocations
[ ] pytest.ini or pyproject.toml [tool.pytest.ini_options] — update testpaths
[ ] backend/.env.example and frontend/.env.example — separate env files per workspace
[ ] GitHub Actions: verify backend tests still pass after restructure before adding frontend
```

Move files in a single commit, then update all configuration references in the same commit. Never split the file move from the config updates across commits — the repo is in a broken state between them.

**Detection:**
- CI fails immediately after restructure with `ModuleNotFoundError` or `alembic: command not found`
- `poetry run pytest` from repo root finds no tests
- Alembic cannot find migration scripts

**Phase to address:** Monorepo setup phase, the very first phase of v3.0.

---

### Pitfall 13: Google OAuth in NextAuth.js Returns a Google `access_token`, Not the FastAPI `access_token` — Backend Calls Fail

**What goes wrong:**
The project supports Google OAuth on both the backend (FastAPI `/auth/google/callback`) and the frontend (NextAuth.js Google provider). When a user signs in with Google via NextAuth.js, NextAuth.js receives a Google OAuth `access_token` (for Google APIs). This is stored in the NextAuth session. Frontend code then sends this Google token in `Authorization: Bearer ${session.accessToken}` to FastAPI. FastAPI's JWT dependency expects a token it issued — the Google OAuth token is rejected.

**Why it happens:**
Two separate OAuth flows exist: NextAuth.js handles authentication on the frontend (user → Google → Next.js), and FastAPI has its own Google OAuth exchange (Google token → FastAPI JWT). These are not automatically connected. The Google `access_token` that NextAuth.js receives cannot be used to call the FastAPI backend directly.

**Prevention:**
After Google sign-in via NextAuth.js, perform a backend token exchange: send the Google `id_token` (not `access_token`) to the FastAPI `/auth/google/callback` endpoint, which verifies it with Google and returns a FastAPI JWT. Store the FastAPI JWT (not the Google token) in the NextAuth.js session:

```typescript
// auth.ts — Google OAuth with backend token exchange
providers: [
  Google({
    clientId: process.env.GOOGLE_CLIENT_ID,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  }),
],
callbacks: {
  async jwt({ token, user, account }) {
    if (account?.provider === "google" && account.id_token) {
      // Exchange Google id_token for FastAPI access token
      const res = await fetch(`${process.env.API_URL}/auth/google/callback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: account.id_token }),
      });
      if (res.ok) {
        const data = await res.json();
        token.accessToken = data.access_token;   // FastAPI JWT — NOT Google token
        token.refreshToken = data.refresh_token; // FastAPI opaque refresh token
        token.accessTokenExpiry = Date.now() + 30 * 60 * 1000;
      }
    }
    return token;
  },
},
```

**Detection:**
- Google sign-in succeeds on the frontend (NextAuth session is created)
- API calls to FastAPI immediately return 401
- Decoding `session.accessToken` shows a Google JWT (iss: `accounts.google.com`), not a FastAPI JWT

**Phase to address:** Auth integration phase. The Google OAuth flow requires a second step (backend token exchange) that is not documented in most NextAuth.js + FastAPI tutorials.

---

## Minor Pitfalls

### Pitfall 14: TanStack Query Mutation Does Not Invalidate the Cart Query — Stale Cart Count in Header

**What goes wrong:**
A user adds a book to their cart. The `useAddToCart` mutation calls `POST /cart/items`. After success, the cart item count in the header remains at the old value because the cart query (`useCartQuery`) is not invalidated after the mutation. The user sees an inconsistent UI — the item was added (they can see it if they navigate to the cart page) but the header shows the wrong count.

**Why it happens:**
TanStack Query does not automatically invalidate related queries after a mutation. The developer must explicitly call `queryClient.invalidateQueries({ queryKey: ["cart"] })` in the mutation's `onSuccess` or `onSettled` callback. This is a documentation gap — the pattern is clear in TanStack Query docs but easy to miss when building mutations.

**Prevention:**
Always pair mutations with explicit query invalidation in `onSettled` (not `onSuccess` — `onSettled` fires whether the mutation succeeded or failed, preventing stale data after rollback):

```typescript
// hooks/use-cart.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useAddToCart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (bookId: number) => addToCartApi(bookId),
    onSettled: () => {
      // Invalidate ALL cart-related queries — header count, cart page, etc.
      queryClient.invalidateQueries({ queryKey: ["cart"] });
    },
  });
}
```

**Detection:**
- Cart item count in header does not update after adding an item without a page refresh
- Test: add item → observe header count → navigate to cart page → navigate back → observe header count is now correct (stale data cleared by navigation)

**Phase to address:** Cart and checkout phase.

---

### Pitfall 15: Server Action vs. Route Handler Confusion — Checkout Server Action Cannot Be Called by External Services

**What goes wrong:**
The developer implements the checkout flow as a Next.js Server Action (`"use server"` function). This works for the frontend. Later, the requirement to support a webhook (e.g., mock payment callback) requires calling the checkout logic from an external service. Server Actions use POST requests with a specific internal encoding that is incompatible with external HTTP callers — webhooks cannot call Server Actions.

**Why it happens:**
Server Actions are appropriate for form submissions and UI mutations triggered from the React component tree. They are not HTTP endpoints in the REST sense. Developers new to the App Router sometimes implement all mutations as Server Actions without considering external callers.

**Prevention:**
Use Server Actions only for mutations called from within the Next.js React component tree. Use Route Handlers for any endpoint that needs to be callable from external services:

```
Decision rule:
- "Will only the Next.js frontend call this?" → Server Action
- "Could a webhook, mobile app, or external service call this?" → Route Handler
```

For the bookstore checkout: the checkout initiation can be a Server Action (form submission from the cart page). Any payment callback handling must be a Route Handler (`app/api/payments/callback/route.ts`).

**Detection:**
- Mock payment system or any external service cannot reach a checkout endpoint
- Server Action URL shows as `undefined` when inspected in Network tab (they use internal encoding)

**Phase to address:** Cart and checkout phase.

---

### Pitfall 16: Environment Variable Misconfiguration in Monorepo — Frontend Uses Backend's `.env`, or Variables Are Missing in CI

**What goes wrong:**
After monorepo restructure, the repo has `backend/.env` and `frontend/.env.local`. CI scripts that previously loaded `.env` from the root now find nothing — Next.js builds fail with `NEXTAUTH_SECRET` undefined. Locally, developers run the backend from `backend/` so they load `backend/.env`, but they run Next.js from `frontend/` which should load `frontend/.env.local`. The separation of environment files is correct but the CI configuration is not updated.

**Why it happens:**
Monorepo environment file management requires explicit per-workspace configuration. CI providers that previously read a single root `.env` need to be reconfigured for per-workspace env files. This is a configuration problem, not a code problem, but it blocks the entire CI pipeline.

**Prevention:**
- `backend/.env` — FastAPI env vars (DB URL, JWT secrets, SMTP creds)
- `frontend/.env.local` — Next.js env vars (`NEXTAUTH_SECRET`, `GOOGLE_CLIENT_ID`, `NEXTAUTH_URL`, `API_URL`)
- CI: Set environment variables explicitly as CI secrets, not by loading `.env` files
- Never share the backend's `.env` with the frontend — they have different variable sets and different exposure rules (FastAPI secrets are never `NEXT_PUBLIC_`)

```bash
# .github/workflows/frontend.yml — explicit env in CI
env:
  NEXTAUTH_SECRET: ${{ secrets.NEXTAUTH_SECRET }}
  NEXTAUTH_URL: ${{ vars.NEXTAUTH_URL }}
  GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
  GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
  API_URL: ${{ vars.API_URL }}
```

**Detection:**
- `Error: NEXTAUTH_SECRET is not set` in CI build logs
- Frontend works locally but fails in CI/CD
- Both backend and frontend read from the same `.env` file

**Phase to address:** Monorepo setup phase, alongside CI/CD configuration.

---

## Technical Debt Patterns

Shortcuts that seem reasonable during early phases but create long-term maintenance problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding `http://localhost:8000` as the API URL in fetch calls | No env setup needed in dev | Breaks in staging/production; must find and replace every occurrence | Never — use `process.env.API_URL` from day one |
| Storing the FastAPI JWT in `localStorage` instead of the NextAuth session cookie | Simpler code, no NextAuth setup | XSS-vulnerable; token accessible by any script on the page; bypasses NextAuth session management | Never — use NextAuth session (encrypted `httpOnly` cookie) |
| Skipping `generateStaticParams` for book detail pages | No SSG setup work | Every book detail page is SSR on every request; no CDN caching; catalog pages are the highest-traffic pages | Acceptable in early phases; revisit before launch for SEO and performance |
| `"use client"` on page-level components to avoid "can't use hooks in Server Component" error | Fast fix for hook-related errors | Entire page (including data fetching) moves to client side; loses SSR SEO benefits | Acceptable for admin-only pages; never for public catalog or book detail pages |
| Not setting `staleTime` in TanStack Query | Fewer configuration decisions | Every `useQuery` call refetches on component mount; catalog pages make 2-3 redundant API calls per navigation | Never — set `staleTime: 60 * 1000` as a default at the QueryClient level |
| Checking in `api.generated.ts` without a regeneration script | Types available in CI without running FastAPI | Types drift from backend without any warning; TypeScript safety is false | Never — always maintain a `generate-types` script and CI check |
| Using the Google `access_token` from NextAuth directly as the FastAPI bearer token | Simpler auth flow | FastAPI JWT verification rejects Google tokens; auth silently fails | Never — always exchange Google token for FastAPI token via backend endpoint |

---

## Integration Gotchas

Mistakes specific to connecting these components together.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FastAPI CORS | `allow_origins=["*"]` + `allow_credentials=True` | `allow_origins=["http://localhost:3000", "https://example.com"]` — explicit list, from env var |
| NextAuth.js + FastAPI JWT | `session.accessToken` is undefined | Map `accessToken` in both `jwt` callback and `session` callback |
| NextAuth.js + Google OAuth | Sending Google `access_token` to FastAPI | Exchange Google `id_token` for FastAPI JWT via `/auth/google/callback` endpoint |
| TanStack Query + Server Components | `initialData` causes double fetch | Use `prefetchQuery()` + `HydrationBoundary` + `dehydrate()` pattern |
| openapi-typescript + Pydantic v2 | Optional fields generate as `never` | Use `openapi-typescript` v7+; validate generated types with `grep ": never"` |
| FastAPI token refresh + NextAuth.js | Race condition revokes token family | Add 60s buffer before expiry; handle `RefreshAccessTokenError` in session callback |
| `is_active` lockout | NextAuth session valid; FastAPI API calls fail | Handle 401 from FastAPI by calling `signOut()` — clear the stale session |
| Environment variables | Same `.env` for frontend and backend | Separate `backend/.env` and `frontend/.env.local`; CI uses secrets, not file loading |
| Monorepo restructure | CI paths break after move to `backend/` | Update all path references in same commit as the file move |
| Next.js 15 dynamic APIs | `cookies()` called without `await` | Always `await cookies()`, `await headers()` in Next.js 15 |
| shadcn/ui dark mode | Hydration error from `next-themes` | `suppressHydrationWarning` on `<html>`; `mounted` state check in theme toggle |
| TanStack Query mutations | Cart count stale after add-to-cart | `invalidateQueries({ queryKey: ["cart"] })` in `onSettled` of every cart mutation |
| Server Actions vs Route Handlers | Checkout logic in Server Action; webhook cannot reach it | Server Actions for frontend-only mutations; Route Handlers for external-facing endpoints |

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Monorepo restructure | Backend CI breaks due to path changes | Single commit for file move + config updates; verify backend CI passes before adding frontend CI |
| Monorepo restructure | `backend/.env` and `frontend/.env.local` confused | Establish separate env files and naming conventions immediately |
| Auth integration (Credentials) | `session.accessToken` undefined | Implement `jwt` and `session` callbacks with explicit token mapping in Pitfall 2 |
| Auth integration (Google OAuth) | Google token sent to FastAPI instead of FastAPI JWT | Implement backend token exchange in `jwt` callback (Pitfall 13) |
| Auth integration (refresh flow) | Race condition invalidates refresh token family | Add 60s expiry buffer; implement `RefreshAccessTokenError` handling (Pitfall 4) |
| Auth integration (deactivation) | Deactivated users see authenticated UI | Handle 401 from FastAPI as session invalidation signal (Pitfall 3) |
| Type generation setup | `api.generated.ts` not regenerated after backend change | Add `generate-types` script, pre-commit hook, CI check in setup phase (Pitfall 5) |
| Type generation setup | Pydantic v2 Optional fields generate as `never` | Use `openapi-typescript` v7+; validate output (Pitfall 6) |
| Catalog implementation | Page-level `"use client"` moves data fetching to client | Extract interactive elements to leaf Client Components (Pitfall 7) |
| Catalog implementation | TanStack Query double-fetches server-prefetched data | Use `HydrationBoundary` + `prefetchQuery` pattern (Pitfall 9) |
| UI foundation | Hydration error from dark mode setup | `suppressHydrationWarning` + `mounted` guard (Pitfall 8) |
| Cart/checkout | Cart count stale after mutation | `invalidateQueries` in `onSettled` (Pitfall 14) |
| Cart/checkout | Checkout logic inaccessible to webhooks | Checkout in Server Action; payment callbacks in Route Handler (Pitfall 15) |
| Environment config | Secrets exposed via `NEXT_PUBLIC_` prefix | Strict naming convention: secrets never get `NEXT_PUBLIC_` prefix (Pitfall 10) |

---

## "Looks Done But Isn't" Checklist

- [ ] **CORS:** FastAPI `allow_origins` is an explicit list — not `["*"]` — when `allow_credentials=True` is set; test with browser Network tab, not just curl/Postman
- [ ] **NextAuth session carries FastAPI token:** `console.log(session)` shows `session.accessToken` is a string (not `undefined`) after sign-in
- [ ] **Google OAuth exchanges token:** After Google sign-in, `session.accessToken` decodes to a FastAPI JWT (iss matches FastAPI), not a Google JWT (iss: accounts.google.com)
- [ ] **Token refresh handles error:** `session.error === "RefreshAccessTokenError"` triggers `signOut()` on the client — test by manually expiring the access token
- [ ] **Deactivated user lockout:** After admin deactivates a user in the DB, the next API call from that user triggers `signOut()` — not just a UI error
- [ ] **Generated types are current:** `npm run generate-types && git diff --exit-code src/types/api.generated.ts` exits 0 (no changes)
- [ ] **No `never` types in generated file:** `grep -c ": never" src/types/api.generated.ts` returns 0
- [ ] **Catalog page is a Server Component:** `grep -l '"use client"' app/catalog/page.tsx` returns nothing (no `"use client"` in the catalog page itself)
- [ ] **No double fetch on catalog:** FastAPI access logs show exactly 1 request per page load for the catalog endpoint (not 2)
- [ ] **Dark mode no hydration error:** Browser console is clean on first load; no React hydration warnings
- [ ] **Cart mutation invalidates query:** After add-to-cart, cart count in header updates without page refresh
- [ ] **No `NEXT_PUBLIC_` on secrets:** `grep -r "NEXT_PUBLIC_.*SECRET\|NEXT_PUBLIC_.*KEY\|NEXT_PUBLIC_.*PASSWORD" frontend/.env*` returns nothing
- [ ] **`await cookies()`:** `grep -r "cookies()" frontend/app --include="*.ts" --include="*.tsx" | grep -v "await cookies()"` returns nothing
- [ ] **Backend CI still passes:** Run the full backend test suite (`poetry run pytest`) after monorepo restructure — all 306 tests pass

---

## Sources

### HIGH Confidence (Official Documentation or Verified Community Reports)

- [FastAPI CORS Tutorial](https://fastapi.tiangolo.com/tutorial/cors/) — wildcard + credentials incompatibility documented officially
- [NextAuth.js Callbacks Documentation](https://next-auth.js.org/configuration/callbacks) — `jwt` and `session` callback required to expose `accessToken`
- [Auth.js Refresh Token Rotation Guide](https://authjs.dev/guides/refresh-token-rotation) — official pattern for refresh token rotation with external backends
- [Various issues with refresh token rotation (NextAuth GitHub #3940)](https://github.com/nextauthjs/next-auth/discussions/3940) — race condition with single-use refresh tokens is a known issue
- [Next.js Dynamic APIs are Asynchronous](https://nextjs.org/docs/messages/sync-dynamic-apis) — `cookies()` and `headers()` must be awaited in Next.js 15
- [NextAuth.js v5 — Using FastAPI discussion (GitHub #8064)](https://github.com/nextauthjs/next-auth/discussions/8064) — community-verified FastAPI + NextAuth.js integration pattern
- [Next Auth google OAuth with custom backend access token (GitHub #8884)](https://github.com/nextauthjs/next-auth/discussions/8884) — Google token exchange pattern
- [TanStack Query Advanced Server Rendering](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr) — `HydrationBoundary` + `prefetchQuery` official pattern
- [Pydantic v2 OpenAPI changes (FastAPI GitHub #9900)](https://github.com/fastapi/fastapi/discussions/9900) — `anyOf` + null schema output confirmed
- [shadcn/ui Next.js 15 dark mode issue #5552](https://github.com/shadcn-ui/ui/issues/5552) — ThemeProvider hydration error in Next.js 15 confirmed
- [Next.js Common App Router Mistakes (Vercel blog)](https://vercel.com/blog/common-mistakes-with-the-next-js-app-router-and-how-to-fix-them) — server/client boundary mistakes, `"use client"` overuse
- [Turborepo Environment Variables Guide](https://turborepo.dev/docs/crafting-your-repository/using-environment-variables) — monorepo env variable management best practices
- [Handling Common CORS Errors in Next.js 15 (Wisp CMS)](https://www.wisp.blog/blog/handling-common-cors-errors-in-nextjs-15) — preflight and credentials interaction confirmed

### MEDIUM Confidence (Community-Verified, Multiple Sources Agree)

- [Next.js Authentication - JWT Refresh Token Rotation with NextAuth.js (DEV)](https://dev.to/mabaranowski/nextjs-authentication-jwt-refresh-token-rotation-with-nextauthjs-5696) — refresh token race condition prevention
- [Managing type safety challenges using the FastAPI + Next.js template (Vinta Software)](https://www.vintasoftware.com/blog/type-safety-fastapi-nextjs-architecture) — type drift prevention workflow
- [Achieving Full-Stack Type Safety with FastAPI, Next.js, and OpenAPI Spec](https://abhayramesh.com/blog/type-safe-fullstack) — openapi-typescript integration with FastAPI
- [Generating API clients in monorepos with FastAPI and Next.js (Vinta Software)](https://www.vintasoftware.com/blog/nextjs-fastapi-monorepo) — monorepo port conflict and shared type generation workflow
- [Fixing Hydration Mismatch in Next.js (next-themes Issue)](https://medium.com/@pavan1419/fixing-hydration-mismatch-in-next-js-next-themes-issue-8017c43dfef9) — `mounted` state workaround confirmed
- [Solving CORS Issues Between Next.js and Python Backend (Nov 2025)](https://medium.com/@nmlmadhusanka/solving-cors-issues-between-next-js-and-python-backend-93800a4ee633) — real-world CORS configuration examples

### Codebase-Specific (Direct Inspection — HIGH Confidence)

- `PROJECT.md` — "Opaque refresh tokens (not JWT)" and "DB is_active check per request" decisions directly referenced in Pitfalls 3 and 4
- `PROJECT.md` — "JWT tokens (access + refresh)" and "NextAuth.js on frontend" confirm the token threading architecture required by Pitfall 2
- `PROJECT.md` — "Google OAuth" on backend confirmed active; frontend Google OAuth requires backend token exchange (Pitfall 13)

---

*Pitfalls research for: BookStore v3.0 — Next.js 15 Customer Storefront added to FastAPI backend*
*Researched: 2026-02-27*
