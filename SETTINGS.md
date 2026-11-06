# Settings and fields

Every setting in Extract Fanfic Metadata, and every field you can map to your own
columns. To open the settings, go to **Preferences → Plugins → Extract Fanfic
Metadata → Customize plugin**, or choose **Configure…** from the plugin's toolbar menu.

Fields are only filled when the file contains that information. Missing details are
left blank, never guessed.

## Extraction tab

You can turn on any combination of the three write options below. Each one has its
own overwrite setting.

### Save all extracted metadata

Saves everything the plugin recovered as one block of data in a **Long text** column,
in the format FanFicFare uses for its Saved Metadata. Your library's title, tags and
other fields are not changed. Use this if you use FanFicFare: run its **Update Calibre
Metadata from Saved Metadata Column** action afterwards to apply your FanFicFare
settings.

- **Saved Metadata Column:** choose the same Long text column that FanFicFare's own
  Saved Metadata Column setting uses.
- **Overwrite existing Saved Metadata:** when off, books that already have saved
  metadata are skipped.

Saved Metadata needs a story URL that FanFicFare supports. When one isn't found, the
preview explains why this book is skipped.

### Update standard Calibre metadata

Writes straight into Calibre's own fields:

| Calibre field | Filled from |
|---|---|
| Title | Title |
| Authors | Author(s) |
| Tags | Fandom(s), Relationship(s), Characters, Additional Tags, AO3 Category, genre, status and any extra tags, following FanFicFare's default rules |
| Comments | Summary |
| Series | Series |
| Published | Date Published |
| Languages | Language |

- **Overwrite existing standard metadata:** when off, fields that already have a
  value are left alone. Blank published dates and Calibre's "Unknown" author are
  still filled in. When on, recovered values replace existing ones, and Tags are
  replaced as a whole.

These direct updates don't apply your FanFicFare `personal.ini` changes. To use those,
save the extracted metadata instead and run FanFicFare's update action.

### Update custom columns

Writes chosen fields into your own columns, for example a Fandom column or a word
count column. Useful whether or not you use FanFicFare.

