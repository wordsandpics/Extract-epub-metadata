"""PDF header recognition, ambiguity and boundaries, without requiring Calibre."""
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path
from xml.sax.saxutils import escape
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'calibre_stub'),str(HERE.parent)]
from extract_epub_metadata.extractors import ao3_pdf
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

    def test_reads_pdf_when_calibre_has_no_creationflags(self):
        # Calibre before 8.6 provides PDFTOHTML but no module-level creationflags.
        old_tool=types.ModuleType('calibre.ebooks.pdf.pdftohtml');old_tool.PDFTOHTML='pdftohtml'
        modules={'calibre.ebooks':types.ModuleType('calibre.ebooks'),
                 'calibre.ebooks.pdf':types.ModuleType('calibre.ebooks.pdf'),
                 'calibre.ebooks.pdf.pdftohtml':old_tool}
        done=subprocess.CompletedProcess([],0,stdout=xml(header()),stderr=b'')
        with mock.patch.dict(sys.modules,modules),mock.patch.object(ao3_pdf.subprocess,'run',return_value=done):
            with (HERE/'fixtures'/'pdf-ao3-table.pdf').open('rb') as stream:
                fields,_=ao3_pdf.extract_pdf_header(stream)
        self.assertEqual(fields['author'],['TestWriterPDF'])


class PdfWrappedTextTests(unittest.TestCase):
    NOTICE=['Posted originally on the Archive of Our Own at','https://archiveofourown.org/works/98000901.',
            'Rating: General Audiences','Fandom: Test Fandom']
    STATS='Stats: Published: 2024-01-02 Words: 123 Chapters: 1/1'
    TAIL=['by TestWriterPDF','Summary','Synthetic description.','Notes','Ignore this note.']

    def test_wrapped_title_without_opening_title(self):
        f,partial=parse_pdf_xml(xml(self.NOTICE+[self.STATS,'A Very Long Title That','Wraps Onto Two Lines']+self.TAIL))
        self.assertEqual(f['title'],'A Very Long Title That Wraps Onto Two Lines')
        self.assertEqual(f['numWords'],'123')
        self.assertFalse(partial)

    def test_wrapped_stats_stay_out_of_the_title(self):
        f,_=parse_pdf_xml(xml(self.NOTICE+['Stats: Published: 2024-01-02 Chapters: 1/1 Words:','15504','Plain Title']+self.TAIL))
        self.assertEqual(f['title'],'Plain Title')
        self.assertEqual(f['numWords'],'15504')

    def test_numeric_title_is_not_read_as_stats(self):
        f,_=parse_pdf_xml(xml(self.NOTICE+[self.STATS,'1984']+self.TAIL))
        self.assertEqual(f['title'],'1984')
        self.assertEqual(f['numWords'],'123')

    def test_hyphen_at_line_end_joins_without_a_space(self):
        lines=self.NOTICE+['Additional Tags: Hurt/Comfort, Self-','Harm, Alternate Universe -','Canon Divergence',
                           self.STATS,'Self-','Made','by TestWriterPDF','Summary','A well-','known story.','Notes','n']
        f,_=parse_pdf_xml(xml(lines))
        self.assertEqual(f['freeformtags'],['Hurt/Comfort','Self-Harm','Alternate Universe - Canon Divergence'])
        self.assertEqual(f['title'],'Self-Made')
        self.assertEqual(f['description'],'A well-known story.')

    def test_separator_lines_keep_their_space(self):
        lines=self.NOTICE+[self.STATS,'Title','by TestWriterPDF','Summary','First part.','-or-','Second part.','----','Third part.','Notes','n']
        f,_=parse_pdf_xml(xml(lines))
        self.assertEqual(f['description'],'First part. -or- Second part. ---- Third part.')

    def test_wrapped_byline_keeps_every_author_and_the_summary(self):
        lines=self.NOTICE+[self.STATS,'Title','by AuthorOne, AuthorTwo,','AuthorThree','Summary','Kept.','Notes','n']
        f,partial=parse_pdf_xml(xml(lines))
        self.assertEqual(f['author'],['AuthorOne','AuthorTwo','AuthorThree'])
        self.assertEqual(f['description'],'Kept.')
        self.assertFalse(partial)

    def test_wrapped_byline_links_stay_aligned(self):
        link='<a href="/users/%s/pseuds/%s">%s</a>'
        rows=[escape(line) for line in self.NOTICE+[self.STATS,'Title']]
        rows+=['by '+link%('A','A','A')+', '+link%('B','B','B')+',',link%('C','C','C'),'Summary','Kept.','Notes','n']
        text=''.join('<text top="%s" left="50" width="500" height="15">%s</text>'%(30+i*20,r) for i,r in enumerate(rows))
        f,_=parse_pdf_xml(('<pdf2xml><page number="1">'+text+'</page></pdf2xml>').encode())
        self.assertEqual(f['author'],['A','B','C'])
        self.assertEqual(f['authorUrl'],['https://archiveofourown.org/users/%s/pseuds/%s'%(n,n) for n in 'ABC'])
