'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useEffect, useState } from 'react'

import { largeCover } from '@/lib/covers'
import { formatScore, scoreOutOfTen } from '@/lib/score'
import { englishAlias, MANGA_STATUS_LABEL, MANGA_TYPE_LABEL } from '@/lib/titles'
import { sourceCopy } from '@/lib/tuning'
import type { Pile } from '@/lib/recommend'
import type {
  MangaDetail,
  MangaSummary,
  RecommendationReason,
  RecommendationSeed,
} from '@/lib/types'
import { CloseIcon, MARK_ICONS } from './icons'
import { PILE_NAMES, PILE_STAMP, useRecommend } from './RecommendProvider'

const PILE_SAYS: Record<Pile, string> = {
  like: 'Every pick is measured from the titles you liked.',
  dislike: 'Kept out, with titles close to it.',
  read: 'Kept out. Nothing else moves.',
}

// Details already fetched this session, so reopening a pick is instant.
const details = new Map<string, MangaDetail>()

/** Fetch one title's detail through the route handler. `null` while loading. */
export function useDetail(id: string) {
  const [state, setState] = useState<{ id: string; detail: MangaDetail | null }>(() => ({
    id,
    detail: details.get(id) ?? null,
  }))
  useEffect(() => {
    if (details.has(id)) return
    const controller = new AbortController()
    fetch(`/api/manga/${id}`, { signal: controller.signal })
      .then((r) => (r.ok ? (r.json() as Promise<MangaDetail>) : null))
      .then((d) => {
        if (!d) return
        details.set(id, d)
        setState({ id, detail: d })
      })
      .catch(() => {})
    return () => controller.abort()
  }, [id])
  return state.id === id
    ? (state.detail ?? details.get(id) ?? null)
    : (details.get(id) ?? null)
}

/** Cut a synopsis at a sentence end under `max` characters. */
function clip(text: string, max = 520) {
  const flat = text.replace(/\s+/g, ' ').trim()
  if (flat.length <= max) return flat
  const cut = flat.slice(0, max)
  const end = Math.max(
    cut.lastIndexOf('. '),
    cut.lastIndexOf('! '),
    cut.lastIndexOf('? '),
  )
  return end > max * 0.5 ? cut.slice(0, end + 1) : `${cut.replace(/\s\S*$/, '')}…`
}

/**
 * One title opened: its marks first, then why it was picked and what it is.
 *
 * The marks sit beside the title so the reader never scrolls to answer; keys 1,
 * 2 and 3 press them while the sheet is open.
 */
