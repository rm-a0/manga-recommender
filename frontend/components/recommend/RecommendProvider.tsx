'use client'

import { useRouter } from 'next/navigation'
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  useTransition,
} from 'react'

import { PILES, pileOf, queryHref, toSearchParams, withMark } from '@/lib/recommend'
import type { Marks, Pile, RecommendQuery, Tuning } from '@/lib/recommend'
import type { StrategyInfo } from '@/lib/types'

/** Enough of a title to draw its stamp in a pile before the page reloads it. */
export interface TitleStub {
  id: string
  title: string
  image_url: string | null
}

export interface NoticeState {
  id: number
  message: React.ReactNode
  undo?: () => void
}

interface RecommendContext {
  /** The query the page was rendered for. */
  query: RecommendQuery
  strategies: StrategyInfo[]
  /** Marks made since the last update, by title. `null` takes a title off its pile. */
  pending: Record<string, Pile | null>
  pendingCount: number
  /** True while a new run is loading. */
  busy: boolean
  /** The pile a title will be on after the next update. */
  effective: (id: string) => Pile | null
  /** Mark a title, or lift the mark when it already heads for that pile. */
  mark: (title: TitleStub, pile: Pile) => void
  /** Take a title off whatever pile it is headed for. */
  take: (id: string) => void
  /** Apply the pending marks: one new run. */
  update: () => void
  /** Apply a tuning straight away, keeping the reader's place on the page. */
  applyTuning: (tuning: Tuning) => void
  /** Remove a liked title straight away. */
  unlike: (id: string) => void
  titles: Record<string, TitleStub>
  /** The opened title, and where it opens: in the grid, or in the sidebar. */
  open: string | null
  openWhere: 'inline' | 'side'
  setOpen: (id: string | null, where?: 'inline' | 'side') => void
  /** Whether the tuning drawer is open. */
  tuneOpen: boolean
  setTuneOpen: (open: boolean) => void
  /** Codes a reader may skip: the vocabulary minus the explicit ones. */
  codes: string[]
  /** The piles as a sheet, on narrow screens. */
  pilesOpen: boolean
  setPilesOpen: (open: boolean) => void
  notice: NoticeState | null
  notify: (message: React.ReactNode, undo?: () => void) => void
  dismiss: () => void
}

const Context = createContext<RecommendContext | null>(null)

export function useRecommend(): RecommendContext {
  const value = useContext(Context)
  if (!value) throw new Error('useRecommend needs a RecommendProvider')
  return value
}

/** The word stamped on a cover while its mark waits for Update picks. */
const PILE_STAMP: Record<Pile, string> = { like: 'Liked', dislike: 'Nope', read: 'Read' }

const PILE_NAMES: Record<Pile, string> = {
  like: 'More like this',
  dislike: 'Not for me',
  read: 'Already read',
}

/**
 * Client state for the recommend page.
 *
 * The URL holds the applied query; this holds what the reader has marked since.
 * Pending marks are keyed to the query they were made against, so they clear
 * themselves the moment the page arrives with a new one.
 */
