"""Synthetic fixture regressions; run with unittest discovery."""
import datetime
import io
import sys
import unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / 'calibre_stub'), str(HERE.parent)]
from extract_epub_metadata.mapping import extract_txt_fields
from extract_epub_metadata.calibre_fields import compute_standard_fields, compute_custom_column_values
from extract_epub_metadata.fff_support import fff_import_support
from extract_epub_metadata.serialize import serialize_saved_metadata

def extract(text):
    return extract_txt_fields(io.BytesIO(text.encode('utf-8')))[0]

class TxtFixtureTest(unittest.TestCase):

    def test_compact_archive_stories(self):
        cases = [('txt-compact-complete.txt', 'Synthetic TXT Compact Complete', 'TestWriter17', 'en', 'Completed', 459, 1, '98000286', '2013-02-18'), ('txt-compact-packaged-date.txt', 'Synthetic TXT Compact Packaged Date', 'TestWriter18', 'en', 'In-Progress', 66818, 16, '98000291', '2014-06-08'), ('txt-compact-missing-url.txt', 'Synthetic TXT Compact Missing URL', 'TestWriter19', 'en', 'In-Progress', 26036, 7, None, '2013-04-04'), ('txt-compact-spanish-ongoing.txt', 'Synthetic TXT Compact Spanish Ongoing', 'TestWriter20', 'es', 'In-Progress', 2196, 1, '98000299', '2013-04-17'), ('txt-compact-spanish-complete.txt', 'Synthetic TXT Compact Spanish Complete — Café', 'TestWriter20', 'es', 'Completed', 3740, 8, '98000302', '2012-12-10'), ('txt-compact-author-digits.txt', 'Synthetic TXT Compact Author Digits', 'TestWriter21', 'en', 'Completed', 1025, 1, '98000305', '2009-07-13'), ('txt-compact-title-punctuation.txt', 'Synthetic TXT Compact Title Punctuation: A & B?', 'TestWriter22', 'en', 'Completed', 893, 1, '98000309', '2012-12-11')]
        for name, title, author, lang, status, words, chapters, story_id, published in cases:
            with self.subTest(name=name), (HERE / 'fixtures' / name).open('rb') as stream:
                fields, sources = extract_txt_fields(stream)
                self.assertEqual(fields['title'], title)
                self.assertEqual(fields['author'], [author])
                self.assertEqual(fields['langcode'], lang)
                self.assertEqual(fields['status'], status)
                self.assertEqual(fields['numWords'], words)
                self.assertEqual(fields['numChapters'], chapters)
                self.assertEqual(fields.get('storyId'), story_id)
                self.assertEqual(fields['datePublished'].date().isoformat(), published)
                self.assertIsInstance(fields['dateCreated'], datetime.datetime)
                self.assertEqual(fields['formatname'], 'txt')
                self.assertEqual(fields['formatext'], '.txt')
                self.assertEqual(fields['site'], 'fanfiction.net')
                self.assertEqual(fields['siteabbrev'], 'ffnet')
                self.assertEqual(sources['title'], 'txt_header')
                self.assertNotIn('warnings', fields)
                self.assertTrue(fields['description'])
                if story_id is None:
                    for key in ('storyUrl', 'authorUrl', 'authorId'):
                        self.assertNotIn(key, fields)
                    self.assertFalse(fff_import_support(fields.get('storyUrl')))
                    self.assertEqual(fields['characters'], ['TestCharacter22', 'TestCharacter23'])
                    self.assertEqual(fields['datePublished'].hour, 7)
                else:
                    self.assertIn('/s/' + story_id + '/', fields['storyUrl'])
                standard = compute_standard_fields(fields)
                self.assertEqual(standard['title'], title)
                self.assertIn(fields['status'], standard['tags'])
                self.assertEqual(fields['fandoms'], fields['category'])
                self.assertIn(fields['category'][0], standard['tags'])
                self.assertIn('comments', standard)
                custom = compute_custom_column_values(fields, {'#words': 'numWords'}, {'#words': {'datatype': 'int'}})
                self.assertEqual(custom['#words'], words)
                blob = serialize_saved_metadata(fields)
                self.assertIn("class='metadata int' id='numWords'>%s" % words, blob)
                self.assertIn("id='formatname'>txt", blob)

    def test_summary_is_exact_and_packaged_date_is_preserved(self):
        path = HERE / 'fixtures/txt-compact-packaged-date.txt'
        original = path.read_text()
        with path.open('rb') as stream:
            fields, _ = extract_txt_fields(stream)
        summary = next((line.removeprefix('Summary: ') for line in original.splitlines() if line.startswith('Summary: ')))
        self.assertEqual(fields['description'], summary)
        self.assertEqual(fields['dateCreated'], datetime.datetime(2014, 9, 11, 18, 6, 26))

