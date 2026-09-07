import { Suspense } from 'react'

import { FilterForm, type FilterState } from '@/components/FilterForm'
import { Pagination } from '@/components/Pagination'
import { HallGrid, HallSkeleton } from '@/components/HallGrid'
import { SectionHead } from '@/components/SectionHead'
import { listAllTags, listManga } from '@/lib/api'
import { barredCodeLimit, unsealed } from '@/lib/explicit'
import {
  DEFAULT_ORDERING,
  METRIC_SORTS,
  ORDER_LABEL,
  VALID_SORTS,
} from '@/lib/ordering'
import { MAX_TAG_FILTERS } from '@/lib/types'
import type { MangaSort, MangaStatus, SortOrder, TagMatch } from '@/lib/types'

const PAGE_SIZE = 35

type Query = Record<string, string | string[] | undefined>

function asArray(value: string | string[] | undefined): string[] {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}

function readState(query: Query): FilterState {
  // The order control submits one field as `field:direction`.
  const [rawSort, rawOrder] = (
    typeof query.sort === 'string' ? query.sort : DEFAULT_ORDERING
  ).split(':')

  const showSealed = query.explicit === '1'
  const barred = asArray(query.exclude_tag)
  // A code cannot be both. Barring wins, because it is the stricter instruction
  // and because a request carrying a code on both lists returns nothing at all.
  const required = asArray(query.include_tag).filter((tag) => !barred.includes(tag))

  return {
    q: typeof query.q === 'string' ? query.q : '',
    status: asArray(query.status),
    includeTag: required.slice(0, MAX_TAG_FILTERS),
    excludeTag: barred.slice(0, barredCodeLimit(showSealed)),
    tagMatch: query.tag_match === 'all' ? 'all' : 'any',
    sort: VALID_SORTS.includes(rawSort as MangaSort) ? rawSort : 'popularity',
    order: rawOrder === 'asc' ? 'asc' : 'desc',
    showSealed,
  }
}

function buildQuery(state: FilterState, offset: number): string {
  const params = new URLSearchParams()
  if (state.q) params.set('q', state.q)
  for (const value of state.status) params.append('status', value)
  for (const value of state.includeTag) params.append('include_tag', value)
  for (const value of state.excludeTag) params.append('exclude_tag', value)
  if (state.includeTag.length > 1) params.set('tag_match', state.tagMatch)
  params.set('sort', `${state.sort}:${state.order}`)
  if (state.showSealed) params.set('explicit', '1')
  if (offset > 0) params.set('offset', String(offset))
  return params.toString()
}

async function Results({ state, offset }: { state: FilterState; offset: number }) {
  const page = await listManga(
    {
      q: state.q.length >= 2 ? state.q : undefined,
      status: state.status as MangaStatus[],
      include_tag: state.includeTag,
      exclude_tag: state.excludeTag,
      tag_match: state.tagMatch as TagMatch,
      sort: state.sort as MangaSort,
      order: state.order as SortOrder,
      limit: PAGE_SIZE,
      offset,
    },
    { showSealed: state.showSealed },
  )

  const ordering = `${state.sort}:${state.order}`
  const orderLabel = ORDER_LABEL[ordering] ?? ordering

  if (page.total === 0) {
    return (
      <>
        <SectionHead title="Hall listing" meta="no matches" />
        <div className="border-b border-line py-8">
          <p className="max-w-[70ch] text-sm text-dim">
            Nothing in the catalogue matches these filters.
            {state.q && ' Title search matches romaji only, so an English title finds nothing.'}
            {state.excludeTag.length > 0 &&
              ` ${state.excludeTag.length === 1 ? 'One code is' : `${state.excludeTag.length} codes are`} barred — dropping one widens the hall.`}
          </p>
        </div>
      </>
    )
  }

  return (
    <>
      <SectionHead
        title="Hall listing"
        meta={`${page.total.toLocaleString('en')} titles · ${orderLabel}`}
      />
      <HallGrid items={page.items} />
      {METRIC_SORTS.includes(state.sort as MangaSort) && (
        <p className="mt-5 max-w-[70ch] text-base text-dim">
          Ordered by the catalogue&rsquo;s own figures. A title needs at least a hundred
          ratings to carry a score, so the rest of the hall sorts to the end.
        </p>
      )}
      <Pagination
        total={page.total}
        limit={PAGE_SIZE}
        offset={offset}
        buildHref={(next) => {
          const query = buildQuery(state, next)
          return query ? `/browse?${query}` : '/browse'
        }}
      />
    </>
  )
}

export default async function BrowsePage(props: PageProps<'/browse'>) {
  const query = (await props.searchParams) as Query
  const state = readState(query)
  const offset = Math.max(0, Number(query.offset ?? 0) || 0)

  // Read the whole vocabulary once, then split it, so the ledger can say how
  // many codes the seal is holding rather than only that it is holding some.
  const allTags = await listAllTags({ showSealed: true })
  const tags = unsealed(allTags, state.showSealed)

  return (
    <div className="mx-auto max-w-[1080px] px-5 pb-16 pt-7 sm:px-8">
      <h1 className="mb-4 font-display text-4xl uppercase leading-[0.9] tracking-[-0.02em] sm:text-5xl">
        The hall
      </h1>
      <FilterForm
        tags={tags}
        state={state}
        sealedCount={allTags.length - tags.length}
      />
      <div className="mt-8">
        <Suspense key={buildQuery(state, offset)} fallback={<HallSkeleton cells={15} />}>
          <Results state={state} offset={offset} />
        </Suspense>
      </div>
    </div>
  )
}
