'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDebounce } from 'use-debounce'
import { type ColumnDef } from '@tanstack/react-table'
import { MoreHorizontal } from 'lucide-react'
import { toast } from 'sonner'
import { adminKeys, createBook, updateBook, deleteBook } from '@/lib/admin'
import { triggerRevalidation } from '@/lib/revalidate'
import { fetchBooks, fetchGenres, type BookResponse } from '@/lib/catalog'
import { ApiError } from '@/lib/api'
import { DataTable } from '@/components/admin/DataTable'
import { AdminPagination } from '@/components/admin/AdminPagination'
import { BookForm, type BookFormValues } from '@/components/admin/BookForm'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { StockUpdateModal } from '@/components/admin/StockUpdateModal'
import { StockBadge } from '@/components/admin/StockBadge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import type { components } from '@/types/api.generated'

type BookCreate = components['schemas']['BookCreate']
type BookUpdate = components['schemas']['BookUpdate']

const PAGE_SIZE = 20

export default function AdminCatalogPage() {
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch] = useDebounce(searchInput, 500)
  const [selectedGenre, setSelectedGenre] = useState<number | undefined>(undefined)
  const [page, setPage] = useState(1)

  // CRUD state
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingBook, setEditingBook] = useState<BookResponse | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<BookResponse | null>(null)
  const [stockTarget, setStockTarget] = useState<{
    book_id: number
    title: string
    current_stock: number
  } | null>(null)

  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

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

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: BookFormValues) => {
      const payload: BookCreate = {
        ...data,
        isbn: data.isbn || null,
        genre_id: typeof data.genre_id === 'number' ? data.genre_id : null,
        description: data.description || null,
        cover_image_url: data.cover_image_url || null,
        publish_date: data.publish_date || null,
      }
      return createBook(accessToken, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.catalog.all })
      queryClient.invalidateQueries({ queryKey: ['books'] })
      triggerRevalidation(['/catalog'])
      toast.success('Book added successfully')
      setDrawerOpen(false)
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.detail ?? 'Failed to add book' : 'Failed to add book'
      )
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: BookFormValues) => {
      const payload: BookUpdate = {
        ...data,
        isbn: data.isbn || null,
        genre_id: typeof data.genre_id === 'number' ? data.genre_id : null,
        description: data.description || null,
        cover_image_url: data.cover_image_url || null,
        publish_date: data.publish_date || null,
      }
      return updateBook(accessToken, editingBook!.id, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.catalog.all })
      queryClient.invalidateQueries({ queryKey: ['books'] })
      triggerRevalidation(['/catalog', `/books/${editingBook!.id}`])
      toast.success('Book updated successfully')
      setDrawerOpen(false)
      setEditingBook(null)
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError
          ? error.detail ?? 'Failed to update book'
          : 'Failed to update book'
      )
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteBook(accessToken, deleteTarget!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.catalog.all })
      queryClient.invalidateQueries({ queryKey: ['books'] })
      triggerRevalidation(['/catalog'])
      toast.success('Book deleted successfully')
      setDeleteTarget(null)
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError
          ? error.detail ?? 'Failed to delete book'
          : 'Failed to delete book'
      )
    },
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
      cell: ({ row }) => <StockBadge stock={row.original.stock_quantity} threshold={10} />,
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
                onClick={() => {
                  setEditingBook(book)
                  setDrawerOpen(true)
                }}
              >
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() =>
                  setStockTarget({
                    book_id: book.id,
                    title: book.title,
                    current_stock: book.stock_quantity,
                  })
                }
              >
                Update Stock
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => setDeleteTarget(book)}
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
        <Button
          onClick={() => {
            setEditingBook(null)
            setDrawerOpen(true)
          }}
        >
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

      {/* Add / Edit Book side drawer */}
      <Sheet
        open={drawerOpen}
        onOpenChange={(open) => {
          if (!open) {
            setDrawerOpen(false)
            setEditingBook(null)
          } else {
            setDrawerOpen(true)
          }
        }}
      >
        <SheetContent side="right" className="sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{editingBook ? 'Edit Book' : 'Add Book'}</SheetTitle>
            <SheetDescription>
              {editingBook ? 'Update book details' : 'Add a new book to the catalog'}
            </SheetDescription>
          </SheetHeader>
          <BookForm
            book={editingBook}
            genres={genresQuery.data ?? []}
            onSubmit={(data) =>
              editingBook ? updateMutation.mutate(data) : createMutation.mutate(data)
            }
            onCancel={() => {
              setDrawerOpen(false)
              setEditingBook(null)
            }}
            isPending={createMutation.isPending || updateMutation.isPending}
            accessToken={accessToken}
          />
        </SheetContent>
      </Sheet>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="Delete Book"
        description={`Are you sure you want to delete '${deleteTarget?.title}'? This action cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => deleteMutation.mutate()}
        isPending={deleteMutation.isPending}
      />

      {/* Stock update modal */}
      <StockUpdateModal
        open={stockTarget !== null}
        onOpenChange={(open) => {
          if (!open) setStockTarget(null)
        }}
        book={stockTarget}
        accessToken={accessToken}
      />
    </div>
  )
}
