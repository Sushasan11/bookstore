'use client'

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ThemeProvider } from 'next-themes'
import { SessionProvider, useSession, signOut } from 'next-auth/react'
import { useState, useEffect } from 'react'
import { Toaster } from '@/components/ui/sonner'
import { ApiError } from '@/lib/api'

/**
 * AuthGuard watches session.error for "RefreshTokenError" and signs the user out.
 *
 * This handles the case where the jwt callback sets token.error = "RefreshTokenError"
 * after a failed token refresh. signOut() cannot be called server-side from the jwt
 * callback — it must be called here, client-side, after the error is surfaced through
 * the session callback. See RESEARCH.md Pitfall 4.
 */
function AuthGuard({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession()

  useEffect(() => {
    if (session?.error === 'RefreshTokenError') {
      signOut({ callbackUrl: '/login' })
    }
  }, [session?.error])

  return <>{children}</>
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (error) => {
            // AUTH-08: deactivated user's API call returns 403 — sign out automatically
            if (error instanceof ApiError && error.status === 403) {
              signOut({ callbackUrl: '/login' })
            }
          },
        }),
        mutationCache: new MutationCache({
          onError: (error) => {
            // AUTH-08: deactivated user's mutation returns 403 — sign out automatically
            if (error instanceof ApiError && error.status === 403) {
              signOut({ callbackUrl: '/login' })
            }
          },
        }),
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
      })
  )

  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthGuard>
            {children}
          </AuthGuard>
          <Toaster richColors position="bottom-right" />
        </ThemeProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </SessionProvider>
  )
}
