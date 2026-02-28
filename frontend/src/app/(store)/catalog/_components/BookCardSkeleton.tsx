import { Skeleton } from '@/components/ui/skeleton'

export function BookCardSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="aspect-[2/3] w-full rounded-lg" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
      <Skeleton className="h-4 w-1/4" />
    </div>
  )
}

export function BookGridSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
      {Array.from({ length: 20 }).map((_, i) => (
        <BookCardSkeleton key={i} />
      ))}
    </div>
  )
}
