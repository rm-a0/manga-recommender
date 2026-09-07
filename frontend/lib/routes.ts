import 'server-only'

import { getManga, listManga } from './api'
import { isSealedTag } from './explicit'
import { MAX_TAG_FILTERS } from './types'
import type { MangaDetail, MangaSummary, TagMatch } from './types'

/**
 * The reading routes.
 *
 * One is live. The rest are recorded here so the contents page can name what is
 * coming without pretending it works. Adding a route later means flipping `live`
 * and writing its resolver — no layout changes, and nothing to unpick.
 */
export interface Route {
  id: string
  name: string
  live: boolean
  description: string
}

export const ROUTES: Route[] = [
  {
    id: 'shared-tags',
    name: 'Shared tags',
    live: true,
    description: 'Titles carrying the tags your selection carries, best rated first.',
  },
  {
    id: 'history',
    name: 'Your reading history',
    live: false,
    description: 'Import a MyAnimeList list instead of typing titles one at a time.',
  },
  {
    id: 'semantic',
    name: 'Themes and description',
    live: false,
    description: 'Similarity read from synopsis text rather than tag labels.',
  },
  {
    id: 'collaborative',
    name: 'What other readers liked',
    live: false,
    description: 'Signal drawn from readers whose lists overlap yours.',
  },
  {
    id: 'custom',
    name: 'A blend you control',
    live: false,
    description: 'Several routes at once, with tags excluded and preferences weighted.',
  },
]

export const LIVE_ROUTE = ROUTES.find((route) => route.live)!
export const PLANNED_ROUTES = ROUTES.filter((route) => !route.live)

/**
 * How many of a seed's tags are required by default.
 *
 * Requiring every tag matches the seed alone; requiring one matches thousands.
 * Three is where the catalogue starts returning titles a reader recognises as
 * related. It is a starting point, not a judgement — the reader changes it.
 */
const DEFAULT_TAG_COUNT = 3

export interface RouteResult {
  items: MangaSummary[]
  /** Every tag carried by the seeds, in the order the API returned them. */
  availableTags: string[]
  /** The tags actually required by this query. */
  activeTags: string[]
  match: TagMatch
  total: number
  seeds: MangaDetail[]
}

/**
 * Resolve the shared-tags route.
 *
 * Asks the catalogue for titles carrying the requested tags, best rated first,
 * and drops the seeds themselves from the answer.
 *
 * The ordering is the API's: this asks for `sort=rating` and renders the page it
 * gets back. Nothing is scored, weighted or reordered here. Which codes matter
 * is still the reader's choice, and how well a title matches them is not part of
 * the ordering — that judgement needs a recommendation engine, which the backend
 * does not have yet.
 */
export async function resolveSharedTags(
  seedIds: string[],
  {
    tags,
    match = 'all',
    limit = 30,
    showSealed = false,
  }: { tags?: string[]; match?: TagMatch; limit?: number; showSealed?: boolean } = {},
): Promise<RouteResult> {
  const seeds = (await Promise.all(seedIds.map((id) => getManga(id)))).filter(
    (seed): seed is MangaDetail => seed !== null,
  )

  const availableTags: string[] = []
  for (const seed of seeds) {
    for (const tag of seed.tags) {
      if (!showSealed && isSealedTag(tag.name)) continue
      if (!availableTags.includes(tag.name)) availableTags.push(tag.name)
    }
  }

  const requested = tags?.filter((tag) => availableTags.includes(tag)) ?? []
  const activeTags = (
    requested.length > 0 ? requested : availableTags.slice(0, DEFAULT_TAG_COUNT)
  ).slice(0, MAX_TAG_FILTERS)

  if (activeTags.length === 0) {
    return { items: [], availableTags, activeTags, match, total: 0, seeds }
  }

  // Over-fetch by the seed count so removing the seeds still fills the page.
  const page = await listManga(
    {
      include_tag: activeTags,
      tag_match: match,
      limit: Math.min(100, limit + seeds.length),
      sort: 'rating',
      order: 'desc',
    },
    { showSealed },
  )

  const seedIdSet = new Set(seeds.map((seed) => seed.id))
  const items = page.items.filter((item) => !seedIdSet.has(item.id)).slice(0, limit)

  return { items, availableTags, activeTags, match, total: page.total, seeds }
}
