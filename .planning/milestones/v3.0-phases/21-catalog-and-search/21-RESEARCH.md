# Phase 21: Catalog and Search - Research

**Researched:** 2026-02-27
**Domain:** Next.js 16 App Router — server components, ISR, URL search params, SEO metadata, shadcn/ui
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Catalog grid layout:**
- Book cover cards: prominent cover image with title, author, price below
- 4 cards per row on desktop, 2 per row on mobile
- Missing cover images: styled placeholder showing book title and author on a colored background
- No hero/banner section — page title, search bar, then straight into the grid

**Book detail page:**
- Cover-left, details-right layout (classic e-commerce two-column)
- Stacks vertically on mobile (cover on top, details below)
- Breadcrumbs: Home > Genre > Book Title
- Rating display: aggregate stars + review count only (clickable, but full review section is Phase 25)
- Action buttons: show "Add to Cart" and "Wishlist" as disabled placeholders — later phases enable them
- "More in this genre" section at the bottom: horizontal row of 4-6 same-genre books
- Metadata shown: ISBN, genre, publish date, description

**Search and filters UX:**
- Search bar at top of catalog page (not in global navbar)
- Inline dropdown filters in a horizontal bar: Genre, Price Range, Sort
- Debounced as-you-type search (~300ms after user stops typing)
- No-results state: friendly message ("No books found for X") with suggestions (check spelling, try broader search, browse genres) and popular books below

**Pagination and loading:**
- Classic numbered pagination (1, 2, 3... Next) with URL reflecting page number
- 20 books per page (5 rows of 4 on desktop)
- Skeleton card loading states matching grid layout while fetching
- Sort options: Relevance (default), Price low-to-high, Price high-to-low, Newest, Highest rated

**URL state persistence:**
- All search, filter, sort, and page state persisted in URL query params
- Bookmarkable and shareable: opening a shared URL reproduces exact results
- Example: `/catalog?q=fantasy&genre=fiction&sort=price_asc&page=2`

**SEO:**
- JSON-LD Book schema on detail pages
- Open Graph meta tags on detail pages
- Server-rendered with ISR for crawlability

### Claude's Discretion

- Card information density (which specific fields to show per card — cover, title, author, price are minimum; stars, stock badge, genre tag, review count are optional)
- Exact skeleton card design
- Price range filter implementation (slider vs preset ranges)
- Sort dropdown behavior details
- Breadcrumb styling
- Responsive breakpoints
- Error state handling (API failures, timeouts)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CATL-01 | User can browse paginated book grid with cover, title, author, price, and stock status | BookCard component + catalog page with ISR, `GET /books?page=N&size=20` |
| CATL-02 | User can view book detail page with description, average rating, review count, and stock status | `GET /books/{id}` returns `BookDetailResponse` with `avg_rating`, `review_count`, `in_stock` |
| CATL-03 | User can search books by title, author, or genre using full-text search | Backend `GET /books?q=` supports full-text search; debounced client search input updates URL params |
| CATL-04 | User can filter search results by genre and price range | `GET /books?genre_id=N` already supported; price range requires client-side filter or backend extension |
| CATL-05 | Search and filter state is persisted in URL (bookmarkable, shareable) | `useSearchParams` + `useRouter().replace()` pattern with `URLSearchParams` |
| CATL-06 | Book detail page has SEO metadata (JSON-LD Book schema, Open Graph tags) | `generateMetadata()` for Open Graph; inline `<script type="application/ld+json">` for JSON-LD |
| CATL-07 | Catalog and book detail pages are server-rendered with ISR for SEO | `export const revalidate = N` on detail page; catalog page is dynamic (searchParams force dynamic) |
</phase_requirements>

---

## Summary

Phase 21 builds the complete public-facing catalog: a filterable/searchable book grid at `/catalog` and individual book detail pages at `/books/[id]`. The backend API (`GET /books`, `GET /books/{id}`, `GET /genres`) is already fully implemented with pagination, full-text search, genre filtering, and sorting. The frontend work is a pure Next.js App Router implementation.

