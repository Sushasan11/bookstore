import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

interface CartSummaryProps {
  totalItems: number
  totalPrice: string
  onCheckout: () => void
  isCheckingOut: boolean
}

export function CartSummary({ totalItems, totalPrice, onCheckout, isCheckingOut }: CartSummaryProps) {
  return (
    <>
      {/* Full summary card — sticky sidebar on desktop, normal flow on mobile */}
      <div className="lg:sticky lg:top-24 rounded-lg border p-6 space-y-4 h-fit">
        <h2 className="font-semibold text-lg">Order Summary</h2>
        <Separator />
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Items ({totalItems})</span>
          <span>${totalPrice}</span>
        </div>
        <Separator />
        <div className="flex justify-between font-semibold">
          <span>Total</span>
          <span>${totalPrice}</span>
        </div>
        {/* Desktop checkout button (hidden on mobile since the fixed bar has one) */}
        <Button
          className="w-full hidden lg:flex"
          size="lg"
          onClick={onCheckout}
          disabled={isCheckingOut}
        >
          {isCheckingOut ? 'Placing Order...' : 'Checkout'}
        </Button>
      </div>

      {/* Mobile fixed bottom bar — visible only below lg breakpoint */}
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t bg-background p-4 flex items-center justify-between lg:hidden">
        <div className="font-semibold">
          Total: <span>${totalPrice}</span>
        </div>
        <Button
          size="lg"
          onClick={onCheckout}
          disabled={isCheckingOut}
        >
          {isCheckingOut ? 'Placing Order...' : 'Checkout'}
        </Button>
      </div>
    </>
  )
}