class TxtPrefaceTest(unittest.TestCase):

    def read_fixture(self, prefix):
        path = next((p for p in (HERE / 'fixtures').iterdir() if p.name.startswith(prefix)))
        with path.open('rb') as stream:
            return extract_txt_fields(stream)

    def test_spaced_archive_headers_and_summary_boundaries(self):
        cases = [('txt-spaced-missing-url', 'Synthetic TXT Spaced Missing URL', 'TestWriter23', 373, 'Synthetic txt-spaced-missing-url summary.'), ('txt-spaced-wrapped-tags', 'Synthetic TXT Spaced Wrapped Tags', 'TestWriter24', 799, 'Synthetic txt-spaced-wrapped-tags summary.'), ('txt-spaced-multiple-fandoms', 'Synthetic TXT Spaced Multiple Fandoms', 'TestWriter25', 565, 'Synthetic txt-spaced-multiple-fandoms summary.')]
        for prefix, title, author, words, summary in cases:
            with self.subTest(prefix=prefix):
                fields, sources = self.read_fixture(prefix)
                self.assertEqual(fields['title'], title)
                self.assertEqual(fields['author'], [author])
                self.assertEqual(fields['numWords'], words)
                self.assertEqual(fields['description'], summary)
                self.assertEqual(fields['status'], 'Completed')
                self.assertEqual(fields['numChapters'], 1)
                self.assertEqual(fields['site'], 'archiveofourown.org')
                self.assertEqual(sources['title'], 'txt_spaced_header')
                self.assertNotIn('storyUrl', fields)
                self.assertNotIn('authorUrl', fields)
                self.assertNotIn('ao3categories', fields)

    def test_wrapped_tags_with_colons_and_relationship_slash(self):
        fields, _ = self.read_fixture('txt-spaced-wrapped-tags')
        self.assertEqual(fields['genre'], ['TestGenre18', 'TestGenre19', 'Test Genre: Colon Case 20', 'TestGenre21', 'TestGenre22', 'TestGenre23', 'M/M', 'TestGenre24', 'TestGenre25', 'TestGenre26', 'TestGenre27', 'TestGenre28', 'TestGenre29', 'TestGenre30'])
        self.assertEqual(fields['ships'], ['TestPair14 & TestPartner14', 'TestPair15/TestPartner15'])
        bundle, _ = self.read_fixture('txt-spaced-multiple-fandoms')
        self.assertEqual(bundle['fandoms'], ['TestFandom14', 'TestFandom13'])

    def test_squidgeworld_pdf_preface(self):
        fields, sources = self.read_fixture('txt-pdf-squidgeworld')
        self.assertEqual(fields['title'], 'Synthetic TXT PDF Squidgeworld')
        self.assertEqual(fields['author'], ['TestWriter26'])
        self.assertEqual(fields['storyUrl'], 'http://squidgeworld.org/works/98000345')
        self.assertEqual(fields['numWords'], 1422)
        self.assertEqual(fields['datePublished'], datetime.datetime(2021, 5, 28))
        self.assertEqual(fields['ao3categories'], ['M/M'])
        self.assertEqual(fields['fandoms'], ['TestFandom15'])
        self.assertEqual(fields['ships'], ['TestPair16/TestPartner16'])
        self.assertEqual(fields['warnings'], ['No Archive Warnings Apply'])
        self.assertEqual(fields['characters'], ['TestCharacter29', 'TestCharacter30'])
        self.assertIn('TestTag191', fields['freeformtags'])
        self.assertEqual(len(fields['freeformtags']), 16)
        self.assertEqual(fields['series'], 'TestSeries04 [18]')
        self.assertEqual(fields['description'], 'Synthetic txt-pdf-squidgeworld summary paragraph one.\n\nSynthetic paragraph two ends here.')
        self.assertEqual(sources['title'], 'txt_pdf_preface')
        for key in ('category', 'dateUpdated', 'status', 'numChapters', 'language', 'authorUrl'):
            self.assertNotIn(key, fields)
        self.assertNotIn('_txt_source', serialize_saved_metadata(fields))

    def test_detached_columns_only_recover_unambiguous_fields(self):
        fields, sources = self.read_fixture('txt-pdf-detached-partial')
        self.assertEqual(fields['title'], 'Synthetic TXT PDF Detached Partial')
        self.assertEqual(fields['storyUrl'], 'https://archiveofourown.org/works/98000347')
        self.assertEqual(fields['numWords'], 857)
        self.assertEqual(fields['numChapters'], 1)
        self.assertEqual(fields['numChaptersTotal'], 1)
        self.assertEqual(fields['status'], 'Completed')
        self.assertEqual(fields['datePublished'], datetime.datetime(2022, 1, 10))
        self.assertIn('—jTest?', fields['description'])
        self.assertEqual(fields['description'].count('\n\n'), 2)
        self.assertNotIn('Disculpen', fields['description'])
        self.assertEqual(sources['title'], 'txt_pdf_partial')
        for key in ('author', 'authorUrl', 'rating', 'warnings', 'ao3categories', 'fandoms', 'ships', 'characters', 'language', 'freeformtags', 'dateUpdated'):
            self.assertNotIn(key, fields)

    def test_notice_heavy_unlabeled_page_remains_unsupported(self):
        self.assertEqual(self.read_fixture('txt-unsupported-notices'), ({}, {}))

    def test_prefaces_require_explicit_boundaries(self):
        spaced = 'Story by Writer\n\nCategory: Fandom\nLanguage: English\nWords: 2\nPublisher: archiveofourown.org\nSummary:\n\nText\n\n'
        self.assertEqual(extract(spaced), {})
        fields = extract(spaced + 'Story\n\nWords: 999\nRating: Fake\n')
        self.assertEqual(fields['numWords'], 2)
        self.assertNotIn('rating', fields)

    def test_pdf_without_notes_does_not_swallow_story_as_summary(self):
        fields = extract('Story\nPosted originally on the Archive of Our Own at https://archiveofourown.org/works/123.\n\nRating: General Audiences\nFandom: Example\nStats: Published: 2020-01-01 Words: 2\n\nStory\nby Writer\n\nSummary\n\nCould be summary or story\n')
        self.assertEqual(fields['title'], 'Story')
        self.assertNotIn('description', fields)
        self.assertNotIn('dateUpdated', fields)

    def test_conflicting_pdf_counts_do_not_infer_completion(self):
        fields = extract('Story\nPosted originally on the Archive of Our Own at https://archiveofourown.org/works/123.\n\nRating: General Audiences\nFandom: Example\nStats: Words: 2 Chapters: 1/1\nChapters: 2/2\n\nStory\nby Writer\n\nSummary\n\nSummary text\n\nNotes\n')
        self.assertEqual(fields['numWords'], 2)
        for key in ('numChapters', 'numChaptersTotal', 'chapterslashtotal', 'status'):
            self.assertNotIn(key, fields)

