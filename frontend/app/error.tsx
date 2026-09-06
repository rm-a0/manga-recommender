'use client'

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-5xl px-5 py-20 sm:px-8">
      <h1 className="font-display text-5xl leading-[0.9] tracking-[-0.02em] sm:text-6xl">
        The press
        <br />
        stopped
      </h1>
      <p className="mt-4 max-w-[60ch] text-dim">
        The catalogue API did not answer. It sleeps when idle, so the first request after
        a quiet spell can time out — trying again usually wakes it.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 bg-spot text-white px-5 py-2.5 font-display text-base uppercase tracking-[0.04em] transition-opacity hover:opacity-85"
      >
        Try again
      </button>
    </div>
  )
}
