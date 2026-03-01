export type RevalidationPath = string | { path: string; type: 'page' | 'layout' }

/**
 * Fire-and-forget storefront cache revalidation.
 *
 * Calls POST /api/revalidate to purge the Next.js fetch cache for the given paths.
 * Admin mutations call this from onSuccess — do NOT await; admin UX must not block.
 * Silent failure in production: ISR safety net (revalidate = 3600) handles recovery.
 *
 * Accepts plain strings for simple paths (e.g. '/catalog') or objects with a `type`
 * field for dynamic route patterns (e.g. { path: '/books/[id]', type: 'page' }).
 * The `type` parameter tells Next.js to revalidate ALL pages matching that pattern.
 */
export function triggerRevalidation(paths: RevalidationPath[]) {
  fetch('/api/revalidate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  }).catch((err) => {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[revalidate] failed:', err)
    }
  })
}
