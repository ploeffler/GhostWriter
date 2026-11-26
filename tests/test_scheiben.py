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


class LibraryAndChapterSliceTest(unittest.TestCase):
    """Bücherregal je Buch und Kapitelansicht je Abschnitt (#674)."""
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        self.lib = Path(tmp.name) / 'library.json'
        book = {'branch': 'buch/adhs', 'status': 'ready', 'title': 'ADHS', 'title_short': 'adhs', 'author': 'A', 'sections_total': 10,
                'sections_approved': 2, 'chapters_total': 2, 'chapters_approved': 0, 'current_edition': 1, 'editions': [{'number': 1, 'tag': 't-1'}],
                'updated_at': '2026-11-01', 'cost': {'text': '–'}}
        book2 = dict(book, branch='buch/zwei', title='Zwei', title_short='zwei', editions=[])
        self.lib.write_text(json.dumps({'books': [book, book2]}), encoding='utf-8')

    def run_view(self, view, *args, check=True):
        extra = ['--library', str(self.lib)] if view == 'library' else []
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), view, *args, '--repo', 'o/r', *extra],
                           capture_output=True, text=True)
        if check:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def data(self, view, name, *where):
        out = self.run_view(view, *where, '--scheibe', name).stdout
        return widget_json(re.search(r'GW\.render\("[a-z]+",(.*)\)</script>', out).group(1))

    def test_library_slices(self):
        r = self.run_view('library', '--scheibe', 'liste')
        names = r.stdout.split()
        self.assertEqual(names[:3], ['kopf', 'buch:1', 'buch:2'])
        head, one, two = self.data('library', 'kopf'), self.data('library', 'buch:1'), self.data('library', 'buch:2')
        self.assertEqual((head['SLICE'], one['SLICE']), ('kopf', 'buch'))
        self.assertFalse(head['BOOKS'])
        self.assertEqual([b['BOOK_BRANCH'] for b in one['BOOKS']], ['buch/adhs'])
        self.assertEqual([e['E_NUMBER'] for e in one['EDITIONS']], [1])                  # nur die Auflagen dieses Buchs
        self.assertEqual([b['BOOK_BRANCH'] for b in two['BOOKS']], ['buch/zwei'])
        self.assertFalse(two['EDITIONS'])
        self.assertNotEqual(self.run_view('library', '--scheibe', 'buch:9', check=False).returncode, 0)
        self.assertNotEqual(self.run_view('library', '--scheibe', 'kopf', '--text', check=False).returncode, 0)

    def test_chapter_slices(self):
        names = self.run_view('chapter', '1', '--scheibe', 'liste').stdout.split()
        n = len(names) - 2
        self.assertEqual((names[0], names[1], names[-1]), ('kopf', 'abschnitt:1', 'ende'))
        head, first, second, last, end = (self.data('chapter', x, '1') for x in ('kopf', 'abschnitt:1', 'abschnitt:2', f'abschnitt:{n}', 'ende'))
        self.assertEqual((head['SLICE'], first['SLICE'], second['SLICE'], end['SLICE']), ('kopf', 'abschnitt', 'abschnitt-weiter', 'ende'))
        self.assertTrue(head['CHAPTER_TITLE'] and not head['SECTIONS'])
        self.assertEqual([len(s['SECTIONS']) for s in (first, second, last)], [1, 1, 1])
        self.assertEqual(first['SECTIONS'][0]['SECTION_NUMBER'], '1.1')
        self.assertFalse(first['CHAPTER_TITLE'])
        full = self.run_view('chapter', '1').stdout
        self.assertEqual(len(re.findall(r'"SECTION_ID"', full)) or 1, 1)                  # ohne --scheibe weiter in einem Stück
        self.assertNotIn('"SLICE"', full)


if __name__ == '__main__':
    unittest.main()
