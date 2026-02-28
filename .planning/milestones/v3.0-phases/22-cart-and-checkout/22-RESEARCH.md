# Phase 22: Cart and Checkout - Research

**Researched:** 2026-02-27
**Domain:** React client-side state, TanStack Query v5 optimistic mutations, Next.js 16 App Router protected pages
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase boundary:** Frontend-only — backend cart API (GET/POST/PUT/DELETE /cart) and orders API (POST /orders/checkout, GET /orders/{id}) are already fully implemented.

**Cart page layout:**
- Vertical list of cart items (not a table) — each row shows cover thumbnail, title, author, unit price, quantity control, line total, and a remove button
- Quantity control: inline stepper (minus / number / plus) — min 1, disable minus at 1
- Sticky order summary sidebar on desktop (items count, subtotal, checkout button); on mobile, summary collapses to a fixed bottom bar with total + "Checkout" button
- Empty cart state: illustration + "Your cart is empty" message with a "Browse Books" CTA linking to /catalog

**Add-to-cart interaction:**
- "Add to Cart" button on BookDetailHero (already exists as disabled placeholder in ActionButtons.tsx) becomes functional
- Catalog grid cards get a small cart icon button on hover (desktop) / always visible (mobile)
- On successful add: sonner toast ("Added to cart") with book title — no cart drawer/flyout (keep it simple)
- If item already in cart: toast says "Already in cart" with link to /cart
- Cart badge: numeric count badge on the ShoppingCart icon in Header, pulled from a `useCart` React Query hook that caches cart state; invalidated on mutations

