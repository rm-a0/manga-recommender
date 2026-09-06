/**
 * A hall heading: display type over the spot rule.
 *
 * `meta` sits on the same line and carries counts and the active ordering, so
 * the reader never has to infer what ordered the listing beneath it.
 */
export function SectionHead({
  title,
  meta,
  as: Tag = 'h2',
}: {
  title: string
  meta?: React.ReactNode
  as?: 'h1' | 'h2'
}) {
  return (
    <div className="hall-rule mb-3.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 pb-1.5">
      <Tag className="font-display text-xl uppercase leading-none tracking-[0.02em] sm:text-2xl">
        {title}
      </Tag>
      {meta && <p className="code text-dim">{meta}</p>}
    </div>
  )
}
