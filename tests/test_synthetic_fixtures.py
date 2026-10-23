"""Keep the public examples small, synthetic, reproducible and self-contained."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / 'fixture_cases.json').read_text())
FIXTURES = HERE / 'fixtures'


class SyntheticFixtureTest(unittest.TestCase):
    def test_each_scenario_has_a_descriptive_title_and_file(self):
        names = [case['name'] for case in CASES]
        self.assertEqual(len(names), len(set(names)))
        for case in CASES:
            with self.subTest(name=case['name']):
                self.assertTrue(case['fields']['title'].startswith('Synthetic '))
                self.assertTrue((FIXTURES / case['name']).is_file())
                self.assertLess((FIXTURES / case['name']).stat().st_size, 20000)

    def test_public_epubs_have_no_image_payloads(self):
        for path in FIXTURES.glob('*.epub'):
            with self.subTest(name=path.name), ZipFile(path) as archive:
                self.assertEqual(archive.testzip(), None)
                self.assertTrue(all(name.endswith(('.xhtml', '.html', '.opf', '.xml')) or
                                    name in ('mimetype', 'META-INF/ficlab-id')
                                    for name in archive.namelist()))
                self.assertLess(sum(info.file_size for info in archive.infolist()), 50000)

    def test_wrapping_cases_retain_their_layout(self):
        spaced = (FIXTURES / 'txt-spaced-wrapped-tags.txt').read_text()
        self.assertIn('/\nTestPartner', spaced)
        self.assertIn('\nTest Genre: Colon Case', spaced)
        pdf = (FIXTURES / 'txt-pdf-squidgeworld.txt').read_text()
        self.assertIn('Synthetic Wrapped\nTag', pdf)
        with ZipFile(FIXTURES / 'ao3-pdf-wrapped-preface.epub') as archive:
            self.assertIn('</a></p><p>(Synthetic)</p>', archive.read('pdf.xhtml').decode())

    def test_rebuild_matches_every_committed_example(self):
        # The builder must run without original stories or the plugin parser.
        with tempfile.TemporaryDirectory(prefix='synthetic-rebuild-') as folder:
            subprocess.run([sys.executable, str(HERE / 'build_fixtures.py'),
                            '--output', folder], check=True, capture_output=True)
            expected = {case['name'] for case in CASES} | {'ao3-native-saved-metadata.html'}
            self.assertEqual({path.name for path in Path(folder).iterdir()}, expected)
            for name in sorted(expected):
                with self.subTest(name=name):
                    self.assertEqual((Path(folder) / name).read_bytes(),
                                     (FIXTURES / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
