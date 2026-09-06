import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // The floating route badge sits over the running order at small widths.
  devIndicators: false,
  images: {
    // Cover art comes from the two ingestion sources' CDNs. MAL rows arrive as
    // `myanimelist.net`, which 301s to `cdn.myanimelist.net`; both are listed so
    // an un-rewritten URL still resolves. See lib/covers.ts for the rewrite.
    remotePatterns: [
      { protocol: 'https', hostname: 'cdn.myanimelist.net', pathname: '/images/**' },
      { protocol: 'https', hostname: 'myanimelist.net', pathname: '/images/**' },
      { protocol: 'https', hostname: 's4.anilist.co', pathname: '/**' },
    ],
  },
}

export default nextConfig
