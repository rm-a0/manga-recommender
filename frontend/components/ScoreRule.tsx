import { formatScore, formatVotes, scoreOutOfTen } from '@/lib/score'
import type { MangaMetrics } from '@/lib/types'

/** One segment per point of the score, so the scale is counted, not guessed. */
const SEGMENTS = 10

/**
 * The weighted score at size: the figure, a ten-segment rule, and how many
 * readers scored it.
 *
 * The rule belongs to this page and not to a cell. Half the catalogue scores
 * between 6.79 and 7.07, so a rule that measures the score separates nothing in
 * a grid — there it is the printed figure that carries the difference. On one
 * title there is nothing to compare against, and the segments do the job the
 * figure cannot: they say what the score is out of.
 *
 * Two thirds of the catalogue has no metrics row, so the unrated case says what
 * is missing and why, rather than printing an empty rule with nothing to explain
 * it.
 */
export function ScoreRule({ metrics }: { metrics: MangaMetrics | null }) {
  const score = scoreOutOfTen(metrics)

  if (!metrics || score === null) {
    return (
      <div className="mt-4 border-t border-line pt-3">
        <p className="code text-dim">Not rated</p>
        <p className="mt-1.5 max-w-[46ch] text-sm text-dim">
          A title needs at least a hundred ratings before the catalogue computes a
          score for it. This one has fewer, or none recorded.
        </p>
      </div>
    )
  }

  const filled = Math.floor(score)
  const remainder = score - filled

  return (
    <div className="mt-4 border-t border-line pt-3">
      <div className="flex items-baseline gap-2.5">
        <span className="font-display text-[2.5rem] leading-none text-spot">
          {formatScore(score)}
        </span>
        <span className="code text-dim">out of 10 · weighted</span>
      </div>

      <div aria-hidden="true" className="mt-2.5 flex h-2 max-w-[22rem] gap-px">
        {Array.from({ length: SEGMENTS }).map((_, index) => (
          <span key={index} className="h-full flex-1 bg-panel">
            {index < filled ? (
              <span className="block h-full w-full bg-spot" />
            ) : index === filled ? (
              <span
                className="block h-full bg-spot"
                style={{ width: `${remainder * 100}%` }}
              />
            ) : null}
          </span>
        ))}
      </div>

      <p className="code mt-2 text-dim">
        {formatVotes(metrics.votes_count)} ratings
      </p>
    </div>
  )
}
