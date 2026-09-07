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
  figure:
    fontFamily: "Anton, Arial Narrow, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "normal"
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
  order-tab-on:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.cell-ink}"
    rounded: "{rounded.none}"
    padding: "6px 12px"
  order-tab-off:
    backgroundColor: "transparent"
    textColor: "{colors.dim}"
    rounded: "{rounded.none}"
    padding: "6px 12px"
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

The governing constraint is honesty, and what it forbids narrowed when the catalogue
gained real figures. A weighted score and a vote count now exist for 30,513 of the 82,629
titles, and the API orders on either, so a listing may rank — it must simply say what
ranked it. What is still forbidden is implying a *recommendation*: nothing here measures
how well a title answers what the reader ringed, because the engine that would is not
built. Every listing states the field that ordered it, and a figure printed on a cell is
the catalogue's own score, never a match.

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
| Figure / count | IBM Plex Mono 600 | 0.78rem | uppercase, 0.07em |
| Score | Anton | 2.5rem | vivid spot, detail page only |

### Named Rules

- **Every figure is mono.** A score, a vote count, an entry count, a page number and a
  field label all belong to the same machine voice. Body type never sets them.
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

The system's atom. Paper ground, cover at `aspect-[225/320]`, the figures line, the cell
rule, caption fixed at two lines. Hover prints a 2px spot outline. A cover-less entry gets its title set
in the cover's place, never a placeholder graphic.

### The figures line

Under the cover: the weighted score in mono red, a dotted leader, then how many readers
scored it, in muted ink — the way a contents page ties an entry to its page number. Two
thirds of the catalogue carries no metrics row, so the unrated case prints `Not rated` in
`cell-sub` and holds the same height. It replaced the table code, which was a coordinate
invented to fill a row that had nothing real to print on it.

### The cell rule

A 2px spot rule under the figures, closing them off from the title. It is the same object
as the rule under a hall heading, at cell scale, so a cell reads as a miniature of the page
it sits on: machine voice, rule, content.

**It measures nothing, and it is drawn on every cell.** A mark present on a third of the
hall and absent on the rest reads as a badge some titles won; drawn everywhere, it is
furniture and the hall stays even.

The reason it cannot be a measure is the distribution. Half the catalogue scores between
6.79 and 7.07 — 2.8% of a bar's width, about 3px on a cell, and invisible in a grid — while
`6.8` and `7.1` are two glyphs apart and read instantly. **At cell scale the digits encode
the score and the rule finishes the cell.** Each does the job the other is bad at.

### The score rule

The detail page only. Ten segments, one per point, the last filling by the fraction it
earned, 8px on `panel`, under the score in vivid `spot` Anton at 2.5rem — the only place in
the system vivid red sets type, and it clears 24px doing it.

Segments earn their place here and nowhere else. On one title there is nothing to compare
against, so the rule's job is to say what the score is *out of*, which a countable scale
does and a bare figure does not.

### The order strip

The hall's ordering, as index tabs on a hairline baseline. The chosen ordering is printed
on paper with a 3px spot bar over its top edge; the rest are `dim` on the stock. Radios
inside the filter form, so the choice submits with everything else and lands in the URL.
Never a select: a popup is the one app widget on a page of printed matter.

### The code ledger

One tri-state box per code — empty, a white tick on spot red, or a red cross struck into
the ink — and the code's own name struck through when it is barred. One column of three
states rather than two columns of two, because a code cannot be required and barred at
once and a control that permits both has to invent a winner. Drawn, not a native checkbox,
which holds two states only.

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
- Print `Not rated` where a figure is missing. Two thirds of the hall has no score, and a
  blank row reads as a defect.
- Draw the cell rule on every cell, rated or not. It is furniture, not a verdict.
- Ring with the pen only what the reader chose.
- Put multi-value state in the URL so it is shareable and survives the back button.
- Let the covers be the colour; keep the interface to stock, paper, red and blue.
- Keep content visible by default — motion may offset a cell but never hide it.

### Don't:

- Imply that a listing is ordered by how well it matches what the reader ringed. The
  catalogue's own score is the only ranking there is, and the heading always says so.
- Set type in vivid `spot` or `pen` below 24px. The score rule's 2.5rem figure is the one
  place vivid red sets type at all.
- Encode a score as a length anywhere a reader compares several at once. Half the
  catalogue lands inside 0.28 points; a bar of it is noise wearing the costume of data.
  Print the figure instead.
- Add a radius, a shadow, or a second border to declare depth.
- Draw the pen ring with `border-radius`.
- Ship a control with browser-default chrome.
