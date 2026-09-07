'use client'

import { useState } from 'react'

import { SEALED_WORK_TAGS, barredCodeLimit } from '@/lib/explicit'
import { MAX_TAG_FILTERS } from '@/lib/types'
import type { TagMatch, TagSummary } from '@/lib/types'

/** What a code is doing in the current filter. */
type CodeState = 'off' | 'required' | 'barred'

/** Clicking a code walks these in order and back to the start. */
const NEXT: Record<CodeState, CodeState> = {
  off: 'required',
  required: 'barred',
  barred: 'off',
}

/** What each state announces, and what a further click will do to it. */
const STATE_TEXT: Record<CodeState, string> = {
  off: 'not filtered, select to require',
  required: 'required, select to bar',
  barred: 'barred, select to clear',
}

/**
 * How each state paints the box.
 *
 * The empty box is bordered in `dim`, not in `line`. `line` is the hairline for
 * structure and reads at 1.25:1 on the panel; a control's own boundary has to
 * clear 3:1, which `dim` does at 4.99:1.
 */
const BOX_STATE: Record<CodeState, string> = {
  off: 'border-dim bg-panel group-hover:border-text',
  required: 'border-spot bg-spot',
  barred: 'border-spot-on-ground bg-cell-ink',
}

/**
 * A single tri-state box: empty, a tick on spot red, or a red cross struck into
 * the ink. Drawn rather than a native checkbox, which holds two states only.
 */
function Box({ state }: { state: CodeState }) {
  return (
    <span
      aria-hidden="true"
      className={`flex size-[15px] shrink-0 items-center justify-center border transition-colors ${BOX_STATE[state]}`}
    >
      {state === 'required' && (
        <svg viewBox="0 0 12 12" className="size-[11px]">
          <path
            d="M2 6.4 4.6 9 10 3.2"
            fill="none"
            stroke="#fff"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
      {state === 'barred' && (
        <svg viewBox="0 0 12 12" className="size-[11px] text-spot-on-ground">
          <path
            d="M2.6 2.6 9.4 9.4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.9"
            strokeLinecap="round"
          />
        </svg>
      )}
    </span>
  )
}

/**
 * The code ledger: every code in the vocabulary, each required, barred or
 * neither.
 *
 * One column of three states rather than two columns of two, because a code
 * cannot be required and barred at once and a control that lets you tick both
 * has to define which one wins. Clicking a code walks the three.
 *
 * The chosen codes leave as hidden inputs on the filter form, so the state lands
 * in the query string and a filtered hall stays shareable. Only codes in the
 * vocabulary passed in are emitted, so re-sealing the explicit codes drops the
 * filters that named them rather than sending a code the picker no longer shows.
 */
export function CodeLedger({
  tags,
  include,
  exclude,
  match,
  showSealed,
  sealedCount,
}: {
  tags: TagSummary[]
  include: string[]
  exclude: string[]
  match: TagMatch
  showSealed: boolean
  /** How many codes the seal is holding back from this vocabulary. */
  sealedCount: number
}) {
  const [state, setState] = useState<Record<string, CodeState>>(() => {
    const initial: Record<string, CodeState> = {}
    for (const name of include) initial[name] = 'required'
    for (const name of exclude) initial[name] = 'barred'
    return initial
  })

  const required = tags.filter((tag) => state[tag.name] === 'required').map((tag) => tag.name)
  const barred = tags.filter((tag) => state[tag.name] === 'barred').map((tag) => tag.name)

  const maxBarred = barredCodeLimit(showSealed)

  /** Return true when the API has no room left for one more code in that state. */
  function isFull(current: Record<string, CodeState>, wanted: CodeState): boolean {
    const used = tags.filter((tag) => current[tag.name] === wanted).length
    if (wanted === 'required') return used >= MAX_TAG_FILTERS
    if (wanted === 'barred') return used >= maxBarred
    return false
  }

  function cycle(name: string) {
    setState((previous) => {
      // Walk to the next state the API has room for. `off` is always reachable,
      // so this stops within one full turn of the three.
      let next = NEXT[previous[name] ?? 'off']
      while (isFull(previous, next)) next = NEXT[next]
      return { ...previous, [name]: next }
    })
  }

  return (
    <div>
      {required.map((name) => (
        <input key={`in-${name}`} type="hidden" name="include_tag" value={name} />
      ))}
      {barred.map((name) => (
        <input key={`ex-${name}`} type="hidden" name="exclude_tag" value={name} />
      ))}

      {required.length > 1 && (
        <div className="mb-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
          <span className="code text-dim">A title must carry</span>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="tag_match"
              value="any"
              defaultChecked={match === 'any'}
              className="size-4"
            />
            Any of them
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="tag_match"
              value="all"
              defaultChecked={match === 'all'}
              className="size-4"
            />
            All of them
          </label>
        </div>
      )}

      <ul className="grid max-h-64 grid-cols-2 gap-x-5 gap-y-0.5 overflow-y-auto border border-line p-2 sm:grid-cols-3 lg:grid-cols-4">
        {tags.map((tag) => {
          const current = state[tag.name] ?? 'off'
          return (
            <li key={tag.id}>
              <button
                type="button"
                onClick={() => cycle(tag.name)}
                className="group flex w-full items-center gap-2 py-1.5 text-left text-[0.92rem]"
              >
                <Box state={current} />
                <span
                  className={`truncate transition-colors ${
                    current === 'barred'
                      ? 'text-dim line-through decoration-spot-on-ground'
                      : current === 'required'
                        ? 'text-text'
                        : 'text-dim group-hover:text-text'
                  }`}
                >
                  {tag.name}
                </span>
                <span className="sr-only"> — {STATE_TEXT[current]}</span>
              </button>
            </li>
          )
        })}
      </ul>

      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1.5">
        <p className="code text-dim">
          {required.length} required · {barred.length} barred
          {required.length >= MAX_TAG_FILTERS && ' · required is full'}
          {barred.length >= maxBarred && ' · barred is full'}
        </p>

        {/*
          The seal, stated where the codes it holds back would have been. It is a
          checkbox on the form like any other filter, so breaking it travels in
          the URL with everything else.
        */}
        <label className="code flex cursor-pointer items-center gap-2 text-dim transition-colors hover:text-text">
          <input
            type="checkbox"
            name="explicit"
            value="1"
            defaultChecked={showSealed}
            onChange={(event) => event.currentTarget.form?.requestSubmit()}
            className="size-4"
          />
          {showSealed
            ? `Explicit codes shown — ${SEALED_WORK_TAGS.join(', ')}`
            : `${sealedCount} explicit ${sealedCount === 1 ? 'code' : 'codes'} withheld — show them`}
        </label>
      </div>
    </div>
  )
}
