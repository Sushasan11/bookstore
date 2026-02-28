import { CartPageContent } from './_components/CartPageContent'

export const metadata = {
  title: 'Shopping Cart',
}

export default function CartPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Shopping Cart</h1>
      <CartPageContent />
    </div>
  )
}
