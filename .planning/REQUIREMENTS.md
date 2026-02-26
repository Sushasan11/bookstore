# Requirements: BookStore

**Defined:** 2026-02-26
**Core Value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## v2.0 Requirements

Requirements for reviews & ratings milestone. Each maps to roadmap phases.

### Review CRUD

- [ ] **REVW-01**: User can submit a review (1-5 star rating with optional text) for a book they purchased
- [ ] **REVW-02**: User can view paginated reviews for any book
- [ ] **REVW-03**: User can edit their own review (update rating and/or text)
- [ ] **REVW-04**: User can delete their own review
- [x] **REVW-05**: One review per user per book (duplicate submission returns 409)

### Verified Purchase

- [ ] **VPRC-01**: Only users with a completed order containing the book can submit a review
- [ ] **VPRC-02**: Review response includes "verified purchase" indicator

### Admin Moderation

- [ ] **ADMR-01**: Admin can delete any review regardless of ownership

### Aggregates

- [ ] **AGGR-01**: Book detail response includes average rating (rounded to 1 decimal)
- [ ] **AGGR-02**: Book detail response includes total review count

## Future Requirements

### Search Enhancement

- **SRCH-01**: User can sort/filter books by average rating in search results

### Social

- **SOCL-01**: Helpfulness voting on reviews (upvote/downvote)
- **SOCL-02**: Sort reviews by helpfulness

## Out of Scope

| Feature | Reason |
|---------|--------|
| Helpfulness voting | Adds table, deduplication, sort complexity — defer until review volume justifies it |
| Pre-moderation queue | Reactive admin-delete is the correct pattern; pre-moderation suppresses authentic reviews |
| Anonymous reviews | FTC 2024 rules prohibit fake reviews; all reviews tied to authenticated users |
| Review replies/comments | Not a social platform; reviews are standalone |
| Rating sort in search | Deferred to future — keep v2.0 focused on core review CRUD |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REVW-01 | Phase 14 | Pending |
| REVW-02 | Phase 14 | Pending |
| REVW-03 | Phase 14 | Pending |
| REVW-04 | Phase 14 | Pending |
| REVW-05 | Phase 13 | Complete |
| VPRC-01 | Phase 13 | Pending |
| VPRC-02 | Phase 14 | Pending |
| ADMR-01 | Phase 14 | Pending |
| AGGR-01 | Phase 15 | Pending |
| AGGR-02 | Phase 15 | Pending |

**Coverage:**
- v2.0 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after v2.0 roadmap creation*
