# Feature Research

**Domain:** Bookstore E-Commerce — v3.0 Next.js Customer Storefront
**Researched:** 2026-02-27
**Confidence:** HIGH for table stakes (well-established across Amazon, Shopify, major book retailers); MEDIUM for Next.js-specific rendering strategy recommendations (verified via official docs + community); LOW for specific conversion rate claims (vendor-reported figures)

> **Scope note:** The FastAPI backend (v1.0–v2.1) already provides full API coverage:
> catalog CRUD, JWT auth (email + Google/GitHub OAuth), FTS with filters, cart,
> checkout (mock payment), order history, wishlist, pre-booking, email notifications,
> verified-purchase reviews with ratings, and admin analytics/moderation.
> This file focuses EXCLUSIVELY on the new v3.0 frontend features: what a customer-facing
> Next.js 15 storefront must expose to users, how each feature should behave in the
> browser, and what complexity that implies for implementation.
> Admin dashboard UI is deferred to v3.1+.

---

## Feature Landscape

### Table Stakes

Features customers expect from any e-commerce storefront in 2026. Missing one makes the product feel broken or untrustworthy. These are the baseline for a shippable storefront.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Catalog browsing with cover images | Every bookstore — Amazon, Barnes & Noble, Booktopia — shows a book grid/list with cover, title, author, price, and stock status. No cover image = feels unfinished. | LOW | RSC: Server-rendered grid page. Paginate with page-based navigation (not infinite scroll — shoppers backtrack and bookmark; pagination is universally preferred for catalog UX per Baymard Institute). TanStack Query for client-side page transitions. Tailwind grid layout with shadcn Card. |
| Book detail page with ratings display | Users navigate to a detail page before purchasing. Seeing average rating, review count, stock status, and description is non-negotiable — it is the main purchase-decision screen. | LOW-MED | RSC page: `generateMetadata()` for SEO, JSON-LD structured data (`Book` schema) for Google rich results. Display avg_rating + review count fetched from backend. "In Stock / Out of Stock / Pre-book available" state must be immediately visible. |
| Full-text search with filters | Users search by title, author, or genre. Filter by genre and price range. No search = no product discovery beyond browsing. | MEDIUM | Client component: search input triggers debounced query, filter state managed in URL search params (enables direct linking and back-button). TanStack Query fetches results. Render server-side on initial load, hydrate client. Debounce: 300ms. |
| Email + password authentication | Sign up, log in, log out. Mandatory. Without it, no cart, no orders, no wishlist, no reviews. | MEDIUM | NextAuth.js v5 credentials provider. JWT strategy (matches backend's JWT-based tokens). Login page with Zod validation. Error states: "invalid credentials", "email already registered". On login success, store access token in session, refresh token in httpOnly cookie. |
| Google OAuth login | Most major storefronts offer at least one social login. Users expect "Sign in with Google" on any consumer-facing product in 2026. Reduces friction significantly — no password to remember. | MEDIUM | NextAuth.js v5 GoogleProvider. Backend `/auth/google` endpoint already exists. The frontend OAuth flow must send the Google token to the backend, receive backend JWTs, and store them in the NextAuth session. The challenge is the custom OAuth handoff (Google → NextAuth → FastAPI → store JWT) — this is the highest-complexity auth subtask. |
| Shopping cart (add, update quantity, remove) | Cart is the core of the purchase flow. Users add books, adjust quantity, remove items. Cart state must persist across page navigations. | MEDIUM | Cart state lives server-side (existing backend `/cart` endpoints). TanStack Query mutations for add/update/remove. Optimistic updates on quantity changes for responsiveness. Cart count in navbar header driven by TanStack Query cache. No client-only localStorage cart — server is source of truth. |
| Checkout flow | Complete a purchase. Show cart summary, confirm (mock) payment, see order confirmation. Without checkout, the product is not a store. | MEDIUM | Multi-step or single-page checkout. Mock payment = no real payment form, just a "Place Order" button. Show order total, shipping address field (or skip for digital goods), confirmation screen with order ID. POST to `/orders/checkout`. On success, invalidate cart cache, redirect to order confirmation page. |
| Order history page | Users expect to see past orders. Required for trust — "What did I buy? When? For how much?" | LOW | RSC page fetching `/orders` with JWT auth. List: date, order total, book titles, status. Click through to individual order detail. Price-at-purchase snapshots already stored in backend. |
| Authentication-gated routes | Cart, checkout, orders, wishlist, and reviews must require login. Accessing them without auth redirects to sign-in with a `callbackUrl`. | LOW | Next.js middleware with NextAuth session check. Redirect to `/auth/signin?callbackUrl=<original>`. After login, redirect back. Standard NextAuth.js middleware pattern. |
| Responsive layout (mobile-first) | Mobile traffic represents 60%+ of e-commerce visits. A site that breaks on mobile loses more than half its audience. Mobile optimization is table stakes in 2026, not a differentiator. | LOW | Tailwind CSS responsive utilities (`sm:`, `md:`, `lg:` breakpoints). shadcn/ui components are built responsive. Navbar: hamburger menu on mobile. Grid: 1 col mobile → 2 col tablet → 3-4 col desktop. |
| Loading and error states | Every data-fetching page needs a loading skeleton and an error boundary. Without these, network delays produce blank screens. | LOW | shadcn Skeleton component for loading states. Next.js `loading.tsx` and `error.tsx` per route segment. TanStack Query `isLoading` / `isError` states on client components. |
| Sign out | Users must be able to log out from any authenticated page. | LOW | NextAuth `signOut()` in navbar. Clears session + cookies. Redirects to homepage. |

### Differentiators

Features beyond the bare minimum that meaningfully improve the customer experience. Not universally expected but appreciated when present. They differentiate a polished storefront from a bare-bones one.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Wishlist management | Save books for later. Major book retailers (Amazon, Goodreads, The Book Depository) all offer wishlists. Users who wishlist are higher-intent buyers who return. Pre-booking and out-of-stock handling make this particularly useful in this system. | MEDIUM | Auth-gated. Heart/bookmark icon on book card and detail page. Optimistic toggle (instant UI feedback, roll back on error). TanStack Query mutation against `/wishlist/{book_id}`. Dedicated `/wishlist` page listing saved books with quick "Add to Cart" from wishlist. |
| Pre-booking for out-of-stock books | When a book is out of stock, let users reserve their spot in the queue. Backend already handles email notification on restock. This is a genuine differentiator — most small storefronts just say "out of stock" with no recourse. | MEDIUM | On book detail page: if `stock_quantity == 0`, replace "Add to Cart" with "Pre-book". Show waitlist count ("N people waiting") if exposed by the API. Allow cancellation from a pre-bookings section in the account area. Surface backend restock notification as a confirmation message: "You'll get an email when this book is back." |
| Verified-purchase reviews with star ratings | Displaying reviews on the book detail page builds trust. Only users who purchased can write reviews (already enforced by backend). Shoppers make better decisions with social proof. | MEDIUM | Read-only review display on book detail: average star rating (visual stars, not just number), review count, chronological list of reviews with reviewer name, rating, text, date. Write/edit/delete review form: visible only if user has purchased this book. 1–5 star interactive selector (shadcn does not ship a native star component — use a community extension or build a small custom one). Edit in-place with optimistic update. |
| Book detail page SEO (structured data + Open Graph) | Public catalog pages can rank in search engines and render well when shared on social media. A bare metadata object is table stakes; rich structured data (`Book` JSON-LD schema) is a differentiator. | LOW | `generateMetadata()` returning title, description, Open Graph image. JSON-LD `Book` schema (`name`, `author`, `isbn`, `aggregateRating`). Statically rendered or ISR-cached book pages. |
| URL-persisted search/filter state | Shareable, bookmarkable search results. "Search for fantasy books under $20" produces a URL that can be shared or bookmarked and reloads with the same results. Most basic implementations use component state that resets on navigation. | LOW-MED | Manage filter state in URL search params via `useSearchParams` + `useRouter`. On filter change, call `router.replace()`. On load, initialize filter state from params. Enables back-button navigation through filter history. |
| Optimistic cart updates | Cart interactions (add, remove, quantity change) feel instant because the UI updates before the server response. If the server rejects the mutation, the UI rolls back with an error toast. | LOW-MED | TanStack Query `useMutation` with `onMutate` (set optimistic state), `onError` (rollback), `onSettled` (invalidate cache). shadcn Toast for error feedback. Already part of TanStack Query's documented pattern. |
| Order confirmation page with order details | After checkout, show a clear confirmation: "Order #1234 confirmed. Books will be ready in X days." with the full order summary. Some storefronts just redirect to order history. A dedicated confirmation page is more reassuring. | LOW | Dedicated `/orders/[id]/confirmation` page. Fetch order by ID with auth. Show items, prices, total, and a "View all orders" link. |
| Account page (profile + pre-bookings view) | Centralized area where users can see their active pre-bookings and manage their account. Provides a single destination for account management. | MEDIUM | Auth-gated `/account` page. Sections: active pre-bookings with cancel action, link to order history, link to wishlist. No profile editing required for v3.0 (backend does not expose PATCH /me endpoint in scope). |

### Anti-Features

Features to explicitly not build in v3.0. These are commonly requested but create problems — either out-of-scope for the milestone, actively harmful to UX, or premature.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Forced account creation before cart | Forcing registration before adding to cart is a well-documented conversion killer. 23–28% of cart abandonments are caused by forced registration (Baymard Institute research). | Allow browsing and adding to cart as a guest concept, OR clearly surface the login prompt only at checkout, with a prominent "Guest checkout" path if the backend ever supports it. For v3.0: show a clear, non-intrusive "Sign in to save your cart" prompt rather than a hard block on cart viewing. |
| Client-side-only cart (localStorage) | A localStorage cart breaks when users switch devices, clears on browser data wipe, and creates sync nightmares with the backend. | Server is source of truth. All cart operations go through the backend API. TanStack Query caches server state locally for responsiveness. |
| Infinite scroll on catalog pages | Infinite scroll is problematic for shop browsing: users cannot bookmark their position, back-navigation loses scroll position, footers become inaccessible, and shoppers need to compare items across positions (they backtrack). Pagination wins for catalog UX. | Standard page-based pagination with visible page numbers. "Load more" button is acceptable as a compromise (preserves footer access). True infinite scroll is an anti-pattern for catalog browsing. |
| Real-time stock count polling | Polling `/books/{id}` every few seconds to show live stock counts creates unnecessary API load and provides minimal user value for a low-traffic bookstore. | Show stock status (in stock / out of stock / low stock) fetched on page load. Revalidate on cart operations (when it actually matters). No continuous polling. |
| Intrusive popups (email capture, newsletter) | Entry popups, exit-intent popups, and mid-browse modals are documented UX harms — higher bounce rates, frustration, and cart abandonment. NN/g research: popups interrupt task completion and force context switching. | No popups for v3.0. If newsletter signup is desired later, use an unobtrusive footer form or an in-page section at natural pause points (e.g., after order confirmation). |
| Admin dashboard UI | Explicitly deferred to v3.1+ in PROJECT.md. Admin UI is a separate concern requiring different layouts, access control, and components. Building it now expands scope without customer benefit. | Admins use the API directly (Postman/curl) or await v3.1. |
| GitHub OAuth on frontend | PROJECT.md explicitly defers GitHub OAuth to post-v3.0. Google + email are sufficient social login coverage for v3.0. | Email + Google OAuth covers the vast majority of users. GitHub OAuth can be added in a minor release without changing auth architecture. |
| Review helpfulness voting ("Was this helpful?") | PROJECT.md explicitly defers this until review volume justifies it. Building a voting system without sufficient reviews to vote on is infrastructure without a use case. | Display reviews chronologically. Sort by most recent (default). Add helpfulness voting only when review volume is sufficient to make ranking meaningful. |
| Real payment integration (Stripe, etc.) | PROJECT.md constraint: mock payment only. Real payment adds PCI compliance surface, webhook handling, idempotency keys, failed payment retry logic, and refund flows — a separate milestone's worth of work. | Mock checkout: "Place Order" button sends POST to `/orders/checkout`. Show order confirmation. Clearly label as "Demo — no real payment processed" in UI. |
| Recommendation engine ("You might also like") | PROJECT.md out of scope. Requires sufficient transaction data for meaningful recommendations and a separate algorithmic layer. | Surface pre-booking demand and review ratings as organic signals of popularity. "Highly rated" and "In demand" badges on book cards are sufficient discovery aids without a full recommendation system. |
| Client-side search (Fuse.js, etc.) | The backend already provides full-text search via PostgreSQL FTS. Rebuilding search logic on the client wastes effort, diverges from backend data, and cannot scale to catalog growth. | Use the existing `GET /books?search=` endpoint. TanStack Query caches results. The backend is the search engine. |

---

## Feature Dependencies

```
[NextAuth.js session (JWT stored in session)]
    └──required by──> [All auth-gated routes] (cart, checkout, orders, wishlist, reviews, account)
    └──required by──> [Google OAuth flow] (custom callback to backend /auth/google)
    └──required by──> [TanStack Query authenticated fetches] (attach Authorization header)

[Auth (email + Google OAuth)]
    └──prerequisite for──> [Cart operations]
    └──prerequisite for──> [Checkout]
    └──prerequisite for──> [Order history]
    └──prerequisite for──> [Wishlist management]
    └──prerequisite for──> [Review creation/editing]
    └──prerequisite for──> [Pre-booking]
    └──prerequisite for──> [Account page]

[Cart management]
    └──prerequisite for──> [Checkout flow]
    └──prerequisite for──> [Cart count in navbar] (shared cache)

[Checkout flow]
    └──prerequisite for──> [Order confirmation page]
    └──enables──> [Verified-purchase review gate] (backend checks order history)

[Book detail page]
    └──surfaces──> [Add to Cart button]
    └──surfaces──> [Add to Wishlist button]
    └──surfaces──> [Pre-book button] (conditional: when stock == 0)
    └──surfaces──> [Reviews section] (read + write)
    └──surfaces──> [Average rating display]

[Order history]
    └──prerequisite for──> [Review eligibility check] (have they purchased this book?)
    └──surfaces──> [Link to order confirmation page]

[Catalog browsing / search]
    └──entry point for──> [Book detail page]
    └──entry point for──> [Add to Wishlist] (from grid card)

[openapi-typescript generated types]
    └──required by──> [All API calls] (type-safe request/response contracts)
    └──dependency on──> [FastAPI OpenAPI spec at /openapi.json]

[Wishlist management]
    └──surfaces──> [Pre-booking option] (wishlist item that's now out-of-stock → pre-book CTA)

[Pre-booking]
    └──shown in──> [Account page pre-bookings section]
    └──cancellable from──> [Account page]
```

### Dependency Notes

- **JWT handoff is the critical integration point:** NextAuth.js v5 sessions must store the FastAPI-issued JWT (not the NextAuth-generated JWT). The credentials and OAuth providers must call the backend's `/auth/login` or `/auth/google` endpoint and extract the `access_token` and `refresh_token` from the response. All TanStack Query fetches attach this `access_token` as `Authorization: Bearer <token>`.
- **Token refresh on expiry:** The backend issues short-lived access tokens (as per JWT pattern in PROJECT.md). The frontend must handle 401 responses by using the refresh token to get a new access token before retrying. This is most cleanly done in an Axios interceptor or a fetch wrapper — not per-component.
- **`is_active` check means immediate lockout:** If an admin deactivates a user account, the backend returns 401 on the next authenticated request. The frontend must handle 401 → clear session → redirect to login, even mid-session. Do not cache the `is_active` status client-side.
- **Pre-booking button conditional:** The "Pre-book" vs "Add to Cart" button state depends on `stock_quantity` returned from the book detail API. This value should not be cached aggressively — it changes after checkout events. Revalidate on focus or use a short TTL (60s) so users see updated stock on return.
- **Review write form conditional:** The review creation form should only render if the user has purchased the book. The backend enforces this at the API level, but the frontend should check proactively to avoid showing a form that will always 403. Check `GET /orders?book_id={id}` or a dedicated endpoint to determine purchase eligibility before rendering the form.
- **openapi-typescript generation step must run after backend changes:** The auto-generated types (from `GET /openapi.json`) need a `npm run generate:types` step in the monorepo. If this step is skipped after backend changes, the frontend TypeScript types will be stale and type errors will hide API contract changes.

---

## MVP Definition

### v3.0 Must Ship

All of the following constitute the v3.0 milestone deliverables. They represent full feature parity with user-facing backend endpoints.

**Foundation:**
- [ ] Monorepo restructure (`backend/` + `frontend/` directories at repo root)
- [ ] Next.js 15 app scaffolded with TypeScript, shadcn/ui, Tailwind CSS, TanStack Query
- [ ] openapi-typescript types generated from FastAPI `/openapi.json`
- [ ] NextAuth.js v5 configured with credentials + Google OAuth providers
- [ ] JWT session storage with token refresh handling
- [ ] Authenticated route middleware

**Catalog & Discovery:**
- [ ] Home page / catalog browse with paginated book grid (cover, title, author, price, stock status)
- [ ] Search page with full-text search and genre/price filters (URL-persisted state)
- [ ] Book detail page (description, price, stock status, average rating, review count)
- [ ] `generateMetadata()` + JSON-LD structured data on book detail pages

**Auth Flows:**
- [ ] Sign up (email + password) with validation
- [ ] Sign in (email + password)
- [ ] Sign in with Google OAuth (custom NextAuth → FastAPI handoff)
- [ ] Sign out from any page
- [ ] Protected route redirect to sign-in with callbackUrl

**Cart & Checkout:**
- [ ] Add to cart from book card and book detail page
- [ ] Cart page (view items, update quantity, remove items, cart total)
- [ ] Checkout page (order summary + "Place Order" button)
- [ ] Order confirmation page (order ID, items, total)
- [ ] Cart count badge in navbar (updates on cart changes)

**Order History:**
- [ ] Order history list page (date, total, items summary)
- [ ] Individual order detail page (full item list, price snapshots, status)

**Wishlist:**
- [ ] Toggle wishlist from book card and detail page (optimistic)
- [ ] Wishlist page (saved books with "Add to Cart" and "Remove from Wishlist")

**Reviews:**
- [ ] Read-only reviews section on book detail page (star display, reviewer, text, date)
- [ ] Write review form (visible only after purchase) with 1–5 star selector and optional text
- [ ] Edit own review (in-place, pre-populated)
- [ ] Delete own review with confirmation

**Pre-booking:**
- [ ] "Pre-book" button on out-of-stock book detail page
- [ ] Cancel pre-booking from account area
- [ ] Active pre-bookings list on account page

**Account:**
- [ ] Account page: active pre-bookings section
- [ ] Account page: links to order history and wishlist

### Add After v3.0 Validation (v3.x)

- [ ] Admin dashboard UI — separate phase, v3.1+
- [ ] GitHub OAuth — can be added as a minor addition once core OAuth pattern is proven
- [ ] Review helpfulness voting — needs sufficient review volume first
- [ ] "Notify me" subscription for stock alerts beyond pre-booking (backend email already handles pre-booking; this would be a separate pattern)

### Future Consideration (v4+)

- [ ] Real payment gateway (Stripe) — separate milestone, adds PCI scope
- [ ] Recommendation engine — requires transaction data history
- [ ] Real-time stock notifications (WebSocket) — backend is email-only for restock; WebSocket would need infrastructure additions
- [ ] Progressive Web App (PWA) — offline catalog access, install prompt

---

## Rendering Strategy by Feature

The choice of rendering strategy (RSC vs. client component) is a critical implementation decision for each feature in Next.js 15.

| Page / Feature | Rendering Strategy | Rationale |
|---------------|-------------------|-----------|
| Home / catalog browse | RSC + ISR (60s revalidate) | SEO-important, mostly static, low-frequency change; ISR keeps it fresh without per-request DB calls |
| Book detail page | RSC + ISR (60s revalidate) | SEO critical (rich snippets, Open Graph); `generateMetadata()` only works in RSC; stock status may need shorter TTL |
| Search results | Client component (TanStack Query) | User-driven, interactive filters, URL-persisted params; RSC for initial server render, hydrate client for interactivity |
| Auth pages (sign in / sign up) | Client component | Form interaction, Zod validation, NextAuth session management |
| Cart page | Client component (TanStack Query) | Highly dynamic, user-specific; no ISR possible; optimistic updates require client state |
| Checkout | Client component | Form + mutation; no caching; server-side auth check in middleware |
| Order history / detail | RSC with dynamic rendering | Auth-gated, user-specific; cannot be cached; RSC is still preferred to reduce client bundle |
| Wishlist page | RSC with dynamic rendering | Auth-gated, user-specific |
| Book detail — reviews section | Split: RSC for list, client for write form | Read list is server-renderable; write form requires client interactivity |
| Account page | RSC with dynamic rendering | Auth-gated, low interactivity |
| Pre-booking actions | Client component (mutation) | Requires user interaction and optimistic feedback |
| Navbar cart count | Client component (TanStack Query) | Must update in real-time after cart mutations; shared cache |

---

## UX Behavior Specifications

Precise expected behavior for key user flows, based on established e-commerce patterns.

### Catalog Browsing
- Default sort: newest arrivals (or backend default)
- Pagination: 20 books per page, visible page numbers, prev/next
- Book card: cover image (Next.js `Image` with aspect ratio), title (truncated at 2 lines), author, price, average star rating (compact), stock badge ("In Stock" / "Low Stock" / "Out of Stock")
- Out-of-stock books remain visible (pre-booking available)

### Search
- Input: 300ms debounce before firing query
- Filter sidebar or filter row: genre (multi-select), min/max price (range inputs)
- State persisted in URL: `?q=fantasy&genre=1,3&min_price=5&max_price=25&page=2`
- Empty results: "No books found for [query]" with clear filters CTA
- Loading: skeleton cards (not spinner) during fetch

### Book Detail Page
- Hero: large cover image left, metadata right (title, author, ISBN, genre, description, price, stock status, rating)
- Rating: visual stars (filled/half/empty) + "(N reviews)" count as anchor link to reviews section
- Stock status: "In Stock", "Low Stock (N remaining)", "Out of Stock"
- Primary CTA: "Add to Cart" (in stock) or "Pre-book" (out of stock) — mutually exclusive
- Secondary CTA: "Add to Wishlist" (heart toggle, works regardless of stock)
- Reviews section: below the fold; star distribution bar chart is a differentiator, skip for v3.0 MVP
- Write review: visible below reviews list if purchase is verified; otherwise hidden

### Cart
- Line items: cover thumbnail, title, author, unit price, quantity spinner (increment/decrement), remove button, subtotal
- Quantity update: optimistic — spinner shows new value immediately; server error rolls back with toast
- Cart total: updates reactively
- Empty cart: illustration + "Browse books" CTA (not just blank)
- Checkout CTA: prominent, disabled if cart is empty

### Checkout
- Single page (not multi-step — reduces friction for mock payment)
- Show cart summary (read-only), order total
- "Place Order" button → POST `/orders/checkout` → redirect to confirmation page
- On success: invalidate cart cache (cart becomes empty)
- On failure: show error inline, do not redirect

### Order Confirmation
- Show order ID, timestamp, list of items purchased, total paid
- "Continue Shopping" and "View Order History" CTAs
- This page is the natural trigger point for "Eligible to leave a review in N days" — skip for v3.0

### Wishlist
- Toggle (add/remove) is optimistic from any page
- Wishlist page: same card as catalog but with "Add to Cart" and "Remove" actions
- If a wishlisted book goes out of stock, show "Out of Stock — Pre-book now" CTA inline on wishlist card (connects wishlist to pre-booking flow)

### Pre-booking
- Only visible when `stock_quantity == 0`
- After pre-booking: button changes to "Pre-booked — Cancel" state
- "You'll receive an email when this book is back in stock" confirmation message
- Cancel from account page or from book detail page if already pre-booked

### Reviews
- Star selector: 1–5 interactive stars (hover preview, click to set)
- Text: optional textarea (no minimum character count — backend doesn't require it)
- Submit: show loading state; on success, optimistically insert review; on 409 (already reviewed), show "You've already reviewed this book — edit your existing review"
- Edit: inline form pre-filled with existing rating + text
- Delete: confirmation dialog before deleting

### Authentication Flow
- Credentials: email + password, Zod validation on client before submit
- Google OAuth: "Continue with Google" button, standard OAuth popup or redirect
- Error states: "Invalid email or password", "Email already in use", "Google account not linked" (if backend returns specific errors)
- After sign-in: redirect to `callbackUrl` if present, otherwise to home
- Session expiry: on 401 from any authenticated request, clear session and redirect to sign-in

---

## Competitor Feature Comparison

| Feature | Amazon Books | Goodreads | Barnes & Noble | Our v3.0 |
|---------|-------------|-----------|----------------|----------|
| Catalog browse with pagination | Yes | Yes | Yes | Yes (RSC + ISR) |
| Full-text search + filters | Yes (advanced) | Yes (basic) | Yes | Yes (backend FTS) |
| Book detail with ratings | Yes | Yes | Yes | Yes |
| Email auth | Yes | Yes | Yes | Yes (NextAuth credentials) |
| Google/social OAuth | Yes | Yes (Google, Facebook) | No | Yes (Google only) |
| Guest checkout | Yes | N/A | Yes | Not in v3.0 (backend requires auth) |
| Cart with quantity management | Yes | N/A | Yes | Yes |
| Mock/demo checkout | N/A | N/A | N/A | Yes (differentiator for demo) |
| Order history | Yes | N/A | Yes | Yes |
| Wishlist | Yes | Reading lists | Yes | Yes |
| Pre-booking (out-of-stock) | Yes (backorder) | N/A | Yes (pre-order) | Yes (unique: email notification on restock) |
| Verified-purchase reviews | Yes | No (any user) | Partial | Yes (enforced by backend) |
| Star ratings on detail page | Yes | Yes | Yes | Yes |
| SEO (structured data + OG) | Yes | Yes | Yes | Yes (`Book` JSON-LD) |
| Admin dashboard | Yes | Yes | Yes | v3.1+ |

---

## Existing System Integration Points

Where new frontend features attach to the already-built FastAPI backend.

| Frontend Feature | Backend Endpoint | Notes |
|-----------------|-----------------|-------|
| Catalog browse | `GET /books?page=N&per_page=20` | RSC fetch with ISR |
| Book detail | `GET /books/{id}` | Includes avg_rating, review_count from live SQL aggregates |
| Search + filter | `GET /books?search=&genre_id=&min_price=&max_price=&page=` | FTS already implemented in backend |
| Sign up | `POST /auth/register` | Returns tokens on success |
| Sign in (email) | `POST /auth/login` | Returns access_token + refresh_token |
| Google OAuth | `POST /auth/google` (backend) + NextAuth GoogleProvider | Custom callback: send Google token to backend, store backend JWT |
| Token refresh | `POST /auth/refresh` | Called automatically on 401 |
| Cart view | `GET /cart` | Auth-gated |
| Add to cart | `POST /cart/items` | Body: `{book_id, quantity}` |
| Update cart | `PATCH /cart/items/{book_id}` | Body: `{quantity}` |
| Remove from cart | `DELETE /cart/items/{book_id}` | |
| Checkout | `POST /orders/checkout` | Triggers order confirmation email (backend BackgroundTasks) |
| Order history | `GET /orders?page=N` | Auth-gated, paginated |
| Order detail | `GET /orders/{id}` | Auth-gated |
| Wishlist view | `GET /wishlist` | Auth-gated |
| Add to wishlist | `POST /wishlist/{book_id}` | |
| Remove from wishlist | `DELETE /wishlist/{book_id}` | |
| Reviews list | `GET /books/{id}/reviews` | Public (no auth required for reading) |
| Create review | `POST /books/{id}/reviews` | Auth-gated + verified purchase check |
| Edit review | `PATCH /books/{id}/reviews/{review_id}` | Auth-gated + owner check |
| Delete own review | `DELETE /books/{id}/reviews/{review_id}` | Auth-gated + owner check |
| Pre-book | `POST /pre-bookings` | Body: `{book_id}` |
| Cancel pre-booking | `DELETE /pre-bookings/{id}` | Auth-gated + owner check |
| View pre-bookings | `GET /pre-bookings` | Auth-gated, shows user's active pre-bookings |

---

## Sources

- [Next.js 15 in eCommerce — RigbyJS](https://www.rigbyjs.com/blog/nextjs-15-in-ecommerce) — rendering strategies and server component adoption in e-commerce context (MEDIUM confidence — industry blog, aligns with Next.js official docs)
- [Vercel Next.js Commerce (GitHub)](https://github.com/vercel/commerce) — reference implementation of headless storefront with App Router, RSC, and streaming by the Next.js team (HIGH confidence — official Vercel reference)
- [Next.js App Router Docs — Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components) — official guidance on component rendering boundaries and "use client" directive (HIGH confidence — official documentation)
- [Next.js Metadata API Docs](https://nextjs.org/docs/app/getting-started/metadata-and-og-images) — `generateMetadata()` and JSON-LD structured data in App Router (HIGH confidence — official documentation)
- [NextAuth.js v5 — Migrating to v5](https://authjs.dev/getting-started/migrating-to-v5) — configuration changes, JWT strategy, and App Router integration (HIGH confidence — official Auth.js documentation)
- [Setting Up Auth.js v5 with Next.js 15 — CodeVoweb](https://codevoweb.com/how-to-set-up-next-js-15-with-nextauth-v5/) — practical implementation patterns for credentials + OAuth in Next.js 15 (MEDIUM confidence — community guide, recent 2026)
- [Full-Stack Type Safety with FastAPI + Next.js + OpenAPI — Abhay Ramesh](https://abhayramesh.com/blog/type-safe-fullstack) — openapi-typescript workflow for FastAPI → Next.js type generation (MEDIUM confidence — developer blog, aligns with PROJECT.md decision)
- [TanStack Query + Next.js App Router — Storieasy](https://www.storieasy.com/blog/integrate-tanstack-query-with-next-js-app-router-2025-ultimate-guide) — server-side prefetch with hydration, mutation patterns for cart (MEDIUM confidence — recent community guide)
- [15 Ecommerce Checkout & Cart UX Best Practices — Design Studio](https://www.designstudiouiux.com/blog/ecommerce-checkout-ux-best-practices/) — checkout UX patterns, cart abandonment factors, one-page vs multi-step (MEDIUM confidence — UX industry publication)
- [Infinite Scroll vs Pagination — NinjaTables](https://ninjatables.com/infinite-scroll-vs-pagination/) — why pagination is preferred for e-commerce catalog browsing (MEDIUM confidence — aligns with Baymard Institute guidance)
- [Wishlist UX Best Practices — Yotpo](https://www.yotpo.com/ecommerce-product-page-guide/wishlists/) — wishlist feature design, connection to out-of-stock and restock notification flows (MEDIUM confidence — e-commerce platform vendor, slight promotional bias)
- [E-Commerce Wishlist UX — thestory.is](https://thestory.is/en/journal/designing-wishlists-in-e-commerce/) — wishlist UX design patterns and expected behaviors (MEDIUM confidence — UX publication)
- [Dark Patterns in E-Commerce — Eleken](https://www.eleken.co/blog-posts/dark-patterns-examples) — anti-features to avoid: forced registration, intrusive popups, etc. (MEDIUM confidence — UX consultancy publication citing Princeton research)
- [Baymard Institute — Product Page UX Best Practices 2025](https://baymard.com/blog/current-state-ecommerce-product-page-ux) — authoritative e-commerce UX research on book detail page expectations (HIGH confidence — leading e-commerce UX research institution)

---

*Feature research for: BookStore v3.0 — Next.js Customer Storefront*
*Researched: 2026-02-27*
