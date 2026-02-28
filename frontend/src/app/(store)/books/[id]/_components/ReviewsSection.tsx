'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { useReviews, REVIEWS_KEY, fetchReviews } from '@/lib/reviews'
import type { components } from '@/types/api.generated'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ReviewCard } from './ReviewCard'
import { ReviewForm } from './ReviewForm'
import Link from 'next/link'

type ReviewResponse = components['schemas']['ReviewResponse']
type ReviewListResponse = components['schemas']['ReviewListResponse']

interface ReviewsSectionProps {
  bookId: number
  initialReviews: ReviewListResponse
}

export function ReviewsSection({ bookId, initialReviews }: ReviewsSectionProps) {
  const { data: session } = useSession()
  const userId = session?.user?.id ? Number(session.user.id) : null

  // Separate query for list data with initialData support (server-seeded)
  const reviewsListQuery = useQuery({
    queryKey: REVIEWS_KEY(bookId),
    queryFn: () => fetchReviews(bookId),
    initialData: initialReviews,
    staleTime: 30_000,
  })

  // Hook for mutations + myReview (shares same REVIEWS_KEY cache — TanStack deduplicates)
  const { createMutation, updateMutation, deleteMutation, myReview } = useReviews(bookId)

  // Internal state
  const [editingReview, setEditingReview] = useState<ReviewResponse | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [reviewToDelete, setReviewToDelete] = useState<number | null>(null)

  // Close delete dialog on successful deletion
  useEffect(() => {
    if (deleteMutation.isSuccess) {
      setDeleteDialogOpen(false)
      setReviewToDelete(null)
      setEditingReview(null)
    }
  }, [deleteMutation.isSuccess])

  const reviews = reviewsListQuery.data

  // Sort reviews: own review first, then by created_at descending
  const sortedReviews = reviews
    ? [...reviews.items].sort((a, b) => {
        const aIsOwn = a.author.user_id === userId
        const bIsOwn = b.author.user_id === userId
        if (aIsOwn && !bIsOwn) return -1
        if (!aIsOwn && bIsOwn) return 1
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      })
    : []

  const reviewCount = reviews?.total ?? 0

  return (
    <section id="reviews" className="mt-12">
      <h2 className="text-xl font-semibold mb-6">
        Reviews {reviewCount > 0 ? `(${reviewCount})` : ''}
      </h2>

      {/* Review form area */}
      {!session?.accessToken ? (
        <p className="text-muted-foreground mb-6">
          <Link href="/login" className="underline hover:text-foreground">
            Sign in
          </Link>{' '}
          to write a review.
        </p>
      ) : editingReview ? (
        <ReviewForm
          bookId={bookId}
          existingReview={editingReview}
          createMutation={createMutation}
          updateMutation={updateMutation}
          onSubmitSuccess={() => setEditingReview(null)}
        />
      ) : myReview ? (
        // User already reviewed — edit/delete buttons are on their ReviewCard
        null
      ) : (
        <ReviewForm
          bookId={bookId}
          createMutation={createMutation}
          updateMutation={updateMutation}
        />
      )}

      {/* Review list */}
      {sortedReviews.length === 0 ? (
        <p className="text-muted-foreground">
          {session?.accessToken
            ? 'No reviews yet. Be the first to review this book!'
            : 'No reviews yet.'}
        </p>
      ) : (
        <div>
          {sortedReviews.map((review) => (
            <ReviewCard
              key={review.id}
              review={review}
              isOwn={review.author.user_id === userId}
              onEdit={() => setEditingReview(review)}
              onDelete={() => {
                setReviewToDelete(review.id)
                setDeleteDialogOpen(true)
              }}
            />
          ))}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Review</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete your review? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (reviewToDelete) {
                  deleteMutation.mutate({ reviewId: reviewToDelete })
                }
              }}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
