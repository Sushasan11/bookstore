/**
 * NextAuth.js v5 configuration — auth session layer bridging Next.js to FastAPI.
 *
 * Providers:
 *   - Credentials: email + password login via POST /auth/login
 *   - Google: OAuth consent flow; jwt callback exchanges id_token for FastAPI tokens
 *
 * Session strategy: JWT (encrypted httpOnly cookie, FastAPI tokens stored inside)
 * Token refresh: transparent in jwt callback when accessTokenExpiry is passed
 */

import NextAuth, { DefaultSession } from "next-auth"
import Credentials from "next-auth/providers/credentials"
import Google from "next-auth/providers/google"
import type { JWT } from "next-auth/jwt"
import { decodeJwt } from "jose"
import { z } from "zod"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// ---------------------------------------------------------------------------
// TypeScript module augmentation — extend NextAuth types with FastAPI fields
// ---------------------------------------------------------------------------

declare module "next-auth" {
  interface Session {
    accessToken: string
    error?: string
    user: { id: string; role: string } & DefaultSession["user"]
  }

  interface User {
    accessToken: string
    refreshToken: string
    accessTokenExpiry: number
    role: string
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string
    refreshToken: string
    accessTokenExpiry: number
    userId: string
    role: string
    error?: string
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Concurrent-refresh guard: if a refresh is already in-flight, return the same promise. */
let refreshPromise: Promise<JWT> | null = null

/**
 * Refresh the FastAPI access token using the stored refresh_token.
 * Called from the jwt callback when accessTokenExpiry is in the past.
 * Sets token.error = "RefreshTokenError" on failure so client can signOut().
 */
async function refreshAccessToken(token: JWT): Promise<JWT> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async (): Promise<JWT> => {
    try {
      const res = await fetch(`${API}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: token.refreshToken }),
      })

      if (!res.ok) throw new Error(`Refresh failed: ${res.status}`)

      const data = await res.json()
      return {
        ...token,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        accessTokenExpiry: Date.now() + 14 * 60 * 1000, // 14 min (1 min buffer before 15-min TTL)
        error: undefined,
      }
    } catch {
      return { ...token, error: "RefreshTokenError" }
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

/**
 * Decode the FastAPI JWT payload to extract sub (userId) and role claims.
 * Uses jose decodeJwt (NOT verify — verification is server-side in FastAPI).
 * Returns safe defaults if decoding fails.
 */
function decodeJwtPayload(accessToken: string): { userId: string; role: string } {
  try {
    const payload = decodeJwt(accessToken)
    return {
      userId: String(payload.sub ?? ""),
      role: String(payload.role ?? "user"),
    }
  } catch {
    return { userId: "", role: "user" }
  }
}

// ---------------------------------------------------------------------------
// Credentials input schema
// ---------------------------------------------------------------------------

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

// ---------------------------------------------------------------------------
// NextAuth configuration
// ---------------------------------------------------------------------------

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { type: "email" },
        password: { type: "password" },
      },
      async authorize(credentials) {
        // Validate input with zod before hitting FastAPI
        const parsed = credentialsSchema.safeParse(credentials)
        if (!parsed.success) return null

        const res = await fetch(`${API}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed.data),
        })

        // IMPORTANT: return null on failure (NOT throw) — per NextAuth Credentials pitfall
        // null triggers CredentialsSignin error handled by the error page
        // Only throw for genuine server errors (5xx) — not handled here to keep UX clean
        if (!res.ok) return null

        const data = await res.json()
        const { userId, role } = decodeJwtPayload(data.access_token)

        return {
          id: userId,
          email: parsed.data.email,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          accessTokenExpiry: Date.now() + 14 * 60 * 1000,
          role,
        }
      },
    }),

    // Google reads AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET from env automatically
    Google,
  ],

  session: { strategy: "jwt" },

  pages: {
    signIn: "/login",
    error: "/login", // Redirect auth errors to login with ?error= param
  },

  callbacks: {
    async jwt({ token, user, account }) {
      // -----------------------------------------------------------------------
      // First sign-in via Credentials: user object is populated
      // -----------------------------------------------------------------------
      if (user) {
        token.accessToken = user.accessToken
        token.refreshToken = user.refreshToken
        token.accessTokenExpiry = user.accessTokenExpiry
        token.userId = user.id ?? ""
        token.role = user.role ?? "user"
        return token
      }

      // -----------------------------------------------------------------------
      // First sign-in via Google: exchange Google id_token for FastAPI tokens
      // -----------------------------------------------------------------------
      if (account?.provider === "google" && account.id_token) {
        const res = await fetch(`${API}/auth/google/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id_token: account.id_token }),
        })

        if (!res.ok) {
          return { ...token, error: "GoogleTokenExchangeError" }
        }

        const data = await res.json()
        const { userId, role } = decodeJwtPayload(data.access_token)

        token.accessToken = data.access_token
        token.refreshToken = data.refresh_token
        token.accessTokenExpiry = Date.now() + 14 * 60 * 1000
        token.userId = userId
        token.role = role
        return token
      }

      // -----------------------------------------------------------------------
      // Subsequent requests: check expiry and refresh transparently if needed
      // -----------------------------------------------------------------------
      if (Date.now() < token.accessTokenExpiry) {
        return token
      }

      return refreshAccessToken(token)
    },

    async session({ session, token }) {
      // Expose FastAPI tokens and user info to the client via useSession()
      session.accessToken = token.accessToken
      session.user.id = token.userId
      session.user.role = token.role
      if (token.error) session.error = token.error
      return session
    },
  },
})
