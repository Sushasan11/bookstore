'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import {
  adminKeys,
  fetchSalesSummary,
  fetchTopBooks,
  fetchLowStock,
} from '@/lib/admin'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Period = 'today' | 'week' | 'month'

const PERIOD_LABELS: Record<Period, string> = {
  today: 'Today',
  week: 'This Week',
  month: 'This Month',
}

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) {
    return <span className="text-muted-foreground text-sm">— 0%</span>
  }
  if (delta > 0) {
    return (
      <span className="text-green-600 dark:text-green-400 text-sm font-medium">
        ▲ {delta.toFixed(1)}%
      </span>
    )
  }
  return (
    <span className="text-red-600 dark:text-red-400 text-sm font-medium">
      ▼ {Math.abs(delta).toFixed(1)}%
    </span>
  )
}

const formatCurrency = (value: number) =>
  `$${Math.round(value).toLocaleString('en-US')}`

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminOverviewPage() {
  const [period, setPeriod] = useState<Period>('today')
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''

  const summaryQuery = useQuery({
    queryKey: adminKeys.sales.summary(period),
    queryFn: () => fetchSalesSummary(accessToken, period),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const topBooksQuery = useQuery({
    queryKey: adminKeys.sales.topBooks(5),
    queryFn: () => fetchTopBooks(accessToken, 5, 'revenue'),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const lowStockQuery = useQuery({
    queryKey: adminKeys.inventory.lowStock(10),
    queryFn: () => fetchLowStock(accessToken, 10),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const summaryData = summaryQuery.data
  const delta = summaryData?.delta_percentage ?? null

  return (
    <div className="space-y-6">
      {/* Page header with period selector */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Dashboard Overview</h1>
        <div className="flex items-center gap-1 rounded-lg border p-1">
          {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
            <Button
              key={p}
              variant={period === p ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setPeriod(p)}
              className="h-8 text-sm"
            >
              {PERIOD_LABELS[p]}
            </Button>
          ))}
        </div>
      </div>

      {/* KPI cards grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">

        {/* Revenue card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryQuery.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-28" />
                <Skeleton className="h-4 w-16" />
              </div>
            ) : summaryQuery.isError ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Failed to load</p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => summaryQuery.refetch()}
                >
                  Retry
                </Button>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-2xl font-bold">
                  {formatCurrency(summaryData?.revenue ?? 0)}
                </p>
                <DeltaBadge delta={delta} />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Orders card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Orders
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryQuery.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-16" />
                <Skeleton className="h-4 w-16" />
              </div>
            ) : summaryQuery.isError ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Failed to load</p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => summaryQuery.refetch()}
                >
                  Retry
                </Button>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-2xl font-bold">
                  {summaryData?.order_count ?? 0}
                </p>
                <DeltaBadge delta={delta} />
              </div>
            )}
          </CardContent>
        </Card>

        {/* AOV card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg. Order Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryQuery.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-24" />
                <Skeleton className="h-4 w-16" />
              </div>
            ) : summaryQuery.isError ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Failed to load</p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => summaryQuery.refetch()}
                >
                  Retry
                </Button>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-2xl font-bold">
                  {formatCurrency(summaryData?.aov ?? 0)}
                </p>
                <DeltaBadge delta={delta} />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Low Stock card */}
        <Card className="border-amber-500/50 bg-amber-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Low Stock Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lowStockQuery.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-12" />
                <Skeleton className="h-4 w-36" />
              </div>
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
              <div className="space-y-1">
                <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                  {lowStockQuery.data?.total_low_stock ?? 0}
                </p>
                <Link
                  href="/admin/inventory"
                  className="text-sm text-amber-600 dark:text-amber-400 hover:underline"
                >
                  View Inventory Alerts →
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top 5 Best Sellers mini-table */}
      <div>
        <h2 className="text-lg font-semibold mt-8 mb-4">Top 5 Best Sellers</h2>
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left text-muted-foreground font-medium py-2 px-4 w-12">
                  #
                </th>
                <th className="text-left text-muted-foreground font-medium py-2 px-4">
                  Title
                </th>
                <th className="text-left text-muted-foreground font-medium py-2 px-4">
                  Author
                </th>
                <th className="text-right text-muted-foreground font-medium py-2 px-4">
                  Revenue
                </th>
              </tr>
            </thead>
            <tbody>
              {topBooksQuery.isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-t">
                    <td className="py-3 px-4">
                      <Skeleton className="h-4 w-4" />
                    </td>
                    <td className="py-3 px-4">
                      <Skeleton className="h-4 w-48" />
                    </td>
                    <td className="py-3 px-4">
                      <Skeleton className="h-4 w-32" />
                    </td>
                    <td className="py-3 px-4">
                      <Skeleton className="h-4 w-16 ml-auto" />
                    </td>
                  </tr>
                ))
              ) : topBooksQuery.isError ? (
                <tr>
                  <td colSpan={4} className="py-6 px-4 text-center text-muted-foreground">
                    Failed to load best sellers.{' '}
                    <button
                      className="underline hover:no-underline"
                      onClick={() => topBooksQuery.refetch()}
                    >
                      Retry
                    </button>
                  </td>
                </tr>
              ) : !topBooksQuery.data?.items?.length ? (
                <tr>
                  <td colSpan={4} className="py-6 px-4 text-center text-muted-foreground">
                    No sales data available.
                  </td>
                </tr>
              ) : (
                topBooksQuery.data.items.map((book, index) => (
                  <tr key={book.book_id} className="border-t hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-4 text-muted-foreground font-medium">
                      {index + 1}
                    </td>
                    <td className="py-3 px-4 font-medium">{book.title}</td>
                    <td className="py-3 px-4 text-muted-foreground">{book.author}</td>
                    <td className="py-3 px-4 text-right font-medium">
                      {formatCurrency(book.total_revenue)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
