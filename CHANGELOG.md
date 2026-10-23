# Changelog

## [Unreleased]

### Fixed
- Refresh the book list, selected Book Details and tag browser after metadata
  writes, so counts and chapters appear without running another plugin. The same
  refresh follows anthology-report writes; books with no changes are not refreshed.

### Added
- FicLab EPUB extraction from marked front matter: labeled counts, status, rating,
  explicit matching author profiles, and uncategorized tags. Summary word counts
  take precedence over EPUB extent; date offsets are preserved. Checked against
  four fanfiction.net exports from FicLab 1.0.111 and 1.0.113.
- Separate TXT readers for spaced/wrapped archive headers and AO3/SquidgeWorld
  PDF-style prefaces. PDF pairing categories remain separate from fandoms.
- Partial recovery from detached PDF columns: retain explicit facts, omit uncertain
  author/tag assignments, and explain the omissions in the preview.
- Direct TXT archive-header extraction, checked against five distinct fanfiction.net
  stories. Supports optional fields, label aliases, English/Spanish text, dated
  timestamps, and grouped counts through the existing preview and write modes.
- TXT is used for books without EPUB. Opening headers are bounded, chapter notes
  are excluded, missing URLs are not guessed, and unrecognized headers are explained.

## [1.0.0] - 2026-10-01

### Added
- Explicit support for AO3 EPUBs downloaded with ao3downloader, verified against five
  real downloads, including coauthored and ongoing works, with Calibre writes and
  FanFicFare Saved Metadata round trips.
- A conservative labelled-header fallback for PDF-reflow EPUBs: title, rating, fandom,
  pairing, warning text, exact word counts, and explicitly marked original LiveJournal
  post URLs. Approximate counts and dates embedded in author notes are skipped.
- Collection-aware metadata extraction for epubmerge anthologies and EPUBs with a primary
  series URL, including safe outer metadata and explicitly available series facts.
- Anthology totals use the ordinary Word Count mapping. Calculated totals require reliable
  counts for every story; additional collection mappings cover work counts and series facts.
- Per-story authors, URLs, dates, summaries, ratings, and warnings in anthology previews;
  compact reports include authors, URLs, and dates.
- Regression checks using the expanded real EPUB fixtures and a separate real-Calibre
  scratch-library smoke check.

### Changed
- Requires Calibre 6.0 or newer; Calibre 5.x is no longer supported. Verified on 6.0 and 9.15.
- Author ID and Author URL are recovered only from explicit metadata or links, rather than
  derived from a bare author name. Some OPF-only books will no longer fill those mapped columns
  or include those fields in Saved Metadata.
- Saved Metadata is skipped when the URL FanFicFare will use is missing or unsupported;
  standard metadata and custom-column updates remain available. An existing Calibre URL/URI
  takes precedence over the URL recovered from the EPUB, matching FanFicFare's behavior.
- Ordinary Calibre Comments are written as escaped HTML paragraphs with preserved line breaks.
  Collection Comments retain their outer rich description.

### Fixed
- Series names come from AO3's series links without surrounding navigation text.
- Anonymous and other bare author names no longer produce invented AO3 profile URLs.
- OPF summaries preserve paragraph breaks and decode HTML entities; generated link markup
  escapes names, titles, and attribute values.
- Standard updates fill blank Calibre publication dates and Unknown authors without overwrite.
- All-unknown anthology statuses no longer write a misleading completed count.
- Conflicting Saved Metadata destinations cannot be selected in configuration; validation
  occurs before closing on Calibre versions that support the hook.
- Unsupported FanFicFare imports are explained in previews and zero-update confirmations.
- FanFicFare support checks respect existing Calibre identifiers, including planned original
  URL additions when a book has a Wayback URI.
- The real-Calibre harness computes its counts, checks multiple FFF fields, exercises independent
  overwrite flags and preview selection, and explicitly enables assertions under optimized Python.
- AO3 download bylines preserve coauthors as separate names, IDs, and profile URLs,
  including when conversion splits the byline into a second preface document.
- EPUBs without a matching PDF header no longer fail while recording extraction sources.
- Collections cannot be mistaken for their first story or written as FFF Saved Metadata.
- Saved Metadata destinations cannot also receive custom mappings or anthology reports.
- Previews show standard fields, custom columns, then raw metadata, explain kept values,
  and disable writing when there are no eligible changes.
- Confirmation counts actual changed books; per-book write failures retain and report
  partial changes while allowing subsequent books to continue.
- Space-grouped AO3 word counts are read in full. Ambiguous anthology counts are skipped.

## [0.3.0-beta] - 2026-09-25

### Added
- AO3 works recovered from an Internet Archive **Wayback Machine** snapshot. The
  snapshot URL (`web.archive.org/web/<timestamp>/https://archiveofourown.org/works/…`) is
  unwrapped to the canonical AO3 URL for the story URL, so site, story ID, author link and
  FanFicFare's adapter lookup all work as for a direct AO3 download. The snapshot URL is kept as
  a new **Wayback Machine URL** field (`waybackUrl`) in the Saved Metadata, also mappable to a
  custom column.
- Tags, rating, warnings, fandom, relationships, characters, language, stats and summary are
  recovered from AO3's *work page* metadata block (as WebToEpub saves it), not just from the
  preface of AO3's own downloads. Works with both WebToEpub's "Information" page and a whole
  AO3 page saved by the "Save as eBook" browser extension (which strips all CSS
  classes); the latter also yields the work's title and author from the page.
