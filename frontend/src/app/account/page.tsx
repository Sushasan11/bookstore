import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { Card } from '@/components/ui/card'
import { Package } from 'lucide-react'

export const metadata = {
  title: 'My Account',
}

export default async function AccountPage() {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  const email = session.user?.email ?? ''

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">My Account</h1>
      <p className="text-muted-foreground mb-8">{email}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/orders">
          <Card className="p-6 hover:bg-accent transition-colors cursor-pointer">
            <Package className="h-6 w-6 mb-3 text-muted-foreground" />
            <h2 className="font-semibold">Order History</h2>
            <p className="text-sm text-muted-foreground mt-1">View your past orders</p>
          </Card>
        </Link>
        {/* Wishlist and Pre-bookings — Phase 24 */}
      </div>
    </div>
  )
}
