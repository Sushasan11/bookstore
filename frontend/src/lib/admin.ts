import { apiFetch, ApiError } from '@/lib/api'
import type { components } from '@/types/api.generated'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type BookCreate = components['schemas']['BookCreate']
type BookUpdate = components['schemas']['BookUpdate']
type BookResponse = components['schemas']['BookResponse']
type AdminUserResponse = components['schemas']['AdminUserResponse']
type UserListResponse = components['schemas']['UserListResponse']
type AdminReviewListResponse = components['schemas']['AdminReviewListResponse']
type BulkDeleteResponse = components['schemas']['BulkDeleteResponse']

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
    topBooks: (limit: number, sort_by: 'revenue' | 'volume' = 'revenue', period?: string) =>
      ['admin', 'sales', 'top-books', limit, sort_by, period] as const,
  },
  inventory: {
    all: ['admin', 'inventory'] as const,
    lowStock: (threshold: number) => ['admin', 'inventory', 'low-stock', threshold] as const,
  },
  catalog: {
    all: ['admin', 'catalog'] as const,
    list: (params: { q?: string; genre_id?: number; page?: number }) =>
      ['admin', 'catalog', 'list', params] as const,
    genres: ['admin', 'catalog', 'genres'] as const,
  },
  users: {
    all: ['admin', 'users'] as const,
    list: (params: { role?: string | null; is_active?: boolean | null; page?: number }) =>
      ['admin', 'users', 'list', params] as const,
  },
  reviews: {
    all: ['admin', 'reviews'] as const,
    list: (params: {
      book_id?: number | null; user_id?: number | null;
      rating_min?: number | null; rating_max?: number | null;
      sort_by?: string; sort_dir?: string; page?: number;
    }) => ['admin', 'reviews', 'list', params] as const,
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
 * Fetch top N books sorted by revenue or volume, optionally filtered by period.
 * Default: top 5 by revenue, all-time data.
 */
export async function fetchTopBooks(
  accessToken: string,
  limit: number = 5,
  sort_by: 'revenue' | 'volume' = 'revenue',
  period?: string
): Promise<TopBooksResponse> {
  const params = new URLSearchParams({ sort_by, limit: String(limit) })
  if (period) params.set('period', period)
  return apiFetch<TopBooksResponse>(
    `/admin/analytics/sales/top-books?${params}`,
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

/**
 * Update a book's stock quantity.
 * Backend: PATCH /books/{book_id}/stock with { quantity: int (>= 0) }
 * Admin-only endpoint. Triggers restock alerts if quantity goes from 0 to positive.
 */
export async function updateBookStock(
  accessToken: string,
  bookId: number,
  quantity: number
): Promise<BookResponse> {
  return apiFetch<BookResponse>(
    `/books/${bookId}/stock`,
    {
      method: 'PATCH',
      body: JSON.stringify({ quantity }),
      headers: { Authorization: `Bearer ${accessToken}` },
    }
  )
}

/**
 * Create a new book. Admin-only (POST /books requires admin role).
 */
export async function createBook(
  accessToken: string,
  data: BookCreate
): Promise<BookResponse> {
  return apiFetch<BookResponse>('/books', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

/**
 * Update an existing book. Admin-only (PUT /books/{id} requires admin role).
 */
export async function updateBook(
  accessToken: string,
  bookId: number,
  data: BookUpdate
): Promise<BookResponse> {
  return apiFetch<BookResponse>(`/books/${bookId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

/**
 * Delete a book. Admin-only (DELETE /books/{id} returns 204 No Content).
 * apiFetch handles 204 No Content by returning undefined as T.
 */
export async function deleteBook(
  accessToken: string,
  bookId: number
): Promise<void> {
  return apiFetch<void>(`/books/${bookId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

// ---------------------------------------------------------------------------
// Image upload
// ---------------------------------------------------------------------------

/**
 * Upload a cover image file. Uses raw fetch with FormData (not apiFetch)
 * because the request is multipart, not JSON.
 * Returns the full URL to the uploaded image.
 */
export async function uploadImage(
  accessToken: string,
  file: File
): Promise<{ url: string }> {
  const form = new FormData()
  form.append('file', file)

  const res = await fetch(`${API_BASE}/uploads/images`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: form,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(body.detail ?? `Upload failed (${res.status})`, res.status, body.detail)
  }

  return res.json()
}

// ---------------------------------------------------------------------------
// User management functions
// ---------------------------------------------------------------------------

/**
 * Fetch paginated list of all users. Supports role and is_active filters.
 * Uses total_count (not total) in UserListResponse.
 */
export async function fetchAdminUsers(
  accessToken: string,
  params: { page?: number; per_page?: number; role?: string | null; is_active?: boolean | null }
): Promise<UserListResponse> {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.per_page) qs.set('per_page', String(params.per_page))
  if (params.role != null) qs.set('role', params.role)
  if (params.is_active != null) qs.set('is_active', String(params.is_active))
  return apiFetch<UserListResponse>(`/admin/users?${qs}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

/**
 * Deactivate a user account. Admin-only. Returns 403 if target is an admin.
 * Immediately revokes session tokens and locks out the user.
 */
export async function deactivateUser(
  accessToken: string,
  userId: number
): Promise<AdminUserResponse> {
  return apiFetch<AdminUserResponse>(`/admin/users/${userId}/deactivate`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

/**
 * Reactivate a previously deactivated user account. Admin-only. Idempotent.
 * User can log in again immediately after reactivation.
 */
export async function reactivateUser(
  accessToken: string,
  userId: number
): Promise<AdminUserResponse> {
  return apiFetch<AdminUserResponse>(`/admin/users/${userId}/reactivate`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

// ---------------------------------------------------------------------------
// Review moderation functions
// ---------------------------------------------------------------------------

/**
 * Fetch paginated list of reviews with optional filters for book, user, rating range,
 * and sort options. Uses total_count (not total) in AdminReviewListResponse.
 */
export async function fetchAdminReviews(
  accessToken: string,
  params: {
    page?: number; per_page?: number;
    book_id?: number | null; user_id?: number | null;
    rating_min?: number | null; rating_max?: number | null;
    sort_by?: string; sort_dir?: string;
  }
): Promise<AdminReviewListResponse> {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.per_page) qs.set('per_page', String(params.per_page))
  if (params.book_id != null) qs.set('book_id', String(params.book_id))
  if (params.user_id != null) qs.set('user_id', String(params.user_id))
  if (params.rating_min != null) qs.set('rating_min', String(params.rating_min))
  if (params.rating_max != null) qs.set('rating_max', String(params.rating_max))
  if (params.sort_by) qs.set('sort_by', params.sort_by)
  if (params.sort_dir) qs.set('sort_dir', params.sort_dir)
  return apiFetch<AdminReviewListResponse>(`/admin/reviews?${qs}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

/**
 * Delete a single review by ID. Uses /reviews/{review_id} — admin bypass is
 * automatic via token role check. Returns 204 No Content.
 */
export async function deleteSingleReview(
  accessToken: string,
  reviewId: number
): Promise<void> {
  return apiFetch<void>(`/reviews/${reviewId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

/**
 * Bulk-delete multiple reviews in a single request. Max 50 review IDs per request.
 * Returns deleted_count indicating how many reviews were removed.
 */
export async function bulkDeleteReviews(
  accessToken: string,
  reviewIds: number[]
): Promise<BulkDeleteResponse> {
  return apiFetch<BulkDeleteResponse>('/admin/reviews/bulk', {
    method: 'DELETE',
    body: JSON.stringify({ review_ids: reviewIds }),
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
