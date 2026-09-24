'use client'

import Image from 'next/image'
import { useState } from 'react'

import { largeCover } from '@/lib/covers'
import type { Pile } from '@/lib/recommend'
import { PenMark } from '../PenMark'
import { CloseIcon, MARK_ICONS } from './icons'
import { PILE_NAMES, PILES, pileMembers, useRecommend } from './RecommendProvider'
import type { TitleStub } from './RecommendProvider'

const PILE_SAYS: Record<Pile, string> = {
  like: 'Every pick is drawn from these.',
  dislike: 'Kept out, with titles close to them.',
  read: 'Kept out. Nothing else moves.',
}
/** Stamps shown per pile before the rest are counted. */
const CAP = 8

/**
 * The reader's three piles: what they liked, what is not for them, what they
 * have read. Picks are dropped here, or marked from their entry.
 *
 * A column on wide screens; on phones a tray pinned to the bottom edge, whose
 * one bar opens the piles as a sheet.
 */
export function Piles({ tools }: { tools?: React.ReactNode }) {
  const { pilesOpen, setPilesOpen } = useRecommend()
  return (
    <>
      <aside
        id="piles"
        aria-label="Your piles"
        className={`piles grid content-start gap-3 lg:sticky lg:top-3 lg:max-h-[calc(100dvh-24px)] lg:self-start lg:overflow-auto ${pilesOpen ? 'piles-open' : ''}`}
        role={pilesOpen ? 'dialog' : undefined}
      >
        <div className="piles-sheet-head hidden items-center justify-between border-b-2 border-spot pb-2">
          <h2 className="font-display text-xl tracking-[0.02em] uppercase">Your piles</h2>
          <button
            type="button"
            onClick={() => setPilesOpen(false)}
            className="flex items-center gap-1.5 border border-line px-2.5 py-1.5 code"
          >
            <CloseIcon className="size-3.5" />
            Close
          </button>
        </div>
        {tools && <div className="piles-tools">{tools}</div>}
        {PILES.map((pile) => (
          <PileZone key={pile} pile={pile} />
        ))}
        <UpdateButton className="piles-update" />
      </aside>
      <Tray tools={tools} />
      {pilesOpen && (
        <div
          className="piles-scrim"
          aria-hidden="true"
          onClick={() => setPilesOpen(false)}
        />
      )}
    </>
  )
}

function PileZone({ pile }: { pile: Pile }) {
  const { query, pending, titles, mark, take, setOpen, setPilesOpen } = useRecommend()
  const [over, setOver] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const members = pileMembers(query, pending, pile)
  const shown = expanded
    ? members
    : members.slice(0, members.length > CAP ? CAP - 1 : CAP)
  const rest = members.length - shown.length
  const Icon = MARK_ICONS[pile]

  return (
    <section
      aria-labelledby={`pile-${pile}`}
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes('application/x-manga')) {
          event.preventDefault()
          setOver(true)
        }
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node)) setOver(false)
      }}
      onDrop={(event) => {
        event.preventDefault()
        setOver(false)
        const data = event.dataTransfer.getData('application/x-manga')
        if (data) mark(JSON.parse(data) as TitleStub, pile)
      }}
      className={`border border-line bg-panel transition-[box-shadow,background-color] ${over ? 'bg-[#1f2f35] shadow-[inset_0_0_0_2px_var(--color-pen)]' : ''}`}
    >
      <div className="grid grid-cols-[22px_1fr_auto] items-center gap-x-2 gap-y-px border-b border-line px-2.5 pt-2.5 pb-2">
        <Icon className="text-pen-on-ground row-span-2 size-[18px]" />
        <h3
          id={`pile-${pile}`}
          className="font-display text-[1.02rem] leading-none tracking-[0.03em] uppercase"
        >
          {PILE_NAMES[pile]}
        </h3>
        <span className="code text-dim">{members.length}</span>
        <p className="col-span-2 text-[0.74rem] leading-tight text-dim">
          {PILE_SAYS[pile]}
        </p>
      </div>
      <div className="flex min-h-16 flex-wrap gap-2 p-2.5">
        {members.length === 0 && (
          <span className="self-center text-[0.8rem] text-dim">
            {pile === 'like'
              ? 'Search above, or drag a pick here.'
              : 'Drag a pick here, or open one and mark it.'}
          </span>
        )}
        {shown.map(({ id, pending: waiting }) => {
          const stub = titles[id]
          const src = largeCover(stub?.image_url ?? null)
          return (
            <div
              key={id}
              className="group relative w-11"
              title={`${stub?.title ?? 'Title'}${waiting ? ' — waiting for Update picks' : ''}`}
            >
              <button
                type="button"
                onClick={() => {
                  setPilesOpen(false)
                  setOpen(id, 'side')
                }}
                aria-label={stub?.title ?? 'Open this title'}
                className={`relative block aspect-[225/320] w-full bg-[#d9d4c5] ${waiting ? 'shadow-[0_0_0_2px_var(--color-pen)]' : 'shadow-[0_0_0_2px_var(--color-cell)]'}`}
              >
                {src && (
                  <Image
                    src={src}
                    alt=""
                    width={44}
                    height={63}
                    sizes="44px"
                    className="h-full w-full object-cover"
                  />
                )}
                {pile === 'like' && <PenMark />}
              </button>
              <button
                type="button"
                onClick={() => take(id)}
                aria-label={`Take ${stub?.title ?? 'this title'} off ${PILE_NAMES[pile]}`}
                className="absolute -top-2 -right-2 z-10 hidden size-[18px] place-items-center border border-line bg-ground text-dim group-focus-within:grid group-hover:grid"
              >
                <CloseIcon className="size-2.5" />
              </button>
            </div>
          )
        })}
        {rest > 0 && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            aria-label={`Show all ${members.length}`}
            className="grid aspect-[225/320] w-11 place-items-center border-[1.5px] border-dashed border-line font-display text-[1.05rem] hover:border-pen"
          >
            +{rest}
          </button>
        )}
        {expanded && members.length > CAP && (
          <button
            type="button"
            onClick={() => setExpanded(false)}
            className="self-center code text-[0.66rem] text-dim underline"
          >
            Fewer
          </button>
        )}
      </div>
    </section>
  )
}

