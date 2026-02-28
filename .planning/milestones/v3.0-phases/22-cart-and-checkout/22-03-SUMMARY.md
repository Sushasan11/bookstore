---
phase: 22-cart-and-checkout
plan: "03"
subsystem: ui
tags: [cart, next-image, shadcn, tanstack-query, optimistic-updates, lucide-react]

dependency_graph:
  requires:
    - phase: 22-01
      provides: useCart hook with optimistic mutations, CartResponse/CartItemResponse types
  provides:
    - cart-page-ui
    - cart-item-component
    - quantity-stepper-component
    - cart-summary-component
    - cart-loading-skeleton
    - cart-empty-state
  affects: [22-04, 22-05]

tech-stack:
  added: []
  patterns: [server-shell-client-content, inline-loading-skeleton, fixed-mobile-bottom-bar, sticky-desktop-sidebar]

key-files:
  created:
    - frontend/src/app/cart/page.tsx
    - frontend/src/app/cart/loading.tsx
    - frontend/src/app/cart/_components/CartPageContent.tsx
    - frontend/src/app/cart/_components/CartItem.tsx
    - frontend/src/app/cart/_components/QuantityStepper.tsx
    - frontend/src/app/cart/_components/CartSummary.tsx
  modified: []

key-decisions:
  - "removeItem.mutate({ itemId }) — hook's mutationFn destructures { itemId }, not a bare number; CartPageContent wraps calls accordingly"
  - "CartSummary renders two elements: sticky sidebar card (desktop) and fixed bottom bar (mobile <lg) — CartPageContent adds pb-20 lg:pb-0 to prevent content overlap"
  - "QuantityStepper disables minus button when quantity <= 1 to enforce minimum of 1"
  - "CartPageContent has inline CartLoadingSkeleton (duplicate of loading.tsx) to handle client-side loading after shell renders"

patterns-established:
  - "Server shell + 'use client' content pattern: page.tsx is server component, CartPageContent.tsx is the client orchestrator"
  - "Inline loading skeleton: CartPageContent renders its own skeleton (not just relying on Suspense loading.tsx) for client-side re-fetching"

requirements-completed: [SHOP-02, SHOP-03, SHOP-04, SHOP-10]

duration: ~3min
completed: 2026-02-27
---

# Phase 22 Plan 03: Cart Page UI Summary

**Complete /cart page with CartItem list, QuantityStepper quantity controls, CartSummary sticky sidebar/mobile bar, and empty/error/loading states wired to useCart optimistic mutations**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-27T17:29:02Z
- **Completed:** 2026-02-27T17:32:21Z
- **Tasks:** 2
- **Files modified:** 6 created

## Accomplishments

- Cart page with server shell + 'use client' CartPageContent orchestrator handling loading/error/empty/populated states
- CartItem rows with next/image cover thumbnail, title, author, unit price, QuantityStepper, line total, and remove (Trash2) button
- CartSummary with two presentations: sticky Order Summary card on desktop, fixed bottom bar on mobile
- QuantityStepper enforces min=1 with minus button disabled at quantity 1
- All mutations called via useCart hook from Plan 01 — optimistic updates handled by the hook

## Task Commits

Each task was committed atomically:

1. **Task 1: Cart page shell, loading state, CartPageContent** - `9ceddaf` (feat)
2. **Task 2: CartItem, QuantityStepper, CartSummary** - `0e02bed` (feat)

## Files Created/Modified

- `frontend/src/app/cart/page.tsx` — Thin server shell: metadata + CartPageContent under max-w-7xl container
- `frontend/src/app/cart/loading.tsx` — Skeleton loading state: 3 placeholder items + sidebar skeleton
- `frontend/src/app/cart/_components/CartPageContent.tsx` — Client orchestrator: loading/error/empty/populated states, delegates to CartItem + CartSummary
- `frontend/src/app/cart/_components/CartItem.tsx` — Item row: cover thumbnail (next/image), title link, author, unit price, QuantityStepper, line total, remove button
- `frontend/src/app/cart/_components/QuantityStepper.tsx` — Inline minus/quantity/plus control with min=1 enforcement
- `frontend/src/app/cart/_components/CartSummary.tsx` — Desktop sticky sidebar card + mobile fixed bottom bar with Order Summary + Checkout button

## Decisions Made

- The `removeItem` mutation in cart.ts takes `{ itemId: number }`, not a bare number. CartPageContent wraps calls in `handleRemove(itemId) { removeItem.mutate({ itemId }) }` accordingly.
- CartSummary renders a fragment with two elements. The desktop checkout button uses `hidden lg:flex` so it only shows on large viewports. The mobile bottom bar uses `lg:hidden`.
- CartPageContent duplicates the loading skeleton inline (rather than relying solely on loading.tsx) to handle client-side loading states after initial page render.

## Deviations from Plan

None — plan executed exactly as written, with one minor adaptation: the `removeItem.mutate(itemId)` call in the plan spec was corrected to `removeItem.mutate({ itemId })` to match the actual hook signature from Plan 01 (mutationFn destructures `{ itemId }`). This is a spec/implementation consistency fix, not a scope change.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- /cart page fully functional with optimistic mutations from Plan 01's useCart hook
- CartSummary Checkout button calls `checkoutMutation.mutate()` directly — Plan 04 will wrap this in a CheckoutDialog confirmation step
- Ready for Plan 04: Checkout dialog and order confirmation flow

## Self-Check: PASSED

Files verified:
- frontend/src/app/cart/page.tsx — FOUND
- frontend/src/app/cart/loading.tsx — FOUND
- frontend/src/app/cart/_components/CartPageContent.tsx — FOUND
- frontend/src/app/cart/_components/CartItem.tsx — FOUND
- frontend/src/app/cart/_components/QuantityStepper.tsx — FOUND
- frontend/src/app/cart/_components/CartSummary.tsx — FOUND

Commits verified:
- 9ceddaf — feat(22-03): create cart page shell, loading skeleton, and CartPageContent
- 0e02bed — feat(22-02): convert BookCard to client component with cart icon button (contained Task 2 files)

---
*Phase: 22-cart-and-checkout*
*Completed: 2026-02-27*
