import 'server-only'

import { cache } from 'react'

import { explicitNames } from './explicit'
import { MAX_TAG_FILTERS } from './types'
import type {
  AuthorDetail,
  AuthorSummary,
  MangaDetail,
  MangaListParams,
  MangaSummary,
  Page,
  RecommendationRequest,
  RecommendationResult,
  StrategyInfo,
  TagSummary,
} from './types'

const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000'

/** The API's ceiling on `limit` for every paged endpoint. */
const MAX_PAGE_SIZE = 100

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

/** Post a JSON body to one API path. Same error contract as `get`. */
async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  if (!response.ok) throw new ApiError(response.status, path)
  return (await response.json()) as T
}

/**
 * Run the recommendation engine once.
 *
 * The picks come back in display order and are rendered in that order: the
 * frontend never scores or re-ranks them.
 */
export function recommend(request: RecommendationRequest): Promise<RecommendationResult> {
  return post('/recommendations', request)
}

/**
 * Return every strategy and the weight it gives each source.
 *
 * Reads no table on the API side, so one call per render is plenty; the drawer
 * uses it for each slider's default and to list the sources at all.
 */
export const listStrategies = cache(
  (): Promise<StrategyInfo[]> => get('/recommendations/strategies'),
)

/**
 * Return the whole tag vocabulary, explicit codes included.
 *
 * Pages through `GET /tags` until `total` is reached: MAL alone ships ~80 codes,
 * but AniList's vocabulary runs past the endpoint's 100-row ceiling. Filtering
 * happens in the browser rather than per keystroke.
 *
 * Wrapped in `cache` so the masthead, the listing's seal and a picker on one
 * render share a single walk rather than three.
 */
export const listAllTags = cache(async (): Promise<TagSummary[]> => {
  const tags: TagSummary[] = []
  for (;;) {
    const page = await get<Page<TagSummary>>(
      `/tags${toQuery({ limit: MAX_PAGE_SIZE, offset: tags.length })}`,
    )
    tags.push(...page.items)
    if (page.items.length === 0 || tags.length >= page.total) return tags
  }
})

/**
 * Return one page of manga.
 *
 * The explicit codes are excluded unless `showSealed` says otherwise. The API caps
 * `exclude_tag` at ten values and the seal's codes go first, so a reader's own
 * barred codes are expected to fit in `barredCodeLimit`. If the vocabulary ever
 * flags more than ten, the surplus cannot be sent: that is the point at which the
 * server-side `include_explicit` filter stops being optional.
 */
export async function listManga(
  params: MangaListParams = {},
  { showSealed = false }: { showSealed?: boolean } = {},
): Promise<Page<MangaSummary>> {
  let exclude = [...(params.exclude_tag ?? [])]
  if (!showSealed) {
    const sealed = explicitNames(await listAllTags())
    exclude = [...sealed, ...exclude.filter((tag) => !sealed.includes(tag))]
  }
  return get(
    `/manga${toQuery({ ...params, exclude_tag: exclude.slice(0, MAX_TAG_FILTERS) })}`,
  )
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
