'use client'

import Image from 'next/image'
import Link from 'next/link'
import { ShoppingCart } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCart } from '@/lib/cart'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
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
  const { data: session } = useSession()
  const { addItem } = useCart()
  const router = useRouter()
  const price = parseFloat(book.price).toFixed(2)
  const inStock = book.stock_quantity > 0

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!session?.accessToken) {
      toast.error('Please sign in to add items to your cart')
      router.push('/login')
      return
    }
    addItem.mutate({ bookId: book.id })
  }

  return (
    <div className="group relative flex flex-col rounded-lg overflow-hidden border hover:shadow-md transition-shadow">
      <Link href={`/books/${book.id}`} className="flex flex-col flex-1">
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

      {/* Cart icon button — always visible on mobile, visible on hover on desktop */}
      {inStock && (
        <Button
          variant="secondary"
          size="icon"
          className="absolute top-2 right-2 h-8 w-8 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity shadow-sm"
          onClick={handleAddToCart}
          disabled={addItem.isPending}
          aria-label={`Add ${book.title} to cart`}
        >
          <ShoppingCart className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}
