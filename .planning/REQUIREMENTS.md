# Requirements: BookStore

**Defined:** 2026-03-02
**Core Value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## v4.1 Requirements

Requirements for v4.1 Clean House milestone. Tech debt resolution and validation.

### Component Cleanup

- [x] **COMP-01**: Admin DeltaBadge extracted to shared component used by both overview and sales pages
- [x] **COMP-02**: Admin StockBadge consolidated into single configurable component with threshold parameter

### Type Safety

- [x] **TYPE-01**: updateBookStock API function returns `Promise<BookResponse>` matching actual backend response

### Analytics

- [x] **ANLY-01**: Top-sellers table respects period selector (today/week/month) instead of showing all-time data

### Documentation

- [x] **DOCS-01**: SUMMARY frontmatter for plans 26-02, 27-01, and 31-02 lists correct requirement IDs in `requirements-completed`; api.generated.ts regenerated with period param

### Email Validation

- [ ] **MAIL-01**: Email improvements (logo CID embedding, Open Library cover fallback) verified working end-to-end

## Future Requirements

### v4.2 Customer Experience

- **RECO-01**: Recommendation engine ("readers also bought") based on purchase/review data
- **DASH-01**: Customer dashboard with order tracking and purchase history
- **SRCH-01**: Search autocomplete and suggestions
- **SRCH-02**: Recent searches persistence

### v4.3 Quality & Hardening

- **TEST-01**: Frontend test coverage (component + integration tests)
- **TEST-02**: Visual E2E testing — launch server, test all UI flows in browser, confirm backend + frontend work together for every feature
- **TEST-03**: Robust test planning for complex logic — think through edge cases, error states, and full user journeys before writing tests
- **UIUX-01**: UI/UX audit — proactively evaluate menu navigation, presentation, and user flow across all pages for clarity and consistency
- **PERF-01**: Performance profiling and optimization
- **A11Y-01**: Accessibility audit and remediation
- **SECR-01**: Security hardening audit

> **Note:** TEST-02, TEST-03, and UIUX-01 reflect core project principles (see PROJECT.md "Quality Principles"). These are not optional — they are the standard for how this project ships.

## Out of Scope

| Feature | Reason |
|---------|--------|
| New backend features | v4.1 is cleanup only — no new API endpoints |
| Payment integration | Deferred beyond v4.3 |
| Mobile app | Web-only project |
| Database schema changes | No model changes needed for tech debt items |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-01 | Phase 31 | Complete |
| COMP-02 | Phase 31 | Complete |
| TYPE-01 | Phase 31 | Complete |
| ANLY-01 | Phase 31 | Complete |
| DOCS-01 | Phase 32 | Complete |
| MAIL-01 | Phase 32 | Pending |

**Coverage:**
- v4.1 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after roadmap creation — all 6 requirements mapped to phases 31-32*
