/**
 * How a hall listing can be ordered.
 *
 * Deliberately not inside the order control: a `'use client'` module exports
 * client references rather than values, so a server component importing one gets
 * a proxy instead of the array.
 */

import type { MangaSort } from './types'

/** The orderings the control offers, as the `field:direction` pairs it submits. */
export const ORDERINGS = [
  { value: 'popularity:desc', label: 'Most read' },
  { value: 'rating:desc', label: 'Best rated' },
  { value: 'published_date:desc', label: 'Newest' },
  { value: 'published_date:asc', label: 'Oldest' },
  { value: 'title:asc', label: 'A–Z' },
  { value: 'title:desc', label: 'Z–A' },
] as const

/** Matches the API's own default, so an unordered request changes nothing. */
export const DEFAULT_ORDERING = 'popularity:desc'

/** Every field the API can order on. */
export const VALID_SORTS: MangaSort[] = ['title', 'published_date', 'popularity', 'rating']

/** Fields that read a metrics row, and so push unrated titles to the end. */
export const METRIC_SORTS: MangaSort[] = ['popularity', 'rating']

/**
 * How a heading names the ordering it applied.
 *
 * Covers both directions of every field, not only the six the control offers,
 * because a hand-written query string can ask for the other two.
 */
export const ORDER_LABEL: Record<string, string> = {
  'popularity:desc': 'most read first',
  'popularity:asc': 'least read first',
  'rating:desc': 'best rated first',
  'rating:asc': 'lowest rated first',
  'published_date:desc': 'newest first',
  'published_date:asc': 'oldest first',
  'title:asc': 'title A–Z',
  'title:desc': 'title Z–A',
}
