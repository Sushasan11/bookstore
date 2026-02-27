'use client'

import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch, ApiError } from '@/lib/api'
import type { components } from '@/types/api.generated'

type PreBookResponse = components['schemas']['PreBookResponse']
type PreBookListResponse = components['schemas']['PreBookListResponse']

export type { PreBookResponse, PreBookListResponse }

// Cache key for pre-booking queries
export const PREBOOK_KEY = ['prebooks'] as const

// ---------------------------------------------------------------------------
// Pre-booking API functions — all require an accessToken from NextAuth session
// ---------------------------------------------------------------------------

export async function createPrebook(
  accessToken: string,
  bookId: number
): Promise<PreBookResponse> {
  return apiFetch<PreBookResponse>('/prebooks', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ book_id: bookId }),
  })
}

export async function cancelPrebook(
  accessToken: string,
  prebookId: number
): Promise<void> {
  return apiFetch<void>(`/prebooks/${prebookId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function fetchPrebooks(
  accessToken: string
): Promise<PreBookListResponse> {
  return apiFetch<PreBookListResponse>('/prebooks', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

// ---------------------------------------------------------------------------
// usePrebook hook — pre-book mutation with 409 error handling
// ---------------------------------------------------------------------------

export function usePrebook() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()
  const router = useRouter()

  const prebooksQuery = useQuery({
    queryKey: PREBOOK_KEY,
    queryFn: () => fetchPrebooks(accessToken),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const prebookMutation = useMutation({
    mutationFn: ({ bookId }: { bookId: number }) => createPrebook(accessToken, bookId),
    onSuccess: () => {
      toast.success(
        'Pre-booking confirmed! We will notify you when this book is back in stock.'
      )
      queryClient.invalidateQueries({ queryKey: PREBOOK_KEY })
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        const detail = typeof err.detail === 'string' ? err.detail : ''
        if (
          detail.includes('PREBOOK_DUPLICATE') ||
          detail.toLowerCase().includes('already')
        ) {
          toast.error('You already have an active pre-booking for this book')
        } else if (detail.includes('IN_STOCK')) {
          toast.error('This book is now in stock — add it to your cart instead!')
        } else {
          toast.error('Failed to create pre-booking')
        }
      } else {
        toast.error('Failed to create pre-booking')
      }
    },
  })

  const handlePrebook = (bookId: number) => {
    if (!session?.accessToken) {
      toast.error('Please sign in to pre-book')
      router.push('/login')
      return
    }
    prebookMutation.mutate({ bookId })
  }

  return {
    prebooksQuery,
    handlePrebook,
    isPending: prebookMutation.isPending,
  }
}
