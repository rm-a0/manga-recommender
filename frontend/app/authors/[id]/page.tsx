import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { Pagination } from '@/components/Pagination'
import { HallGrid } from '@/components/HallGrid'
import { SectionHead } from '@/components/SectionHead'
import { getAuthor, listAuthorManga } from '@/lib/api'

const PAGE_SIZE = 25

export async function generateMetadata(props: PageProps<'/authors/[id]'>): Promise<Metadata> {
  const { id } = await props.params
  const author = await getAuthor(id)
  return { title: author ? `${author.name} — MangaRec` : 'Unknown author — MangaRec' }
}

export default async function AuthorPage(props: PageProps<'/authors/[id]'>) {
  const { id } = await props.params
  const searchParams = await props.searchParams
  const offset = Math.max(0, Number(searchParams.offset ?? 0) || 0)

  const author = await getAuthor(id)
  if (!author) notFound()

  const page = await listAuthorManga(id, { limit: PAGE_SIZE, offset })

  return (
    <div className="mx-auto max-w-5xl px-5 pb-16 pt-8 sm:px-8">
      <h1 className="font-display text-4xl leading-[0.95] tracking-[-0.02em] sm:text-5xl">
        {author.name}
      </h1>
      <p className="mt-2 text-sm text-dim">
        Credited on {author.manga_count.toLocaleString('en')}{' '}
        {author.manga_count === 1 ? 'title' : 'titles'} in the catalogue.
      </p>

      <div className="mt-8">
        <SectionHead title="Credits" meta="catalogue order" />
        {page.items.length > 0 ? (
          <>
            <HallGrid items={page.items} offset={offset} />
            <Pagination
              total={page.total}
              limit={PAGE_SIZE}
              offset={offset}
              buildHref={(next) => (next > 0 ? `/authors/${id}?offset=${next}` : `/authors/${id}`)}
            />
          </>
        ) : (
          <p className="border-b border-line py-8 text-sm text-dim">
            The catalogue records this author but credits them on nothing.
          </p>
        )}
      </div>
    </div>
  )
}
