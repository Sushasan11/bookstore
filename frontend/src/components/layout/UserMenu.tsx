'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useSession, signOut } from 'next-auth/react'
import { Button } from '@/components/ui/button'

export function UserMenu() {
  const { data: session, status } = useSession()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Return null before hydration to prevent SSR/CSR mismatch
  if (!mounted) return null

  if (status === 'loading') {
    return (
      <div className="h-8 w-20 animate-pulse rounded-md bg-muted" aria-hidden="true" />
    )
  }

  if (status === 'unauthenticated') {
    return (
      <Link href="/login">
        <Button variant="ghost" size="sm">
          Sign In
        </Button>
      </Link>
    )
  }

  // Authenticated state
  const email = session?.user?.email ?? ''
  const truncatedEmail = email.length > 20 ? `${email.slice(0, 17)}...` : email

  return (
    <div className="flex items-center gap-2">
      <span
        className="hidden text-sm text-muted-foreground sm:block"
        title={email}
      >
        {truncatedEmail}
      </span>
      {session?.user?.role === 'admin' && (
        <Link href="/admin">
          <Button variant="ghost" size="sm">
            Admin
          </Button>
        </Link>
      )}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => signOut({ callbackUrl: '/' })}
      >
        Sign Out
      </Button>
    </div>
  )
}
