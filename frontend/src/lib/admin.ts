import { apiFetch } from '@/lib/api'

// ---------------------------------------------------------------------------
// TypeScript types — mirror backend analytics_schemas.py field names exactly
// ---------------------------------------------------------------------------

export type SalesSummaryResponse = {
  period: string
  revenue: number
  order_count: number
  aov: number
  delta_percentage: number | null
}

export type TopBookEntry = {
  book_id: number
  title: string
  author: string
  total_revenue: number
  units_sold: number
}

export type TopBooksResponse = {
  sort_by: string
  items: TopBookEntry[]
}

export type LowStockResponse = {
  threshold: number
  total_low_stock: number
  items: Array<{
    book_id: number
    title: string
    author: string
    current_stock: number
    threshold: number
  }>
}

// ---------------------------------------------------------------------------
// Query key factory — hierarchical prefix enables scoped cache invalidation
// ---------------------------------------------------------------------------

export const adminKeys = {
  all: ['admin'] as const,
  sales: {
    all: ['admin', 'sales'] as const,
    summary: (period: string) => ['admin', 'sales', 'summary', period] as const,
    topBooks: (limit: number) => ['admin', 'sales', 'top-books', limit] as const,
  },
  inventory: {
    all: ['admin', 'inventory'] as const,
    lowStock: (threshold: number) => ['admin', 'inventory', 'low-stock', threshold] as const,
  },
} as const

// ---------------------------------------------------------------------------
// Fetch functions — all require accessToken (admin endpoints enforce require_admin)
// ---------------------------------------------------------------------------

/**
 * Fetch sales summary KPIs (revenue, order_count, aov, delta_percentage)
 * for the selected period. All admin endpoints return 403 without Bearer token.
 */
export async function fetchSalesSummary(
  accessToken: string,
  period: 'today' | 'week' | 'month'
): Promise<SalesSummaryResponse> {
  return apiFetch<SalesSummaryResponse>(
    `/admin/analytics/sales/summary?period=${period}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}

/**
 * Fetch top N books sorted by revenue or volume.
 * Default: top 5 by revenue.
 */
export async function fetchTopBooks(
  accessToken: string,
  limit: number = 5,
  sort_by: 'revenue' | 'volume' = 'revenue'
): Promise<TopBooksResponse> {
  return apiFetch<TopBooksResponse>(
    `/admin/analytics/sales/top-books?sort_by=${sort_by}&limit=${limit}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}

/**
 * Fetch inventory items below the stock threshold.
 * Default threshold: 10 units.
 */
export async function fetchLowStock(
  accessToken: string,
  threshold: number = 10
): Promise<LowStockResponse> {
  return apiFetch<LowStockResponse>(
    `/admin/analytics/inventory/low-stock?threshold=${threshold}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}
