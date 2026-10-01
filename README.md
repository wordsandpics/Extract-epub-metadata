# Extract EPUB Metadata

Extract Epub Metadata recovers metadata already stored in **fanfiction EPUBs** in your
Calibre library. It can save that data for FanFicFare, update standard Calibre fields,
or fill custom columns. It does not download stories.

It is useful when a story cannot be downloaded again, or when an EPUB came from outside
your Calibre library without its metadata. What it can recover depends on what the EPUB
contains.

> **Disclaimer:** this was shamelessly vibe-coded. It's provided as-is, and support is minimal —
> issues and PRs are welcome, but don't expect a fast turnaround. Back up your library (or at
> least test on a couple of books first) before relying on it.

This plugin is built and tested primarily around [Archive of Our Own](https://archiveofourown.org)
downloads. AO3 EPUBs downloaded with
[ao3downloader](https://github.com/nianeyna/ao3downloader) are explicitly supported, including
coauthored works, completed works, and ongoing works with known or unknown chapter totals.
fanfiction.net EPUBs from [fichub.net](https://fichub.net) or the
[WebToEpub](https://github.com/dteviot/WebToEpub) browser extension are also explicitly supported,
as are AO3 works saved from an [Internet Archive Wayback Machine](https://web.archive.org)
snapshot, either with WebToEpub or with the
[Save as eBook](https://chromewebstore.google.com/detail/save-as-ebook/haaplkpoiimngbppjihnegfmpejdnffj)
browser extension (which saves the whole page). With Save as eBook, save the work's
"Entire Work" snapshot (`?view_full_work=true`) — otherwise you only get the chapter on screen.
AO3's own **PDF** downloads, converted to EPUB (e.g. in Calibre), are supported too.
PDF-reflow EPUBs with a clearly labelled opening header can also supply rating, fandom,
pairing, warning text, and exact word counts. Explicit original LiveJournal post links in
archive notices are recovered. This limited fallback does not infer publication dates or
completion status, and approximate counts such as `~3400` are skipped.
Recovered LiveJournal metadata is intended for standard metadata and custom-column updates.
An installed FanFicFare adapter registry is checked offline when staging Saved Metadata,
using the existing Calibre URL/URI first, then the recovered EPUB URL. A Wayback URI is
bypassed when the original URL will be added as a URL identifier. Unsupported URLs are
skipped with an explanation. Without FanFicFare installed, support for
other hosts is marked as unverified rather than assumed absent.
Other sites and tools may work too — the extraction degrades gracefully rather than erroring out —
but haven't been tested, so your mileage may vary.

It reads the EPUB and recovers as much metadata as possible (title, author, fandom, relationships,
characters, tags, rating, warnings, word/chapter counts, dates, story URL, etc.), then does
whichever of the following you've enabled:

1. **Save all extracted metadata** (on by default) — stores the recovered metadata in a
   Saved Metadata column using FanFicFare's native format. You then run FFF's existing
   **"Update Calibre Metadata from Saved Metadata Column"** action to process it as if you were downloading it, using your
   existing `personal.ini` replacements, custom-column mappings, and cover generation. This mode
   deliberately does not re-implement any of FFF's metadata processing.

2. **Update standard Calibre metadata** (off by default) — writes directly to your library's
   Title, Author, Tags, Series and Comments using FanFicFare's default AO3 metadata mapping. No
   separate FFF update step is required. This is a simpler path intended for users who
   don't rely on extensive `personal.ini` customisation.

3. **Update custom columns** (off by default) — writes selected recovered metadata fields (such as
   fandom, word count or rating) directly to custom columns you choose.

The three options are independent and can be combined however you like. By default, only the
Saved Metadata option is enabled because it modifies only a single custom column. The
other two write more changes immediately to your metadata, so they're opt-in.

## What this plugin does *not* do

It doesn't download stories or replace FanFicFare — extraction only works with metadata already
present in the EPUB itself. And with only mode 1 enabled (the default), it never touches your
library's Title/Tags/Comments/etc. directly; it just reconstructs FanFicFare's Saved Metadata
column so FFF can do its thing. 

## Known limitations

Coverage uses real EPUBs from AO3, ao3downloader, fichub.net, WebToEpub, Wayback snapshots, converted AO3 PDFs,
epubmerge anthologies, and files obtained from Reddit whose creation tools are unknown.
The expanded checks do not cover every EPUB layout; review the preview before writing.

- Crossover fics (multiple fandoms) downloaded from fanfiction.net via WebToEpub will only get
  the *last* fandom in the site's breadcrumb — there's no fixture to verify multi-fandom handling
  against yet, so rather than guess, only the single-fandom case is handled.
- Other sites and layouts may have incomplete coverage. Extraction is designed to
  degrade gracefully (skip a field rather than guess at it) when it doesn't recognize a page's
  layout, but "graceful" can still mean a field silently isn't recovered rather than erroring
  loudly — always check the preview before writing.

## How it works

Metadata is extracted from multiple sources, preferring the most complete source first:

1. Standard EPUB/OPF metadata (title, authors, language, description, an explicit story-URL
   identifier, `dc:source`).
2. A title page, if the EPUB has one — either FanFicFare's own generated page, or a
   fichub.net-style front-matter page (a similar but not identical layout).
3. AO3's own native front-matter preface, if the EPUB was downloaded directly from
   [Archive of Our Own](https://archiveofourown.org) — or AO3's work-page metadata block, as
   saved by WebToEpub.
4. AO3's preface page in an AO3 PDF download that was converted to EPUB (read from the text, since
   the conversion keeps no structure).
5. fanfiction.net's own native story-info page, as saved verbatim by the WebToEpub browser
   extension.
6. A generic scan for the first recognized fanfic-site link, as a last-resort way to recover the
   story URL.

Before the final link scan, a limited fallback reads consecutive labelled fields at the start
of EPUB content explicitly marked as a PDF conversion. It stops at author notes or story text.

Earlier sources take precedence; later sources only fill in missing values.

**Wayback Machine copies.** When the story URL is a `web.archive.org` snapshot, the plugin uses
the original URL it wraps (e.g. `https://archiveofourown.org/works/…`) as the story URL, so site,
story ID and author link are recovered and FanFicFare picks the right site adapter. The
snapshot URL itself is kept in the Saved Metadata as `waybackUrl` (and is available to map to a
custom column), since it may be the only way back to that exact copy. Stats (status, chapter and
word counts) reflect the snapshot's date, not the live site. FanFicFare stores `waybackUrl` but only shows
it to `personal.ini` templates if you add it to `extra_valid_entries`.

When a story URL is recovered, the plugin can also add it as a `url` identifier (if one doesn't
already exist). FanFicFare uses this identifier to determine which site adapter to use when it
later imports the Saved Metadata — relevant to mode 1's round trip, but harmless to leave on
regardless of which modes you use.

## Installing

Requires **Calibre 6.0 or newer**. The current code has been checked on official Calibre 6.0
and 9.15 on macOS, plus user testing in Calibre Zen. Older Calibre versions are not supported.

Download the latest `extract_epub_metadata-*.zip` from the
[Releases page](https://github.com/wordsandpics/Extract-epub-metadata/releases), then in the Calibre
GUI: Preferences → Plugins → Load plugin from file, and pick the zip you downloaded.

> **Download the right file.** On the release page, use the zip listed under **Assets** named
> `extract_epub_metadata-v1.0.0.zip` — *not* the "Source code (zip)" link GitHub adds
> automatically. The source download nests the plugin inside a folder, and Calibre will reject it
> with *"does not contain a top-level `__init__.py` file"*.

If you're working from a clone of this repository instead:

```sh
# from this directory
/Applications/calibre.app/Contents/MacOS/calibre-customize -b extract_epub_metadata
```

(On Linux/Windows, use whichever `calibre-customize` is on your `PATH`.)

## Configuring

In Preferences → Plugins → Extract EPUB Metadata → Customize plugin, each mode is its own
checkable section:

- **Save all extracted metadata** (default on)
  - **Saved Metadata Column** — a Long Text ("comments") custom column. This should be the same
    column configured as FanFicFare's Saved Metadata column.
  - **Overwrite existing Saved Metadata** — off by default; books with an existing value are skipped.
    Enabling it also refreshes the extraction timestamp, so an otherwise unchanged book can
    still count as updated on a repeated run.
- **Update standard Calibre metadata** (default off)
  - **Overwrite existing standard metadata** — off by default; a field already populated in
    Calibre (e.g. an existing Title or Tags) is left alone. Blank publication dates and Calibre's
    localized “Unknown” author are treated as empty and filled in. Other existing authors,
    including an imported site organization or combined coauthors, require overwrite to replace.
- **Update custom columns** (default off)
  - **Configure column mapping…** opens a dialog listing your custom columns (of a supported
    datatype: text, comments, enumeration, series, bool, int, float, datetime), each with a
    dropdown of recovered-metadata fields compatible with that column's type. Leave a column
    "(not mapped)" to never touch it.

Independent of all three modes:

- **Add missing story-URL identifier** — on by default; only adds a `url` identifier when the
  book doesn't already have one.
- **Preview before writing** — on by default; review everything that would be written, across
  whichever modes are enabled, before anything is written.
- **Show confirmation after writing** — on by default; shows a small popup summarizing how many
  books were updated. Turn off to skip it and return straight to Calibre.

## Usage

Select one or more books with an EPUB, click the toolbar button (or use the dropdown arrow next
to it for the options below), review the preview, and confirm. If you're using mode 1 (Saved
Metadata Column), follow up by running FanFicFare's **Update Calibre Metadata from Saved Metadata
Column** action. If you're only using modes 2/3, your library fields are already updated — no
further action needed.

The toolbar dropdown has three options:
- **Extract Metadata** — the main action described above.
- **Extract story status from anthology** — see below.
- **Configure…** — opens this plugin's settings directly, without needing to go through
  Preferences → Plugins first.

## Anthologies and series collections

**Extract Metadata** recognizes epubmerge anthologies and EPUBs whose primary URL is a
`/series/<id>` URL. A series link mentioned inside an ordinary story does not make it an anthology.
Collection title, authors, language, tags, and description come from the outer EPUB metadata.
An outer description may be a generated contents list rather than author-written notes.

Embedded epubmerge stories can supply individual authors, URLs, summaries, dates, statuses,
and counts. The preview shows those details. WebToEpub series files may preserve only a saved
series page; the plugin uses its explicit work count, word total, completion flag, and dates
when available, without inventing individual story records.

The ordinary **Word Count** mapping records the total for the whole anthology. A calculated
total requires a reliable count for every embedded story; a saved series page can also supply
an explicit total. Additional collection mappings cover story/work count, completed count,
unknown statuses, total chapters, collection URL, and series dates.
Completed-story counts mean known completed stories; unknown statuses are counted separately.
If every story's status is unknown, the completed count is omitted.

FanFicFare's **Update Calibre Metadata from Saved Metadata Column** requires one story URL,
so this plugin skips Saved Metadata for collections and explains why in the preview. Enable
standard metadata or custom-column updates to write collection data. Existing anthology
identifiers are preserved. Ratings, warnings, and story summaries stay attached to each story
in the preview rather than becoming collection-wide values.

The preview lists standard fields first, then custom columns, then Saved Metadata. It marks
existing standard values that will be kept when overwrite is off. Books with nothing to write
cannot be selected for writing. Confirmation counts books whose data actually changed;
write errors identify the book and any fields already changed.

The Saved Metadata column is reserved: custom mappings and the anthology report cannot use
it as their destination.

### Anthology status report

FanFicFare can bundle several separately-downloaded fics into one EPUB (via `epubmerge`) — e.g. every fic in an AO3 series. The bundle's own metadata only ever carries **one** completion status for the whole thing, manually set by the author,  with no way to tell if it's an unfinished anthology made up of completed works, or having incomplete works too. This action recovers each individual fic's own status instead, by reading each one's front-matter page inside the bundle (the same page FanFicFare itself generates per fic), and writes a per-fic breakdown into a column you choose:

```
6/7 fics complete.

1. In Arduis Fidelis 1 -- Completed (12 ch, 17,673 words)
...
7. In Arduis Fidelis 7 -- In-Progress (110 ch, 300,469 words)
```

This is a separate, independent action from the main metadata extraction above — it has its own settings (its own destination column, overwrite, preview, and show-confirmation toggles) on the **Anthology Status** tab of this plugin's configuration. Running it on a book that isn't an epubmerge-bundled anthology just skips that book with an explanatory note rather than erroring, so you can select a mix of anthologies and regular books at once.

The compact report also includes authors, story URLs, and dates when available. Long summaries,
ratings, and warnings appear only in the detailed preview. Unknown completion statuses are
reported separately.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for architecture, design rationale, and the FanFicFare
internals research behind several of the trickier fixes.

```sh
python3 -m unittest discover -s tests -v
```

The test suite is stdlib-only (`unittest`, `xml.etree.ElementTree`) and runs without Calibre
installed, using a minimal stub in `tests/calibre_stub/` so
`extract_epub_metadata/__init__.py` can be imported outside a real Calibre environment. It
runs against real fixtures in `tests/fixtures/`, including an actual AO3-downloaded EPUB and a
real Saved Metadata column value.

One test (`test_round_trips_through_fanficfare_load_html_metadata`) additionally verifies against
FanFicFare's own installed `load_html_metadata()` when available, and skips cleanly otherwise.
