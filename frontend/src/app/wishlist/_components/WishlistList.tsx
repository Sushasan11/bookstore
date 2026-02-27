'use client'

import Image from 'next/image'
import Link from 'next/link'
import { Trash2 } from 'lucide-react'
import { useWishlist } from '@/lib/wishlist'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { components } from '@/types/api.generated'

type WishlistItemResponse = components['schemas']['WishlistItemResponse']

interface WishlistListProps {
  items: WishlistItemResponse[]
}

export function WishlistList({ items }: WishlistListProps) {
  const { wishlistQuery, handleToggle } = useWishlist()

  // TanStack Query cache takes over after first client-side fetch; SSR items are the fallback
  const displayItems = wishlistQuery.data?.items ?? items

  if (displayItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-lg text-muted-foreground mb-4">Your wishlist is empty</p>
        <Link
          href="/catalog"
          className="text-sm font-medium text-primary hover:underline"
        >
          Browse the catalog to find books you love
        </Link>
      </div>
    )
  }

  return (
    <ul className="divide-y">
      {displayItems.map((item) => (
        <li key={item.id} className="flex items-center gap-4 py-4 last:border-b-0">
          {/* Cover thumbnail */}
          <Link href={`/books/${item.book_id}`} className="flex-shrink-0">
            <div className="relative h-[72px] w-12 overflow-hidden rounded">
              {item.book.cover_image_url ? (
                <Image
                  src={item.book.cover_image_url}
                  alt={item.book.title}
                  fill
                  sizes="48px"
                  className="object-cover"
                />
              ) : (
                <div className="h-full w-full bg-muted flex items-center justify-center">
                  <span className="text-xs text-muted-foreground">No cover</span>
                </div>
              )}
            </div>
          </Link>

          {/* Book info */}
          <div className="flex-1 min-w-0">
            <Link href={`/books/${item.book_id}`}>
              <p className="font-medium leading-tight hover:underline truncate">
                {item.book.title}
              </p>
            </Link>
            <p className="text-sm text-muted-foreground truncate">{item.book.author}</p>
            <p className="text-sm font-semibold mt-1">${item.book.price}</p>
            <div className="mt-1">
              {item.book.stock_quantity > 0 ? (
                <Badge variant="outline" className="text-green-600 border-green-600 text-xs">
                  In Stock
                </Badge>
              ) : (
                <Badge variant="outline" className="text-red-600 border-red-600 text-xs">
                  Out of Stock
                </Badge>
              )}
            </div>
          </div>

          {/* Remove button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => handleToggle(item.book_id)}
            aria-label={`Remove ${item.book.title} from wishlist`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </li>
      ))}
    </ul>
  )
}