class TxtBoundaryTest(unittest.TestCase):

    def test_labels_aliases_spacing_and_literal_summary(self):
        fields = extract('\ufeff  tItLe : A <B> & C\r\nAUTHOR: Writer, Jr.\r\nWORD COUNT : 1,234\r\nFandom: TestFandom11\r\nDescription: A - Rating: T <literal>\r\nExtra: ignored\r\n\r\nRating: M\r\nWords: 999\r\n')
        self.assertEqual(fields['title'], 'A <B> & C')
        self.assertEqual(fields['author'], ['Writer, Jr.'])
        self.assertEqual(fields['numWords'], 1234)
        self.assertEqual(fields['fandoms'], ['TestFandom11'])
        self.assertEqual(fields['description'], 'A - Rating: T <literal>')
        self.assertNotIn('rating', fields)
        self.assertIn('&lt;literal&gt;', compute_standard_fields(fields)['comments'])

    def test_title_with_colon_and_unknown_optional_label(self):
        fields = extract('Story: the beginning\n\nby A\n\nLanguage: English\nArchive Notes: ignored\nWords: 2\n\nBody')
        self.assertEqual(fields['title'], 'Story: the beginning')
        self.assertEqual(fields['numWords'], 2)

    def test_invalid_values_are_omitted_without_guessing(self):
        fields = extract('Title: Story\nAuthor: A\nWords: ~3400\nPublished: 2013-99-99\nStatus: Unknown\nStory URL: javascript:bad\nAuthor URL: not a URL\n\nBody')
        self.assertEqual(fields['title'], 'Story')
        for key in ('numWords', 'datePublished', 'status', 'storyUrl', 'authorUrl', 'storyId'):
            self.assertNotIn(key, fields)

    def test_conflicting_fields_are_omitted(self):
        fields = extract('Title: Story\nAuthor: A\nWords: 1\nWord Count: 2\nLanguage: English\nWords: 1\n\nBody')
        self.assertNotIn('numWords', fields)

    def test_unrecognized_opening_does_not_search_later(self):
        for text in ('Ordinary story text\n\nTitle: Story\nAuthor: A\nWords: 2\nRating: T\n\n', 'Story\nby A\n\nSummary: prose only\n\n', 'Summary: prose\nRating: T\nWords: 2\n\n'):
            with self.subTest(text=text):
                self.assertEqual(extract(text), {})

    def test_utf16_and_legacy_windows_text(self):
        text = 'Synthetic Café Encoding\nby A\n\nLanguage: Spanish\nWords: 2\n\nBody'
        for encoding in ('utf-16', 'utf-8-sig', 'cp1252'):
            with self.subTest(encoding=encoding):
                fields, _ = extract_txt_fields(io.BytesIO(text.encode(encoding)))
                self.assertEqual(fields['title'], 'Synthetic Café Encoding')
                self.assertEqual(fields['langcode'], 'es')

    def test_read_is_bounded_and_incomplete_long_header_is_rejected(self):
        data = b'Title: Story\nAuthor: A\nLanguage: English\nWords: 2\n' + b'Note: x\n' * 20000
        stream = io.BytesIO(data)
        self.assertEqual(extract_txt_fields(stream), ({}, {}))
        self.assertLessEqual(stream.tell(), 65536)
if __name__ == '__main__':
    unittest.main()
