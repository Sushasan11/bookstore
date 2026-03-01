'use client'

import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch, ApiError } from '@/lib/api'
import type { components } from '@/types/api.generated'

type CartResponse = components['schemas']['CartResponse']
type CartItemResponse = components['schemas']['CartItemResponse']
type OrderResponse = components['schemas']['OrderResponse']

export type { CartResponse, CartItemResponse, OrderResponse }

// Cache key for cart queries — all cart-related hooks share this key
export const CART_KEY = ['cart'] as const

// ---------------------------------------------------------------------------
// Cart API functions — all require an accessToken from NextAuth session
// ---------------------------------------------------------------------------

export async function fetchCart(accessToken: string): Promise<CartResponse> {
  return apiFetch<CartResponse>('/cart', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function addCartItem(
  accessToken: string,
  bookId: number,
  quantity = 1
): Promise<CartItemResponse> {
  return apiFetch<CartItemResponse>('/cart/items', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ book_id: bookId, quantity }),
  })
}

export async function updateCartItem(
  accessToken: string,
  itemId: number,
  quantity: number
): Promise<CartItemResponse> {
  return apiFetch<CartItemResponse>(`/cart/items/${itemId}`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ quantity }),
  })
}

export async function removeCartItem(
  accessToken: string,
  itemId: number
): Promise<void> {
  return apiFetch<void>(`/cart/items/${itemId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function checkout(accessToken: string): Promise<OrderResponse> {
  return apiFetch<OrderResponse>('/orders/checkout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ force_payment_failure: false }),
  })
}

export async function fetchOrder(
  accessToken: string,
  orderId: number
): Promise<OrderResponse> {
  return apiFetch<OrderResponse>(`/orders/${orderId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

// ---------------------------------------------------------------------------
// Shared helpers for optimistic total recomputation
// ---------------------------------------------------------------------------

function recomputeTotals(items: CartItemResponse[]): Pick<CartResponse, 'total_items' | 'total_price'> {
  const total_items = items.reduce((sum, item) => sum + item.quantity, 0)
  const total_price = items
    .reduce((sum, item) => sum + parseFloat(item.book.price) * item.quantity, 0)
    .toFixed(2)
  return { total_items, total_price }
}

// ---------------------------------------------------------------------------
// useCart hook — shared cart state + mutations with optimistic updates
// ---------------------------------------------------------------------------

export function useCart() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()
  const router = useRouter()

  const cartQuery = useQuery({
    queryKey: CART_KEY,
    queryFn: () => fetchCart(accessToken),
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  // ---- addItem ----
  const addItem = useMutation({
    mutationFn: ({ bookId, quantity = 1 }: { bookId: number; quantity?: number }) =>
      addCartItem(accessToken, bookId, quantity),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: CART_KEY })
      const previousCart = queryClient.getQueryData<CartResponse>(CART_KEY)
      if (previousCart) {
        queryClient.setQueryData<CartResponse>(CART_KEY, {
          ...previousCart,
          total_items: previousCart.total_items + 1,
        } as CartResponse)
      }
      return { previousCart }
    },
    onError: (err, _vars, context) => {
      if (context?.previousCart) {
        queryClient.setQueryData(CART_KEY, context.previousCart)
      }
      if (err instanceof ApiError && err.status === 409) {
        toast.error('Already in cart', {
          action: {
            label: 'View Cart',
            onClick: () => router.push('/cart'),
          },
        })
      } else {
        toast.error('Failed to add item to cart')
      }
    },
    onSuccess: () => {
      toast.success('Added to cart')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: CART_KEY })
    },
  })

  // ---- updateItem ----
  const updateItem = useMutation({
    mutationFn: ({ itemId, quantity }: { itemId: number; quantity: number }) =>
      updateCartItem(accessToken, itemId, quantity),
    onMutate: async ({ itemId, quantity }) => {
      await queryClient.cancelQueries({ queryKey: CART_KEY })
      const previousCart = queryClient.getQueryData<CartResponse>(CART_KEY)
      if (previousCart) {
        const updatedItems = previousCart.items.map((item) =>
          item.id === itemId ? { ...item, quantity } : item
        )
        const { total_items, total_price } = recomputeTotals(updatedItems)
        queryClient.setQueryData<CartResponse>(CART_KEY, {
          ...previousCart,
          items: updatedItems,
          total_items,
          total_price,
        } as CartResponse)
      }
      return { previousCart }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousCart) {
        queryClient.setQueryData(CART_KEY, context.previousCart)
      }
      toast.error('Failed to update item quantity')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: CART_KEY })
    },
  })

  // ---- removeItem ----
  const removeItem = useMutation({
    mutationFn: ({ itemId }: { itemId: number }) =>
      removeCartItem(accessToken, itemId),
    onMutate: async ({ itemId }) => {
      await queryClient.cancelQueries({ queryKey: CART_KEY })
      const previousCart = queryClient.getQueryData<CartResponse>(CART_KEY)
      if (previousCart) {
        const updatedItems = previousCart.items.filter((item) => item.id !== itemId)
        const { total_items, total_price } = recomputeTotals(updatedItems)
        queryClient.setQueryData<CartResponse>(CART_KEY, {
          ...previousCart,
          items: updatedItems,
          total_items,
          total_price,
        } as CartResponse)
      }
      return { previousCart }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousCart) {
        queryClient.setQueryData(CART_KEY, context.previousCart)
      }
      toast.error('Failed to remove item from cart')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: CART_KEY })
    },
  })

  // ---- checkoutMutation ----
  const checkoutMutation = useMutation({
    mutationFn: () => checkout(accessToken),
    onSuccess: (order) => {
      queryClient.setQueryData<CartResponse>(CART_KEY, {
        items: [],
        total_items: 0,
        total_price: '0.00',
      } as CartResponse)
      // Seed order data into cache so the order page doesn't need to re-fetch
      queryClient.setQueryData(['order', String(order.id)], order)
      router.push(`/orders/${order.id}?confirmed=true`)
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        if (err.status === 409 && (err.data as Record<string, unknown>)?.code === 'ORDER_ITEMS_UNAVAILABLE') {
          toast.error('Some items in your cart are no longer available. Please review your cart.')
        } else if (err.status === 409) {
          toast.error('Some items are out of stock. Please review your cart.')
        } else if (err.status === 402) {
          toast.error('Payment failed. Please try again.')
        } else if (err.status === 422) {
          toast.error('Your cart is empty. Add some books before checking out.')
        } else {
          toast.error('Checkout failed. Please try again.')
        }
      } else {
        toast.error('Checkout failed. Please try again.')
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: CART_KEY })
    },
  })

  return {
    cartQuery,
    addItem,
    updateItem,
    removeItem,
    checkoutMutation,
  }
}
