---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Customer Storefront
status: unknown
last_updated: "2026-02-28T06:27:52.255Z"
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 20
  completed_plans: 20
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Customer Storefront
status: unknown
last_updated: "2026-02-27T19:45:52.086Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 17
  completed_plans: 17
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Customer Storefront
status: unknown
last_updated: "2026-02-27T17:56:41.454Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 15
  completed_plans: 15
---

---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Customer Storefront
status: active
last_updated: "2026-02-27T17:48:48Z"
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 16
  completed_plans: 15
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** v3.0 Customer Storefront — Phase 25: Reviews and Ratings

## Current Position

Phase: 25 of 25 (Reviews) — NEXT
Plan: Phase 24 complete (3/3 plans: hooks, wishlist page + account, human verification)
Status: Active
Last activity: 2026-02-28 — Completed 24-03 (human verification — all WISH and PREB requirements approved)

Progress: [███████░░░] 93% (7/7 phases started, Phase 24 fully verified)

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: ~7 min
- Total execution time: ~69 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19 (complete) | 3 | ~41 min | ~14 min |
| 20 (complete) | 3 | ~28 min | ~9 min |
| 21 (complete) | 4/4 | ~51 min | ~13 min |
| 22 (complete) | 5/5 | ~11 min | ~2 min |

*Updated after each plan completion*
| Phase 22 P04 | 102 | 2 tasks | 4 files |
| Phase 22 P05 | ~2min | 1 task (human verify) | 0 files |

## Accumulated Context

### Decisions

Recent decisions affecting v3.0 work:

