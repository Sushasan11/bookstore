'use client'

import Link from 'next/link'
import { ShoppingCart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useCart } from '@/lib/cart'
import { CartItem } from './CartItem'
import { CartSummary } from './CartSummary'

function CartLoadingSkeleton() {
  return (
    <div className="lg:flex lg:gap-8">
      <div className="flex-1 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-4 p-4 border rounded-lg">
            <Skeleton className="h-24 w-16 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-20" />
            </div>
          </div>
        ))}
      </div>
      <Skeleton className="h-48 w-full lg:w-80 mt-6 lg:mt-0 rounded-lg" />
    </div>
  )
}

export function CartPageContent() {
  const { cartQuery, updateItem, removeItem, checkoutMutation } = useCart()

  if (cartQuery.isLoading) {
    return <CartLoadingSkeleton />
  }

  if (cartQuery.isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
        <p className="text-muted-foreground">Failed to load your cart. Please try again.</p>
        <Button variant="outline" onClick={() => cartQuery.refetch()}>
          Retry
        </Button>
      </div>
    )
  }

  const cart = cartQuery.data

  if (!cart || cart.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
        <ShoppingCart className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-xl font-semibold">Your cart is empty</h2>
        <p className="text-muted-foreground">Add some books to get started</p>
        <Button asChild>
          <Link href="/catalog">Browse Books</Link>
        </Button>
      </div>
    )
  }

  function handleUpdateQuantity(itemId: number, quantity: number) {
    updateItem.mutate({ itemId, quantity })
  }

  function handleRemove(itemId: number) {
    removeItem.mutate({ itemId })
  }

  function handleCheckout() {
    checkoutMutation.mutate()
  }

  return (
    <div className="lg:flex lg:gap-8 pb-20 lg:pb-0">
      <div className="flex-1 space-y-4">
        {cart.items.map((item) => (
          <CartItem
            key={item.id}
            item={item}
            onUpdateQuantity={handleUpdateQuantity}
            onRemove={handleRemove}
          />
        ))}
      </div>
      <div className="w-full lg:w-80 mt-6 lg:mt-0">
        <CartSummary
          totalItems={cart.total_items}
          totalPrice={cart.total_price}
          onCheckout={handleCheckout}
          isCheckingOut={checkoutMutation.isPending}
        />
      </div>
    </div>
  )
}
