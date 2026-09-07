/**
 * The codes the catalogue keeps sealed.
 *
 * Two lists, because they answer two different questions and the API caps one
 * of them. `SEALED_WORK_TAGS` is what a listing excludes, and `exclude_tag`
 * accepts at most ten values. `SEALED_TAGS` is what a picker hides, which has
 * no cap and can therefore cover a vocabulary this dataset has not seen yet.
 *
 * The set is written down here because the API has no way to say it. `TagSummary`
 * carries a name and nothing else, and even `TagDetail.category` only separates
 * Genre from Theme. An `is_adult` column on the tag model, surfaced on both tag
 * models, would replace this file with one boolean — worth doing in the backend
 * before AniList ingestion lands and the vocabulary grows.
 */

import { MAX_TAG_FILTERS } from './types'

/**
 * Codes whose titles are kept out of a sealed listing.
 *
 * They cover ~26,000 of the 82,629 titles held. Ten values at most: the API
 * rejects an eleventh.
 *
 * MyAnimeList counts Ecchi as a third explicit genre and hides it under the same
 * setting. This does not. Ecchi is fanservice rather than explicit content, and
 * 4,002 of the 4,080 titles carrying it carry neither of the two above — sealing
 * it would take that many ordinary titles out of the hall for no gain.
 */
export const SEALED_WORK_TAGS = ['Hentai', 'Erotica'] as const

/**
 * Codes kept out of a sealed picker.
 *
 * The three above, plus AniList's sexual-content vocabulary, which arrives with
 * that source's ingestion. Listing a code here hides it from every picker; it
 * does not filter any listing, so this list has no length limit and being
 * over-inclusive costs a reader nothing but a code they cannot filter on.
 *
 * Deliberately absent: Boys Love, Girls Love, Harem, Crossdressing and
 * Magical Sex Shift. They describe who a story is about, not what it shows.
 */
export const SEALED_TAGS: readonly string[] = [
  ...SEALED_WORK_TAGS,
  'Anal Sex',
  'Armpits',
  'Ashikoki',
  'Asphyxiation',
  'Blackmail',
  'Boobjob',
  'Bondage',
  'Cervix Penetration',
  'Cheating',
  'Cumflation',
  'Cunnilingus',
  'Deepthroat',
  'Defloration',
  'DILF',
  'Double Penetration',
  'Erotic Piercings',
  'Exhibitionism',
  'Facial',
  'Feet',
  'Femdom',
  'Fisting',
  'Flat Chest',
  'Futanari',
  'Group Sex',
  'Handjob',
  'Hypersexuality',
  'Incest',
  'Inseki',
  'Irrumatio',
  'Lactation',
  'Lolicon',
  'Male Pregnancy',
  'Masturbation',
  'Mating Press',
  'MILF',
  'Nakadashi',
  'Netorare',
  'Netorase',
  'Netori',
  'Pet Play',
  'Prostitution',
  'Public Sex',
  'Rape',
  'Rimjob',
  'Scat',
  'Scissoring',
  'Sex Toys',
  'Shotacon',
  'Squirting',
  'Sumata',
  'Sweat',
  'Tentacles',
  'Threesome',
  'Virginity',
  'Voyeur',
  'Watersports',
]

const sealed = new Set(SEALED_TAGS.map((name) => name.toLowerCase()))

/** Return true when a code is kept out of a sealed picker. */
export function isSealedTag(name: string): boolean {
  return sealed.has(name.toLowerCase())
}

/** Drop the sealed codes from a vocabulary, unless the seal is broken. */
export function unsealed<T extends { name: string }>(tags: T[], showSealed: boolean): T[] {
  return showSealed ? tags : tags.filter((tag) => !isSealedTag(tag.name))
}

/**
 * Return how many codes a reader may bar.
 *
 * A sealed listing spends one of the API's ten `exclude_tag` slots on each code
 * the seal holds back, so the reader's own budget is what is left over.
 */
export function barredCodeLimit(showSealed: boolean): number {
  return MAX_TAG_FILTERS - (showSealed ? 0 : SEALED_WORK_TAGS.length)
}
