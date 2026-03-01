import { Badge } from '@/components/ui/badge'

export function StockBadge({ stock, threshold }: { stock: number; threshold: number }) {
  if (stock === 0) {
    return (
      <Badge className="bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400">
        Out of Stock
      </Badge>
    )
  }
  if (stock <= threshold) {
    return (
      <Badge className="bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400">
        Low Stock ({stock})
      </Badge>
    )
  }
  return <span className="font-medium">{stock}</span>
}
