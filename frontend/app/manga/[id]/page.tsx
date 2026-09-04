import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { Suspense } from 'react'

import { Cover } from '@/components/Cover'
import { HallGrid } from '@/components/HallGrid'
import { SectionHead } from '@/components/SectionHead'
import { getManga } from '@/lib/api'
import { resolveSharedTags } from '@/lib/routes'

const STATUS_LABEL: Record<string, string> = {
  ongoing: 'Still running',
  finished: 'Complete',
  hiatus: 'On hiatus',
  cancelled: 'Cancelled',
  not_released_yet: 'Announced',
}

/** Format the publication date. The stored time is always midnight, so it is dropped. */
function publicationDate(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

export async function generateMetadata(props: PageProps<'/manga/[id]'>): Promise<Metadata> {
  const { id } = await props.params
  const manga = await getManga(id)
  if (!manga) return { title: 'Not in the catalogue — MangaRec' }
  return {
    title: `${manga.title} — MangaRec`,
    description: manga.description?.slice(0, 160) ?? undefined,
  }
}

async function AlsoCarrying({ id, title }: { id: string; title: string }) {
  const { items, activeTags } = await resolveSharedTags([id], { limit: 10 })
  if (items.length === 0) return null

  return (
    <section className="mt-12">
      <SectionHead title="Also coded this way" meta="listed A–Z, not ranked" />
      <p className="border-b border-line py-3 max-w-[70ch] text-sm text-dim">
        Every title below carries {activeTags.join(', ')} — tags recorded for {title}.
        This is a catalogue filter, not a ranked recommendation.{' '}
        <Link href={`/?seed=${id}`} className="text-text underline">
          Choose the tags yourself
        </Link>
        .
      </p>
      <HallGrid items={items} />
    </section>
  )
}

export default async function MangaPage(props: PageProps<'/manga/[id]'>) {
  const { id } = await props.params
  const manga = await getManga(id)
  if (!manga) notFound()

  const published = publicationDate(manga.published_date)
  const status = manga.status ? STATUS_LABEL[manga.status] : null

  return (
    <article className="mx-auto max-w-5xl px-5 pb-16 pt-8 sm:px-8">
      <div className="flex flex-col gap-6 sm:flex-row sm:gap-8">
        <Cover url={manga.image_url} title={manga.title} width={200} priority />

        <div className="min-w-0 flex-1">
          <h1 className="font-display text-4xl leading-[0.95] tracking-[-0.02em] sm:text-5xl">
            {manga.title}
          </h1>

          <p className="mt-3 text-base">
            {manga.authors.length > 0 ? (
              manga.authors.map((author, index) => (
                <span key={author.id}>
                  {index > 0 && <span className="text-dim"> · </span>}
                  <Link href={`/authors/${author.id}`} className="underline">
                    {author.name}
                  </Link>
                </span>
              ))
            ) : (
              <span className="text-dim">Author unrecorded</span>
            )}
          </p>

          <dl className="border-t border-line mt-4 flex flex-wrap gap-x-8 gap-y-2 pt-3 text-sm">
            {status && (
              <div>
                <dt className="font-display text-xs uppercase tracking-[0.08em] text-dim">
                  Status
                </dt>
                <dd className="text-dim">{status}</dd>
              </div>
            )}
            <div>
              <dt className="font-display text-xs uppercase tracking-[0.08em] text-dim">
                First published
              </dt>
              <dd>{published ?? <span className="text-dim">Not recorded</span>}</dd>
            </div>
          </dl>

          {manga.tags.length > 0 && (
            <div className="mt-5">
              <h2 className="font-display text-xs uppercase tracking-[0.08em] text-dim">
                Tags
              </h2>
              <ul className="mt-1.5 flex flex-wrap gap-1.5">
                {manga.tags.map((tag) => (
                  <li key={tag.id}>
                    <Link
                      href={`/browse?include_tag=${encodeURIComponent(tag.name)}&tag_match=any&sort=published_date:desc`}
                      className="block border border-line px-2 py-0.5 text-sm no-underline transition-colors hover:bg-spot hover:text-white hover:border-line"
                    >
                      {tag.name}
                      {tag.is_spoiler && (
                        <span className="ml-1 text-xs text-spot-on-ground">spoiler</span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Link
            href={`/?seed=${manga.id}`}
            className="mt-6 inline-block bg-spot text-white px-5 py-2.5 font-display text-base uppercase tracking-[0.04em] no-underline transition-opacity hover:opacity-85"
          >
            Use as a starting point
          </Link>
        </div>
      </div>

      <section className="mt-10 max-w-[68ch]">
        <h2 className="font-display text-xs uppercase tracking-[0.08em] text-dim">
          Synopsis
        </h2>
        {manga.description ? (
          <div className="mt-2 space-y-3 text-base leading-relaxed">
            {manga.description.split(/\n{2,}/).map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-dim">
            The catalogue holds no synopsis for this title. Roughly three in ten entries
            arrive without one.
          </p>
        )}
      </section>

      <Suspense fallback={null}>
        <AlsoCarrying id={manga.id} title={manga.title} />
      </Suspense>
    </article>
  )
}
