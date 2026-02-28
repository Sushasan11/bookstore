'use client'

import { useState, useEffect } from 'react'
import type { UseMutationResult } from '@tanstack/react-query'
import type { components } from '@/types/api.generated'
import { StarSelector } from './StarSelector'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'

type ReviewResponse = components['schemas']['ReviewResponse']
type ReviewCreate = components['schemas']['ReviewCreate']
type ReviewUpdate = components['schemas']['ReviewUpdate']

interface ReviewFormProps {
  bookId: number
  existingReview?: ReviewResponse | null  // null = create mode, review = edit mode
  onSubmitSuccess?: () => void            // callback to reset edit mode in parent
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  createMutation: UseMutationResult<ReviewResponse, Error, ReviewCreate, any>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  updateMutation: UseMutationResult<ReviewResponse, Error, { reviewId: number; body: ReviewUpdate }, any>
}

export function ReviewForm({
  existingReview,
  onSubmitSuccess,
  createMutation,
  updateMutation,
}: ReviewFormProps) {
  const isEditMode = existingReview != null

  const [rating, setRating] = useState<number>(existingReview?.rating ?? 0)
  const [text, setText] = useState<string>(existingReview?.text ?? '')

  // When existingReview changes (edit mode toggled), reset local state
  useEffect(() => {
    setRating(existingReview?.rating ?? 0)
    setText(existingReview?.text ?? '')
  }, [existingReview])

  const isPending = createMutation.isPending || updateMutation.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (isEditMode && existingReview) {
      // Build selective PATCH body — only include changed fields
      const body: ReviewUpdate = {}
      if (rating !== existingReview.rating) {
        body.rating = rating
      }
      const trimmedText = text.trim()
      const originalText = existingReview.text ?? ''
      if (trimmedText !== originalText) {
        body.text = trimmedText || null
      }

      updateMutation.mutate(
        { reviewId: existingReview.id, body },
        {
          onSuccess: () => {
            onSubmitSuccess?.()
          },
        }
      )
    } else {
      // Create mode
      const body: ReviewCreate = {
        rating,
        text: text.trim() || undefined,
      }
      createMutation.mutate(body, {
        onSuccess: () => {
          onSubmitSuccess?.()
          setRating(0)
          setText('')
        },
      })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 mb-8">
      <h3 className="text-lg font-semibold">
        {isEditMode ? 'Edit Your Review' : 'Write a Review'}
      </h3>

      <div>
        <label className="block text-sm font-medium mb-2">Your Rating</label>
        <StarSelector value={rating} onChange={setRating} disabled={isPending} />
      </div>

      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Share your thoughts about this book (optional)"
        rows={3}
        disabled={isPending}
      />

      <div className="flex gap-2">
        <Button
          type="submit"
          disabled={rating === 0 || isPending}
        >
          {isPending
            ? isEditMode ? 'Updating...' : 'Submitting...'
            : isEditMode ? 'Update Review' : 'Submit Review'}
        </Button>

        {isEditMode && (
          <Button
            type="button"
            variant="outline"
            onClick={() => onSubmitSuccess?.()}
            disabled={isPending}
          >
            Cancel
          </Button>
        )}
      </div>
    </form>
  )
}
