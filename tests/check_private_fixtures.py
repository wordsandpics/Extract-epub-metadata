"""Optional local regression check against privately retained original examples.

Run: python3 tests/check_private_fixtures.py
The public test suite does not import this script or require these files.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'tests/private-fixtures/original-tests'
sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    if not (PRIVATE / 'fixtures').is_dir():
        raise SystemExit('Private original tests are not present. Use the public synthetic test suite instead.')
    suite = unittest.defaultTestLoader.discover(str(PRIVATE), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())
