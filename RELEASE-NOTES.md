# Extract Epub Metadata 1.1.0

Recover metadata directly from supported TXT archive headers and FicLab EPUBs.

## New

- **TXT support:** read recognizable opening archive headers directly, including
  compact headers, spaced/wrapped headers and AO3/SquidgeWorld PDF-style prefaces.
  There is no need to convert supported TXT files to EPUB first.
- **Partial TXT recovery:** when PDF text has detached columns, recover explicit
  facts and explain which ambiguous fields were omitted.
- **FicLab EPUB support:** recover labeled counts, status, rating, matching author
  profiles and mixed tags from marked front matter. Preserve source timestamps;
  prefer summary story word counts over the EPUB extent count.

## Fixed

- Refresh the book list, Book Details and tag browser after writes, so fields such
  as word count and chapters appear without running FanFicFare afterward.

## Install or update

Download **extract_epub_metadata-v1.1.0.zip** under Assets. In Calibre, open
**Preferences → Plugins → Load plugin from file**, select the ZIP, then restart
Calibre. Existing plugin settings are preserved.

Requires Calibre 6.0 or newer. This release is checked on Calibre 9.15 for macOS;
preview builds received additional testing in Calibre Zen. Windows, Linux and
Calibre 6.0 were not rechecked for this release.

## Notes

- EPUB remains preferred when a book has both EPUB and TXT.
- Recovery depends on the saved file’s layout and available fields; TXT support
  does not cover every archive format. Missing URLs and ambiguous metadata are
  not guessed.
- Enable **Update standard Calibre metadata** to write recovered author names to
  Authors. Existing values are kept unless standard overwrite is enabled.
- Direct writes do not apply FanFicFare personal.ini transformations. Run
  FanFicFare’s Update from Saved action afterward if you use those rules.
- The plugin does not download stories. The installable ZIP includes only plugin
  files; the repository’s public test examples are synthetic.
