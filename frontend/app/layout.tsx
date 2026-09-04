import type { Metadata } from 'next'
import { Anton, IBM_Plex_Mono, Zen_Kaku_Gothic_New } from 'next/font/google'

import { Masthead } from '@/components/Masthead'
import './globals.css'

const anton = Anton({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-anton',
  display: 'swap',
})

const zen = Zen_Kaku_Gothic_New({
  weight: ['400', '500', '700'],
  subsets: ['latin'],
  variable: '--font-zen',
  display: 'swap',
})

const mono = IBM_Plex_Mono({
  weight: ['400', '500', '600'],
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'MangaRec — 推',
  description:
    'A manga recommender over a catalogue of 82,629 titles. Ring what you have read, choose which codes matter, read the hall listing.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${anton.variable} ${zen.variable} ${mono.variable}`}>
      <body className="min-h-dvh">
        <a
          href="#hall"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-spot focus:px-4 focus:py-2 focus:text-sm focus:uppercase focus:tracking-wide focus:text-white"
        >
          Skip to the hall listing
        </a>
        <Masthead />
        <main id="hall">{children}</main>
        <footer className="mt-20 border-t border-line px-5 py-9 text-sm text-dim sm:px-8">
          <p className="max-w-[70ch]">
            MangaRec is open source and reads a catalogue built from the Kaggle MyAnimeList
            2026 dataset and AniList. Cover art and synopses belong to their publishers.
          </p>
          <p className="mt-2 max-w-[70ch]">
            The recommendation engine is not built yet. Nothing here ranks or scores a
            title, and no route claims a result it did not fetch.
          </p>
        </footer>
      </body>
    </html>
  )
}