The critical architectural insight for this phase is the rendering split: the **catalog page** (`/catalog`) uses `searchParams` for filtering/sorting/pagination, which forces dynamic server-side rendering (SSR on every request). The **book detail page** (`/books/[id]`) is a stable dynamic route that can use ISR with `export const revalidate = 3600`, giving SEO bots pre-rendered HTML while keeping data fresh hourly. This split is the correct approach — trying to use ISR on the catalog page with searchParams creates a conflict since searchParams are request-time only.

URL state persistence uses the official Next.js pattern: a client `SearchControls` component using `useSearchParams()` + `useRouter().replace()` pushes filter state to the URL, while the server Page component reads `await searchParams` and passes them to a server-rendered results component wrapped in `<Suspense>`. This keeps the catalog page SEO-friendly (server-rendered initial state) while enabling dynamic filter updates without full page reloads.

**Primary recommendation:** Split rendering strategy — catalog page is dynamic SSR (searchParams-driven), book detail page uses ISR (`revalidate = 3600`). Use the official `useSearchParams` + `useRouter().replace()` URL pattern with `use-debounce` for the search input.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js (already installed) | 16.1.6 | App Router, ISR, `generateMetadata`, server components | Project standard — already installed |
| `next/image` | built-in | Optimized book cover images with lazy loading and responsive sizing | Official Next.js — automatic optimization, prevents CLS |
| `use-debounce` | latest (^4.x) | Debounce search input before URL update | Official pattern in Next.js Learn docs; prevents API flooding |
| `schema-dts` | latest | TypeScript types for JSON-LD structured data | Community standard; enables type-safe Book schema construction |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui `skeleton` | add via CLI | Book card skeleton loading states | Already using shadcn/ui — consistent with rest of UI |
| `@tanstack/react-query` | ^5.x (installed) | Client-side mutations / cart actions (Phase 22 prep) | Already installed; NOT needed for catalog SSR data |
| `next/navigation` | built-in | `useSearchParams`, `useRouter`, `usePathname` | Client-side URL manipulation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `use-debounce` | Manual `setTimeout` + `useRef` | `use-debounce` is the documented pattern; manual impl is error-prone (cleanup, StrictMode) |
| Inline `<script>` JSON-LD | `next-seo` library | `next-seo` adds a dependency; Next.js 16 official docs recommend inline `<script>` in RSC |
| `schema-dts` | Plain object literal | `schema-dts` adds type safety; safe to skip if team prefers simplicity — LOW priority |
| ISR on catalog page | Dynamic SSR | searchParams force dynamic anyway; ISR cannot be combined with per-request searchParams |

**Installation:**
```bash
npm install use-debounce
npx shadcn@latest add skeleton
npm install --save-dev schema-dts   # optional, for JSON-LD type safety
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── app/
│   ├── catalog/
│   │   ├── page.tsx              # Server component — reads await searchParams, fetches books
│   │   ├── loading.tsx           # Skeleton grid (automatic Suspense fallback for navigation)
│   │   └── _components/
│   │       ├── SearchControls.tsx      # 'use client' — search input, filters, sort dropdown
│   │       ├── BookGrid.tsx            # Server component — renders grid from fetched data
│   │       ├── BookCard.tsx            # Server component — individual card
│   │       ├── BookCardSkeleton.tsx    # Skeleton card for loading state
│   │       ├── Pagination.tsx          # 'use client' — page links using searchParams
│   │       └── NoResults.tsx           # Empty state component
│   └── books/
│       └── [id]/
│           ├── page.tsx          # Server component — ISR, generateMetadata, JSON-LD
│           └── _components/
│               ├── BookDetailHero.tsx   # Cover + details two-column layout
│               ├── BreadcrumbNav.tsx    # Home > Genre > Title
│               ├── RatingDisplay.tsx    # Stars + review count
│               ├── ActionButtons.tsx    # Disabled Add to Cart + Wishlist buttons
│               └── MoreInGenre.tsx      # Horizontal scroll of related books
├── components/
│   └── ui/
│       └── skeleton.tsx          # Add via: npx shadcn@latest add skeleton
└── lib/
    └── api.ts                    # Existing — extend with typed catalog fetch helpers
```

### Pattern 1: Catalog Page — Dynamic SSR with URL Search Params

**What:** The catalog page reads `searchParams` server-side to fetch filtered/paginated books, while a client SearchControls component updates the URL to trigger server re-renders.
**When to use:** Any page where filters/search must be URL-persistent and SEO-crawlable.

