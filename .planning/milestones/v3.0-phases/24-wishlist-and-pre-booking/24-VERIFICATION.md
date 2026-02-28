---
phase: 24-wishlist-and-pre-booking
verified: 2026-02-28T00:00:00Z
status: passed
score: 12/12 must-haves verified
human_verification:
  - test: "Wishlist heart toggle — optimistic UI on BookCard (catalog grid)"
    expected: "Clicking the heart fills it red instantly, toast appears, second click unfills it"
    why_human: "Optimistic timing and visual state swap cannot be verified by static file inspection"
  - test: "Wishlist heart toggle — ActionButtons on book detail page"
    expected: "Heart button label changes from 'Add to Wishlist' to 'Wishlisted' with filled red heart; second click reverts"
    why_human: "Requires live component rendering and shared TanStack Query cache interaction"
  - test: "Unauthenticated heart click redirects to /login"
    expected: "Clicking heart while logged out shows toast error and navigates to /login"
    why_human: "Requires browser session state; cannot verify redirect behaviour from static analysis"
  - test: "Pre-book button appears on out-of-stock book detail page"
    expected: "Book with stock_quantity=0 shows 'Pre-book' button, no 'Add to Cart'"
    why_human: "Requires a real out-of-stock book in the database to trigger the inStock=false branch"
  - test: "Duplicate pre-book shows specific error toast"
    expected: "Second pre-book click shows 'You already have an active pre-booking for this book'"
    why_human: "Requires live API returning 409 PREBOOK_DUPLICATE; cannot simulate 409 from static read"
  - test: "Wishlist page SSR + cache takeover — items display correctly"
    expected: "SSR-fetched items render on first paint; after hydration TanStack Query cache takes over without flash"
    why_human: "Hydration timing and SSR/CSR data handoff requires browser inspection"
  - test: "Pre-booking cancel — optimistic removal from account page"
    expected: "Clicking Cancel removes pre-booking row immediately; 'Pre-booking cancelled' toast appears"
    why_human: "Optimistic useState update with rollback on error requires live runtime testing"
  - test: "Human sign-off from 24-03-SUMMARY.md"
    expected: "Human typed 'approved' in browser session as part of Plan 03 verification checkpoint"
    why_human: "Plan 03 was a human-only verification plan; approval was given but occurred outside automated traceability"
---

# Phase 24: Wishlist and Pre-booking Verification Report

**Phase Goal:** Wishlist toggle, wishlist page, pre-book for out-of-stock, pre-booking management
**Verified:** 2026-02-28
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can tap heart on BookCard (catalog grid) and it fills red instantly (optimistic) | VERIFIED | `BookCard.tsx` calls `useWishlist()`, derives `isWishlisted`, `handleHeartClick` uses `e.stopPropagation()`, Heart renders with `fill-red-500 text-red-500` when wishlisted |
| 2 | User can tap heart on ActionButtons (book detail page) and it fills red instantly (optimistic) | VERIFIED | `ActionButtons.tsx` calls `useWishlist()`, renders live Heart with `isWishlisted ? 'fill-red-500 text-red-500' : ''`, label switches "Wishlisted"/"Add to Wishlist" |
| 3 | A second tap on a filled heart unfills it and removes the book from wishlist | VERIFIED | `handleToggle` in `wishlist.ts` mutates with `{ bookId, isWishlisted: wishlistedIds.has(bookId) }`, `mutationFn` calls `removeFromWishlist` when `isWishlisted=true` |
| 4 | Unauthenticated user tapping heart gets toast error and redirect to /login | VERIFIED | `handleToggle` checks `!session?.accessToken`, calls `toast.error('Please sign in to save books to your wishlist')` and `router.push('/login')` |
| 5 | Out-of-stock book shows Pre-book button instead of Add to Cart on book detail page | VERIFIED | `ActionButtons.tsx` conditional: `inStock ? <Add to Cart> : <Pre-book onClick={() => handlePrebook(bookId)}>` |
| 6 | User can click Pre-book and receives success toast; duplicate pre-book shows descriptive error | VERIFIED | `prebook.ts` `onSuccess` → `toast.success('Pre-booking confirmed! We will notify you when this book is back in stock.')`, `onError` checks `ApiError 409` detail for `PREBOOK_DUPLICATE` |
| 7 | User can view /wishlist page showing saved books with cover, title, author, price, and stock badge | VERIFIED | `wishlist/page.tsx` server-fetches, `WishlistList.tsx` renders cover thumbnail, title, author, price, In Stock/Out of Stock badge per item |
| 8 | User can remove a book from the wishlist page and item disappears immediately (optimistic) | VERIFIED | `WishlistList.tsx` remove button calls `handleToggle(item.book_id)` which triggers optimistic removal via `onMutate` in `useWishlist` |
| 9 | User can see active pre-bookings listed on the /account page | VERIFIED | `account/page.tsx` calls `fetchPrebooks(session.accessToken)`, filters non-cancelled, passes to `PrebookingsList` rendered in `<div className="mt-8">` |
| 10 | User can cancel a pre-booking and it disappears from the list | VERIFIED | `PrebookingsList.tsx` `cancelMutation.onMutate` filters item from `localPrebooks` optimistically, restores on error |
| 11 | Wishlist link appears in Header nav and MobileNav drawer | VERIFIED | `Header.tsx` has `<Link href="/wishlist">Wishlist</Link>` in desktop `<nav>`; `MobileNav.tsx` has `{ href: '/wishlist', label: 'Wishlist' }` in `navLinks` |
| 12 | Loading skeleton shows during wishlist page load | VERIFIED | `wishlist/loading.tsx` renders 3 Skeleton rows matching wishlist list layout |

