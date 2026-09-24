'use client'

import { useEffect, useRef, useState } from 'react'

import { GENRE_SEAL } from '@/lib/explicit'
import {
  DEFAULT_TUNING,
  effectiveWeights,
  normaliseTuning,
  sourcesOf,
  toRequest,
  toSearchParams,
  withMark,
} from '@/lib/recommend'
import type { Tuning } from '@/lib/recommend'
import {
  balanceWords,
  ENGINE_NOTES,
  LIMIT_RANGE,
  limitHelp,
  RECIPES,
  sourceCopy,
  WEIGHT_RANGE,
  weightWords,
} from '@/lib/tuning'
import { CloseIcon, DialIcon } from './icons'
import { useRecommend } from './RecommendProvider'
import { Slider } from './Slider'

const ENGINE_KEY = 'mangarec.engine-details'

/** Opens the drawer. Used in the hero, above the piles, and in the phone tray. */
export function TuneButton({ className = '' }: { className?: string }) {
  const { setTuneOpen, query } = useRecommend()
  const tuned = toSearchParams({
    marks: { like: [], dislike: [], read: [] },
    tuning: query.tuning,
  }).size
  return (
    <button
      type="button"
      onClick={() => setTuneOpen(true)}
      aria-haspopup="dialog"
      className={`inline-flex items-center gap-2 border border-line px-3.5 py-2 font-display tracking-[0.03em] uppercase hover:border-spot ${className}`}
    >
      <DialIcon className="size-[18px]" />
      Tune
      {tuned > 0 && (
        <span className="bg-pen px-1.5 py-0.5 code text-[0.66rem] leading-none text-white">
          {tuned}
        </span>
      )}
    </button>
  )
}

function readEngineDetails() {
  try {
    return localStorage.getItem(ENGINE_KEY) === '1'
  } catch {
    return false
  }
}

/**
 * The tuning drawer: every setting the recommendation API accepts, in plain
 * language, drafted and applied only on Apply.
 *
 * A modal dialog from the right; full screen on phones. Apply keeps the reader's
 * place on the page.
 */
export function TuneDrawer() {
  const { tuneOpen, setTuneOpen } = useRecommend()
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const el = dialog.current
    if (!el) return
    if (tuneOpen && !el.open) el.showModal()
    if (!tuneOpen && el.open) el.close()
  }, [tuneOpen])

  return (
    <dialog
      ref={dialog}
      onClose={() => setTuneOpen(false)}
      onClick={(event) => {
        if (event.target === event.currentTarget) setTuneOpen(false)
      }}
      aria-labelledby="tune-title"
      className="side-drawer"
    >
      {tuneOpen && <DrawerBody onClose={() => setTuneOpen(false)} />}
    </dialog>
  )
}

