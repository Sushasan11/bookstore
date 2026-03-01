'use client'

import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { adminKeys, updateBookStock } from '@/lib/admin'

interface StockUpdateModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  book: { book_id: number; title: string; current_stock: number } | null
  accessToken: string
  onSuccess?: () => void
}

export function StockUpdateModal({
  open,
  onOpenChange,
  book,
  accessToken,
  onSuccess,
}: StockUpdateModalProps) {
  const [newQuantity, setNewQuantity] = useState<number>(0)
  const queryClient = useQueryClient()

  useEffect(() => {
    setNewQuantity(book?.current_stock ?? 0)
  }, [book])

  const stockMutation = useMutation({
    mutationFn: ({ bookId, quantity }: { bookId: number; quantity: number }) =>
      updateBookStock(accessToken, bookId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.inventory.all })
      queryClient.invalidateQueries({ queryKey: adminKeys.catalog.all })
      queryClient.invalidateQueries({ queryKey: ['books'] })

      if (book?.current_stock === 0 && newQuantity > 0) {
        toast.success('Stock updated — pre-booking notifications sent')
      } else {
        toast.success('Stock updated successfully')
      }

      onSuccess?.()
      onOpenChange(false)
    },
    onError: () => {
      toast.error('Failed to update stock')
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Update Stock</DialogTitle>
          <DialogDescription>
            Set a new stock quantity for {book?.title}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="text-sm text-muted-foreground">
            Current stock:{' '}
            <span className="font-medium text-foreground">{book?.current_stock}</span>
          </div>
          <div className="space-y-2">
            <Label htmlFor="stock-input">New quantity</Label>
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
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={stockMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (book) {
                stockMutation.mutate({ bookId: book.book_id, quantity: newQuantity })
              }
            }}
            disabled={stockMutation.isPending}
          >
            {stockMutation.isPending ? 'Updating...' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
