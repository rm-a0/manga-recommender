import { NextResponse } from 'next/server'

import { listManga } from '@/lib/api'

/**
 * Title lookup for the survey field.
 *
 * Exists so the browser never calls the manga API directly: the API sets no CORS
 * headers, and keeping the call server-side means it never needs to. Results are
 * trimmed to what the picker draws.
 */
export async function GET(request: Request) {
  const q = new URL(request.url).searchParams.get('q')?.trim() ?? ''

  // The API rejects a `q` under two characters, so answer empty rather than 422.
  if (q.length < 2) return NextResponse.json({ items: [] })

  const page = await listManga({ q, limit: 8, sort: 'title', order: 'asc' })

  return NextResponse.json({
    items: page.items.map((manga) => ({
      id: manga.id,
      title: manga.title,
      author: manga.authors[0]?.name ?? null,
    })),
  })
}