function DrawerBody({ onClose }: { onClose: () => void }) {
  const { query, strategies, codes, applyTuning, notify } = useRecommend()
  const [draft, setDraft] = useState<Tuning>(query.tuning)
  const [engine, setEngine] = useState(readEngineDetails)
  const sources = sourcesOf(strategies)
  const weights = effectiveWeights(draft, strategies)
  const base = effectiveWeights({ ...draft, weights: {} }, strategies)
  const normalised = normaliseTuning(draft, strategies)
  const same =
    toSearchParams({ ...query, tuning: normalised }).toString() ===
    toSearchParams(query).toString()

  const toggleEngine = (on: boolean) => {
    setEngine(on)
    try {
      localStorage.setItem(ENGINE_KEY, on ? '1' : '0')
    } catch {
      /* private window: keep it for this session */
    }
  }

  const apply = () => {
    applyTuning(normalised)
    onClose()
    notify('Applied. The picks are being redrawn.')
  }

  const setWeight = (source: string, value: number) =>
    setDraft((d) => ({ ...d, weights: { ...d.weights, [source]: value } }))

  return (
    <div className="grid h-full grid-rows-[auto_minmax(0,1fr)_auto]">
      <header className="flex items-start justify-between gap-3 border-b-[3px] border-spot bg-cell px-[18px] pt-3 pb-2.5 text-cell-ink">
        <div>
          <h2
            id="tune-title"
            className="font-display text-[1.35rem] leading-none tracking-[0.02em] uppercase"
          >
            Tune your picks
          </h2>
          <p className="mt-0.5 text-[0.82rem] text-cell-sub">
            Change how picks are chosen. Nothing moves until you apply.
          </p>
          <label className="engine-switch mt-2">
            <input
              type="checkbox"
              role="switch"
              checked={engine}
              onChange={(event) => toggleEngine(event.target.checked)}
            />
            <span className="engine-track" aria-hidden="true">
              <span />
            </span>
            <span className="code">Engine details</span>
          </label>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close without applying"
          className="grid size-[30px] shrink-0 place-items-center border border-[#cbc5b5] hover:border-cell-ink"
        >
          <CloseIcon className="size-4" />
        </button>
      </header>

      <div className="overflow-auto overscroll-contain px-5 pb-6">
        <p className="mt-4 code text-[0.7rem] text-dim">Start from</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {RECIPES.map((r) => {
            const on =
              draft.strategy === r.strategy && !Object.keys(normalised.weights).length
            return (
              <button
                key={r.strategy}
                type="button"
                aria-pressed={on}
                onClick={() =>
                  setDraft((d) => ({ ...d, strategy: r.strategy, weights: {} }))
                }
                className="grid gap-0.5 border border-line p-2.5 text-left hover:border-dim aria-pressed:border-cell aria-pressed:bg-cell aria-pressed:text-cell-ink aria-pressed:shadow-[inset_0_3px_0_var(--color-spot)]"
              >
                <b className="font-display font-normal tracking-[0.03em] uppercase">
                  {r.label}
                </b>
                <span className="text-[0.76rem] leading-snug opacity-75">{r.says}</span>
              </button>
            )
          })}
        </div>
        {engine && <p className="engine-line">{ENGINE_NOTES.strategy}</p>}
        <p className="mt-2 text-[0.84rem] text-dim">
          A recipe sets the sliders below. Move any of them to make it your own.
        </p>

        <Section
          title="What makes a match"
          lead="Ways a title can resemble what you liked. Only the balance between them matters."
          changed={Object.keys(normalised.weights).length > 0}
          onReset={() => setDraft((d) => ({ ...d, weights: {} }))}
        >
          <div className="mt-2.5 mb-1 flex h-2.5 gap-0.5" aria-hidden="true">
            {sources.map((s, i) => (
              <i
                key={s}
                className={`block transition-[flex] ${i % 2 ? 'bg-dim' : 'bg-text'}`}
                style={{ flex: weights[s] || 0.0001 }}
              />
            ))}
          </div>
          <p className="mb-1 font-bold">{balanceWords(weights)}</p>
          {sources.map((source) => {
            const copy = sourceCopy(source)
            return (
              <Slider
                key={source}
                id={`weight-${source}`}
                label={copy.label}
                value={Math.min(WEIGHT_RANGE.max, weights[source])}
                defaultValue={base[source]}
                {...WEIGHT_RANGE}
                words={weightWords(weights[source])}
                ends={['Off', 'Full']}
                help={copy.help}
                engine={engine ? ENGINE_NOTES.weight(source) : undefined}
                onChange={(v) => setWeight(source, v)}
              />
            )
          })}
        </Section>

        <Section
          title="Leave out"
          lead="Titles carrying any of these codes are dropped from your picks."
          changed={draft.skip.length > 0}
          onReset={() => setDraft((d) => ({ ...d, skip: [] }))}
        >
          <SkipCodes
            codes={codes}
            skip={draft.skip}
            onChange={(skip) => setDraft((d) => ({ ...d, skip }))}
          />
          {engine && <p className="engine-line">{ENGINE_NOTES.skip}</p>}
        </Section>

        <Section
          title="How many"
          changed={draft.limit !== DEFAULT_TUNING.limit}
          onReset={() => setDraft((d) => ({ ...d, limit: DEFAULT_TUNING.limit }))}
        >
          <Slider
            id="limit"
            label="Picks to show"
            value={draft.limit}
            defaultValue={DEFAULT_TUNING.limit}
            {...LIMIT_RANGE}
            words={String(draft.limit)}
            ends={['1', String(LIMIT_RANGE.max)]}
            help={limitHelp(draft.limit)}
            engine={engine ? ENGINE_NOTES.limit : undefined}
            onChange={(limit) => setDraft((d) => ({ ...d, limit }))}
          />
        </Section>

        {engine && <UnderTheHood draft={normalised} weights={weights} />}
      </div>

      <footer className="drawer-foot border-t border-line bg-ground px-[18px] py-2.5">
        <Preview draft={normalised} same={same} />
        <button
          type="button"
          onClick={() => setDraft({ ...DEFAULT_TUNING })}
          className="drawer-reset code text-[0.64rem] text-dim underline hover:text-text"
        >
          Reset to default
        </button>
        <button
          type="button"
          onClick={onClose}
          className="drawer-cancel border border-line px-3 py-2 font-display tracking-[0.03em] uppercase hover:border-dim"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={apply}
          disabled={same}
          className="drawer-apply bg-spot px-5 py-2 font-display tracking-[0.03em] text-white uppercase disabled:cursor-default disabled:bg-line disabled:text-dim"
        >
          Apply
        </button>
      </footer>
    </div>
  )
}

