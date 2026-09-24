'use client'

import Image from 'next/image'
import { Fragment, useEffect, useRef, useState } from 'react'

import { largeCover } from '@/lib/covers'
import type { MangaSummary, RecommendationReason, RecommendationSeed } from '@/lib/types'
import { Figures, HALL_GRID } from '../HallGrid'
import { EntrySheet } from './EntrySheet'
import { useFinePointer } from './hooks'
import { PILE_STAMP, useRecommend } from './RecommendProvider'

export interface HallItem {
  manga: MangaSummary
  reasons: RecommendationReason[]
}


/**
 * What changed since the previous run: titles that arrived, and how far the
 * rest moved. Held in state and adjusted during render when the list changes,
 * so it needs no effect.
 */
function useRunDiff(ids: string[]) {
  const key = ids.join(',')
  const [state, setState] = useState<{
    key: string
    previous: string[] | null
    current: string[]
  }>({ key, previous: null, current: ids })
  if (state.key !== key) setState({ key, previous: state.current, current: ids })
  const before = state.key === key ? state.previous : state.current
  if (!before) return { added: new Set<string>(), moved: new Map<string, number>() }
  const was = new Map(before.map((id, i) => [id, i]))
  const added = new Set<string>()
  const moved = new Map<string, number>()
  ids.forEach((id, i) => {
    const previous = was.get(id)
    if (previous === undefined) added.add(id)
    else if (previous !== i) moved.set(id, previous - i)
  })
  return { added, moved }
}

/** Columns the grid is laid out in right now, so an opened sheet lands after its row. */
function useColumns(ref: React.RefObject<HTMLUListElement | null>) {
  const [columns, setColumns] = useState(6)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () =>
      setColumns(
        getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length || 1,
      )
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref])
  return columns
}

/**
 * The hall of picks, in the engine's order.
 *
 * Every cell opens its entry in place; on phones the entry is a bottom sheet.
 * Cells can be dragged onto a pile where there is a real pointer. Titles the
 * last run brought in carry a red flag, because the engine put them there.
 */
export function PicksHall({
  items,
  seeds = [],
  ranked = true,
}: {
  items: HallItem[]
  seeds?: RecommendationSeed[]
  ranked?: boolean
}) {
  const { pending, open: opened, openWhere, setOpen, busy } = useRecommend()
  const open = openWhere === 'inline' ? opened : null
  const grid = useRef<HTMLUListElement>(null)
  const columns = useColumns(grid)
  const fine = useFinePointer()
  const diff = useRunDiff(ranked ? items.map((x) => x.manga.id) : [])

  const at = items.findIndex((x) => x.manga.id === open)
  const sheetAfter =
    at >= 0
      ? Math.min(items.length - 1, Math.floor(at / columns) * columns + columns - 1)
      : -1

  return (
    <ul
      ref={grid}
      className={`${HALL_GRID} [grid-auto-flow:row_dense] transition-opacity ${busy ? 'opacity-60' : ''}`}
      aria-busy={busy}
    >
      {items.map((x, i) => {
        const m = x.manga
        const mark = pending[m.id]
        const moved = diff.moved.get(m.id)
        const src = largeCover(m.image_url)
        return (
          <Fragment key={m.id}>
            <li
              className="paste-in relative flex"
              style={{ '--cell-index': i % 30 } as React.CSSProperties}
            >
              {ranked && (
                <span className="absolute -top-2 -left-2 z-10 border border-line bg-ground px-1.5 py-0.5 code text-[0.64rem] text-dim">
                  {i + 1}
                </span>
              )}
              {moved ? (
                <span
                  className={`absolute -top-2 -right-2 z-10 border border-line bg-ground px-1 py-0.5 code text-[0.6rem] ${moved > 0 ? 'text-[#9fd3a8]' : 'text-dim'}`}
                >
                  <span aria-hidden="true">{moved > 0 ? '▲' : '▼'}</span>
                  {Math.abs(moved)}
                  <span className="sr-only"> places {moved > 0 ? 'up' : 'down'}</span>
                </span>
              ) : null}
              <button
                type="button"
                aria-expanded={open === m.id}
                aria-label={`${m.title}${ranked ? `, pick ${i + 1}` : ''}`}
                draggable={fine || undefined}
                onDragStart={(event) => {
                  event.dataTransfer.setData(
                    'application/x-manga',
                    JSON.stringify({ id: m.id, title: m.title, image_url: m.image_url }),
                  )
                  event.dataTransfer.effectAllowed = 'move'
                }}
                onClick={() => setOpen(open === m.id ? null : m.id)}
                className={`group flex w-full flex-col bg-cell p-2 pb-2.5 text-left text-cell-ink transition-shadow hover:shadow-[0_0_0_2px_var(--color-spot)] aria-expanded:shadow-[0_0_0_2px_var(--color-spot)] ${fine ? 'cursor-grab' : ''} ${mark !== undefined ? 'is-marked' : ''}`}
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
                    <span className="flex aspect-[225/320] w-full items-center justify-center bg-[#d9d4c5] p-2 text-center font-display text-sm leading-tight text-cell-sub uppercase">
                      {m.title.slice(0, 28)}
                    </span>
                  )}
                  {mark && <span className="stamp">{PILE_STAMP[mark]}</span>}
                  {diff.added.has(m.id) && (
                    <span className="absolute bottom-1.5 left-1.5 z-10 bg-spot px-1.5 py-1 code text-[0.6rem] leading-none text-white">
                      New
                    </span>
                  )}
                </span>
                <Figures manga={m} />
                <span
                  className="mt-1.5 line-clamp-2 min-h-[2.5em] text-[0.9rem] leading-[1.25] font-medium group-hover:underline"
                  lang="ja-Latn"
                >
                  {m.title}
                </span>
              </button>
            </li>
            {i === sheetAfter && open && (
              <>
                <li className="pick-sheet col-span-full">
                  <EntrySheet
                    manga={items[at].manga}
                    reasons={items[at].reasons}
                    rank={ranked ? at : undefined}
                    seeds={seeds}
                    onClose={() => setOpen(null)}
                  />
                </li>
                <li
                  className="pick-scrim"
                  aria-hidden="true"
                  onClick={() => setOpen(null)}
                />
              </>
            )}
          </Fragment>
        )
      })}
    </ul>
  )
}
