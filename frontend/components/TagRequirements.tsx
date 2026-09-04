import Link from 'next/link'

import type { TagMatch } from '@/lib/types'

/**
 * The codes this listing requires, as toggles.
 *
 * Rendered as links rather than a client form: each chip is the same page with
 * one code added or removed, so the state is the URL, it works without
 * JavaScript, and the back button walks the reader's choices.
 *
 * The reader picks which codes matter. Nothing here weighs one against another
 * — that judgement belongs to the recommendation engine, which does not exist.
 */
export function TagRequirements({
  seedIds,
  available,
  active,
  match,
  total,
}: {
  seedIds: string[]
  available: string[]
  active: string[]
  match: TagMatch
  total: number
}) {
  function href(nextTags: string[], nextMatch: TagMatch = match): string {
    const params = new URLSearchParams()
    for (const id of seedIds) params.append('seed', id)
    for (const tag of nextTags) params.append('tag', tag)
    if (nextMatch !== 'all') params.set('match', nextMatch)
    return `/?${params}`
  }

  return (
    <div className="mb-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <p className="code text-dim">Require</p>
        <div className="code flex items-baseline gap-1.5">
          <Link
            href={href(active, 'all')}
            aria-current={match === 'all' ? 'true' : undefined}
            className={`no-underline ${match === 'all' ? 'text-spot-on-ground underline' : 'text-dim'}`}
          >
            all
          </Link>
          <span className="text-dim">/</span>
          <Link
            href={href(active, 'any')}
            aria-current={match === 'any' ? 'true' : undefined}
            className={`no-underline ${match === 'any' ? 'text-spot-on-ground underline' : 'text-dim'}`}
          >
            any
          </Link>
        </div>
        <p className="code ml-auto text-dim">{total.toLocaleString('en')} in the hall</p>
      </div>

      <ul className="mt-2 flex flex-wrap gap-1.5">
        {available.map((tag) => {
          const on = active.includes(tag)
          const next = on ? active.filter((t) => t !== tag) : [...active, tag]
          return (
            <li key={tag}>
              {/*
                A link, not a button: state lives in the URL. aria-pressed is
                defined for role="button" only, so the state travels in the
                accessible name instead.
              */}
              <Link
                href={href(next)}
                className={`code block border px-2 py-1 no-underline transition-colors ${
                  on
                    ? 'border-spot bg-spot text-white'
                    : 'border-line text-dim hover:border-dim hover:text-text'
                }`}
              >
                {tag}
                <span className="sr-only">
                  {on ? ' — required, select to drop' : ' — not required, select to add'}
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
