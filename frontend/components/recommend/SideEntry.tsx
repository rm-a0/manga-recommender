'use client'

import { useEffect, useRef } from 'react'

import { EntrySheet, useDetail } from './EntrySheet'
import { CloseIcon } from './icons'
import { PILE_NAMES, useRecommend } from './RecommendProvider'

/**
 * A title opened from a pile, in a sidebar from the right; full screen on phones.
 *
 * Pile titles are not in the picks grid, so they cannot open in place. The
 * sidebar is a modal dialog: it holds focus until closed.
 */
export function SideEntry() {
  const { open, openWhere, setOpen, effective } = useRecommend()
  const id = openWhere === 'side' ? open : null
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = dialog.current
    if (!el) return
    if (id && !el.open) el.showModal()
    if (!id && el.open) el.close()
  }, [id])

  return (
    <dialog
      ref={dialog}
      onClose={() => setOpen(null)}
      onClick={(event) => {
        if (event.target === event.currentTarget) setOpen(null)
      }}
      aria-labelledby="side-entry-title"
      className="side-drawer"
    >
      {id && <SideBody id={id} pile={effective(id)} onClose={() => setOpen(null)} />}
    </dialog>
  )
}

function SideBody({
  id,
  pile,
  onClose,
}: {
  id: string
  pile: ReturnType<ReturnType<typeof useRecommend>['effective']>
  onClose: () => void
}) {
  const detail = useDetail(id)
  return (
    <div className="grid h-full grid-rows-[auto_minmax(0,1fr)]">
      <header className="flex items-start justify-between gap-3 border-b-[3px] border-spot bg-cell px-[18px] pt-3 pb-2.5 text-cell-ink">
        <div>
          <h2
            id="side-entry-title"
            className="font-display text-[1.35rem] leading-none tracking-[0.02em] uppercase"
          >
            {pile ? PILE_NAMES[pile] : 'Title'}
          </h2>
          <p className="mt-0.5 text-[0.82rem] text-cell-sub">
            {pile
              ? 'In your pile. Mark it differently, or take it off.'
              : 'Not in your current picks.'}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="grid size-[30px] shrink-0 place-items-center border border-[#cbc5b5] hover:border-cell-ink"
        >
          <CloseIcon className="size-4" />
        </button>
      </header>
      <div className="overflow-auto overscroll-contain p-4">
        {detail ? (
          <EntrySheet manga={detail} narrow onClose={onClose} />
        ) : (
          <p className="text-dim">Loading…</p>
        )}
      </div>
    </div>
  )
}
