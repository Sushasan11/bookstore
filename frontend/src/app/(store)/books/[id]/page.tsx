import { cache } from 'react'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { fetchBook, fetchBooks, fetchGenres } from '@/lib/catalog'
import { fetchReviews } from '@/lib/reviews'
import type { components } from '@/types/api.generated'
import { BreadcrumbNav } from './_components/BreadcrumbNav'
import { BookDetailHero } from './_components/BookDetailHero'
import { ActionButtons } from './_components/ActionButtons'
import { MoreInGenre } from './_components/MoreInGenre'
import { ReviewsSection } from './_components/ReviewsSection'

type ReviewListResponse = components['schemas']['ReviewListResponse']

export const revalidate = 3600 // Revalidate once per hour

type PageProps = { params: Promise<{ id: string }> }

// Use React.cache so generateMetadata and the page component share the same request
const getBook = cache(async (id: number) => fetchBook(id))

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  const book = await getBook(Number(id))
  if (!book) return { title: 'Book Not Found' }

  return {
    title: `${book.title} by ${book.author}`,
    description: book.description ?? `${book.title} — available at Bookstore`,
    openGraph: {
      title: `${book.title} by ${book.author}`,
      description: book.description ?? `Browse ${book.title} at Bookstore`,
      type: 'book',
      images: book.cover_image_url ? [{ url: book.cover_image_url, alt: book.title }] : [],
    },
  }
}

export default async function BookDetailPage({ params }: PageProps) {
  const { id } = await params
  const book = await getBook(Number(id))

  if (!book) {
    notFound()
  }

  const genres = await fetchGenres()
  const genre = genres.find(g => g.id === book.genre_id)

  // Fetch related books for "More in Genre"
  let relatedBooks: import('@/lib/catalog').BookResponse[] = []
  if (book.genre_id) {
    const related = await fetchBooks({ genre_id: book.genre_id, size: 7 })
    relatedBooks = related.items
      .filter(b => b.id !== book.id)
      .slice(0, 6)
  }

  // Fetch reviews server-side for initial data (graceful fallback on error)
  let initialReviews: ReviewListResponse = { items: [], total: 0, page: 1, size: 50 }
  try {
    initialReviews = await fetchReviews(book.id)
  } catch {
    // Show empty state — don't crash the page
  }

  // Build JSON-LD Book schema (schema.org)
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Book',
    name: book.title,
    author: { '@type': 'Person', name: book.author },
    isbn: book.isbn ?? undefined,
    description: book.description ?? undefined,
    image: book.cover_image_url ?? undefined,
    offers: {
      '@type': 'Offer',
      price: book.price,
      priceCurrency: 'USD',
      availability: book.in_stock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
    },
    ...(book.avg_rating != null ? {
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: book.avg_rating,
        reviewCount: book.review_count,
      },
    } : {}),
  }

  return (
    <>
      {/* JSON-LD structured data — XSS-safe via unicode escape of < */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c'),
        }}
      />
      <div className="mx-auto max-w-7xl px-4 py-8">
        <BreadcrumbNav genre={genre} bookTitle={book.title} />
        <BookDetailHero book={book} />
        <ActionButtons bookId={book.id} inStock={book.in_stock} />
        {book.description && (
          <div className="mt-8">
            <h2 className="text-xl font-semibold mb-3">Description</h2>
            <p className="text-muted-foreground leading-relaxed prose prose-sm max-w-none">
              {book.description}
            </p>
          </div>
        )}
        <ReviewsSection bookId={book.id} initialReviews={initialReviews} />
        {relatedBooks.length > 0 && (
          <MoreInGenre books={relatedBooks} genreName={genre?.name} />
        )}
      </div>
    </>
  )
}