```typescript
// Source: https://nextjs.org/docs/app/guides/upgrading/version-16
// src/app/catalog/page.tsx — Server Component (dynamic, no revalidate needed)

import { Suspense } from 'react'
import { SearchControls } from './_components/SearchControls'
import { BookGrid } from './_components/BookGrid'
import { BookGridSkeleton } from './_components/BookCardSkeleton'
import { Pagination } from './_components/Pagination'

type CatalogPageProps = {
  searchParams: Promise<{
    q?: string
    genre_id?: string
    sort?: string
    page?: string
  }>
}

export default async function CatalogPage({ searchParams }: CatalogPageProps) {
  // CRITICAL: Next.js 16 — searchParams is a Promise, must await
  const params = await searchParams

  const q = params.q ?? ''
  const genreId = params.genre_id ? Number(params.genre_id) : undefined
  const sort = (params.sort ?? 'title') as 'title' | 'price' | 'date' | 'created_at'
  const page = Number(params.page ?? 1)

  // Fetch books server-side (no TanStack Query — this is RSC)
  const [booksData, genres] = await Promise.all([
    fetchBooks({ q, genreId, sort, page, size: 20 }),
    fetchGenres(),
  ])

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Browse Books</h1>
      {/* Client component handles URL updates */}
      <SearchControls genres={genres} initialValues={{ q, genreId, sort, page }} />
      {/* Suspense key triggers re-render when URL changes */}
      <Suspense key={`${q}-${genreId}-${sort}-${page}`} fallback={<BookGridSkeleton />}>
        <BookGrid books={booksData.items} />
      </Suspense>
      <Pagination total={booksData.total} page={page} size={20} />
    </div>
  )
}
```

### Pattern 2: Search + Filter Client Component with Debounce

**What:** Client component reads current URL params, updates them on user interaction with debounce for text input.
**When to use:** Any filter/search UI that must persist state to URL.

```typescript
// Source: https://nextjs.org/learn/dashboard-app/adding-search-and-pagination
// src/app/catalog/_components/SearchControls.tsx
'use client'

import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { useDebouncedCallback } from 'use-debounce'

export function SearchControls({ genres, initialValues }) {
  const searchParams = useSearchParams()
  const { replace } = useRouter()
  const pathname = usePathname()

  // Debounce text search — 300ms after user stops typing
  const handleSearch = useDebouncedCallback((term: string) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', '1')  // Reset to page 1 on new search
    if (term) {
      params.set('q', term)
    } else {
      params.delete('q')
    }
    replace(`${pathname}?${params.toString()}`)
  }, 300)

  // Genre filter — immediate (no debounce needed for dropdown)
  const handleGenreChange = (genreId: string) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', '1')
    if (genreId) {
      params.set('genre_id', genreId)
    } else {
      params.delete('genre_id')
    }
    replace(`${pathname}?${params.toString()}`)
  }

  return (
    <div className="flex gap-4 mb-6">
      <input
        defaultValue={initialValues.q}
        onChange={(e) => handleSearch(e.target.value)}
        placeholder="Search books..."
      />
      {/* Genre, Price Range, Sort dropdowns */}
    </div>
  )
}
```

### Pattern 3: Book Detail Page — ISR with generateMetadata and JSON-LD

**What:** Dynamic route `/books/[id]` with ISR revalidation, Open Graph metadata, and Book JSON-LD structured data.
**When to use:** Detail pages with stable content (book info rarely changes).

