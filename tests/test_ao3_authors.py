"""Synthetic fixture regressions; run with unittest discovery."""
import io
import sys
import unittest
from pathlib import Path
from zipfile import ZipFile
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / 'calibre_stub'), str(HERE.parent)]
from extract_epub_metadata.mapping import extract_fields
from extract_epub_metadata.calibre_fields import compute_standard_fields

class NativeAO3AuthorsTest(unittest.TestCase):

    def test_split_preface_keeps_separate_authors_and_profiles(self):
        fields, sources = extract_fields(HERE / 'fixtures/ao3-split-coauthors.epub')
        names = ['TestWriter02', 'TestWriter03']
        self.assertEqual(fields['author'], names)
        self.assertEqual(fields['authorId'], names)
        self.assertEqual(fields['authorUrl'], ['https://archiveofourown.org/users/%s/pseuds/%s' % (n, n) for n in names])
        self.assertEqual(compute_standard_fields(fields)['authors'], names)
        self.assertEqual(sources['author'], 'ao3_frontmatter')
        self.assertEqual(fields['numWords'], 17674)
        self.assertEqual(fields['numChapters'], 5)

    def test_plain_opf_author_with_comma_remains_one_person(self):
        data = io.BytesIO()
        with ZipFile(HERE / 'fixtures/opf-only-no-markers.epub') as source, ZipFile(data, 'w') as target:
            for name in source.namelist():
                content = source.read(name)
                if name.endswith('.opf'):
                    content = content.replace(b'Test OPF Writer', b'Writer, Test')
                target.writestr(name, content)
        data.seek(0)
        fields, _ = extract_fields(data)
        self.assertEqual(fields['author'], ['Writer, Test'])
if __name__ == '__main__':
    unittest.main()
