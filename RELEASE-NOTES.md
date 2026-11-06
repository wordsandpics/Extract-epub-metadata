# Extract Fanfic Metadata 1.2.2

## Fixed

- **Fandom from FanFicFare EPUBs.** FanFicFare's title page lists the fandom under
  "Category" rather than "Fandom", so it was missed for AO3 and fanfiction.net books.
  It now fills your Fandom column and is added to Tags. Other sites use Category for
  their own labels, so those are left alone. (Issue #2)
- **Translation credits.** A test now confirms that people credited for translations
  or related works are not added as authors. The fix itself shipped in 1.2.0. (Issue #3)

## Changed

- The mapping field for AO3's M/M, F/F, Gen label is now called
  **AO3 Category (M/M, F/F, Gen...)**, so it isn't mistaken for the fandom.
  Your existing column mappings are kept.

## New

- A [Settings and fields](https://github.com/wordsandpics/Extract-fanfic-metadata/blob/main/SETTINGS.md)
  guide explains every setting and every field you can map to a column.
- Every field in the column mapping now has hover help.

## Install

Download **extract_fanfic_metadata-v1.2.2.zip** under Assets. In Calibre, open
**Preferences → Plugins → Load plugin from file**, select the ZIP, then restart.

If you still have the old **Extract Epub Metadata** installed, remove it in
**Preferences → Plugins** after installing. Your settings and toolbar button are kept.

## Notes

- Requires Calibre 6.0 or newer. Checked on Calibre 9.15 for macOS and in Calibre Zen.
  Windows and Linux were not rechecked.
