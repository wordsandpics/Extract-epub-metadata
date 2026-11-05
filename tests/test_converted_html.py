"""Invented AO3 metadata as split by HTML-to-EPUB conversion."""
import sys
import tempfile
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'calibre_stub'),str(HERE.parent)]
from build_fixtures import write_epub, page, metadata
from extract_epub_metadata.mapping import extract_fields
from extract_epub_metadata.extractors.ao3_frontmatter import extract_ao3_frontmatter
from zipfile import ZipFile

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

    def test_translation_and_related_work_credits_are_not_authors(self):
        # AO3 lists translations in the preface with rel=author links (issue 3).
        credits=('<p>Notes</p><blockquote class="userstuff"><p>See <a href="https://archiveofourown.org/users/NoteUser/pseuds/NoteUser">NoteUser</a>.</p></blockquote>'
                 '<ul><li>Translation into Test Language available: <a href="https://archiveofourown.org/works/98000953">Translated Work</a> by '
                 '<a rel="author" href="https://archiveofourown.org/users/Translator/pseuds/Translator">Translator</a></li></ul>')
        header='<div id="preface"><p>Posted originally on the Archive of Our Own at <a href="'+URL+'">'+URL+'</a></p>'+TAGS
        for docs in ({'preface.xhtml':header+BYLINE+credits+'</div>'},
                     {'header.xhtml':header+'</div>','byline.xhtml':'<div id="preface">'+BYLINE+credits+'</div>'}):
            f=self.extract(docs)
            self.assertEqual(f['author'],['TestPseud (TestAccount)'])
            self.assertEqual(f['authorUrl'],['https://archiveofourown.org/users/TestAccount/pseuds/TestPseud'])

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

    def header_url(self,docs):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'example.epub'
            write_epub(path,F,{k:page(v) for k,v in docs.items()})
            with ZipFile(path) as zf:
                return (extract_ao3_frontmatter(zf) or {}).get('storyUrl')

    def test_links_to_other_works_are_not_the_story_url(self):
        summary=lambda href:BYLINE.replace('First summary paragraph.','Sequel to <a href="%s">my earlier story</a>.'%href)
        for label,docs in (
                ('relative summary link',{'page.xhtml':TAGS+summary('/works/555')}),
                ('summary chapter link',{'page.xhtml':TAGS+summary('/works/555/chapters/7')}),
                ('absolute summary link',{'page.xhtml':TAGS+summary('https://archiveofourown.org/works/555')}),
                ('next work link only',{'page.xhtml':TAGS+BYLINE+'<a href="/works/555">Next Work</a>'}),
                ('story text class',{'page.xhtml':TAGS+BYLINE+'<div class="userstuff"><a href="/works/555/chapters/7">Part one</a></div>'}),
                ('later story document',{'page.xhtml':TAGS,'chapter.xhtml':'<p><a href="/works/555/chapters/7">Part one</a></p>'})):
            self.assertIsNone(self.header_url(docs),label)

    def test_own_page_controls_identify_the_work(self):
        wayback='https://web.archive.org/web/2019/https://archiveofourown.org/works/98000950/bookmarks'
        share='<textarea>&lt;a href="http://archiveofourown.org/works/98000950"&gt;Title&lt;/a&gt;</textarea>'
        for label,extra in (('bookmarks','<a href="/works/98000950/bookmarks">Bookmarks</a>'),
                            ('comments','<a href="/works/98000950?show_comments=true#comments">Comments</a>'),
                            ('wayback control','<a href="%s">Bookmarks</a>'%wayback),
                            ('share box',share)):
            self.assertEqual(self.header_url({'page.xhtml':TAGS+BYLINE+extra}),URL,label)
