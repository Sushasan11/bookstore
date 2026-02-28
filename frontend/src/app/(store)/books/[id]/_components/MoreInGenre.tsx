import type { BookResponse } from '@/lib/catalog'
import { BookCard } from '@/app/(store)/catalog/_components/BookCard'

interface MoreInGenreProps {
  books: BookResponse[]
  genreName?: string
}

export function MoreInGenre({ books, genreName }: MoreInGenreProps) {
  if (books.length === 0) {
    return null
  }

  return (
    <section className="mt-12">
      <h2 className="text-2xl font-semibold mb-6">
        More in {genreName ?? 'this Genre'}
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {books.map(book => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>
    </section>
  )
}
