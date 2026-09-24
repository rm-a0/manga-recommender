import { NextResponse } from 'next/server'

import { getManga } from '@/lib/api'

/**
 * One title in full, for the entry sheet.
 *
 * A recommendation carries only the summary, so the synopsis and codes are
 * fetched when a reader opens a pick. Server-side, because the API sets no CORS
 * headers.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const manga = await getManga(id)
  if (!manga) return NextResponse.json({ detail: 'Not found' }, { status: 404 })
  return NextResponse.json(manga)
}
