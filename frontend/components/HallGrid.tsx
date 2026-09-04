import Link from 'next/link'
import Image from 'next/image'

import { largeCover } from '@/lib/covers'
import type { MangaSummary } from '@/lib/types'
import { PenMark } from './PenMark'

/**
 * Grid template for a hall listing.
 *
 * 132px minimum lands seven cells across the 1080px container and three on a
 * phone. auto-fill picks the column count from (container + gap) / (min + gap),
 * so changing the minimum is how the density is tuned.
 */
export const HALL_GRID =
  'grid grid-cols-3 gap-3 sm:grid-cols-[repeat(auto-fill,minmax(132px,1fr))]'

/**
 * The hall's shape before its entries arrive.
 *
 * Same grid and same cell proportions as the real listing, so the page does not
 * reflow when the data lands. Hidden from assistive tech: it carries no content.
 */
export function HallSkeleton({ cells = 14 }: { cells?: number }) {
  return (
    <ul className={HALL_GRID} aria-hidden="true">
      {Array.from({ length: cells }).map((_, index) => (
        <li key={index} className="bg-cell p-2 pb-2.5">
          <span className="block aspect-[225/320] w-full bg-[#d9d4c5]" />
          <span className="mt-2 block h-3 w-1/3 bg-[#d9d4c5]" />
          <span className="mt-1.5 block h-[2.5em] w-full bg-[#d9d4c5]" />
        </li>
      ))}
    </ul>
  )
}

/**
 * A table code for an entry's position in the hall: A-01, B-04.
 *
 * Derived from the entry's index in the current listing, so it is a coordinate
 * in what you are looking at — never an identifier and never a rank.
 */
export function hallCode(index: number): string {
  return `${String.fromCharCode(65 + (Math.floor(index / 5) % 26))}-${(index % 5) + 1}`
}

function Cell({
  manga,
  index,
  ringed,
}: {
  manga: MangaSummary
  index: number
  ringed: boolean
}) {
  const src = largeCover(manga.image_url)

  return (
    <li className="paste-in" style={{ '--cell-index': index % 30 } as React.CSSProperties}>
      <Link
        href={`/manga/${manga.id}`}
        className="group flex h-full flex-col bg-cell p-2 pb-2.5 no-underline transition-shadow hover:shadow-[0_0_0_2px_var(--color-spot)]"
      >
        <span className="relative block">
          {src ? (
            <Image
              src={src}
              alt=""
              width={150}
              height={213}
              sizes="(max-width: 640px) 31vw, 150px"
              className="aspect-[225/320] w-full object-cover"
            />
          ) : (
            <span className="flex aspect-[225/320] w-full items-center justify-center bg-[#d9d4c5] p-2 text-center font-display text-sm uppercase leading-tight text-cell-sub">
              {manga.title.slice(0, 28)}
            </span>
          )}
          {ringed && <PenMark label="You named this title" />}
        </span>

        <span className="code mt-2 block text-spot-on-cell">{hallCode(index)}</span>

        {/*
          Exactly two lines, always. `line-clamp-2` caps a long title; the
          min-height stops a short one from making its cell shorter than its
          neighbours. No `block` here on purpose — it overrides the
          `display: -webkit-box` that line-clamp needs, and the clamp then
          silently stops working.
        */}
        <span className="mt-0.5 line-clamp-2 min-h-[2.5em] text-[0.9rem] font-medium leading-[1.25] text-cell-ink group-hover:underline">
          {manga.title}
        </span>
      </Link>
    </li>
  )
}

/**
 * The hall listing: every entry as a cell with its table code.
 *
 * Entries the reader named are ringed in pen. Cell order is the order the API
 * returned; the codes are coordinates in that listing, not a ranking.
 */
export function HallGrid({
  items,
  offset = 0,
  ringedIds = [],
}: {
  items: MangaSummary[]
  offset?: number
  ringedIds?: string[]
}) {
  const ringed = new Set(ringedIds)

  return (
    <ul className={HALL_GRID}>
      {items.map((manga, index) => (
        <Cell
          key={manga.id}
          manga={manga}
          index={offset + index}
          ringed={ringed.has(manga.id)}
        />
      ))}
    </ul>
  )
}
