# Feature Research

**Domain:** Bookstore E-Commerce — v2.0 Milestone (Reviews & Ratings)
**Researched:** 2026-02-26
**Confidence:** HIGH for core review CRUD and verified-purchase constraint (well-established patterns); MEDIUM for aggregate rating storage strategy (tradeoffs require validation against query volume); LOW for helpfulness voting and moderation complexity estimates

> **Scope note:** v1.0 and v1.1 built auth, catalog, FTS, cart, checkout, orders, wishlist,
> pre-booking, email notifications, and admin user management.
> This file focuses exclusively on the new features for v2.0:
> Reviews and ratings — create, read, edit, delete, aggregate display, admin moderation.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these makes the review system feel broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Submit a star rating (1-5) with optional text | Every bookstore from Amazon to Goodreads offers this; absence makes the system feel unfinished | LOW | Integer field constrained to [1, 5]. Text field nullable. Single endpoint: `POST /books/{id}/reviews`. |
| One review per user per book | Users expect a single authoritative opinion per person; duplicates erode trust and pollute aggregates | LOW | Unique DB constraint on `(book_id, user_id)`. Service layer returns 409 on duplicate. Enforce at both DB and service layer. |
| Verified-purchase gate | Users trust "Verified Purchase" badges on Amazon; reviews from non-buyers feel suspicious | MEDIUM | Query `orders` and `order_items` tables to confirm user has a completed order containing the book. No new table needed, join existing data. |
| Edit your own review | Users expect to correct typos or update opinion after re-reading | LOW | `PATCH /books/{book_id}/reviews/{review_id}` or `PUT /reviews/{review_id}`. Only owner can edit. Update `updated_at` timestamp. |
| Delete your own review | Users expect the right to withdraw their opinion | LOW | `DELETE /reviews/{review_id}`. Soft-delete (set `is_deleted = True`) preserves aggregate history between recomputation vs hard-delete. Either works; hard-delete is simpler for this scale. |
| Admin can delete any review | Admins need moderation authority to remove abusive, spam, or policy-violating content | LOW | Same delete endpoint with admin-role override, or a dedicated `DELETE /admin/reviews/{review_id}`. Role check in route dependency. |
| Average rating displayed on book detail | Users scan aggregate scores to triage purchase decisions before reading individual reviews | LOW | Computed field on book detail response: `average_rating` (float, 1 decimal) + `review_count` (int). See Architecture section on storage strategy. |
| List reviews for a book (paginated) | Users expect to read other opinions before buying; infinite scroll or paginated list is standard | LOW | `GET /books/{book_id}/reviews?page=1&page_size=20`. Default sort: most recent first. |
| Review count alongside average | "4.7 stars" from 2 reviews vs 2,000 reviews carries very different weight; both numbers are required | LOW | Return both `average_rating` and `review_count` together — never one without the other. |

### Differentiators (Competitive Advantage)

