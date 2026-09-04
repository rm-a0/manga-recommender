import type { MangaStatus, TagSummary } from '@/lib/types'

const STATUSES: { value: MangaStatus; label: string }[] = [
  { value: 'ongoing', label: 'Running' },
  { value: 'finished', label: 'Complete' },
  { value: 'hiatus', label: 'On hiatus' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'not_released_yet', label: 'Announced' },
]

const SORTS = [
  { value: 'published_date:desc', label: 'Newest first' },
  { value: 'published_date:asc', label: 'Oldest first' },
  { value: 'title:asc', label: 'Title A–Z' },
  { value: 'title:desc', label: 'Title Z–A' },
]

export interface FilterState {
  q: string
  status: string[]
  includeTag: string[]
  tagMatch: 'any' | 'all'
  sort: string
  order: string
  allowAdult: boolean
}

const FIELD =
  'border border-line bg-panel px-2.5 py-2 text-base text-text placeholder:text-dim'

/**
 * The hall's tools, as a plain GET form.
 *
 * No client JavaScript: submitting writes the query string the page already
 * reads, so a filtered hall is shareable, survives the back button, and works
 * before hydration. The code vocabulary is fetched once by the page.
 */
export function FilterForm({ tags, state }: { tags: TagSummary[]; state: FilterState }) {
  const selectedSort = `${state.sort}:${state.order}`
  const activeTagCount = state.includeTag.length

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

        {/* The stock select ships chrome that belongs to no design system. */}
        <div className="relative">
          <label htmlFor="sort" className="sr-only">
            Order the hall
          </label>
          <select
            id="sort"
            name="sort"
            defaultValue={selectedSort}
            className={`${FIELD} appearance-none pr-8`}
          >
            {SORTS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <svg
            viewBox="0 0 12 8"
            aria-hidden="true"
            className="pointer-events-none absolute right-2.5 top-1/2 h-2 w-3 -translate-y-1/2 text-dim"
          >
            <path d="M1 1.5 6 6.5 11 1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
          </svg>
        </div>

        <button
          type="submit"
          className="bg-spot px-4 py-2 font-display text-base uppercase tracking-[0.04em] text-white transition-opacity hover:opacity-90"
        >
          Set the hall
        </button>
      </div>

      <fieldset className="mt-3">
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

      <details className="mt-3" open={activeTagCount > 0}>
        <summary className="code cursor-pointer text-dim">
          Codes{activeTagCount > 0 ? ` · ${activeTagCount} required` : ` · ${tags.length} in use`}
        </summary>

        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-sm">
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="tag_match"
              value="any"
              defaultChecked={state.tagMatch === 'any'}
              className="size-4"
            />
            Any of them
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="tag_match"
              value="all"
              defaultChecked={state.tagMatch === 'all'}
              className="size-4"
            />
            All of them
          </label>
        </div>

        <div className="mt-2 grid max-h-56 grid-cols-2 gap-x-4 gap-y-1 overflow-y-auto border border-line p-2 sm:grid-cols-3 lg:grid-cols-4">
          {tags.map((tag) => (
            <label key={tag.id} className="flex items-center gap-1.5 text-base">
              <input
                type="checkbox"
                name="include_tag"
                value={tag.name}
                defaultChecked={state.includeTag.includes(tag.name)}
                className="size-4 shrink-0"
              />
              <span className="truncate">{tag.name}</span>
            </label>
          ))}
        </div>
        <p className="mt-1.5 text-xs text-dim">
          The endpoint accepts ten codes at most; extras beyond that are dropped.
        </p>
      </details>

      <label className="mt-3 flex items-center gap-2 text-sm text-dim">
        <input
          type="checkbox"
          name="adult"
          value="1"
          defaultChecked={state.allowAdult}
          className="size-4"
        />
        Include entries coded Hentai or Erotica
      </label>
    </form>
  )
}
