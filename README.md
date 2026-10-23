# Extract EPUB Metadata

Recover metadata already stored in your fanfiction EPUBs and TXT archives and add it to Calibre. Useful for saved stories that are missing metadata or can no longer be downloaded.

You can recover fields such as author, fandom, tags, summary, word count and chapters, depending on what the file contains. The plugin does not download stories.

## Supported files

Supports common AO3 and fanfiction.net EPUB layouts, including FanFicFare, ao3downloader, Fichub, WebToEpub and FicLab exports, plus some saved web pages and PDF-to-EPUB conversions.

TXT archives with recognizable metadata at the beginning can be read directly—no EPUB conversion needed. If a book has both formats, EPUB takes priority.

## Install

Requires **Calibre 6.0 or newer**. FanFicFare is optional.

Download the installable plugin ZIP from the latest release’s [Assets](https://github.com/wordsandpics/Extract-epub-metadata/releases/latest). In Calibre, open **Preferences → Plugins → Load plugin from file**, select the ZIP, then restart Calibre.

## Use

1. Open **Preferences → Plugins → Extract EPUB Metadata → Customize plugin** and choose what to update:

   - **Save extracted metadata:** Store it in the Long Text column you use for FanFicFare’s Saved Metadata.
   - **Update standard metadata:** Write fields such as Title, Authors, Tags, Series and Comments.
   - **Update custom columns:** Map recovered fields, such as word count or rating, to your own columns.

   You can combine these options. Existing values are kept unless you enable overwrite.

2. Select your books and choose **Extract Metadata** from the plugin’s toolbar button.

3. Review the preview, uncheck any books you want to skip, and confirm the changes.

### Using FanFicFare settings

Direct updates do not apply your FanFicFare `personal.ini` transformations. To use those, save the extracted metadata, then run FanFicFare’s **Update Calibre Metadata from Saved Metadata Column** action.

Saved Metadata needs a supported story URL. Standard fields and custom columns may still be updated without one.

## Anthologies

The plugin can recover collection metadata and available totals from supported anthologies and series collections. Use standard metadata or custom columns for these; FanFicFare’s Saved Metadata applies to individual stories.

The separate **Extract story status from anthology** action creates a report of the included stories and their completion status. Configure its destination column on the **Anthology Status** tab.

## What to expect

Recovery depends on the file’s contents and layout. Some fields may be missing, and some files may not be recognized. Status and counts describe the saved copy, not the story’s current state online.

Provided as-is, with limited support. Back up your library before making bulk changes. Issues and pull requests are welcome, but responses may be slow.

[Changelog](CHANGELOG.md) · [Testing and fixtures](FIXTURE-INVENTORY.md)
