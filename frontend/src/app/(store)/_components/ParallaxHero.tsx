'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import { ArrowRight, BookOpen, Library, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ParallaxHero() {
  const heroRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleScroll = () => {
      if (!heroRef.current) return
      const scrollY = window.scrollY
      const inner = heroRef.current.querySelector(
        '[data-parallax-content]'
      ) as HTMLElement | null
      if (inner) {
        inner.style.transform = `translateY(${scrollY * 0.4}px)`
        inner.style.opacity = `${Math.max(0, 1 - scrollY / 600)}`
      }
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div ref={heroRef} className="relative overflow-hidden">
      {/* Background layer with gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-muted/80 to-primary/10" />

      {/* Floating decorative icons */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <BookOpen className="absolute top-12 left-[10%] h-16 w-16 text-primary/[0.07] rotate-[-15deg]" />
        <Library className="absolute top-20 right-[15%] h-20 w-20 text-primary/[0.06] rotate-[10deg]" />
        <Sparkles className="absolute bottom-16 left-[20%] h-12 w-12 text-primary/[0.08] rotate-[20deg]" />
        <BookOpen className="absolute bottom-24 right-[10%] h-14 w-14 text-primary/[0.05] rotate-[-10deg]" />
      </div>

      {/* Content */}
      <div data-parallax-content className="relative z-10 px-4 py-24 md:py-36">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border bg-background/60 backdrop-blur-sm px-4 py-1.5 text-sm text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" />
            Discover thousands of titles
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Your Next Great Read
            <span className="block text-primary">Awaits</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg text-muted-foreground">
            Browse our curated collection of books across every genre. From
            bestsellers to hidden gems, find your perfect read.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Button asChild size="lg">
              <Link href="/catalog">
                Browse All Books
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/catalog?sort=avg_rating&sort_dir=desc">
                Top Rated
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Bottom wave divider */}
      <div className="absolute bottom-0 left-0 right-0">
        <svg
          viewBox="0 0 1440 80"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-auto block"
          preserveAspectRatio="none"
        >
          <path
            d="M0 40C240 80 480 0 720 40C960 80 1200 0 1440 40V80H0V40Z"
            className="fill-background"
          />
        </svg>
      </div>
    </div>
  )
}
