# Requirements: BookStore

**Defined:** 2026-02-25
**Core Value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Authentication

- [x] **AUTH-01**: User can sign up with email and password
- [x] **AUTH-02**: User can log in and receive JWT access + refresh tokens
- [x] **AUTH-03**: User can refresh expired access token using refresh token
- [x] **AUTH-04**: User can log out (refresh token revoked)
- [x] **AUTH-05**: Endpoints enforce role-based access (admin vs user)
- [x] **AUTH-06**: User can log in with Google or GitHub OAuth

### Catalog

- [x] **CATL-01**: Admin can add a book with title, author, price, ISBN, genre, description, cover image URL, publish date
- [x] **CATL-02**: Admin can edit book details
- [x] **CATL-03**: Admin can delete a book
- [x] **CATL-04**: Admin can update book stock quantity
- [x] **CATL-05**: Admin can manage genre taxonomy (add/list genres)

### Discovery

- [ ] **DISC-01**: User can browse books with pagination and sorting (by title, price, date)
- [ ] **DISC-02**: User can search books by title, author, or genre (full-text search)
- [ ] **DISC-03**: User can filter books by genre and/or author
- [ ] **DISC-04**: User can view book details including stock status

### Commerce

- [x] **COMM-01**: User can add books to shopping cart
- [x] **COMM-02**: User can update cart item quantity or remove items
- [x] **COMM-03**: User can checkout cart with mock payment (creates order, decrements stock)
- [x] **COMM-04**: User can view order confirmation after checkout
- [x] **COMM-05**: User can view order history with line items

### Engagement

- [ ] **ENGM-01**: User can add/remove books from wishlist
- [ ] **ENGM-02**: User can view their wishlist
- [ ] **ENGM-03**: User can pre-book (reserve) an out-of-stock book
- [ ] **ENGM-04**: User is notified in-app when a reserved book is back in stock
- [ ] **ENGM-05**: User can view and cancel their reservations
- [x] **ENGM-06**: Admin can view all placed orders

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Notifications

- **NOTF-01**: User receives email notifications for order confirmation
- **NOTF-02**: User receives email when reserved book is back in stock
- **NOTF-03**: User can configure notification preferences

### Moderation

- **MODR-01**: Admin can manage users (view, deactivate)
- **MODR-02**: Admin can manage genres in bulk

### Enhanced Commerce

- **ECOM-01**: Price range filter on catalog
- **ECOM-02**: Multiple genre filtering (AND/OR)
- **ECOM-03**: Auto-fulfill reservations (convert to cart item when stock arrives)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real payment integration (Stripe) | Mock payment sufficient for v1; real integration doubles complexity with PCI scope |
| Email delivery system | In-app notifications only for v1; email requires SMTP infrastructure |
| User reviews and ratings | Requires moderation strategy; distracts from core commerce |
| Social features (reading lists, follows) | Different product model; not a social platform |
| Recommendation engine | Cold-start problem; needs transaction data first |
| Guest checkout | Breaks order history, wishlist, pre-booking linkage |
| Mobile app | API-first; web/API only |
| Multi-tenant / multiple storefronts | Single bookstore |
| Advanced search (Elasticsearch) | PostgreSQL full-text search sufficient at this scale |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 2 | Done |
| AUTH-02 | Phase 2 | Done |
| AUTH-03 | Phase 2 | Done |
| AUTH-04 | Phase 2 | Done |
| AUTH-05 | Phase 2 | Done |
| AUTH-06 | Phase 3 | Done |
| CATL-01 | Phase 4 | Done |
| CATL-02 | Phase 4 | Done |
| CATL-03 | Phase 4 | Done |
| CATL-04 | Phase 4 | Done |
| CATL-05 | Phase 4 | Done |
| DISC-01 | Phase 5 | Pending |
| DISC-02 | Phase 5 | Pending |
| DISC-03 | Phase 5 | Pending |
| DISC-04 | Phase 5 | Pending |
| COMM-01 | Phase 6 | Complete |
| COMM-02 | Phase 6 | Complete |
| COMM-03 | Phase 7 | Complete |
| COMM-04 | Phase 7 | Complete |
| COMM-05 | Phase 7 | Complete |
| ENGM-01 | Phase 8 | Pending |
| ENGM-02 | Phase 8 | Pending |
| ENGM-03 | Phase 9 | Pending |
| ENGM-04 | Phase 9 | Pending |
| ENGM-05 | Phase 9 | Pending |
| ENGM-06 | Phase 7 | Complete |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after Phase 4 completion — CATL-01 through CATL-05 marked Done*
