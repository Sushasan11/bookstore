---
phase: 21-catalog-and-search
plan: "01"
subsystem: catalog
tags: [backend, frontend, api, book-search, filtering, sorting, components]
dependency_graph:
  requires: [20-auth-integration]
  provides: [catalog-api-helpers, book-card-component, skeleton-components, price-filter-backend]
  affects: [21-02-catalog-page, 21-03-book-detail-page]
tech_stack:
  added: [use-debounce@10.1.0, shadcn/skeleton, shadcn/badge]
  patterns: [avg_rating-left-join-subquery, next-image-remote-patterns, typed-api-helpers]
key_files:
  created:
    - backend/tests/test_books.py
    - frontend/src/lib/catalog.ts
    - frontend/src/app/catalog/_components/BookCard.tsx
    - frontend/src/app/catalog/_components/BookCardSkeleton.tsx
    - frontend/src/components/ui/skeleton.tsx
    - frontend/src/components/ui/badge.tsx
  modified:
    - backend/app/books/router.py
    - backend/app/books/repository.py
    - backend/app/books/service.py
    - frontend/next.config.ts
    - frontend/src/types/api.generated.ts
    - frontend/package.json
key_decisions:
  - "avg_rating sort uses LEFT JOIN subquery on reviews with nulls_last() so un-reviewed books sort last"
  - "Price range params added to backend (min_price/max_price) — client-side filtering rejected as unviable for large catalogs"
  - "sort_dir defaults to asc for all sorts; created_at and avg_rating still respect sort_dir override"
  - "BookCard as server component (no 'use client') — pure RSC with Link wrapper for navigation"
  - "remotePatterns uses https://** (permissive) — covers future cover URLs from any CDN without config changes"
metrics:
  duration: ~14 min
  completed: 2026-02-27
  tasks_completed: 2
  files_created: 6
  files_modified: 6
---

# Phase 21 Plan 01: Catalog Foundation — Backend Extension and Frontend Components Summary

**One-liner:** Extended GET /books with price range filtering and sort direction (including avg_rating LEFT JOIN sort), plus typed catalog API helpers, BookCard server component with deterministic placeholder, and skeleton loading components.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Extend backend GET /books with min_price, max_price, sort_dir, avg_rating | e32186f | router.py, repository.py, service.py, test_books.py |
| 2 | Create catalog API helpers, BookCard, skeleton components, configure next/image | acf975f | catalog.ts, BookCard.tsx, BookCardSkeleton.tsx, skeleton.tsx, badge.tsx, next.config.ts |

## Decisions Made

### Decision 1: avg_rating Sort via LEFT JOIN Subquery with nulls_last()

**Context:** CONTEXT.md requires "Highest rated" as a sort option. The existing backend had no avg_rating sort.

**Decision:** Add `sort=avg_rating` support by joining a subquery that computes `avg(rating)` per book (excluding soft-deleted reviews) using SQLAlchemy's `nulls_last()`. Books with no reviews sort to the end in both asc and desc directions.

**Rationale:** LEFT JOIN preserves all books in results; nulls_last() ensures books without ratings are consistently ordered regardless of sort direction; this matches common e-commerce "Highest rated" sort behavior.

### Decision 2: Price Range as Backend Parameters (not Client-Side)

**Context:** CATL-04 requires price range filtering. The existing backend had no min_price/max_price params.

**Decision:** Added min_price/max_price as Decimal query params to the FastAPI router and repository rather than filtering client-side.

**Rationale:** Client-side filtering across 26+ books (and growing catalog) would require fetching all records — non-viable at scale. Backend filtering is the correct approach per research findings.

### Decision 3: BookCard as Pure Server Component

**Context:** BookCard renders book data from the catalog API. No interactivity required at the card level.

**Decision:** BookCard is a pure server component (no 'use client' directive). It uses `next/link` for navigation and `next/image` for cover images.

**Rationale:** SSR server components render fully on the server, improving Time-to-First-Byte and SEO for the catalog grid.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

### Files Created

- [x] backend/tests/test_books.py — FOUND
- [x] frontend/src/lib/catalog.ts — FOUND
- [x] frontend/src/app/catalog/_components/BookCard.tsx — FOUND
- [x] frontend/src/app/catalog/_components/BookCardSkeleton.tsx — FOUND
- [x] frontend/src/components/ui/skeleton.tsx — FOUND
- [x] frontend/src/components/ui/badge.tsx — FOUND

### Commits

- [x] e32186f — backend extension commit FOUND
- [x] acf975f — frontend components commit FOUND

### Verifications

- [x] `pytest tests/test_books.py` — 5 passed
- [x] `npx tsc --noEmit` — 0 errors

## Self-Check: PASSED