export function RecommendProvider({
  query,
  strategies,
  initialTitles,
  codes,
  children,
}: {
  query: RecommendQuery
  strategies: StrategyInfo[]
  initialTitles: TitleStub[]
  codes: string[]
  children: React.ReactNode
}) {
  const router = useRouter()
  const [busy, startTransition] = useTransition()
  const queryKey = toSearchParams(query).toString()

  const [draft, setDraft] = useState<{ key: string; marks: Record<string, Pile | null> }>(
    {
      key: queryKey,
      marks: {},
    },
  )
  const pending = useMemo(
    () => (draft.key === queryKey ? draft.marks : {}),
    [draft, queryKey],
  )

  const [stubs, setStubs] = useState<Record<string, TitleStub>>({})
  const titles = useMemo(
    () => ({ ...Object.fromEntries(initialTitles.map((t) => [t.id, t])), ...stubs }),
    [initialTitles, stubs],
  )

  const [opened, setOpened] = useState<{ id: string; where: 'inline' | 'side' } | null>(
    null,
  )
  const open = opened?.id ?? null
  const openWhere = opened?.where ?? 'inline'
  const setOpen = useCallback(
    (id: string | null, where: 'inline' | 'side' = 'inline') =>
      setOpened(id ? { id, where } : null),
    [],
  )
  const [pilesOpen, setPilesOpen] = useState(false)
  const [tuneOpen, setTuneOpen] = useState(false)
  const [notice, setNotice] = useState<NoticeState | null>(null)
  const noticeId = useRef(0)
  const notify = useCallback((message: React.ReactNode, undo?: () => void) => {
    noticeId.current += 1
    setNotice({ id: noticeId.current, message, undo })
  }, [])
  const dismiss = useCallback(() => setNotice(null), [])

  const navigate = useCallback(
    (next: RecommendQuery) =>
      startTransition(() => router.push(queryHref(next), { scroll: false })),
    [router],
  )

  const effective = useCallback(
    (id: string) => (id in pending ? pending[id] : pileOf(query.marks, id)),
    [pending, query.marks],
  )

  const setPending = useCallback(
    (fn: (marks: Record<string, Pile | null>) => Record<string, Pile | null>) =>
      setDraft((d) => ({ key: queryKey, marks: fn(d.key === queryKey ? d.marks : {}) })),
    [queryKey],
  )

  const mark = useCallback(
    (title: TitleStub, pile: Pile) => {
      setStubs((s) => ({ ...s, [title.id]: title }))
      // The first liked title has nothing to wait for: run straight away.
      if (!query.marks.like.length && pile === 'like' && !Object.keys(pending).length) {
        navigate({ ...query, marks: withMark(query.marks, title.id, 'like') })
        setOpen(null)
        notify(
          <>
            <b>{title.title}</b> is your first title. Picks are drawn from it.
          </>,
        )
        return
      }
      const applied = pileOf(query.marks, title.id)
      const next = effective(title.id) === pile ? null : pile
      setPending((m) => {
        const copy = { ...m }
        if (next === applied) delete copy[title.id]
        else copy[title.id] = next
        return copy
      })
      const waiting = Object.keys(pending).length + (title.id in pending ? 0 : 1)
      notify(
        <>
          <b>{title.title}</b> → {next ? PILE_NAMES[next] : 'off its pile'}.{' '}
          <b>{waiting}</b> waiting for Update picks.
        </>,
        () =>
          setPending((m) => {
            const copy = { ...m }
            delete copy[title.id]
            return copy
          }),
      )
    },
    [query, pending, effective, navigate, notify, setPending, setOpen],
  )

  const take = useCallback(
    (id: string) => {
      const current = effective(id)
      if (current)
        mark(titles[id] ?? { id, title: 'This title', image_url: null }, current)
    },
    [effective, mark, titles],
  )

  const update = useCallback(() => {
    const entries = Object.entries(pending)
    if (!entries.length) return
    let marks: Marks = query.marks
    for (const [id, pile] of entries) marks = withMark(marks, id, pile)
    setOpen(null)
    setPilesOpen(false)
    navigate({ ...query, marks })
    notify(
      <>
        Updated with {entries.length} mark{entries.length > 1 ? 's' : ''}. New picks are
        flagged <b>New</b>.
      </>,
    )
  }, [pending, query, navigate, notify, setOpen])

  const applyTuning = useCallback(
    (tuning: Tuning) => navigate({ ...query, tuning }),
    [query, navigate],
  )
  const unlike = useCallback(
    (id: string) => navigate({ ...query, marks: withMark(query.marks, id, null) }),
    [query, navigate],
  )

  const value = useMemo<RecommendContext>(
    () => ({
      query,
      strategies,
      pending,
      pendingCount: Object.keys(pending).length,
      busy,
      effective,
      mark,
      take,
      update,
      applyTuning,
      unlike,
      titles,
      open,
      openWhere,
      setOpen,
      pilesOpen,
      setPilesOpen,
      tuneOpen,
      setTuneOpen,
      codes,
      notice,
      notify,
      dismiss,
    }),
    [
      query,
      strategies,
      pending,
      busy,
      effective,
      mark,
      take,
      update,
      applyTuning,
      unlike,
      titles,
      open,
      openWhere,
      setOpen,
      pilesOpen,
      tuneOpen,
      codes,
      notice,
      notify,
      dismiss,
    ],
  )

  return <Context.Provider value={value}>{children}</Context.Provider>
}

/** Members of a pile after the next update: applied ones first, then incoming. */
export function pileMembers(
  query: RecommendQuery,
  pending: Record<string, Pile | null>,
  pile: Pile,
) {
  const applied = query.marks[pile]
    .filter((id) => !(id in pending))
    .map((id) => ({ id, pending: false }))
  const incoming = Object.entries(pending)
    .filter(([, p]) => p === pile)
    .map(([id]) => ({ id, pending: true }))
  return [...applied, ...incoming]
}

export { PILE_NAMES, PILE_STAMP, PILES }
