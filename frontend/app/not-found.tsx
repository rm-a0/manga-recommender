import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-5xl px-5 py-20 sm:px-8">
      <h1 className="font-display text-5xl leading-[0.9] tracking-[-0.02em] sm:text-6xl">
        Not in
        <br />
        this issue
      </h1>
      <p className="mt-4 max-w-[60ch] text-dim">
        Nothing in the catalogue has that address. It may have been dropped when the
        catalogue was last rebuilt.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href="/"
          className="bg-spot text-white px-5 py-2.5 font-display text-base uppercase tracking-[0.04em] no-underline"
        >
          Back to contents
        </Link>
        <Link
          href="/browse"
          className="border border-line px-5 py-2.5 font-display text-base uppercase tracking-[0.04em] no-underline transition-colors hover:bg-spot hover:text-white"
        >
          Search the catalogue
        </Link>
      </div>
    </div>
  )
}
