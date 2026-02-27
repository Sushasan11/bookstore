import { BookGridSkeleton } from './_components/BookCardSkeleton'

export default function CatalogLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="h-9 w-48 bg-muted rounded mb-6" />
      <div className="h-10 w-full bg-muted rounded mb-6" />
      <BookGridSkeleton />
    </div>
  )
}
