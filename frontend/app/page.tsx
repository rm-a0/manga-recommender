import { Suspense } from 'react'

import { HallSkeleton } from '@/components/HallGrid'
import { Hero } from '@/components/recommend/Hero'
import { Notice } from '@/components/recommend/Notice'
import { Piles } from '@/components/recommend/Piles'
import { PicksHall } from '@/components/recommend/PicksHall'
import { RecommendProvider } from '@/components/recommend/RecommendProvider'
import type { TitleStub } from '@/components/recommend/RecommendProvider'
import { SideEntry } from '@/components/recommend/SideEntry'
import { TuneButton, TuneDrawer } from '@/components/recommend/TuneDrawer'
import { SectionHead } from '@/components/SectionHead'
import { getManga, listAllTags, listManga, listStrategies, recommend } from '@/lib/api'
import { GENRE_SEAL, unsealed } from '@/lib/explicit'
import { parseQuery, toRequest } from '@/lib/recommend'
import type { RecommendQuery } from '@/lib/recommend'

/** The engine's picks for the reader's marks, in the order it returned them. */
async function Picks({ query }: { query: RecommendQuery }) {
  const result = await recommend(toRequest(query, GENRE_SEAL))

  if (!result.seeds.length) {
    return (
      <p className="border-t border-line py-6 text-dim">
        None of the titles you liked are in the catalogue any more. Add another one above.
      </p>
    )
  }
  if (!result.recommendations.length) {
    return (
      <>
        <SectionHead title="Your picks" meta="none left" />
        <p className="max-w-[62ch] py-6 text-dim">
          Nothing is left after your marks and skipped codes. Take a title off Not for me
          or Already read, or skip fewer codes.
        </p>
      </>
    )
  }
  return (
    <>
      <SectionHead
        title="Your picks"
        meta={`${result.recommendations.length} · engine order`}
      />
      <PicksHall items={result.recommendations} seeds={result.seeds} />
    </>
  )
}

/** Before anything is liked: the most-read titles, as a place to start. Not picks. */
async function MostRead() {
  const page = await listManga({ limit: 21, sort: 'popularity', order: 'desc' })
  return (
    <>
      <SectionHead title="Most read in the hall" meta="not picks · open one you liked" />
      <PicksHall
        items={page.items.map((manga) => ({ manga, reasons: [] }))}
        ranked={false}
      />
    </>
  )
}

export default async function Page(props: PageProps<'/'>) {
  const query = parseQuery(await props.searchParams)
  const marked = [...query.marks.like, ...query.marks.dislike, ...query.marks.read]

  // Titles for the piles and the headline. One request per marked title.
  const [strategies, tags, stubs] = await Promise.all([
    listStrategies(),
    listAllTags(),
    Promise.all(
      marked.map(async (id): Promise<TitleStub | null> => {
        const manga = await getManga(id)
        return manga
          ? { id: manga.id, title: manga.title, image_url: manga.image_url }
          : null
      }),
    ),
  ])

  return (
    <RecommendProvider
      query={query}
      strategies={strategies}
      initialTitles={stubs.filter((stub): stub is TitleStub => stub !== null)}
      codes={unsealed(tags, false).map((tag) => tag.name)}
    >
      <div className="mx-auto max-w-[1320px] px-5 pb-16 sm:px-8">
        <Hero tools={<TuneButton />} />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_260px]">
          <div>
            <Suspense fallback={<HallSkeleton cells={14} />}>
              {query.marks.like.length ? <Picks query={query} /> : <MostRead />}
            </Suspense>
          </div>
          <Piles tools={<TuneButton />} />
        </div>
      </div>
      <SideEntry />
      <TuneDrawer />
      <Notice />
    </RecommendProvider>
  )
}
