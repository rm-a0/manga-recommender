import Link from 'next/link'
import { Suspense } from 'react'

import { HallGrid, HallSkeleton } from '@/components/HallGrid'
import { SectionHead } from '@/components/SectionHead'
import { SurveyStrip } from '@/components/SurveyStrip'
import { TagRequirements } from '@/components/TagRequirements'
import { getManga, listManga } from '@/lib/api'
import { LIVE_ROUTE, PLANNED_ROUTES, resolveSharedTags } from '@/lib/routes'
import type { TagMatch } from '@/lib/types'

function asArray(value: string | string[] | undefined): string[] {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}

/** The hall's newest entries, shown before the reader has ringed anything. */
async function InTheHall() {
  const page = await listManga({ limit: 14, sort: 'published_date', order: 'desc' })

  return (
    <>
      <SectionHead
        title="Hall listing"
        meta={`${page.total.toLocaleString('en')} entries · newest first`}
      />
      <HallGrid items={page.items} />
      <p className="mt-5 text-base text-dim">
        This is the hall, not a recommendation.{' '}
        <Link href="/browse" className="text-text underline">
          Open the full catalogue
        </Link>{' '}
        to filter and order it.
      </p>
    </>
  )
}

async function RouteResults({
  seedIds,
  tags,
  match,
}: {
  seedIds: string[]
  tags: string[]
  match: TagMatch
}) {
  const result = await resolveSharedTags(seedIds, { tags, match, limit: 30 })

  if (result.seeds.length === 0) {
    return (
      <p className="border-t border-line py-6 text-base text-dim">
        None of those entries are in the hall any more.
      </p>
    )
  }

  if (result.availableTags.length === 0) {
    return (
      <>
        <SectionHead title="Shared codes" meta="nothing to match on" />
        <p className="py-6 text-base text-dim">
          The catalogue records no codes for the entries you ringed, so this route has
          nothing to work from.
        </p>
      </>
    )
  }

  return (
    <>
      <section className="mb-9">
        <SectionHead title="Your marks" meta={`${result.seeds.length} ringed`} />
        <HallGrid items={result.seeds} ringedIds={result.seeds.map((s) => s.id)} />
      </section>

      <SectionHead
        title="Shared codes"
        meta={
          result.items.length > 0
            ? `${result.items.length} shown · A–Z, not ranked`
            : 'no matches'
        }
      />

      <TagRequirements
        seedIds={seedIds}
        available={result.availableTags}
        active={result.activeTags}
        match={result.match}
        total={result.total}
      />

      {result.items.length > 0 ? (
        <>
          <HallGrid items={result.items} />
          <p className="mt-5 max-w-[70ch] text-base text-dim">
            Listed alphabetically. Nothing here is scored or ordered by how well it
            matches — you chose the codes, the hall returned what carries them.
          </p>
        </>
      ) : (
        <p className="py-6 text-base text-dim">
          Nothing else in the hall carries {result.match === 'all' ? 'all of' : 'any of'}{' '}
          these codes. Drop one, or switch to matching any of them.
        </p>
      )}
    </>
  )
}

export default async function Page(props: PageProps<'/'>) {
  const searchParams = await props.searchParams
  const seedIds = asArray(searchParams.seed)
  const tags = asArray(searchParams.tag)
  const match: TagMatch = searchParams.match === 'any' ? 'any' : 'all'

  // Resolve the ringed titles for the chips. Cheap: one request per named title.
  const seeds = (
    await Promise.all(
      seedIds.map(async (id) => {
        const manga = await getManga(id)
        return manga ? { id: manga.id, title: manga.title } : null
      }),
    )
  ).filter((seed): seed is { id: string; title: string } => seed !== null)

  return (
    <div className="mx-auto max-w-[1080px] px-5 pb-16 pt-7 sm:px-8">
      <SurveyStrip seeds={seeds} />

      {seedIds.length === 0 && (
        <p className="mt-5 max-w-[62ch] text-base text-dim">
          <span className="font-display text-lg uppercase tracking-[0.02em] text-text">
            {LIVE_ROUTE.name}
          </span>{' '}
          is the only route built so far. Ring a title above and it runs against it.
        </p>
      )}

      <div className="mt-8">
        {seedIds.length === 0 ? (
          <Suspense fallback={<HallSkeleton />}>
            <InTheHall />
          </Suspense>
        ) : (
          <Suspense
            key={`${seedIds.join(',')}|${tags.join(',')}|${match}`}
            fallback={<HallSkeleton />}
          >
            <RouteResults seedIds={seedIds} tags={tags} match={match} />
          </Suspense>
        )}
      </div>

      {/* The catalogue's back matter: what is coming, stated plainly and never
          dressed as something you can use today. */}
      <section className="mt-14" aria-labelledby="next-issue-heading">
        <h2 id="next-issue-heading" className="code hall-rule pb-1.5 text-dim">
          Next edition — routes not built yet
        </h2>
        <ul className="mt-3 grid gap-x-8 gap-y-2 sm:grid-cols-2">
          {PLANNED_ROUTES.map((route) => (
            <li key={route.id} className="text-base text-dim">
              <span className="font-display uppercase tracking-[0.02em] text-text">
                {route.name}
              </span>
              <br />
              {route.description}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
