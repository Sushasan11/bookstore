'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDebounce } from 'use-debounce'
import { adminKeys, fetchLowStock, updateBookStock } from '@/lib/admin'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { toast } from 'sonner'

const PRESETS = [5, 10, 20] as const

function StockBadge({ stock, threshold }: { stock: number; threshold: number }) {
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

export default function AdminInventoryPage() {
  const [thresholdInput, setThresholdInput] = useState<number>(10)
  const [debouncedThreshold] = useDebounce(thresholdInput, 500)
  const [selectedBook, setSelectedBook] = useState<{
    book_id: number
    title: string
    current_stock: number
  } | null>(null)
  const [newQuantity, setNewQuantity] = useState<number>(0)
  const modalOpen = selectedBook !== null

  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

  const lowStockQuery = useQuery({
    queryKey: adminKeys.inventory.lowStock(debouncedThreshold),
    queryFn: () => fetchLowStock(accessToken, debouncedThreshold),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const stockMutation = useMutation({
    mutationFn: ({ bookId, quantity }: { bookId: number; quantity: number }) =>
      updateBookStock(accessToken, bookId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.inventory.all })
      toast.success('Stock updated successfully')
      setSelectedBook(null)
    },
    onError: () => {
      toast.error('Failed to update stock')
    },
  })

  return (
    <div className="space-y-6">
      {/* Header with threshold controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Inventory Alerts</h1>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-lg border p-1">
            {PRESETS.map((t) => (
              <Button
                key={t}
                variant={thresholdInput === t ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setThresholdInput(t)}
                className="h-8 text-sm"
              >
                &lt; {t}
              </Button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Custom:</span>
            <Input
              type="number"
              min={0}
              max={999}
              value={thresholdInput}
              onChange={(e) => setThresholdInput(Number(e.target.value))}
              className="h-8 w-20 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Summary card */}
      <Card className="border-amber-500/50 bg-amber-500/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Low Stock Items (threshold: {debouncedThreshold})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {lowStockQuery.isLoading ? (
            <Skeleton className="h-8 w-12" />
          ) : lowStockQuery.isError ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Failed to load</p>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => lowStockQuery.refetch()}
              >
                Retry
              </Button>
            </div>
          ) : (
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {lowStockQuery.data?.total_low_stock ?? 0}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Low stock items table */}
      <div className="rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left text-muted-foreground font-medium py-2 px-4">
                Title
              </th>
              <th className="text-left text-muted-foreground font-medium py-2 px-4">
                Author
              </th>
              <th className="text-right text-muted-foreground font-medium py-2 px-4">
                Current Stock
              </th>
              <th className="text-right text-muted-foreground font-medium py-2 px-4">
                Threshold
              </th>
              <th className="text-right text-muted-foreground font-medium py-2 px-4 w-32">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {lowStockQuery.isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-t">
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-48" />
                  </td>
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-32" />
                  </td>
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-12 ml-auto" />
                  </td>
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-12 ml-auto" />
                  </td>
                  <td className="py-3 px-4">
                    <Skeleton className="h-4 w-20 ml-auto" />
                  </td>
                </tr>
              ))
            ) : lowStockQuery.isError ? (
              <tr>
                <td colSpan={5} className="py-6 px-4 text-center text-muted-foreground">
                  Failed to load inventory data.{' '}
                  <button
                    className="underline hover:no-underline"
                    onClick={() => lowStockQuery.refetch()}
                  >
                    Retry
                  </button>
                </td>
              </tr>
            ) : !lowStockQuery.data?.items?.length ? (
              <tr>
                <td colSpan={5} className="py-6 px-4 text-center text-muted-foreground">
                  No low stock items
                </td>
              </tr>
            ) : (
              lowStockQuery.data.items.map((item) => (
                <tr key={item.book_id} className="border-t hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4 font-medium">{item.title}</td>
                  <td className="py-3 px-4 text-muted-foreground">{item.author}</td>
                  <td className="py-3 px-4 text-right">
                    <StockBadge stock={item.current_stock} threshold={debouncedThreshold} />
                  </td>
                  <td className="py-3 px-4 text-right text-muted-foreground">
                    {item.threshold}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedBook({
                          book_id: item.book_id,
                          title: item.title,
                          current_stock: item.current_stock,
                        })
                        setNewQuantity(item.current_stock)
                      }}
                    >
                      Update Stock
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Stock Update Modal */}
      <Dialog
        open={modalOpen}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedBook(null)
            setNewQuantity(0)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Stock</DialogTitle>
            <DialogDescription>
              Set a new stock quantity for {selectedBook?.title}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="text-sm text-muted-foreground">
              Current stock:{' '}
              <span className="font-medium text-foreground">{selectedBook?.current_stock}</span>
            </div>
            <div className="space-y-2">
              <label htmlFor="stock-input" className="text-sm font-medium">
                New quantity
              </label>
              <Input
                id="stock-input"
                type="number"
                min={0}
                value={newQuantity}
                onChange={(e) => setNewQuantity(Number(e.target.value))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedBook(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (selectedBook) {
                  stockMutation.mutate({ bookId: selectedBook.book_id, quantity: newQuantity })
                }
              }}
              disabled={stockMutation.isPending}
            >
              {stockMutation.isPending ? 'Updating...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
