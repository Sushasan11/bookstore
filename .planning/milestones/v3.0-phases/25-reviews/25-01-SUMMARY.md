---
phase: 25-reviews
plan: "01"
subsystem: frontend-reviews
tags: [reviews, tanstack-query, hooks, star-selector, review-card, shadcn]
dependency_graph:
  requires:
    - "frontend/src/lib/api.ts (apiFetch, ApiError)"
    - "frontend/src/types/api.generated.ts (ReviewResponse, ReviewListResponse, ReviewCreate, ReviewUpdate)"
    - "next-auth (useSession)"
    - "@tanstack/react-query (useQuery, useMutation, useQueryClient)"
    - "sonner (toast)"
  provides:
    - "frontend/src/lib/reviews.ts — reviews data layer for Plan 25-02"
    - "frontend/src/app/books/[id]/_components/StarSelector.tsx — for ReviewForm in Plan 25-02"
    - "frontend/src/app/books/[id]/_components/ReviewCard.tsx — for ReviewsSection in Plan 25-02"
    - "frontend/src/components/ui/textarea.tsx — for ReviewForm in Plan 25-02"
  affects:
    - "Plan 25-02 (ReviewsSection, ReviewForm) — all 4 files are direct imports"
tech_stack:
  added:
    - "shadcn Textarea component (npx shadcn@latest add textarea)"
  patterns:
    - "TanStack Query useQuery + useMutation pattern (same as wishlist.ts, prebook.ts)"
    - "Parameterized REVIEWS_KEY (bookId) => ['reviews', bookId] — per-book cache isolation"
    - "DUPLICATE_REVIEW 409 error handled with query invalidation + toast.info (shows existing review)"
    - "Purchase gate 403 surfaced as toast.error (no client-side purchase check)"
    - "Controlled StarSelector using useState(hovered) — display = hovered || value"
    - "ReviewCard is a pure presentational component — no client boundary needed"
key_files:
  created:
    - "frontend/src/lib/reviews.ts"
    - "frontend/src/app/books/[id]/_components/StarSelector.tsx"
    - "frontend/src/app/books/[id]/_components/ReviewCard.tsx"
    - "frontend/src/components/ui/textarea.tsx"
  modified: []
decisions:
  - "session.user.id is the FastAPI user ID as string — confirmed from auth.ts session callback (token.userId → session.user.id)"
  - "myReview detection uses author.user_id (number) compared to Number(session.user.id) — no separate userId field needed"
  - "REVIEWS_KEY parameterized by bookId (unlike WISHLIST_KEY which is global) — each book has its own isolated cache"
  - "ReviewCard has no 'use client' directive — it is a pure server-compatible presentational component"
  - "updateMutation takes { reviewId, body } object — body built selectively by caller to respect PATCH partial update semantics"
metrics:
  duration: "~2 min"
  completed_date: "2026-02-28"
  tasks_completed: 2
  files_created: 4
  files_modified: 0
---

# Phase 25 Plan 01: Reviews Data Layer and Foundational Components Summary

**One-liner:** Reviews data layer (useReviews hook + API functions) with StarSelector interactive star picker and ReviewCard display component using established TanStack Query and shadcn patterns.

## What Was Built

Plan 25-01 delivers the data layer and reusable UI primitives that Plan 25-02 will compose into the full ReviewsSection and ReviewForm on the book detail page.

### Files Created

**`frontend/src/lib/reviews.ts`** — The reviews data layer following the established project hook pattern (`wishlist.ts`, `prebook.ts`):
- `fetchReviews(bookId)` — public GET endpoint, no auth, fetches with `size=50`
- `createReview(accessToken, bookId, body)` — POST with Authorization header
- `updateReview(accessToken, reviewId, body)` — PATCH for partial updates (caller builds selective body)
- `deleteReview(accessToken, reviewId)` — DELETE returning void (204)
- `REVIEWS_KEY(bookId)` — parameterized query cache key
- `useReviews(bookId)` hook — returns `reviewsQuery`, `createMutation`, `updateMutation`, `deleteMutation`, `myReview`
- 403 → "You must purchase this book" toast, 409 DUPLICATE_REVIEW → query invalidation + toast.info, others → generic error toast

**`frontend/src/app/books/[id]/_components/StarSelector.tsx`** — Controlled 1-5 star rating picker:
- 5 `<button type="button">` elements (keyboard accessible, form-safe)
- Hover preview via `useState(hovered)` — display = hovered || value
- `aria-label` on each star, `role="group"` wrapper
- Filled: `text-yellow-500`, empty: `text-muted-foreground`, disabled: `cursor-not-allowed opacity-50`
- Matches existing `RatingDisplay.tsx` Unicode `★` aesthetic

**`frontend/src/app/books/[id]/_components/ReviewCard.tsx`** — Presentational review display:
- Author display name, verified-purchase Badge (green), formatted date
- Integer star rating using inline `★` map (no RatingDisplay import — avoids half-star logic)
- Optional review text in muted paragraph
- Conditional edit (Pencil) / delete (Trash2) icon buttons when `isOwn && (onEdit || onDelete)`
- `formatReviewDate` helper using `toLocaleDateString`

**`frontend/src/components/ui/textarea.tsx`** — Installed via `npx shadcn@latest add textarea`.

## Key Decisions

1. `session.user.id` (confirmed from auth.ts) holds the FastAPI user ID as a string — `myReview` uses `Number(session.user.id)` for comparison against `author.user_id` (number).
2. `ReviewCard` has no `'use client'` directive — it is a pure presentational component with no hooks, safe for server rendering.
3. `updateMutation` exposes `{ reviewId, body }` params — caller (ReviewForm in Plan 25-02) builds the selective PATCH body to avoid clearing unchanged fields.
4. Reviews query has no `enabled` guard — it is a public endpoint always fetched regardless of auth state.

## Verification Results

- `npx tsc --noEmit` — zero errors after both tasks
- `npm run build` — production build succeeds (11 routes compiled)
- All 4 required files present on disk

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All 5 files confirmed present on disk. Both task commits (65eb6f3, 98f15a0) confirmed in git log.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `65eb6f3` | feat(25-01): add reviews data layer and shadcn Textarea |
| Task 2 | `98f15a0` | feat(25-01): add StarSelector and ReviewCard components |
