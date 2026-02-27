'use client'

import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch, ApiError } from '@/lib/api'
import type { components } from '@/types/api.generated'

type WishlistResponse = components['schemas']['WishlistResponse']
type WishlistItemResponse = components['schemas']['WishlistItemResponse']

export type { WishlistResponse, WishlistItemResponse }

// Cache key for wishlist queries — all wishlist-related hooks share this key
export const WISHLIST_KEY = ['wishlist'] as const

// ---------------------------------------------------------------------------
// Wishlist API functions — all require an accessToken from NextAuth session
// ---------------------------------------------------------------------------

export async function fetchWishlist(accessToken: string): Promise<WishlistResponse> {
  return apiFetch<WishlistResponse>('/wishlist', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function addToWishlist(
  accessToken: string,
  bookId: number
): Promise<WishlistItemResponse> {
  return apiFetch<WishlistItemResponse>('/wishlist', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ book_id: bookId }),
  })
}

export async function removeFromWishlist(
  accessToken: string,
  bookId: number
): Promise<void> {
  return apiFetch<void>(`/wishlist/${bookId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

// ---------------------------------------------------------------------------
// useWishlist hook — shared wishlist state + toggle mutation with optimistic updates
// ---------------------------------------------------------------------------

export function useWishlist() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()
  const router = useRouter()

  const wishlistQuery = useQuery({
    queryKey: WISHLIST_KEY,
    queryFn: () => fetchWishlist(accessToken),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  // Derive a Set of book IDs for O(1) heart-state lookup
  const wishlistedIds = new Set<number>(
    wishlistQuery.data?.items.map((i) => i.book_id) ?? []
  )

  // ---- toggleWishlist ----
  const toggleWishlist = useMutation<
    WishlistItemResponse | void,
    Error,
    { bookId: number; isWishlisted: boolean },
    { previousWishlist: WishlistResponse | undefined; isWishlisted: boolean }
  >({
    mutationFn: ({ bookId, isWishlisted }) =>
      isWishlisted
        ? removeFromWishlist(accessToken, bookId)
        : addToWishlist(accessToken, bookId),
    onMutate: async ({ bookId, isWishlisted }) => {
      await queryClient.cancelQueries({ queryKey: WISHLIST_KEY })
      const previousWishlist = queryClient.getQueryData<WishlistResponse>(WISHLIST_KEY)
      if (previousWishlist) {
        if (isWishlisted) {
          // Optimistically remove the item
          queryClient.setQueryData<WishlistResponse>(WISHLIST_KEY, {
            ...previousWishlist,
            items: previousWishlist.items.filter((i) => i.book_id !== bookId),
          })
        } else {
          // Optimistically add a stub item
          const stubItem: WishlistItemResponse = {
            id: -1,
            book_id: bookId,
            added_at: new Date().toISOString(),
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            book: {} as any,
          }
          queryClient.setQueryData<WishlistResponse>(WISHLIST_KEY, {
            ...previousWishlist,
            items: [...previousWishlist.items, stubItem],
          })
        }
      }
      return { previousWishlist, isWishlisted }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousWishlist) {
        queryClient.setQueryData(WISHLIST_KEY, context.previousWishlist)
      }
      toast.error(
        context?.isWishlisted
          ? 'Failed to remove from wishlist'
          : 'Failed to add to wishlist'
      )
    },
    onSuccess: (_data, _vars, context) => {
      toast.success(
        context?.isWishlisted ? 'Removed from wishlist' : 'Added to wishlist'
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: WISHLIST_KEY })
    },
  })

  const handleToggle = (bookId: number) => {
    if (!session?.accessToken) {
      toast.error('Please sign in to save books to your wishlist')
      router.push('/login')
      return
    }
    toggleWishlist.mutate({ bookId, isWishlisted: wishlistedIds.has(bookId) })
  }

  return {
    wishlistQuery,
    wishlistedIds,
    handleToggle,
    isPending: toggleWishlist.isPending,
  }
}
