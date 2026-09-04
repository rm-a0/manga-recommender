/**
 * A biro ring — the reader's own mark on an entry they named.
 *
 * One continuous stroke that closes past where it started, the way a pen
 * actually rings something. Drawn rather than approximated with a border
 * radius, which reads as a wobbly rectangle at any size.
 *
 * It stretches to the cell, so `preserveAspectRatio` is off deliberately: a
 * real pen loop follows the shape of what it is ringing.
 */
export function PenMark({ label }: { label?: string }) {
  return (
    <svg
      viewBox="0 0 104 78"
      preserveAspectRatio="none"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className="pointer-events-none absolute -inset-y-1.5 -inset-x-1 h-[calc(100%+0.75rem)] w-[calc(100%+0.5rem)] text-pen mix-blend-multiply"
    >
      <path
        d="M56 6C81 5 98 19 99 37c1 19-17 34-45 35C26 73 6 60 5 41 4 23 22 8 50 6c16-1 30 3 38 11"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
    </svg>
  )
}
