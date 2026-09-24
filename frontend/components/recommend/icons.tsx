/**
 * The recommend page's icons: one stroke weight, drawn on a 24-unit grid.
 *
 * The ring, strike and tick are the reader's three marks, so they read as pen
 * strokes rather than interface glyphs.
 */

type IconProps = { className?: string }

function Icon({
  className = 'size-5',
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={`shrink-0 fill-none stroke-current [stroke-width:2] [stroke-linecap:round] [stroke-linejoin:round] ${className}`}
    >
      {children}
    </svg>
  )
}

export const RingIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M13 3.5c5 0 8 3 8 8.2 0 5-3.8 8.8-9 8.8-5 0-8.5-3.4-8.5-8.2C3.5 7 7 3.6 12.4 3.5c3 0 5.5 1 7 3" />
  </Icon>
)
export const StrikeIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M5 6.5 19 18M18.5 5.5 6 18.5" />
  </Icon>
)
export const TickIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m4.5 12.5 5 5L20 6.5" />
  </Icon>
)
export const CloseIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Icon>
)
export const DialIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 7h10M18 7h2M4 17h4M12 17h8M14 4v6M8 14v6" />
  </Icon>
)
export const InfoIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5M12 7.6v.2" />
  </Icon>
)

export const MARK_ICONS = { like: RingIcon, dislike: StrikeIcon, read: TickIcon } as const
