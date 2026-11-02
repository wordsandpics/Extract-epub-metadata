"""PDF header recognition, ambiguity and boundaries, without requiring Calibre."""
import sys
import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import escape
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'calibre_stub'),str(HERE.parent)]
from extract_epub_metadata.extractors.ao3_pdf import parse_pdf_xml, MAX_XML_BYTES
from build_pdf_fixtures import build_all, NAMES


def xml(lines):
    text=''.join('<text top="%s" left="50" width="500" height="15">%s</text>'%(30+i*20,escape(line)) for i,line in enumerate(lines))
    return ('<pdf2xml><page number="1">'+text+'</page></pdf2xml>').encode()


def header(extra=(),tail=('Summary','Synthetic description.','Notes','Ignore this note.')):
    return ['Synthetic PDF Test','Posted originally on the Archive of Our Own at',
            'https://archiveofourown.org/works/98000901.', 'Rating: General Audiences',
            'Fandom: Synthetic Test Fandom',*extra,'Stats: Published: 2024-01-02 Words: 123 Chapters: 2/?',
            'Synthetic PDF Test','by TestWriterPDF',*tail]


class PdfTests(unittest.TestCase):
    def test_wrapped_notice_and_summary_boundaries(self):
        f,partial=parse_pdf_xml(xml(header()))
        self.assertFalse(partial)
        self.assertEqual(f['author'],['TestWriterPDF'])
        self.assertNotIn('authorUrl',f)
        self.assertEqual(f['description'],'Synthetic description.')
        self.assertEqual(f['status'],'In-Progress')

    def test_series_with_comma_and_distinct_positions(self):
        f,_=parse_pdf_xml(xml(header(['Series: Part 2 of Synthetic Series, With Comma, Part 3 of Other Series'])))
        self.assertEqual(f['series00'],'Synthetic Series, With Comma [2]')
        self.assertEqual(f['series01'],'Other Series [3]')

    def test_plural_categories_and_decoration(self):
        f,partial=parse_pdf_xml(xml(header(['Categories: Gen, F/M','Language: English','✨'])))
        self.assertEqual(f['ao3categories'],['Gen','F/M'])
        self.assertNotIn('language',f)
        self.assertTrue(partial)

    def test_missing_summary_boundary_is_partial(self):
        f,partial=parse_pdf_xml(xml(header(tail=('Summary','Unbounded text.'))))
        self.assertNotIn('description',f)
        self.assertTrue(partial)

    def test_browser_print_and_unrelated_story_links_rejected(self):
        f,_=parse_pdf_xml(xml(['Previous work https://archiveofourown.org/works/98000902',
                              'Synthetic story','Rating: General Audiences','Fandom: Test','by Someone']))
        self.assertEqual(f,{})

    def test_conflicting_scalar_omitted(self):
        f,partial=parse_pdf_xml(xml(header(['Language: English','Language: French'])))
        self.assertNotIn('language',f)
        self.assertTrue(partial)

    def test_conflicting_stats_are_not_last_value_wins(self):
        f,partial=parse_pdf_xml(xml(header(['Stats: Words: 999 Chapters: 3/3'])))
        self.assertNotIn('numWords',f)
        self.assertNotIn('numChapters',f)
        self.assertNotIn('status',f)
        self.assertTrue(partial)

    def test_bound_on_xml(self):
        with self.assertRaises(ValueError):parse_pdf_xml(b' '*(MAX_XML_BYTES+1))

    def test_public_pdf_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            build_all(folder)
            for name in NAMES:self.assertEqual((Path(folder)/name).read_bytes(),(HERE/'fixtures'/name).read_bytes())
