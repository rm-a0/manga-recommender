import 'server-only'

import type {
  AuthorDetail,
  MangaDetail,
  MangaListParams,
  MangaSummary,
  Page,
  TagSummary,
} from './types'

const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000'

/** Tags excluded from every catalogue query unless the reader opts back in. */
export const ADULT_TAGS = ['Hentai', 'Erotica'] as const

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
  ) {
    super(`API ${status} on ${path}`)
    this.name = 'ApiError'
  }
}

function toQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      for (const entry of value) search.append(key, String(entry))
    } else {
      search.set(key, String(value))
    }
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

/**
 * Fetch one API path. Throws ApiError on a non-2xx so a route's error boundary
 * can distinguish a missing record from an unreachable API.
 *
 * Responses are not cached: the catalogue is re-ingested out of band and a stale
 * page is worse than a slow one. Pages stream instead, which is what covers the
 * API's cold start.
 */
async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: 'no-store' })
  if (!response.ok) throw new ApiError(response.status, path)
  return (await response.json()) as T
}

/** Return one page of manga. `allowAdult` opts out of the default tag exclusion. */
export function listManga(
  params: MangaListParams = {},
  { allowAdult = false }: { allowAdult?: boolean } = {},
): Promise<Page<MangaSummary>> {
  const exclude = [...(params.exclude_tag ?? [])]
  if (!allowAdult) {
    for (const tag of ADULT_TAGS) if (!exclude.includes(tag)) exclude.push(tag)
  }
  return get(`/manga${toQuery({ ...params, exclude_tag: exclude })}`)
}

/** Return one manga in full, or null when the ID matches nothing. */
export async function getManga(id: string): Promise<MangaDetail | null> {
  try {
    return await get<MangaDetail>(`/manga/${id}`)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

/**
 * Return the whole tag vocabulary in one call.
 *
 * The vocabulary is ~79 rows and the endpoint caps `limit` at 100, so one page
 * holds all of it. Filtering happens in the browser rather than per keystroke.
 */
export async function listAllTags(): Promise<TagSummary[]> {
  const page = await get<Page<TagSummary>>(`/tags${toQuery({ limit: 100 })}`)
  return page.items
}

/** Return one author in full, or null when the ID matches nothing. */
export async function getAuthor(id: string): Promise<AuthorDetail | null> {
  try {
    return await get<AuthorDetail>(`/authors/${id}`)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

/** Return one page of the manga credited to an author. */
export function listAuthorManga(
  id: string,
  params: { limit?: number; offset?: number } = {},
): Promise<Page<MangaSummary>> {
  return get(`/authors/${id}/manga${toQuery(params)}`)
}
