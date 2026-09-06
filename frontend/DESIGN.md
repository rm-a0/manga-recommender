---
name: MangaRec
description: A manga recommender printed as a convention circle catalogue on dark stock.
colors:
  ground: "#17211F"
  panel: "#1E2B28"
  line: "#2B3B37"
  cell: "#E8E4D8"
  cell-ink: "#141A19"
  cell-sub: "#54615D"
  text: "#DFE6E2"
  dim: "#8A9A95"
  spot: "#D1402F"
  spot-on-cell: "#A8291B"
  spot-on-ground: "#EF7060"
  pen: "#3F6FD8"
  on-spot: "#FFFFFF"
typography:
  masthead:
    fontFamily: "Anton, Arial Narrow, sans-serif"
    fontSize: "1.7rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.01em"
  display:
    fontFamily: "Anton, Arial Narrow, sans-serif"
    fontSize: "clamp(1.875rem, 4vw, 2.25rem)"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.02em"
  section:
    fontFamily: "Anton, Arial Narrow, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.02em"
  body:
    fontFamily: "Zen Kaku Gothic New, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  code:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "0.78rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.07em"
  cell-title:
    fontFamily: "Zen Kaku Gothic New, system-ui, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "normal"
rounded:
  none: "0px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "18px"
  lg: "32px"
  xl: "56px"
components:
  cell:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.cell-ink}"
    rounded: "{rounded.none}"
    padding: "6px 6px 8px"
  masthead:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.cell-ink}"
    rounded: "{rounded.none}"
    padding: "10px 20px"
  button-primary:
    backgroundColor: "{colors.spot}"
    textColor: "#FFFFFF"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  input-search:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.cell-ink}"
    rounded: "{rounded.none}"
    padding: "10px 12px"
  chip-code-on:
    backgroundColor: "{colors.spot}"
    textColor: "#FFFFFF"
    rounded: "{rounded.none}"
    padding: "4px 8px"
  chip-code-off:
    backgroundColor: "transparent"
    textColor: "{colors.dim}"
    rounded: "{rounded.none}"
    padding: "4px 8px"
  chip-ringed:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.none}"
    padding: "4px 10px"
---

# Design System: MangaRec

## Overview

A convention circle catalogue printed on dark stock. Thousands of stamp-sized cells packed
into a coded hall grid, single ink plus one spot red, and the reader's own marks in blue
biro.

The world was chosen because it does two jobs the product needs. At stamp scale the source
covers (~225×320) are *oversupplied* with pixels rather than starved — the constraint that
rules out every editorial layout becomes this format's advantage. And "circled in pen" is a
native state for the seed set: the titles you name are the ones you ring.

The governing constraint is honesty. The API has no score, popularity or relevance
ordering, so nothing here may imply a ranking. Every listing states the field that ordered
it; table codes are coordinates, never ranks.

## Colors

Dark printing stock, one ink, one spot red, one pen.

### Primary

`spot` `#D1402F` — the press ink. Rules under every hall heading, the masthead's bottom
edge, active code chips, primary buttons. **It is a fill.** It clears 3:1 painted but not
4.5:1 as small type on either ground, so it never sets text.

`spot-on-cell` `#A8291B` (5.51:1 on cell) sets table codes. `spot-on-ground` `#EF7060`
(5.62:1 on ground) sets red type on the stock. These two are the only reds under 24px.

### Secondary

`pen` `#3F6FD8` — blue biro. It marks **only what the reader chose**: the ring around an
entry they named. It never marks a system state, a status, or a result. Painted at
`mix-blend-multiply` over the cell so it reads as ink on paper.

### Neutral

`ground` `#17211F` is the stock everything is printed on. `panel` `#1E2B28` is the strip
and any inset. `line` `#2B3B37` is every hairline. `cell` `#E8E4D8` is the paper an entry
is printed on — the masthead sits on it too. `text` `#DFE6E2` (13.0:1) and `dim` `#8A9A95`
(5.6:1) on the stock; `cell-ink` `#141A19` (13.9:1) and `cell-sub` `#54615D` (5.1:1) on
paper.

### Named Rules

- **Red is the press, blue is the reader.** A red mark is something the catalogue did. A
  blue mark is something you did. Nothing is both.
- **The covers carry the colour.** 82,629 cover images supply the chroma; the interface is
  stock, paper, one red and one blue. No fourth hue is ever added.
- **Vivid red never sets type.** Use `spot-on-cell` or `spot-on-ground` below 24px.

## Typography

