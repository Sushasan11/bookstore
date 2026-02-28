'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { adminKeys, fetchLowStock } from '@/lib/admin'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const THRESHOLDS = [5, 10, 20] as const
type Threshold = (typeof THRESHOLDS)[number]

export default function AdminInventoryPage() {
  const [threshold, setThreshold] = useState<Threshold>(10)
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''

  const lowStockQuery = useQuery({
    queryKey: adminKeys.inventory.lowStock(threshold),
    queryFn: () => fetchLowStock(accessToken, threshold),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  return (
    <div className="space-y-6">
      {/* Header with threshold selector */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Inventory Alerts</h1>
        <div className="flex items-center gap-1 rounded-lg border p-1">
          {THRESHOLDS.map((t) => (
            <Button
              key={t}
              variant={threshold === t ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setThreshold(t)}
              className="h-8 text-sm"
            >
              &lt; {t}
            </Button>
          ))}
        </div>
      </div>

      {/* Summary card */}
      <Card className="border-amber-500/50 bg-amber-500/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Low Stock Items (threshold: {threshold})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {lowStockQuery.isLoading ? (
            <Skeleton className="h-8 w-12" />
          ) : lowStockQuery.isError ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Failed to load</p>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => lowStockQuery.refetch()}
              >
                Retry
              </Button>
            </div>
          ) : (
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {lowStockQuery.data?.total_low_stock ?? 0}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Low stock items table */}
      <div className="rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left text-muted-foreground font-medium py-2 px-4">
                Title
              </th>
              <th className="text-left text-muted-foreground font-medium py-2 px-4">
                Author
              </th>
              <th className="text-right text-muted-foreground font-medium py-2 px-4">
                Current Stock
              </th>
              <th className="text-right text-muted-foreground font-medium py-2 px-4">
                Threshold
              </th>
            </tr>
          </thead>
          <tbody>
            {lowStockQuery.isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-t">
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-48" />
                  </td>
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-32" />
                  </td>
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-12 ml-auto" />
                  </td>
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-12 ml-auto" />
                  </td>
                </tr>
              ))
            ) : lowStockQuery.isError ? (
              <tr>
                <td colSpan={4} className="py-6 px-4 text-center text-muted-foreground">
                  Failed to load inventory data.{' '}
                  <button
                    className="underline hover:no-underline"
                    onClick={() => lowStockQuery.refetch()}
                  >
                    Retry
                  </button>
                </td>
              </tr>
            ) : !lowStockQuery.data?.items?.length ? (
              <tr>
                <td colSpan={4} className="py-6 px-4 text-center text-muted-foreground">
                  No low stock items
                </td>
              </tr>
            ) : (
              lowStockQuery.data.items.map((item) => (
                <tr key={item.book_id} className="border-t hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4 font-medium">{item.title}</td>
                  <td className="py-3 px-4 text-muted-foreground">{item.author}</td>
                  <td
                    className={`py-3 px-4 text-right font-medium ${
                      item.current_stock === 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-amber-600 dark:text-amber-400'
                    }`}
                  >
                    {item.current_stock}
                  </td>
                  <td className="py-3 px-4 text-right text-muted-foreground">
                    {item.threshold}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
