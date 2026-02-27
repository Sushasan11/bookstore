# Roadmap: BookStore

## Milestones

- ✅ **v1.0 MVP** — Phases 1-8 (shipped 2026-02-25)
- ✅ **v1.1 Pre-booking, Notifications & Admin** — Phases 9-12 (shipped 2026-02-26)
- ✅ **v2.0 Reviews & Ratings** — Phases 13-15 (shipped 2026-02-27)
- ✅ **v2.1 Admin Dashboard & Analytics** — Phases 16-18 (shipped 2026-02-27)
- 🚧 **v3.0 Customer Storefront** — Phases 19-25 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-8) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: Infrastructure (4/4 plans) — completed 2026-02-25
- [x] Phase 2: Core Auth (5/5 plans) — completed 2026-02-25
- [x] Phase 3: OAuth (3/3 plans) — completed 2026-02-25
- [x] Phase 4: Catalog (3/3 plans) — completed 2026-02-25
- [x] Phase 5: Discovery (3/3 plans) — completed 2026-02-25
- [x] Phase 6: Cart (2/2 plans) — completed 2026-02-25
- [x] Phase 7: Orders (2/2 plans) — completed 2026-02-25
- [x] Phase 8: Wishlist (2/2 plans) — completed 2026-02-25

</details>

<details>
<summary>✅ v1.1 Pre-booking, Notifications & Admin (Phases 9-12) — SHIPPED 2026-02-26</summary>

- [x] Phase 9: Email Infrastructure (2/2 plans) — completed 2026-02-26
- [x] Phase 10: Admin User Management (2/2 plans) — completed 2026-02-26
- [x] Phase 11: Pre-booking (2/2 plans) — completed 2026-02-26
- [x] Phase 12: Email Notifications Wiring (2/2 plans) — completed 2026-02-26

</details>

<details>
<summary>✅ v2.0 Reviews & Ratings (Phases 13-15) — SHIPPED 2026-02-27</summary>

- [x] Phase 13: Review Data Layer (2/2 plans) — completed 2026-02-26
- [x] Phase 14: Review CRUD Endpoints (2/2 plans) — completed 2026-02-26
- [x] Phase 15: Book Detail Aggregates (1/1 plan) — completed 2026-02-27

</details>

<details>
<summary>✅ v2.1 Admin Dashboard & Analytics (Phases 16-18) — SHIPPED 2026-02-27</summary>

- [x] Phase 16: Sales Analytics (2/2 plans) — completed 2026-02-27
- [x] Phase 17: Inventory Analytics (1/1 plan) — completed 2026-02-27
- [x] Phase 18: Review Moderation Dashboard (2/2 plans) — completed 2026-02-27

</details>

### 🚧 v3.0 Customer Storefront (In Progress)

**Milestone Goal:** Build a Next.js 15 customer-facing storefront with full feature parity against all user-facing backend endpoints. Monorepo restructure with `backend/` and `frontend/` directories. Catalog browsing, auth, cart/checkout, orders, wishlist, pre-booking, and reviews delivered as a responsive, SEO-optimized storefront.

- [ ] **Phase 19: Monorepo + Frontend Foundation** — Restructure repo, scaffold Next.js 15 app with full tooling
- [ ] **Phase 20: Auth Integration** — NextAuth.js with email/password and Google OAuth, JWT bridge to FastAPI
- [ ] **Phase 21: Catalog and Search** — SSR catalog, book detail pages with SEO, full-text search with URL-persisted filters
- [ ] **Phase 22: Cart and Checkout** — Full cart management with optimistic updates, checkout flow, order confirmation
- [ ] **Phase 23: Orders and Account** — Order history, order detail, account page with navigation
- [ ] **Phase 24: Wishlist and Pre-booking** — Wishlist with optimistic toggle, pre-booking for out-of-stock titles
- [ ] **Phase 25: Reviews** — Read/write/edit/delete reviews on book detail page with verified-purchase gate

## Phase Details

### Phase 19: Monorepo + Frontend Foundation
**Goal**: Working monorepo and fully scaffolded Next.js 15 app ready for feature development
**Depends on**: Nothing (first phase of v3.0)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06
**Success Criteria** (what must be TRUE):
  1. Running `cd backend && poetry run pytest` passes all 306 backend tests with the code under `backend/`
  2. Running `cd frontend && npm run dev` starts a Next.js 15 app with TypeScript, shadcn/ui, and Tailwind v4 visible in the browser
  3. `frontend/src/types/api.generated.ts` exists and was generated from the live FastAPI `/openapi.json`
  4. The browser renders a responsive layout (header, nav, footer) on mobile and desktop viewports
  5. Any fetch from the frontend to `localhost:8000` succeeds without a CORS error in the browser console
**Plans**: 3 plans
- [ ] 19-01-PLAN.md — Monorepo restructure (git mv to backend/) + CORS + root package.json
- [ ] 19-02-PLAN.md — Next.js 15 scaffold + shadcn/ui + API types + TanStack Query + providers
- [ ] 19-03-PLAN.md — Responsive layout shell (header, mobile nav, footer, dark mode) + smoke test

### Phase 20: Auth Integration
**Goal**: Users can securely sign up, sign in (email + Google), and maintain sessions that carry FastAPI tokens
**Depends on**: Phase 19
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08
**Success Criteria** (what must be TRUE):
  1. User can create an account with email and password and is immediately signed in
  2. User can sign in with a Google account and land on the store as an authenticated user
  3. After browser refresh or navigating away and back, the user remains signed in without re-entering credentials
  4. Navigating to a protected route while signed out redirects to the login page, then back to the original destination after sign-in
  5. A deactivated user's next API call signs them out automatically and returns them to the login page
