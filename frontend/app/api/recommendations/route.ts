import { NextResponse } from 'next/server'

import { ApiError, recommend } from '@/lib/api'
import { GENRE_SEAL } from '@/lib/explicit'
import { parseQuery, toRequest } from '@/lib/recommend'

async function run(query: string) {
  const parsed = parseQuery(new URLSearchParams(query))
  if (!parsed.marks.like.length) return []
  const result = await recommend(toRequest(parsed, GENRE_SEAL))
  return result.recommendations.map((r) => r.manga.id)
}

/**
 * A dry run for the tuning drawer: what applying a draft would change.
 *
 * Takes the page's current query string and the drafted one, builds both
 * requests here the same way the page does, and answers with counts only.
 */
export async function POST(request: Request) {
  const { query = '', draft = '' } = (await request.json().catch(() => ({}))) as {
    query?: string
    draft?: string
  }
  try {
    const [now, next] = await Promise.all([run(query), run(draft)])
    const was = new Map(now.map((id, i) => [id, i]))
    const added = next.filter((id) => !was.has(id)).length
    const moved = next.filter((id, i) => was.has(id) && was.get(id) !== i).length
    const left = now.length - (next.length - added)
    return NextResponse.json({ added, moved, left })
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 502
    return NextResponse.json({ detail: 'The engine did not answer.' }, { status })
  }
}
