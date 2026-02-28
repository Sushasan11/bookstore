---
phase: 24-wishlist-and-pre-booking
plan: "02"
subsystem: ui
tags: [react, next-js, tanstack-query, wishlist, pre-booking, navigation, server-components]

# Dependency graph
requires:
  - phase: 24-01
    provides: useWishlist hook (WISHLIST_KEY, handleToggle), usePrebook hook (PREBOOK_KEY, cancelPrebook, fetchPrebooks)
  - phase: 23-orders-and-account
    provides: /orders page pattern (server component + auth guard + try/catch fetch + client list component)
provides:
  - /wishlist page: server-rendered with WishlistList client component, loading skeleton, auth guard
  - WishlistList: SSR fallback + TanStack Query cache takeover, remove via handleToggle
  - PrebookingsList: optimistic cancel with local state, status badges, cancel-only-for-waiting
  - /account page: Wishlist card + inline pre-bookings section
  - Wishlist link in Header (desktop) and MobileNav (mobile)
affects: [navigation, account-hub, wishlist-ux, pre-booking-ux]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server-fetch + client-list pattern: server component fetches data with accessToken, passes as props to 'use client' list component which uses TanStack Query cache as source of truth"
    - "Optimistic local state for cancel: useState(prebooks) + onMutate filter + onError restore — no query key needed since list is server-seeded"
    - "SSR fallback with cache takeover: wishlistQuery.data?.items ?? items (server props) — client-side TanStack Query wins once mounted"

key-files:
  created:
    - frontend/src/app/wishlist/page.tsx
    - frontend/src/app/wishlist/_components/WishlistList.tsx
    - frontend/src/app/wishlist/loading.tsx
    - frontend/src/app/account/_components/PrebookingsList.tsx
  modified:
    - frontend/src/app/account/page.tsx
    - frontend/src/components/layout/Header.tsx
    - frontend/src/components/layout/MobileNav.tsx

key-decisions:
  - "WishlistList uses wishlistQuery.data?.items ?? items pattern — SSR-fetched items render immediately, TanStack Query cache takes over after hydration without flash"
  - "PrebookingsList uses useState(prebooks) for optimistic removal — server-seeded list is one-shot; no query invalidation needed for visual correctness"
  - "Pre-bookings rendered inline on /account page (not separate /prebooks route) — bounded list, lower complexity, account hub is the natural home"
  - "Cancel button only appears for status === 'waiting' — notified pre-bookings cannot be cancelled once book is back in stock"

requirements-completed: [WISH-03, PREB-03, PREB-04]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 24 Plan 02: Wishlist Page, Pre-bookings Management, and Navigation Summary

**Wishlist page with SSR + TanStack Query cache takeover, inline pre-bookings section on account page with optimistic cancel, and Wishlist link added to Header and MobileNav**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-27T20:39:51Z
- **Completed:** 2026-02-27T20:41:58Z
- **Tasks:** 2
- **Files modified:** 7 (created 4, modified 3)

## Accomplishments

- Created `/wishlist` page: server component fetches wishlist with auth guard, passes items to `WishlistList` client component
- Created `WishlistList`: SSR items as fallback, TanStack Query cache takes over after hydration, list layout with cover thumbnail, title, author, price, stock badge (green/red), remove button using `handleToggle`
- Created empty state for wishlist with link to `/catalog`
- Created `loading.tsx` skeleton with 3 placeholder rows matching wishlist layout
- Created `PrebookingsList` client component: optimistic cancel removes item from local state immediately, restores on error, cancel button only for `waiting` status, yellow/blue badges for waiting/notified
- Updated `/account` page: added Wishlist card link (matching Order History card pattern), fetches pre-bookings server-side (filtered to non-cancelled), renders `PrebookingsList` inline below cards
- Added Wishlist link to `Header` desktop nav between Books and Account
- Added Wishlist entry to `MobileNav` `navLinks` array after Cart

## Task Commits

Each task was committed atomically:

1. **Task 1: Create /wishlist page with WishlistList component and loading skeleton** - `8c5162d` (feat)
2. **Task 2: Add pre-bookings to account page and Wishlist to navigation** - `22740ee` (feat)

## Files Created/Modified

- `frontend/src/app/wishlist/page.tsx` - Server component, auth guard, fetchWishlist with try/catch, renders WishlistList
- `frontend/src/app/wishlist/_components/WishlistList.tsx` - Client component, SSR fallback + cache takeover, list layout with remove
- `frontend/src/app/wishlist/loading.tsx` - Loading skeleton, 3 placeholder rows
- `frontend/src/app/account/_components/PrebookingsList.tsx` - Client component, optimistic cancel, status badges, cancel-for-waiting only
- `frontend/src/app/account/page.tsx` - Added Heart import, fetchPrebooks server-side, Wishlist card, PrebookingsList section
- `frontend/src/components/layout/Header.tsx` - Added Wishlist link between Books and Account in desktop nav
- `frontend/src/components/layout/MobileNav.tsx` - Added `{ href: '/wishlist', label: 'Wishlist' }` to navLinks

## Decisions Made

- `WishlistList` uses `wishlistQuery.data?.items ?? items` — server-rendered items show immediately on first paint, TanStack Query cache takes over after client hydration without a loading flash
- `PrebookingsList` uses `useState(prebooks)` for optimistic removal — server-seeded list is appropriate for one-shot cancel action without needing a separate query subscription
- Pre-bookings rendered inline on `/account` page — bounded list (users rarely have many pre-bookings), account hub is the natural home, avoids creating another route
- Cancel button only shown for `status === 'waiting'` — notified pre-bookings indicate the book is back in stock, cancellation no longer meaningful

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None beyond expected LF/CRLF line ending warnings from git on Windows (cosmetic only).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 24 is complete: WISH-01 through WISH-04 and PREB-01 through PREB-04 all satisfied
- Phase 25 (Reviews and Ratings) is ready to begin
- Star rating component will be needed — plan noted a non-shadcn component may be required (see STATE.md blocker note)

---
*Phase: 24-wishlist-and-pre-booking*
*Completed: 2026-02-28*

## Self-Check: PASSED

- FOUND: frontend/src/app/wishlist/page.tsx
- FOUND: frontend/src/app/wishlist/_components/WishlistList.tsx
- FOUND: frontend/src/app/wishlist/loading.tsx
- FOUND: frontend/src/app/account/_components/PrebookingsList.tsx
- FOUND: frontend/src/app/account/page.tsx (modified)
- FOUND: frontend/src/components/layout/Header.tsx (modified)
- FOUND: frontend/src/components/layout/MobileNav.tsx (modified)
- FOUND: commit 8c5162d (Task 1)
- FOUND: commit 22740ee (Task 2)
