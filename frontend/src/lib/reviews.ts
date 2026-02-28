'use client'

import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch, ApiError } from '@/lib/api'
import type { components } from '@/types/api.generated'

export type ReviewResponse = components['schemas']['ReviewResponse']
export type ReviewListResponse = components['schemas']['ReviewListResponse']
export type ReviewCreate = components['schemas']['ReviewCreate']
export type ReviewUpdate = components['schemas']['ReviewUpdate']

// Cache key for reviews queries — parameterized by bookId (per-book cache)
export const REVIEWS_KEY = (bookId: number) => ['reviews', bookId] as const

// ---------------------------------------------------------------------------
// Reviews API functions
// ---------------------------------------------------------------------------

/** Fetch all reviews for a book — public endpoint, no auth required. */
export async function fetchReviews(bookId: number): Promise<ReviewListResponse> {
  return apiFetch<ReviewListResponse>(`/books/${bookId}/reviews?size=50`)
}

/** Create a review for a book — requires auth and prior purchase (403 otherwise). */
export async function createReview(
  accessToken: string,
  bookId: number,
  body: ReviewCreate
): Promise<ReviewResponse> {
  return apiFetch<ReviewResponse>(`/books/${bookId}/reviews`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(body),
  })
}

/**
 * Update an existing review — PATCH with partial body only.
 * Only include fields that changed (see Pitfall 4: partial update semantics).
 */
export async function updateReview(
  accessToken: string,
  reviewId: number,
  body: ReviewUpdate
): Promise<ReviewResponse> {
  return apiFetch<ReviewResponse>(`/reviews/${reviewId}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(body),
  })
}

/** Delete a review — returns void (204 No Content). */
export async function deleteReview(
  accessToken: string,
  reviewId: number
): Promise<void> {
  return apiFetch<void>(`/reviews/${reviewId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

// ---------------------------------------------------------------------------
// useReviews hook — reviews list query + create/update/delete mutations
// ---------------------------------------------------------------------------

export function useReviews(bookId: number) {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

  // Public query — does NOT require auth, always fetches
  const reviewsQuery = useQuery({
    queryKey: REVIEWS_KEY(bookId),
    queryFn: () => fetchReviews(bookId),
    staleTime: 30_000,
  })

  // Derive current user's own review by matching author.user_id to session user
  const myReview: ReviewResponse | null = (() => {
    if (!session?.user?.id) return null
    const userId = Number(session.user.id)
    return reviewsQuery.data?.items.find((r) => r.author.user_id === userId) ?? null
  })()

  // ---- createMutation ----
  const createMutation = useMutation({
    mutationFn: (body: ReviewCreate) => createReview(accessToken, bookId, body),
    onSuccess: () => {
      toast.success('Review submitted!')
      queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 403) {
        toast.error('You must purchase this book before reviewing it')
      } else if (err instanceof ApiError && err.status === 409) {
        const body = err.data as { code: string; existing_review_id?: number }
        if (body?.code === 'DUPLICATE_REVIEW') {
          queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
          toast.info('Showing your existing review — you can edit it below')
        } else {
          toast.error('Failed to submit review')
        }
      } else {
        toast.error('Failed to submit review')
      }
    },
  })

  // ---- updateMutation ----
  const updateMutation = useMutation({
    mutationFn: ({ reviewId, body }: { reviewId: number; body: ReviewUpdate }) =>
      updateReview(accessToken, reviewId, body),
    onSuccess: () => {
      toast.success('Review updated!')
      queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
    },
    onError: () => {
      toast.error('Failed to update review')
    },
  })

  // ---- deleteMutation ----
  const deleteMutation = useMutation({
    mutationFn: ({ reviewId }: { reviewId: number }) =>
      deleteReview(accessToken, reviewId),
    onSuccess: () => {
      toast.success('Review deleted')
      queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
    },
    onError: () => {
      toast.error('Failed to delete review')
    },
  })

  return {
    reviewsQuery,
    createMutation,
    updateMutation,
    deleteMutation,
    myReview,
  }
}
