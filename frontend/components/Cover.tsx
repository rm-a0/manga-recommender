import Image from 'next/image'

import { largeCover } from '@/lib/covers'

interface CoverProps {
  url: string | null
  title: string
  /** Rendered width in CSS pixels. Kept at or under 200: the sources cap there. */
  width: number
  className?: string
  priority?: boolean
}

/**
 * One cover at printed-thumbnail scale.
 *
 * The cover is decorative here because every caller sets the title as real text
 * beside it, so the alt is empty rather than a duplicate announcement. A record
 * with no cover gets a set title block instead of a placeholder graphic.
 */
export function Cover({ url, title, width, className = '', priority = false }: CoverProps) {
  const height = Math.round(width * (320 / 225))
  const src = largeCover(url)

  return (
    <div
      className={`relative shrink-0 overflow-hidden bg-cell p-1.5 ${className}`}
      style={{ width, height }}
    >
      {src ? (
        <Image
          src={src}
          alt=""
          width={width}
          height={height}
          priority={priority}
          sizes={`${width}px`}
          className="h-full w-full object-cover"
        />
      ) : (
        <span
          className="flex h-full w-full items-center justify-center p-1.5 text-center font-display uppercase leading-[0.95] text-cell-sub"
          style={{ fontSize: Math.max(9, width / 9) }}
          aria-hidden="true"
        >
          {title.slice(0, 28)}
        </span>
      )}
    </div>
  )
}
