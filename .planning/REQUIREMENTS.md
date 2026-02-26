# Requirements: BookStore

**Defined:** 2026-02-26
**Core Value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## v1.1 Requirements

Requirements for milestone v1.1: Pre-booking, Notifications & Admin. Each maps to roadmap phases.

### Pre-booking

- [ ] **PRBK-01**: User can reserve (pre-book) an out-of-stock book
- [ ] **PRBK-02**: User can view their list of pre-booked books
- [ ] **PRBK-03**: User can cancel a pre-booking
- [ ] **PRBK-04**: Pre-booking is rejected with 409 when the book is currently in stock
- [ ] **PRBK-05**: Pre-booking records track status (waiting → notified → cancelled) with notified_at timestamp
- [ ] **PRBK-06**: When admin restocks a book, all waiting pre-bookers are notified simultaneously (broadcast)

### Email Notifications

- [x] **EMAL-01**: Email infrastructure exists with async SMTP sending via fastapi-mail
- [ ] **EMAL-02**: User receives order confirmation email after successful checkout
- [ ] **EMAL-03**: User receives restock alert email when a pre-booked book is restocked
- [x] **EMAL-04**: Emails use Jinja2 HTML templates with plain-text fallback
- [x] **EMAL-05**: Email sending never blocks or delays the API response (BackgroundTasks)
- [x] **EMAL-06**: Email is only sent after the database transaction commits (no email on rollback)

### Admin User Management

- [x] **ADMN-01**: Admin can view a paginated list of all users
- [x] **ADMN-02**: Admin can filter user list by role and active status
- [x] **ADMN-03**: Admin can deactivate a user account (sets is_active=false, revokes all refresh tokens)
- [x] **ADMN-04**: Admin can reactivate a previously deactivated user account
- [x] **ADMN-05**: Admin cannot deactivate themselves or other admin users

## Future Requirements

Deferred to v2+. Tracked but not in current roadmap.

### Enhanced Auth

- **EAUTH-01**: JWT invalidation on user deactivation (immediate token revocation)
- **EAUTH-02**: Welcome email on user registration

### Advanced Pre-booking

- **APRBK-01**: Pre-booking with quantity > 1
- **APRBK-02**: Auto-add to cart on restock
- **APRBK-03**: Auto-reserve stock for pre-bookers (FIFO queue fulfillment)

### Email Analytics

- **EANL-01**: Email delivery confirmation tracking
- **EANL-02**: Email open/click tracking

### Admin

- **AADM-01**: Admin can promote/demote user roles
- **AADM-02**: Admin can hard-delete users

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real payment integration | Mock payment sufficient for v1.1 |
| Real-time notifications (WebSocket) | Email sufficient for restock alerts |
| Admin UI / dashboard | API-only; no frontend in scope |
| Celery / Redis task queue | BackgroundTasks sufficient at v1.1 volume |
| SMTP provider selection | Ops decision outside milestone scope |
| Email template visual design system (MJML) | Inline CSS sufficient for transactional emails |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EMAL-01 | Phase 9 | Complete |
| EMAL-04 | Phase 9 | Complete |
| EMAL-05 | Phase 9 | Complete |
| EMAL-06 | Phase 9 | Complete |
| ADMN-01 | Phase 10 | Complete |
| ADMN-02 | Phase 10 | Complete |
| ADMN-03 | Phase 10 | Complete |
| ADMN-04 | Phase 10 | Complete |
| ADMN-05 | Phase 10 | Complete |
| PRBK-01 | Phase 11 | Pending |
| PRBK-02 | Phase 11 | Pending |
| PRBK-03 | Phase 11 | Pending |
| PRBK-04 | Phase 11 | Pending |
| PRBK-05 | Phase 11 | Pending |
| PRBK-06 | Phase 11 | Pending |
| EMAL-02 | Phase 12 | Pending |
| EMAL-03 | Phase 12 | Pending |

**Coverage:**
- v1.1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 — traceability filled after roadmap creation*