function UpdateButton({ className = '' }: { className?: string }) {
  const { pendingCount, update } = useRecommend()
  return (
    <button
      type="button"
      onClick={update}
      disabled={!pendingCount}
      className={`flex w-full items-center justify-between gap-2.5 bg-spot p-2.5 text-left text-white disabled:cursor-default disabled:border disabled:border-dashed disabled:border-line disabled:bg-transparent disabled:text-dim ${className}`}
    >
      <b className="font-display text-[1.05rem] font-normal tracking-[0.03em] uppercase">
        Update picks
      </b>
      <span className="code text-[0.66rem]">
        {pendingCount
          ? `${pendingCount} mark${pendingCount > 1 ? 's' : ''} waiting`
          : 'Mark a pick first'}
      </span>
    </button>
  )
}

/** Phones: one bar saying what is in the piles, and the actions that apply them. */
function Tray({ tools }: { tools?: React.ReactNode }) {
  const { query, pending, pilesOpen, setPilesOpen, pendingCount, update } = useRecommend()
  const count = (pile: Pile) => pileMembers(query, pending, pile).length
  return (
    <nav
      aria-label="Your piles"
      className="tray fixed inset-x-0 bottom-0 z-[38] hidden grid-cols-[minmax(0,1fr)_auto_auto] border-t-[3px] border-spot bg-cell text-cell-ink"
    >
      <button
        type="button"
        onClick={() => setPilesOpen(!pilesOpen)}
        aria-expanded={pilesOpen}
        className="flex min-w-0 items-center gap-2.5 px-3.5 py-2.5 text-left"
      >
        <span className="grid min-w-0 flex-1 gap-0.5">
          <b className="font-display text-[1.05rem] leading-none font-normal tracking-[0.03em] uppercase">
            Your piles
          </b>
          <span className="truncate code text-[0.6rem] text-cell-sub">
            {count('like')} liked · {count('dislike')} not for me · {count('read')} read
          </span>
        </span>
        <span className="border border-[#cbc5b5] px-2 py-1 code text-[0.64rem]">
          {pilesOpen ? 'Close' : 'Open'}
        </span>
      </button>
      {tools && <span className="tray-tools grid">{tools}</span>}
      <button
        type="button"
        onClick={update}
        disabled={!pendingCount}
        className="bg-spot px-4 font-display tracking-[0.03em] text-white uppercase disabled:bg-[#d9d4c5] disabled:text-cell-sub"
      >
        {pendingCount ? `Update · ${pendingCount}` : 'Update'}
      </button>
    </nav>
  )
}
