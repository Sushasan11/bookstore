---
phase: 19-monorepo-frontend-foundation
plan: "03"
subsystem: ui
tags: [nextjs, react, tailwind, shadcn-ui, next-themes, lucide-react, tanstack-query]

# Dependency graph
requires:
  - phase: 19-02
    provides: "apiFetch wrapper, TanStack Query providers, shadcn/ui Sheet and Button components, Providers component"
provides:
  - "Responsive sticky header with logo, desktop nav links, cart icon, and theme toggle"
  - "Mobile hamburger menu with Sheet-based slide-out navigation drawer"
  - "Minimal footer with copyright text and page links"
  - "Dark/light mode toggle (next-themes) with hydration guard and system-preference detection"
  - "Root layout wiring Header + Footer around all pages with flex-column structure"
  - "Health check home page that calls /health via TanStack Query + apiFetch — proves CORS + fetch + query pipeline end-to-end"
  - "Themed 404 not-found page (dark mode applies to missing routes)"
affects:
  - phase-20-auth-integration
  - phase-21-catalog-search
  - phase-22-cart-checkout
  - all-storefront-pages

# Tech tracking
tech-stack:
  added:
    - next-themes (dark/light mode with system preference detection and localStorage persistence)
  patterns:
    - Hydration guard pattern — ThemeToggle returns null before mount to prevent SSR/CSR mismatch
    - Controlled Sheet pattern — MobileNav uses useState(open) to close drawer on link click
    - Sticky header via sticky top-0 z-50 with bg-background/95 backdrop-blur
    - Flex column layout in root layout (relative flex min-h-screen flex-col) for sticky footer
    - Health check query as integration smoke test pattern

key-files:
  created:
    - frontend/src/components/layout/Header.tsx
    - frontend/src/components/layout/MobileNav.tsx
    - frontend/src/components/layout/Footer.tsx
    - frontend/src/components/layout/ThemeToggle.tsx
    - frontend/src/app/not-found.tsx
  modified:
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx

key-decisions:
  - "ThemeToggle uses useEffect/useState mounted guard to return null before hydration — prevents SSR/CSR theme flicker"
  - "MobileNav Sheet open state controlled by component (not just trigger) — enables programmatic close on link click"
  - "Header is a server component that composes client sub-components (ThemeToggle, MobileNav) — avoids unnecessary client boundary at root"
  - "not-found.tsx themed with same dark-mode tokens as the rest of the app — consistent user experience on 404s"

patterns-established:
  - "Hydration guard: 'use client' components using next-themes must guard with useState(false)/useEffect(() => setMounted(true)) and return null before mount"
  - "Layout shell: root layout wraps <Header /><main className=flex-1>{children}</main><Footer /> inside relative flex min-h-screen flex-col div"
  - "Mobile-first nav: nav links hidden with hidden md:flex on desktop; hamburger MobileNav visible with md:hidden on mobile only"

requirements-completed: [FOUND-06]

# Metrics
duration: 25min
completed: 2026-02-27
---

# Phase 19 Plan 03: Responsive Layout Shell and Health Check Smoke Test Summary

**Sticky responsive header with mobile hamburger Sheet drawer, dark mode toggle with hydration guard, and a health check home page that proves CORS + apiFetch + TanStack Query end-to-end**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-27
- **Completed:** 2026-02-27
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 7

## Accomplishments
- Four layout components created: sticky Header with responsive nav, Sheet-based MobileNav, minimal Footer, next-themes ThemeToggle with hydration guard
- Root layout wired with Header + Footer surrounding all pages in a flex column structure
- Home page smoke test fetches `/health` via TanStack Query and renders "Connected — v1.0.0" when backend is up
- User verified responsive layout, dark mode toggle, mobile hamburger drawer, and no CORS errors in browser console

## Task Commits

Each task was committed atomically:

1. **Task 1: Create layout components (Header, MobileNav, Footer, ThemeToggle)** - `2918b89` (feat)
2. **Task 2: Wire layout shell into root layout and create health check home page** - `c2c80a5` (feat)
3. **Task 3: Verify responsive layout and backend connectivity** - checkpoint (human-verify, approved by user)

**Deviation fix:** `694928e` — fix(19-03): add themed 404 page so dark mode applies to missing routes

## Files Created/Modified
- `frontend/src/components/layout/Header.tsx` — Sticky top navbar with logo, hidden-md desktop nav, cart icon, ThemeToggle; composes MobileNav
- `frontend/src/components/layout/MobileNav.tsx` — 'use client' Sheet-based slide-out drawer; hamburger trigger visible only on mobile (md:hidden); closes on link click
- `frontend/src/components/layout/Footer.tsx` — Minimal footer with copyright and Browse Books / Cart links; muted-foreground text
- `frontend/src/components/layout/ThemeToggle.tsx` — 'use client' sun/moon toggle using next-themes useTheme(); mounted guard prevents hydration mismatch
- `frontend/src/app/not-found.tsx` — Themed 404 page that inherits dark mode tokens (deviation fix)
- `frontend/src/app/layout.tsx` — Updated root layout with Header, Footer, flex column structure, and metadata template
- `frontend/src/app/page.tsx` — Health check home page calling /health via useQuery + apiFetch; displays backend status

## Decisions Made
- ThemeToggle returns null before hydration mount to prevent theme flicker on initial render — required pattern for next-themes in Next.js App Router
- MobileNav controls Sheet open state internally to enable closing the drawer when the user taps a nav link (otherwise the drawer stays open)
- Header declared as server component composing client sub-components — keeps client bundle minimal
- 404 page explicitly themed (not left as default Next.js styling) so dark mode does not break on missing routes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added themed 404 page**
- **Found during:** Task 2 (reviewing root layout and app shell completeness)
- **Issue:** The default Next.js 404 page does not use the `Providers` context (ThemeProvider, etc.), so navigating to a missing route showed an unstyled page ignoring the dark mode setting
- **Fix:** Created `frontend/src/app/not-found.tsx` with the same shadcn/ui token-based styling as the rest of the app
- **Files modified:** `frontend/src/app/not-found.tsx`
- **Verification:** Page renders with correct dark/light tokens at any missing route
- **Committed in:** `694928e`

---

**Total deviations:** 1 auto-fixed (missing critical — themed 404)
**Impact on plan:** Necessary for a consistent user experience. No scope creep.

## Issues Encountered
None beyond the auto-fixed 404 deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Layout shell is complete and ready for all subsequent storefront pages to render inside it
- Dark mode, Header, Footer, and MobileNav will be inherited by every page added in phases 20-25
- Health check home page will be replaced by the actual catalog page in Phase 21
- Phase 20 (Auth Integration) can begin: NextAuth.js login/register pages will slot into the existing layout

---
*Phase: 19-monorepo-frontend-foundation*
*Completed: 2026-02-27*
