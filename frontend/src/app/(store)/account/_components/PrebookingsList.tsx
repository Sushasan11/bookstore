'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { X } from 'lucide-react'
import { cancelPrebook, PREBOOK_KEY } from '@/lib/prebook'
import { ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { components } from '@/types/api.generated'

type PreBookResponse = components['schemas']['PreBookResponse']

interface PrebookingsListProps {
  prebooks: PreBookResponse[]
}

export function PrebookingsList({ prebooks }: PrebookingsListProps) {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

  // Local state for optimistic removal
  const [localPrebooks, setLocalPrebooks] = useState<PreBookResponse[]>(prebooks)

  const cancelMutation = useMutation({
    mutationFn: ({ prebookId }: { prebookId: number }) =>
      cancelPrebook(accessToken, prebookId),
    onMutate: async ({ prebookId }) => {
      // Optimistically remove item from local list
      const previous = localPrebooks
      setLocalPrebooks((prev) => prev.filter((p) => p.id !== prebookId))
      return { previous }
    },
    onError: (err, _vars, context) => {
      // Restore previous list on error
      if (context?.previous) {
        setLocalPrebooks(context.previous)
      }
      if (err instanceof ApiError && err.status === 409) {
        const detail = typeof err.detail === 'string' ? err.detail : ''
        if (detail.includes('ALREADY_CANCELLED')) {
          toast.error('This pre-booking was already cancelled')
        } else {
          toast.error('Failed to cancel pre-booking')
        }
      } else {
        toast.error('Failed to cancel pre-booking')
      }
    },
    onSuccess: () => {
      toast.success('Pre-booking cancelled')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: PREBOOK_KEY })
    },
  })

  const handleCancel = (prebookId: number) => {
    cancelMutation.mutate({ prebookId })
  }

  if (localPrebooks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">No active pre-bookings</p>
    )
  }

  return (
    <ul className="divide-y rounded-lg border">
      {localPrebooks.map((prebook) => (
        <li
          key={prebook.id}
          className="flex items-center justify-between px-4 py-3 last:border-b-0"
        >
          <div className="flex-1 min-w-0 mr-4">
            <p className="font-medium truncate">{prebook.book_title}</p>
            <p className="text-sm text-muted-foreground truncate">{prebook.book_author}</p>
            <div className="flex items-center gap-2 mt-1">
              {prebook.status === 'waiting' && (
                <Badge variant="outline" className="text-yellow-600 border-yellow-600 text-xs">
                  Waiting
                </Badge>
              )}
              {prebook.status === 'notified' && (
                <Badge variant="outline" className="text-blue-600 border-blue-600 text-xs">
                  Notified
                </Badge>
              )}
              <span className="text-xs text-muted-foreground">
                {new Date(prebook.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          {/* Cancel button — only for waiting status */}
          {prebook.status === 'waiting' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleCancel(prebook.id)}
              disabled={cancelMutation.isPending}
              aria-label={`Cancel pre-booking for ${prebook.book_title}`}
            >
              <X className="h-4 w-4 mr-1" />
              Cancel
            </Button>
          )}
        </li>
      ))}
    </ul>
  )
}
