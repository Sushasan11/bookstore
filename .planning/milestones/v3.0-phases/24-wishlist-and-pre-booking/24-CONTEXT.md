# Phase 24: Wishlist and Pre-booking - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can save books for later via a wishlist toggle and reserve out-of-stock titles via pre-booking. Covers: wishlist add/remove/view with optimistic toggle, pre-book button for out-of-stock books, pre-bookings list on account page, and pre-booking cancellation. Backend wishlist and pre-booking APIs already exist (Phases 8 and 11).

</domain>

<decisions>
## Implementation Decisions

### Wishlist toggle & feedback
- Heart icon appears on **both** BookCard (catalog grid) and book detail page (ActionButtons area)
- Toggle state: **filled red heart** when wishlisted, **outline heart** when not — classic pattern (Amazon, Airbnb)
- No animation on toggle — simple state swap
- After toggle: **toast notification** ("Added to wishlist" / "Removed from wishlist") — consistent with existing cart toast pattern
- Optimistic update: heart fills/unfills immediately, rolls back with error toast on failure
- Unauthenticated user tapping heart: **toast error + redirect to /login** — same pattern as unauthenticated add-to-cart (no auto-wishlist after login)

### Claude's Discretion
- Wishlist page layout (grid vs list, sorting, empty state design)
- Pre-book button design and placement (replacing "Add to Cart" when out of stock)
- Pre-book confirmation flow (inline vs dialog)
- Pre-bookings list layout on account page
- Pre-booking cancellation interaction
- Heart icon positioning on BookCard (corner placement, z-index relative to cart icon)
- What happens when a wishlisted book's stock status changes

</decisions>

<specifics>
## Specific Ideas

- Follow the existing pattern from Phase 22: BookCard and ActionButtons are already 'use client' components with cart functionality — wishlist toggle should integrate alongside the existing cart button
- Toast pattern already established via sonner in cart mutations — reuse same approach
- Unauthenticated redirect pattern already exists: toast.error + router.push('/login') in click handlers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-wishlist-and-pre-booking*
*Context gathered: 2026-02-28*
