import { auth } from "@/auth"
import { NextResponse } from "next/server"

// Routes that require authentication
const protectedPrefixes = ["/account", "/orders", "/checkout", "/wishlist", "/prebook", "/cart"]

// Admin routes — require admin role (Layer 1: UX redirect, not the security boundary)
const adminPrefixes = ["/admin"]

// Auth-only pages (redirect to / when already signed in)
const authOnlyPaths = ["/login", "/register"]

export const proxy = auth((req) => {
  const isLoggedIn = !!req.auth
  const { pathname } = req.nextUrl

  const isProtected = protectedPrefixes.some((p) => pathname.startsWith(p))

  if (isProtected && !isLoggedIn) {
    const url = new URL("/login", req.nextUrl.origin)
    url.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(url)
  }

  // Admin routes require admin role — silent redirect to / (don't reveal route exists)
  const isAdminRoute = adminPrefixes.some((p) => pathname.startsWith(p))
  if (isAdminRoute && !isLoggedIn) {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))
  }
  if (isAdminRoute && req.auth?.user?.role !== "admin") {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))
  }

  // Redirect authenticated users away from auth pages (better UX)
  const isAuthPage = authOnlyPaths.some((p) => pathname === p)
  if (isAuthPage && isLoggedIn) {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))
  }

  return NextResponse.next()
})

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}
