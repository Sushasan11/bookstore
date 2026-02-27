---
phase: 20-auth-integration
plan: 02
subsystem: auth
tags: [nextauth, next-auth-v5, login, register, google-oauth, route-protection, proxy-ts, tanstack-query, shadcn-ui, 403-interceptor]

requires:
  - phase: 20-auth-integration (plan 01)
    provides: NextAuth.js v5 auth.ts with handlers/auth/signIn/signOut; SessionProvider in providers.tsx

provides:
  - /login page with email/password LoginForm + Google sign-in button + link to /register
  - /register page with RegisterForm (POST /auth/register + auto signIn) + Google sign-in button
  - (auth) route group layout — centered card, no site Header/Footer
  - LoginForm: credentials signIn with callbackUrl redirect, error banner, show/hide password
  - RegisterForm: POST /auth/register, client-side confirm password validation, auto signIn after success
  - GoogleSignInButton: outline button with Google SVG calling signIn('google', { callbackUrl })
  - proxy.ts: Next.js 16 route protection — named proxy export redirecting unauthenticated users to /login?callbackUrl=
  - UserMenu: client component with useSession() + mounted guard — Sign In link or email + Sign Out button
  - Updated Header: UserMenu between cart button and ThemeToggle
  - 403 interceptor in QueryCache/MutationCache: auto signOut on ApiError status 403 (AUTH-08)
  - AuthGuard: watches session.error for RefreshTokenError and calls signOut

affects:
  - 20-03-route-protection (if exists — proxy.ts already handles route protection)
  - Phase 21+ (all pages see auth state in Header; UserMenu shows logged-in user)

tech-stack:
  added:
    - shadcn/ui Input — form input component
    - shadcn/ui Card (CardHeader, CardTitle, CardDescription, CardContent, CardFooter) — auth page layout
    - shadcn/ui Label — form label component
  patterns:
    - (auth) route group overrides root layout for auth-only pages (no Header/Footer)
    - useSearchParams() components wrapped in Suspense boundary (required by Next.js for static builds)
    - UserMenu mounted guard (useEffect + useState) to prevent SSR/CSR hydration mismatch
    - QueryCache/MutationCache onError global 403 intercept pattern (TanStack Query v5)
    - AuthGuard component watches session.error client-side to trigger signOut for server-side errors

key-files:
  created:
    - frontend/src/app/(auth)/layout.tsx — centered card layout for auth route group (no site chrome)
    - frontend/src/app/(auth)/login/page.tsx — login page with LoginForm + GoogleSignInButton + Suspense
    - frontend/src/app/(auth)/register/page.tsx — register page with RegisterForm + GoogleSignInButton
    - frontend/src/components/auth/LoginForm.tsx — credentials signIn form with callbackUrl + show/hide password
    - frontend/src/components/auth/RegisterForm.tsx — registration form with confirm password and POST /auth/register
    - frontend/src/components/auth/GoogleSignInButton.tsx — Google OAuth button with G logo SVG
    - frontend/src/components/layout/UserMenu.tsx — auth-aware header item (Sign In / user email + Sign Out)
    - frontend/src/proxy.ts — Next.js 16 route protection middleware (named proxy export)
    - frontend/src/components/ui/input.tsx — shadcn Input component (installed via npx shadcn@latest add)
    - frontend/src/components/ui/card.tsx — shadcn Card component family
    - frontend/src/components/ui/label.tsx — shadcn Label component
  modified:
    - frontend/src/components/layout/Header.tsx — added UserMenu import and rendering
    - frontend/src/components/providers.tsx — added QueryCache/MutationCache 403 interceptor and AuthGuard

key-decisions:
  - "Suspense boundary wraps LoginForm in login/page.tsx: useSearchParams() requires Suspense in Next.js static builds — caught during npm run build (Rule 1 auto-fix)"
  - "UserMenu uses mounted guard (useEffect + useState): prevents SSR/CSR mismatch since useSession returns loading state server-side — same pattern as ThemeToggle"
  - "AuthGuard is a separate child component inside SessionProvider: allows useSession() to be called without requiring providers.tsx itself to be refactored"
  - "proxy.ts uses named export const proxy = auth(...) (not export default): Next.js 16 requires the named proxy export per RESEARCH.md Pitfall 7"
  - "RegisterForm directly calls POST /auth/register then signIn('credentials'): registration is not a NextAuth flow — NextAuth Credentials authorize is login-only"

patterns-established:
  - "(auth) route group pattern: wrap auth-only pages in a route group to override layout without affecting URL structure"
  - "Suspense boundary for useSearchParams(): any client component using useSearchParams must be wrapped in Suspense at the page level"
  - "403 global auto-signout: QueryCache.onError + MutationCache.onError intercept ApiError status 403 and call signOut — standard AUTH-08 pattern"
  - "session.error surface pattern: jwt callback sets token.error, session callback surfaces to client, AuthGuard useEffect watches and calls signOut()"

requirements-completed: [AUTH-05, AUTH-06, AUTH-08]

duration: ~5min
completed: 2026-02-27
---

# Phase 20 Plan 02: Auth UI Summary

**Login/register pages with shadcn forms, proxy.ts route protection for Next.js 16, Header auth state via UserMenu, and global 403 interceptor for deactivated users**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-27T12:16:59Z
- **Completed:** 2026-02-27T12:21:16Z
- **Tasks:** 2
- **Files modified:** 13 (9 created + 2 new + 2 modified existing)

## Accomplishments

