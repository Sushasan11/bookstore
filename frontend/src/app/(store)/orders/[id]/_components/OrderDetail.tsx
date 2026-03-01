import Link from 'next/link'
import Image from 'next/image'
import { CheckCircle, Package, BookOpen } from 'lucide-react'
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
        <div className="rounded-xl border border-green-200 bg-gradient-to-r from-green-50 to-emerald-50 dark:border-green-800 dark:from-green-950 dark:to-emerald-950 p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
              <CheckCircle className="h-7 w-7 text-green-600 dark:text-green-400" />
            </div>
            <div className="space-y-1">
              <p className="text-lg font-bold text-green-800 dark:text-green-200">
                Thank you for your purchase!
              </p>
              <p className="text-sm text-green-700 dark:text-green-300">
                Your order <span className="font-semibold">#{order.id}</span> has been confirmed. A confirmation email with your order details has been sent to your inbox.
              </p>
              <p className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1.5 mt-2">
                <Package className="h-4 w-4" />
                Happy reading!
              </p>
            </div>
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
          <div key={item.id} className="flex gap-4 py-3">
            {/* Book cover */}
            <div className="h-20 w-14 shrink-0 rounded overflow-hidden bg-muted flex items-center justify-center">
              {item.book?.cover_image_url ? (
                <Image
                  src={item.book.cover_image_url}
                  alt={item.book?.title ?? 'Book cover'}
                  width={56}
                  height={80}
                  className="h-full w-full object-cover"
                />
              ) : (
                <BookOpen className="h-6 w-6 text-muted-foreground" />
              )}
            </div>
            {/* Book details */}
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">
                {item.book ? item.book.title : 'Deleted Book'}
              </p>
              {item.book && (
                <p className="text-xs text-muted-foreground">{item.book.author}</p>
              )}
              <p className="text-xs text-muted-foreground mt-1">
                Qty: {item.quantity} x ${parseFloat(item.unit_price).toFixed(2)}
              </p>
            </div>
            {/* Item total */}
            <p className="font-medium text-sm shrink-0">
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
