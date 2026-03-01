'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { BookCard } from '@/app/(store)/catalog/_components/BookCard'
import type { BookResponse } from '@/lib/catalog'

interface FeaturedBooksProps {
  title: string
  books: BookResponse[]
  viewAllHref: string
  viewAllLabel?: string
}

export function FeaturedBooks({
  title,
  books,
  viewAllHref,
  viewAllLabel = 'View all',
}: FeaturedBooksProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const section = sectionRef.current
    if (!section) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate-in')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.1 }
    )

    observer.observe(section)
    return () => observer.disconnect()
  }, [])

  if (books.length === 0) return null

  return (
    <section
      ref={sectionRef}
      className="translate-y-8 opacity-0 transition-all duration-700 ease-out [&.animate-in]:translate-y-0 [&.animate-in]:opacity-100"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
        <Link
          href={viewAllHref}
          className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
        >
          {viewAllLabel}
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {books.map((book) => (
          <BookCard key={book.id} book={book} />
        ))}
      </div>
    </section>
  )
}
