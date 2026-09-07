import Link from 'next/link'
import Image from 'next/image'

import { largeCover } from '@/lib/covers'
import { formatScore, formatVotes, formatVotesShort, scoreOutOfTen } from '@/lib/score'
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
          <span className="mt-1.5 block h-0.5 w-full bg-[#d9d4c5]" />
          <span className="mt-1.5 block h-[2.5em] w-full bg-[#d9d4c5]" />
        </li>
      ))}
    </ul>
  )
}

/**
 * The figures under a cover: the weighted score, then how many readers scored it.
 *
 * Both are real fields off the metrics row, tied by a dotted leader the way a
 * contents page ties an entry to its page number.
 *
 * The figures are printed, never drawn as a measure. Half the catalogue scores
 * between 6.79 and 7.07, which is 2.8% of a bar's width and invisible in a grid,
 * while `6.8` and `7.1` are two glyphs apart. The digits carry the difference
 * here; the spot rule under them is furniture.
 */
/**
 * The rule that closes a cell's figures, in the press ink.
 *
 * The same object as the rule under a hall heading, at cell scale: the page's
 * own move, so a cell reads as a miniature of the page it sits on. It measures
 * nothing and is drawn on every cell, rated or not — which is what keeps the
 * hall even and stops the mark reading as a badge some titles won.
 */
function CellRule() {
  return <span aria-hidden="true" className="mt-1.5 block h-0.5 bg-spot" />
}

function Figures({ manga }: { manga: MangaSummary }) {
  const score = scoreOutOfTen(manga.metrics)

  if (!manga.metrics || score === null) {
    return (
      <>
        <span className="code mt-2 block text-cell-sub">Not rated</span>
        <CellRule />
      </>
    )
  }

  return (
    <>
      <span className="code mt-2 flex items-baseline gap-1.5">
        <span aria-hidden="true" className="text-spot-on-cell">
          {formatScore(score)}
        </span>
        <span
          aria-hidden="true"
          className="-translate-y-[0.18em] flex-1 border-b border-dotted border-cell-sub/55"
        />
        <span aria-hidden="true" className="text-cell-sub">
          {formatVotesShort(manga.metrics.votes_count)}
        </span>
        <span className="sr-only">
          Weighted score {formatScore(score)} out of 10, from{' '}
          {formatVotes(manga.metrics.votes_count)} ratings.
        </span>
      </span>
      <CellRule />
    </>
  )
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

        <Figures manga={manga} />

        {/*
          Exactly two lines, always. `line-clamp-2` caps a long title; the
          min-height stops a short one from making its cell shorter than its
          neighbours. No `block` here on purpose — it overrides the
          `display: -webkit-box` that line-clamp needs, and the clamp then
          silently stops working.
        */}
        <span className="mt-1.5 line-clamp-2 min-h-[2.5em] text-[0.9rem] font-medium leading-[1.25] text-cell-ink group-hover:underline">
          {manga.title}
        </span>
      </Link>
    </li>
  )
}

/**
 * The hall listing: every entry as a cell with its figures.
 *
 * Entries the reader named are ringed in pen. Cell order is the order the API
 * returned, under the ordering the listing's own heading names.
 */
export function HallGrid({
  items,
  ringedIds = [],
}: {
  items: MangaSummary[]
  ringedIds?: string[]
}) {
  const ringed = new Set(ringedIds)

  return (
    <ul className={HALL_GRID}>
      {items.map((manga, index) => (
        <Cell key={manga.id} manga={manga} index={index} ringed={ringed.has(manga.id)} />
      ))}
    </ul>
  )
}