- [v3.0 Roadmap]: Next.js 15 App Router with NextAuth.js v5 as JWT bridge to FastAPI — no BFF proxy, FastAPI is auth authority
- [v3.0 Roadmap]: Flat monorepo (no Turborepo) — `backend/` Python + `frontend/` Next.js, no shared JS packages
- [v3.0 Roadmap]: openapi-typescript v7 + openapi-fetch for zero-runtime-cost typed API client auto-generated from FastAPI `/openapi.json`
- [v3.0 Roadmap]: TanStack Query v5 for server state; Zustand v5 context-provider pattern for cart display state (SSR-safe)
- [19-01]: CORSMiddleware uses explicit ALLOWED_ORIGINS (not wildcard) — required for allow_credentials=True; includes both localhost:3000 and 127.0.0.1:3000
- [19-01]: CORSMiddleware registered last in add_middleware() — FastAPI reverse execution order makes it run first (CORS before session)
- [19-02]: QueryClient created in useState factory pattern — prevents shared state across SSR requests
- [19-02]: openapi-typescript v7 generates types from live FastAPI /openapi.json — backend must be running to regenerate types
- [19-02]: Next.js 16 --yes creates flat layout (no src/) — restructured to src/ and updated tsconfig @/* and components.json paths
- [19-03]: ThemeToggle uses useEffect/useState mounted guard to return null before hydration — prevents SSR/CSR theme flicker (required next-themes pattern)
- [19-03]: MobileNav Sheet open state controlled internally — enables programmatic close on link click
- [19-03]: 404 page must be explicitly themed with shadcn/ui tokens — default Next.js not-found does not inherit ThemeProvider context
- [20-01]: POST /auth/google/token new endpoint (not calling existing /auth/google): existing Authlib redirect flow conflicts with NextAuth's own OAuth state management
- [20-01]: jose decodeJwt (not verify) for FastAPI JWT claims extraction: verification is FastAPI's responsibility; decoding avoids extra /me API call
- [20-01]: Concurrent-refresh guard with module-level refreshPromise: prevents race condition when multiple server components hit jwt callback simultaneously during token expiry window
- [20-01]: Credentials authorize returns null on 4xx failures (not throw): per NextAuth v5 spec — throw triggers 500, null triggers CredentialsSignin error with clean UX
- [20-02]: Suspense boundary required around components using useSearchParams() in Next.js static builds — caught by npm run build, not TypeScript
- [20-02]: proxy.ts uses named export const proxy = auth(...) (not export default): Next.js 16 requires named proxy export per pitfall documentation
- [20-02]: UserMenu as separate 'use client' component with mounted guard: keeps Header as server component, prevents SSR/CSR hydration mismatch
- [20-02]: AuthGuard as child component inside SessionProvider: calls useSession() to watch session.error and trigger signOut on RefreshTokenError
- [21-01]: avg_rating sort uses LEFT JOIN subquery on reviews with nulls_last() — books without reviews sort last in both asc and desc directions
- [21-01]: Price range added as backend params (min_price/max_price) — client-side filtering rejected as unviable at scale
- [21-01]: BookCard is a pure server component (no 'use client') — uses next/link and next/image for SSR performance
- [21-01]: remotePatterns uses https://** (permissive) — covers any future cover image CDN without config changes
- [21-02]: SearchControls and Pagination wrapped in Suspense on catalog page — useSearchParams() requires Suspense boundary for Next.js static build
- [21-02]: Sort encoded as composite key (price_asc, price_desc, avg_rating) in Select, mapped to sort+sort_dir params at update time
- [21-02]: BookGrid as async server component — fetches popular books server-side on empty results without client waterfall
- [21-03]: React.cache() wraps fetchBook so generateMetadata and page component share a single cached request — avoids double fetch
- [21-03]: ActionButtons are disabled placeholders — Phase 22 (cart) and Phase 24 (wishlist) will enable them
- [21-03]: MoreInGenre fetches size=7, filters current book, slices to 6 — avoids separate count query
- [21-04]: All CATL-01 through CATL-07 requirements verified by human in browser — Phase 21 approved complete; Phase 22 (cart) ready to begin
- [22-01]: CartBadge uses mounted guard (useEffect/useState) to prevent SSR/CSR hydration mismatch — same pattern as UserMenu
- [22-01]: useCart hook exported from cart.ts — all mutations share CART_KEY so CartBadge and cart page stay in sync via TanStack Query cache
- [22-01]: recomputeTotals helper uses parseFloat/toFixed(2) to recompute price strings optimistically without backend round-trip
- [22-01]: ApiError.data carries full response body — enables 409 ORDER_INSUFFICIENT_STOCK to expose items[] for per-item stock error display
- [22-02]: ActionButtons.tsx converted to 'use client' — accepts bookId + inStock props, calls useCart().addItem.mutate on click
- [22-02]: BookCard.tsx converted to 'use client' — cart icon button is absolute-positioned outside the Link to prevent navigation on cart click
- [22-02]: Unauthenticated add-to-cart: toast.error + router.push('/login') in click handler — consistent pattern across both components
- [22-02]: BookCard cart icon: opacity-0 md:group-hover:opacity-100 on desktop, always visible mobile — per CONTEXT.md hover decision
- [Phase 22-03]: removeItem.mutate({ itemId }) — hook's mutationFn destructures { itemId }, not a bare number
- [Phase 22-03]: CartSummary renders sticky sidebar card (desktop) + fixed bottom bar (mobile <lg); CartPageContent adds pb-20 lg:pb-0 to prevent content overlap
- [Phase 22-04]: CheckoutDialog is a pure controlled component — open/onOpenChange/isPending state owned by CartPageContent, dialog is stateless
- [Phase 22-04]: isConfirmed passed as prop from server component (not useSearchParams) — OrderDetail stays a plain component with no client boundary needed
- [Phase 22-04]: Dialog closes on both isSuccess and isError via useEffect — success triggers router.push redirect; error surfaces toast from useCart hook
- [Phase 22-05]: All SHOP-01 through SHOP-10 requirements verified by human in browser — Phase 22 approved complete; Phase 23 (orders and account) ready to begin
- [23-01]: fetchOrders() lives in orders.ts (not cart.ts) to keep order-list concerns separate from fetchOrder (singular) in cart.ts — avoids breaking existing /orders/[id]/page.tsx import
- [23-01]: /orders page wraps fetchOrders in try/catch returning [] on error — shows empty state gracefully rather than crashing with 500 if backend down
- [23-01]: Client-side pagination in OrderHistoryList — order history is a bounded user-owned list; simpler than URL-param pagination with no router/searchParams dependency
- [23-02]: Human approval of SHOP-07 and SHOP-08 confirms Phase 23 implementation is production-ready
- [24-01]: useMutation explicit generic type parameters required when mutationFn returns union type (WishlistItemResponse | void) — TypeScript loses context type inference without explicit TContext generic
- [24-01]: Pre-book button replaces (not supplements) Add to Cart when inStock is false — cleaner conditional render, no disabled state needed
- [24-01]: Heart button on BookCard uses e.preventDefault()+e.stopPropagation() — prevents Link navigation, matching cart button established pattern
- [24-02]: WishlistList uses wishlistQuery.data?.items ?? items pattern — SSR items render immediately, TanStack Query cache takes over after hydration
- [24-02]: PrebookingsList uses useState(prebooks) for optimistic removal — server-seeded list, no query subscription needed
- [24-02]: Pre-bookings rendered inline on /account page (not separate route) — bounded list, account hub is natural home
- [24-03]: Human approved all 8 requirements (WISH-01 through WISH-04, PREB-01 through PREB-04) — Phase 24 complete and production-ready

### Blockers/Concerns

- [Phase 20]: Google OAuth requires user to configure Google Cloud Console credentials and run npx auth secret — documented in 20-01-SUMMARY.md User Setup section
- [Phase 25]: Star rating selector not in shadcn/ui — evaluate community extensions vs. small custom component before phase starts

### Pending Todos

None.

## Session Continuity

Last session: 2026-02-28
Stopped at: Completed 24-03-PLAN.md — human verification of all WISH and PREB requirements approved
Resume file: None
