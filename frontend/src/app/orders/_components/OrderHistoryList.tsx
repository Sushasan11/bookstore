'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import type { components } from '@/types/api.generated'

type OrderResponse = components['schemas']['OrderResponse']

const PAGE_SIZE = 10

interface OrderHistoryListProps {
  orders: OrderResponse[]
}

export function OrderHistoryList({ orders }: OrderHistoryListProps) {
  const [page, setPage] = useState(1)

  if (orders.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-muted-foreground mb-4">No orders yet.</p>
        <Button asChild>
          <Link href="/catalog">Browse Books</Link>
        </Button>
      </div>
    )
  }

  const totalPages = Math.ceil(orders.length / PAGE_SIZE)
  const pageOrders = orders.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div>
      <div className="space-y-3">
        {pageOrders.map((order) => {
          const itemCount = order.items.length
          const firstTitle = order.items[0]?.book?.title ?? 'Deleted Book'
          const itemSummary =
            itemCount === 0
              ? 'No items'
              : itemCount === 1
              ? firstTitle
              : `${firstTitle} +${itemCount - 1} more`

          const orderDate = new Date(order.created_at).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })

          return (
            <Link
              key={order.id}
              href={`/orders/${order.id}`}
              className="block rounded-lg border p-4 hover:bg-accent transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <p className="font-medium text-sm">Order #{order.id}</p>
                  <p className="text-sm text-muted-foreground">{orderDate}</p>
                  <p className="text-sm text-muted-foreground">{itemSummary}</p>
                </div>
                <p className="font-semibold text-sm">${order.total_price}</p>
              </div>
            </Link>
          )
        })}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-6">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p - 1)}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={page === totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
