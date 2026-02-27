---
phase: 22-cart-and-checkout
plan: "02"
subsystem: frontend-add-to-cart
tags: [cart, add-to-cart, client-component, optimistic-updates, book-detail, catalog]
dependency_graph:
  requires: [22-01]
  provides: [add-to-cart-action-buttons, add-to-cart-book-card]
  affects: [22-03, 22-04]
tech_stack:
  added: []
  patterns: [useCart-hook-consumption, unauthenticated-redirect-guard, group-hover-visibility]
key_files:
  created: []
  modified:
    - frontend/src/app/books/[id]/_components/ActionButtons.tsx
    - frontend/src/app/books/[id]/page.tsx
    - frontend/src/app/catalog/_components/BookCard.tsx
decisions:
  - "ActionButtons.tsx converted to 'use client' — accepts bookId + inStock props, calls useCart().addItem.mutate on click"
  - "BookCard.tsx converted to 'use client' — cart icon button is absolute-positioned outside the Link to prevent navigation on cart click"
  - "Unauthenticated add-to-cart: toast.error + router.push('/login') in click handler — consistent pattern across both components"
  - "BookCard cart icon: opacity-0 md:group-hover:opacity-100 on desktop, always visible mobile — per CONTEXT.md hover decision"
metrics:
  duration: "~3 min"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_created: 0
  files_modified: 3
requirements: [SHOP-01, SHOP-10]
---

# Phase 22 Plan 02: Add to Cart UI Wiring Summary

ActionButtons on book detail page and BookCard on catalog grid converted to client components and wired to useCart().addItem mutation with optimistic badge updates, toast feedback, loading states, out-of-stock handling, and unauthenticated redirect.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Convert ActionButtons to client component with functional Add to Cart | 3019d67 | ActionButtons.tsx, page.tsx |
| 2 | Add cart icon to BookCard on catalog grid | 0e02bed | BookCard.tsx |

## What Was Built

### ActionButtons.tsx (Book Detail Page)

Converted from static Server Component to interactive Client Component:

- `'use client'` directive added
- Props extended: `bookId: number` added alongside existing `inStock: boolean`
- `useCart().addItem` mutation wired to button click
- Button states:
  - `!inStock`: disabled, "Out of Stock"
  - `addItem.isPending`: disabled, "Adding..."
  - default: enabled, "Add to Cart"
- Unauthenticated guard: checks `session?.accessToken` in click handler, shows `toast.error('Please sign in...')` and redirects to `/login`
- Wishlist button remains disabled (Phase 24)
- "Coming soon" `<p>` tag removed

### page.tsx Update

Single line change: `<ActionButtons inStock={book.in_stock} />` → `<ActionButtons bookId={book.id} inStock={book.in_stock} />`. Server Component passes the book's numeric ID to the new client component.

### BookCard.tsx (Catalog Grid)

Converted from pure Server Component to Client Component:

- `'use client'` directive added
- Restructured layout: outer `<div className="group relative ...">` wraps both the `<Link>` (cover + info) and the absolute-positioned cart button
- Cart icon button (`<Button variant="secondary" size="icon">`) positioned `absolute top-2 right-2`
- Visibility: `opacity-100 md:opacity-0 md:group-hover:opacity-100` — always visible on mobile, hover-reveal on desktop
- `e.preventDefault()` + `e.stopPropagation()` in click handler prevents Link navigation
- Only rendered when `inStock` is true (no icon for out-of-stock books)
- Same unauthenticated guard pattern as ActionButtons
- All existing styling preserved: cover colors, badges, aspect ratio, hover shadow

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx tsc --noEmit` — passes (no type errors in modified files)
- `npm run build` — passes (8 pages including /cart, all routes generated)
- ActionButtons wired to useCart().addItem with toast feedback from cart.ts
- BookCard cart icon positioned outside Link, hover behavior per CONTEXT.md spec

## Self-Check: PASSED

Files verified:
- frontend/src/app/books/[id]/_components/ActionButtons.tsx — FOUND (has 'use client', useCart, bookId prop)
- frontend/src/app/books/[id]/page.tsx — FOUND (passes bookId prop)
- frontend/src/app/catalog/_components/BookCard.tsx — FOUND (has 'use client', group-hover pattern)

Commits verified:
- 3019d67 — feat(22-02): convert ActionButtons to client component with functional Add to Cart
- 0e02bed — feat(22-02): convert BookCard to client component with cart icon button
