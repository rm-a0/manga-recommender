/**
 * Cover art arrives at roughly 225x320, which is sharp only to about 112 CSS px
 * on a 2x display. Both sources publish a larger variant at a derivable URL, so
 * the view layer asks for that instead.
 *
 * This is a URL rewrite, not a data change. The stored value is untouched; if a
 * larger variant is ever written at ingest, delete this module and the callers
 * keep working.
 */

/**
 * Return the largest cover URL derivable from a stored one.
 *
 * MAL: insert `l` before the extension and use the CDN host directly, which also
 * avoids a 301. Verified on a random sample of eight; the variant is capped by
 * the original upload, so it can return less than 424px wide.
 * AniList: swap the `large` path segment for `extraLarge`.
 */
export function largeCover(url: string | null): string | null {
  if (!url) return null

  let next = url
  if (next.includes('myanimelist.net/images/')) {
    next = next.replace('://myanimelist.net/', '://cdn.myanimelist.net/')
    next = next.replace(/(\/\d+)(\.[a-z]+)$/i, '$1l$2')
  } else if (next.includes('s4.anilist.co/')) {
    next = next.replace('/cover/large/', '/cover/extraLarge/')
  }
  return next
}
