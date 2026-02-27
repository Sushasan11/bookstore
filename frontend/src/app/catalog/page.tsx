import { Suspense } from 'react'
import type { Metadata } from 'next'
import { fetchBooks, fetchGenres } from '@/lib/catalog'
import { SearchControls } from './_components/SearchControls'
import { BookGrid } from './_components/BookGrid'
import { BookGridSkeleton } from './_components/BookCardSkeleton'
import { Pagination } from './_components/Pagination'

export const metadata: Metadata = {
  title: 'Browse Books',
  description: 'Browse, search, and filter our book catalog',
}

type CatalogPageProps = {
  searchParams: Promise<{
    q?: string
    genre_id?: string
    min_price?: string
    max_price?: string
    sort?: string
    sort_dir?: string
    page?: string
  }>
}

const PAGE_SIZE = 20

export default async function CatalogPage({ searchParams }: CatalogPageProps) {
  const params = await searchParams

  const q = params.q
  const genre_id = params.genre_id ? Number(params.genre_id) : undefined
  const min_price = params.min_price ? Number(params.min_price) : undefined
  const max_price = params.max_price ? Number(params.max_price) : undefined
  const sort = params.sort
  const sort_dir = params.sort_dir as 'asc' | 'desc' | undefined
  const page = params.page ? Number(params.page) : 1

  const [booksData, genres] = await Promise.all([
    fetchBooks({ q, genre_id, min_price, max_price, sort, sort_dir, page, size: PAGE_SIZE }),
    fetchGenres(),
  ])

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Browse Books</h1>

      <Suspense fallback={null}>
        <SearchControls genres={genres} />
      </Suspense>

      <Suspense fallback={<BookGridSkeleton />}>
        <BookGrid books={booksData.items} query={q} />
      </Suspense>

      <Suspense fallback={null}>
        <Pagination total={booksData.total} page={page} size={PAGE_SIZE} />
      </Suspense>
    </div>
  )
}
