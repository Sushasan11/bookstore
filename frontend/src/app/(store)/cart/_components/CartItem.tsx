import Image from 'next/image'
import Link from 'next/link'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { QuantityStepper } from './QuantityStepper'
import type { components } from '@/types/api.generated'

type CartItemResponse = components['schemas']['CartItemResponse']

interface CartItemProps {
  item: CartItemResponse
  onUpdateQuantity: (itemId: number, quantity: number) => void
  onRemove: (itemId: number) => void
}

export function CartItem({ item, onUpdateQuantity, onRemove }: CartItemProps) {
  const unitPrice = parseFloat(item.book.price)
  const lineTotal = (unitPrice * item.quantity).toFixed(2)

  return (
    <div className="flex gap-4 p-4 border rounded-lg">
      {/* Cover thumbnail — link to book detail */}
      <Link href={`/books/${item.book_id}`} className="shrink-0">
        {item.book.cover_image_url ? (
          <Image
            src={item.book.cover_image_url}
            alt={item.book.title}
            width={64}
            height={96}
            className="rounded object-cover"
          />
        ) : (
          <div className="w-16 h-24 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground">
            No cover
          </div>
        )}
      </Link>

      {/* Item details */}
      <div className="flex-1 min-w-0">
        <Link href={`/books/${item.book_id}`} className="hover:underline">
          <p className="font-medium text-sm line-clamp-1">{item.book.title}</p>
        </Link>
        <p className="text-xs text-muted-foreground">{item.book.author}</p>
        <p className="text-sm text-muted-foreground mt-1">${unitPrice.toFixed(2)} each</p>

        <div className="flex items-center justify-between mt-3">
          <QuantityStepper
            quantity={item.quantity}
            onUpdate={(qty) => onUpdateQuantity(item.id, qty)}
          />
          <div className="flex items-center gap-4">
            <p className="font-semibold text-sm">${lineTotal}</p>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
              onClick={() => onRemove(item.id)}
              aria-label={`Remove ${item.book.title} from cart`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
