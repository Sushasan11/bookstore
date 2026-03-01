import Link from 'next/link'

export function Footer() {
  return (
    <footer className="border-t border-border mt-auto">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            &copy; 2026 BookStore. All rights reserved.
          </p>
          <nav className="flex gap-4 text-sm text-muted-foreground">
            <Link
              href="/books"
              className="hover:text-foreground transition-colors"
            >
              Browse Books
            </Link>
            <Link
              href="/cart"
              className="hover:text-foreground transition-colors"
            >
              Cart
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  )
}
