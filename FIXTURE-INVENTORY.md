# Synthetic fixture catalogue

All public fixtures contain invented metadata and short placeholder text. Their filenames and book titles identify the layout or regression case. They contain no original story text, covers or other embedded images. Site hostnames and URL shapes are retained where needed to exercise adapter recognition; the test suite never downloads the stories. Counts describe test inputs and need not match the length of the placeholder chapter.

## Layouts and variations

`tests/build_fixtures.py` shares builders across formats; `tests/fixture_cases.json` declares the scenarios. There are 48 generated EPUB/TXT examples plus one synthetic Saved Metadata HTML reference. Named variations retain existing regression coverage for dates, missing URLs, multiple authors, collections, wrapped fields and source priorities.

| Fixture | Layout |
|---|---|
| `ao3-native-complete.epub` | native |
| `ao3-split-coauthors.epub` | native |
| `ao3-anonymous-singular-tags.epub` | native |
| `fff-bold-packaged-date.epub` | fff bold |
| `titlepage-paragraph-summary.epub` | fff para |
| `titlepage-unknown-total-41.epub` | fff para |
| `titlepage-unknown-total-16.epub` | fff para |
| `fichub-ffnet-composite.epub` | intro |
| `ffnet-webtoepub-profile.epub` | ffnet |
| `fff-cover-before-title.epub` | fff bold |
| `ao3-wayback-information.epub` | work |
| `ao3-wayback-whole-page.epub` | work |
| `ao3-pdf-wrapped-preface.epub` | pdf |
| `opf-only-no-markers.epub` | opf |
| `anthology-multiple-authors.epub` | anthology |
| `anthology-mixed-status.epub` | anthology |
| `txt-compact-complete.txt` | compact |
| `txt-compact-packaged-date.txt` | compact |
| `txt-compact-missing-url.txt` | compact |
| `txt-compact-spanish-ongoing.txt` | compact |
| `txt-compact-spanish-complete.txt` | compact |
| `txt-compact-author-digits.txt` | compact |
| `txt-compact-title-punctuation.txt` | compact |
| `txt-spaced-missing-url.txt` | spaced |
| `txt-spaced-wrapped-tags.txt` | spaced |
| `txt-spaced-multiple-fandoms.txt` | spaced |
| `txt-pdf-squidgeworld.txt` | txt pdf |
| `txt-pdf-detached-partial.txt` | partial |
| `txt-unsupported-notices.txt` | unsupported |
| `ficlab-multichapter-count-priority.epub` | ficlab |
| `ficlab-timestamp-day-boundary.epub` | ficlab |
| `ficlab-rating-k-plus.epub` | ficlab |
| `ficlab-mixed-tags.epub` | ficlab |
| `ao3-information-thin-space.epub` | work |
| `ao3-series-collection.epub` | series |
| `ao3-information-ongoing.epub` | work |
| `anthology-outer-status-tag.epub` | anthology |
| `anthology-complete.epub` | anthology |
| `ao3-series-navigation.epub` | work |
| `fichub-ao3-summary-entities.epub` | intro |
| `ao3-browser-space-counts.epub` | work |
| `titlepage-paragraph-ffnet.epub` | fff para |
| `titlepage-unicode.epub` | fff para |
| `titlepage-ongoing.epub` | fff para |
| `fichub-ao3-introduction.epub` | intro |
| `fichub-ao3-completed.epub` | intro |
| `ao3-native-ongoing.epub` | native |
| `pdf-labelled-header.epub` | pdf header |

## Rebuild and check

For format-specific behavior and isolated Calibre test instructions, see
[Format notes and testing](DEVELOPMENT.md).

```sh
python3 tests/build_fixtures.py
python3 -m unittest discover -s tests -v
```

The generator uses only the standard library and public scenario data. It does not read private examples or call the extractor to obtain expected values. Rebuilding produces identical EPUB bytes. To rebuild separately for comparison, use `python3 tests/build_fixtures.py --output /tmp/synthetic-fixture-comparison`. It writes only its named outputs; it does not clean unrelated files from the destination.

For the isolated Calibre workflow, follow [Format notes and testing](DEVELOPMENT.md). It imports only the synthetic fixtures.
