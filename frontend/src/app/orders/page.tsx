import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { fetchOrders } from '@/lib/orders'
import { OrderHistoryList } from './_components/OrderHistoryList'
import type { components } from '@/types/api.generated'

type OrderResponse = components['schemas']['OrderResponse']

export const metadata = {
  title: 'Order History',
}

export default async function OrdersPage() {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  let orders: OrderResponse[]
  try {
    orders = await fetchOrders(session.accessToken)
  } catch {
    orders = []
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Order History</h1>
      <OrderHistoryList orders={orders} />
    </div>
  )
}
