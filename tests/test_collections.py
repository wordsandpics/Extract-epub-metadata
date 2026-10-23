"""Synthetic fixture regressions; run with unittest discovery."""
import io
import sys
import unittest
from pathlib import Path
from zipfile import ZipFile
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'calibre_stub'))
sys.path.insert(0, str(HERE.parent))
from extract_epub_metadata.calibre_fields import compute_custom_column_values, compute_standard_fields
from extract_epub_metadata.collections import extract_collection
from extract_epub_metadata.extractors._numbers import parse_count
from extract_epub_metadata.mapping import extract_fields
from extract_epub_metadata.serialize import serialize_saved_metadata
FIXTURES = HERE / 'fixtures'
FRESH = FIXTURES
MULTI = FIXTURES / 'anthology-multiple-authors.epub'

class CollectionExtractionTest(unittest.TestCase):

    def test_multi_author_records_and_complete_totals(self):
        fields, sources = extract_fields(MULTI)
        self.assertEqual(fields['author'], ['TestWriter14', 'TestWriter15'])
        self.assertEqual(fields['collectionStoryCount'], 5)
        self.assertEqual(fields['collectionCompletedCount'], 5)
        self.assertEqual(fields['collectionUnknownCount'], 0)
        self.assertEqual(fields['numWords'], 93149)
        self.assertEqual(fields['collectionChapterCount'], 66)
        records = fields['collectionRecords']
        self.assertEqual([r['author'] for r in records], [['TestWriter14']] * 2 + [['TestWriter14', 'TestWriter15']] * 3)
        self.assertTrue(all((r.get('description') for r in records)))
        self.assertEqual(records[0]['rating'], 'Teen And Up Audiences')
        self.assertEqual(records[-1]['rating'], 'Explicit')
        self.assertEqual(sources['numWords'], 'collection_stories')
        for key in ('rating', 'warnings', 'storyUrl', 'numChapters', 'status', 'datePublished'):
            self.assertNotIn(key, fields)
        with self.assertRaises(ValueError):
            serialize_saved_metadata(fields)

    def test_mixed_completion_does_not_become_first_story_status(self):
        fields, _ = extract_fields(FIXTURES / 'anthology-mixed-status.epub')
        self.assertEqual(fields['collectionStoryCount'], 7)
        self.assertEqual(fields['collectionCompletedCount'], 6)
        self.assertEqual(fields['collectionRecords'][-1]['status'], 'In-Progress')
        self.assertNotIn('datePublished', fields['collectionRecords'][-1])
        self.assertNotIn('status', fields)

    def test_series_page_facts_without_fabricated_story_records(self):
        fields, sources = extract_fields(FRESH / 'ao3-series-collection.epub')
        self.assertEqual(fields['collectionType'], 'series collection')
        self.assertEqual(fields['collectionStoryCount'], 2)
        self.assertEqual(fields['numWords'], 11822)
        self.assertEqual(fields['collectionStatus'], 'In-Progress')
        self.assertEqual(fields['collectionDateBegun'].isoformat(), '2018-11-24T00:00:00')
        self.assertEqual(fields['collectionDateUpdated'].isoformat(), '2019-05-31T00:00:00')
        self.assertEqual(sources['collectionStatus'], 'collection_series_page')
        for key in ('collectionRecords', 'collectionCompletedCount', 'collectionChapterCount', 'storyUrl'):
            self.assertNotIn(key, fields)

    def test_work_with_series_link_stays_single_story(self):
        fields, _ = extract_fields(FRESH / 'ao3-information-thin-space.epub')
        self.assertNotIn('collectionType', fields)
        self.assertEqual(fields['storyUrl'], 'https://archiveofourown.org/works/98000408')
        self.assertIn('series', fields)

    def test_missing_story_count_prevents_partial_total(self):
        buf = io.BytesIO()
        with ZipFile(MULTI) as source, ZipFile(buf, 'w') as target:
            for name in source.namelist():
                data = source.read(name)
                if name == '1/OEBPS/title_page.xhtml':
                    data = data.replace(b'572', b'unknown')
                target.writestr(name, data)
        buf.seek(0)
        fields, _ = extract_fields(buf)
        self.assertNotIn('numWords', fields)
        self.assertEqual(fields['collectionChapterCount'], 66)

    def test_outer_tags_remain_tags_without_changing_status(self):
        fields, _ = extract_fields(FRESH / 'anthology-outer-status-tag.epub')
        computed = compute_standard_fields(fields)
        self.assertEqual(computed['tags'], sorted(set(fields['collectionTags'])))
        self.assertEqual(fields['collectionCompletedCount'], 2)
        self.assertIn('In-Progress', computed['tags'])
        self.assertNotIn('pubdate', computed)
        self.assertNotIn('series', computed)

    def test_custom_columns_use_collection_keys_and_accept_zero(self):
        fields, _ = extract_fields(MULTI)
        columns = {k: {'datatype': 'int'} for k in ('#words', '#count', '#unknown')}
        columns['#rating'] = {'datatype': 'text'}
        values = compute_custom_column_values(fields, {'#words': 'numWords', '#count': 'collectionStoryCount', '#unknown': 'collectionUnknownCount', '#rating': 'rating'}, columns)
        self.assertEqual(values, {'#words': 93149, '#count': 5, '#unknown': 0})

    def test_series_marker_uses_primary_url_not_an_incidental_link(self):
        with ZipFile(FRESH / 'ao3-series-collection.epub') as zf:
            result = extract_collection(zf, {'identifiers': {'url': 'https://archiveofourown.org/works/123'}, 'dc_source': 'https://archiveofourown.org/series/98000411'})
            self.assertIsNone(result)
            fields, _ = extract_collection(zf, {'identifiers': {'uri': 'https://web.archive.org/web/20200101000000/https://archiveofourown.org/series/98000411'}})
            self.assertEqual(fields['collectionUrl'], 'https://archiveofourown.org/series/98000411')
            self.assertIn('waybackUrl', fields)

class FreshNumericTest(unittest.TestCase):

    def test_webtoepub_thin_space_words(self):
        fields, _ = extract_fields(FRESH / 'ao3-information-thin-space.epub')
        self.assertEqual(fields['numWords'], 111536)
        self.assertEqual(fields['numChapters'], 24)

    def test_save_as_ebook_space_words(self):
        path = next(FRESH.glob('ao3-browser-space-counts.epub'))
        fields, _ = extract_fields(path)
        self.assertEqual(fields['numWords'], 3334)
        self.assertEqual(fields['numChapters'], 1)

    def test_counts_reject_ambiguous_or_partial_values(self):
        for text in ('12/24', '12/?', 'about 100', '12 34', '1,23', '-5', '1.5', True):
            self.assertIsNone(parse_count(text), text)
        for text in ('1,234', '1 234', '1\u2009234', '1\xa0234', '1\u202f234'):
            self.assertEqual(parse_count(text), 1234, text)
        self.assertEqual(parse_count(0), 0)
if __name__ == '__main__':
    unittest.main()