- AO3's own **PDF** downloads converted to EPUB (e.g. in Calibre): rating, warnings, category,
  fandoms, relationships, characters, tags, series, stats, title, author and summary are read
  from the preserved AO3 preface page.
- **Series** is now recovered (from AO3 downloads, AO3 work pages and AO3 PDFs) — FanFicFare's
  own `series`/`seriesUrl` keys, written to Calibre's Series field by "Update standard Calibre
  metadata" and mappable to a custom column.

### Fixed
- Story URLs on AO3's old `download.archiveofourown.org` host are recognized, and normalized to
  `https://archiveofourown.org/works/…`.
- Calibre's "Unknown" placeholder author is no longer treated as a real author name (it produced
  an AO3 profile link for a user called "Unknown").
- "Update standard Calibre metadata" read the wrong series key (FanFicFare's *second* series).
- A whole AO3 page saved as an EPUB carries the *page's* metadata in the EPUB itself — the
  browser-tab title ("Title - author - Fandom [Archive of Our Own]"), "Organization for
  Transformative Works" as author, and AO3's site tagline as description. Those no longer
  override the real title/author/summary recovered from the page.
- The `url` identifier is now added even when the book already has a `uri` identifier, if that
  `uri` is a Wayback Machine snapshot (Calibre imports one from these EPUBs). FanFicFare reads
  `url` first, so it now gets the real AO3 URL; the snapshot `uri` is left in place.
- AO3 stats with no whitespace between entries ("Chapters:1/1Comments:41") no longer turn a
  finished work into In-Progress with no chapter total.

## [0.2.1-beta] - 2026-08-27

### Added
- A separate **Total Chapters (if known)** field, mappable to its own custom column —
  previously the only way to get a chapter total was the combined "x/y" text field, with no way
  to get just the total as its own number (e.g. for a template column that composes its own
  "x/y" display from two separate int columns). Absent, not zero, when the source itself doesn't
  know the total yet (an open-ended, still-updating work).
- The custom column mapping dialog now labels its two columns ("Extracted Field" / "Write To
  Column"), so it's clear at a glance which side is this plugin's data and which is your Calibre
  column — the dropdown lists every column that's merely *type-compatible*, not just ones that
  are semantically related, which could look like a mismatch without the header.

### Fixed
- A FanFicFare-downloaded EPUB whose spine has Calibre's own auto-inserted cover page (commonly
  named literally `titlepage.xhtml`) ahead of the real title page could lose its entire
  category/genre/status/dates/chapters/words silently — the extractor gave up on the first
  title-page-shaped file it found even when that file turned out to have no actual content.
- AO3 singularizes some of its own preface labels when there's exactly one tag in that category
  ("Relationship:" instead of "Relationships:" for a single-pairing work) — only the plural form
  was recognized, so ships were silently dropped entirely for any single-relationship work.

## [0.2.0-beta] - 2026-07-28

### Added
- Recovers metadata from fanfiction.net stories, from two additional sources beyond the
  original AO3/FanFicFare-focused extraction:
  - Front-matter pages generated by [fichub.net](https://fichub.net) (recovers fandom, rating,
    status, chapters/words, dates, and more).
  - fanfiction.net's own native story-info page, as saved by the
    [WebToEpub](https://github.com/dteviot/WebToEpub) browser extension (recovers the same
    fields, plus author profile link/ID and fandom from the site's own breadcrumb).
- **Show confirmation after writing** — a new toggle (on both the Extraction and Anthology
  Status tabs) to turn off the "Updated N of M books" popup after a run.

### Fixed
- A book with a fandom recovered from fanfiction.net would lose it from Tags the moment
  FanFicFare's own "Update Calibre Metadata from Saved Metadata Column" action ran — FFF has no
  fanfiction.net-specific config, so it reads the fandom from a different metadata key than it
  does for AO3. Verified fixed directly against FanFicFare's own Tags-computation logic.
- A title page whose chapter count was reported as "n/?" (final count not yet known) could crash
  Calibre outright when writing to an integer custom column.
- Some title pages (e.g. from fichub.net) use a plain `<p>Label: value</p>` layout instead of
  FanFicFare's own `<b>Label:</b> value` layout; these were previously invisible to extraction
  entirely, silently dropping every field past title and author.
- An EPUB with more than one `<dc:source>` tag in its metadata (as WebToEpub produces — one per
  chapter, plus the cover image) could pick up the cover image URL as the story URL instead of
  the actual story.
- `genre` now also contributes to the Tags composite when directly updating standard Calibre
  metadata (previously only used for the Saved Metadata column).

## [0.1.0-beta] - 2026-07-21

Initial public beta release.

### Added
- **Save all extracted metadata** — writes recovered metadata into a Saved Metadata custom
  column in FanFicFare's own native format, ready for FFF's "Update Calibre Metadata from Saved
  Metadata Column" action.
- **Update standard Calibre metadata** — writes directly to Title, Author, Tags, Series and
  Comments using FanFicFare's default AO3 field-composition rules, no FFF round trip required.
- **Update custom columns** — a configurable mapping from recovered metadata fields to your own
  custom columns.
- **Extract story status from anthology** — a separate action for epubmerge-bundled anthology
  EPUBs (e.g. a downloaded AO3 series), recovering each individual fic's own completion status
  instead of just the bundle's single aggregate status, and writing a per-fic breakdown into a
  column you choose.
- Toolbar dropdown for quick access to both actions plus settings, without needing to select
  books first.
- Preview dialog before any writes, with per-book opt-out, for every mode above.
