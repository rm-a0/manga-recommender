import { CodeLedger } from '@/components/CodeLedger'
import { OrderTabs } from '@/components/OrderTabs'
import type { MangaStatus, TagMatch, TagSummary } from '@/lib/types'

const STATUSES: { value: MangaStatus; label: string }[] = [
  { value: 'ongoing', label: 'Running' },
  { value: 'finished', label: 'Complete' },
  { value: 'hiatus', label: 'On hiatus' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'not_released_yet', label: 'Announced' },
]

export interface FilterState {
  q: string
  status: string[]
  includeTag: string[]
  excludeTag: string[]
  tagMatch: TagMatch
  sort: string
  order: string
  showSealed: boolean
}

/**
 * The hall's tools, as a GET form.
 *
 * Submitting writes the query string the page already reads, so a filtered hall
 * is shareable and survives the back button. The two controls that change what
 * the page is rather than narrowing it — the ordering and the seal — submit as
 * soon as they change; everything else waits for the button.
 */
export function FilterForm({
  tags,
  state,
  sealedCount,
}: {
  tags: TagSummary[]
  state: FilterState
  sealedCount: number
}) {
  const activeCodes = state.includeTag.length + state.excludeTag.length

  return (
    <form method="GET" action="/browse" className="mb-5">
      <div className="flex flex-wrap items-center gap-2">
        <input
          id="q"
          name="q"
          type="search"
          defaultValue={state.q}
          minLength={2}
          placeholder="Search the hall — romaji title"
          aria-label="Search the hall by title"
          className="min-w-[13rem] flex-1 border-0 bg-cell px-3 py-2 text-base text-cell-ink placeholder:text-cell-sub"
        />
        <button
          type="submit"
          className="bg-spot px-4 py-2 font-display text-base uppercase tracking-[0.04em] text-white transition-opacity hover:opacity-90"
        >
          Set the hall
        </button>
      </div>

      <OrderTabs selected={`${state.sort}:${state.order}`} />

      <fieldset className="mt-3.5">
        <legend className="code text-dim">Status</legend>
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1.5">
          {STATUSES.map((option) => (
            <label key={option.value} className="flex items-center gap-1.5 text-base">
              <input
                type="checkbox"
                name="status"
                value={option.value}
                defaultChecked={state.status.includes(option.value)}
                className="size-4"
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>

      <details className="mt-3.5" open={activeCodes > 0}>
        <summary className="code cursor-pointer text-dim transition-colors hover:text-text">
          Codes
          {activeCodes > 0
            ? ` · ${state.includeTag.length} required, ${state.excludeTag.length} barred`
            : ` · ${tags.length} in use`}
        </summary>

        <div className="mt-2.5">
          <p className="mb-2 max-w-[70ch] text-sm text-dim">
            Select a code once to require it, again to bar it, a third time to clear it.
          </p>
          <CodeLedger
            tags={tags}
            include={state.includeTag}
            exclude={state.excludeTag}
            match={state.tagMatch}
            showSealed={state.showSealed}
            sealedCount={sealedCount}
          />
        </div>
      </details>
    </form>
  )
}
