'use client'

import { useSyncExternalStore } from 'react'

// One subscribe function per query, so React does not resubscribe on every render.
const subscribers = new Map<string, (onChange: () => void) => () => void>()
function subscribe(query: string) {
  let fn = subscribers.get(query)
  if (!fn) {
    fn = (onChange) => {
      const list = matchMedia(query)
      list.addEventListener('change', onChange)
      return () => list.removeEventListener('change', onChange)
    }
    subscribers.set(query, fn)
  }
  return fn
}

/** Whether a media query matches, kept in sync. `false` on the server. */
export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    subscribe(query),
    () => matchMedia(query).matches,
    () => false,
  )
}

/**
 * Whether drag and drop is offered: only with a real pointer, because on touch a
 * long-press drag fights scrolling.
 */
export const useFinePointer = () => useMedia('(pointer: fine)')
export const useNarrow = () => useMedia('(max-width: 759px)')
