'use client'

import { ShoppingCart, Heart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCart } from '@/lib/cart'
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
  const router = useRouter()

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
        <Button
          size="lg"
          variant="default"
          disabled={!inStock || addItem.isPending}
          onClick={handleAddToCart}
        >
          <ShoppingCart />
          {!inStock ? 'Out of Stock' : addItem.isPending ? 'Adding...' : 'Add to Cart'}
        </Button>
        <Button disabled size="lg" variant="outline">
          <Heart />
          Add to Wishlist
        </Button>
      </div>
    </div>
  )
}
