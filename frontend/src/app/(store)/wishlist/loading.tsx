import { Skeleton } from '@/components/ui/skeleton'

export default function WishlistLoading() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <Skeleton className="h-8 w-40 mb-6" />
      <ul className="divide-y">
        {Array.from({ length: 3 }).map((_, i) => (
          <li key={i} className="flex items-center gap-4 py-4">
            {/* Cover thumbnail skeleton */}
            <Skeleton className="h-[72px] w-12 rounded flex-shrink-0" />

            {/* Book info skeleton */}
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>

            {/* Remove button skeleton */}
            <Skeleton className="h-9 w-9 rounded-md" />
          </li>
        ))}
      </ul>
    </div>
  )
}
