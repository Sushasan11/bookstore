import { Minus, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface QuantityStepperProps {
  quantity: number
  onUpdate: (newQuantity: number) => void
  disabled?: boolean
}

export function QuantityStepper({ quantity, onUpdate, disabled }: QuantityStepperProps) {
  return (
    <div className="flex items-center gap-1">
      <Button
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={disabled || quantity <= 1}
        onClick={() => onUpdate(Math.max(1, quantity - 1))}
        aria-label="Decrease quantity"
      >
        <Minus className="h-3 w-3" />
      </Button>
      <span className="w-8 text-center text-sm font-medium">{quantity}</span>
      <Button
        variant="outline"
        size="icon"
        className="h-8 w-8"
        disabled={disabled}
        onClick={() => onUpdate(quantity + 1)}
        aria-label="Increase quantity"
      >
        <Plus className="h-3 w-3" />
      </Button>
    </div>
  )
}
