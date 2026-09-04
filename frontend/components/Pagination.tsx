import Link from 'next/link'

/**
 * Offset pagination over the catalogue.
 *
 * Rendered as links so a page is shareable and the browser can prefetch it. The
 * endpoint returns `total`, so the last page is known rather than guessed.
 */
export function Pagination({
  total,
  limit,
  offset,
  buildHref,
}: {
  total: number
  limit: number
  offset: number
  buildHref: (offset: number) => string
}) {
  const page = Math.floor(offset / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))
  if (pages <= 1) return null

  const previous = offset - limit
  const next = offset + limit

  return (
    <nav className="mt-6 flex items-center justify-between gap-4 border-t border-line pt-4" aria-label="Pages">
      {previous >= 0 ? (
        <Link
          href={buildHref(previous)}
          rel="prev"
          className="border border-line px-4 py-2 font-display text-sm uppercase tracking-[0.04em] no-underline transition-colors hover:border-spot hover:text-spot-on-ground"
        >
          ← Previous
        </Link>
      ) : (
        <span aria-hidden="true" />
      )}

      <p className="code text-dim">
        Page {page.toLocaleString('en')} of {pages.toLocaleString('en')}
      </p>

      {next < total ? (
        <Link
          href={buildHref(next)}
          rel="next"
          className="border border-line px-4 py-2 font-display text-sm uppercase tracking-[0.04em] no-underline transition-colors hover:border-spot hover:text-spot-on-ground"
        >
          Next →
        </Link>
      ) : (
        <span aria-hidden="true" />
      )}
    </nav>
  )
}
