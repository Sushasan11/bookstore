'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from 'use-debounce'
import { type ColumnDef } from '@tanstack/react-table'
import { MoreHorizontal } from 'lucide-react'
import { adminKeys } from '@/lib/admin'
import { fetchBooks, fetchGenres, type BookResponse } from '@/lib/catalog'
import { DataTable } from '@/components/admin/DataTable'
import { AdminPagination } from '@/components/admin/AdminPagination'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const PAGE_SIZE = 20

function StockBadge({ stock }: { stock: number }) {
  if (stock === 0) {
    return (
      <Badge className="bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400">
        Out of Stock
      </Badge>
    )
  }
  if (stock <= 10) {
    return (
      <Badge className="bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400">
        Low Stock ({stock})
      </Badge>
    )
  }
  return <span className="font-medium">{stock}</span>
}

export default function AdminCatalogPage() {
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch] = useDebounce(searchInput, 500)
  const [selectedGenre, setSelectedGenre] = useState<number | undefined>(undefined)
  const [page, setPage] = useState(1)

  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''

  // Fetch genres for filter dropdown and genreMap
  const genresQuery = useQuery({
    queryKey: adminKeys.catalog.genres,
    queryFn: fetchGenres,
    staleTime: 5 * 60_000,
  })

  const genreMap = new Map<number, string>(
    (genresQuery.data ?? []).map((g) => [g.id, g.name])
  )

  // Fetch books with pagination, search, and genre filter
  const booksQuery = useQuery({
    queryKey: adminKeys.catalog.list({
      q: debouncedSearch || undefined,
      genre_id: selectedGenre,
      page,
    }),
    queryFn: () =>
      fetchBooks({
        q: debouncedSearch || undefined,
        genre_id: selectedGenre,
        page,
        size: PAGE_SIZE,
      }),
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  function handleSearchChange(value: string) {
    setSearchInput(value)
    setPage(1)
  }

  function handleGenreChange(value: string) {
    setSelectedGenre(value === 'all' ? undefined : Number(value))
    setPage(1)
  }

  // Column definitions for DataTable
  const columns: ColumnDef<BookResponse, unknown>[] = [
    {
      accessorKey: 'title',
      header: 'Title',
      cell: ({ row }) => (
        <span className="font-medium">{row.original.title}</span>
      ),
    },
    {
      accessorKey: 'author',
      header: 'Author',
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.author}</span>
      ),
    },
    {
      accessorKey: 'price',
      header: 'Price',
      cell: ({ row }) => (
        <span className="text-right block">${row.original.price}</span>
      ),
    },
    {
      id: 'genre',
      header: 'Genre',
      cell: ({ row }) => {
        const genreName = row.original.genre_id
          ? genreMap.get(row.original.genre_id)
          : null
        return <span className="text-muted-foreground">{genreName ?? '—'}</span>
      },
    },
    {
      id: 'stock',
      header: 'Stock',
      cell: ({ row }) => <StockBadge stock={row.original.stock_quantity} />,
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const book = row.original
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => console.log('Edit', book.id)}
              >
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => console.log('Update Stock', book.id)}
              >
                Update Stock
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => console.log('Delete', book.id)}
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )
      },
    },
  ]

  const books = booksQuery.data?.items ?? []
  const total = booksQuery.data?.total ?? 0

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Book Catalog</h1>
        <Button onClick={() => console.log('Add Book — wired in Plan 02')}>
          Add Book
        </Button>
      </div>

      {/* Search and filter controls */}
      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search books..."
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={selectedGenre !== undefined ? String(selectedGenre) : 'all'}
          onValueChange={handleGenreChange}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Genres" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Genres</SelectItem>
            {(genresQuery.data ?? []).map((genre) => (
              <SelectItem key={genre.id} value={String(genre.id)}>
                {genre.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Error state */}
      {booksQuery.isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 flex items-center justify-between">
          <p className="text-sm text-destructive">Failed to load catalog.</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => booksQuery.refetch()}
          >
            Retry
          </Button>
        </div>
      )}

      {/* Books table */}
      <DataTable
        columns={columns}
        data={books}
        isLoading={booksQuery.isLoading}
        emptyMessage="No books found. Try adjusting your search or filter."
      />

      {/* Pagination */}
      {total > 0 && (
        <AdminPagination
          page={page}
          total={total}
          size={PAGE_SIZE}
          onPageChange={setPage}
        />
      )}
    </div>
  )
}
