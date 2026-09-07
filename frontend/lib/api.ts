import 'server-only'

import { SEALED_WORK_TAGS, unsealed } from './explicit'
import type {
  AuthorDetail,
  AuthorSummary,
  MangaDetail,
  MangaListParams,
  MangaSummary,
  Page,
  TagSummary,
} from './types'

const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000'

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

/**
 * Return one page of manga.
 *
 * The sealed codes are excluded unless `showSealed` says otherwise. The API caps
 * `exclude_tag` at ten values, so a caller barring codes of its own has to leave
 * room for the seal's three.
 */
export function listManga(
  params: MangaListParams = {},
  { showSealed = false }: { showSealed?: boolean } = {},
): Promise<Page<MangaSummary>> {
  const exclude = [...(params.exclude_tag ?? [])]
  if (!showSealed) {
    for (const tag of SEALED_WORK_TAGS) if (!exclude.includes(tag)) exclude.push(tag)
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
 * Return the tag vocabulary in one call.
 *
 * The vocabulary is ~79 rows and the endpoint caps `limit` at 100, so one page
 * holds all of it. Filtering happens in the browser rather than per keystroke.
 *
 * Sealed codes are dropped unless `showSealed` says otherwise, so a picker built
 * on this never lists a code the reader asked not to see.
 */
export async function listAllTags(
  { showSealed = false }: { showSealed?: boolean } = {},
): Promise<TagSummary[]> {
  const page = await get<Page<TagSummary>>(`/tags${toQuery({ limit: 100 })}`)
  return unsealed(page.items, showSealed)
}

/**
 * Return how many authors the catalogue credits.
 *
 * Asks for a single row and reads `total` off the page, because the count is
 * the only part wanted and the endpoint has no cheaper way to give it.
 */
export async function countAuthors(): Promise<number> {
  const page = await get<Page<AuthorSummary>>(`/authors${toQuery({ limit: 1 })}`)
  return page.total
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
