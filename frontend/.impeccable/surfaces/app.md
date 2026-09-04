---
version: 1
slug: "app"
primary_target: "app"
related_targets: []
---

# Surface: MangaRec front page and catalogue

Scope: `frontend/app` — the recommender front page (`/`), the catalogue (`/browse`),
manga detail, tag index, author pages. Visitor mode: **Operate**.

Audience: manga readers deciding what to read next, arriving with titles in mind.
Task: name what you have read, choose a route, scan the result.
Content: 82,629 real titles from the local dataset. Constraints: covers sharp only to
~200px; ~30% have no description; romaji-only search; no ranking or scoring endpoint
exists, and none may be simulated.

Chosen direction: **The Convention Catalog**, the challenger that beat the roll's assigned
direction (the Obi Band), then chosen by the user over four rendered alternatives on the
strength of its palette. Memorable moment: the running order assembling itself into
the contents page after a route is chosen.

Raises carried from declined challengers: tabular numeric honesty (every count a real
figure) and state change as a visible event. Two further raises written for the Obi Band
were deliberately dropped as inapplicable here — an achromatic interface would defeat the
two-ink palette the user chose this world for, and a one-face rule would flatten the
masthead/text contrast the anthology form depends on.

Unresolved: light variant deferred — the world is printed on dark stock, so the ground is
dark; reading in bright daylight is the honest risk.

## Direction contract

THESIS: A convention circle catalogue on dark stock — stamp-sized cells in a coded hall
grid, the reader's own entries ringed in biro. Refuses the dark cover-grid with hover
overlays that every anime database ships.

OWN-WORLD: Stock #17211F, paper cells #E8E4D8, one spot red #D1402F as fill only, blue
biro #3F6FD8 for reader marks. Anton headings, Zen Kaku Gothic New body, IBM Plex Mono for
every code and count. Hairlines, zero radius, no shadows.

STORY: The reader rings what they have read, chooses which codes matter, and reads a hall
listing — ordering always named, unbuilt routes stated as back matter rather than faked.

FIRST VIEWPORT: Masthead on paper with a 4px spot rule, mono statistics strip beneath.
Then "Ring what you have read" over a paper search field with a spot index tab. Ringed
titles as pen-bordered chips. The hall grid starts above the fold.

FORM: Comiket circle catalogue; the challenger that beat the roll's assigned direction on
both axes, then chosen by the user over four rendered alternatives. Seed key dac99887.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review,
the verdict, DESIGN.md, and every shipping raster carrying its provenance.
