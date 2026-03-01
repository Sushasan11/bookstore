import { revalidatePath } from 'next/cache'
import { auth } from '@/auth'
import { NextResponse } from 'next/server'

interface RevalidationEntry {
  path: string
  type?: 'page' | 'layout'
}

export async function POST(request: Request) {
  const session = await auth()

  // Admin guard — prevent unauthorized cache busting
  if (!session?.user || session.user.role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const body = await request.json().catch(() => ({}))
  const paths: RevalidationEntry[] = Array.isArray(body.paths) ? body.paths : []

  for (const entry of paths) {
    // Support both string entries (legacy) and object entries with type
    if (typeof entry === 'string') {
      revalidatePath(entry)
    } else {
      revalidatePath(entry.path, entry.type)
    }
  }

  return NextResponse.json({ revalidated: true, paths })
}
