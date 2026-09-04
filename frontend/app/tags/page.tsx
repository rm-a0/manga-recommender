import type { Metadata } from 'next'
import Link from 'next/link'

import { SectionHead } from '@/components/SectionHead'
import { listAllTags } from '@/lib/api'

export const metadata: Metadata = {
  title: 'Tags — MangaRec',
  description: 'The whole tag vocabulary the catalogue records.',
}

export default async function TagsPage() {
  const tags = await listAllTags()

  return (
    <div className="mx-auto max-w-5xl px-5 pb-16 pt-8 sm:px-8">
      <SectionHead as="h1" title="Tags" meta={`${tags.length} in the vocabulary`} />

      <p className="border-b border-line py-3 max-w-[70ch] text-sm text-dim">
        Every tag the catalogue records. The vocabulary is closed and small enough to read
        in one sitting, which is why this page has no search.
      </p>

      <ul className="mt-6 grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3 lg:grid-cols-4">
        {tags.map((tag) => (
          <li key={tag.id} className="border-b border-line">
            <Link
              href={`/browse?include_tag=${encodeURIComponent(tag.name)}&tag_match=any&sort=published_date:desc`}
              className="block py-1.5 font-display text-base uppercase tracking-[0.01em] no-underline transition-colors hover:text-spot-on-ground"
            >
              {tag.name}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
