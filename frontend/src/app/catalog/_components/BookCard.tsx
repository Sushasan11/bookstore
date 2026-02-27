import Image from 'next/image'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import type { BookResponse } from '@/lib/catalog'

const COVER_COLORS = [
  'bg-blue-100 dark:bg-blue-900',
  'bg-green-100 dark:bg-green-900',
  'bg-purple-100 dark:bg-purple-900',
  'bg-amber-100 dark:bg-amber-900',
  'bg-rose-100 dark:bg-rose-900',
]

function CoverPlaceholder({ book }: { book: BookResponse }) {
  const colorClass = COVER_COLORS[book.id % COVER_COLORS.length]
  return (
    <div
      className={`absolute inset-0 ${colorClass} flex flex-col items-center justify-center p-3 text-center`}
    >
      <span className="text-sm font-bold line-clamp-3">{book.title}</span>
      <span className="text-xs text-muted-foreground mt-1">{book.author}</span>
    </div>
  )
}

export function BookCard({ book }: { book: BookResponse }) {
  const price = parseFloat(book.price).toFixed(2)
  const inStock = book.stock_quantity > 0

  return (
    <Link
      href={`/books/${book.id}`}
      className="flex flex-col rounded-lg overflow-hidden border hover:shadow-md transition-shadow"
    >
      {/* Cover area */}
      <div className="relative aspect-[2/3] w-full">
        {book.cover_image_url ? (
          <Image
            src={book.cover_image_url}
            alt={`Cover of ${book.title}`}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 50vw, 25vw"
          />
        ) : (
          <CoverPlaceholder book={book} />
        )}
      </div>

      {/* Book info */}
      <div className="flex flex-col gap-1 p-3">
        <p className="font-medium text-sm line-clamp-1">{book.title}</p>
        <p className="text-xs text-muted-foreground line-clamp-1">{book.author}</p>
        <p className="text-sm font-semibold">${price}</p>
        <div>
          {inStock ? (
            <Badge variant="secondary" className="text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900">
              In Stock
            </Badge>
          ) : (
            <Badge variant="secondary" className="text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900">
              Out of Stock
            </Badge>
          )}
        </div>
      </div>
    </Link>
  )
}