export function EntrySheet({
  manga,
  reasons,
  rank,
  seeds = [],
  narrow = false,
  onClose,
}: {
  manga: MangaSummary
  reasons?: RecommendationReason[]
  rank?: number
  seeds?: RecommendationSeed[]
  /** In the sidebar: marks go under the title whatever the viewport width. */
  narrow?: boolean
  onClose: () => void
}) {
  const { effective, mark, query, pendingCount, update } = useRecommend()
  const detail = useDetail(manga.id)
  const pile = effective(manga.id)
  const isPick = Boolean(reasons?.length)
  const piles: Pile[] = isPick ? ['like', 'dislike', 'read'] : ['like', 'read']
  const stub = { id: manga.id, title: manga.title, image_url: manga.image_url }

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.target as HTMLElement).matches('input, textarea')) return
      if (event.key === 'Escape') onClose()
      const index = Number(event.key) - 1
      if (piles[index]) mark(stub, piles[index])
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  const score = scoreOutOfTen(manga.metrics)
  const alias = englishAlias(manga)
  const facts = [
    detail?.type ? MANGA_TYPE_LABEL[detail.type] : null,
    detail?.published_date?.slice(0, 4) ?? null,
    manga.status ? MANGA_STATUS_LABEL[manga.status] : null,
  ].filter(Boolean)
  const seedTitle = (id: string | null) => seeds.find((s) => s.id === id)?.title ?? null
  const from = [
    ...new Set((reasons ?? []).map((r) => seedTitle(r.seed_id)).filter(Boolean)),
  ]
  const sources = [...new Set((reasons ?? []).map((r) => sourceCopy(r.source).label))]

  let why: { head: string; body: React.ReactNode }
  if (isPick) {
    why = {
      head: sources.join(' + '),
      body: (
        <>
          from{' '}
          {from.map((t, i) => (
            <span key={t}>
              {i > 0 && ' and '}
              <i lang="ja-Latn" className="font-medium text-cell-ink not-italic">
                {t}
              </i>
            </span>
          ))}
          {rank != null && ` · #${rank + 1} in the engine's order`}
        </>
      ),
    }
  } else if (pile === 'like' && query.marks.like.includes(manga.id))
    why = { head: 'You liked this', body: PILE_SAYS.like }
  else if (pile) why = { head: PILE_NAMES[pile], body: PILE_SAYS[pile] }
  else
    why = {
      head: query.marks.like.length ? 'Not in your picks' : 'Most read',
      body: query.marks.like.length
        ? 'The engine did not pick it for your current titles.'
        : 'Not a pick. Ordered by readership.',
    }

  return (
    <article
      aria-label={manga.title}
      className="entry-sheet relative grid grid-cols-[84px_minmax(0,1fr)] gap-x-3.5 bg-cell p-3.5 text-cell-ink shadow-[0_0_0_2px_var(--color-spot)] sm:grid-cols-[150px_minmax(0,1fr)] sm:gap-x-5 sm:p-[18px]"
    >
      <div className="row-span-1 sm:row-span-3">
        <span className="relative block aspect-[225/320] bg-[#d9d4c5]">
          {largeCover(manga.image_url) && (
            <Image
              src={largeCover(manga.image_url)!}
              alt=""
              fill
              sizes="(max-width: 640px) 84px, 150px"
              className="object-cover"
            />
          )}
        </span>
      </div>
      <div
        className={`grid items-start gap-x-5 gap-y-3 ${narrow ? '' : 'lg:grid-cols-[minmax(0,1fr)_auto]'}`}
      >
        <div className={narrow ? 'pr-16' : 'pr-16 lg:pr-0'}>
          <h2
            className="font-display text-[1.35rem] leading-none tracking-[0.02em] [overflow-wrap:anywhere] uppercase sm:text-[1.9rem]"
            lang="ja-Latn"
          >
            {manga.title}
          </h2>
          {alias && <p className="mt-1 text-cell-sub">{alias}</p>}
          <p className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 code text-cell-sub">
            {manga.authors[0] && (
              <b className="font-semibold text-cell-ink">
                {manga.authors.map((a) => a.name).join(', ')}
              </b>
            )}
            {facts.map((f) => (
              <span key={f}>{f}</span>
            ))}
            {score !== null && manga.metrics ? (
              <span className="text-spot-on-cell">
                {formatScore(score)} / 10 ·{' '}
                {manga.metrics.votes_count.toLocaleString('en')} ratings
              </span>
            ) : (
              <span>Not rated</span>
            )}
          </p>
        </div>
        <div
          role="group"
          aria-label="Your mark"
          className={`entry-marks col-span-2 flex border border-[#cbc5b5] ${narrow ? '' : 'lg:col-span-1'}`}
        >
          {piles.map((p, i) => {
            const Icon = MARK_ICONS[p]
            const on = pile === p
            return (
              <button
                key={p}
                type="button"
                aria-pressed={on}
                onClick={() => mark(stub, p)}
                className="group grid min-w-0 flex-1 justify-items-center gap-1 border-r border-[#cbc5b5] px-3 pt-2.5 pb-2 text-center last:border-r-0 hover:bg-pen/10 aria-pressed:bg-pen aria-pressed:text-white lg:min-w-[92px]"
              >
                <Icon className="size-[22px] text-pen group-aria-pressed:text-white" />
                <b className="text-[0.82rem] leading-tight font-bold">
                  {on
                    ? `${PILE_STAMP[p]} · undo`
                    : !isPick && p === 'like'
                      ? 'I liked this'
                      : PILE_NAMES[p]}
                </b>
                <kbd className="font-mono text-[0.6rem] text-cell-sub group-aria-pressed:text-white">
                  {i + 1}
                </kbd>
              </button>
            )
          })}
        </div>
      </div>
      <div className="col-span-2 sm:col-span-1">
        <p className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-t-2 border-spot pt-2 code">
          <b className="font-display text-[1.1rem] font-normal">{why.head}</b>
          <span
            className="text-[0.88rem] tracking-normal text-cell-sub normal-case"
            style={{ fontFamily: 'var(--font-text)' }}
          >
            {why.body}
          </span>
        </p>
        {detail ? (
          <>
            {detail.description ? (
              <p className="mt-2.5 max-w-[70ch] text-[0.95rem] leading-relaxed">
                {clip(detail.description)}
              </p>
            ) : (
              <p className="mt-2.5 text-cell-sub">No synopsis recorded for this title.</p>
            )}
            <p className="mt-2 flex flex-wrap gap-x-2.5 gap-y-1 code text-[0.68rem] text-cell-sub">
              {detail.tags
                .filter((t) => !t.is_spoiler)
                .slice(0, 10)
                .map((t) => (
                  <span key={t.id}>{t.name}</span>
                ))}
            </p>
          </>
        ) : (
          <div aria-hidden="true" className="mt-3 grid gap-1.5">
            {[100, 94, 97, 60].map((w) => (
              <span
                key={w}
                className="block h-3 bg-[#d9d4c5]"
                style={{ width: `${w}%` }}
              />
            ))}
          </div>
        )}
        <Link
          href={`/manga/${manga.id}`}
          className="mt-3 inline-block code text-cell-ink underline decoration-spot"
        >
          Open the full entry
        </Link>
        {/* Phones: the tray is hidden under an open sheet, so the sheet carries Update itself. */}
        {pendingCount > 0 && (
          <button
            type="button"
            onClick={update}
            className="mt-3.5 flex w-full items-center justify-between bg-spot px-3 py-2.5 text-white md:hidden"
          >
            <b className="font-display font-normal tracking-[0.03em] uppercase">
              Update picks
            </b>
            <span className="code text-[0.66rem]">{pendingCount} waiting</span>
          </button>
        )}
      </div>
      <button
        type="button"
        onClick={onClose}
        className="absolute top-2.5 right-2.5 z-10 flex items-center gap-1 border border-[#cbc5b5] bg-cell px-2 py-1.5 code text-cell-sub hover:text-cell-ink"
      >
        <CloseIcon className="size-3.5" />
        Close
      </button>
    </article>
  )
}
