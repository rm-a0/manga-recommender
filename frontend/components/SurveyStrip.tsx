'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useRef, useState, useTransition } from 'react'

interface Hit {
  id: string
  title: string
  author: string | null
}

export interface Seed {
  id: string
  title: string
}

/**
 * The reader's own marks: the titles they ring in the hall.
 *
 * Seeds live in the URL, so a set of them is shareable and the back button walks
 * them. Lookup is debounced because the API's title search is an unindexed
 * `ILIKE` scan, and matches romaji only — the field says so rather than leaving
 * an English title to fail silently.
 */
export function SurveyStrip({ seeds }: { seeds: Seed[] }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isPending, startTransition] = useTransition()

  const [query, setQuery] = useState('')
  // Results carry the term that produced them, so a stale response is never
  // shown against a newer query and the effect sets no state up front.
  const [result, setResult] = useState<{ term: string; items: Hit[] }>({ term: '', items: [] })
  const [open, setOpen] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)

  const term = query.trim()
  const settled = result.term === term
  const hits = settled ? result.items : []
  const searching = term.length >= 2 && !settled

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
        setOpen(true)
      } catch {
        // An aborted keystroke is not an error worth showing.
      }
    }, 350)

    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [term])

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [])

  function commit(next: string[]) {
    // Code requirements derive from the ringed set, so changing it clears them
    // rather than carrying a selection the new codes may not contain.
    const params = new URLSearchParams(searchParams.toString())
    params.delete('seed')
    params.delete('tag')
    params.delete('match')
    for (const id of next) params.append('seed', id)
    startTransition(() => router.push(params.size ? `/?${params}` : '/', { scroll: false }))
  }

  function addSeed(hit: Hit) {
    setQuery('')
    setResult({ term: '', items: [] })
    setOpen(false)
    if (seeds.some((seed) => seed.id === hit.id)) return
    commit([...seeds.map((seed) => seed.id), hit.id])
  }

  return (
    <section aria-labelledby="survey-heading">
      <h1
        id="survey-heading"
        className="font-display text-3xl uppercase leading-none tracking-[0.02em] sm:text-4xl"
      >
        Ring what you have read
      </h1>
      <p className="mt-2 max-w-[62ch] text-base text-dim">
        Name titles you already know and they are marked in the hall. Search matches romaji
        only, so <span className="text-text">shingeki no kyojin</span>, not{' '}
        <span className="text-text">attack on titan</span>.
      </p>

      <div ref={boxRef} className="relative mt-3.5 max-w-xl">
        <label htmlFor="survey-input" className="sr-only">
          Search the hall by title
        </label>
        {/*
          Deliberately not a combobox. The full ARIA pattern needs listbox
          semantics, arrow traversal and aria-activedescendant; half of it
          announces options assistive tech then cannot find. This is a search
          field over a list of buttons, and Tab already reaches every result.
        */}
        <input
          id="survey-input"
          type="search"
          autoComplete="off"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => hits.length > 0 && setOpen(true)}
          onKeyDown={(event) => event.key === 'Escape' && setOpen(false)}
          placeholder="Search the hall — romaji title"
          className="w-full border-0 bg-cell px-3 py-2.5 text-base text-cell-ink placeholder:text-cell-sub"
        />

        <p aria-live="polite" className="sr-only">
          {searching ? 'Searching' : `${hits.length} matches`}
        </p>

        {open && hits.length > 0 && (
          <ul
            aria-label="Matching titles"
            className="absolute z-20 mt-px w-full border border-line bg-panel"
          >
            {hits.map((hit) => (
              <li key={hit.id} className="border-b border-line last:border-b-0">
                <button
                  type="button"
                  onClick={() => addSeed(hit)}
                  className="flex w-full items-baseline gap-2 px-3 py-2 text-left hover:bg-ground"
                >
                  <span className="truncate text-base">{hit.title}</span>
                  {hit.author && (
                    <span className="ml-auto shrink-0 truncate text-xs text-dim">
                      {hit.author}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}

        {term.length >= 2 && !searching && hits.length === 0 && (
          <p className="mt-2 text-base text-dim">
            No title matches “{term}”. Try the romaji spelling.
          </p>
        )}
      </div>

      {seeds.length > 0 && (
        <ul className="mt-3.5 flex flex-wrap gap-2" aria-label="Titles you have ringed">
          {seeds.map((seed) => (
            <li key={seed.id}>
              <button
                type="button"
                onClick={() => commit(seeds.filter((s) => s.id !== seed.id).map((s) => s.id))}
                disabled={isPending}
                className="flex items-center gap-2 border border-pen px-3 py-1.5 text-base text-text transition-colors hover:bg-pen hover:text-white disabled:opacity-60"
              >
                <span>{seed.title}</span>
                <span aria-hidden="true" className="text-base leading-none">
                  ×
                </span>
                <span className="sr-only">Remove</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
