import type { MangaSummary, MangaType } from './types'

/**
 * Return the English title when it says something the romaji does not.
 *
 * The romaji title is the entry: the API sorts and searches on it, and a catalogue
 * keeps one name per entry. The English title is printed beside it only when it
 * differs — 8,000 entries carry an English title that is the romaji letter for
 * letter (`Chainsaw Man`), and printing it twice is noise.
 */
export function englishAlias(
  manga: Pick<MangaSummary, 'title' | 'title_english'>,
): string | null {
  const english = manga.title_english?.trim()
  if (!english) return null
  const same = english.localeCompare(manga.title, 'en', { sensitivity: 'base' }) === 0
  return same ? null : english
}

/** How the detail page names each medium. */
export const MANGA_TYPE_LABEL: Record<MangaType, string> = {
  manga: 'Manga',
  light_novel: 'Light novel',
  manhwa: 'Manhwa',
  manhua: 'Manhua',
  one_shot: 'One-shot',
  doujinshi: 'Doujinshi',
}
