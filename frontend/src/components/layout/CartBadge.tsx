'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { fetchCart, CART_KEY } from '@/lib/cart'

export function CartBadge() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const { data: cart } = useQuery({
    queryKey: CART_KEY,
    queryFn: () => fetchCart(accessToken),
    enabled: !!accessToken && mounted,
    staleTime: 30_000,
  })

  if (!mounted || !cart || cart.total_items === 0) return null

  return (
    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
      {cart.total_items > 99 ? '99+' : cart.total_items}
    </span>
  )
}
