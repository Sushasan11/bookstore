import { apiFetch, ApiError } from '@/lib/api'
import type { components } from '@/types/api.generated'

type BookListResponse = components['schemas']['BookListResponse']
type BookDetailResponse = components['schemas']['BookDetailResponse']
type GenreResponse = components['schemas']['GenreResponse']

// Re-export types for consumer convenience
export type { BookListResponse, BookDetailResponse, GenreResponse }
export type BookResponse = components['schemas']['BookResponse']

export async function fetchBooks(params: {
  q?: string
  genre_id?: number
  min_price?: number
  max_price?: number
  sort?: string
  sort_dir?: 'asc' | 'desc'
  page?: number
  size?: number
}): Promise<BookListResponse> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.genre_id) qs.set('genre_id', String(params.genre_id))
  if (params.min_price !== undefined) qs.set('min_price', String(params.min_price))
  if (params.max_price !== undefined) qs.set('max_price', String(params.max_price))
  if (params.sort) qs.set('sort', params.sort)
  if (params.sort_dir) qs.set('sort_dir', params.sort_dir)
  if (params.page) qs.set('page', String(params.page))
  if (params.size) qs.set('size', String(params.size))
  return apiFetch<BookListResponse>(`/books?${qs}`)
}

export async function fetchBook(id: number): Promise<BookDetailResponse | null> {
  try {
    return await apiFetch<BookDetailResponse>(`/books/${id}`)
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

export async function fetchGenres(): Promise<GenreResponse[]> {
  return apiFetch<GenreResponse[]>('/genres')
}
