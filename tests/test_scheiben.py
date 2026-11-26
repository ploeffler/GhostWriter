"""#674 Schritt 3: Projektübersicht in Scheiben (kopf, kapitel:N, ende) für das Widget."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from tests.widget_helpers import widget_json  # noqa: E402


class SliceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def run_view(self, *args, check=True):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'project', '--repo', 'o/r', *args],
                           capture_output=True, text=True)
        if check:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def data(self, name):
        out = self.run_view('--scheibe', name).stdout
        return widget_json(re.search(r'GW\.render\("projektuebersicht",(.*)\)</script>', out).group(1))

    def test_list_and_slices_cover_everything_once(self):
        names = self.run_view('--scheibe', 'liste').stdout.split()
        self.assertEqual(names[0], 'kopf')
        self.assertEqual(names[-1], 'ende')
        n = len(names) - 2
        self.assertGreater(n, 2)
        head, first, second, last, end = (self.data(x) for x in ('kopf', 'kapitel:1', 'kapitel:2', f'kapitel:{n}', 'ende'))
        self.assertEqual(head['SLICE'], 'kopf')
        self.assertTrue(head['PROJECT_TITLE'] and not head['CHAPTERS'])               # Kopf ohne Kapitel
        self.assertEqual((first['SLICE'], second['SLICE'], last['SLICE'], end['SLICE']), ('kapitel', 'kapitel-weiter', 'kapitel-weiter', 'ende'))
        self.assertEqual([len(s['CHAPTERS']) for s in (first, second, last)], [1, 1, 1])
        self.assertEqual(first['CHAPTERS'][0]['CHAPTER_NUMBER'], 1)
        self.assertEqual(last['CHAPTERS'][0]['CHAPTER_NUMBER'], n)
        for s in (first, second, last, end):
            self.assertFalse(s['PROJECT_TITLE'])                                       # Titel nur im Kopf
        self.assertTrue(end['CREDIT_TEXT'] and not head['CREDIT_TEXT'])                # Nachweis am Ende
        self.assertNotIn('CHECKS_LEGEND', first)

    def test_unknown_slice_text_and_default_unchanged(self):
        self.assertNotEqual(self.run_view('--scheibe', 'kapitel:99', check=False).returncode, 0)
        self.assertNotEqual(self.run_view('--scheibe', 'kopf', '--text', check=False).returncode, 0)
        full = self.run_view().stdout
        self.assertNotIn('SLICE', full)                                                # ohne --scheibe wie bisher
        self.assertIn('"CHAPTERS"', full)

    def test_slices_are_small_and_start_is_the_head(self):
        sizes = {n: len(self.run_view('--scheibe', n).stdout) for n in ('kopf', 'kapitel:1')}
        full = len(self.run_view().stdout)
        self.assertLess(sizes['kopf'], full)
        self.assertLess(sizes['kapitel:1'], sizes['kopf'] + 600)


if __name__ == '__main__':
    unittest.main()