**Plans**: TBD

### Phase 21: Catalog and Search
**Goal**: Users can browse, search, and filter the book catalog through SEO-optimized server-rendered pages
**Depends on**: Phase 19
**Requirements**: CATL-01, CATL-02, CATL-03, CATL-04, CATL-05, CATL-06, CATL-07
**Success Criteria** (what must be TRUE):
  1. User can browse a paginated grid of books showing cover, title, author, price, and stock status
  2. User can view a book detail page showing description, average rating, review count, and stock status
  3. User can search by title, author, or genre and filter results by genre and price range
  4. Copying the URL from a search results page and opening it in a new tab reproduces the exact same results and filters
  5. The book detail page HTML source (view-source) contains JSON-LD Book schema and Open Graph meta tags
**Plans**: TBD

### Phase 22: Cart and Checkout
**Goal**: Users can manage a shopping cart and complete a checkout that produces an order
**Depends on**: Phase 20
**Requirements**: SHOP-01, SHOP-02, SHOP-03, SHOP-04, SHOP-05, SHOP-06, SHOP-09, SHOP-10
**Success Criteria** (what must be TRUE):
  1. User can add a book from the catalog or detail page and see the cart count badge in the navbar update immediately
  2. User can view the cart with all items, quantities, and the correct total, then update quantities or remove items
  3. User can place an order via the checkout page and land on an order confirmation page showing the order details
  4. Adding or removing an item updates the cart UI instantly (optimistic), and rolls back with a visible error if the server returns an error
**Plans**: TBD

### Phase 23: Orders and Account
**Goal**: Users can review their purchase history and access their account in one central place
**Depends on**: Phase 22
**Requirements**: SHOP-07, SHOP-08
**Success Criteria** (what must be TRUE):
  1. User can view a paginated order history list showing date, total, and a summary of items for each order
  2. User can click an order to see the full item list with individual prices and quantities as recorded at time of purchase
**Plans**: TBD

### Phase 24: Wishlist and Pre-booking
**Goal**: Users can save books for later and reserve out-of-stock titles with a single action
**Depends on**: Phase 20
**Requirements**: WISH-01, WISH-02, WISH-03, WISH-04, PREB-01, PREB-02, PREB-03, PREB-04
**Success Criteria** (what must be TRUE):
  1. User can toggle the wishlist heart icon on any book card or detail page and see it update instantly without a page reload
  2. User can view their wishlist page showing all saved books with current price and stock status
  3. An out-of-stock book shows a "Pre-book" button instead of "Add to Cart" on the book detail page
  4. User can cancel an active pre-booking from their account page and it disappears from the pre-bookings list
**Plans**: TBD

### Phase 25: Reviews
**Goal**: Users can read reviews on book detail pages and write, edit, or delete their own reviews on books they purchased
**Depends on**: Phase 23
**Requirements**: REVW-01, REVW-02, REVW-03, REVW-04, REVW-05
**Success Criteria** (what must be TRUE):
  1. The book detail page displays all reviews with star rating, reviewer name, optional text, and date
  2. A user who purchased a book sees a "Write a Review" form with an interactive 1-5 star selector
  3. A user who already reviewed a book sees their review in an editable state with the existing rating and text pre-populated
  4. User can delete their own review after confirming a deletion prompt, and the review disappears from the page
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Infrastructure | v1.0 | 4/4 | Complete | 2026-02-25 |
| 2. Core Auth | v1.0 | 5/5 | Complete | 2026-02-25 |
| 3. OAuth | v1.0 | 3/3 | Complete | 2026-02-25 |
| 4. Catalog | v1.0 | 3/3 | Complete | 2026-02-25 |
| 5. Discovery | v1.0 | 3/3 | Complete | 2026-02-25 |
| 6. Cart | v1.0 | 2/2 | Complete | 2026-02-25 |
| 7. Orders | v1.0 | 2/2 | Complete | 2026-02-25 |
| 8. Wishlist | v1.0 | 2/2 | Complete | 2026-02-25 |
| 9. Email Infrastructure | v1.1 | 2/2 | Complete | 2026-02-26 |
| 10. Admin User Management | v1.1 | 2/2 | Complete | 2026-02-26 |
| 11. Pre-booking | v1.1 | 2/2 | Complete | 2026-02-26 |
| 12. Email Notifications Wiring | v1.1 | 2/2 | Complete | 2026-02-26 |
| 13. Review Data Layer | v2.0 | 2/2 | Complete | 2026-02-26 |
| 14. Review CRUD Endpoints | v2.0 | 2/2 | Complete | 2026-02-26 |
| 15. Book Detail Aggregates | v2.0 | 1/1 | Complete | 2026-02-27 |
| 16. Sales Analytics | v2.1 | 2/2 | Complete | 2026-02-27 |
| 17. Inventory Analytics | v2.1 | 1/1 | Complete | 2026-02-27 |
| 18. Review Moderation Dashboard | v2.1 | 2/2 | Complete | 2026-02-27 |
| 19. Monorepo + Frontend Foundation | v3.0 | 0/3 | Planned | - |
| 20. Auth Integration | v3.0 | 0/? | Not started | - |
| 21. Catalog and Search | v3.0 | 0/? | Not started | - |
| 22. Cart and Checkout | v3.0 | 0/? | Not started | - |
| 23. Orders and Account | v3.0 | 0/? | Not started | - |
| 24. Wishlist and Pre-booking | v3.0 | 0/? | Not started | - |
| 25. Reviews | v3.0 | 0/? | Not started | - |
