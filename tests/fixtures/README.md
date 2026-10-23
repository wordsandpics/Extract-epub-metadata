# Synthetic metadata examples

These files are invented test cases, not real fanfiction. Filenames and book titles describe the format or behavior being tested. Story text and summaries are placeholders; numerical metadata is deliberately chosen for regression tests.

See [the fixture catalogue](../../FIXTURE-INVENTORY.md) for each scenario. Rebuild the EPUB/TXT files and Saved Metadata reference with:

```sh
python3 tests/build_fixtures.py
```

No private files or network connection are required. The generator writes deterministic EPUBs with no images. It keeps format markers needed by the parsers. URL shapes refer to supported sites solely to test recognition; no downloads occur.
