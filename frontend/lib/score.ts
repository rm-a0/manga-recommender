/**
 * The catalogue's rating figures, as the interface prints them.
 *
 * `bayesian_score` arrives as a 0-1 fraction. Everything here reads out of ten,
 * which is the scale the source ratings were given on and the one a reader
 * already knows.
 */

import type { MangaMetrics } from './types'

/** Return the weighted score out of ten, or null when the title has no rating. */
export function scoreOutOfTen(metrics: MangaMetrics | null): number | null {
  if (!metrics) return null
  return metrics.bayesian_score * 10
}

/** Set a score to one decimal: 9.5, never 9.46. */
export function formatScore(score: number): string {
  return score.toFixed(1)
}

/**
 * Set a vote count for a cell, where the column is a few characters wide.
 *
 * Thousands round to one decimal below ten thousand and to whole units above,
 * so the figure never grows past four characters: 9.9K, 442K, 1.2M.
 */
export function formatVotesShort(votes: number): string {
  if (votes < 1000) return String(votes)
  if (votes < 10_000) return `${(votes / 1000).toFixed(1)}K`
  if (votes < 1_000_000) return `${Math.round(votes / 1000)}K`
  return `${(votes / 1_000_000).toFixed(1)}M`
}

/** Set a vote count in full, for pages with room for the real figure. */
export function formatVotes(votes: number): string {
  return votes.toLocaleString('en')
}
