'use client'

import Image from 'next/image'
import { useEffect, useRef, useState } from 'react'

import { largeCover } from '@/lib/covers'
import { CloseIcon } from './icons'
import { PenMark } from '../PenMark'
import { useRecommend } from './RecommendProvider'
import { useTitleSearch } from './useTitleSearch'

/** How many liked titles the headline names before it counts the rest. */
const NAMED = 3
/** How many liked covers stand beside the headline before a "+N" tile. */
const COVERS = 4

const short = (title: string) => title.split(/:| - /)[0].trim()

/**
 * The page's cover line: who the picks are for, and where to add another title.
 *
 * The headline shrinks as it gets longer, and names three titles at most; the
 * rest are counted, and the count opens the liked pile.
 */
export function Hero({ tools }: { tools?: React.ReactNode }) {
  const { query, titles, unlike, setPilesOpen } = useRecommend()
  const likes = query.marks.like

  const named = likes
    .slice(0, NAMED)
    .map((id) => ({ id, title: short(titles[id]?.title ?? 'A title') }))
  const more = likes.length - named.length
  const length = named.map((n) => n.title).join(' & ').length + (more ? 10 : 0)
  // Rem size falls with the headline's length, between a floor and a ceiling.
  const size = Math.max(1.9, Math.min(4.6, 95 / (length + 4)))

  const showAll = () => {
    setPilesOpen(true)
    document
      .getElementById('piles')
      ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }

  return (
    <section
      aria-labelledby="hero-heading"
      className="grid items-end gap-x-9 gap-y-5 pt-7 pb-5 lg:grid-cols-[minmax(0,1fr)_auto]"
    >
      <div>
        <p className="mb-2 code text-dim">
          {likes.length
            ? `Picks for your ${likes.length} title${likes.length > 1 ? 's' : ''} · engine order`
            : 'Recommend'}
        </p>
        <h1
          id="hero-heading"
          className="hero-line font-display leading-[0.95] tracking-[0.005em] uppercase"
          style={
            {
              '--hs': `${likes.length ? size.toFixed(2) : 4.4}rem`,
            } as React.CSSProperties
          }
        >
          <span className="mb-[0.18em] block text-[max(0.4em,1.2rem)] tracking-[0.03em] text-dim">
            Picks for readers of
          </span>
          {likes.length === 0 && 'what you liked'}
          {named.map((n, i) => (
            <span key={n.id}>
              {i > 0 && (
                <span className="text-dim">
                  {i === named.length - 1 && !more ? ' & ' : ', '}
                </span>
              )}
              <span className="hero-name" lang="ja-Latn">
                {n.title}
              </span>
            </span>
          ))}
          {more > 0 && (
            <>
              <span className="text-dim"> & </span>
              <button
                type="button"
                onClick={showAll}
                className="hero-more text-dim uppercase hover:text-text"
              >
                {more} more
              </button>
            </>
          )}
        </h1>
        <div className="mt-4 flex flex-wrap items-center gap-x-3.5 gap-y-2.5">
          <TitleSearch
            placeholder={likes.length ? 'Add a title you liked…' : 'A title you liked…'}
          />
          {tools}
        </div>
      </div>

      {likes.length > 0 && (
        <ul className="flex flex-wrap gap-3" aria-label="Titles you liked">
          {likes.slice(0, COVERS).map((id) => {
            const stub = titles[id]
            const src = largeCover(stub?.image_url ?? null)
            return (
              <li key={id} className="relative w-[56px] sm:w-[74px]">
                <span className="relative block aspect-[225/320] bg-[#d9d4c5] shadow-[0_0_0_4px_var(--color-cell)]">
                  {src && (
                    <Image
                      src={src}
                      alt=""
                      width={74}
                      height={105}
                      sizes="74px"
                      className="h-full w-full object-cover"
                    />
                  )}
                  <PenMark label="You liked this" />
                </span>
                <button
                  type="button"
                  onClick={() => unlike(id)}
                  className="absolute -top-2.5 -right-2.5 z-10 grid size-6 place-items-center border border-line bg-ground text-dim hover:border-spot hover:text-spot-on-ground"
                  aria-label={`Remove ${stub?.title ?? 'this title'} from what you liked`}
                >
                  <CloseIcon className="size-3.5" />
                </button>
              </li>
            )
          })}
          {likes.length > COVERS && (
            <li>
              <button
                type="button"
                onClick={showAll}
                className="grid aspect-[225/320] w-[56px] place-content-center justify-items-center gap-1 border-[1.5px] border-dashed border-line hover:border-pen sm:w-[74px]"
                aria-label={`Show all ${likes.length} liked titles`}
              >
                <b className="font-display text-xl sm:text-2xl">
                  +{likes.length - COVERS}
                </b>
                <span className="code text-[0.56rem] text-dim">all liked</span>
              </button>
            </li>
          )}
        </ul>
      )}
    </section>
  )
}

/**
 * The search field that adds a liked title.
 *
 * Not a combobox: a search field over a list of buttons, which Tab already reaches.
 */
function TitleSearch({ placeholder }: { placeholder: string }) {
  const { mark } = useRecommend()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const { term, hits, searching } = useTitleSearch(query)

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [])

  return (
    <div ref={box} className="relative w-full max-w-[19rem]">
      <label htmlFor="title-search" className="sr-only">
        Add a title you liked
      </label>
      <input
        id="title-search"
        type="search"
        autoComplete="off"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => event.key === 'Escape' && setOpen(false)}
        placeholder={placeholder}
        className="w-full border-0 bg-cell px-3 py-2 text-base text-cell-ink placeholder:text-cell-sub"
      />
      <p aria-live="polite" className="sr-only">
        {searching ? 'Searching' : `${hits.length} matches`}
      </p>
      {open && hits.length > 0 && (
        <ul
          aria-label="Matching titles"
          className="absolute z-30 mt-px w-full border border-line bg-panel"
        >
          {hits.map((hit) => (
            <li key={hit.id} className="border-b border-line last:border-b-0">
              <button
                type="button"
                onClick={() => {
                  setQuery('')
                  setOpen(false)
                  mark({ id: hit.id, title: hit.title, image_url: hit.image_url }, 'like')
                }}
                className="flex w-full items-baseline gap-3 px-3 py-2 text-left hover:bg-ground"
              >
                <span className="min-w-0 flex-1">
                  <span lang="ja-Latn" className="block truncate">
                    {hit.title}
                  </span>
                  {hit.english && (
                    <span className="block truncate text-sm text-dim">{hit.english}</span>
                  )}
                </span>
                {hit.author && (
                  <span className="max-w-[40%] shrink-0 truncate text-xs text-dim">
                    {hit.author}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && term.length >= 2 && !searching && hits.length === 0 && (
        <p className="absolute z-30 mt-px w-full border border-line bg-panel px-3 py-2 text-dim">
          No title matches “{term}”. Try a shorter part of it.
        </p>
      )}
    </div>
  )
}
