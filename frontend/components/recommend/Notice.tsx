'use client'

import { useEffect } from 'react'

import { useRecommend } from './RecommendProvider'

/**
 * What the last mark or update did, with an undo where one makes sense.
 *
 * Fades in place and never slides across the phone tray; moves to the top edge
 * while a sheet or the drawer covers the bottom.
 */
export function Notice() {
  const { notice, dismiss } = useRecommend()
  useEffect(() => {
    if (!notice) return
    const timer = setTimeout(dismiss, 4200)
    return () => clearTimeout(timer)
  }, [notice, dismiss])

  return (
    <div
      role="status"
      aria-live="polite"
      className={`notice ${notice ? 'notice-show' : ''}`}
    >
      {notice && (
        <>
          <span>{notice.message}</span>
          {notice.undo && (
            <button
              type="button"
              onClick={() => {
                notice.undo?.()
                dismiss()
              }}
              className="code text-pen underline"
            >
              Undo
            </button>
          )}
        </>
      )}
    </div>
  )
}