```typescript
// Source: https://nextjs.org/docs/app/guides/json-ld + https://nextjs.org/docs/app/guides/incremental-static-regeneration
// src/app/books/[id]/page.tsx

import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

// ISR: revalidate once per hour — book data rarely changes
export const revalidate = 3600

type PageProps = {
  params: Promise<{ id: string }>
}

// Open Graph metadata — generated server-side, cached by ISR
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params  // Next.js 16: params is a Promise
  const book = await fetchBook(Number(id))
  if (!book) return {}

  return {
    title: `${book.title} by ${book.author}`,
    description: book.description ?? `${book.title} — available at Bookstore`,
    openGraph: {
      title: `${book.title} by ${book.author}`,
      description: book.description ?? '',
      type: 'book',
      images: book.cover_image_url ? [{ url: book.cover_image_url }] : [],
    },
  }
}

export default async function BookDetailPage({ params }: PageProps) {
  const { id } = await params
  const book = await fetchBook(Number(id))
  if (!book) notFound()

  // JSON-LD Book schema — rendered server-side in RSC
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Book',
    name: book.title,
    author: { '@type': 'Person', name: book.author },
    isbn: book.isbn,
    description: book.description,
    image: book.cover_image_url,
    offers: {
      '@type': 'Offer',
      price: book.price,
      priceCurrency: 'USD',
      availability: book.in_stock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
    },
  }

  return (
    <div>
      {/* XSS-safe JSON-LD injection — replace < with unicode escape */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c'),
        }}
      />
      {/* ... page content */}
    </div>
  )
}
```

### Pattern 4: API Fetch Helpers for Catalog

**What:** Typed fetch helpers that call the FastAPI backend using the existing `apiFetch` utility.
**When to use:** Server components calling the catalog endpoints.

```typescript
// Extend src/lib/api.ts with catalog helpers (or create src/lib/catalog.ts)
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type BookListResponse = components['schemas']['BookListResponse']
type BookDetailResponse = components['schemas']['BookDetailResponse']
type GenreResponse = components['schemas']['GenreResponse']

export async function fetchBooks(params: {
  q?: string
  genre_id?: number
  sort?: 'title' | 'price' | 'date' | 'created_at'
  page?: number
  size?: number
}): Promise<BookListResponse> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.genre_id) qs.set('genre_id', String(params.genre_id))
  if (params.sort) qs.set('sort', params.sort)
  if (params.page) qs.set('page', String(params.page))
  if (params.size) qs.set('size', String(params.size))
  return apiFetch<BookListResponse>(`/books?${qs}`)
}

export async function fetchBook(id: number): Promise<BookDetailResponse | null> {
  try {
    return await apiFetch<BookDetailResponse>(`/books/${id}`)
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

export async function fetchGenres(): Promise<GenreResponse[]> {
  return apiFetch<GenreResponse[]>('/genres')
}
```

### Pattern 5: Missing Cover Image Placeholder

**What:** Styled div placeholder for books without `cover_image_url`.
**When to use:** Any `BookCard` or detail page where `cover_image_url` is null.

```tsx
// src/app/catalog/_components/BookCard.tsx

function CoverImage({ book }: { book: BookResponse }) {
  if (book.cover_image_url) {
    return (
      <Image
        src={book.cover_image_url}
        alt={`Cover of ${book.title}`}
        fill
        className="object-cover"
        sizes="(max-width: 768px) 50vw, 25vw"
      />
    )
  }
  // Placeholder: book title + author on colored background
  // Use a deterministic color from book ID for visual variety
  const colors = ['bg-blue-100', 'bg-green-100', 'bg-purple-100', 'bg-amber-100', 'bg-rose-100']
  const color = colors[book.id % colors.length]
  return (
    <div className={`absolute inset-0 ${color} flex flex-col items-center justify-center p-3 text-center`}>
      <span className="text-sm font-semibold line-clamp-3">{book.title}</span>
      <span className="text-xs text-muted-foreground mt-1">{book.author}</span>
    </div>
  )
}
```

### Anti-Patterns to Avoid

