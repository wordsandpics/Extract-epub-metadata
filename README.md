# Extract EPUB Metadata

Extract EPUB Metadata recovers metadata already stored in fanfiction EPUBs in your Calibre library. It can prepare metadata for FanFicFare, update standard Calibre fields, or fill custom columns. It does not download stories.

It’s useful when a story can’t be downloaded again or an EPUB is missing metadata in Calibre. What can be recovered depends on what the EPUB contains.

> Provided as-is, with limited support. Please back up your library or try a few books first. Issues and pull requests are welcome, but responses may be slow.

## Supported EPUBs

The plugin is built and tested primarily with Archive of Our Own (AO3) EPUBs, including downloads made with [ao3downloader](https://github.com/nianeyna/ao3downloader). It also supports:

- fanfiction.net EPUBs from [fichub.net](https://fichub.net) and the [WebToEpub browser extension](https://github.com/dteviot/WebToEpub)
- AO3 works saved from a [Wayback Machine](https://web.archive.org) snapshot using WebToEpub or [Save as eBook](https://chromewebstore.google.com/detail/save-as-ebook/haaplkpoiimngbppjihnegfmpejdnffj)
- AO3 PDF downloads converted to EPUB
- EPUBs with a clearly labelled opening header from a PDF conversion, for a limited set of fields

For Save as eBook, save the work’s **Entire Work** snapshot (`?view_full_work=true`); otherwise, the EPUB may contain only the chapter currently on screen.

Other sites and EPUB layouts may work, but haven’t been tested. The plugin skips metadata it can’t confidently recognize, so always review the preview before writing.

## What it writes

The three write modes are independent and can be combined:

1. **Save extracted metadata** (on by default) stores metadata in FanFicFare’s Saved Metadata format. You can then run FanFicFare’s **Update Calibre Metadata from Saved Metadata Column** action to apply your existing FanFicFare settings, including `personal.ini` replacements and custom-column mappings.
2. **Update standard Calibre metadata** (off by default) writes fields such as Title, Author, Tags, Series, and Comments using FanFicFare’s default AO3 mapping.
3. **Update custom columns** (off by default) writes selected recovered fields, such as fandom, word count, or rating, to columns you choose.

The default mode only changes the Saved Metadata column. Standard fields and mapped columns are opt-in.

The plugin only reads metadata already in the EPUB; it does not download stories or replace FanFicFare. When only Saved Metadata is enabled, it does not directly change Title, Tags, Comments, or other standard Calibre fields.

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

When FanFicFare is installed, the plugin checks its local adapter registry before staging Saved Metadata. It uses the Calibre URL or URI first, then the URL recovered from the EPUB. Unsupported URLs are skipped with an explanation. Without FanFicFare, support for other hosts is marked unverified.

## Use

Select one or more books with an EPUB and choose **Extract Metadata** from the toolbar button. Review the preview and confirm the changes. If you used the Saved Metadata mode, run FanFicFare’s **Update Calibre Metadata from Saved Metadata Column** afterward.

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

The suite runs without Calibre installed and uses EPUB fixtures in `tests/fixtures/`. An optional test also checks FanFicFare’s metadata loader when FanFicFare is installed.
