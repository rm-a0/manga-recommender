'use client'

import { useEffect, useState } from 'react'

export interface Hit {
  id: string
  title: string
  /** The English title, only when it differs from the romaji. */
  english: string | null
  author: string | null
  image_url: string | null
}

/**
 * Debounced title lookup through `/api/search`.
 *
 * The API's title search is an unindexed `ILIKE` scan, so keystrokes wait 350 ms.
 * Results carry the term that produced them, so a stale response never shows
 * against a newer query.
 */
export function useTitleSearch(query: string) {
  const [result, setResult] = useState<{ term: string; items: Hit[] }>({
    term: '',
    items: [],
  })
  const term = query.trim()

  useEffect(() => {
    if (term.length < 2) return
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(term)}`, {
          signal: controller.signal,
        })
        const data = (await response.json()) as { items: Hit[] }
        setResult({ term, items: data.items })
      } catch {
        // An aborted keystroke is not an error worth showing.
      }
    }, 350)
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [term])

  const settled = result.term === term
  return {
    term,
    hits: settled ? result.items : [],
    searching: term.length >= 2 && !settled,
  }
}