**Score:** 12/12 truths verified (automated code check)

---

## Required Artifacts

### Plan 24-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/wishlist.ts` | useWishlist hook with optimistic toggle, WISHLIST_KEY shared cache | VERIFIED | 145 lines; exports `useWishlist`, `WISHLIST_KEY`, `fetchWishlist`, `addToWishlist`, `removeFromWishlist`; full optimistic update with `onMutate`/`onError`/`onSettled` |
| `frontend/src/lib/prebook.ts` | usePrebook hook with pre-book mutation | VERIFIED | 110 lines; exports `usePrebook`, `PREBOOK_KEY`, `createPrebook`, `cancelPrebook`, `fetchPrebooks`; 409 error detail matching for PREBOOK_DUPLICATE and IN_STOCK |
| `frontend/src/app/catalog/_components/BookCard.tsx` | Heart icon top-left, wired to useWishlist | VERIFIED | Imports `useWishlist`, `Heart`; `handleHeartClick` with `stopPropagation`; heart button at `absolute top-2 left-2`; `fill-red-500 text-red-500` when wishlisted |
| `frontend/src/app/books/[id]/_components/ActionButtons.tsx` | Live heart toggle + Pre-book for out-of-stock | VERIFIED | Imports `useWishlist` and `usePrebook`; conditional renders Pre-book when `!inStock`; live Heart button with Wishlisted/Add to Wishlist label |

### Plan 24-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/app/wishlist/page.tsx` | Server-rendered wishlist page with auth guard | VERIFIED | Contains `auth()`, `redirect('/login')`, `fetchWishlist`, passes `data.items` to `WishlistList` |
| `frontend/src/app/wishlist/_components/WishlistList.tsx` | Client component for wishlist items with remove | VERIFIED | Contains `useWishlist`, renders cover/title/author/price/stock badge per item, remove via `handleToggle` |
| `frontend/src/app/wishlist/loading.tsx` | Loading skeleton for wishlist page | VERIFIED | 3-row Skeleton layout matching wishlist item structure |
| `frontend/src/app/account/_components/PrebookingsList.tsx` | Client component with cancel mutation | VERIFIED | Contains `cancelPrebook`, `PREBOOK_KEY`, `useState` for optimistic removal, cancel only for `status === 'waiting'` |
| `frontend/src/app/account/page.tsx` | Updated account hub with wishlist card and pre-bookings | VERIFIED | Contains `PrebookingsList`, `fetchPrebooks`, Wishlist card link, inline pre-bookings section |
| `frontend/src/components/layout/Header.tsx` | Wishlist link in desktop nav | VERIFIED | `<Link href="/wishlist">Wishlist</Link>` between Books and Account links |
| `frontend/src/components/layout/MobileNav.tsx` | Wishlist entry in mobile nav | VERIFIED | `{ href: '/wishlist', label: 'Wishlist' }` in `navLinks` array after Cart |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `BookCard.tsx` | `wishlist.ts` | `useWishlist()` hook | WIRED | Import present; `wishlistedIds`, `handleToggle`, `isPending` all consumed |
| `ActionButtons.tsx` | `wishlist.ts` | `useWishlist()` hook | WIRED | Import present; `wishlistedIds`, `handleToggle`, `isPending` all consumed |
| `ActionButtons.tsx` | `prebook.ts` | `usePrebook()` hook | WIRED | Import present; `handlePrebook`, `isPending` consumed; conditional Pre-book button rendered |
| `WishlistList.tsx` | `wishlist.ts` | `useWishlist()` for remove mutation | WIRED | Import present; `wishlistQuery.data?.items` for cache takeover; `handleToggle` on remove button |
| `PrebookingsList.tsx` | `prebook.ts` | `cancelPrebook` and `PREBOOK_KEY` | WIRED | Both imported and consumed in `cancelMutation` `mutationFn` and `invalidateQueries` |
| `account/page.tsx` | `prebook.ts` | `fetchPrebooks` server-side call | WIRED | Imported and called inside `try { const data = await fetchPrebooks(session.accessToken) }` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WISH-01 | 24-01 | User can add a book to their wishlist from catalog or detail page | SATISFIED | Heart on BookCard + ActionButtons; `handleToggle` calls `addToWishlist` when not wishlisted |
| WISH-02 | 24-01 | User can remove a book from their wishlist | SATISFIED | Heart second-tap calls `removeFromWishlist`; WishlistList trash button also calls `handleToggle` |
| WISH-03 | 24-02 | User can view their wishlist with book details and current price/stock | SATISFIED | `/wishlist/page.tsx` + `WishlistList.tsx` render cover, title, author, price, stock badge |
| WISH-04 | 24-01 | Wishlist toggle uses optimistic update (instant heart icon feedback) | SATISFIED | `onMutate` in `useWishlist` updates query cache immediately; `onError` rolls back to snapshot |
| PREB-01 | 24-01 | User sees "Pre-book" button instead of "Add to Cart" when a book is out of stock | SATISFIED | `ActionButtons.tsx` ternary on `inStock` prop |
| PREB-02 | 24-01 | User can pre-book an out-of-stock book | SATISFIED | `usePrebook.prebookMutation` calls `createPrebook`; success + 409-aware error toasts |
| PREB-03 | 24-02 | User can view active pre-bookings on their account page | SATISFIED | `account/page.tsx` fetches + filters non-cancelled; `PrebookingsList` renders them inline |
| PREB-04 | 24-02 | User can cancel a pre-booking | SATISFIED | `PrebookingsList.tsx` `cancelMutation` with optimistic local state removal |

