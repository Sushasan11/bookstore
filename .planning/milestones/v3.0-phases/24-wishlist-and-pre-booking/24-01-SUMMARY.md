---
phase: 24-wishlist-and-pre-booking
plan: "01"
subsystem: ui
tags: [react, tanstack-query, optimistic-updates, wishlist, pre-booking, lucide-react]

# Dependency graph
requires:
  - phase: 22-cart-and-checkout
    provides: cart.ts hook pattern (useCart, CART_KEY, apiFetch, optimistic updates with onMutate/onError/onSettled)
  - phase: 20-auth-integration
    provides: useSession() for accessToken, toast.error + router.push('/login') unauthenticated guard pattern
provides:
  - useWishlist hook with WISHLIST_KEY shared cache, optimistic toggle, Set<number> wishlistedIds for O(1) lookup
  - usePrebook hook with pre-book mutation and 409 error handling (PREBOOK_DUPLICATE, IN_STOCK)
  - Heart icon on BookCard (top-left, stopPropagation, hover visibility matching cart icon)
  - Heart toggle on ActionButtons with Wishlisted/Add to Wishlist label (live, not disabled)
  - Pre-book button on ActionButtons replacing Add to Cart when book is out of stock
affects: [25-reviews-and-ratings, wishlist-page, pre-bookings-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generic useMutation type parameters for explicit context typing: useMutation<TData, TError, TVariables, TContext>"
    - "Shared query key pattern (WISHLIST_KEY, PREBOOK_KEY) mirrors CART_KEY for multi-component cache sharing"
    - "Heart toggle: optimistic update with stub item (id: -1) for immediate UI feedback before server confirms"

key-files:
  created:
    - frontend/src/lib/wishlist.ts
    - frontend/src/lib/prebook.ts
  modified:
    - frontend/src/app/catalog/_components/BookCard.tsx
    - frontend/src/app/books/[id]/_components/ActionButtons.tsx

key-decisions:
  - "useMutation explicit generic type parameters required for TypeScript to correctly type onMutate context when mutationFn returns union type (WishlistItemResponse | void)"
  - "Heart button on BookCard uses e.preventDefault()+e.stopPropagation() — prevents Link navigation on heart click, matching cart button pattern"
  - "Pre-book button replaces entire Add to Cart button (not added alongside) when inStock is false — cleaner UX, no disabled state"
  - "usePrebook includes prebooksQuery for future wishlist/pre-bookings page consumption"

patterns-established:
  - "Heart filled state: fill-red-500 text-red-500 classes on Heart icon (lucide-react stroke-only by default)"
  - "No animation on heart toggle — per CONTEXT.md locked decision; simple class swap only"
  - "409 error detail string matching: check for PREBOOK_DUPLICATE/already (duplicate) vs IN_STOCK (book restocked)"

requirements-completed: [WISH-01, WISH-02, WISH-04, PREB-01, PREB-02]

# Metrics
duration: 10min
completed: 2026-02-28
---

# Phase 24 Plan 01: Wishlist and Pre-booking Core Summary

**useWishlist hook with optimistic heart toggle and usePrebook hook with 409 error handling, wired into BookCard (top-left heart) and ActionButtons (live toggle + Pre-book button for out-of-stock books)**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-27T20:34:25Z
- **Completed:** 2026-02-27T20:44:00Z
- **Tasks:** 2
- **Files modified:** 4 (created 2, modified 2)

## Accomplishments

- Created `wishlist.ts` with useWishlist hook: shared WISHLIST_KEY cache, Set<number> wishlistedIds for O(1) heart-state lookup, optimistic toggle with rollback, toast notifications
- Created `prebook.ts` with usePrebook hook: pre-book mutation with granular 409 error handling (PREBOOK_DUPLICATE vs IN_STOCK), auth guard redirecting to /login
- Wired heart icon into BookCard (top-left corner, stopPropagation prevents navigation, same hover visibility pattern as cart icon)
- Wired live heart toggle into ActionButtons with "Wishlisted"/"Add to Wishlist" label (replaces disabled placeholder)
- Added Pre-book button to ActionButtons: renders when `inStock` is false, replaces Add to Cart button entirely

## Task Commits

Each task was committed atomically:

1. **Task 1: Create useWishlist hook and usePrebook hook** - `824d73f` (feat)
2. **Task 2: Wire heart icon on BookCard and ActionButtons + Pre-book button** - `dfb6130` (feat)

## Files Created/Modified

- `frontend/src/lib/wishlist.ts` - useWishlist hook with optimistic toggle, WISHLIST_KEY cache, fetchWishlist/addToWishlist/removeFromWishlist API functions
- `frontend/src/lib/prebook.ts` - usePrebook hook with pre-book mutation, PREBOOK_KEY, fetchPrebooks/createPrebook/cancelPrebook API functions
- `frontend/src/app/catalog/_components/BookCard.tsx` - Added Heart import, useWishlist(), handleHeartClick with stopPropagation, heart button top-left
- `frontend/src/app/books/[id]/_components/ActionButtons.tsx` - Added useWishlist/usePrebook imports, live heart toggle, Pre-book button for out-of-stock

## Decisions Made

- Used explicit generic type parameters on `useMutation<TData, TError, TVariables, TContext>` — required when mutationFn returns `WishlistItemResponse | void` (union type) so TypeScript correctly infers context type in onMutate/onError/onSuccess callbacks
- Pre-book button replaces (not supplements) Add to Cart when out of stock — cleaner conditional render using ternary instead of disabled state
- `usePrebook` includes `prebooksQuery` even though not used by the current UI — prepares for pre-bookings management page in Phase 24

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript union return type causing context type inference failure**
- **Found during:** Task 1 (useWishlist hook creation)
- **Issue:** `useMutation` with `mutationFn` returning `Promise<WishlistItemResponse | void>` caused TypeScript error TS2322 and lost context type in callbacks (context typed as `{}` instead of `{ previousWishlist, isWishlisted }`)
- **Fix:** Added explicit generic type parameters: `useMutation<WishlistItemResponse | void, Error, { bookId: number; isWishlisted: boolean }, { previousWishlist: WishlistResponse | undefined; isWishlisted: boolean }>(...)`
- **Files modified:** `frontend/src/lib/wishlist.ts`
- **Verification:** `npx tsc --noEmit` — zero errors
- **Committed in:** `824d73f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - TypeScript type inference bug)
**Impact on plan:** Fix necessary for correct TypeScript typing of onMutate context. No scope creep.

## Issues Encountered

None beyond the TypeScript mutation type inference issue documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wishlist and pre-booking data layer is complete and ready for Phase 24 Plan 02 (wishlist page and pre-bookings management page)
- Heart icon is live on both BookCard (catalog) and ActionButtons (book detail) — users can toggle wishlist from any surface
- Pre-book flow is complete for out-of-stock books on the detail page
- WISH-01, WISH-02, WISH-04, PREB-01, PREB-02 requirements satisfied

---
*Phase: 24-wishlist-and-pre-booking*
*Completed: 2026-02-28*

## Self-Check: PASSED

- FOUND: frontend/src/lib/wishlist.ts
- FOUND: frontend/src/lib/prebook.ts
- FOUND: frontend/src/app/catalog/_components/BookCard.tsx
- FOUND: frontend/src/app/books/[id]/_components/ActionButtons.tsx
- FOUND: .planning/phases/24-wishlist-and-pre-booking/24-01-SUMMARY.md
- FOUND: commit 824d73f (feat: useWishlist and usePrebook hooks)
- FOUND: commit dfb6130 (feat: BookCard heart + ActionButtons pre-book)
