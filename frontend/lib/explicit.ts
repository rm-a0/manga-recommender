/**
 * The codes the catalogue keeps sealed.
 *
 * Which codes are explicit is the API's call: `TagSummary.is_explicit`, set at
 * ingest. Nothing here names a code, except the recommendation stopgap at the
 * bottom, `GENRE_SEAL`. What stays in the frontend is how a seal is
 * applied, because the API has no switch for it yet.
 *
 * A picker drops the flagged codes itself. A listing cannot: `MangaSummary`
 * carries no tags and `GET /manga` has no `include_explicit`, so a sealed listing
 * sends the flagged codes as `exclude_tag`. That parameter caps at ten values, and
 * the seal spends its slots before the reader does. The backend TODO tracks the
 * server-side filter that retires this.
 */

import { MAX_TAG_FILTERS } from './types'

/** Drop the explicit codes from a vocabulary, unless the seal is broken. */
export function unsealed<T extends { is_explicit: boolean }>(tags: T[], showSealed: boolean): T[] {
  return showSealed ? tags : tags.filter((tag) => !tag.is_explicit)
}

/** Return the names of the explicit codes in a vocabulary, in its own order. */
export function explicitNames(tags: { name: string; is_explicit: boolean }[]): string[] {
  return tags.filter((tag) => tag.is_explicit).map((tag) => tag.name)
}

/**
 * Return how many codes a reader may bar.
 *
 * A sealed listing spends one `exclude_tag` slot on each explicit code, so the
 * reader's own budget is what is left over. It never goes below zero.
 */
export function barredCodeLimit(showSealed: boolean, explicitCount: number): number {
  return showSealed ? MAX_TAG_FILTERS : Math.max(0, MAX_TAG_FILTERS - explicitCount)
}

/**
 * The codes a recommendation run keeps out, until the API can filter explicit titles.
 *
 * Genre level only, and deliberately short. The tag-level flag also marks codes
 * that sit on mainstream titles, so sending every flagged code as `exclude_tags`
 * drops series no one would call explicit. These two are the source genres that
 * mark a whole title adult. Retire this list when the API gains `include_explicit`
 * (backend issue #23).
 */
export const GENRE_SEAL: readonly string[] = ['Hentai', 'Erotica']