**Checkout flow:**
- Single-page checkout (not multi-step) — the cart page itself has the checkout action
- No separate /checkout route; the checkout CTA on the cart page triggers the order
- Mock payment: POST /orders/checkout with no payment form (the API already handles mock payment)
- On checkout click: confirm dialog ("Place order for $X.XX?") → loading state → redirect to confirmation
- Error handling: 422 empty cart (shouldn't happen, but show toast), 409 insufficient stock (show which items, let user adjust), 402 payment failed (show error toast)

**Order confirmation page:**
- Route: /orders/[id] — serves as both confirmation (redirected after checkout) and order detail (from order history)
- Shows: order number, date, item list with titles/quantities/prices, and order total
- Success banner at top when arriving from checkout (via query param like ?confirmed=true)
- CTA: "Continue Shopping" → /catalog, "View All Orders" → /orders
- No separate /orders list page in this phase — just the single order detail; order history is a future concern

**Optimistic updates:**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SHOP-01 | User can add a book to the shopping cart | POST /cart/items — needs auth token, 409 CART_ITEM_DUPLICATE handling, optimistic badge increment |
| SHOP-02 | User can update item quantity in the cart | PUT /cart/items/{item_id} — optimistic setQueryData, min=1 enforced client-side |
| SHOP-03 | User can remove an item from the cart | DELETE /cart/items/{item_id} returns 204 — optimistic list removal, rollback on error |
| SHOP-04 | User can view cart with item list, quantities, and total | GET /cart — CartResponse.items, total_items, total_price; empty state when items=[] |
| SHOP-05 | User can checkout and place an order (mock payment) | POST /orders/checkout — confirm dialog, loading state, redirect to /orders/[id]?confirmed=true |
| SHOP-06 | User sees order confirmation page after successful checkout | GET /orders/{order_id} — /orders/[id] route with ?confirmed=true banner |
| SHOP-09 | Cart count badge in navbar updates reactively after mutations | useCart hook reading CartResponse.total_items; Header needs CartBadge client component with mounted guard |
| SHOP-10 | Cart add/remove uses optimistic updates with rollback on error | TanStack Query v5 useMutation onMutate/onError/onSettled pattern with cancelQueries + setQueryData |
</phase_requirements>

---

## Summary

Phase 22 is a pure frontend phase that builds the cart and checkout UI on top of a fully implemented backend API. The technical challenge is not the API integration itself (the patterns for that are established in prior phases) but rather orchestrating **optimistic UI updates** correctly and wiring the **cart badge** into the server-rendered Header without hydration mismatches.

The backend exposes `GET /cart` → `CartResponse` (with computed `total_items` and `total_price`), four mutation endpoints (POST /cart/items, PUT /cart/items/{id}, DELETE /cart/items/{id}, POST /orders/checkout), and `GET /orders/{id}` for confirmation. All cart/order endpoints require `Authorization: Bearer <token>` — the access token is available from `session.accessToken` via `useSession()`.

The key architectural challenge is the **Header cart badge**: the Header is currently a Server Component, but the badge count is dynamic client state. The established pattern from Phase 20's `UserMenu` is to extract dynamic parts into a separate `'use client'` component with a `mounted` guard. The same pattern applies here — a `CartBadge` client component fetches cart count via `useQuery` and renders it on the `ShoppingCart` icon.

**Primary recommendation:** Create a `useCart` shared hook that returns cart data and all mutation functions with optimistic updates baked in. This keeps the cache key structure (`['cart']`) consistent across the entire phase and makes invalidation simple.

## Standard Stack

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | 5.90.21 | Cart data fetching + mutations + optimistic updates | Already configured in providers.tsx |
| next-auth/react | ^5.0.0-beta.30 | `useSession()` to get `accessToken` for authenticated API calls | Already in use |
| sonner | 2.0.7 | Toast notifications for add/remove/error feedback | Already configured in providers.tsx as `<Toaster richColors position="bottom-right" />` |
| lucide-react | ^0.575.0 | ShoppingCart icon (already in Header), Plus/Minus for stepper | Already installed |
| shadcn/ui | Components already in `/components/ui/` | button, card, skeleton, badge, input | Already installed |

### shadcn Components to Install

These are needed but not yet present in `/frontend/src/components/ui/`:

| Component | Command | Used For |
|-----------|---------|----------|
| dialog | `npx shadcn@latest add dialog` | Checkout confirmation dialog |
| separator | `npx shadcn@latest add separator` | Cart page section dividers |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| React Query optimistic updates | Zustand local cart state | STATE.md mentions Zustand for display state, but CONTEXT.md locked `useCart` React Query hook — RQ is server source of truth, correct choice |
| AlertDialog (shadcn) | window.confirm() | AlertDialog is on-brand, accessible; window.confirm() is ugly and not theme-aware |

**Installation:**
```bash
# From frontend/ directory
npx shadcn@latest add dialog
npx shadcn@latest add separator
```

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── app/
│   ├── cart/
│   │   ├── page.tsx                  # Cart page (server shell, client cart content)
│   │   ├── loading.tsx               # Skeleton loading state
│   │   └── _components/
│   │       ├── CartPageContent.tsx   # 'use client' — fetches + renders cart
│   │       ├── CartItem.tsx          # Single cart item row
│   │       ├── CartSummary.tsx       # Sticky sidebar / mobile bottom bar
│   │       ├── QuantityStepper.tsx   # Minus / count / Plus inline control
│   │       └── CheckoutDialog.tsx    # Confirm dialog for place order
│   └── orders/
│       └── [id]/
│           ├── page.tsx              # Order detail / confirmation page
│           └── _components/
│               └── OrderDetail.tsx   # 'use client' — fetches order, shows banner
├── components/
│   └── layout/
│       ├── Header.tsx                # Add <CartBadge /> next to ShoppingCart icon
│       └── CartBadge.tsx             # 'use client' — useCart hook → badge count
└── lib/
    ├── api.ts                        # Already exists — add apiFetchAuthed() helper
    └── cart.ts                       # New: cart API functions + useCart hook
```

### Pattern 1: Authenticated API Calls

The existing `apiFetch()` in `/lib/api.ts` does not attach auth tokens. All cart/order endpoints require `Authorization: Bearer <token>`. The access token is on `session.accessToken` from `useSession()`. The correct approach is to create an auth-aware fetch wrapper used within client components:

```typescript
// lib/cart.ts
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type CartResponse = components['schemas']['CartResponse']
type CartItemResponse = components['schemas']['CartItemResponse']
type OrderResponse = components['schemas']['OrderResponse']

export async function fetchCart(accessToken: string): Promise<CartResponse> {
  return apiFetch<CartResponse>('/cart', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function addCartItem(
  accessToken: string,
  bookId: number,
  quantity = 1
): Promise<CartItemResponse> {
  return apiFetch<CartItemResponse>('/cart/items', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ book_id: bookId, quantity }),
  })
}

