import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { fetchOrder } from '@/lib/cart'
import { OrderDetail } from './_components/OrderDetail'

export const metadata = {
  title: 'Order Details',
}

export default async function OrderDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<{ confirmed?: string }>
}) {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  const { id } = await params
  const { confirmed } = await searchParams

  let order
  try {
    order = await fetchOrder(session.accessToken, Number(id))
  } catch {
    // Order not found or forbidden — redirect to catalog
    redirect('/catalog')
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <OrderDetail order={order} isConfirmed={confirmed === 'true'} />
    </div>
  )
}
