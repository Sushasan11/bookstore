import type { Metadata } from 'next'
import { Suspense } from 'react'
import Link from 'next/link'
import { LoginForm } from '@/components/auth/LoginForm'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card'

export const metadata: Metadata = {
  title: 'Sign In',
}

export default function LoginPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Welcome back</CardTitle>
        <CardDescription>Sign in to your account</CardDescription>
      </CardHeader>

      {/* Suspense required: LoginForm uses useSearchParams() for callbackUrl */}
      <Suspense fallback={<CardContent><div className="h-40 animate-pulse rounded-md bg-muted" /></CardContent>}>
        <LoginForm />
      </Suspense>

      <div className="px-6">
        <div className="relative my-2">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">or</span>
          </div>
        </div>

        <GoogleSignInButton />
      </div>

      <div className="px-6 pb-2 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{' '}
        <Link href="/register" className="text-foreground font-medium hover:underline">
          Sign up
        </Link>
      </div>
    </Card>
  )
}
