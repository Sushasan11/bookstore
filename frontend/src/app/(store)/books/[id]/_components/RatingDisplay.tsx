interface RatingDisplayProps {
  avgRating: number | null | undefined
  reviewCount: number
}

function StarIcon({ filled, half }: { filled: boolean; half?: boolean }) {
  if (half) {
    // Simple half-star representation using two spans
    return (
      <span className="relative inline-block" aria-hidden="true">
        <span className="text-muted-foreground">★</span>
        <span className="absolute inset-0 overflow-hidden w-1/2 text-yellow-500">★</span>
      </span>
    )
  }
  return (
    <span aria-hidden="true" className={filled ? 'text-yellow-500' : 'text-muted-foreground'}>
      ★
    </span>
  )
}

export function RatingDisplay({ avgRating, reviewCount }: RatingDisplayProps) {
  if (avgRating == null || reviewCount === 0) {
    return (
      <p className="text-sm text-muted-foreground mt-2">No reviews yet</p>
    )
  }

  const fullStars = Math.floor(avgRating)
  const hasHalfStar = avgRating % 1 >= 0.5
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0)

  const reviewLabel = `${reviewCount} review${reviewCount !== 1 ? 's' : ''}`

  return (
    <a
      href="#reviews"
      className="flex items-center gap-2 mt-2 cursor-pointer hover:underline"
      title={`${avgRating.toFixed(1)} out of 5 stars — ${reviewLabel}`}
    >
      <span className="flex items-center text-lg leading-none" aria-label={`${avgRating.toFixed(1)} out of 5 stars`}>
        {Array.from({ length: fullStars }, (_, i) => (
          <StarIcon key={`full-${i}`} filled />
        ))}
        {hasHalfStar && <StarIcon filled={false} half />}
        {Array.from({ length: emptyStars }, (_, i) => (
          <StarIcon key={`empty-${i}`} filled={false} />
        ))}
      </span>
      <span className="text-sm text-muted-foreground">
        {avgRating.toFixed(1)} ({reviewLabel})
      </span>
    </a>
  )
}
