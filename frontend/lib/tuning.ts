/**
 * The tuning drawer's controls, as data: what each one is called, what its value
 * means in words, and which request field it sets.
 *
 * Only what `POST /recommendations` accepts appears here. A knob the API does not
 * take yet is not shown at all, rather than faked.
 */

import { MAX_RECOMMENDATIONS } from './types'
import type { RecommendationStrategy } from './types'

export interface Recipe {
  strategy: RecommendationStrategy
  label: string
  says: string
}

/** The strategies, as starting points. Choosing one clears the weight overrides. */
export const RECIPES: readonly Recipe[] = [
  {
    strategy: 'auto',
    label: 'Best of both',
    says: 'Story first, genre as a tiebreak. The default.',
  },
  { strategy: 'balanced', label: 'Even mix', says: 'Story and genre count the same.' },
  {
    strategy: 'content',
    label: 'Story only',
    says: 'What the plot is about. Genre labels are ignored.',
  },
  {
    strategy: 'tags',
    label: 'Genre only',
    says: 'Shared genre and theme codes. The plot is ignored.',
  },
]

export interface SourceCopy {
  label: string
  help: string
  /** What the source does, for the engine details layer. */
  engine: string
}

/** Plain names for the engine's sources. An unknown source falls back to its API name. */
const SOURCES: Record<string, SourceCopy> = {
  content: {
    label: 'Story',
    help: 'How much a similar synopsis counts — what the plot is about.',
    engine:
      'content source · nearest synopsis embeddings (BAAI/bge-small-en-v1.5), HNSW inner product on unit vectors = cosine similarity',
  },
  tags: {
    label: 'Genre',
    help: 'How much shared genre and theme codes count.',
    engine: 'tags source · titles ranked by how many codes they share with yours',
  },
}

export function sourceCopy(source: string): SourceCopy {
  return (
    SOURCES[source] ?? {
      label: source,
      help: `How much the ${source} source counts.`,
      engine: `${source} source`,
    }
  )
}

/**
 * Weight sliders run 0–1.
 *
 * Only the ratio between sources changes the order, so this range reaches every mix.
 */
export const WEIGHT_RANGE = { min: 0, max: 1, step: 0.01 } as const
export const LIMIT_RANGE = { min: 1, max: MAX_RECOMMENDATIONS, step: 1 } as const

export const weightWords = (value: number) => (value ? value.toFixed(2) : 'Off')

const times = (ratio: number) =>
  Math.abs(ratio - Math.round(ratio)) < 0.05
    ? String(Math.round(ratio))
    : ratio.toFixed(ratio < 1.5 ? 2 : 1)

/**
 * One sentence on how two weights compare. Written for the Story/Genre pair; for
 * any other set of sources it names the strongest one.
 */
export function balanceWords(weights: Record<string, number>): string {
  const entries = Object.entries(weights)
  if (entries.every(([, w]) => !w)) return 'Nothing counts yet — raise at least one.'
  if (entries.length !== 2) {
    const [top] = [...entries].sort((a, b) => b[1] - a[1])
    return `${sourceCopy(top[0]).label} counts most.`
  }
  const [[a, wa], [b, wb]] = entries
  const la = sourceCopy(a).label,
    lb = sourceCopy(b).label
  if (!wb) return `Only ${la.toLowerCase()} counts.`
  if (!wa) return `Only ${lb.toLowerCase()} counts.`
  const ratio = wa / wb
  if (ratio > 1.04) return `${la} counts ${times(ratio)}× as much as ${lb.toLowerCase()}.`
  if (ratio < 0.96)
    return `${lb} counts ${times(1 / ratio)}× as much as ${la.toLowerCase()}.`
  return `${la} and ${lb.toLowerCase()} count the same.`
}

export const limitHelp = (n: number) =>
  `The engine returns ${n} pick${n === 1 ? '' : 's'}. It accepts 1 to ${MAX_RECOMMENDATIONS}.`

/** Where each control lands in the request, for the engine details layer. */
export const ENGINE_NOTES = {
  strategy:
    'sent as strategy · one of auto · balanced · content · tags; supplies every weight you leave alone',
  weight: (source: string) => `sent as weights.${source} · ${sourceCopy(source).engine}`,
  skip: 'sent as exclude_tags · titles carrying any of these codes are dropped',
  limit: `sent as limit · 1 – ${MAX_RECOMMENDATIONS}`,
  piles:
    'More like this → liked_ids · Not for me → disliked_ids · Already read → exclude_ids',
} as const
