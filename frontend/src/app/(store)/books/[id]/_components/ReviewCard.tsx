import { Pencil, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { components } from '@/types/api.generated'

type ReviewResponse = components['schemas']['ReviewResponse']

interface ReviewCardProps {
  review: ReviewResponse
  isOwn: boolean       // true if this review belongs to the current user
  onEdit?: () => void  // called when user clicks "Edit" (Plan 25-02 will wire this)
  onDelete?: () => void // called when user clicks "Delete" (Plan 25-02 will wire this)
}

function formatReviewDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric', month: 'long', day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function ReviewCard({ review, isOwn, onEdit, onDelete }: ReviewCardProps) {
  const stars = [1, 2, 3, 4, 5]

  return (
    <div className="border-b py-4">
      {/* Header row: author, verified badge, date, and optional action buttons */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{review.author.display_name}</span>
          {review.verified_purchase && (
            <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-200 dark:border-green-800">
              Verified Purchase
            </Badge>
          )}
          <span className="text-sm text-muted-foreground">
            {formatReviewDate(review.created_at)}
          </span>
        </div>
        {/* Action buttons — only shown for current user's own review */}
        {isOwn && (onEdit || onDelete) && (
          <div className="flex items-center gap-1 shrink-0">
            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={onEdit}
                aria-label="Edit review"
              >
                <Pencil className="h-4 w-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={onDelete}
                aria-label="Delete review"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Star rating row */}
      <div className="flex gap-0.5 mt-1">
        {stars.map((star) => (
          <span
            key={star}
            className={star <= review.rating ? 'text-yellow-500' : 'text-muted-foreground'}
          >
            ★
          </span>
        ))}
      </div>

      {/* Review text */}
      {review.text && (
        <p className="text-muted-foreground mt-2">{review.text}</p>
      )}
    </div>
  )
}