- Complete auth UX: /login and /register pages with email/password forms and Google sign-in button — users can now sign in, register, and sign out with full feedback
- Route protection via proxy.ts (Next.js 16 pattern): unauthenticated users redirected from /account, /orders, /checkout, /wishlist, /prebook to /login?callbackUrl=...
- Header shows auth state: UserMenu displays "Sign In" link when logged out, user email + "Sign Out" button when logged in — updates without page reload via useSession()
- 403 global interceptor + RefreshTokenError handler: deactivated users and expired refresh tokens trigger automatic sign-out — no per-query error handling needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auth UI pages with login, register forms, and Google sign-in button** - `73daa43` (feat)
2. **Task 2: Add proxy.ts route protection, Header auth state, logout, and 403 interceptor** - `d64a918` (feat)

**Plan metadata:** (final docs commit below)

## Files Created/Modified

- `frontend/src/app/(auth)/layout.tsx` — centered card layout for auth pages, skips site Header/Footer
- `frontend/src/app/(auth)/login/page.tsx` — /login page: Card header + LoginForm (in Suspense) + divider + GoogleSignInButton + link to /register
- `frontend/src/app/(auth)/register/page.tsx` — /register page: Card header + RegisterForm + divider + GoogleSignInButton + link to /login
- `frontend/src/components/auth/LoginForm.tsx` — 'use client' form: email/password with show/hide toggle, error banner, callbackUrl redirect via signIn('credentials')
- `frontend/src/components/auth/RegisterForm.tsx` — 'use client' form: email/password/confirm with client-side validation, POST /auth/register, auto signIn on success
- `frontend/src/components/auth/GoogleSignInButton.tsx` — 'use client' button: outline variant with Google G logo SVG, calls signIn('google', { callbackUrl })
- `frontend/src/components/layout/UserMenu.tsx` — 'use client' with mounted guard: uses useSession() to show Sign In link or email + Sign Out button
- `frontend/src/proxy.ts` — Next.js 16 proxy: named export const proxy = auth(...), protects 5 route prefixes, redirects authenticated users off auth pages
- `frontend/src/components/ui/input.tsx` — shadcn Input (installed via npx shadcn@latest add)
- `frontend/src/components/ui/card.tsx` — shadcn Card family (Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, CardAction)
- `frontend/src/components/ui/label.tsx` — shadcn Label
- `frontend/src/components/layout/Header.tsx` — added `<UserMenu />` between cart button and ThemeToggle
- `frontend/src/components/providers.tsx` — added QueryCache/MutationCache with 403 interceptors and AuthGuard component

## Decisions Made

- **Suspense boundary for LoginForm:** `useSearchParams()` in LoginForm requires a Suspense boundary when the page is statically pre-rendered. Discovered during `npm run build` — added `<Suspense>` wrapper in login/page.tsx. Standard Next.js requirement.
- **UserMenu as separate client component (not inline in Header):** Header stays as a server component for better performance. UserMenu is the only part that needs client-side session state — extracted to minimize client boundary.
- **AuthGuard as inner child component:** Placing AuthGuard inside SessionProvider (as a child component that calls useSession()) is cleaner than adding session-watching logic directly in Providers — avoids React Rules of Hooks violations.
- **proxy.ts named export:** Used `export const proxy = auth(...)` pattern (inline callback) per RESEARCH.md Pitfall 7 — named `proxy` export required by Next.js 16.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added Suspense boundary around LoginForm for useSearchParams()**
- **Found during:** Task 2 (running npm run build to verify)
- **Issue:** `useSearchParams()` called in LoginForm causes build error: "useSearchParams() should be wrapped in a suspense boundary at page /login". Next.js requires components using useSearchParams() to be wrapped in Suspense during static generation.
- **Fix:** Wrapped `<LoginForm />` in `<Suspense fallback={...}>` in `frontend/src/app/(auth)/login/page.tsx`. Added `CardContent` import to show skeleton fallback.
- **Files modified:** `frontend/src/app/(auth)/login/page.tsx`
- **Verification:** `npm run build` succeeds — /login and /register both prerendered as static (○)
- **Committed in:** d64a918 (Task 2 commit, login/page.tsx updated)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug causing build failure)
**Impact on plan:** Required Next.js behavior — useSearchParams() always needs Suspense in static builds. No scope creep.

## Issues Encountered

None beyond the auto-fixed Suspense boundary issue above.

## User Setup Required

None beyond what was documented in 20-01-SUMMARY.md (AUTH_SECRET, Google OAuth credentials). The auth UI works without Google credentials — email/password login and registration function immediately.

## Next Phase Readiness

- Auth UX complete: users can sign in (email/password or Google), register, and sign out
- Route protection active: proxy.ts guards all private route prefixes
- Header auth state: UserMenu ready — shows correct state after sign-in/sign-out without page reload
- 403 interceptor active: deactivated users auto-signed-out on next API call
- RefreshTokenError handler active: expired sessions trigger automatic sign-out
- Plan 20-03 (if any): session.accessToken available via useSession() for API Bearer header injection

## Self-Check: PASSED

All files present and commits verified:
- frontend/src/app/(auth)/layout.tsx: FOUND
- frontend/src/app/(auth)/login/page.tsx: FOUND
- frontend/src/app/(auth)/register/page.tsx: FOUND
- frontend/src/components/auth/LoginForm.tsx: FOUND
- frontend/src/components/auth/RegisterForm.tsx: FOUND
- frontend/src/components/auth/GoogleSignInButton.tsx: FOUND
- frontend/src/components/layout/UserMenu.tsx: FOUND
- frontend/src/proxy.ts: FOUND
- .planning/phases/20-auth-integration/20-02-SUMMARY.md: FOUND
- Commit 73daa43: FOUND
- Commit d64a918: FOUND

---
*Phase: 20-auth-integration*
*Completed: 2026-02-27*
