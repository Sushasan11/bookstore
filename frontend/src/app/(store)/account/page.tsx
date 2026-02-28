import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { Card } from '@/components/ui/card'
import { Package, Heart } from 'lucide-react'
import { fetchPrebooks } from '@/lib/prebook'
import { PrebookingsList } from './_components/PrebookingsList'
import type { components } from '@/types/api.generated'

type PreBookResponse = components['schemas']['PreBookResponse']

export const metadata = {
  title: 'My Account',
}

export default async function AccountPage() {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  const email = session.user?.email ?? ''

  let prebooks: PreBookResponse[] = []
  try {
    const data = await fetchPrebooks(session.accessToken)
    prebooks = data.items.filter((p) => p.status !== 'cancelled')
  } catch {
    prebooks = []
  }

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
        <Link href="/wishlist">
          <Card className="p-6 hover:bg-accent transition-colors cursor-pointer">
            <Heart className="h-6 w-6 mb-3 text-muted-foreground" />
            <h2 className="font-semibold">Wishlist</h2>
            <p className="text-sm text-muted-foreground mt-1">Books you saved for later</p>
          </Card>
        </Link>
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4">Pre-bookings</h2>
        <PrebookingsList prebooks={prebooks} />
      </div>
    </div>
  )
}