Features beyond bare minimum that add meaningful value. These are optional for v2.0 launch.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Rating distribution breakdown | Showing "5-star: 60%, 4-star: 25%, 1-star: 10%" builds more trust than a single average; a J-shaped distribution (many positives, some negatives) converts better than a perfect 5.0 | MEDIUM | Store per-star counts in `books` table or compute via GROUP BY. Return as `rating_breakdown: {1: N, 2: N, ...}`. One extra aggregate query or stored counts. |
| User's own review visible first | When a user views a book they have reviewed, showing their review prominently reduces confusion ("did I review this?") | LOW | In the review list response, include `my_review` as a separate field if the requesting user has reviewed the book. Simple lookup by user_id on the reviews list. |
| `reviewed` flag on book detail | Boolean flag on book detail response indicating whether the current user has already reviewed this book; lets clients disable/hide the "Write a review" button | LOW | Add `user_has_reviewed: bool` to book detail response for authenticated users. Single extra query or join. |
| Sort reviews by most helpful | Surfacing well-voted reviews first is standard on Amazon and Goodreads; most recent is easier but less useful at scale | HIGH | Requires "helpful vote" feature (see anti-features — this is a scope decision). Mark as DEFERRED unless helpfulness voting is in scope. |
| Reviewer display name | Personalizes reviews, increases authenticity | LOW | Already available from the `User` model. Return `reviewer_name` (derived from user email prefix or a `display_name` field if added). No new table; display_name field optional addition to User model. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem natural but create significant problems for a v2.0 milestone.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Helpfulness voting ("Was this review helpful?") | Amazon-style; surfaces quality reviews above noise | Adds a new `review_votes` table, vote deduplication logic, a vote endpoint, and sort-by-helpful complexity. At this catalog scale, review volume is too low for votes to be statistically meaningful. Votes can be gamed. | Default sort by most-recent; no voting infrastructure in v2.0. Revisit if review volume grows. |
| Anonymous (unregistered) reviews | Increases review volume and lowers friction | Breaks the verified-purchase requirement entirely. Anonymous reviews are the primary vector for fake review abuse. FTC 2024 rules penalize fake reviews up to $51,744 per violation. | Require JWT auth to submit; verified-purchase gate provides authenticity signal. |
| Review photos / media uploads | Richer review content, higher trust | Requires file upload handling, image storage (S3 or equivalent), CDN, thumbnail generation. Completely out of scope for a text+rating system. Adds significant infra complexity. | Text-only reviews in v2.0. Media uploads are a separate infrastructure milestone. |
| Review approval queue (pre-moderation) | Appears to prevent spam before it goes live | Creates latency between submission and display; users don't see their own review immediately and assume it was lost; queue needs staffing. Over-moderation hides negative reviews, which decreases conversion (products with only 5-star reviews are trusted less). | Publish immediately; admin reactive-delete is sufficient moderation at this scale. |
| Weighted average (newer reviews count more) | Recency-weighted ratings reflect current product state | Complex algorithm, harder to explain to users, harder to audit. At this scale, recency weighting offers no practical benefit. | Simple arithmetic mean. Transparent and correct. |
| Incentivized reviews (reward for leaving review) | Increases review count quickly | FTC 2024 rules prohibit incentivized reviews unless clearly disclosed. Creates legal liability. Distorts rating upward. | Organic reviews only; email prompts after order delivery (if email is in scope) are acceptable. |
| Review flagging by users | Community self-moderation | Requires a `review_flags` table, flag resolution workflow, threshold-based auto-hide logic. Adds significant backend complexity with limited value at low review volume. | Admin-only delete is sufficient moderation for v2.0. |
| Soft-delete with "deleted review" placeholder | Preserves the thread feel for replies | This project has no replies/comment threads. Soft-delete is unnecessary complexity without that use case. | Hard-delete. Recalculate aggregate after deletion. |

---

## Feature Dependencies

```
[Existing: User Auth (JWT)]
    └──required by──> [Submit review] (must be authenticated)
    └──required by──> [Edit/delete own review] (must own the review)
    └──required by──> [Admin: delete any review] (must have admin role)

[Existing: Orders + Order Items tables]
    └──required by──> [Verified-purchase gate] (JOIN to confirm purchase)

[Existing: Books table]
    └──stores──> [average_rating, review_count] (cached aggregate fields)
    └──required by──> [Submit review] (book must exist)

[Review record]
    └──requires──> [Book exists in catalog]
    └──requires──> [User is authenticated]
    └──requires──> [User has purchased this book] (verified-purchase gate)
    └──unique constraint on──> [(book_id, user_id)]

[Average rating on book detail]
    └──derived from──> [Review records] (via stored fields or live aggregate)
    └──updated by──> [Submit review] (increment review_count, recalculate average)
    └──updated by──> [Delete review] (decrement review_count, recalculate average)
    └──updated by──> [Edit review] (recalculate average if star rating changed)

[Admin: delete review]
    └──requires──> [Admin role on JWT]
    └──triggers──> [Aggregate recalculation] (same as user delete)
```

### Dependency Notes

