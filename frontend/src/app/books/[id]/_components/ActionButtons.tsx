'use client'

import { ShoppingCart, Heart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCart } from '@/lib/cart'
import { useWishlist } from '@/lib/wishlist'
import { usePrebook } from '@/lib/prebook'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'

interface ActionButtonsProps {
  bookId: number
  inStock: boolean
}

export function ActionButtons({ bookId, inStock }: ActionButtonsProps) {
  const { data: session } = useSession()
  const { addItem } = useCart()
  const { wishlistedIds, handleToggle, isPending: wishlistPending } = useWishlist()
  const { handlePrebook, isPending: prebookPending } = usePrebook()
  const router = useRouter()
  const isWishlisted = wishlistedIds.has(bookId)

  const handleAddToCart = () => {
    if (!session?.accessToken) {
      toast.error('Please sign in to add items to your cart')
      router.push('/login')
      return
    }
    addItem.mutate({ bookId })
  }

  return (
    <div className="mt-6">
      <div className="flex flex-wrap gap-4">
        {inStock ? (
          <Button
            size="lg"
            variant="default"
            disabled={addItem.isPending}
            onClick={handleAddToCart}
          >
            <ShoppingCart />
            {addItem.isPending ? 'Adding...' : 'Add to Cart'}
          </Button>
        ) : (
          <Button
            size="lg"
            variant="outline"
            onClick={() => handlePrebook(bookId)}
            disabled={prebookPending}
          >
            {prebookPending ? 'Pre-booking...' : 'Pre-book'}
          </Button>
        )}
        <Button
          size="lg"
          variant="outline"
          onClick={() => handleToggle(bookId)}
          disabled={wishlistPending}
        >
          <Heart className={isWishlisted ? 'fill-red-500 text-red-500' : ''} />
          {isWishlisted ? 'Wishlisted' : 'Add to Wishlist'}
        </Button>
      </div>
    </div>
  )
}