- **Using TanStack Query for catalog SSR data:** Catalog and detail pages are server components. TanStack Query is for client-side state (already configured for Phase 22 cart). Don't fetch catalog data in `useQuery` — fetch server-side in the async page component.
- **Wrapping catalog page in `'use client'`:** This disables SSR and breaks CATL-07. The page must be a server component; only `SearchControls` and `Pagination` are client components.
- **Using ISR on the catalog page:** `searchParams` forces dynamic rendering (`export const revalidate = N` is ignored when `searchParams` are used). The catalog page is inherently dynamic — accept this and let it SSR.
- **Calling `useSearchParams()` without Suspense boundary:** Components using `useSearchParams()` in Next.js must be wrapped in `<Suspense>` or the build fails. The existing codebase has a precedent for this pattern (LoginForm).
- **XSS in JSON-LD:** Never use `JSON.stringify(jsonLd)` directly in `dangerouslySetInnerHTML`. Always apply `.replace(/</g, '\\u003c')` per official Next.js docs.
- **Synchronous `params`/`searchParams` access:** Next.js 16 made these async — always `await params` and `await searchParams` in server components.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounce search input | Custom `setTimeout` cleanup | `use-debounce` (`useDebouncedCallback`) | Handles React StrictMode double-invoke, cleanup on unmount |
| Book cover image optimization | `<img>` tags | `next/image` | Automatic WebP conversion, lazy loading, blur placeholder, prevents CLS |
| URL query string manipulation | Manual string concatenation | `new URLSearchParams(searchParams)` (Web API) | Handles encoding, existing params preserved correctly |
| Skeleton loading | CSS spinners | shadcn/ui `<Skeleton>` component | Already using shadcn/ui; matches design system |
| SEO metadata | Custom `<head>` injection | `generateMetadata()` + inline JSON-LD `<script>` | Official Next.js pattern; deduplicates, handles streaming |
| TypeScript JSON-LD types | `any` type | `schema-dts` package | Prevents incorrect schema structure |

**Key insight:** The URL param pattern (`URLSearchParams` + `useRouter().replace()`) is the only correct way to persist filter state in Next.js App Router. Don't use `useState` alone — state is lost on navigation and breaks shareability.

---

## Common Pitfalls

### Pitfall 1: searchParams Forces Dynamic Rendering on Catalog Page

