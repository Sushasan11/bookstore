'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import dynamic from 'next/dynamic'
import {
  adminKeys,
  fetchSalesSummary,
  fetchTopBooks,
} from '@/lib/admin'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

// ---------------------------------------------------------------------------
// Dynamic import — recharts MUST NOT run on the server (SSR hydration errors)
// ---------------------------------------------------------------------------

const RevenueChart = dynamic(
  () => import('@/components/admin/RevenueChart'),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[300px] w-full rounded-lg" />,
  }
)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Period = 'today' | 'week' | 'month'
type SortBy = 'revenue' | 'volume'
type Limit = 5 | 10 | 25

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

export default function SalesAnalyticsPage() {
  const [period, setPeriod] = useState<Period>('today')
  const [sortBy, setSortBy] = useState<SortBy>('revenue')
  const [limit, setLimit] = useState<Limit>(10)

  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''

  const summaryQuery = useQuery({
    queryKey: adminKeys.sales.summary(period),
    queryFn: () => fetchSalesSummary(accessToken, period),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const topBooksQuery = useQuery({
    queryKey: adminKeys.sales.topBooks(limit, sortBy),
    queryFn: () => fetchTopBooks(accessToken, limit, sortBy),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  // Derive prior revenue from delta_percentage
  // Guard against null (no prior data) and -100 (division by zero)
  const summaryData = summaryQuery.data
  const delta = summaryData?.delta_percentage ?? null
  const priorRevenue =
    delta !== null && delta !== -100
      ? (summaryData?.revenue ?? 0) / (1 + delta / 100)
      : null

  return (
    <div className="space-y-6">
      {/* Page header with period selector */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Sales Analytics</h1>
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

        {/* Period context card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-2xl font-bold">{PERIOD_LABELS[period]}</p>
              <p className="text-sm text-muted-foreground">Selected period</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Revenue Comparison Chart */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Revenue Comparison</h2>
        <div className="rounded-lg border p-4">
          {summaryQuery.isLoading ? (
            <Skeleton className="h-[300px] w-full rounded-lg" />
          ) : summaryQuery.isError ? (
            <div className="flex h-[300px] flex-col items-center justify-center gap-3 text-muted-foreground">
              <p className="text-sm">Failed to load chart data.</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => summaryQuery.refetch()}
              >
                Retry
              </Button>
            </div>
          ) : (
            <RevenueChart
              currentRevenue={summaryData?.revenue ?? 0}
              priorRevenue={priorRevenue}
              periodLabel={PERIOD_LABELS[period]}
            />
          )}
        </div>
      </div>

      {/* Top Sellers Table */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <h2 className="text-lg font-semibold">Top Sellers</h2>
          <div className="flex items-center gap-3">
            {/* Sort toggle */}
            <div className="flex items-center gap-1 rounded-lg border p-1">
              {(['revenue', 'volume'] as SortBy[]).map((s) => (
                <Button
                  key={s}
                  variant={sortBy === s ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setSortBy(s)}
                  className="h-8 text-sm capitalize"
                >
                  {s === 'revenue' ? 'Revenue' : 'Volume'}
                </Button>
              ))}
            </div>
            {/* Limit selector */}
            <div className="flex items-center gap-1 rounded-lg border p-1">
              {([5, 10, 25] as Limit[]).map((l) => (
                <Button
                  key={l}
                  variant={limit === l ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setLimit(l)}
                  className="h-8 text-sm"
                >
                  {l}
                </Button>
              ))}
            </div>
          </div>
        </div>

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
                  {sortBy === 'revenue' ? 'Revenue' : 'Units Sold'}
                </th>
              </tr>
            </thead>
            <tbody>
              {topBooksQuery.isLoading ? (
                Array.from({ length: limit }).map((_, i) => (
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
                  <td
                    colSpan={4}
                    className="py-6 px-4 text-center text-muted-foreground"
                  >
                    Failed to load top sellers.{' '}
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
                  <td
                    colSpan={4}
                    className="py-6 px-4 text-center text-muted-foreground"
                  >
                    No sales data available.
                  </td>
                </tr>
              ) : (
                topBooksQuery.data.items.map((book, index) => (
                  <tr
                    key={book.book_id}
                    className="border-t hover:bg-muted/30 transition-colors"
                  >
                    <td className="py-3 px-4 text-muted-foreground font-medium">
                      {index + 1}
                    </td>
                    <td className="py-3 px-4 font-medium">{book.title}</td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {book.author}
                    </td>
                    <td className="py-3 px-4 text-right font-medium">
                      {sortBy === 'revenue'
                        ? formatCurrency(book.total_revenue)
                        : book.units_sold}
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
