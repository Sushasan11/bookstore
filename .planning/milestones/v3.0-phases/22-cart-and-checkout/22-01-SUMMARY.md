---
phase: 22-cart-and-checkout
plan: "01"
subsystem: frontend-cart-foundation
tags: [cart, tanstack-query, optimistic-updates, auth-protection, shadcn]
dependency_graph:
  requires: [21-catalog-and-search]
  provides: [cart-data-layer, cart-badge, cart-route-protection, dialog-separator-ui]
  affects: [22-02, 22-03, 22-04, 22-05]
tech_stack:
  added: [shadcn/dialog, shadcn/separator]
  patterns: [optimistic-mutations, mounted-guard, cart-query-key-sharing]
key_files:
  created:
    - frontend/src/lib/cart.ts
    - frontend/src/components/layout/CartBadge.tsx
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/separator.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/components/layout/Header.tsx
    - frontend/src/proxy.ts
decisions:
  - "CartBadge uses mounted guard (useEffect/useState) to prevent SSR/CSR hydration mismatch — same pattern as UserMenu"
  - "useCart hook exported from cart.ts — all mutations share CART_KEY so CartBadge and cart page stay in sync via TanStack Query cache"
  - "recomputeTotals helper uses parseFloat/toFixed(2) to recompute price strings optimistically without backend round-trip"
  - "ApiError.data carries full response body — enables 409 ORDER_INSUFFICIENT_STOCK to expose items[] for per-item stock error display"
metrics:
  duration: "~3 min"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_created: 4
  files_modified: 3
requirements: [SHOP-09, SHOP-10]
---

# Phase 22 Plan 01: Cart Data Layer and Header Badge Summary

Cart API functions (fetchCart, addCartItem, updateCartItem, removeCartItem, checkout, fetchOrder) + useCart hook with optimistic mutations, CartBadge in Header, /cart auth-protected via proxy, shadcn dialog+separator installed.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Extend ApiError with data field, create cart.ts API + useCart hook | b217ec6 | api.ts, cart.ts |
| 2 | Create CartBadge, update Header, protect /cart, install shadcn components | e0d2311 | CartBadge.tsx, Header.tsx, proxy.ts, dialog.tsx, separator.tsx |

## What Was Built

### Cart Data Layer (lib/cart.ts)

Six API functions for cart and order operations, all accepting `accessToken: string` and using `apiFetch` with `Authorization: Bearer` header:

- `fetchCart(accessToken)` — GET /cart → CartResponse
- `addCartItem(accessToken, bookId, quantity?)` — POST /cart/items → CartItemResponse
- `updateCartItem(accessToken, itemId, quantity)` — PUT /cart/items/{itemId} → CartItemResponse
- `removeCartItem(accessToken, itemId)` — DELETE /cart/items/{itemId} → void
- `checkout(accessToken)` — POST /orders/checkout → OrderResponse
- `fetchOrder(accessToken, orderId)` — GET /orders/{orderId} → OrderResponse

`CART_KEY = ['cart'] as const` — shared cache key all components use.

### useCart Hook

Returns: `{ cartQuery, addItem, updateItem, removeItem, checkoutMutation }`

Each mutation follows the full optimistic update pattern:
1. `onMutate`: cancel queries → snapshot previousCart → apply optimistic update → return snapshot
2. `onError`: rollback to snapshot + toast notification
3. `onSettled`: invalidateQueries to sync with server

Optimistic total recomputation uses `recomputeTotals()` helper (parseFloat/toFixed(2) on price strings).

Checkout mutation clears cart cache on success and redirects to `/orders/{id}?confirmed=true`.

### CartBadge Component

Client component with mounted guard (same pattern as UserMenu) — returns null before hydration to prevent mismatch. Shows count badge (capped at "99+") on ShoppingCart icon when user has items. Hidden when: not mounted, not authenticated, or cart is empty.

### Header Integration

Cart link has `className="relative"` so CartBadge (absolutely positioned `-top-1 -right-1`) overlays the ShoppingCart icon correctly.

### Route Protection

`/cart` added to `protectedPrefixes` in proxy.ts — unauthenticated users redirect to `/login?callbackUrl=/cart`.

### ApiError Extension

Added `data?: unknown` field — carries full response body for structured error handling (e.g., 409 ORDER_INSUFFICIENT_STOCK returns `items[]` listing which books are out of stock).

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx tsc --noEmit` — passes (no type errors)
- `npm run build` — passes (7 static pages generated, middleware compiled)
- CartBadge mounted guard prevents hydration mismatch
- /cart protected in proxy.ts

## Self-Check: PASSED

Files verified:
- frontend/src/lib/cart.ts — FOUND
- frontend/src/lib/api.ts — FOUND (data? field added)
- frontend/src/components/layout/CartBadge.tsx — FOUND
- frontend/src/components/layout/Header.tsx — FOUND (CartBadge integrated)
- frontend/src/proxy.ts — FOUND (/cart in protectedPrefixes)
- frontend/src/components/ui/dialog.tsx — FOUND
- frontend/src/components/ui/separator.tsx — FOUND

Commits verified:
- b217ec6 — feat(22-01): extend ApiError with data field, create cart API + useCart hook
- e0d2311 — feat(22-01): add CartBadge to Header, protect /cart route, install shadcn dialog+separator
