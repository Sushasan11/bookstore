import { Skeleton } from '@/components/ui/skeleton'

export default function CartLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Skeleton className="h-8 w-48 mb-6" />
      <div className="lg:flex lg:gap-8">
        <div className="flex-1 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-4 p-4 border rounded-lg">
              <Skeleton className="h-24 w-16 rounded" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-4 w-20" />
              </div>
            </div>
          ))}
        </div>
        <Skeleton className="h-48 w-full lg:w-80 mt-6 lg:mt-0 rounded-lg" />
      </div>
    </div>
  )
}