function Section({
  title,
  lead,
  changed,
  onReset,
  children,
}: {
  title: string
  lead?: string
  changed: boolean
  onReset: () => void
  children: React.ReactNode
}) {
  return (
    <section className="pt-5 pb-2">
      <div className="flex items-baseline justify-between gap-2.5 border-b-2 border-spot pb-1.5">
        <h3 className="font-display text-[1.15rem] leading-none tracking-[0.03em] uppercase">
          {title}
        </h3>
        {changed && (
          <button
            type="button"
            onClick={onReset}
            className="text-pen-on-ground code text-[0.66rem] underline"
          >
            Reset
          </button>
        )}
      </div>
      {lead && <p className="mt-2 mb-1 text-[0.84rem] leading-snug text-dim">{lead}</p>}
      {children}
    </section>
  )
}

/** Search the vocabulary, pick codes to skip. Skipped codes stay listed first. */
function SkipCodes({
  codes,
  skip,
  onChange,
}: {
  codes: string[]
  skip: string[]
  onChange: (skip: string[]) => void
}) {
  const [filter, setFilter] = useState('')
  const term = filter.trim().toLowerCase()
  const shown = [
    ...skip,
    ...codes
      .filter((c) => !skip.includes(c) && (!term || c.toLowerCase().includes(term)))
      .slice(0, term ? 30 : 18),
  ]
  return (
    <div className="pt-2">
      <label htmlFor="skip-filter" className="sr-only">
        Search codes
      </label>
      <input
        id="skip-filter"
        type="search"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder="Search codes…"
        className="mb-2.5 w-full border-0 bg-cell px-2.5 py-2 text-[0.9rem] text-cell-ink placeholder:text-cell-sub"
      />
      <div className="flex flex-wrap gap-1.5">
        {shown.map((code) => {
          const on = skip.includes(code)
          return (
            <button
              key={code}
              type="button"
              aria-pressed={on}
              onClick={() =>
                onChange(on ? skip.filter((c) => c !== code) : [...skip, code])
              }
              className="max-w-full border border-line px-2 py-1 text-left text-[0.8rem] leading-snug [overflow-wrap:anywhere] text-dim hover:border-dim hover:text-text aria-pressed:border-spot aria-pressed:bg-spot aria-pressed:text-white aria-pressed:line-through"
            >
              {code}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** What applying would change, from a dry run of the draft against the current picks. */
function Preview({ draft, same }: { draft: Tuning; same: boolean }) {
  const { query } = useRecommend()
  const [counts, setCounts] = useState<{
    key: string
    added: number
    moved: number
    left: number
  } | null>(null)
  const key = toSearchParams({ ...query, tuning: draft }).toString()

  useEffect(() => {
    if (same || !query.marks.like.length) return
    const controller = new AbortController()
    const timer = setTimeout(() => {
      fetch('/api/recommendations', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ query: toSearchParams(query).toString(), draft: key }),
        signal: controller.signal,
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => d && setCounts({ key, ...d }))
        .catch(() => {})
    }, 300)
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [key, same, query])

  let line: React.ReactNode = 'No changes yet.'
  if (!same && !query.marks.like.length) line = 'Applies once you like a title.'
  else if (!same)
    line =
      counts?.key === key ? (
        <>
          Applying: <b className="font-semibold text-text">{counts.added}</b> new ·{' '}
          <b className="font-semibold text-text">{counts.moved}</b> move ·{' '}
          <b className="font-semibold text-text">{counts.left}</b> leave
        </>
      ) : (
        'Working out what changes…'
      )
  return (
    <p className="drawer-line text-[0.82rem] text-dim" aria-live="polite">
      {line}
    </p>
  )
}

/** The optional engine layer: the fusion formula and the exact request. */
function UnderTheHood({
  draft,
  weights,
}: {
  draft: Tuning
  weights: Record<string, number>
}) {
  const { query, pending } = useRecommend()
  let marks = query.marks
  for (const [id, pile] of Object.entries(pending)) marks = withMark(marks, id, pile)
  const request = toRequest({ marks, tuning: draft }, GENRE_SEAL)
  const shorten = (_key: string, v: unknown) =>
    typeof v === 'string' && v.length > 30 ? `${v.slice(0, 8)}…` : v
  const sources = Object.keys(weights)

  return (
    <details open className="mt-6 border-t-2 border-spot pt-1">
      <summary className="cursor-pointer list-none py-2.5 font-display text-[1.1rem] tracking-[0.03em] uppercase">
        Under the hood
      </summary>
      <p className="text-[0.84rem] text-dim">
        Each source ranks candidates on its own. The ranks are fused, and the top of the
        fused list is your picks:
      </p>
      <div
        className="formula"
        role="img"
        aria-label="score equals the sum over sources of weight divided by k plus rank"
      >
        <span className="italic">score</span>
        <span className="text-dim">=</span>
        <span className="formula-sum">
          <span>Σ</span>
          <small>sources</small>
        </span>
        <span className="formula-frac">
          <span>weight</span>
          <span>60 + rank</span>
        </span>
      </div>
      <div className="formula formula-now" role="img" aria-label="with your draft">
        <span className="text-dim">=</span>
        {sources.map((s, i) => (
          <span key={s} className="contents">
            {i > 0 && <span className="text-dim">+</span>}
            <span className="formula-frac">
              <span>{weights[s].toFixed(2)}</span>
              <span>
                60 + rank<sub>{sourceCopy(s).label.toLowerCase()}</sub>
              </span>
            </span>
          </span>
        ))}
      </div>
      <p className="text-[0.84rem] text-dim">
        The engine fixes k at 60. A title only one source found gets only that source’s
        term.
      </p>
      <dl className="my-2.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[0.8rem] text-dim">
        {sources.map((s) => (
          <div key={s} className="contents">
            <dt className="code text-text">{s}</dt>
            <dd>{sourceCopy(s).engine}.</dd>
          </div>
        ))}
        <dt className="code text-text">piles</dt>
        <dd>{ENGINE_NOTES.piles}.</dd>
        <dt className="code text-text">seal</dt>
        <dd>{GENRE_SEAL.join(' and ')} are always added to exclude_tags.</dd>
      </dl>
      <p className="mt-3 mb-1 code text-dim">POST /recommendations</p>
      <pre className="overflow-x-auto border border-line bg-ground p-3 font-mono text-[0.72rem] leading-relaxed text-text">
        {JSON.stringify(request, shorten, 2)}
      </pre>
    </details>
  )
}
