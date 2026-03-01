import type { Metadata } from 'next'
import { fetchBooks } from '@/lib/catalog'
import { HeroSection } from './_components/HeroSection'
import { FeaturedBooks } from './_components/FeaturedBooks'

export const metadata: Metadata = {
  title: 'BookStore — Discover Your Next Great Read',
  description:
    'Browse our curated collection of books across every genre. From bestsellers to hidden gems.',
}

export default async function HomePage() {
  const [topRated, newest] = await Promise.all([
    fetchBooks({ sort: 'avg_rating', sort_dir: 'desc', size: 4 }),
    fetchBooks({ sort: 'created_at', sort_dir: 'desc', size: 4 }),
  ])

  return (
    <>
      <HeroSection />

      <div className="mx-auto max-w-7xl px-4 py-12 space-y-16">
        <FeaturedBooks
          title="Top Rated"
          books={topRated.items}
          viewAllHref="/catalog?sort=avg_rating&sort_dir=desc"
          viewAllLabel="View all top rated"
        />

        <FeaturedBooks
          title="New Arrivals"
          books={newest.items}
          viewAllHref="/catalog?sort=created_at&sort_dir=desc"
          viewAllLabel="View all new arrivals"
        />
      </div>
    </>
  )
}
