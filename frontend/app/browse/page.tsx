import { Suspense } from 'react'

import { FilterForm, type FilterState } from '@/components/FilterForm'
import { Pagination } from '@/components/Pagination'
import { HallGrid, HallSkeleton } from '@/components/HallGrid'
import { SectionHead } from '@/components/SectionHead'
import { listAllTags, listManga } from '@/lib/api'
import type { MangaSort, MangaStatus, SortOrder, TagMatch } from '@/lib/types'

const PAGE_SIZE = 35
const VALID_SORTS: MangaSort[] = ['title', 'published_date']

type Query = Record<string, string | string[] | undefined>

function asArray(value: string | string[] | undefined): string[] {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}

function readState(query: Query): FilterState {
  // The sort control submits one field as `field:direction`.
  const [rawSort, rawOrder] = (
    typeof query.sort === 'string' ? query.sort : 'published_date:desc'
  ).split(':')

  return {
    q: typeof query.q === 'string' ? query.q : '',
    status: asArray(query.status),
    includeTag: asArray(query.include_tag).slice(0, 10),
    tagMatch: query.tag_match === 'all' ? 'all' : 'any',
    sort: VALID_SORTS.includes(rawSort as MangaSort) ? rawSort : 'published_date',
    order: rawOrder === 'asc' ? 'asc' : 'desc',
    allowAdult: query.adult === '1',
  }
}

function buildQuery(state: FilterState, offset: number): string {
  const params = new URLSearchParams()
  if (state.q) params.set('q', state.q)
  for (const value of state.status) params.append('status', value)
  for (const value of state.includeTag) params.append('include_tag', value)
  if (state.includeTag.length > 0) params.set('tag_match', state.tagMatch)
  params.set('sort', `${state.sort}:${state.order}`)
  if (state.allowAdult) params.set('adult', '1')
  if (offset > 0) params.set('offset', String(offset))
  return params.toString()
}

async function Results({ state, offset }: { state: FilterState; offset: number }) {
  const page = await listManga(
    {
      q: state.q.length >= 2 ? state.q : undefined,
      status: state.status as MangaStatus[],
      include_tag: state.includeTag,
      tag_match: state.tagMatch as TagMatch,
      sort: state.sort as MangaSort,
      order: state.order as SortOrder,
      limit: PAGE_SIZE,
      offset,
    },
    { allowAdult: state.allowAdult },
  )

  const orderLabel =
    state.sort === 'title'
      ? `title ${state.order === 'asc' ? 'A–Z' : 'Z–A'}`
      : `${state.order === 'desc' ? 'newest' : 'oldest'} first`

  if (page.total === 0) {
    return (
      <>
        <SectionHead title="Hall listing" meta="no matches" />
        <div className="border-b border-line py-8">
          <p className="text-sm text-dim">
            Nothing in the catalogue matches these filters.
            {state.q && ' Title search matches romaji only, so an English title finds nothing.'}
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
      <HallGrid items={page.items} offset={offset} />
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
  const tags = await listAllTags()

  return (
    <div className="mx-auto max-w-[1080px] px-5 pb-16 pt-7 sm:px-8">
      <h1 className="mb-4 font-display text-4xl uppercase leading-[0.9] tracking-[-0.02em] sm:text-5xl">
        The hall
      </h1>
      <FilterForm tags={tags} state={state} />
      <div className="mt-8">
        <Suspense key={buildQuery(state, offset)} fallback={<HallSkeleton cells={15} />}>
          <Results state={state} offset={offset} />
        </Suspense>
      </div>
    </div>
  )
}