- **Verified-purchase gate requires the existing orders + order_items tables:** No new data is needed. A JOIN from `order_items` to `orders` to `books` filtered by `orders.user_id = current_user.id` is sufficient. This is a read-only check.
- **Average rating depends on the recalculation strategy:** Two valid approaches: (A) store `average_rating` and `review_count` directly on the `books` table, update on every review mutation — fast reads, requires careful update logic; (B) compute `AVG(rating)` and `COUNT(*)` live from the `reviews` table — always accurate, slightly slower at high volume. At this bookstore scale, option A is recommended (see ARCHITECTURE.md).
- **Edit review must trigger aggregate recalculation only when star rating changes:** If the user edits only the text body, no recalculation is needed. Check `old_rating != new_rating` before updating aggregate.
- **One-review-per-user-per-book constraint must be enforced at both database level (unique index) and service layer (409 response).** Database constraint catches race conditions; service layer provides a human-readable error message.

---

## MVP Definition

### This Milestone (v2.0) — Launch With

All of the following must ship together. They constitute the milestone deliverables.

- [ ] `Review` model + Alembic migration (`id`, `book_id`, `user_id`, `rating` [1-5], `body` [nullable text], `created_at`, `updated_at`)
- [ ] Unique DB index on `(book_id, user_id)` — enforces one review per user per book
- [ ] `average_rating` (Float, nullable) and `review_count` (Integer, default 0) columns on `Book` model via Alembic migration
- [ ] Verified-purchase check service: confirms `user_id` has a completed order containing `book_id`
- [ ] Submit review: `POST /books/{book_id}/reviews` — auth required, verified-purchase gate, one-per-user check, updates book aggregate
- [ ] List reviews for a book: `GET /books/{book_id}/reviews` — public, paginated, sorted by `created_at DESC`
- [ ] Edit own review: `PATCH /reviews/{review_id}` — owner only, updates aggregate if rating changed
- [ ] Delete own review: `DELETE /reviews/{review_id}` — owner only, updates aggregate
- [ ] Admin delete any review: `DELETE /admin/reviews/{review_id}` — admin role, updates aggregate
- [ ] Book detail response updated: include `average_rating` and `review_count` fields
- [ ] Book detail response: include `user_has_reviewed: bool` for authenticated users (optional but LOW complexity, high UX value)

### Add After Validation (v2.x)

- [ ] Rating distribution breakdown (`rating_breakdown: {1: N, 2: N, ...}`) — low complexity, high trust signal; hold until v2.0 is stable
- [ ] Reviewer display name in review list response — requires `display_name` field on User model, minor schema addition
- [ ] Helpfulness voting — only add if review volume justifies it; evaluate after 90 days

### Future Consideration (v3+)

- [ ] Sort reviews by helpfulness — requires helpfulness voting first
- [ ] Review photos / media upload — requires object storage infrastructure (S3, etc.)
- [ ] Email prompt to leave review after order delivery — requires review system stable + email template work
- [ ] Review import from Goodreads or other platforms — complex data normalization, legal/IP questions

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Submit review (star + text) | HIGH | LOW | P1 |
| List reviews for a book | HIGH | LOW | P1 |
| Average rating on book detail | HIGH | LOW | P1 |
| Review count on book detail | HIGH | LOW | P1 |
| Edit own review | MEDIUM | LOW | P1 |
| Delete own review | MEDIUM | LOW | P1 |
| Admin delete any review | MEDIUM | LOW | P1 |
| Verified-purchase gate | HIGH | MEDIUM | P1 (core trust feature) |
| One-review-per-user constraint | HIGH | LOW | P1 (data integrity) |
| `user_has_reviewed` flag on book detail | MEDIUM | LOW | P1 (cheap, prevents double-submit confusion) |
| Rating distribution breakdown | MEDIUM | LOW | P2 |
| Reviewer display name | LOW | LOW | P2 |
| Helpfulness voting | LOW | HIGH | P3 (defer) |
| Review photos | LOW | HIGH | P3 (defer) |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Based on the established patterns of Amazon, Goodreads, and standard e-commerce review platforms:

