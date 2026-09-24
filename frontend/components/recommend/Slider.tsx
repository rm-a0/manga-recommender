'use client'

/**
 * A slider drawn to the catalogue: a ruled track, the filled run, a tick at the
 * default, and a paper thumb. Built on a native range input, so keyboard,
 * touch and assistive tech behave as they always do.
 */
export function Slider({
  id,
  label,
  value,
  defaultValue,
  min,
  max,
  step,
  words,
  ends,
  help,
  engine,
  onChange,
}: {
  id: string
  label: string
  value: number
  defaultValue: number
  min: number
  max: number
  step: number
  /** The current value in a few words. */
  words: string
  ends: [string, string]
  help?: string
  /** The request field it sets, shown with engine details on. */
  engine?: string
  onChange: (value: number) => void
}) {
  const at = (v: number) =>
    `${((Math.min(max, Math.max(min, v)) - min) / (max - min)) * 100}%`
  const changed = Math.abs(value - defaultValue) > 1e-9
  return (
    <div className="border-t border-line py-3 first:border-t-0">
      <div className="flex items-center gap-2.5">
        <label htmlFor={id} className="min-w-0 flex-1 truncate font-bold">
          {label}
        </label>
        <b
          className={`code whitespace-nowrap ${changed ? 'text-pen-on-ground' : 'text-dim'}`}
        >
          {words}
        </b>
      </div>
      <span
        className={`slider mt-1.5 ${changed ? 'slider-changed' : ''}`}
        style={{ '--v': at(value), '--d': at(defaultValue) } as React.CSSProperties}
      >
        <span className="slider-default" aria-hidden="true" />
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          aria-valuetext={words}
          onChange={(event) => onChange(Number(event.target.value))}
        />
      </span>
      <div className="mt-px flex justify-between code text-[0.6rem] text-dim">
        <span>{ends[0]}</span>
        <span>{ends[1]}</span>
      </div>
      {engine && <p className="engine-line">{engine}</p>}
      {help && <p className="mt-1.5 text-[0.82rem] leading-snug text-dim">{help}</p>}
    </div>
  )
}
