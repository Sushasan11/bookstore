import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function HeroSection() {
  return (
    <section className="border-b bg-muted/50 px-4 py-20 md:py-28">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
          Your Next Great Read Awaits
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
          Browse our curated collection of books across every genre. From
          bestsellers to hidden gems, find your perfect read.
        </p>
        <div className="mt-8">
          <Button asChild size="lg">
            <Link href="/catalog">
              Browse All Books
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
