import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { fetchWishlist } from '@/lib/wishlist'
import { WishlistList } from './_components/WishlistList'
import type { components } from '@/types/api.generated'

type WishlistResponse = components['schemas']['WishlistResponse']

export const metadata = {
  title: 'My Wishlist',
}

export default async function WishlistPage() {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  let data: WishlistResponse
  try {
    data = await fetchWishlist(session.accessToken)
  } catch {
    data = { items: [] }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">My Wishlist</h1>
      <WishlistList items={data.items} />
    </div>
  )
}
