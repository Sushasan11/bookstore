'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

interface HealthResponse {
  status: string
  version: string
}

export default function HomePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<HealthResponse>('/health'),
  })

  return (
    <div className="container mx-auto px-4 py-16">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Welcome to Bookstore
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Discover and purchase books from our curated catalog.
        </p>

        {/* Health check status — proves full stack integration */}
        <div className="mt-8 rounded-lg border p-6">
          <h2 className="text-sm font-medium text-muted-foreground mb-2">
            Backend Status
          </h2>
          {isLoading && (
            <p className="text-muted-foreground">Checking backend...</p>
          )}
          {error && (
            <p className="text-destructive">
              Backend unreachable: {error.message}
            </p>
          )}
          {data && (
            <p className="text-green-600 dark:text-green-400">
              Connected &#8212; v{data.version}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
