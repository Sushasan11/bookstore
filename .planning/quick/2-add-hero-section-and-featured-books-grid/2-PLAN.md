---
phase: quick-2
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/app/(store)/page.tsx
  - frontend/src/app/(store)/_components/HeroSection.tsx
  - frontend/src/app/(store)/_components/FeaturedBooks.tsx
autonomous: true
requirements: []

must_haves:
  truths:
    - "Homepage shows an inviting hero banner with headline, tagline, and a CTA button to browse the catalog"
    - "Homepage displays a grid of top-rated books fetched from the API"
    - "Homepage displays a grid of newest arrivals fetched from the API"
    - "Each book in the featured grids links to its detail page and shows cover, title, author, and price"
    - "Page works as a server component with no client-side data fetching for the book grids"
  artifacts:
    - path: "frontend/src/app/(store)/page.tsx"
      provides: "Refactored homepage composing HeroSection and FeaturedBooks"
    - path: "frontend/src/app/(store)/_components/HeroSection.tsx"
      provides: "Hero banner with headline, tagline, and Browse Books CTA"
    - path: "frontend/src/app/(store)/_components/FeaturedBooks.tsx"
      provides: "Reusable server component rendering a labeled book grid"
  key_links:
    - from: "frontend/src/app/(store)/page.tsx"
      to: "/books?sort=avg_rating&sort_dir=desc&size=4"
      via: "fetchBooks() from @/lib/catalog"
      pattern: "fetchBooks.*avg_rating"
    - from: "frontend/src/app/(store)/page.tsx"
      to: "/books?sort=created_at&sort_dir=desc&size=4"
      via: "fetchBooks() from @/lib/catalog"
      pattern: "fetchBooks.*created_at"
    - from: "frontend/src/app/(store)/_components/FeaturedBooks.tsx"
      to: "frontend/src/app/(store)/catalog/_components/BookCard.tsx"
      via: "imports and renders BookCard for each book"
      pattern: "import.*BookCard"
---

<objective>
Replace the placeholder homepage (health-check only) with a proper landing page featuring a hero section and two featured book grids (top-rated and newest arrivals).

Purpose: Give visitors an engaging first impression with curated book recommendations instead of a bare status page.
Output: Three new/modified files creating the complete homepage experience.
</objective>

<execution_context>
@C:/Users/Sushasan/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Sushasan/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md

Existing patterns and key files:
- `frontend/src/lib/catalog.ts` — `fetchBooks({ sort, sort_dir, size })` returns `BookListResponse` with `.items` array of `BookResponse`
- `frontend/src/app/(store)/catalog/_components/BookCard.tsx` — client component rendering a single book card with cover placeholder, price, stock badge, cart/wishlist buttons
- `frontend/src/app/(store)/catalog/_components/BookGrid.tsx` — server component rendering a grid of BookCard items in a `grid-cols-2 md:grid-cols-4` layout
- `frontend/src/app/(store)/layout.tsx` — wraps children with Header + Footer
- `frontend/src/components/brand/BookStoreLogo.tsx` — reusable logo component with variant/iconSize props

API sort options for /books endpoint: "title", "price", "date", "created_at", "avg_rating"
- `sort=avg_rating&sort_dir=desc` gives highest-rated books
- `sort=created_at&sort_dir=desc` gives newest additions

BookResponse fields: id, title, author, price, isbn, genre_id, description, cover_image_url, publish_date, stock_quantity, avg_rating, review_count
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create HeroSection and FeaturedBooks components</name>
  <files>
    frontend/src/app/(store)/_components/HeroSection.tsx,
    frontend/src/app/(store)/_components/FeaturedBooks.tsx
  </files>
  <action>
Create a `_components` directory inside `frontend/src/app/(store)/` for page-level components shared across the store homepage.

**HeroSection.tsx — Server component (no 'use client'):**

Create a visually appealing hero banner. Structure:
- Full-width section with generous vertical padding (`py-20 md:py-28`)
- Centered content with `max-w-3xl mx-auto text-center`
- Large heading: "Your Next Great Read Awaits" — use `text-4xl md:text-5xl font-bold tracking-tight`
- Subtitle paragraph beneath: "Browse our curated collection of books across every genre. From bestsellers to hidden gems, find your perfect read." — use `mt-4 text-lg text-muted-foreground max-w-xl mx-auto`
- CTA button: Link to `/catalog` styled as a primary Button (import from `@/components/ui/button`) with text "Browse All Books" and an `ArrowRight` icon from lucide-react. Use `mt-8` spacing. Wrap the Button with a Next.js `Link` (use `asChild` on Button so the Link is the actual anchor element).
- Subtle decorative background: apply `bg-muted/50` to the section wrapper for a gentle contrast against the white page background. Add `border-b` at the bottom.

```tsx
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function HeroSection() {
  return (
    <section className="border-b bg-muted/50 px-4 py-20 md:py-28">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
          Your Next Great Read Awaits
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
          Browse our curated collection of books across every genre. From
          bestsellers to hidden gems, find your perfect read.
        </p>
        <div className="mt-8">
          <Button asChild size="lg">
            <Link href="/catalog">
              Browse All Books
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
```

**FeaturedBooks.tsx — Client component ('use client' required because BookCard uses useCart/useWishlist hooks):**

A reusable section that receives a title, a books array, and an optional "View all" link. It renders a heading row with a "View all" link on the right, then a grid of BookCard components.

