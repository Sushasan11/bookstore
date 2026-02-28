import { BookCard } from './BookCard'
import type { BookResponse } from '@/lib/catalog'

interface NoResultsProps {
  query?: string
  popularBooks?: BookResponse[]
}

export function NoResults({ query, popularBooks }: NoResultsProps) {
  return (
    <div className="flex flex-col items-center py-16 text-center">
      <h2 className="text-2xl font-semibold mb-3">
        {query ? `No books found for "${query}"` : 'No books found'}
      </h2>
      <p className="text-muted-foreground mb-4">Try adjusting your search or filters.</p>
      <ul className="text-sm text-muted-foreground space-y-1 text-left list-disc list-inside">
        <li>Check your spelling</li>
        <li>Try a broader search term</li>
        <li>Browse by genre using the filter above</li>
      </ul>

      {popularBooks && popularBooks.length > 0 && (
        <div className="w-full mt-8">
          <h3 className="text-lg font-semibold mb-4 text-left">Popular Books</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {popularBooks.map((book) => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
