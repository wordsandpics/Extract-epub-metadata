"""Invented AO3 metadata as split by HTML-to-EPUB conversion."""
import sys
import tempfile
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'calibre_stub'),str(HERE.parent)]
from build_fixtures import write_epub, page, metadata
from extract_epub_metadata.mapping import extract_fields

F={'title':'Synthetic Converted Header','author':['Wrong imported author'],
   'langcode':'en'}
URL='https://archiveofourown.org/works/98000950'
TAGS='<dl class="tags"><dt>Rating:</dt><dd>General Audiences</dd><dt>Categories:</dt><dd><a>Gen</a>, <a>F/M</a></dd><dt>Fandom:</dt><dd><a>Test Fandom</a></dd><dt>Stats:</dt><dd>Published: 2024-01-02 Words: 123 Chapters: 1/1</dd></dl>'
BYLINE='<h1>Synthetic Converted Header</h1><div class="byline">by <a rel="author" href="https://archiveofourown.org/users/TestAccount/pseuds/TestPseud">TestPseud (TestAccount)</a></div><p>Summary</p><blockquote><p>First summary paragraph.</p><p>Second summary paragraph.</p></blockquote>'


class ConvertedHtmlTests(unittest.TestCase):
    def extract(self,docs,title=None):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'example.epub'
            f=dict(F,title=title or F['title'])
            write_epub(path,f,{k:page(v) for k,v in docs.items()})
            return extract_fields(path)[0]

    def test_split_preface_overrides_browser_metadata(self):
        f=self.extract({'header.xhtml':'<div id="preface"><p>Posted originally on the Archive of Our Own at <a href="'+URL+'">'+URL+'</a></p>'+TAGS+'</div>',
                        'byline.xhtml':'<div id="preface">'+BYLINE+'</div>'},F['title']+' - TestPseud - Multifandom')
        self.assertEqual(f['title'],F['title'])
        self.assertEqual(f['author'],['TestPseud (TestAccount)'])
        self.assertEqual(f['authorUrl'],['https://archiveofourown.org/users/TestAccount/pseuds/TestPseud'])
        self.assertEqual(f['ao3categories'],['Gen','F/M'])
        self.assertEqual(f['description'],'First summary paragraph.\n\nSecond summary paragraph.')

    def test_older_download_without_preface_id(self):
        f=self.extract({'header.xhtml':TAGS,'byline.xhtml':BYLINE+'<p>Inspired by <a rel="author" href="https://archiveofourown.org/users/Other/pseuds/Other">Other</a></p>'})
        self.assertEqual(f['author'],['TestPseud (TestAccount)'])
        self.assertEqual(f['description'],'First summary paragraph.\n\nSecond summary paragraph.')

    def test_relative_work_url_is_unique_and_not_first_link_guess(self):
        body=TAGS+BYLINE+'<a href="/works/98000950/chapters/98000951">Chapter</a>'
        f=self.extract({'page.xhtml':body})
        self.assertEqual(f['storyUrl'],URL)
        f=self.extract({'page.xhtml':body+'<a href="/works/98000952">Other work</a>'})
        # The shared fallback may still find absolute links; neither relative
        # candidate is chosen when the header is ambiguous.
        self.assertFalse(f.get('storyUrl'))

    def test_clean_opf_title_is_preserved(self):
        f=self.extract({'header.xhtml':TAGS,'byline.xhtml':BYLINE},'My edited library title')
        self.assertEqual(f['title'],'My edited library title')
