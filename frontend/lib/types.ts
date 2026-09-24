/**
 * Mirrors backend/manga_recommender/schemas/*.py.
 *
 * Kept hand-written rather than generated: the API is small and stable, and a
 * generator would be one more thing to run. If these drift, the backend schema
 * is the authority.
 */

/**
 * How many values `include_tag` and `exclude_tag` each accept.
 *
 * Mirrors `Field(max_length=10)` on `MangaListParams`. The API rejects an
 * eleventh with a 422, so anything building either list caps itself here.
 */
export const MAX_TAG_FILTERS = 10

export type MangaStatus = 'ongoing' | 'finished' | 'hiatus' | 'cancelled' | 'not_released_yet'

/** The medium an entry was published in. Mirrors `MangaType`. */
export type MangaType =
  | 'manga'
  | 'light_novel'
  | 'manhwa'
  | 'one_shot'
  | 'doujinshi'
  | 'manhua'

export type SortOrder = 'asc' | 'desc'
export type MangaSort = 'title' | 'published_date' | 'popularity' | 'rating'
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
  /** Adult content. Set at ingest: a tag any source marks adult stays adult. */
  is_explicit: boolean
}

export interface TagDetail extends TagSummary {
  category: string | null
  manga_count: number
}

/** A tag inside a manga response. Carries no `is_explicit`: read it off the vocabulary. */
export interface MangaTag {
  id: string
  name: string
  is_spoiler: boolean
  rank: number | null
}

/**
 * The rating figures derived from a title's external ratings.
 *
 * `bayesian_score` is a 0-1 fraction, weighted towards the catalogue mean so a
 * title with few votes cannot outrank a well-read one on a handful of scores.
 * A title with no usable source rating has no row at all, so this is null on
 * roughly two thirds of the catalogue.
 */
export interface MangaMetrics {
  id: string
  bayesian_score: number
  votes_count: number
}

export interface MangaSummary {
  id: string
  /** The romaji title. The API sorts and deduplicates on this one. */
  title: string
  /** The licensed English title, when a source records one. Often equal to `title`. */
  title_english: string | null
  authors: AuthorSummary[]
  status: MangaStatus | null
  image_url: string | null
  metrics: MangaMetrics | null
}

export interface MangaDetail extends MangaSummary {
  /** Only the detail response carries it, so a listing cannot print or filter on it. */
  type: MangaType | null
  /** A calendar date, `YYYY-MM-DD`, with no time part. */
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

/** The most picks one recommendation may return. Mirrors `le=50` on `limit`. */
export const MAX_RECOMMENDATIONS = 50

/** A named blend of the candidate sources. Mirrors `RecommendationStrategy`. */
export type RecommendationStrategy = 'auto' | 'balanced' | 'content' | 'tags'

/**
 * Query body for `POST /recommendations`. Mirrors `RecommendationRequest`.
 *
 * `weights` overrides single weights of the strategy; the strategy supplies the
 * rest. Only the ratio between weights changes the order.
 */
export interface RecommendationRequest {
  liked_ids: string[]
  disliked_ids?: string[]
  exclude_ids?: string[]
  exclude_tags?: string[]
  strategy?: RecommendationStrategy
  weights?: Record<string, number>
  limit?: number
}

/** Why one candidate source nominated a pick, and from which liked title. */
export interface RecommendationReason {
  source: string
  seed_id: string | null
}

export interface Recommendation {
  manga: MangaSummary
  reasons: RecommendationReason[]
}

/** A liked title the run started from. */
export interface RecommendationSeed {
  id: string
  title: string
}

/** One run's picks, in display order. The whole result, never a page. */
export interface RecommendationResult {
  recommendations: Recommendation[]
  strategy: RecommendationStrategy
  seeds: RecommendationSeed[]
}

/** One strategy and the weight it gives each source. Mirrors `StrategyInfo`. */
export interface StrategyInfo {
  strategy: RecommendationStrategy
  weights: Record<string, number>
}
