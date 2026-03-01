'use client'

import { use, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { fetchOrder } from '@/lib/cart'
import { OrderDetail } from './_components/OrderDetail'
import { Skeleton } from '@/components/ui/skeleton'

function OrderSkeleton() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <Skeleton className="h-24 w-full rounded-xl" />
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-64" />
      <Skeleton className="h-px w-full" />
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="flex gap-4 py-3">
            <Skeleton className="h-20 w-14 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function OrderDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<{ confirmed?: string }>
}) {
  const { id } = use(params)
  const { confirmed } = use(searchParams)
  const { data: session, status } = useSession()
  const router = useRouter()

  const orderQuery = useQuery({
    queryKey: ['order', id],
    queryFn: () => fetchOrder(session!.accessToken, Number(id)),
    enabled: !!session?.accessToken,
    retry: 1,
  })

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/login')
    }
  }, [status, router])

  if (status === 'loading' || orderQuery.isLoading) {
    return <OrderSkeleton />
  }

  if (orderQuery.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center space-y-4">
        <p className="text-muted-foreground">Unable to load order details.</p>
        <button onClick={() => orderQuery.refetch()} className="text-sm underline">
          Try again
        </button>
      </div>
    )
  }

  if (!orderQuery.data) return <OrderSkeleton />

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <OrderDetail order={orderQuery.data} isConfirmed={confirmed === 'true'} />
    </div>
  )
}
