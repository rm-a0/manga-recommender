/**
 * The recommend page's query: what the reader marked and how the engine is tuned.
 *
 * One URL parameter per API field, defaults left out, so a first visit's link
 * stays `?like=…` and every tuned link is shareable. Safe on the server and in
 * the browser: it only reads and writes search params.
 */

import { MAX_RECOMMENDATIONS } from './types'
import type { RecommendationRequest, RecommendationStrategy, StrategyInfo } from './types'

export const STRATEGIES: readonly RecommendationStrategy[] = [
  'auto',
  'balanced',
  'content',
  'tags',
]
export const DEFAULT_STRATEGY: RecommendationStrategy = 'auto'
export const DEFAULT_LIMIT = 20

/** The three piles a reader sorts titles into. Each is one request field. */
export type Pile = 'like' | 'dislike' | 'read'
export const PILES: readonly Pile[] = ['like', 'dislike', 'read']

export interface Marks {
  like: string[]
  dislike: string[]
  read: string[]
}

export interface Tuning {
  strategy: RecommendationStrategy
  /** Per-source overrides of the strategy's weights. Absent keys use the strategy. */
  weights: Record<string, number>
  /** Codes whose titles are kept out: `exclude_tags`. */
  skip: string[]
  limit: number
}

export interface RecommendQuery {
  marks: Marks
  tuning: Tuning
}

export const DEFAULT_TUNING: Tuning = {
  strategy: DEFAULT_STRATEGY,
  weights: {},
  skip: [],
  limit: DEFAULT_LIMIT,
}

type Params = Record<string, string | string[] | undefined> | URLSearchParams

function all(params: Params, key: string): string[] {
  if (params instanceof URLSearchParams) return params.getAll(key)
  const value = params[key]
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}

const one = (params: Params, key: string) => all(params, key)[0]
const unique = (ids: string[]) => [...new Set(ids.filter(Boolean))]

/**
 * Read a query from page `searchParams` or a `URLSearchParams`.
 *
 * Invalid values fall back to their defaults.
 */
export function parseQuery(params: Params): RecommendQuery {
  // `seed` is the old name for a liked title; links shared before the engine still land.
  const marks: Marks = {
    like: unique([...all(params, 'like'), ...all(params, 'seed')]),
    dislike: unique(all(params, 'dislike')),
    read: unique(all(params, 'read')),
  }
  // A title sits on one pile at most; the first pile listed wins.
  const seen = new Set<string>()
  for (const pile of PILES)
    marks[pile] = marks[pile].filter((id) => !seen.has(id) && seen.add(id))

  const strategy = one(params, 'strategy') as RecommendationStrategy | undefined
  const weights: Record<string, number> = {}
  const keys =
    params instanceof URLSearchParams ? [...params.keys()] : Object.keys(params)
  for (const key of keys) {
    if (!key.startsWith('w.')) continue
    const value = Number(one(params, key))
    if (Number.isFinite(value) && value >= 0) weights[key.slice(2)] = value
  }
  const limit = Number(one(params, 'n'))
  return {
    marks,
    tuning: {
      strategy: strategy && STRATEGIES.includes(strategy) ? strategy : DEFAULT_STRATEGY,
      weights,
      skip: unique(all(params, 'skip')),
      limit:
        Number.isInteger(limit) && limit >= 1 && limit <= MAX_RECOMMENDATIONS
          ? limit
          : DEFAULT_LIMIT,
    },
  }
}

/** Write a query as search params, leaving out every default. */
export function toSearchParams({ marks, tuning }: RecommendQuery): URLSearchParams {
  const params = new URLSearchParams()
  for (const pile of PILES) for (const id of marks[pile]) params.append(pile, id)
  if (tuning.strategy !== DEFAULT_STRATEGY) params.set('strategy', tuning.strategy)
  for (const [source, weight] of Object.entries(tuning.weights))
    params.set(`w.${source}`, String(weight))
  for (const code of tuning.skip) params.append('skip', code)
  if (tuning.limit !== DEFAULT_LIMIT) params.set('n', String(tuning.limit))
  return params
}

/** The URL of the recommend page for a query. */
export function queryHref(query: RecommendQuery): string {
  const params = toSearchParams(query)
  return params.size ? `/?${params}` : '/'
}

/** The weight each source gets under a tuning: the strategy's, then any override. */
export function effectiveWeights(
  tuning: Tuning,
  strategies: StrategyInfo[],
): Record<string, number> {
  const base = strategies.find((s) => s.strategy === tuning.strategy)?.weights ?? {}
  const sources = sourcesOf(strategies)
  return Object.fromEntries(sources.map((s) => [s, tuning.weights[s] ?? base[s] ?? 0]))
}

/**
 * Every source any strategy names, in first-seen order.
 *
 * A source the backend adds appears here, and so in the drawer, without a change.
 */
export function sourcesOf(strategies: StrategyInfo[]): string[] {
  return [...new Set(strategies.flatMap((s) => Object.keys(s.weights)))]
}

/**
 * Drop overrides that equal the strategy's own weight, so the URL and the request
 * carry only real changes.
 */
export function normaliseTuning(tuning: Tuning, strategies: StrategyInfo[]): Tuning {
  const base = strategies.find((s) => s.strategy === tuning.strategy)?.weights ?? {}
  const weights = Object.fromEntries(
    Object.entries(tuning.weights).filter(
      ([source, weight]) => Math.abs((base[source] ?? 0) - weight) > 1e-9,
    ),
  )
  return { ...tuning, weights }
}

/** The request body for a query. `seal` is added to the reader's own skipped codes. */
export function toRequest(
  { marks, tuning }: RecommendQuery,
  seal: readonly string[] = [],
): RecommendationRequest {
  const excludeTags = [...new Set([...seal, ...tuning.skip])]
  const request: RecommendationRequest = {
    liked_ids: marks.like,
    disliked_ids: marks.dislike,
    exclude_ids: marks.read,
    exclude_tags: excludeTags,
    strategy: tuning.strategy,
    limit: tuning.limit,
  }
  if (Object.keys(tuning.weights).length) request.weights = tuning.weights
  return request
}

/** Move one title onto a pile, or off every pile when `pile` is null. */
export function withMark(marks: Marks, id: string, pile: Pile | null): Marks {
  const next: Marks = {
    like: marks.like.filter((x) => x !== id),
    dislike: marks.dislike.filter((x) => x !== id),
    read: marks.read.filter((x) => x !== id),
  }
  if (pile) next[pile] = [...next[pile], id]
  return next
}

export function pileOf(marks: Marks, id: string): Pile | null {
  return PILES.find((pile) => marks[pile].includes(id)) ?? null
}
