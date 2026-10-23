"""Synthetic fixture regressions; run with unittest discovery."""
import datetime
import io
import re
import sys
import unittest
from pathlib import Path
from zipfile import ZipFile
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / 'calibre_stub'), str(HERE.parent)]
from extract_epub_metadata.mapping import extract_fields
from extract_epub_metadata.calibre_fields import compute_standard_fields
from extract_epub_metadata.serialize import serialize_saved_metadata
FIXTURES = HERE / 'fixtures'
BASE = FIXTURES / 'ficlab-timestamp-day-boundary.epub'

def altered(transform, omitted=()):
    output = io.BytesIO()
    with ZipFile(BASE) as source, ZipFile(output, 'w') as target:
        for name in source.namelist():
            if name in omitted:
                continue
            data = source.read(name)
            if name.endswith(('.xhtml', '.opf')):
                data = transform(name, data.decode('utf-8')).encode('utf-8')
            target.writestr(name, data)
    output.seek(0)
    return extract_fields(output)

class FicLabTest(unittest.TestCase):

    def test_synthetic_ficlab_variants(self):
        cases = [('ficlab-multichapter-count-priority.epub', 101933, 23, 'Fiction M', '98000358', '2012-02-01T05:34:56+00:00', '2012-07-05T21:00:07+00:00'), ('ficlab-timestamp-day-boundary.epub', 4054, 1, 'Fiction T', '98000363', '2012-12-29T23:59:29+00:00', '2012-12-29T23:59:29+00:00'), ('ficlab-rating-k-plus.epub', 5661, 1, 'Fiction K+', '98000368', '2012-01-01T05:30:09+00:00', '2012-01-01T05:30:09+00:00'), ('ficlab-mixed-tags.epub', 2944, 1, 'Fiction K+', '98000373', '2010-08-17T15:51:19+00:00', '2010-08-17T15:51:19+00:00')]
        for filename, words, chapters, rating, author_id, published, updated in cases:
            with self.subTest(filename=filename):
                fields, sources = extract_fields(FIXTURES / filename)
                self.assertEqual(fields['numWords'], words)
                self.assertEqual(fields['numChapters'], chapters)
                self.assertEqual(fields['rating'], rating)
                self.assertEqual(fields['status'], 'Completed')
                self.assertEqual(fields['authorId'], [author_id])
                self.assertIn('/u/' + author_id + '/', fields['authorUrl'][0])
                self.assertEqual(fields['datePublished'].isoformat(), published)
                self.assertEqual(fields['dateUpdated'].isoformat(), updated)
                self.assertEqual(sources['numWords'], 'ficlab_summary')
                self.assertEqual(sources['datePublished'], 'ficlab_opf')
                self.assertEqual(sources['authorUrl'], 'ficlab_copyright')
                self.assertTrue(fields['extratags'])
                standard = compute_standard_fields(fields)
                self.assertIn('TestTag207', standard['tags'])
                self.assertIn('Complete', standard['tags'])
                for key in ('fandoms', 'characters', 'genre', 'ships'):
                    self.assertNotIn(key, fields)
                self.assertIn(published, serialize_saved_metadata(fields))

    def test_timestamp_offset_is_preserved(self):
        replacement = '2012-12-30T05:29:29+05:30'
        fields, _ = altered(lambda name, text: text.replace('2012-12-29T23:59:29Z', replacement) if name.endswith('.opf') else text)
        date = fields['datePublished']
        self.assertEqual(date.utcoffset(), datetime.timedelta(hours=5, minutes=30))
        self.assertEqual(date.isoformat(), replacement)
        self.assertEqual(date.astimezone(datetime.timezone.utc).isoformat(), '2012-12-29T23:59:29+00:00')
        blob = serialize_saved_metadata(fields)
        self.assertIn("class='metadata datetime' id='datePublished'>2012-12-29T23:59:29</div>", blob)
        self.assertIn("id='datePublishedSourceTimestamp'>" + replacement + '</div>', blob)
        self.assertEqual(fields['datePublished'].isoformat(), replacement)

    def test_summary_date_is_only_a_fallback(self):

        def remove_dates(name, text):
            if name.endswith('.opf'):
                text = re.sub('<meta property="dcterms:(?:date|issued|modified)">.*?</meta>', '', text)
                text = re.sub('<dc:date>.*?</dc:date>', '', text)
            return text
        fields, sources = altered(remove_dates)
        self.assertEqual(fields['datePublished'], datetime.date(2012, 12, 30))
        self.assertEqual(sources['datePublished'], 'ficlab_summary')
        self.assertEqual(fields['dateUpdated'], datetime.date(2012, 12, 30))

    def test_missing_summary_count_uses_extent(self):
        fields, sources = altered(lambda name, text: re.sub('<tr>\\s*<th>words</th>.*?</tr>', '', text, flags=re.S) if 'summary.xhtml' in name else text)
        self.assertEqual(fields['numWords'], 4235)
        self.assertEqual(sources['numWords'], 'ficlab_opf')

    def test_invalid_summary_count_does_not_silently_use_different_extent(self):
        fields, _ = altered(lambda name, text: text.replace('<td>4,054</td>', '<td>~4,000</td>') if 'summary.xhtml' in name else text)
        self.assertNotIn('numWords', fields)

    def test_conflicting_summary_counts_are_omitted(self):
        fields, _ = altered(lambda name, text: text.replace('</table>', '<tr><th>words</th><td>123</td></tr></table>') if 'summary.xhtml' in name else text)
        self.assertNotIn('numWords', fields)

    def test_no_summary_page_still_uses_marked_opf(self):
        fields, sources = altered(lambda name, text: text, omitted=('OEBPS/frontmatter/summary.xhtml',))
        self.assertEqual(fields['numWords'], 4235)
        self.assertEqual(sources['numWords'], 'ficlab_opf')
        self.assertIn('authorUrl', fields)
        self.assertNotIn('status', fields)
        self.assertNotIn('numChapters', fields)

    def test_no_ficlab_marker_does_not_activate_reader(self):
        fields, sources = altered(lambda name, text: text.replace('ficlab:', 'other:') if name.endswith('.opf') else text, omitted=('META-INF/ficlab-id',))
        self.assertNotIn('numWords', fields)
        self.assertFalse(any((source.startswith('ficlab') for source in sources.values())))

    def test_profile_link_must_match_author(self):
        fields, _ = altered(lambda name, text: text.replace('>TestWriter28</a>', '>Synthetic TXT PDF Detached Partial</a>') if 'copyright.xhtml' in name else text)
        self.assertNotIn('authorUrl', fields)
        self.assertNotIn('authorId', fields)

    def test_ongoing_and_unknown_statuses_are_not_inferred_from_counts(self):
        for status, expected in (('In-Progress', 'In-Progress'), ('Unknown', None)):
            fields, _ = altered(lambda name, text: text.replace('<td>Complete</td>', '<td>' + status + '</td>') if 'summary.xhtml' in name else text)
            self.assertEqual(fields.get('status'), expected)

    def test_subject_tag_boundaries_are_preserved(self):
        fields, _ = altered(lambda name, text: text.replace('<dc:subject>TestGenre15</dc:subject>', '<dc:subject>A tag, with a comma</dc:subject>') if name.endswith('.opf') else text)
        self.assertIn('A tag, with a comma', fields['extratags'])
        self.assertNotIn('with a comma', fields['extratags'])
if __name__ == '__main__':
    unittest.main()
