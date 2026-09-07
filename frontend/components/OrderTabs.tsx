'use client'

import { ORDERINGS } from '@/lib/ordering'

/**
 * The hall's ordering, as a printed index tab strip.
 *
 * Every ordering is a radio inside the filter form, so the choice submits with
 * the rest of it, lands in the query string and stays shareable. Changing a tab
 * submits the form immediately where scripting is available; where it is not,
 * the strip still works and the form's own button applies it.
 *
 * The chosen tab is printed on paper with a spot bar over it, which is how a
 * tabbed index marks the section you are in.
 */
export function OrderTabs({ selected }: { selected: string }) {
  return (
    <fieldset className="mt-3.5 flex flex-wrap items-end gap-x-0.5 gap-y-1 border-b border-line">
      {/*
        The legend names the group for assistive tech; the printed "Order" beside
        it is the same word set in the catalogue's voice, so it is hidden rather
        than announced twice.
      */}
      <legend className="sr-only">Order the hall</legend>
      <span aria-hidden="true" className="code self-center pr-3 text-dim">
        Order
      </span>

      {ORDERINGS.map((ordering) => (
        <label key={ordering.value} className="relative cursor-pointer">
          <input
            type="radio"
            name="sort"
            value={ordering.value}
            defaultChecked={ordering.value === selected}
            onChange={(event) => event.currentTarget.form?.requestSubmit()}
            className="peer sr-only"
          />
          <span className="code block px-3 py-1.5 text-dim transition-colors hover:text-text peer-checked:bg-cell peer-checked:text-cell-ink peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-spot-on-ground">
            {ordering.label}
          </span>
          {/* The tab marker. Printed over the paper, never under it. */}
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 top-0 h-[3px] bg-spot opacity-0 peer-checked:opacity-100"
          />
        </label>
      ))}
    </fieldset>
  )
}