No orphaned requirements — all 8 IDs declared in plan frontmatter match requirement entries and are accounted for.

---

## Anti-Patterns Found

No anti-patterns detected across all 11 modified/created files.

Scan covered: TODO/FIXME/HACK/PLACEHOLDER markers, empty implementations (`return null`, `return {}`, `=> {}`), stub handlers.

Result: Clean — no blockers, no warnings.

---

## Commit Verification

All 4 commits documented in SUMMARY files are confirmed present in git history:

| Commit | Description | Plan |
|--------|-------------|------|
| `824d73f` | feat(24-01): create useWishlist and usePrebook hooks | 24-01 |
| `dfb6130` | feat(24-01): wire wishlist heart and pre-book button into BookCard and ActionButtons | 24-01 |
| `8c5162d` | feat(24-02): create /wishlist page with WishlistList component and loading skeleton | 24-02 |
| `22740ee` | feat(24-02): add pre-bookings to account page and Wishlist to navigation | 24-02 |

---

## Human Verification Required

Plan 24-03 was a dedicated human verification checkpoint. According to `24-03-SUMMARY.md`, the human typed "approved" after testing all 8 requirements in the browser. That approval is recorded in the SUMMARY but is not independently re-testable from this automated pass.

The following items require human confirmation if a fresh sign-off is needed:

### 1. Wishlist Heart Toggle — Optimistic Visual Feedback

**Test:** Go to `/catalog`, hover a book card, click the heart icon.
**Expected:** Heart fills red immediately (no loading spinner), "Added to wishlist" toast appears. Second click: heart unfills, "Removed from wishlist" toast.
**Why human:** Optimistic timing and visual state swap are runtime behaviours; CSS class presence is verified but rendering requires a browser.

### 2. Cross-Surface Wishlist Sync

**Test:** Add a book to wishlist from catalog, navigate to that book's detail page.
**Expected:** ActionButtons heart shows "Wishlisted" with filled heart — shared `WISHLIST_KEY` TanStack Query cache keeps both surfaces in sync.
**Why human:** Shared cache behaviour across route navigation requires live browser session.

### 3. Unauthenticated Guard — Heart and Pre-book

**Test:** Log out, click a heart on the catalog, click Pre-book on an out-of-stock detail page.
**Expected:** Both show toast error and redirect to `/login`.
**Why human:** Requires active logged-out session state.

### 4. Pre-book Button Conditionality

**Test:** Find or set a book with `stock_quantity=0` in the database, visit its detail page.
**Expected:** "Pre-book" button is shown, "Add to Cart" is absent.
**Why human:** Requires a real out-of-stock record in the database.

### 5. Duplicate Pre-book Error Toast

**Test:** Pre-book the same out-of-stock book twice.
**Expected:** Second attempt shows "You already have an active pre-booking for this book" (from 409 PREBOOK_DUPLICATE).
**Why human:** Requires live API 409 response.

### 6. Pre-booking Cancel — Optimistic Removal

**Test:** Go to `/account`, click Cancel on a waiting pre-booking.
**Expected:** Row disappears immediately, "Pre-booking cancelled" toast appears.
**Why human:** Optimistic `useState` local state manipulation requires live browser rendering.

### 7. Wishlist Page — SSR Hydration

**Test:** Navigate directly to `/wishlist` with wishlisted books.
**Expected:** Items appear on first paint (SSR), no flash of empty state after hydration.
**Why human:** SSR/CSR handoff timing requires browser devtools or network throttling to observe.

---

## Gaps Summary

No automated gaps found. All 12 must-have truths are supported by substantive, wired code. All 8 requirement IDs are satisfied. No anti-patterns. All commits verified.

The only outstanding items are runtime behaviours (optimistic timing, session-gated redirects, live API 409 responses) that require a browser. These were exercised and approved in Plan 24-03 by the human verifier typing "approved". If a fresh sign-off is required, the 7 items above cover the full test matrix.

---

_Verified: 2026-02-28_
_Verifier: Claude (gsd-verifier)_
