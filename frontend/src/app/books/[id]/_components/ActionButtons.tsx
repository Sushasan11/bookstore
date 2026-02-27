import { ShoppingCart, Heart } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ActionButtonsProps {
  inStock: boolean
}

export function ActionButtons({ inStock }: ActionButtonsProps) {
  return (
    <div className="mt-6">
      <div className="flex flex-wrap gap-4">
        <Button disabled size="lg" variant="default">
          <ShoppingCart />
          {inStock ? 'Add to Cart' : 'Out of Stock'}
        </Button>
        <Button disabled size="lg" variant="outline">
          <Heart />
          Add to Wishlist
        </Button>
      </div>
      <p className="text-xs text-muted-foreground mt-2">Coming soon</p>
    </div>
  )
}
