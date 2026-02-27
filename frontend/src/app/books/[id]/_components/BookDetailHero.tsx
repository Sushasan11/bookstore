import Image from 'next/image'
import { Badge } from '@/components/ui/badge'
import type { BookDetailResponse } from '@/lib/catalog'
import { RatingDisplay } from './RatingDisplay'

const COVER_COLORS = [
  'bg-blue-100 dark:bg-blue-900',
  'bg-green-100 dark:bg-green-900',
  'bg-purple-100 dark:bg-purple-900',
  'bg-amber-100 dark:bg-amber-900',
  'bg-rose-100 dark:bg-rose-900',
]

function CoverPlaceholder({ book }: { book: BookDetailResponse }) {
  const colorClass = COVER_COLORS[book.id % COVER_COLORS.length]
  return (
    <div
      className={`aspect-[2/3] w-full rounded-lg ${colorClass} flex flex-col items-center justify-center p-6 text-center`}
    >
      <span className="text-base font-bold line-clamp-4">{book.title}</span>
      <span className="text-sm text-muted-foreground mt-2">{book.author}</span>
    </div>
  )
}

function formatPublishDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

interface BookDetailHeroProps {
  book: BookDetailResponse
}

export function BookDetailHero({ book }: BookDetailHeroProps) {
  return (
    <div className="md:flex md:gap-8 mt-4">
      {/* Left column: Cover image */}
      <div className="md:w-1/3 shrink-0">
        {book.cover_image_url ? (
          <Image
            src={book.cover_image_url}
            alt={`Cover of ${book.title}`}
            width={400}
            height={600}
            className="rounded-lg object-cover w-full"
            priority
          />
        ) : (
          <CoverPlaceholder book={book} />
        )}
      </div>

      {/* Right column: Book details */}
      <div className="md:w-2/3 mt-6 md:mt-0">
        <h1 className="text-3xl font-bold">{book.title}</h1>
        <p className="text-lg text-muted-foreground mt-1">by {book.author}</p>

        <RatingDisplay avgRating={book.avg_rating} reviewCount={book.review_count} />

        <p className="text-2xl font-semibold mt-4">${parseFloat(book.price).toFixed(2)}</p>

        <div className="mt-2">
          {book.in_stock ? (
            <Badge
              variant="secondary"
              className="text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900"
            >
              In Stock
            </Badge>
          ) : (
            <Badge
              variant="secondary"
              className="text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900"
            >
              Out of Stock
            </Badge>
          )}
        </div>

        {/* Metadata grid */}
        <dl className="mt-6 grid grid-cols-1 gap-y-2 text-sm">
          {book.isbn && (
            <div className="flex gap-2">
              <dt className="font-medium text-muted-foreground w-24 shrink-0">ISBN</dt>
              <dd>{book.isbn}</dd>
            </div>
          )}
          {book.publish_date && (
            <div className="flex gap-2">
              <dt className="font-medium text-muted-foreground w-24 shrink-0">Published</dt>
              <dd>{formatPublishDate(book.publish_date)}</dd>
            </div>
          )}
        </dl>
      </div>
    </div>
  )
}
