'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { type ColumnDef } from '@tanstack/react-table'
import { MoreHorizontal, Star } from 'lucide-react'
import { toast } from 'sonner'
import {
  adminKeys,
  fetchAdminReviews,
  deleteSingleReview,
  bulkDeleteReviews,
} from '@/lib/admin'
import { triggerRevalidation } from '@/lib/revalidate'
import { ApiError } from '@/lib/api'
import { DataTable } from '@/components/admin/DataTable'
import { AdminPagination } from '@/components/admin/AdminPagination'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
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
import type { components } from '@/types/api.generated'

type AdminReviewEntry = components['schemas']['AdminReviewEntry']

const PAGE_SIZE = 20

export default function ReviewsPage() {
  const [bookIdFilter, setBookIdFilter] = useState<string>('')
  const [userIdFilter, setUserIdFilter] = useState<string>('')
  const [ratingMin, setRatingMin] = useState<string>('any')
  const [ratingMax, setRatingMax] = useState<string>('any')
  const [sortBy, setSortBy] = useState<string>('date')
  const [sortDir, setSortDir] = useState<string>('desc')
  const [page, setPage] = useState<number>(1)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [deleteTarget, setDeleteTarget] = useState<AdminReviewEntry | null>(null)
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState<boolean>(false)

  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

  const reviewsQuery = useQuery({
    queryKey: adminKeys.reviews.list({
      book_id: bookIdFilter ? Number(bookIdFilter) : null,
      user_id: userIdFilter ? Number(userIdFilter) : null,
      rating_min: ratingMin !== 'any' ? Number(ratingMin) : null,
      rating_max: ratingMax !== 'any' ? Number(ratingMax) : null,
      sort_by: sortBy,
      sort_dir: sortDir,
      page,
    }),
    queryFn: () =>
      fetchAdminReviews(accessToken, {
        page,
        per_page: PAGE_SIZE,
        book_id: bookIdFilter ? Number(bookIdFilter) : null,
        user_id: userIdFilter ? Number(userIdFilter) : null,
        rating_min: ratingMin !== 'any' ? Number(ratingMin) : null,
        rating_max: ratingMax !== 'any' ? Number(ratingMax) : null,
        sort_by: sortBy,
        sort_dir: sortDir,
      }),
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  const singleDeleteMutation = useMutation({
    mutationFn: () => deleteSingleReview(accessToken, deleteTarget!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.reviews.all })
      triggerRevalidation([`/books/${deleteTarget!.book.book_id}`])
      toast.success('Review deleted')
      setDeleteTarget(null)
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.detail ?? 'Failed to delete review' : 'Failed to delete review'
      )
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: () => bulkDeleteReviews(accessToken, Array.from(selectedIds)),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.reviews.all })
      triggerRevalidation([{ path: '/books/[id]', type: 'page' }])
      toast.success(
        `${data.deleted_count} review${data.deleted_count === 1 ? '' : 's'} deleted`
      )
      setSelectedIds(new Set())
      setBulkConfirmOpen(false)
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.detail ?? 'Failed to delete reviews' : 'Failed to delete reviews'
      )
    },
  })

  // Checkbox selection helpers
  const allPageIds = (reviewsQuery.data?.items ?? []).map((r) => r.id)
  const allPageSelected =
    allPageIds.length > 0 && allPageIds.every((id) => selectedIds.has(id))

  // Filter change handlers — all reset page to 1 and clear selectedIds
  function handlePageChange(newPage: number) {
    setPage(newPage)
    setSelectedIds(new Set())
  }

  function handleBookIdChange(value: string) {
    setBookIdFilter(value)
    setPage(1)
    setSelectedIds(new Set())
  }

  function handleUserIdChange(value: string) {
    setUserIdFilter(value)
    setPage(1)
    setSelectedIds(new Set())
  }

  function handleRatingMinChange(value: string) {
    setRatingMin(value)
    setPage(1)
    setSelectedIds(new Set())
  }

  function handleRatingMaxChange(value: string) {
    setRatingMax(value)
    setPage(1)
    setSelectedIds(new Set())
  }

  function handleSortByChange(value: string) {
    setSortBy(value)
    setPage(1)
    setSelectedIds(new Set())
  }

  function handleSortDirChange(value: string) {
    setSortDir(value)
    setPage(1)
    setSelectedIds(new Set())
  }

  function toggleSelectAll() {
    if (allPageSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        allPageIds.forEach((id) => next.delete(id))
        return next
      })
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        allPageIds.forEach((id) => next.add(id))
        return next
      })
    }
  }

  function toggleSelectOne(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const columns: ColumnDef<AdminReviewEntry, unknown>[] = [
    {
      id: 'select',
      header: () => (
        <input
          type="checkbox"
          aria-label="Select all"
          checked={allPageSelected}
          onChange={toggleSelectAll}
          className="h-4 w-4 cursor-pointer"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          aria-label="Select row"
          checked={selectedIds.has(row.original.id)}
          onChange={() => toggleSelectOne(row.original.id)}
          className="h-4 w-4 cursor-pointer"
        />
      ),
    },
    {
      id: 'book',
      header: 'Book',
      cell: ({ row }) => (
        <span className="font-medium">{row.original.book.title}</span>
      ),
    },
    {
      id: 'reviewer',
      header: 'Reviewer',
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.author.display_name}</span>
      ),
    },
    {
      accessorKey: 'rating',
      header: 'Rating',
      cell: ({ row }) => (
        <span className="flex items-center gap-1">
          <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
          {row.original.rating}
        </span>
      ),
    },
    {
      id: 'text',
      header: 'Review',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-xs max-w-[200px] block">
          {row.original.text
            ? row.original.text.substring(0, 80) +
              (row.original.text.length > 80 ? '...' : '')
            : '—'}
        </span>
      ),
    },
    {
      id: 'date',
      header: 'Date',
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {new Date(row.original.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => setDeleteTarget(row.original)}
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  const reviews = reviewsQuery.data?.items ?? []

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Review Moderation</h1>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3">
        <Input
          type="number"
          placeholder="Book ID"
          value={bookIdFilter}
          onChange={(e) => handleBookIdChange(e.target.value)}
          className="w-28"
        />
        <Input
          type="number"
          placeholder="User ID"
          value={userIdFilter}
          onChange={(e) => handleUserIdChange(e.target.value)}
          className="w-28"
        />
        <Select value={ratingMin} onValueChange={handleRatingMinChange}>
          <SelectTrigger className="w-28">
            <SelectValue placeholder="Min ★" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Any</SelectItem>
            <SelectItem value="1">1 ★</SelectItem>
            <SelectItem value="2">2 ★</SelectItem>
            <SelectItem value="3">3 ★</SelectItem>
            <SelectItem value="4">4 ★</SelectItem>
            <SelectItem value="5">5 ★</SelectItem>
          </SelectContent>
        </Select>
        <Select value={ratingMax} onValueChange={handleRatingMaxChange}>
          <SelectTrigger className="w-28">
            <SelectValue placeholder="Max ★" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Any</SelectItem>
            <SelectItem value="1">1 ★</SelectItem>
            <SelectItem value="2">2 ★</SelectItem>
            <SelectItem value="3">3 ★</SelectItem>
            <SelectItem value="4">4 ★</SelectItem>
            <SelectItem value="5">5 ★</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sortBy} onValueChange={handleSortByChange}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="date">Date</SelectItem>
            <SelectItem value="rating">Rating</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sortDir} onValueChange={handleSortDirChange}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="desc">Desc</SelectItem>
            <SelectItem value="asc">Asc</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 rounded-lg border bg-muted/50 px-4 py-2">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setBulkConfirmOpen(true)}
          >
            Delete Selected
          </Button>
        </div>
      )}

      {/* Error state */}
      {reviewsQuery.isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 flex items-center justify-between">
          <p className="text-sm text-destructive">Failed to load reviews.</p>
          <Button variant="outline" size="sm" onClick={() => reviewsQuery.refetch()}>
            Retry
          </Button>
        </div>
      )}

      {/* Reviews table */}
      <DataTable
        columns={columns}
        data={reviews}
        isLoading={reviewsQuery.isLoading}
        emptyMessage="No reviews found."
      />

      {/* Pagination */}
      {(reviewsQuery.data?.total_count ?? 0) > 0 && (
        <AdminPagination
          page={page}
          total={reviewsQuery.data?.total_count ?? 0}
          size={PAGE_SIZE}
          onPageChange={handlePageChange}
        />
      )}

      {/* Single-delete ConfirmDialog */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="Delete Review"
        description={`Delete the review by ${deleteTarget?.author.display_name} for '${deleteTarget?.book.title}'? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => singleDeleteMutation.mutate()}
        isPending={singleDeleteMutation.isPending}
      />

      {/* Bulk-delete ConfirmDialog */}
      <ConfirmDialog
        open={bulkConfirmOpen}
        onOpenChange={(open) => {
          if (!open) setBulkConfirmOpen(false)
        }}
        title="Delete Reviews"
        description={`Delete ${selectedIds.size} selected review${selectedIds.size === 1 ? '' : 's'}? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => bulkDeleteMutation.mutate()}
        isPending={bulkDeleteMutation.isPending}
      />
    </div>
  )
}