**What goes wrong:** Developer adds `export const revalidate = 60` to the catalog page expecting ISR, but the page is still SSR'd on every request. Tests show fresh data each time but Vercel dashboard shows no ISR activity.
**Why it happens:** `searchParams` is a [Dynamic API](https://nextjs.org/docs/app/guides/caching#dynamic-rendering) in Next.js. Any page that uses `searchParams` is automatically opted into dynamic rendering, overriding `revalidate`.
**How to avoid:** Accept that `/catalog` is dynamic. Apply ISR only to `/books/[id]` where the URL doesn't use search params.
**Warning signs:** Expecting cache hits on `/catalog` in production — there won't be any.

### Pitfall 2: Suspense Required for useSearchParams Components

**What goes wrong:** Build succeeds in dev but `npm run build` fails with: "useSearchParams() should be wrapped in a suspense boundary."
**Why it happens:** Components using `useSearchParams()` cannot be statically analyzed at build time — Next.js requires an explicit Suspense boundary.
**How to avoid:** Wrap `SearchControls` and `Pagination` (any client component using `useSearchParams`) in `<Suspense fallback={...}>` in the parent server component. Already established as project pattern (see `LoginForm`).
**Warning signs:** Build passes in dev, fails on `npm run build`.

### Pitfall 3: params and searchParams are Promises in Next.js 16

**What goes wrong:** TypeScript doesn't catch the error, but at runtime `params.id` is `undefined` because `params` is a Promise object.
**Why it happens:** Next.js 15 introduced async Request APIs; Next.js 16 removed the synchronous compatibility layer entirely. This project is on Next.js 16.1.6.
**How to avoid:** Always `const { id } = await params` in server components. Use `React.use(params)` in client components (not `await`).
**Warning signs:** Page renders with `undefined` ID causing 404 or empty state.

### Pitfall 4: XSS Vulnerability in JSON-LD

**What goes wrong:** Book descriptions containing `<script>` tags or `</script>` break out of the JSON-LD script tag, creating an XSS vulnerability.
**Why it happens:** `dangerouslySetInnerHTML` with raw `JSON.stringify()` doesn't escape HTML characters.
**How to avoid:** Always apply `.replace(/</g, '\\u003c')` per the [official Next.js JSON-LD docs](https://nextjs.org/docs/app/guides/json-ld).
**Warning signs:** Any user-editable content (book descriptions) in JSON-LD without escaping.

### Pitfall 5: next/image Requires remotePatterns for External Cover Images

**What goes wrong:** Book cover images from external URLs (CDN, publisher sites) fail with "hostname not configured" error.
**Why it happens:** `next/image` blocks external hostnames by default for security. The current `next.config.ts` has no `remotePatterns` configured.
**How to avoid:** Add `images.remotePatterns` to `next.config.ts` before using `next/image` with external URLs. Since cover URLs can be any hostname (seeded from scripts), use a permissive pattern for development or require HTTPS.
**Warning signs:** Images fail to load with Error 400 from `/_next/image?url=...`.

### Pitfall 6: Price Range Filter — Backend Doesn't Have Min/Max Price Params

**What goes wrong:** The user selected "Price: $10-$20" filter but the backend `GET /books` only supports `genre_id` and `q` filters. No `min_price` / `max_price` query params exist.
**Why it happens:** The backend `BookListResponse` doesn't expose price range filtering in `GET /books`.
**How to avoid:** Two options: (1) Implement price range filtering client-side by fetching all books for the genre and filtering in JS — not viable for large catalogs. (2) Add `min_price`/`max_price` query params to the FastAPI router and repository. Option 2 is correct. This is a **backend extension needed** before CATL-04 can be fully implemented.
**Warning signs:** CATL-04 can't be completed without this backend change.

---

## Code Examples

Verified patterns from official sources:

### generateMetadata with Open Graph for Book Detail Page

```typescript
// Source: https://nextjs.org/docs/app/getting-started/metadata-and-og-images
// Note: fetch the book once for both metadata and page using React.cache()
import { cache } from 'react'

const getBook = cache(async (id: number) => {
  return fetchBook(id)
})

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  const book = await getBook(Number(id))
  if (!book) return { title: 'Book Not Found' }

  return {
    title: `${book.title} by ${book.author}`,
    description: book.description ?? undefined,
    openGraph: {
      title: book.title,
      description: book.description ?? undefined,
      type: 'book',
      images: book.cover_image_url
        ? [{ url: book.cover_image_url, alt: book.title }]
        : [],
    },
  }
}

export default async function BookDetailPage({ params }: PageProps) {
  const { id } = await params
  const book = await getBook(Number(id))  // React.cache() deduplicates this call
  if (!book) notFound()
  // ...
}
```

### Skeleton Grid for Loading State

```typescript
// Source: https://ui.shadcn.com/docs/components/radix/skeleton
// src/app/catalog/_components/BookCardSkeleton.tsx
import { Skeleton } from '@/components/ui/skeleton'

export function BookCardSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="aspect-[2/3] w-full rounded-lg" />  {/* Cover */}
      <Skeleton className="h-4 w-3/4" />                        {/* Title */}
      <Skeleton className="h-3 w-1/2" />                        {/* Author */}
      <Skeleton className="h-4 w-1/4" />                        {/* Price */}
    </div>
  )
}

export function BookGridSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 20 }).map((_, i) => (
        <BookCardSkeleton key={i} />
      ))}
    </div>
  )
}
```

### Backend Sort Param Mapping

The backend `sort` param values differ from the UX sort labels in the CONTEXT.md:

| UX Label | Backend `sort` param value |
|----------|--------------------------|
| Relevance (when q is set) | Not needed — backend auto-sorts by relevance when `q` present |
| Price low-to-high | `price` |
| Price high-to-low | Not natively supported — requires client-side reverse OR backend extension |
| Newest | `created_at` |
| Highest rated | Not natively supported — backend has no `avg_rating` sort |

**Clarification needed:** The `sort=price` param sorts ascending. "Price high-to-low" and "Highest rated" sorts are not in the current backend. Options:
1. Add `sort_dir=asc|desc` param to backend (recommended)
2. Implement only the supported sorts in Phase 21, extend in later phase

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pages Router `getServerSideProps` for catalog | App Router async server component + `await searchParams` | Next.js 13 → stable in 15, enforced in 16 | No `getServerSideProps` — fetch directly in async component |
| Synchronous `params.id` | `const { id } = await params` | Next.js 15 (enforced Next.js 16) | All dynamic route page components must be `async` |
| `next-seo` library for metadata | Built-in `generateMetadata()` | Next.js 13 App Router | No external library needed for OG/Twitter tags |
| `middleware.ts` | `proxy.ts` (already done in Phase 20) | Next.js 16 | Phase 21 does not need to change proxy.ts |
| `images.domains` | `images.remotePatterns` | Next.js 16 deprecation | Must use `remotePatterns` for external cover image URLs |
| `experimental_ppr` | `cacheComponents` | Next.js 16 | PPR not needed for this phase |

**Deprecated/outdated:**
- `next/legacy/image`: Use `next/image` (already standard in project)
- `images.domains`: Use `images.remotePatterns` (needed for external cover URLs)
- Synchronous `params`/`searchParams` access: Removed in Next.js 16

---

## Open Questions

1. **Price range and sort direction — backend extension needed**
   - What we know: `GET /books` supports `sort=title|price|date|created_at` (always ascending) and no `min_price`/`max_price` params
   - What's unclear: Whether "Price high-to-low" and "Highest rated" sort options in the CONTEXT.md decisions require backend changes, or if they'll be added as Phase 22 prep
   - Recommendation: Plan a backend task to add `sort_dir=asc|desc` and optionally `min_price`/`max_price` to the FastAPI books router. Without this, CATL-04 (price range filter) and two sort options cannot be completed

2. **Cover image URL domains for next/image remotePatterns**
   - What we know: Verified `/backend/scripts/seed_books.py` — all 26 seeded books have NO `cover_image_url` (field is absent, defaults to null). So the placeholder component will be the primary visual for all seeded books.
   - What's unclear: If cover images are added later (admin dashboard, Phase 22+), they could come from any domain
   - Recommendation: Add a permissive `images.remotePatterns` for `https://**` in `next.config.ts` so that when cover URLs are added later, they just work. The deterministic colored placeholder is critical for the demo and must look polished.

3. **Genre lookup on book detail page breadcrumb**
   - What we know: `BookDetailResponse` includes `genre_id` (an integer), not a genre name
   - What's unclear: The breadcrumb "Home > Genre > Book Title" needs the genre name, requiring a separate `GET /genres` call or a join in the backend response
   - Recommendation: On the detail page, fetch genres list separately and look up by `genre_id`. Genre list is small and stable — cache with `{ cache: 'force-cache' }`.

---

## Validation Architecture

`workflow.nyquist_validation` is not present in `.planning/config.json` — this section is skipped per instructions.

---

## Sources

### Primary (HIGH confidence)
- [Next.js ISR Guide](https://nextjs.org/docs/app/guides/incremental-static-regeneration) — `revalidate`, `generateStaticParams`, ISR patterns (docs version 16.1.6, updated 2026-02-24)
- [Next.js JSON-LD Guide](https://nextjs.org/docs/app/guides/json-ld) — Exact JSON-LD injection pattern with XSS escaping (docs version 16.1.6, updated 2026-02-24)
- [Next.js Metadata Guide](https://nextjs.org/docs/app/getting-started/metadata-and-og-images) — `generateMetadata`, Open Graph, `React.cache()` deduplication (docs version 16.1.6, updated 2026-02-24)
- [Next.js Route Segment Config](https://nextjs.org/docs/app/api-reference/file-conventions/route-segment-config) — `dynamic`, `revalidate`, `dynamicParams` options (docs version 16.1.6, updated 2026-02-24)
- [Next.js Version 16 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-16) — Async `params`/`searchParams` breaking change, `remotePatterns` requirement (docs version 16.1.6, updated 2026-02-24)
- [Next.js Learn: Search and Pagination](https://nextjs.org/learn/dashboard-app/adding-search-and-pagination) — `useSearchParams` + `useRouter().replace()` + `use-debounce` official pattern
- Backend `/backend/app/books/router.py` — Verified `GET /books` and `GET /books/{id}` endpoints, params, and response schemas

### Secondary (MEDIUM confidence)
- [Google Book Structured Data](https://developers.google.com/search/docs/appearance/structured-data/book) — Required/recommended JSON-LD fields for Book schema (verified against schema.org)
- [shadcn/ui Skeleton docs](https://ui.shadcn.com/docs/components/radix/skeleton) — Install command and import pattern

### Tertiary (LOW confidence)
- WebSearch finding on searchParams + ISR conflict — verified against official Route Segment Config docs (upgraded to HIGH)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against official Next.js 16.1.6 docs and existing codebase
- Architecture: HIGH — patterns directly from official Next.js Learn tutorial and docs
- Pitfalls: HIGH — Next.js 16 breaking changes documented in official upgrade guide; backend gap verified by reading router.py
- Backend API: HIGH — verified by reading actual backend router.py and schemas.py

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable framework APIs; check for Next.js patch releases)
