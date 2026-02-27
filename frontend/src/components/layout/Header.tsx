import Link from 'next/link'
import { ShoppingCart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MobileNav } from '@/components/layout/MobileNav'
import { ThemeToggle } from '@/components/layout/ThemeToggle'

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        {/* Left: Mobile hamburger + Logo */}
        <div className="flex items-center gap-4">
          <MobileNav />
          <Link
            href="/"
            className="font-bold text-xl tracking-tight hover:opacity-80 transition-opacity"
          >
            Bookstore
          </Link>
        </div>

        {/* Center: Desktop nav links (hidden on mobile) */}
        <nav className="hidden md:flex items-center gap-6">
          <Link
            href="/books"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Books
          </Link>
        </nav>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <Link href="/cart">
            <Button variant="ghost" size="icon" aria-label="Shopping cart">
              <ShoppingCart className="h-5 w-5" />
            </Button>
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