Three faces, each with one job. `Anton` is the display voice — condensed, one weight, the
catalogue's headings and masthead. `Zen Kaku Gothic New` is everything read at length: a
Japanese gothic whose Latin carries the proportions subtly, without any costume, and which
holds its shape down at cell-caption size. `IBM Plex Mono` sets every table code, count and
machine-readable label, always tracked at 0.07em and uppercase.

### Hierarchy

| Role | Face | Size | Notes |
|---|---|---|---|
| Masthead | Anton | 1.7rem | uppercase, on paper |
| Page title | Anton | 1.875–2.25rem | uppercase |
| Hall heading | Anton | 1.25–1.5rem | over the spot rule |
| Body | Zen Kaku Gothic New | 1rem | measure capped at 70ch |
| Cell caption | Zen Kaku Gothic New 500 | 0.9rem | exactly two lines |
| Code / count | IBM Plex Mono 600 | 0.78rem | uppercase, 0.07em |

### Named Rules

- **Every code is mono.** A table code, an entry count, a page number and a field label all
  belong to the same machine voice. Body type never sets them.
- **Tabular figures are global**, so counts and codes align down a column.
- **Cell captions occupy exactly two lines.** `line-clamp-2` caps a long title and a
  min-height holds a short one, so every cell in a row is the same height. Never put a
  `display` utility on a clamped element — it overrides the clamp silently.

## Layout

One column, `max-w-[1080px]`, gutters 20px rising to 32px. The hall grid is
`repeat(auto-fill, minmax(132px, 1fr))` at 12px gaps — seven cells across the container —
dropping to three fixed columns below 640px. auto-fill derives the column count from
`(container + gap) / (min + gap)`, so the minimum is the density dial.

Page order is fixed: masthead on paper → mono statistics strip → tools → hall heading over
its spot rule → grid.

**Responsive:** the grid repacks in whole cells, never partial ones. The statistics strip
wraps. Filters stack. Nothing is hidden on mobile that is visible on desktop, except the
code vocabulary, which is a `<details>` at both sizes.

## Elevation & Depth

**There is none.** This is printed matter: no shadows, no blur, no layering. A cell is
distinguished by being paper on stock, and a heading by the spot rule under it. Hover
raises nothing — it prints a 2px spot outline instead.

## Shapes

**Zero radius, everywhere.** Cells, chips, buttons, inputs, popovers, images.
`rounded: none` is the only shape token, and a control arriving with browser-default chrome
is restyled rather than accepted.

The only curve in the system is the pen ring, and it is a drawn SVG stroke — never a border
radius, which reads as a wobbly rectangle at any size.

## Components

### The cell

The system's atom. Paper ground, cover at `aspect-[225/320]`, table code in mono red,
caption fixed at two lines. Hover prints a 2px spot outline. A cover-less entry gets its
title set in the cover's place, never a placeholder graphic.

### The pen ring

An SVG stroke that closes past where it started, stretched to the artwork it rings via
`preserveAspectRatio="none"` — a real pen follows the shape of what it circles. Applied
only to entries the reader named, and carries an accessible label saying so.

### Buttons

Primary is a solid spot block, white label, Anton uppercase. Secondary is a 1px line border
that adopts the spot colour on hover.

### Chips

**Code chip** — mono, square, `spot` filled when required, line-bordered when not. Rendered
as links, because the state is the URL. **Ringed chip** — pen-bordered, carries the title
the reader named and removes it on click.

### Inputs

Search is paper on stock — the contrast alone separates it, with no coloured edge doing
the work a ground already does. Selects are `appearance-none` with a drawn chevron. Focus is the global ring, 2px `spot-on-ground`
at 2px offset; no component overrides it.

### Navigation

The masthead prints on paper with a 4px spot rule beneath, and a mono statistics strip sits
under it on the stock: hall, entries, codes. Counts degrade to `—`, never to zero, when the
API is unreachable.

## Do's and Don'ts

### Do:

- State the ordering field in the heading of every listing.
- Ring with the pen only what the reader chose.
- Put multi-value state in the URL so it is shareable and survives the back button.
- Let the covers be the colour; keep the interface to stock, paper, red and blue.
- Keep content visible by default — motion may offset a cell but never hide it.

### Don't:

- Imply a ranking, score or quality judgement. The API cannot support one.
- Set type in vivid `spot` or `pen` below 24px.
- Add a radius, a shadow, or a second border to declare depth.
- Draw the pen ring with `border-radius`.
- Ship a control with browser-default chrome.
