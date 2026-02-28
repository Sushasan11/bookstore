import { fetchBooks } from '@/lib/catalog'
import type { BookResponse } from '@/lib/catalog'
import { BookCard } from './BookCard'
import { NoResults } from './NoResults'

interface BookGridProps {
  books: BookResponse[]
  query?: string
}

export async function BookGrid({ books, query }: BookGridProps) {
  if (books.length === 0) {
    const popular = await fetchBooks({ sort: 'avg_rating', sort_dir: 'desc', size: 4 })
    return <NoResults query={query} popularBooks={popular.items} />
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
      {books.map((book) => (
        <BookCard key={book.id} book={book} />
      ))}
    </div>
  )
}
