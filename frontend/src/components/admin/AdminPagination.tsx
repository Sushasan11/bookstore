import { Button } from '@/components/ui/button'

interface AdminPaginationProps {
  page: number
  total: number
  size: number
  onPageChange: (page: number) => void
}

export function AdminPagination({
  page,
  total,
  size,
  onPageChange,
}: AdminPaginationProps) {
  const totalPages = Math.ceil(total / size)
  const from = Math.min((page - 1) * size + 1, total)
  const to = Math.min(page * size, total)

  return (
    <div className="flex items-center justify-between text-sm text-muted-foreground">
      <span>
        Showing {from}&ndash;{to} of {total}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
