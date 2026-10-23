"""Synthetic fixture regressions; run with unittest discovery."""
import datetime
import io
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
from zipfile import ZipFile
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / 'calibre_stub'), str(HERE.parent)]
from extract_epub_metadata.mapping import extract_fields, _derive_fields
from extract_epub_metadata.extractors._text import html_to_text
from extract_epub_metadata.extractors.ao3_frontmatter import parse_series
from extract_epub_metadata.fff_support import fff_support_url
from extract_epub_metadata.calibre_fields import compute_standard_fields, compute_custom_column_values, plan_standard_fields
import xml.etree.ElementTree as ET

class ReviewExtractionTest(unittest.TestCase):

    def test_series_link_with_the_and_navigation(self):
        path = next((HERE / 'fixtures').glob('ao3-series-navigation.epub'))
        fields, _ = extract_fields(path)
        self.assertEqual(fields['series'], 'TestSeries06 [1]')
        self.assertEqual(fields['seriesUrl'], 'https://archiveofourown.org/series/98000436')

    def test_unmatched_series_link_does_not_fall_back_to_navigation_text(self):
        dd = ET.fromstring('<dd>Related: <a href="https://archiveofourown.org/series/1">Series</a> Next Work →</dd>')
        self.assertEqual(parse_series([dd]), [])

    def test_anonymous_has_no_invented_profile(self):
        fields, _ = extract_fields(HERE / 'fixtures/ao3-anonymous-singular-tags.epub')
        self.assertEqual(fields['author'], ['Anonymous'])
        self.assertNotIn('authorId', fields)
        self.assertNotIn('authorUrl', fields)
        self.assertEqual(fields['authorHTML'], 'Anonymous')

    def test_bare_pseud_does_not_imply_matching_username(self):
        fields = {'author': ['Pseud (DifferentUser)'], 'site': 'archiveofourown.org'}
        _derive_fields(fields)
        self.assertNotIn('authorUrl', fields)
        self.assertNotIn('authorId', fields)

    def test_summary_paragraphs_preserved(self):
        fields, _ = extract_fields(HERE / 'fixtures/titlepage-paragraph-summary.epub')
        self.assertIn('summary paragraph one.\n\nSynthetic paragraph two', fields['description'])

    def test_summary_entities_decoded(self):
        path = next((HERE / 'fixtures').glob('fichub-ao3-summary-entities.epub'))
        fields, _ = extract_fields(path)
        self.assertIn('entity’s', fields['description'])
        self.assertIn('\n\n', fields['description'])
        self.assertNotRegex(fields['description'], '&(?:[a-z]+|#[0-9]+);')

    def test_html_components_are_escaped(self):
        fields = {'title': 'A <B> & C', 'author': ['Writer <X> & Co'], 'authorUrl': ["https://example.com/user'quoted"], 'storyUrl': "https://example.com/story'quoted"}
        _derive_fields(fields)
        self.assertIn('A &lt;B&gt; &amp; C', fields['titleHTML'])
        self.assertIn('Writer &lt;X&gt; &amp; Co', fields['authorHTML'])
        self.assertIn('&#x27;', fields['titleHTML'])
        self.assertIn('&#x27;', fields['authorHTML'])

    def test_collection_rich_comments_and_plain_custom_description(self):
        fields = {'collectionType': 'epubmerge anthology', 'description': '<p>A &amp; B</p><p>Next</p>'}
        self.assertEqual(compute_standard_fields(fields)['comments'], fields['description'])
        custom = compute_custom_column_values(fields, {'#text': 'description'}, {'#text': {'datatype': 'text'}})
        self.assertEqual(custom['#text'], 'A & B\n\nNext')

    def test_html_text_preserves_line_break_and_ignores_script(self):
        self.assertEqual(html_to_text('<p>A<br />B &amp; C</p><script>bad()</script><p>D</p>'), 'A\nB & C\n\nD')

    def test_all_unknown_statuses_omit_completed_count(self):
        data = io.BytesIO()
        with ZipFile(HERE / 'fixtures/anthology-multiple-authors.epub') as source, ZipFile(data, 'w') as target:
            for name in source.namelist():
                content = source.read(name)
                if name.endswith('title_page.xhtml'):
                    content = re.sub(b'(<b>Status:</b>)\\s*Completed', b'\\1 Unknown', content)
                if name.endswith('content.opf'):
                    content = re.sub(b'(<(?:\\w+:)?subject[^>]*>)Completed(</(?:\\w+:)?subject>)', b'\\1Unknown\\2', content)
                target.writestr(name, content)
        data.seek(0)
        fields, _ = extract_fields(data)
        self.assertEqual(fields['collectionUnknownCount'], 5)
        self.assertNotIn('collectionCompletedCount', fields)

class PlaceholderPlanningTest(unittest.TestCase):

    def test_placeholders_are_empty_and_real_values_are_kept(self):
        date_module = ModuleType('calibre.utils.date')
        date_module.is_date_undefined = lambda d: d is None or d.year == 101
        locale_module = ModuleType('calibre.utils.localization')
        locale_module._ = lambda s: 'Inconnu' if s == 'Unknown' else s
        modules = {'calibre.utils.date': date_module, 'calibre.utils.localization': locale_module}

        class DB:

            def __init__(self, values):
                self.values = values

            def field_for(self, field, _id):
                return self.values.get(field)
        computed = {'authors': ['Writer'], 'pubdate': datetime.datetime(2020, 1, 1), 'title': 'New'}
        with patch.dict(sys.modules, modules), patch('builtins._', locale_module._, create=True):
            for name in ('Unknown', 'Inconnu'):
                pending, kept = plan_standard_fields(DB({'authors': [name], 'pubdate': datetime.datetime(101, 1, 1), 'title': 'Existing'}), 1, computed, False)
                self.assertEqual(set(pending), {'authors', 'pubdate'})
                self.assertEqual(kept, {'title': 'New'})
            pending, kept = plan_standard_fields(DB({'authors': ['Real Writer'], 'pubdate': datetime.datetime(1990, 1, 1)}), 1, computed, False)
            self.assertEqual(pending, {'title': 'New'})
            self.assertEqual(set(kept), {'authors', 'pubdate'})

class FanFicFareIdentifierTest(unittest.TestCase):

    def test_url_precedence_and_planned_wayback_replacement(self):
        work = 'https://archiveofourown.org/works/123'
        other = 'https://example.com/story'
        wayback = 'https://web.archive.org/web/20200101/' + work
        cases = [({'url': work.replace(':', '|'), 'uri': other}, None, False, work), ({'url': work}, other, True, work), ({'uri': other}, work, True, other), ({'uri': wayback}, work, True, work), ({'uri': wayback}, work, False, wayback), ({'uri': wayback}, None, True, wayback), ({}, work, False, work), ({}, None, True, None)]
        for identifiers, recovered, add, expected in cases:
            with self.subTest(identifiers=identifiers, add=add):
                self.assertEqual(fff_support_url(identifiers, recovered, add), expected)
if __name__ == '__main__':
    unittest.main()