| Feature | Amazon | Goodreads | Our v2.0 Approach |
|---------|--------|-----------|-------------------|
| Star rating scale | 1-5 stars | 1-5 stars | 1-5 stars (universal expectation) |
| Verified purchase badge | Yes (prominent) | No (no purchase gate) | Yes — verified purchase required to submit, not just badged |
| One review per user | Yes | Yes | Yes — unique DB constraint |
| Text body required | No | No | No — rating only is valid; body is optional |
| Edit own review | Yes | Yes | Yes |
| Delete own review | Yes | Yes | Yes |
| Admin moderation | Yes | Yes | Yes — admin delete |
| Rating distribution | Yes (bar chart) | Yes | Deferred to v2.x (data available, UI is frontend concern) |
| Helpfulness voting | Yes ("helpful" button) | Yes | No — scope too large for v2.0 |
| Photo uploads | Yes | No | No — out of scope |
| Pre-moderation queue | No (post-moderation) | No (post-moderation) | No — reactive admin delete |
| Sort options | Helpful, Recent, Critical | Date, Recommended | Recent-first only in v2.0 |

---

## Existing System Integration Points

These are the specific hooks where new v2.0 features attach to existing code.

| New Feature | Attaches To | How |
|-------------|-------------|-----|
| Verified-purchase check | `Order` + `OrderItem` models | Read-only JOIN: `order_items.book_id = ? AND orders.user_id = ? AND orders.status = 'completed'` |
| Average rating on book detail | `Book` model | Add `average_rating` (Float) and `review_count` (Integer) columns via Alembic migration |
| Review submit | `BookService` or new `ReviewService` | After writing review, update `books.average_rating` and `books.review_count` in same transaction |
| Book detail response | `BookSchema` / book detail serializer | Add `average_rating`, `review_count`, `user_has_reviewed` to existing response schema |
| Admin review delete | Existing admin router pattern | Add `DELETE /admin/reviews/{id}` alongside existing `/admin/users` routes |

---

## Sources

- [Product Reviews and Ratings UX — Smashing Magazine](https://www.smashingmagazine.com/2023/01/product-reviews-ratings-ux/) — comprehensive UX patterns for review systems; verified-purchase credibility, distribution displays, anti-patterns (MEDIUM confidence — industry-recognized publication, 2023)
- [Reviews and Ratings UX — Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/reviews-and-ratings-ux/) — table stakes and differentiators for e-commerce review UX (MEDIUM confidence — UX reference site)
- [Goodreads Rating and Review Guidelines](https://www.goodreads.com/review/guidelines) — real-world policy decisions for a book-specific review platform (HIGH confidence — official platform guidelines)
- [Bazaarvoice: Ratings and Reviews Platform](https://www.bazaarvoice.com/products/ratings-and-reviews/) — enterprise review platform patterns; moderation and authenticity approaches (MEDIUM confidence — vendor documentation)
- [Bazaarvoice: Authenticity Rules to Combat Fake Reviews](https://www.bazaarvoice.com/blog/authenticity-rules-combat-fake-reviews/) — fake review vectors and moderation patterns (MEDIUM confidence)
- [FTC Fake Reviews Rule 2024](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials) — legal constraints on incentivized reviews; civil penalties up to $51,744 per violation (HIGH confidence — official government source)
- [Implementing Event Average Rating with SQLAlchemy — FOSSASIA](https://blog.fossasia.org/implementing-event-average-rating-with-sqlalchemy/) — stored aggregate vs. live compute pattern in SQLAlchemy context (MEDIUM confidence)
- [FastAPI SQLAlchemy 2.0 Async Patterns — Medium 2025](https://dev-faizan.medium.com/fastapi-sqlalchemy-2-0-modern-async-database-patterns-7879d39b6843) — modern async patterns for aggregate update queries (LOW confidence — blog post, unverified claims)
- [commercetools Reviews API](https://docs.commercetools.com/api/projects/reviews) — production review API design patterns (HIGH confidence — official API documentation)

---

*Feature research for: BookStore v2.0 — Reviews & Ratings*
*Researched: 2026-02-26*