```tsx
'use client'

import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { BookCard } from '@/app/(store)/catalog/_components/BookCard'
import type { BookResponse } from '@/lib/catalog'

interface FeaturedBooksProps {
  title: string
  books: BookResponse[]
  viewAllHref: string
  viewAllLabel?: string
}

export function FeaturedBooks({
  title,
  books,
  viewAllHref,
  viewAllLabel = 'View all',
}: FeaturedBooksProps) {
  if (books.length === 0) return null

  return (
    <section>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
        <Link
          href={viewAllHref}
          className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
        >
          {viewAllLabel}
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>
    </section>
  )
}
```

Note: BookCard is a client component (uses useCart, useWishlist, useSession), so FeaturedBooks must also be a client component. The data fetching happens in the server-rendered page.tsx and is passed as props.
  </action>
  <verify>
    <automated>test -f "frontend/src/app/(store)/_components/HeroSection.tsx" &amp;&amp; test -f "frontend/src/app/(store)/_components/FeaturedBooks.tsx" &amp;&amp; echo "Both components created"</automated>
  </verify>
  <done>HeroSection.tsx exists as a server component with hero headline, tagline, and CTA linking to /catalog. FeaturedBooks.tsx exists as a client component accepting title, books array, and viewAllHref props, rendering BookCard grid.</done>
</task>

<task type="auto">
  <name>Task 2: Refactor homepage to compose hero and featured book sections</name>
  <files>
    frontend/src/app/(store)/page.tsx
  </files>
  <action>
Rewrite `frontend/src/app/(store)/page.tsx` as a **server component** (remove 'use client' and the useQuery health check). The new page fetches featured books server-side and composes the sections.

Read the existing file first (`frontend/src/app/(store)/page.tsx`), then replace entirely.

**New page.tsx structure:**

```tsx
import { Suspense } from 'react'
import type { Metadata } from 'next'
import { fetchBooks } from '@/lib/catalog'
import { HeroSection } from './_components/HeroSection'
import { FeaturedBooks } from './_components/FeaturedBooks'
import { BookGridSkeleton } from './catalog/_components/BookCardSkeleton'

export const metadata: Metadata = {
  title: 'BookStore — Discover Your Next Great Read',
  description:
    'Browse our curated collection of books across every genre. From bestsellers to hidden gems.',
}

export default async function HomePage() {
  const [topRated, newest] = await Promise.all([
    fetchBooks({ sort: 'avg_rating', sort_dir: 'desc', size: 4 }),
    fetchBooks({ sort: 'created_at', sort_dir: 'desc', size: 4 }),
  ])

  return (
    <>
      <HeroSection />

      <div className="mx-auto max-w-7xl px-4 py-12 space-y-16">
        <FeaturedBooks
          title="Top Rated"
          books={topRated.items}
          viewAllHref="/catalog?sort=avg_rating&sort_dir=desc"
          viewAllLabel="View all top rated"
        />

        <FeaturedBooks
          title="New Arrivals"
          books={newest.items}
          viewAllHref="/catalog?sort=created_at&sort_dir=desc"
          viewAllLabel="View all new arrivals"
        />
      </div>
    </>
  )
}
```

Key design decisions:
- **Server component** — no 'use client' directive. Data fetched at request time server-side via `fetchBooks()` (same function the catalog page uses). This means zero client-side loading spinners for the book data.
- **Parallel fetch** — `Promise.all` for both queries concurrently.
- **4 books per section** — enough to fill one row of the `grid-cols-2 md:grid-cols-4` grid without scrolling.
- **Remove old health check** — The health check widget was a dev-time integration test; it has no place on a customer-facing homepage. If needed later, it can be a footer badge or admin-only widget.
- **Metadata** — Set a proper page title for SEO.
- **Spacing** — `space-y-16` between sections gives generous vertical rhythm. `py-12` top/bottom padding for the content area.

The "View all" links include sort params so users land on the catalog pre-sorted by the same criteria.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx tsc --noEmit 2>&amp;1 | head -30</automated>
  </verify>
  <done>Homepage renders HeroSection at top, then Top Rated grid (4 books sorted by avg_rating desc), then New Arrivals grid (4 books sorted by created_at desc). TypeScript compiles with no new errors. Old health-check widget removed.</done>
</task>

</tasks>

<verification>
After both tasks complete:
1. TypeScript check: `cd frontend && npx tsc --noEmit` — no new errors
2. Start dev server: `cd frontend && npm run dev`
3. Visit http://localhost:3000 — hero section visible with "Your Next Great Read Awaits" heading and "Browse All Books" CTA
4. Below the hero: "Top Rated" section showing 4 book cards with covers, titles, authors, prices
5. Below that: "New Arrivals" section showing 4 book cards
6. Click "Browse All Books" CTA — navigates to /catalog
7. Click "View all top rated" — navigates to /catalog?sort=avg_rating&sort_dir=desc
8. Click any book card — navigates to /books/{id} detail page
9. Cart and wishlist buttons on book cards function correctly
</verification>

<success_criteria>
- Hero section displays with headline, tagline, and working CTA link to /catalog
- Top Rated section shows 4 books sorted by average rating (descending)
- New Arrivals section shows 4 books sorted by created_at (descending)
- Each book card shows cover (or placeholder), title, author, price, stock badge
- Cart and wishlist buttons work on featured book cards
- Page is a server component — book data fetched server-side, no loading spinners
- `npx tsc --noEmit` passes with no new TypeScript errors
</success_criteria>

<output>
After completion, create `.planning/quick/2-add-hero-section-and-featured-books-grid/2-SUMMARY.md`
</output>
