import Link from 'next/link'

const STEP =
  'border border-line px-3 py-2 font-display text-sm uppercase tracking-[0.04em] no-underline transition-colors hover:border-spot hover:text-spot-on-ground'

const EDGE = 'code text-dim no-underline transition-colors hover:text-spot-on-ground'

/**
 * Offset pagination over the catalogue.
 *
 * Rendered as links so a page is shareable and the browser can prefetch it. The
 * endpoint returns `total`, so both ends are known rather than guessed — which
 * matters here, where a listing runs to two thousand pages and stepping is not a
 * way to reach the end of one.
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
  const last = (pages - 1) * limit

  return (
    <nav
      className="mt-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-t border-line pt-4"
      aria-label="Pages"
    >
      <div className="flex items-center gap-3">
        {page > 2 && (
          <Link href={buildHref(0)} className={EDGE}>
            First
          </Link>
        )}
        {previous >= 0 ? (
          <Link href={buildHref(previous)} rel="prev" className={STEP}>
            ← Previous
          </Link>
        ) : (
          <span aria-hidden="true" />
        )}
      </div>

      <p className="code text-dim">
        Page {page.toLocaleString('en')} of {pages.toLocaleString('en')}
      </p>

      <div className="flex items-center gap-3">
        {next < total ? (
          <Link href={buildHref(next)} rel="next" className={STEP}>
            Next →
          </Link>
        ) : (
          <span aria-hidden="true" />
        )}
        {page < pages - 1 && (
          <Link href={buildHref(last)} className={EDGE}>
            Last
          </Link>
        )}
      </div>
    </nav>
  )
}
