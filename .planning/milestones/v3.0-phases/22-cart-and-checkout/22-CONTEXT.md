# Phase 22: Cart and Checkout - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can manage a shopping cart and complete a checkout that produces an order. Covers: add to cart from catalog/detail pages, view cart with quantities and totals, update quantities, remove items, checkout with mock payment, and order confirmation page. Cart badge in navbar updates reactively. Optimistic updates with rollback on error.

Backend cart API (GET/POST/PUT/DELETE /cart) and orders API (POST /orders/checkout, GET /orders, GET /orders/{id}) are already fully implemented. This phase is **frontend-only** — building the React pages/components that consume these existing APIs.

</domain>

<decisions>
## Implementation Decisions

### Cart page layout
- Vertical list of cart items (not a table) — each row shows cover thumbnail, title, author, unit price, quantity control, line total, and a remove button
- Quantity control: inline stepper (minus / number / plus) — min 1, disable minus at 1
- Sticky order summary sidebar on desktop (items count, subtotal, checkout button); on mobile, summary collapses to a fixed bottom bar with total + "Checkout" button
- Empty cart state: illustration + "Your cart is empty" message with a "Browse Books" CTA linking to /catalog

### Add-to-cart interaction
- "Add to Cart" button on BookDetailHero (already exists as disabled placeholder) becomes functional
- Catalog grid cards get a small cart icon button on hover (desktop) / always visible (mobile)
- On successful add: sonner toast ("Added to cart") with book title — no cart drawer/flyout (keep it simple)
- If item already in cart: toast says "Already in cart" with link to /cart
- Cart badge: numeric count badge on the ShoppingCart icon in Header, pulled from a `useCart` React Query hook that caches cart state; invalidated on mutations

### Checkout flow
- Single-page checkout (not multi-step) — the cart page itself has the checkout action
- No separate /checkout route; the checkout CTA on the cart page triggers the order
- Mock payment: POST /orders/checkout with no payment form (the API already handles mock payment)
- On checkout click: confirm dialog ("Place order for $X.XX?") → loading state → redirect to confirmation
- Error handling: 422 empty cart (shouldn't happen, but show toast), 409 insufficient stock (show which items, let user adjust), 402 payment failed (show error toast)

### Order confirmation page
- Route: /orders/[id] — serves as both confirmation (redirected after checkout) and order detail (from order history)
- Shows: order number, date, item list with titles/quantities/prices, and order total
- Success banner at top when arriving from checkout (via query param like ?confirmed=true)
- CTA: "Continue Shopping" → /catalog, "View All Orders" → /orders
- No separate /orders list page in this phase — just the single order detail; order history is a future concern

### Optimistic updates
- Add to cart: optimistically increment badge count, roll back on error with toast
- Remove from cart: optimistically remove item from list, roll back on error with toast
- Update quantity: optimistically update quantity + recalculate totals, roll back on error
- All mutations use React Query's `useMutation` with `onMutate`/`onError`/`onSettled` for optimistic patterns

### Claude's Discretion
- Loading skeleton designs for cart page
- Exact spacing, typography, and responsive breakpoints (follow existing patterns)
- React Query key structure and cache invalidation strategy
- Whether to use a shared `useCart` hook or separate hooks per mutation
- Cart item animation on add/remove (subtle or none)

</decisions>

<specifics>
## Specific Ideas

- The Header already has a ShoppingCart icon linking to `/cart` and the MobileNav already includes a Cart link — just need to add the badge count
- ActionButtons.tsx in the book detail page already has a disabled "Add to Cart" button — wire it up
- Use sonner toasts (already configured) for all feedback — matches existing patterns
- Backend returns `CartResponse.total_items` and `CartResponse.total_price` as computed fields — use these directly for badge and summary

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-cart-and-checkout*
*Context gathered: 2026-02-27*
