import Link from 'next/link'

type Genre = { id: number; name: string }

interface BreadcrumbNavProps {
  genre?: Genre | undefined
  bookTitle: string
}

export function BreadcrumbNav({ genre, bookTitle }: BreadcrumbNavProps) {
  return (
    <nav aria-label="Breadcrumb" className="mb-6">
      <ol className="flex items-center gap-1 text-sm text-muted-foreground">
        <li>
          <Link href="/" className="hover:text-foreground transition-colors">
            Home
          </Link>
        </li>
        {genre && (
          <>
            <li className="mx-1 select-none">/</li>
            <li>
              <Link
                href={`/catalog?genre_id=${genre.id}`}
                className="hover:text-foreground transition-colors"
              >
                {genre.name}
              </Link>
            </li>
          </>
        )}
        <li className="mx-1 select-none">/</li>
        <li className="text-foreground font-medium truncate max-w-[200px] sm:max-w-xs">
          {bookTitle}
        </li>
      </ol>
    </nav>
  )
}
