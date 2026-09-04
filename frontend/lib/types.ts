/**
 * Mirrors backend/manga_recommender/schemas/*.py.
 *
 * Kept hand-written rather than generated: the API is small and stable, and a
 * generator would be one more thing to run. If these drift, the backend schema
 * is the authority.
 */

export type MangaStatus = 'ongoing' | 'finished' | 'hiatus' | 'cancelled' | 'not_released_yet'

export type SortOrder = 'asc' | 'desc'
export type MangaSort = 'title' | 'published_date'
export type TagMatch = 'any' | 'all'

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface AuthorSummary {
  id: string
  name: string
}

export interface AuthorDetail extends AuthorSummary {
  manga_count: number
}

export interface TagSummary {
  id: string
  name: string
}

export interface TagDetail extends TagSummary {
  category: string | null
  manga_count: number
}

export interface MangaTag extends TagSummary {
  is_spoiler: boolean
  rank: number | null
}

export interface MangaSummary {
  id: string
  title: string
  authors: AuthorSummary[]
  status: MangaStatus | null
  image_url: string | null
}

export interface MangaDetail extends MangaSummary {
  published_date: string | null
  description: string | null
  tags: MangaTag[]
}

/** Query shape for `GET /manga`. Mirrors MangaListParams. */
export interface MangaListParams {
  q?: string
  status?: MangaStatus[]
  include_tag?: string[]
  exclude_tag?: string[]
  tag_match?: TagMatch
  published_from?: string
  published_to?: string
  sort?: MangaSort
  order?: SortOrder
  limit?: number
  offset?: number
}
