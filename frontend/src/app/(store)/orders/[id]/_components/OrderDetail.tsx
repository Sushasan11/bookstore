import Link from 'next/link'
import { CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import type { components } from '@/types/api.generated'

type OrderResponse = components['schemas']['OrderResponse']

interface OrderDetailProps {
  order: OrderResponse
  isConfirmed: boolean
}

export function OrderDetail({ order, isConfirmed }: OrderDetailProps) {
  const orderDate = new Date(order.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div className="space-y-6">
      {/* Success banner — shown when arriving from checkout */}
      {isConfirmed && (
        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950 p-4">
          <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400 shrink-0" />
          <div>
            <p className="font-semibold text-green-800 dark:text-green-200">Order Confirmed!</p>
            <p className="text-sm text-green-700 dark:text-green-300">
              Your order has been placed successfully.
            </p>
          </div>
        </div>
      )}

      {/* Order header */}
      <div>
        <h1 className="text-2xl font-bold">Order #{order.id}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Placed on {orderDate} · Status: {order.status}
        </p>
      </div>

      <Separator />

      {/* Order items */}
      <div className="space-y-4">
        <h2 className="font-semibold">Items</h2>
        {order.items.map((item) => (
          <div key={item.id} className="flex justify-between items-center py-2">
            <div>
              <p className="font-medium text-sm">
                {item.book ? item.book.title : 'Deleted Book'}
              </p>
              {item.book && (
                <p className="text-xs text-muted-foreground">{item.book.author}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Qty: {item.quantity} x ${parseFloat(item.unit_price).toFixed(2)}
              </p>
            </div>
            <p className="font-medium text-sm">
              ${(parseFloat(item.unit_price) * item.quantity).toFixed(2)}
            </p>
          </div>
        ))}
      </div>

      <Separator />

      {/* Order total */}
      <div className="flex justify-between font-semibold text-lg">
        <span>Total</span>
        <span>${order.total_price}</span>
      </div>

      <Separator />

      {/* CTAs */}
      <div className="flex flex-wrap gap-4">
        <Link href="/catalog">
          <Button>Continue Shopping</Button>
        </Link>
        <Link href="/orders">
          <Button variant="outline">View All Orders</Button>
        </Link>
      </div>
    </div>
  )
}
