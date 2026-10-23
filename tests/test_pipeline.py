"""Synthetic fixture regressions; run with unittest discovery."""
import datetime
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(TESTS_DIR / 'calibre_stub'))
sys.path.insert(0, str(REPO_ROOT))
from extract_epub_metadata.anthology import extract_fic_records, format_summary, is_anthology
from extract_epub_metadata.calibre_fields import STATUS_COMPLETE_KEY, compatible_columns_for_key, compute_custom_column_values, compute_standard_fields, field_label, permitted_keys_for_datatype
from extract_epub_metadata.extractors._urls import canonical_ao3_url, unwrap_wayback_url
from extract_epub_metadata.extractors.ao3_frontmatter import parse_series, series_fields
from extract_epub_metadata.extractors.fallback_link_scan import _is_recognized_url
from extract_epub_metadata.mapping import extract_fields
from extract_epub_metadata.serialize import serialize_saved_metadata
EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'ao3-native-complete.epub'
GOLDEN_HTML_FIXTURE = TESTS_DIR / 'fixtures' / 'ao3-native-saved-metadata.html'
ANTHOLOGY_FIXTURE = TESTS_DIR / 'fixtures' / 'anthology-mixed-status.epub'
EXPECTED_POPULATED_KEYS = {'ao3categories', 'author', 'authorId', 'authorUrl', 'byline', 'chapterslashtotal', 'characters', 'dateCreated', 'datePublished', 'dateUpdated', 'description', 'fandoms', 'formatext', 'formatname', 'freeformtags', 'langcode', 'language', 'lastupdate', 'numChapters', 'numChaptersTotal', 'numWords', 'rating', 'sectionUrl', 'ships', 'site', 'siteabbrev', 'status', 'storyId', 'storyUrl', 'title', 'warnings'}

def _local(tag):
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag

def parse_golden(path):
    root = ET.fromstring(path.read_text(encoding='utf-8'))
    expected = {}
    for el in root.iter():
        el_id = el.get('id')
        if not el_id:
            continue
        if _local(el.tag) == 'li':
            ul = None
            for parent in root.iter():
                if _local(parent.tag) == 'ul' and el in list(parent):
                    ul = parent
                    break
            items = [''.join(li.itertext()).strip() for li in (list(ul) if ul is not None else [el])]
            expected[el_id] = items
        else:
            expected[el_id] = ''.join(el.itertext()).strip()
    return expected

class PipelineTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fields, cls.sources = extract_fields(str(EPUB_FIXTURE))
        cls.blob = serialize_saved_metadata(cls.fields)
        cls.golden = parse_golden(GOLDEN_HTML_FIXTURE)

    def test_populates_expected_core_fields(self):
        missing = EXPECTED_POPULATED_KEYS - set(self.fields)
        self.assertFalse(missing, 'missing expected fields: %s' % missing)

    def test_values_match_golden_sample(self):
        skip = {'dateCreated'}
        for key in EXPECTED_POPULATED_KEYS - skip:
            if key not in self.golden:
                continue
            actual = self.fields[key]
            expected = self.golden[key]
            if isinstance(actual, (datetime.date, datetime.datetime)):
                actual = actual.isoformat()
            if key in ('numChapters', 'numWords'):
                self.assertEqual(actual, int(str(expected).replace(',', '')), 'field %r mismatch' % key)
            elif isinstance(actual, list):
                self.assertEqual(actual, expected, 'field %r mismatch' % key)
            else:
                self.assertEqual(str(actual), str(expected), 'field %r mismatch' % key)

    def test_serialized_blob_uses_dump_html_metadata_shape(self):
        self.assertIn("<div class='metadata list' id='characters'><ul>\n<li>TestCharacter01</li>", self.blob)
        self.assertIn("<div class='metadata int' id='numChapters'>1</div>", self.blob)
        self.assertIn("<span class='label'>", self.blob)

    def test_omits_unrecoverable_live_stats(self):
        for key in ('hits', 'kudos', 'bookmarks', 'subscribed', 'markedforlater', 'python_version', 'version', 'adapter_classes'):
            self.assertNotIn(key, self.fields)

    def test_round_trips_through_fanficfare_load_html_metadata(self):
        try:
            import fanficfare.story as fff_story
        except ImportError:
            self.skipTest('fanficfare.story not importable in this environment')
        story = fff_story.Story.__new__(fff_story.Story)
        story.metadata = {}
        story.load_html_metadata(self.blob)
        self.assertEqual(story.metadata.get('storyId'), '98000015')
        self.assertEqual(story.metadata.get('numChapters'), 1)
        self.assertIn('TestCharacter01', story.metadata.get('characters', []))
        self.assertIn('TestPair01/TestPartner01', story.metadata.get('ships', []))
        self.assertEqual(story.metadata.get('status'), 'Completed')

class DateFieldTypingTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'fff-bold-packaged-date.epub'

    def test_all_date_fields_are_real_datetimes(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        for key in ('dateCreated', 'datePublished', 'dateUpdated'):
            if key in fields:
                self.assertIsInstance(fields[key], (datetime.date, datetime.datetime), '%r was left as %r instead of being parsed into a datetime (or dropped) -- this is what crashes FFF downstream' % (key, fields[key]))

    def test_serialized_date_fields_carry_the_datetime_class(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        blob = serialize_saved_metadata(fields)
        self.assertIn("<div class='metadata datetime' id='dateCreated'>", blob)
        self.assertNotIn("<div class='metadata' id='dateCreated'>", blob)

class NonAO3FallbackTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'opf-only-no-markers.epub'

    def test_degrades_to_opf_only(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('title'), 'Synthetic OPF Only No Markers')
        self.assertEqual(fields.get('author'), ['Test OPF Writer'])
        self.assertEqual(fields.get('description'), 'Synthetic OPF-only summary with no site markers.')
        for key in ('fandoms', 'ships', 'characters', 'warnings', 'freeformtags', 'ao3categories', 'rating', 'status', 'numChapters', 'numWords', 'storyId'):
            self.assertNotIn(key, fields, 'unexpected AO3-shaped field %r' % key)
        self.assertNotIn('storyUrl', fields)
        self.assertNotIn('site', fields)

class TitlepageParagraphVariantTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'titlepage-paragraph-summary.epub'

    def test_recovers_fields_from_paragraph_style_titlepage(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('fandoms'), ['TestFandom04'])
        self.assertEqual(fields.get('ships'), ['TestPair06/TestPartner06'])
        self.assertEqual(fields.get('freeformtags'), ['TestTag77', 'TestTag78'])
        self.assertEqual(fields.get('ao3categories'), ['M/M'])
        self.assertEqual(fields.get('rating'), 'Mature')
        self.assertEqual(fields.get('status'), 'In-Progress')
        self.assertEqual(fields.get('numWords'), 4066)
        for key in ('fandoms', 'ships', 'freeformtags', 'ao3categories', 'rating', 'status', 'numChapters', 'numWords'):
            self.assertEqual(sources.get(key), 'fff_titlepage')

    def test_chapters_slash_notation_recovers_numerator_and_status(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('numChapters'), 1)
        self.assertEqual(fields.get('chapterslashtotal'), '1/1')

    def test_dates_are_real_datetimes(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertIsInstance(fields.get('datePublished'), datetime.datetime)
        self.assertIsInstance(fields.get('dateUpdated'), datetime.datetime)

class UnknownChapterTotalTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'titlepage-unknown-total-41.epub'

    def test_numerator_recovered_as_a_real_int(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('numChapters'), 41)
        self.assertIsInstance(fields['numChapters'], int)
        self.assertEqual(fields.get('chapterslashtotal'), '41/?')
        self.assertNotIn('numChaptersTotal', fields)

    def test_status_not_fabricated_from_unknown_total(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('status'), 'In-Progress')
        self.assertEqual(sources.get('status'), 'fff_titlepage')

    def test_no_non_numeric_string_survives_into_numChapters(self):
        from extract_epub_metadata.mapping import _finalize_numerics
        fields = {'numChapters': '41/?', 'numWords': '1,234'}
        _finalize_numerics(fields)
        self.assertNotIn('numChapters', fields)
        self.assertEqual(fields['numWords'], 1234)

class KnownChapterTotalTest(unittest.TestCase):

    def test_ao3_frontmatter_recovers_known_total(self):
        from extract_epub_metadata.extractors.ao3_frontmatter import _parse_stats
        result = {}
        _parse_stats('Published: 2024-01-01\nWords: 1,234\nChapters: 12/24', result)
        self.assertEqual(result.get('numChaptersTotal'), '24')
        self.assertEqual(result.get('numChapters'), '12')

    def test_ao3_frontmatter_omits_total_when_unknown(self):
        from extract_epub_metadata.extractors.ao3_frontmatter import _parse_stats
        result = {}
        _parse_stats('Published: 2024-01-01\nWords: 1,234\nChapters: 12/?', result)
        self.assertNotIn('numChaptersTotal', result)
        self.assertEqual(result.get('numChapters'), '12')

    def test_titlepage_slash_notation_recovers_known_total(self):
        from extract_epub_metadata.mapping import _map_titlepage
        titlepage = {'label_entries': {'Chapters': '12/24'}}
        fields = _map_titlepage(titlepage)
        self.assertEqual(fields.get('numChaptersTotal'), '24')
        self.assertEqual(fields.get('numChapters'), '12')

    def test_native_fixture_with_known_total_of_one(self):
        fields, sources = extract_fields(str(EPUB_FIXTURE))
        self.assertEqual(fields.get('numChaptersTotal'), 1)
        self.assertIsInstance(fields['numChaptersTotal'], int)
        self.assertEqual(sources.get('numChaptersTotal'), 'ao3_frontmatter')

class ParagraphUnknownTotalTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'titlepage-unknown-total-16.epub'

    def test_current_count_recovered_total_absent(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('numChapters'), 16)
        self.assertEqual(fields.get('chapterslashtotal'), '16/?')
        self.assertNotIn('numChaptersTotal', fields)
        self.assertEqual(sources.get('numChapters'), 'fff_titlepage')

class FfnetViaFichubTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'fichub-ffnet-composite.epub'

    def test_recovers_fields_from_composite_stats_line(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('rating'), 'Fiction M')
        self.assertEqual(fields.get('language'), 'English')
        self.assertEqual(fields.get('genre'), ['TestGenre06'])
        self.assertEqual(fields.get('characters'), ['TestCharacter15', 'TestCharacter16'])
        for key in ('rating', 'language', 'genre', 'characters'):
            self.assertEqual(sources.get(key), 'fff_titlepage')

    def test_live_engagement_stats_not_fabricated(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        for key in fields:
            self.assertNotIn(key.lower(), ('reviews', 'favs', 'follows'))

    def test_status_normalized_from_lowercase(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('status'), 'Completed')

    def test_chapters_and_words_and_dates(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('numChapters'), 36)
        self.assertEqual(fields.get('numWords'), 191497)
        self.assertIsInstance(fields.get('datePublished'), datetime.datetime)
        self.assertIsInstance(fields.get('dateUpdated'), datetime.datetime)

    def test_story_id_recovered_from_ffnet_url_shape(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('storyId'), '98000181')

    def test_author_html_has_no_broken_empty_link(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('authorHTML'), 'TestWriter08')

    def test_genre_flows_into_mode2_tags(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        computed = compute_standard_fields(fields)
        self.assertIn('TestGenre06', computed['tags'])

    def test_composite_splitter_leaves_non_matching_values_untouched(self):
        from extract_epub_metadata.mapping import _split_composite_label_value
        tags = 'TestTag79, TestTag80'
        head, sub_entries = _split_composite_label_value(tags)
        self.assertEqual(head, tags)
        self.assertEqual(sub_entries, {})

class FfnetViaWebToEpubTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'ffnet-webtoepub-profile.epub'

    def test_story_url_is_not_the_cover_image(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('storyUrl'), 'https://www.fanfiction.net/s/98000184/1/Synthetic-Case')
        self.assertNotIn('image', fields['storyUrl'])
        self.assertEqual(sources.get('storyUrl'), 'opf')

    def test_recovers_unlabeled_positional_fields(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('language'), 'English')
        self.assertEqual(fields.get('genre'), ['TestGenre07'])
        self.assertEqual(fields.get('characters'), ['TestCharacter16', 'TestCharacter15'])
        for key in ('language', 'genre', 'characters', 'rating', 'numChapters'):
            self.assertEqual(sources.get(key), 'ffnet_infopage')

    def test_fandom_from_breadcrumb(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('fandoms'), ['TestFandom07'])
        self.assertEqual(sources.get('fandoms'), 'ffnet_infopage')

    def test_fandom_also_populates_category_for_fff_roundtrip(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('category'), ['TestFandom07'])
        self.assertEqual(sources.get('category'), 'ffnet_infopage')

    def test_status_normalized_from_native_casing(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('status'), 'Completed')

    def test_story_id_from_explicit_id_label(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('storyId'), '98000184')

    def test_author_id_and_url_recovered(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('authorId'), ['98000185'])
        self.assertEqual(fields.get('authorUrl'), ['https://www.fanfiction.net/u/98000185/Test-Writer'])

    def test_dates_use_native_ffnet_format(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('datePublished'), datetime.datetime(2010, 9, 2, 14, 43, 45))
        self.assertEqual(fields.get('dateUpdated'), datetime.datetime(2020, 1, 5, 3, 12, 37))

    def test_description_is_just_the_summary(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        description = fields.get('description', '')
        self.assertTrue(description.startswith('Synthetic ffnet-webtoepub-profile summary paragraph one.'))
        self.assertNotIn('Rated:', description)
        self.assertNotIn('By:', description)

    def test_live_engagement_stats_not_fabricated(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        for key in fields:
            self.assertNotIn(key.lower(), ('reviews', 'favs', 'follows'))

    def test_unlabeled_fields_skipped_when_count_is_ambiguous(self):
        from extract_epub_metadata.extractors.ffnet_infopage import _split_stats_line
        labeled, unlabeled = _split_stats_line('Rated: Fiction T - English - Harry P. - Chapters: 5 - Words: 1,000 - Status: Complete - id: 123')
        self.assertEqual(len(unlabeled), 2)
        self.assertNotIn('language', labeled)
        self.assertNotIn('genre', labeled)
        self.assertNotIn('characters', labeled)
        self.assertEqual(labeled.get('rating'), 'Fiction T')
        self.assertEqual(labeled.get('numChapters'), '5')
        self.assertEqual(labeled.get('storyId'), '123')

class CoverPageBeforeTitlePageTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'fff-cover-before-title.epub'

    def test_recovers_fields_past_the_cover_page(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('category'), ['TestCategory02', 'TestCategory03', 'TestCategory04'])
        self.assertEqual(fields.get('genre'), ['TestCategory02', 'TestGenre08', 'TestGenre09'])
        self.assertEqual(fields.get('status'), 'In-Progress')
        self.assertEqual(fields.get('numChapters'), 139)
        self.assertEqual(fields.get('numWords'), 823304)
        for key in ('category', 'genre', 'status', 'numChapters', 'numWords'):
            self.assertEqual(sources.get(key), 'fff_titlepage')

    def test_cover_page_alone_yields_nothing(self):
        from extract_epub_metadata.extractors.fff_titlepage import _is_titlepage
        import xml.etree.ElementTree as ET
        cover_html = '<html><body><div><svg/></div></body></html>'
        root = ET.fromstring(cover_html)
        self.assertTrue(_is_titlepage(root, 'OEBPS/titlepage.xhtml'))

class SingularAO3TagLabelTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'ao3-anonymous-singular-tags.epub'

    def test_ships_recovered_from_singular_relationship_label(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('ships'), ['TestPair04/TestPartner04'])
        self.assertEqual(sources.get('ships'), 'ao3_frontmatter')

    def test_other_ao3_frontmatter_fields_still_populated(self):
        fields, _sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('fandoms'), ['TestFandom03'])
        self.assertEqual(fields.get('ao3categories'), ['M/M'])
        self.assertEqual(fields.get('rating'), 'Explicit')
        self.assertEqual(fields.get('warnings'), ['Creator Chose Not To Use Archive Warnings'])
        self.assertEqual(fields.get('status'), 'In-Progress')

    def test_series_from_native_preface(self):
        fields, sources = extract_fields(str(self.EPUB_FIXTURE))
        self.assertEqual(fields.get('series'), 'TestSeries02 [1]')
        self.assertEqual(fields.get('seriesUrl'), 'https://archiveofourown.org/series/98000102')
        self.assertEqual(sources.get('series'), 'ao3_frontmatter')

class AO3ViaWaybackWebToEpubTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'ao3-wayback-information.epub'
    WAYBACK_URL = 'https://web.archive.org/web/20171212114900/https://archiveofourown.org/works/98000216'

    def setUp(self):
        self.fields, self.sources = extract_fields(str(self.EPUB_FIXTURE))

    def test_story_url_is_canonical_ao3_not_the_snapshot(self):
        self.assertEqual(self.fields.get('storyUrl'), 'https://archiveofourown.org/works/98000216')
        self.assertEqual(self.fields.get('sectionUrl'), self.fields['storyUrl'])
        self.assertEqual(self.fields.get('site'), 'archiveofourown.org')
        self.assertEqual(self.fields.get('siteabbrev'), 'ao3')
        self.assertEqual(self.fields.get('storyId'), '98000216')
        self.assertNotIn('authorUrl', self.fields)
        self.assertNotIn('authorId', self.fields)

    def test_snapshot_url_kept_in_saved_metadata(self):
        self.assertEqual(self.fields.get('waybackUrl'), self.WAYBACK_URL)
        blob = serialize_saved_metadata(self.fields)
        self.assertIn("id='waybackUrl'>%s</div>" % self.WAYBACK_URL, blob)

    def test_recovers_tags_from_work_page_markup(self):
        f = self.fields
        self.assertEqual(f.get('rating'), 'Explicit')
        self.assertEqual(f.get('warnings'), ['No Archive Warnings Apply'])
        self.assertEqual(f.get('ao3categories'), ['M/M'])
        self.assertEqual(f.get('fandoms'), ['TestFandom08'])
        self.assertEqual(f.get('ships'), ['TestPair09/TestPartner09', 'TestPair10/TestPartner10'])
        self.assertEqual(f.get('characters'), ['TestCharacter01', 'TestCharacter17'])
        self.assertEqual(len(f.get('freeformtags') or []), 25)
        self.assertEqual(f['freeformtags'][-1], 'TestTag157')
        self.assertEqual(f.get('language'), 'English')
        self.assertEqual(self.sources.get('fandoms'), 'ao3_frontmatter')

    def test_title_and_author_still_from_opf(self):
        self.assertEqual(self.fields.get('title'), 'Synthetic AO3 Wayback Information')
        self.assertEqual(self.fields.get('author'), ['TestWriter10'])

    def test_unspaced_stats_parse_correctly(self):
        self.assertEqual(self.fields.get('status'), 'Completed')
        self.assertEqual(self.fields.get('chapterslashtotal'), '1/1')
        self.assertEqual(self.fields.get('numChapters'), 1)
        self.assertEqual(self.fields.get('numChaptersTotal'), 1)
        self.assertEqual(self.fields.get('numWords'), 4674)
        self.assertEqual(self.fields.get('datePublished'), datetime.datetime(2016, 3, 6))

    def test_live_engagement_stats_not_fabricated(self):
        for key in ('hits', 'kudos', 'bookmarks', 'comments'):
            self.assertNotIn(key, self.fields)

    def test_description_is_the_summary_only(self):
        desc = self.fields.get('description') or ''
        self.assertTrue(desc.startswith('Synthetic information summary starts here.'))
        self.assertIn('Synthetic line one\nSynthetic line two\nabout', desc)
        self.assertTrue(desc.endswith('Synthetic summary ends here.'))
        self.assertNotIn('MissDavis', desc)

    def test_unwrap_wayback_url_variants(self):
        self.assertEqual(unwrap_wayback_url(self.WAYBACK_URL), 'https://archiveofourown.org/works/98000216')
        self.assertEqual(unwrap_wayback_url('http://web.archive.org/web/2017id_/http:/archiveofourown.org/works/1/chapters/2'), 'https://archiveofourown.org/works/1')
        self.assertEqual(unwrap_wayback_url('https://web.archive.org/web/20200101000000/www.fanfiction.net/s/5/1/X'), 'https://www.fanfiction.net/s/5/1/X')
        self.assertIsNone(unwrap_wayback_url('https://archiveofourown.org/works/1'))
        self.assertIsNone(unwrap_wayback_url(None))

    def test_fallback_link_scan_recognizes_snapshot_links(self):
        self.assertTrue(_is_recognized_url(self.WAYBACK_URL))
        self.assertFalse(_is_recognized_url('https://web.archive.org/web/2017/http://skulls-and-tea.tumblr.com/post/1'))

class AO3WaybackWholePageSaveTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'ao3-wayback-whole-page.epub'

    def setUp(self):
        self.fields, self.sources = extract_fields(str(self.EPUB_FIXTURE))

    def test_page_level_opf_metadata_does_not_win(self):
        self.assertEqual(self.fields.get('title'), 'Synthetic AO3 Wayback Whole Page')
        self.assertEqual(self.sources.get('title'), 'ao3_frontmatter')
        self.assertNotIn('Organization for Transformative Works', self.fields.get('author'))
        self.assertNotIn('project of the Organization', self.fields.get('description'))

    def test_author_fields_match_fanficfare_ao3_adapter(self):
        self.assertEqual(self.fields.get('author'), ['TestWriter11'])
        self.assertEqual(self.fields.get('authorId'), ['TestWriter04'])
        self.assertEqual(self.fields.get('authorUrl'), ['https://archiveofourown.org/users/TestUser01/pseuds/TestWriter04'])

    def test_story_url_unwrapped_from_view_full_work_snapshot(self):
        self.assertEqual(self.fields.get('storyUrl'), 'https://archiveofourown.org/works/98000236')
        self.assertEqual(self.fields.get('storyId'), '98000236')
        self.assertEqual(self.fields.get('siteabbrev'), 'ao3')
        self.assertEqual(self.fields.get('waybackUrl'), 'https://web.archive.org/web/20190411192321/https://archiveofourown.org/works/98000236?view_full_work=true')

    def test_recovers_tags_without_class_attributes(self):
        f = self.fields
        self.assertEqual(f.get('rating'), 'Explicit')
        self.assertEqual(f.get('warnings'), ['No Archive Warnings Apply'])
        self.assertEqual(f.get('ao3categories'), ['M/M'])
        self.assertEqual(f.get('fandoms'), ['TestFandom08', 'TestFandom02'])
        self.assertEqual(f.get('ships'), ['TestPair01/TestPartner01'])
        self.assertEqual(f.get('characters'), ['TestCharacter01', 'TestCharacter02'])
        self.assertEqual(len(f.get('freeformtags') or []), 19)
        self.assertEqual(f.get('language'), 'English')

    def test_stats(self):
        self.assertEqual(self.fields.get('status'), 'Completed')
        self.assertEqual(self.fields.get('numChapters'), 3)
        self.assertEqual(self.fields.get('numChaptersTotal'), 3)
        self.assertEqual(self.fields.get('numWords'), 10722)
        self.assertEqual(self.fields.get('datePublished'), datetime.datetime(2018, 5, 17))
        self.assertEqual(self.fields.get('dateUpdated'), datetime.datetime(2018, 6, 6))

    def test_description_is_the_work_summary_only(self):
        desc = self.fields.get('description') or ''
        self.assertTrue(desc.startswith('Synthetic whole-page summary begins here.'))
        self.assertTrue(desc.endswith('Synthetic whole-page summary ends here.'))
        self.assertNotIn('stand alone ficlet', desc)

class AO3PdfConvertedTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'ao3-pdf-wrapped-preface.epub'

    def setUp(self):
        self.fields, self.sources = extract_fields(str(self.EPUB_FIXTURE))

    def test_story_url_from_download_host_is_canonicalized(self):
        self.assertEqual(self.fields.get('storyUrl'), 'https://archiveofourown.org/works/98000260')
        self.assertEqual(self.fields.get('storyId'), '98000260')
        self.assertEqual(self.fields.get('siteabbrev'), 'ao3')

    def test_placeholder_author_replaced_by_byline(self):
        self.assertEqual(self.fields.get('author'), ['TestWriter12'])
        self.assertEqual(self.sources.get('author'), 'ao3_pdf_preface')
        self.assertEqual(self.fields.get('authorUrl'), ['https://archiveofourown.org/users/TestWriter12/pseuds/TestWriter12'])

    def test_tags_read_from_text_not_misaligned_links(self):
        f = self.fields
        self.assertEqual(f.get('rating'), 'Mature')
        self.assertEqual(f.get('warnings'), ['No Archive Warnings Apply'])
        self.assertEqual(f.get('ao3categories'), ['M/M'])
        self.assertEqual(f.get('fandoms'), ['TestFandom09', 'TestFandom10'])
        self.assertEqual(f.get('ships'), ['TestPair11/TestPartner11'])
        self.assertEqual(f.get('characters'), ['TestCharacter18', 'TestCharacter19', 'TestCharacter20', 'Test Character Four (Synthetic)'])
        tags = f.get('freeformtags') or []
        self.assertEqual(len(tags), 14)
        for tag in ('TestTag181', 'TestTag182', 'TestTag183', 'TestTag184'):
            self.assertIn(tag, tags)

    def test_series(self):
        self.assertEqual(self.fields.get('series'), 'TestSeries03 [2]')
        self.assertEqual(self.fields.get('seriesUrl'), 'https://archiveofourown.org/series/98000261')
        self.assertEqual(self.fields.get('series00'), 'TestSeries03 [2]')
        self.assertEqual(compute_standard_fields(self.fields).get('series'), 'TestSeries03 [2]')

    def test_wrapped_stats_with_unknown_total(self):
        self.assertEqual(self.fields.get('status'), 'In-Progress')
        self.assertEqual(self.fields.get('numChapters'), 3)
        self.assertNotIn('numChaptersTotal', self.fields)
        self.assertEqual(self.fields.get('numWords'), 15504)
        self.assertEqual(self.fields.get('datePublished'), datetime.datetime(2016, 12, 21))
        self.assertEqual(self.fields.get('dateUpdated'), datetime.datetime(2017, 10, 10))

    def test_summary_paragraphs_rejoined(self):
        self.assertEqual(self.fields.get('description'), 'Synthetic ao3-pdf-wrapped-preface summary paragraph one.\n\nSynthetic paragraph two ends here.')

    def test_series_parsing_across_ao3_shapes(self):
        dd = ET.fromstring('<dd>Part 1 of <a href="https://archiveofourown.org/series/5">First</a>, Part 3 of <a href="https://archiveofourown.org/series/9">Second One</a></dd>')
        self.assertEqual(parse_series([dd]), [('First', 1, 'https://archiveofourown.org/series/5'), ('Second One', 3, 'https://archiveofourown.org/series/9')])
        self.assertEqual(series_fields(parse_series([dd])), {'series': 'First [1]', 'seriesUrl': 'https://archiveofourown.org/series/5', 'series00': 'First [1]', 'series00Url': 'https://archiveofourown.org/series/5', 'series01': 'Second One [3]', 'series01Url': 'https://archiveofourown.org/series/9'})
        wrapped = ET.fromstring('<dd><span>Part 4 of <a href="https://web.archive.org/web/2019/https://archiveofourown.org/series/7">S</a></span></dd>')
        self.assertEqual(parse_series([wrapped]), [('S', 4, 'https://archiveofourown.org/series/7')])
        self.assertEqual(parse_series([ET.fromstring('<p>Part 2 of TestSeries03</p>')]), [('TestSeries03', 2, None)])

    def test_canonical_ao3_url(self):
        self.assertEqual(canonical_ao3_url('http://download.archiveofourown.org/works/1/chapters/2'), 'https://archiveofourown.org/works/1')
        self.assertEqual(canonical_ao3_url('https://www.archiveofourown.org/series/3'), 'https://archiveofourown.org/series/3')
        self.assertIsNone(canonical_ao3_url('https://www.fanfiction.net/s/5/1/X'))

class ComputeStandardFieldsTest(unittest.TestCase):
    EPUB_FIXTURE = TESTS_DIR / 'fixtures' / 'ao3-native-complete.epub'

    @classmethod
    def setUpClass(cls):
        cls.fields, _sources = extract_fields(str(cls.EPUB_FIXTURE))
        cls.computed = compute_standard_fields(cls.fields)

    def test_title_and_authors(self):
        self.assertEqual(self.computed['title'], 'Synthetic AO3 Native Complete')
        self.assertEqual(self.computed['authors'], ['TestWriter01'])

    def test_tags_composite_matches_fff_defaults(self):
        tags = set(self.computed['tags'])
        self.assertIn('TestFandom01', tags)
        self.assertIn('TestPair01/TestPartner01', tags)
        self.assertIn('TestCharacter01', tags)
        self.assertIn('TestTag01', tags)
        self.assertIn('M/M', tags)
        self.assertIn('Completed', tags)
        self.assertNotIn('General Audiences', tags)
        self.assertNotIn('Creator Chose Not To Use Archive Warnings', tags)
        self.assertEqual(len(self.computed['tags']), len(tags))

    def test_comments_wraps_and_escapes_plain_description(self):
        from html import escape
        self.assertEqual(self.computed['comments'], '<p>%s</p>' % escape(self.fields['description']).replace('\n', '<br />'))

    def test_no_series_when_not_extracted(self):
        self.assertNotIn('series', self.computed)

    def test_pubdate_and_language(self):
        self.assertEqual(self.computed['pubdate'], self.fields['datePublished'])
        self.assertEqual(self.computed['language'], 'English')

    def test_sparse_in_sparse_out(self):
        minimal = compute_standard_fields({'title': 'Only A Title'})
        self.assertEqual(minimal, {'title': 'Only A Title'})

class CustomColumnMappingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fields, _sources = extract_fields(str(TESTS_DIR / 'fixtures' / 'ao3-native-complete.epub'))
        cls.columns = {'#text_col': {'datatype': 'text', 'is_multiple': False, 'display': {}}, '#tags_col': {'datatype': 'text', 'is_multiple': True, 'display': {}}, '#names_col': {'datatype': 'text', 'is_multiple': True, 'display': {'is_names': True}}, '#int_col': {'datatype': 'int', 'is_multiple': False, 'display': {}}, '#bool_col': {'datatype': 'bool', 'is_multiple': False, 'display': {}}, '#date_col': {'datatype': 'datetime', 'is_multiple': False, 'display': {}}, '#enum_col': {'datatype': 'enumeration', 'is_multiple': False, 'display': {'enum_values': ['Completed', 'In-Progress']}}, '#series_col': {'datatype': 'series', 'is_multiple': False, 'display': {}}}

    def test_permitted_keys_by_datatype(self):
        self.assertIn('numWords', permitted_keys_for_datatype('int'))
        self.assertNotIn('title', permitted_keys_for_datatype('int'))
        self.assertEqual(permitted_keys_for_datatype('bool'), [STATUS_COMPLETE_KEY])
        self.assertIn('datePublished', permitted_keys_for_datatype('datetime'))
        self.assertIn('fandoms', permitted_keys_for_datatype('text', is_multiple=True))
        self.assertIn('fandoms', permitted_keys_for_datatype('text', is_multiple=False))
        self.assertIn('title', permitted_keys_for_datatype('text', is_multiple=False))

    def test_scalar_text_column(self):
        mapping = {'#text_col': 'rating'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertEqual(values['#text_col'], 'General Audiences')

    def test_multiple_text_column_gets_a_list(self):
        mapping = {'#tags_col': 'characters'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertEqual(values['#tags_col'], self.fields['characters'])

    def test_single_text_column_joins_a_list_source(self):
        mapping = {'#text_col': 'characters'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertEqual(values['#text_col'], ', '.join(self.fields['characters']))

    def test_is_names_column_joins_with_ampersand(self):
        mapping = {'#names_col': 'author'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertEqual(values['#names_col'], self.fields['author'])

    def test_int_column(self):
        mapping = {'#int_col': 'numWords'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertEqual(values['#int_col'], self.fields['numWords'])
        self.assertIsInstance(values['#int_col'], int)

    def test_int_column_rejects_non_int_key(self):
        mapping = {'#int_col': 'title'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertNotIn('#int_col', values)

    def test_bool_column_from_status(self):
        mapping = {'#bool_col': STATUS_COMPLETE_KEY}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertIs(values['#bool_col'], self.fields['status'] == 'Completed')

    def test_datetime_column(self):
        mapping = {'#date_col': 'datePublished'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertEqual(values['#date_col'], self.fields['datePublished'])

    def test_enumeration_column_accepts_valid_value(self):
        mapping = {'#enum_col': 'status'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertEqual(values['#enum_col'], 'Completed')

    def test_enumeration_column_rejects_value_not_in_enum(self):
        mapping = {'#enum_col': 'rating'}
        values = compute_custom_column_values(self.fields, mapping, self.columns)
        self.assertNotIn('#enum_col', values)

    def test_series_column(self):
        fields_with_series = dict(self.fields, series='My Series [3]')
        mapping = {'#series_col': 'series'}
        values = compute_custom_column_values(fields_with_series, mapping, self.columns)
        self.assertEqual(values['#series_col'], 'My Series [3]')

    def test_unmapped_columns_produce_nothing(self):
        values = compute_custom_column_values(self.fields, {}, self.columns)
        self.assertEqual(values, {})

    def test_missing_source_key_is_skipped_not_error(self):
        mapping = {'#int_col': 'numWords', '#date_col': 'dateCreated'}
        fields_without_dateCreated = {k: v for k, v in self.fields.items() if k != 'dateCreated'}
        values = compute_custom_column_values(fields_without_dateCreated, mapping, self.columns)
        self.assertIn('#int_col', values)
        self.assertNotIn('#date_col', values)

    def test_compatible_columns_for_key_is_the_reverse_of_permitted_keys(self):
        self.assertEqual(compatible_columns_for_key('numWords', self.columns), ['#int_col'])
        self.assertEqual(compatible_columns_for_key('datePublished', self.columns), ['#date_col'])
        self.assertEqual(compatible_columns_for_key(STATUS_COMPLETE_KEY, self.columns), ['#bool_col'])
        text_like = compatible_columns_for_key('characters', self.columns)
        for col in ('#text_col', '#tags_col', '#names_col', '#enum_col'):
            self.assertIn(col, text_like)
        self.assertNotIn('#series_col', text_like)
        self.assertNotIn('#int_col', text_like)

    def test_field_label_falls_back_to_raw_key(self):
        self.assertEqual(field_label('numWords'), 'Word Count')
        self.assertEqual(field_label('not_a_real_key'), 'not_a_real_key')

class AnthologyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with ZipFile(ANTHOLOGY_FIXTURE) as zf:
            cls.is_anthology = is_anthology(zf)
            cls.records = extract_fic_records(zf)

    def test_detects_anthology(self):
        self.assertTrue(self.is_anthology)

    def test_recovers_all_seven_fics(self):
        self.assertEqual(len(self.records), 7)

    def test_per_fic_status_and_chapters_match_verified_findings(self):
        expected = [('Completed', 12), ('Completed', 18), ('Completed', 18), ('Completed', 37), ('Completed', 56), ('Completed', 93), ('In-Progress', 110)]
        actual = [(r.get('status'), r.get('numChapters')) for r in self.records]
        self.assertEqual(actual, expected)

    def test_only_fic_seven_is_incomplete(self):
        incomplete = [r for r in self.records if r.get('status') != 'Completed']
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]['title'], 'Synthetic anthology-mixed-status Story 7')

    def test_fic_seven_missing_published_date_handled_gracefully(self):
        fic7 = self.records[6]
        self.assertNotIn('datePublished', fic7)
        self.assertIn('dateUpdated', fic7)

    def test_story_urls_recovered_per_fic(self):
        urls = [r.get('storyUrl') for r in self.records]
        self.assertEqual(urls, ['https://archiveofourown.org/works/98000276', 'https://archiveofourown.org/works/98000277', 'https://archiveofourown.org/works/98000278', 'https://archiveofourown.org/works/98000279', 'https://archiveofourown.org/works/98000280', 'https://archiveofourown.org/works/98000281', 'https://archiveofourown.org/works/98000282'])

    def test_format_summary_reports_six_of_seven(self):
        summary = format_summary(self.records)
        self.assertIn('6/7 fics complete.', summary)
        self.assertIn('7. Synthetic anthology-mixed-status Story 7 -- In-Progress', summary)

    def test_non_anthology_epub_is_not_detected(self):
        with ZipFile(EPUB_FIXTURE) as zf:
            self.assertFalse(is_anthology(zf))
            self.assertEqual(extract_fic_records(zf), [])

    def test_format_summary_empty_for_no_records(self):
        self.assertEqual(format_summary([]), '')
if __name__ == '__main__':
    unittest.main()
