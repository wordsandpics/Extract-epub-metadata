# Extract Epub Metadata 1.2.0

You can now recover metadata directly from AO3-generated PDFs, using the same
preview and Saved Metadata, standard metadata and custom-column options.

This update also improves recovery from AO3 HTML files converted to EPUB,
including titles, authors, summaries, categories and story URLs.

## Install or update

Download **extract_epub_metadata-v1.2.0.zip** under Assets. In Calibre, open
**Preferences → Plugins → Load plugin from file**, select the ZIP, then restart.
Existing plugin settings are preserved.

## Notes

- EPUB takes priority, followed by TXT, then PDF. PDF recovery reads only the
  opening pages; scanned PDFs and browser printouts are not supported.
- For HTML, import into Calibre and convert to EPUB before running extraction.
- Recovery depends on the metadata present. Review the preview before writing;
  ambiguous fields may be omitted with an explanation.
- Requires Calibre 6.0 or newer. Checked on Calibre 9.15 for macOS, with additional
  PDF testing in Calibre Zen. Calibre 6, Windows and Linux were not rechecked.
