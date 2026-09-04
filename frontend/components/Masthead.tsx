import Link from 'next/link'

import { listAllTags, listManga } from '@/lib/api'

const NAV = [
  { href: '/', label: 'Discover' },
  { href: '/browse', label: 'Catalogue' },
  { href: '/tags', label: 'Codes' },
]

/** Read the counts the strip prints. Never let them take the page down. */
async function counts(): Promise<{ titles: number; tags: number } | null> {
  try {
    const [page, tags] = await Promise.all([listManga({ limit: 1 }), listAllTags()])
    return { titles: page.total, tags: tags.length }
  } catch {
    // The strip is chrome. If the API is asleep the page still prints.
    return null
  }
}

/**
 * The catalogue's cover: the masthead printed on paper, then a mono strip of
 * the hall's vital statistics on the stock beneath it.
 */
export async function Masthead() {
  const stats = await counts()

  return (
    <header>
      <div className="on-cell border-b-4 border-spot">
        <div className="mx-auto flex max-w-[1080px] items-center gap-3 px-5 py-2.5 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5 no-underline">
            <span aria-hidden="true" className="text-[1.7rem] leading-none text-spot-on-cell">
              推
            </span>
            <span className="font-display text-[1.7rem] uppercase leading-none tracking-[0.01em] text-cell-ink">
              MangaRec
            </span>
          </Link>

          <nav aria-label="Sections" className="ml-auto flex flex-wrap gap-x-4 gap-y-1">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="code text-cell-sub no-underline transition-colors hover:text-cell-ink"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      <div className="flex flex-wrap border-b border-line bg-panel">
        {[
          ['Hall', 'A–P'],
          ['Entries', stats ? stats.titles.toLocaleString('en') : '—'],
          ['Codes', stats ? String(stats.tags) : '—'],
        ].map(([k, v]) => (
          <div key={k} className="code border-r border-line px-3.5 py-1.5 text-dim">
            {k} <b className="font-semibold text-cell">{v}</b>
          </div>
        ))}
      </div>
    </header>
  )
}
