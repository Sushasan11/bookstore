# Requirements: BookStore

**Defined:** 2026-02-27
**Core Value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience

## v3.0 Requirements

Requirements for the Next.js customer-facing storefront. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: Monorepo restructured with `backend/` and `frontend/` directories, backend CI passing
- [x] **FOUND-02**: Next.js 15 app scaffolded with TypeScript, shadcn/ui, Tailwind v4, and root layout shell
- [x] **FOUND-03**: CORS enabled on FastAPI backend for frontend origin
- [x] **FOUND-04**: openapi-typescript types auto-generated from FastAPI `/openapi.json`
- [x] **FOUND-05**: TanStack Query provider configured at root layout
- [x] **FOUND-06**: Responsive mobile-first layout with header, navigation, and footer

### Auth

- [x] **AUTH-01**: User can sign up with email and password
- [x] **AUTH-02**: User can log in with email and password
- [x] **AUTH-03**: User can log in with Google OAuth
- [x] **AUTH-04**: User session persists across page navigation and refresh
- [x] **AUTH-05**: User can log out
- [x] **AUTH-06**: Protected routes redirect unauthenticated users to login
- [x] **AUTH-07**: Access token refreshes transparently when expired
- [x] **AUTH-08**: Deactivated user is signed out on next API call (401 handling)

### Catalog

- [x] **CATL-01**: User can browse paginated book grid with cover, title, author, price, and stock status
- [ ] **CATL-02**: User can view book detail page with description, average rating, review count, and stock status
- [ ] **CATL-03**: User can search books by title, author, or genre using full-text search
- [x] **CATL-04**: User can filter search results by genre and price range
- [ ] **CATL-05**: Search and filter state is persisted in URL (bookmarkable, shareable)
- [ ] **CATL-06**: Book detail page has SEO metadata (JSON-LD Book schema, Open Graph tags)
- [ ] **CATL-07**: Catalog and book detail pages are server-rendered with ISR for SEO

### Shopping

- [ ] **SHOP-01**: User can add a book to the shopping cart
- [ ] **SHOP-02**: User can update item quantity in the cart
- [ ] **SHOP-03**: User can remove an item from the cart
- [ ] **SHOP-04**: User can view cart with item list, quantities, and total
- [ ] **SHOP-05**: User can checkout and place an order (mock payment)
- [ ] **SHOP-06**: User sees order confirmation page after successful checkout
- [ ] **SHOP-07**: User can view order history with date, total, and item summary
- [ ] **SHOP-08**: User can view individual order detail with full item list and price snapshots
- [ ] **SHOP-09**: Cart count badge in navbar updates reactively after mutations
- [ ] **SHOP-10**: Cart add/remove uses optimistic updates with rollback on error

### Wishlist

- [ ] **WISH-01**: User can add a book to their wishlist from catalog or detail page
- [ ] **WISH-02**: User can remove a book from their wishlist
- [ ] **WISH-03**: User can view their wishlist with book details and current price/stock
- [ ] **WISH-04**: Wishlist toggle uses optimistic update (instant heart icon feedback)

### Pre-booking

- [ ] **PREB-01**: User sees "Pre-book" button instead of "Add to Cart" when a book is out of stock
- [ ] **PREB-02**: User can pre-book an out-of-stock book
- [ ] **PREB-03**: User can view active pre-bookings on their account page
- [ ] **PREB-04**: User can cancel a pre-booking

### Reviews

- [ ] **REVW-01**: User can see reviews and ratings on the book detail page
- [ ] **REVW-02**: User who purchased a book can leave a 1-5 star rating with optional text review
- [ ] **REVW-03**: User can edit their own review
- [ ] **REVW-04**: User can delete their own review
- [ ] **REVW-05**: User sees "already reviewed" state with edit option if they've already reviewed

## Future Requirements

Deferred to v3.1+ milestones.

### Admin Dashboard

- **ADMN-01**: Admin can view sales analytics dashboard
- **ADMN-02**: Admin can manage book catalog (CRUD) via UI
- **ADMN-03**: Admin can manage users (list, deactivate/reactivate) via UI
- **ADMN-04**: Admin can moderate reviews (list, bulk delete) via UI
- **ADMN-05**: Admin can view inventory analytics (low stock, turnover) via UI

### Additional Auth

- **AUTH-09**: User can log in with GitHub OAuth

## Out of Scope

| Feature | Reason |
|---------|--------|
| Admin dashboard UI | Deferred to v3.1+ — separate layouts, access control, components |
| GitHub OAuth on frontend | Email + Google covers majority of users |
| Real payment gateway (Stripe) | Mock payment sufficient; PCI scope is a separate milestone |
| Mobile app | Web-first, API-only |
| Real-time stock notifications | Backend is email-only for restock alerts |
| Infinite scroll on catalog | Pagination is better UX for e-commerce (Baymard Institute) |
| Client-only localStorage cart | Server is source of truth; breaks cross-device |
| Recommendation engine | Needs transaction data first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 19 | Complete |
| FOUND-02 | Phase 19 | Complete |
| FOUND-03 | Phase 19 | Complete |
| FOUND-04 | Phase 19 | Complete |
| FOUND-05 | Phase 19 | Complete |
| FOUND-06 | Phase 19 | Complete |
| AUTH-01 | Phase 20 | Complete |
| AUTH-02 | Phase 20 | Complete |
| AUTH-03 | Phase 20 | Complete |
| AUTH-04 | Phase 20 | Complete |
| AUTH-05 | Phase 20 | Complete |
| AUTH-06 | Phase 20 | Complete |
| AUTH-07 | Phase 20 | Complete |
| AUTH-08 | Phase 20 | Complete |
| CATL-01 | Phase 21 | Complete |
| CATL-02 | Phase 21 | Pending |
| CATL-03 | Phase 21 | Pending |
| CATL-04 | Phase 21 | Complete |
| CATL-05 | Phase 21 | Pending |
| CATL-06 | Phase 21 | Pending |
| CATL-07 | Phase 21 | Pending |
| SHOP-01 | Phase 22 | Pending |
| SHOP-02 | Phase 22 | Pending |
| SHOP-03 | Phase 22 | Pending |
| SHOP-04 | Phase 22 | Pending |
| SHOP-05 | Phase 22 | Pending |
| SHOP-06 | Phase 22 | Pending |
| SHOP-07 | Phase 23 | Pending |
| SHOP-08 | Phase 23 | Pending |
| SHOP-09 | Phase 22 | Pending |
| SHOP-10 | Phase 22 | Pending |
| WISH-01 | Phase 24 | Pending |
| WISH-02 | Phase 24 | Pending |
| WISH-03 | Phase 24 | Pending |
| WISH-04 | Phase 24 | Pending |
| PREB-01 | Phase 24 | Pending |
| PREB-02 | Phase 24 | Pending |
| PREB-03 | Phase 24 | Pending |
| PREB-04 | Phase 24 | Pending |
| REVW-01 | Phase 25 | Pending |
| REVW-02 | Phase 25 | Pending |
| REVW-03 | Phase 25 | Pending |
| REVW-04 | Phase 25 | Pending |
| REVW-05 | Phase 25 | Pending |

**Coverage:**
- v3.0 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-02-27*
*Last updated: 2026-02-27 after roadmap creation (phases 19-25 finalized)*