- **Configure column mapping…:** pick a column for each field you want. Each field
  only lists columns of a suitable type. See [Fields](#fields) below.

A column can't be both the Saved Metadata column and a mapped column.

### Other options

- **Add missing story-URL identifier:** adds the recovered story URL to the book's
  identifiers when it has none. An existing identifier is never replaced. FanFicFare
  uses this URL to recognize the story's site. This applies whichever write options are on.
- **Preview before writing:** shows everything that would change, book by book, before
  anything is written. You can uncheck books to skip them.
- **Show confirmation after writing:** shows a short summary of how many books were
  updated.

## Anthology Status tab

Settings for the separate **Extract story status from anthology** action. It reports
the completion status of each story inside an anthology EPUB made by FanFicFare, since
the anthology's own status only describes the whole bundle.

- **Destination Column:** a Long text column for the report. It must be different
  from the Saved Metadata column.
- **Overwrite existing column value:** when off, books that already have a report are
  skipped.
- **Preview before writing** and **Show confirmation after writing:** as on the
  Extraction tab. Books that aren't anthologies show in the preview unchecked, with a note.

## Fields

These are the fields you can map in **Configure column mapping…**. The column type is
what Calibre calls it when you create a column.

**Which column types work**

| Field holds | Suitable column types |
|---|---|
| Text | Text; Long text; Series (for Series only); Text with a fixed set of permitted values (only when the value is one of them) |
| A list | Comma separated text, like tags (each value kept separate). Text and Long text also work; the values are joined into one line. |
| A number | Integers; Floating point numbers |
| A date | Date |
| Yes/no | Yes/No |

### Story

| Field | What it holds | Holds |
|---|---|---|
| Title | The story's title. | Text |
| Summary | The story's summary. | Text (Long text suits it best) |
| Rating | Content rating, e.g. "Teen And Up Audiences" or "Mature". | Text |
| Archive Warnings | Archive warnings, e.g. "Major Character Death". | A list |
| Language | Full language name, e.g. "English". | Text |
| Language Code | Short language code, e.g. "en". | Text |
| Status | "Completed" or "In-Progress". | Text |
| Completed? (yes/no) | Yes if the status is "Completed", no otherwise. | Yes/no |
| Series | First series this work is part of, as "Name [N]". A Series column splits out the number itself. | Text |
| Series URL | Link to that series' page. | Text |

### Authors

| Field | What it holds | Holds |
|---|---|---|
| Author(s) | Each author's name, kept separate. | A list |
| Byline | All author names as one line of text, e.g. "Name1, Name2". | Text |
| Author ID | The site's username for each author. | A list |
| Author URL | Link to each author's profile. | A list |

**Author(s) or Byline?** Both hold the same names. Use Author(s) for a column that
holds several values, so you can search and sort by each author. Use Byline for a plain
text column. Some saved AO3 pages keep the byline as written, including the account
name, e.g. "pseud (username)".

### Tags and categories

| Field | What it holds | Holds |
|---|---|---|
| Fandom(s) | The fandom(s) or canon(s) the story is set in. | A list |
| Relationship(s) | Relationships or pairings, as tagged on the site. | A list |
| Characters | Characters, as tagged on the site. | A list |
| Additional Tags | AO3's freeform or additional tags. | A list |
| AO3 Category (M/M, F/F, Gen...) | AO3's relationship category, e.g. "M/M", "F/F", "Gen". | A list |

**Fandom or AO3 Category?** AO3 Category is the M/M, F/F, Gen label, not the fandom.
FanFicFare's title pages list the fandom under "Category". For AO3 and fanfiction.net
books, the plugin puts that into Fandom(s).

### Counts and dates

| Field | What it holds | Holds |
|---|---|---|
| Word Count | The story's word count. For anthologies and collections, a reliable total across all stories, or a total stated on a saved series page. | A number |
| Chapter Count | Number of chapters in the saved copy. | A number |
| Total Chapters (if known) | The planned final chapter count, only when the file states one. Blank, not zero, for a work still in progress with no set total. | A number |
| Chapters (Downloaded/Total) | Chapters saved vs. total chapters, e.g. "12/20". | Text |
| Date Published | When the story was first published, as recorded in the file. | A date |
| Date Updated | When the story was last updated, as recorded in the file. | A date |
| Last Update (text) | Last-update text FanFicFare uses, e.g. "Last Update Year/Month: 2024/03". | A list |
| Date Recovered | When the file was downloaded, if it records this; otherwise when the plugin ran. Not a date from the story itself. | A date |

**Which chapter field?** Chapter Count is how many chapters you have. Total Chapters is
how many the story will have, when known. Chapters (Downloaded/Total) shows both as text.

### Links, site and file

| Field | What it holds | Holds |
|---|---|---|
| Story URL | Link to the original story. | Text |
| Story URL (Section) | Same as Story URL, unless only part of the story was recovered. | Text |
| Wayback Machine URL | The Internet Archive snapshot this copy came from, when it was saved from the Wayback Machine. | Text |
| Story ID | The site's ID number for this story. | Text |
| Site | The site the story was posted on, e.g. "archiveofourown.org". | Text |
| Site Abbreviation | Short site code FanFicFare uses, e.g. "ao3". | Text |
| File Format | The file the metadata came from: "epub", "txt" or "pdf". | Text |
| File Extension | The matching file extension, e.g. ".epub". | Text |

### Anthologies and series collections

These fields only apply to anthology and collection EPUBs and saved series pages.

| Field | What it holds | Holds |
|---|---|---|
| Collection URL | The anthology or series URL, not an individual story's. | Text |
| Collection Tags (from EPUB) | Tags recorded for the collection as a whole. | A list |
| Series Completion (from saved page) | Whether a saved series page marks the series complete. It doesn't describe each story. | Text |
| Collection Story/Work Count | Stories found in the collection, or the work count on a saved series page. | A number |
| Collection Completed Story Count | Stories known to be complete. Blank if no story's status is known. | A number |
| Collection Unknown Status Count | Stories with no recognizable completion status. | A number |
| Collection Total Chapters | Total chapters across all stories. Blank if any story's count is unknown. | A number |
| Series Begun (from saved page) | When the series was begun, from a saved series page. | A date |
| Series Updated (from saved page) | When the series was last updated, from a saved series page. | A date |
