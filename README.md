# Extract EPUB Metadata

Extract EPUB Metadata recovers metadata already stored in fanfiction EPUBs and recognizable TXT archive headers in your Calibre library. It can prepare metadata for FanFicFare, update standard Calibre fields, or fill custom columns. It does not download stories.

It's useful when a story can’t be downloaded again or a book is missing metadata in Calibre. What can be recovered depends on what the file contains.

> Provided as-is, with limited support. Please back up your library or try a few books first. Issues and pull requests are welcome, but responses may be slow.

## Supported EPUBs

The plugin is built and tested primarily with Archive of Our Own (AO3) EPUBs, including downloads made with [ao3downloader](https://github.com/nianeyna/ao3downloader). It also supports:

- fanfiction.net EPUBs from [fichub.net](https://fichub.net) and the [WebToEpub browser extension](https://github.com/dteviot/WebToEpub)
- FicLab fanfiction.net EPUBs, checked against four downloads from versions 1.0.111 and 1.0.113
- AO3 works saved from a [Wayback Machine](https://web.archive.org) snapshot using WebToEpub or [Save as eBook](https://chromewebstore.google.com/detail/save-as-ebook/haaplkpoiimngbppjihnegfmpejdnffj)
- AO3 PDF downloads converted to EPUB
- EPUBs with a clearly labelled opening header from a PDF conversion, for a limited set of fields

For Save as eBook, save the work’s **Entire Work** snapshot (`?view_full_work=true`); otherwise, the EPUB may contain only the chapter currently on screen.

Other sites and EPUB layouts may work, but haven’t been tested. The plugin skips metadata it can’t confidently recognize, so always review the preview before writing.

### FicLab metadata

FicLab's labeled summary table supplies story word/chapter counts, completion
status, and rating. Explicit copyright-page profile links supply author URLs and
IDs when they match the book's author names. Mixed tags are retained as ordinary
tags; the plugin does not guess which are fandoms, characters, or genres.

**Word Count uses the summary's story count.** FicLab's internal EPUB extent count
differs in all four samples; it is used only when the summary has no word count.
An invalid or conflicting summary count is left unset rather than silently
replaced with the other count.

Publication/update timestamps retain their recorded time-zone offsets. Calibre
may display them in local time: for example, December 29, 2012 at 23:59:29 UTC
is December 30 in UTC+01:00. The synthetic timestamp-day-boundary example covers
this case. If timestamps are missing,
the reader can use FicLab's displayed English dates without inventing an offset.
FanFicFare's Saved Metadata reader cannot load offsets in its date fields. Those
fields use UTC without an offset suffix; the saved record also keeps the original
offset-bearing timestamps as text. Calibre's direct standard/custom writes retain
the full timestamps.
Other FicLab source sites, ongoing works, and altered layouts have not yet been
checked with real samples.

## Supported TXT archives

TXT files with this opening header structure are supported directly; conversion
to EPUB is not required:

```text
Story title

by Author name

Category: Fandom name
Language: English
Status: Completed
Published: 2013-02-18
Words: 1,234
Story URL: https://www.fanfiction.net/s/1234567/1/
Summary: The archive's summary, on a single line.

Chapter text begins here.
```

Explicit `Title:` and `Author:` labels also work. Recognition requires a title,
an author, and at least two additional factual labels. Fields are optional apart
from that minimum. Their order, capitalization, and surrounding spaces may vary.
Supported fields include category/fandom, genre, language, characters,
relationships/ships, warnings, status, published/updated/packaged dates, rating,
chapter count, word count, publisher, story URL, author URL, and summary/description.
`Word Count` and `Chapter Count` are accepted aliases.

For this compact format, the metadata block must be contiguous, with one
`Label: value` per line. The first blank or ordinary text line ends it. Its summary
must be on one line. Seven distinct fanfiction.net examples in English and Spanish
have been checked.

Two additional layouts are recognized separately:

- **Spaced archive headers:** title and author on one line (`Title by Author`),
  blank lines between labeled fields, wrapped values, and a separate Summary
  section. A repeated story title must mark the end of the summary before chapter
  text. Checked against three privately retained source examples. Wrapped relationship
  slashes are rejoined; OCR spelling and punctuation are preserved as supplied.
- **PDF-style prefaces:** an opening “Posted originally on…” notice with an AO3
  or SquidgeWorld work URL, labeled metadata, and a repeated title/byline before
  the summary. PDF-style `Category` means pairing category (such as M/M), while
  `Fandom` is kept separately. A summary is recovered only when a recognizable
  section heading marks its end. Explicit series positions and stats are supported;
  missing dates, status, chapter counts, and author URLs are not invented.

If PDF text separates labels and values into detached columns, only reliable
fields are recovered: title, explicit story URL, labeled dates/counts, and a bounded
summary. Author, language, rating, and tag fields are omitted; the preview explains
the partial recovery. Public synthetic examples cover both the detached-column
layout and the clearly labeled PDF layout, alongside private source-file checks.
Notice-heavy saved web pages with largely unlabelled metadata remain unsupported.

Only the first 64 KiB and 200 lines are inspected. UTF-8, BOM-marked UTF-16, and
Windows-1252 text are supported. Conflicting duplicate fields are omitted;
unrecognized layouts are skipped with an explanation. These readers do not cover
every TXT archive format. Status and dates describe the saved copy, not the story's
current state online. Missing URLs and damaged names are not reconstructed from
filenames. Without a supported story URL in the header or Calibre's existing
identifiers, Saved Metadata is skipped; standard metadata and mapped custom columns
remain available.

When a book has both EPUB and TXT, EPUB takes precedence. TXT is used only when
the book has no EPUB; an unreadable EPUB does not trigger a TXT fallback.

## What it writes

The three write modes are independent and can be combined:

1. **Save extracted metadata** (on by default) stores metadata in FanFicFare’s Saved Metadata format. You can then run FanFicFare’s **Update Calibre Metadata from Saved Metadata Column** action to apply your existing FanFicFare settings, including `personal.ini` replacements and custom-column mappings.
2. **Update standard Calibre metadata** (off by default) writes fields such as Title, Author, Tags, Series, and Comments using FanFicFare’s default AO3 mapping.
3. **Update custom columns** (off by default) writes selected recovered fields, such as fandom, word count, or rating, to columns you choose.

The default mode only changes the Saved Metadata column. Standard fields and mapped columns are opt-in.

Enabling all three modes writes recovered values directly and also stages Saved
Metadata for FanFicFare. Direct standard/custom updates do not run your
FanFicFare `personal.ini` replacements or calculated mappings. To apply those
rules, run FanFicFare's **Update Calibre Metadata from Saved Metadata Column**
afterward. That later action can replace direct values with your transformed ones.

The plugin only reads metadata already in the book file; it does not download stories or replace FanFicFare. When only Saved Metadata is enabled, it does not directly change Title, Tags, Comments, or other standard Calibre fields.

## Install

Requires **Calibre 6.0 or newer**. The plugin has been checked on Calibre 6.0 and 9.15 for macOS, with additional user testing in Calibre Zen.

Download `extract_epub_metadata-v1.0.0.zip` from the [Releases page](https://github.com/wordsandpics/Extract-epub-metadata/releases). In Calibre, choose **Preferences → Plugins → Load plugin from file** and select the downloaded ZIP.

Use the ZIP under the release’s **Assets**. GitHub’s automatic **Source code (zip)** archive is not installable by Calibre.

## Configure

Open **Preferences → Plugins → Extract EPUB Metadata → Customize plugin**.

- **Save extracted metadata:** Choose the Long Text custom column also configured as FanFicFare’s Saved Metadata column. Existing values are kept unless you enable overwrite.
- **Update standard metadata:** Existing values are kept unless you enable overwrite. Blank publication dates and Calibre’s “Unknown” author are treated as empty.
- **Update custom columns:** Map supported custom columns to compatible recovered fields. Unmapped columns are left alone.
- **Add missing story-URL identifier:** On by default; adds a `url` identifier only when one is missing.
- **Preview before writing:** On by default; lets you review the changes before anything is written.
- **Show confirmation after writing:** On by default; summarizes the results.

When FanFicFare is installed, the plugin checks its local adapter registry before staging Saved Metadata. It uses the Calibre URL or URI first, then the URL recovered from the book file. Unsupported URLs are skipped with an explanation. Without FanFicFare, support for other hosts is marked unverified.

## Use

Select one or more books with an EPUB or a supported TXT archive and choose **Extract Metadata** from the toolbar button. Review the preview and confirm the changes. If you used the Saved Metadata mode, run FanFicFare’s **Update Calibre Metadata from Saved Metadata Column** afterward.

The toolbar menu also includes **Extract story status from anthology** and **Configure…**.

## Anthologies and series collections

**Extract Metadata** recognizes epubmerge anthologies and EPUBs whose primary URL is a series URL. A story that merely links to a series is still treated as an ordinary story.

Collection title, authors, language, tags, and description come from the outer EPUB metadata. Embedded stories may provide individual authors, URLs, summaries, dates, statuses, and counts. WebToEpub series EPUBs may contain only a saved series page; in that case, the plugin uses explicit collection totals and dates when available rather than inventing individual story details.

The ordinary **Word Count** mapping uses the total for the collection. A calculated total is written only when every embedded story has a reliable count. Additional collection fields include work count, completed count, unknown statuses, total chapters, collection URL, and series dates.

FanFicFare’s Saved Metadata import expects one story URL, so Saved Metadata is skipped for collections. Use standard metadata or custom-column updates instead. Ratings, warnings, and summaries remain associated with individual stories rather than being combined into collection-wide values.

Existing anthology identifiers are preserved. Collection previews show which values will be written or kept; books with no eligible changes can’t be selected for writing.

### Anthology status report

This separate action reads the status of individual stories inside epubmerge anthologies and writes a compact report to a column you choose. It has its own destination, overwrite, preview, and confirmation settings on the **Anthology Status** tab.

The report includes completion counts and, when available, story authors, URLs, dates, chapter counts, and word counts. Long summaries, ratings, and warnings appear in the detailed preview. Unknown statuses are reported separately. Non-anthology books are skipped with an explanation.

## Known limitations

- fanfiction.net crossover EPUBs made with WebToEpub currently recover only the last fandom in the site breadcrumb.
- Other sites and EPUB layouts may yield incomplete metadata. A field may be skipped without an error if its format isn’t recognized.
- The PDF-reflow fallback does not infer publication dates or completion status, and skips approximate counts such as `~3400`.
- For Wayback snapshots, the plugin uses the original story URL as the story URL and retains the snapshot URL separately as `waybackUrl`. Status and counts reflect the snapshot date. FanFicFare exposes `waybackUrl` to `personal.ini` templates only if you add it to `extra_valid_entries`.

Always review the preview before writing.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Running tests

Run the standard-library test suite with:

```sh
python3 -m unittest discover -s tests -v
```

The suite runs without Calibre installed and uses only synthetic EPUB and TXT examples in `tests/fixtures/`. Their filenames and titles identify the test cases. No original stories or private files are required. An optional test also checks FanFicFare’s metadata loader when FanFicFare is installed.

See the [fixture catalogue](FIXTURE-INVENTORY.md). Recreate the examples with `python3 tests/build_fixtures.py`; this uses only the standard library and invented scenario data. Optional local checks against privately retained originals are described in the catalogue.


For a real Calibre check, set `CALIBRE_CONFIG_DIRECTORY` to a configuration in a
**temporary folder**, install FanFicFare and a ZIP built from the contents of
`extract_epub_metadata/` there, then run `tests/calibre_smoke.py` using
`calibre-debug -e`. Set `QT_QPA_PLATFORM=offscreen` to keep its windows off screen.
The harness refuses to run against a regular configuration and creates a temporary
library. It checks EPUB and TXT previews, database writes, and FanFicFare imports.
Set `EXTRACT_METADATA_SCREENSHOTS` to an output folder to save preview screenshots.
