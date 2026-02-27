import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type OrderResponse = components['schemas']['OrderResponse']

export async function fetchOrders(accessToken: string): Promise<OrderResponse[]> {
  return apiFetch<OrderResponse[]>('/orders', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