export async function updateCartItem(
  accessToken: string,
  itemId: number,
  quantity: number
): Promise<CartItemResponse> {
  return apiFetch<CartItemResponse>(`/cart/items/${itemId}`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ quantity }),
  })
}

export async function removeCartItem(
  accessToken: string,
  itemId: number
): Promise<void> {
  return apiFetch<void>(`/cart/items/${itemId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function checkout(accessToken: string): Promise<OrderResponse> {
  return apiFetch<OrderResponse>('/orders/checkout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ force_payment_failure: false }),
  })
}

export async function fetchOrder(
  accessToken: string,
  orderId: number
): Promise<OrderResponse> {
  return apiFetch<OrderResponse>(`/orders/${orderId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Pattern 2: useCart Hook

A shared `useCart` hook keeps the `['cart']` query key consistent across all components. All mutations live here so cache invalidation is centralized:

```typescript
// lib/cart.ts — continued
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'

export const CART_KEY = ['cart'] as const

export function useCart() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

  const cartQuery = useQuery({
    queryKey: CART_KEY,
    queryFn: () => fetchCart(accessToken),
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  return { cartQuery }
}
```

### Pattern 3: TanStack Query v5 Optimistic Updates

The full optimistic update pattern for remove-from-cart (example — add/update follow the same shape):

```typescript
// Source: https://tanstack.com/query/v5/docs/react/guides/optimistic-updates
const removeItem = useMutation({
  mutationFn: (itemId: number) => removeCartItem(accessToken, itemId),
  onMutate: async (itemId) => {
    // 1. Cancel any outgoing refetches (prevent overwriting optimistic update)
    await queryClient.cancelQueries({ queryKey: CART_KEY })

    // 2. Snapshot the previous value
    const previousCart = queryClient.getQueryData<CartResponse>(CART_KEY)

    // 3. Optimistically update to the new value
    if (previousCart) {
      queryClient.setQueryData<CartResponse>(CART_KEY, {
        ...previousCart,
        items: previousCart.items.filter((item) => item.id !== itemId),
        // Note: total_items and total_price are read-only computed fields in the schema.
        // The optimistic cart does not need accurate totals — server reconciles on settle.
        // For the badge count, invalidation in onSettled provides the accurate value.
      })
    }

    // 4. Return context for rollback
    return { previousCart }
  },
  onError: (_err, _itemId, context) => {
    // 5. Rollback to previous state
    if (context?.previousCart) {
      queryClient.setQueryData(CART_KEY, context.previousCart)
    }
    toast.error('Failed to remove item. Please try again.')
  },
  onSettled: () => {
    // 6. Always sync with server after mutation (error or success)
    queryClient.invalidateQueries({ queryKey: CART_KEY })
  },
})
```

**Important:** `CartResponse.total_items` and `total_price` are `readonly` computed fields — the TypeScript schema marks them as `readonly`. When doing `setQueryData` for optimistic updates, compute these locally for the optimistic state or accept that they will be slightly stale until `onSettled` invalidates. For add/update, compute the new total locally; for remove, filter the items array and recompute from items client-side.

### Pattern 4: CartBadge Client Component (Header Integration)

The Header is a Server Component. Cart count is dynamic. Use the same pattern as `UserMenu` — a separate `'use client'` component with mounted guard:

```typescript
// components/layout/CartBadge.tsx
'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { fetchCart, CART_KEY } from '@/lib/cart'

export function CartBadge() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  const { data: cart } = useQuery({
    queryKey: CART_KEY,
    queryFn: () => fetchCart(accessToken),
    enabled: !!accessToken && mounted,
  })

  if (!mounted || !cart || cart.total_items === 0) return null

  return (
    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
      {cart.total_items > 99 ? '99+' : cart.total_items}
    </span>
  )
}
```

In `Header.tsx`, wrap the ShoppingCart icon button with `relative` positioning and add `<CartBadge />`:

```typescript
// Header.tsx — ShoppingCart section
<Link href="/cart" className="relative">
  <Button variant="ghost" size="icon" aria-label="Shopping cart">
    <ShoppingCart className="h-5 w-5" />
    <CartBadge />
  </Button>
</Link>
```

### Pattern 5: Middleware — Add /cart to Protected Routes

The current `proxy.ts` protects `/orders` but not `/cart`. Cart must require authentication (the backend requires it). Add `/cart` to `protectedPrefixes`:

```typescript
// src/proxy.ts
const protectedPrefixes = ["/account", "/orders", "/checkout", "/wishlist", "/prebook", "/cart"]
```

### Pattern 6: Order Confirmation Page

The `/orders/[id]` page is a Server Component that fetches order data, but it needs `?confirmed=true` banner logic. The cleanest approach: make the page a server component that passes `confirmed` prop to a client component:

```typescript
// app/orders/[id]/page.tsx
import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { fetchOrder } from '@/lib/cart'
import { OrderDetail } from './_components/OrderDetail'

export default async function OrderDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<{ confirmed?: string }>
}) {
  const session = await auth()
  if (!session) redirect('/login')

  const { id } = await params
  const { confirmed } = await searchParams
  const order = await fetchOrder(session.accessToken, Number(id))

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <OrderDetail order={order} isConfirmed={confirmed === 'true'} />
    </div>
  )
}
```

### Pattern 7: 409 CART_ITEM_DUPLICATE Handling

When a book is already in cart, the backend returns 409 with `code: "CART_ITEM_DUPLICATE"`. The add-to-cart mutation must catch this and show "Already in cart" toast with a `/cart` link:

```typescript
onError: (err) => {
  if (err instanceof ApiError && err.status === 409) {
    // Check if duplicate or out-of-stock
    toast.error('Already in cart', {
      description: 'This book is already in your cart.',
      action: { label: 'View Cart', onClick: () => router.push('/cart') },
    })
  } else {
    toast.error('Failed to add to cart. Please try again.')
  }
}
```

### Pattern 8: 409 Insufficient Stock at Checkout

The checkout endpoint returns 409 `ORDER_INSUFFICIENT_STOCK` with body containing `items: InsufficientStockItem[]` (each with `book_id`, `title`, `requested`, `available`). Show these in the error toast or inline error state:

```typescript
// The ApiError.detail contains the message. For insufficient stock,
// need to parse the response body which the ApiError captures in `detail`.
// Since ApiError captures body.detail as string, the insufficient stock items
// are in the HTTP response body. Consider extending ApiError to capture full body.
```

**Decision needed for planning:** Should `ApiError` be extended to carry the full response body (not just `detail` string), or parse the detail string for insufficient stock item names? Recommendation: extend `ApiError` to accept an optional `body` field so the 409 response items can be displayed properly.

### Anti-Patterns to Avoid

- **Don't put cart mutations in a single giant component:** Split `CartPageContent` (data + mutations), `CartItem` (display + per-item mutations), and `CartSummary` (totals + checkout trigger) — this avoids re-rendering the whole list on every mutation.
- **Don't call `fetchCart` server-side with `auth()`:** The `/orders/[id]` page is the exception (server-fetches order). The cart page should be client-side data because the cart changes frequently and does not need ISR — unlike catalog pages.
- **Don't forget the `enabled: !!accessToken` guard on cart queries:** Without this, the query fires on page load before session is ready, producing a 401 error logged to the console.
- **Don't optimistically compute `total_price` as a string:** `CartResponse.total_price` is a `string` in the TypeScript type (Pydantic Decimal serializes to string). Compute local optimistic totals as numbers with `parseFloat()`, display with `.toFixed(2)`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confirm dialog | Custom modal with useState | `shadcn/ui Dialog` (install) or `AlertDialog` | Accessibility, focus trap, keyboard dismiss built-in |
| Toast notifications | Custom notification system | `sonner` (already installed + configured) | Already in providers.tsx with richColors |
| Quantity input validation | Custom input with regex | Inline min/max clamp + disabled state on the stepper | No separate validation library needed — just `Math.max(1, newQty)` |
| Auth token on API calls | Token passed as prop through component tree | `useSession()` called at the hook level | Session is already available anywhere inside SessionProvider |
| Cart item badge count | Separate API call for count | Derive from `CartResponse.total_items` — same query | The GET /cart returns total_items; no extra endpoint needed |

**Key insight:** The backend does all the hard work (stock checking, price locking, payment simulation). The frontend is purely display + mutation orchestration.

## Common Pitfalls

### Pitfall 1: CartBadge Causes Hydration Mismatch

**What goes wrong:** `CartBadge` renders a non-zero count on client but the server renders nothing (or 0), causing React hydration error.

**Why it happens:** The badge count depends on session (client-only) and a network request. Server can't know this value.

**How to avoid:** Apply the established `mounted` guard pattern from `UserMenu.tsx` — return `null` before `useEffect` sets `mounted = true`. This matches the server render (null) with the initial client render (null), then updates client-side.

**Warning signs:** React hydration mismatch console error, badge flickering on first load.

### Pitfall 2: Stale Cart After Navigation

**What goes wrong:** User adds item to cart on book detail page, navigates to cart page, cart shows old count.

**Why it happens:** React Query caches the cart query. If `staleTime` is too long, the cached result is shown instead of refetching.

**How to avoid:** Set `staleTime: 30_000` (30 seconds) on the cart query — short enough that normal navigation triggers a refetch. Mutations must call `queryClient.invalidateQueries({ queryKey: CART_KEY })` in `onSettled` to force immediate sync.

**Warning signs:** Cart page shows 0 items after add-to-cart from detail page.

### Pitfall 3: /cart Not Protected, Cart Page Shows Error Instead of Login Redirect

**What goes wrong:** Unauthenticated user visits `/cart`, the `useCart` query fires with an empty `accessToken`, gets a 401, shows an error state instead of redirecting to `/login`.

**Why it happens:** `/cart` is not in `protectedPrefixes` in `proxy.ts`.

**How to avoid:** Add `/cart` to `protectedPrefixes` in `proxy.ts`. The middleware handles the redirect before any React code runs.

**Warning signs:** Unauthenticated users see an error page at /cart.

### Pitfall 4: ApiError Cannot Surface InsufficientStockItem Details

**What goes wrong:** The 409 checkout response includes a list of stock-constrained items (`book_id`, `title`, `requested`, `available`), but `ApiError` only captures `body.detail` as a string. The item list is lost.

**Why it happens:** `api.ts` currently does `throw new ApiError(body.detail, res.status, body.detail)` — only the string `detail` is preserved.

**How to avoid:** Extend `ApiError` to accept an optional `data` field: `throw new ApiError(body.detail, res.status, body.data ?? body.detail)`. Then in the checkout `onError`, check `err instanceof ApiError && err.status === 409` and render `err.data.items` to show which books are short on stock.

**Warning signs:** Checkout 409 shows generic error toast with no specifics about which items have stock issues.

### Pitfall 5: Optimistic Update Leaves Total_Price Stale

**What goes wrong:** The cart summary shows the pre-removal total price for a moment after removing an item.

**Why it happens:** `CartResponse.total_price` is computed server-side and is `readonly` in TypeScript. The optimistic update sets items to the filtered list but can't set a new `total_price` via TypeScript assignment.

**How to avoid:** Cast the optimistic cart update: when building the optimistic `CartResponse`, compute a local `total_price` string:

```typescript
const newItems = previousCart.items.filter((item) => item.id !== itemId)
const newTotalPrice = newItems
  .reduce((sum, item) => sum + parseFloat(item.book.price) * item.quantity, 0)
  .toFixed(2)
queryClient.setQueryData<CartResponse>(CART_KEY, {
  items: newItems,
  total_items: newItems.reduce((sum, item) => sum + item.quantity, 0),
  total_price: newTotalPrice,
} as CartResponse)
```

**Warning signs:** Cart total flickers or shows wrong amount after removing an item, then corrects on server sync.

### Pitfall 6: BookDetail ActionButtons is a Server Component

**What goes wrong:** Trying to add a `useMutation` call directly to `ActionButtons.tsx` (currently a Server Component) causes a build error.

**Why it happens:** `ActionButtons.tsx` has no `'use client'` directive. Client hooks like `useMutation` and `useSession` can only be called in Client Components.

**How to avoid:** Convert `ActionButtons.tsx` to a Client Component by adding `'use client'` at the top. It currently receives `inStock: boolean` as a prop — keep that prop, just add the client directive and wire up the mutation.

**Warning signs:** `Error: Hooks can only be called inside of a body of a function component` at build time.

### Pitfall 7: Catalog BookCard is a Server Component — Cart Icon Requires Client Component

**What goes wrong:** Adding cart icon button to `BookCard.tsx` (currently a pure Server Component) with `onClick` handler causes a build error.

**Why it happens:** `BookCard.tsx` has no `'use client'` directive.

**How to avoid:** Create a new `BookCardWithCart.tsx` client wrapper that renders the `BookCard` content plus the cart icon, OR convert `BookCard.tsx` to a client component. Given BookCard uses `next/image` and `next/link` (both work in client components), converting is cleaner than wrapping.

**Warning signs:** `onClick` prop on Server Component causes build error.

## Code Examples

Verified patterns from official sources and established project conventions:

### useQuery for Cart (with auth)
```typescript
// Source: established pattern from Phase 20 (useSession) + Phase 19 (TanStack Query setup)
const { data: session } = useSession()
const accessToken = session?.accessToken ?? ''

const { data: cart, isLoading } = useQuery({
  queryKey: ['cart'],
  queryFn: () => fetchCart(accessToken),
  enabled: !!accessToken,
  staleTime: 30_000,
})
```

### useMutation for Add to Cart (with optimistic badge update)
```typescript
// Source: TanStack Query v5 docs — optimistic updates pattern
const queryClient = useQueryClient()
const router = useRouter()

const addToCart = useMutation({
  mutationFn: ({ bookId }: { bookId: number }) =>
    addCartItem(accessToken, bookId),
  onMutate: async ({ bookId: _ }) => {
    await queryClient.cancelQueries({ queryKey: CART_KEY })
    const previousCart = queryClient.getQueryData<CartResponse>(CART_KEY)
    // Optimistically increment total_items for badge
    if (previousCart) {
      queryClient.setQueryData<CartResponse>(CART_KEY, {
        ...previousCart,
        total_items: previousCart.total_items + 1,
      } as CartResponse)
    }
    return { previousCart }
  },
  onError: (err, _vars, context) => {
    if (context?.previousCart) {
      queryClient.setQueryData(CART_KEY, context.previousCart)
    }
    if (err instanceof ApiError && err.status === 409) {
      toast.error('Already in cart', {
        action: { label: 'View Cart', onClick: () => router.push('/cart') },
      })
    } else {
      toast.error('Failed to add to cart')
    }
  },
  onSuccess: (_data, _vars) => {
    toast.success(`Added to cart`)
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: CART_KEY })
  },
})
```

### Checkout Mutation with Router Redirect
```typescript
const router = useRouter()

const checkoutMutation = useMutation({
  mutationFn: () => checkout(accessToken),
  onSuccess: (order) => {
    // Clear local cart cache optimistically
    queryClient.setQueryData(CART_KEY, { items: [], total_items: 0, total_price: '0.00' })
    router.push(`/orders/${order.id}?confirmed=true`)
  },
  onError: (err) => {
    if (err instanceof ApiError && err.status === 409) {
      toast.error('Some items are out of stock. Please update your cart.')
    } else if (err instanceof ApiError && err.status === 402) {
      toast.error('Payment failed. Please try again.')
    } else if (err instanceof ApiError && err.status === 422) {
      toast.error('Your cart is empty.')
    } else {
      toast.error('Checkout failed. Please try again.')
    }
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: CART_KEY })
  },
})
```

### Sonner Toast with Action Link (already installed v2.0.7)
```typescript
import { toast } from 'sonner'

// Simple toast
toast.success('Added to cart')
toast.error('Failed to remove item. Please try again.')

// Toast with action (for "Already in cart" → view cart)
toast.error('Already in cart', {
  description: 'This book is already in your cart.',
  action: {
    label: 'View Cart',
    onClick: () => router.push('/cart'),
  },
})
```

### Dialog for Checkout Confirmation (shadcn/ui — needs install)
```typescript
// After: npx shadcn@latest add dialog
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

// Usage in CheckoutDialog component:
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Place Order</DialogTitle>
      <DialogDescription>
        Confirm your order for ${totalPrice}?
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
      <Button onClick={handleConfirm} disabled={checkoutMutation.isPending}>
        {checkoutMutation.isPending ? 'Placing...' : 'Place Order'}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

## Backend API Contract (Confirmed from Source)

All endpoints are verified from `/backend/app/cart/router.py`, `/backend/app/orders/router.py`, and `/frontend/src/types/api.generated.ts`.

### Cart Endpoints

| Method | Path | Auth | Request Body | Success | Error Codes |
|--------|------|------|--------------|---------|-------------|
| GET | /cart | Bearer | — | 200 CartResponse | 401 (not authenticated) |
| POST | /cart/items | Bearer | `{book_id, quantity=1}` | 201 CartItemResponse | 409 CART_BOOK_OUT_OF_STOCK, 409 CART_ITEM_DUPLICATE, 404 BOOK_NOT_FOUND |
| PUT | /cart/items/{id} | Bearer | `{quantity}` | 200 CartItemResponse | 404 CART_ITEM_NOT_FOUND, 403 CART_ITEM_FORBIDDEN |
| DELETE | /cart/items/{id} | Bearer | — | 204 No Content | 404 CART_ITEM_NOT_FOUND, 403 CART_ITEM_FORBIDDEN |

### Order Endpoints

| Method | Path | Auth | Request Body | Success | Error Codes |
|--------|------|------|--------------|---------|-------------|
| POST | /orders/checkout | Bearer | `{force_payment_failure=false}` | 201 OrderResponse | 422 ORDER_CART_EMPTY, 409 ORDER_INSUFFICIENT_STOCK, 402 ORDER_PAYMENT_FAILED |
| GET | /orders/{id} | Bearer | — | 200 OrderResponse | 404 ORDER_NOT_FOUND |

### Key TypeScript Types (from api.generated.ts)

```typescript
// CartResponse — what GET /cart returns
type CartResponse = {
  items: CartItemResponse[]
  readonly total_items: number       // sum of quantities
  readonly total_price: string       // decimal string e.g. "49.98"
}

// CartItemResponse — each item in cart
type CartItemResponse = {
  id: number
  book_id: number
  quantity: number
  book: {
    id: number
    title: string
    author: string
    price: string        // decimal string e.g. "12.99"
    cover_image_url: string | null
  }
}

// OrderResponse — what /orders/checkout and /orders/{id} return
type OrderResponse = {
  id: number
  status: string       // "CONFIRMED"
  created_at: string   // ISO datetime string
  items: OrderItemResponse[]
  readonly total_price: string
}

type OrderItemResponse = {
  id: number
  book_id: number | null       // null if book was deleted after purchase
  quantity: number
  unit_price: string           // price at time of purchase
  book: { id: number; title: string; author: string } | null
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| localStorage cart | Server cart via API | This project always used server | No offline cart, correct cross-device behavior |
| Redux for cart state | TanStack Query + optimistic updates | TQ v5 (2023) | No separate action/reducer boilerplate |
| `variables` approach for optimistic | `onMutate`/`onError`/`onSettled` pattern | TQ v5 | Both work; onMutate is more flexible for complex rollbacks |

**Note:** TanStack Query v5 introduced a `variables`-based approach as an alternative to `onMutate` for simpler optimistic updates. For cart (where rollback needs to restore full item list), `onMutate` is the correct choice.

## Open Questions

1. **ApiError body extension for InsufficientStockItems**
   - What we know: 409 ORDER_INSUFFICIENT_STOCK returns `{detail: str, items: [{book_id, title, requested, available}]}`
   - What's unclear: `ApiError` in `api.ts` only stores `detail: string`. The items list is lost.
   - Recommendation: Extend `ApiError` to accept `data?: unknown` carrying the full body. Low risk change — it's a new optional field.

2. **Cart page: full server component shell vs. full client component**
   - What we know: Catalog page uses a server shell with async data fetch. Cart data requires auth (session), so server-side fetch needs `await auth()`.
   - What's unclear: Whether to fetch cart server-side (using `await auth()` → `session.accessToken` → `fetchCart`) for initial SSR, or render a client-side loading skeleton immediately.
   - Recommendation: Use a client-side pattern (render page.tsx as a thin server shell, CartPageContent is `'use client'`). Cart is personalized/dynamic — ISR doesn't apply. This avoids token passing complexity and matches the pattern of client-side cart state that updates optimistically.

3. **BookCard conversion: server → client component**
   - What we know: `BookCard.tsx` is a pure Server Component. Adding cart icon with onClick requires 'use client'.
   - What's unclear: Whether to convert the whole BookCard or create a `BookCardActions` overlay client component.
   - Recommendation: Convert `BookCard.tsx` to a Client Component entirely. It uses `next/image` and `next/link` (both work in client components). The SEO benefit of SSR doesn't apply to interactive cards. The simpler architecture wins.

## Sources

### Primary (HIGH confidence)
- Codebase: `/backend/app/cart/router.py` + `schemas.py` — verified API contract and error codes
- Codebase: `/backend/app/orders/router.py` + `schemas.py` — verified checkout and order detail contract
- Codebase: `/frontend/src/types/api.generated.ts` — verified TypeScript types for all cart/order schemas
- Codebase: `/frontend/src/components/layout/UserMenu.tsx` — established mounted-guard pattern
- Codebase: `/frontend/src/components/providers.tsx` — confirmed QueryClient, Toaster, SessionProvider configuration
- Codebase: `/frontend/src/proxy.ts` — confirmed protected routes, /cart needs to be added
- Codebase: `/frontend/src/lib/api.ts` — confirmed apiFetch pattern and ApiError class
- Codebase: `/frontend/src/app/books/[id]/_components/ActionButtons.tsx` — confirmed disabled placeholder to wire up
- Package: `/frontend/package.json` — confirmed all installed packages and versions

### Secondary (MEDIUM confidence)
- WebSearch: TanStack Query v5 optimistic updates — `onMutate`/`cancelQueries`/`setQueryData`/`onError` rollback pattern — confirmed with official docs URL `https://tanstack.com/query/v5/docs/react/guides/optimistic-updates`

### Tertiary (LOW confidence)
None — all critical claims verified from codebase or official sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed from package.json; shadcn dialog/separator identified as missing from ui/ dir
- Architecture: HIGH — patterns derived from existing codebase conventions (UserMenu, providers, proxy, catalog page) with direct code reading
- API contract: HIGH — read directly from backend source and generated TypeScript types
- Optimistic updates: MEDIUM-HIGH — pattern confirmed from official TQ v5 docs URL; specific code for cart is extrapolated from the general pattern
- Pitfalls: HIGH — most derived from reading existing code and identifying what will break (ActionButtons is Server Component, /cart not protected, hydration issue)

**Research date:** 2026-02-27
**Valid until:** 2026-03-29 (stable libraries; TanStack Query v5 and Next.js 16 are stable)
