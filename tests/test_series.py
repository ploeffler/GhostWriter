"""Serien (#116, Stufe 1): anlegen, Bände, Regeln, library.json, Ansichten – Testserie „Strolchi und Opi“."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import library  # noqa: E402
import series  # noqa: E402
import validate_project  # noqa: E402

MANIFEST = yaml.safe_load((ROOT / 'ghostwriter-manifest.yml').read_text(encoding='utf-8'))
STARTER_FILE = ROOT / 'templates/ghostwriter-starter.yml'


class SeriesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.g('init', '-q', '-b', 'main')
        Path(self.d, 'ghostwriter.yml').write_text(STARTER_FILE.read_text(encoding='utf-8'), encoding='utf-8')
        self.g('add', '.')
        self.g('commit', '-qm', 'Starter')
        for title, short in (('Strolchi findet einen Freund', 'Strolchi 1'), ('Strolchi im Schnee', 'Strolchi 2'),
                             ('Mein Gartenjahr', 'Garten')):
            library.create_book(title, short, 'Opa Karl', self.d, 'refs/heads', MANIFEST, base='main')
            self.g('checkout', '-q', 'main')

    def g(self, *a):
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=self.d,
                              check=True, capture_output=True, text=True).stdout

    def commit(self, msg):
        self.g('add', '-A')
        self.g('commit', '-qm', msg)

    def view(self, *a, branch=None):
        if branch:
            self.g('checkout', '-q', branch)
        try:
            return subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), self.d, *a],
                                  capture_output=True, text=True, check=True).stdout
        finally:
            if branch:
                self.g('checkout', '-q', 'main')

    def widget(self, *a, **kw):
        m = re.search(r'GW\.render\("([^"]+)",(.*)\)</script>', self.view(*a, **kw))
        return m.group(1), json.loads(m.group(2).replace('<\\/', '</'))

    def test_create_add_reorder_remove(self):
        s = series.create(self.d, 'Strolchi und Opi', kind='continuous', books=['buch/strolchi-1'])
        self.assertEqual(s['id'], 'ser-strolchi-und-opi')
        s, n = series.add(self.d, 'ser-strolchi-und-opi', 'buch/strolchi-2')
        self.assertEqual(n, 2)
        self.assertEqual(validate_project.check_project(self.d), [])
        # Regeln: kein zweites Mal, keine zweite Serie, nur Bücher der Bibliothek
        with self.assertRaisesRegex(SystemExit, 'schon Band 1'):
            series.add(self.d, 'ser-strolchi-und-opi', 'buch/strolchi-1')
        series.create(self.d, 'Gartenbücher', kind='standalone')
        with self.assertRaisesRegex(SystemExit, 'höchstens einer Serie'):
            series.add(self.d, 'ser-gartenbuecher', 'buch/strolchi-2')
        with self.assertRaisesRegex(SystemExit, 'kein Buch'):
            series.add(self.d, 'ser-gartenbuecher', 'buch/gibt-es-nicht')
        series.reorder(self.d, 'ser-strolchi-und-opi', ['buch/strolchi-2', 'buch/strolchi-1'])
        all_s = series.load_all(self.d)
        self.assertEqual(series.of(all_s, 'buch/strolchi-1')[1], 2)
        with self.assertRaises(SystemExit):
            series.reorder(self.d, 'ser-strolchi-und-opi', ['buch/strolchi-1'])
        series.update(self.d, 'ser-strolchi-und-opi', {'title': 'Strolchi & Opi'})
        self.assertEqual(series.load_all(self.d)['ser-strolchi-und-opi']['title'], 'Strolchi & Opi')   # ID bleibt
        series.remove(self.d, 'ser-strolchi-und-opi', 'buch/strolchi-1')
        self.assertEqual(series.load_all(self.d)['ser-strolchi-und-opi']['volumes'], ['buch/strolchi-2'])
        # von Hand doppelt eingetragen: die Prüfung meldet es
        p = series.series_file(self.d, 'ser-gartenbuecher')
        p.write_text(p.read_text(encoding='utf-8').replace('volumes: []', 'volumes: [buch/strolchi-2]'), encoding='utf-8')
        self.assertTrue(any('höchstens einer Serie' in e for e in validate_project.check_project(self.d)))

    def test_only_in_library(self):
        cfg = Path(self.d, 'ghostwriter.yml')
        data = yaml.safe_load(cfg.read_text(encoding='utf-8'))
        data['structure']['chapters'] = [{'id': 'ch-01', 'title': 'X', 'path': 'chapters/01-x', 'status': 'planned', 'sections': []}]
        cfg.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
        with self.assertRaisesRegex(SystemExit, 'nur in einer Bibliothek'):
            series.create(self.d, 'Reihe')

    def test_new_book_in_series_and_views(self):
        series.create(self.d, 'Strolchi und Opi', books=['buch/strolchi-1', 'buch/strolchi-2'])
        self.commit('Serie „Strolchi und Opi“ angelegt')
        r = library.create_book('Strolchi am Meer', 'Strolchi 3', 'Opa Karl', self.d, 'refs/heads', MANIFEST,
                                base='main', series_id='ser-strolchi-und-opi')
        self.assertEqual((r['taken'], r['volume']), ([], 3))
        self.assertFalse(Path(self.d, 'series').exists())        # Buch-Branch ohne series/
        self.assertIn('Band 3 zur Serie', self.g('log', '-1', '--format=%s', 'main'))
        self.g('checkout', '-q', 'main')
        # library.json mit Serien
        data = library.build_library('refs/heads', self.d, MANIFEST)
        self.assertEqual(data['series'][0]['volumes'], ['buch/strolchi-1', 'buch/strolchi-2', 'buch/strolchi-3'])
        b = {x['branch']: x for x in data['books']}
        self.assertEqual((b['buch/strolchi-2']['series'], b['buch/strolchi-2']['volume']), ('ser-strolchi-und-opi', 2))
        self.assertNotIn('series', b['buch/garten'])
        lib = Path(self.tmp.name, 'library.json')
        lib.write_text(json.dumps(data), encoding='utf-8')
        # Bücherregal: Serie zuerst, in Bandreihenfolge
        name, shelf = self.widget('library', '--library', str(lib))
        self.assertEqual([r['BOOK_BRANCH'] for r in shelf['BOOKS']],
                         ['buch/strolchi-1', 'buch/strolchi-2', 'buch/strolchi-3', 'buch/garten'])
        self.assertEqual(shelf['BOOKS'][1]['BOOK_VOLUME_TEXT'], 'Band 2')
        self.assertEqual(shelf['BOOK_COUNT_TEXT'], '4 Bücher · 1 Serie')
        text = self.view('library', '--library', str(lib), '--text')
        self.assertIn('📚 **Serie „Strolchi und Opi“** (`S1`)', text)
        self.assertIn('**Einzelne Bücher**', text)
        # Seite der Serie
        name, page = self.widget('series', 'S1', '--library', str(lib))
        self.assertEqual(name, 'serie')
        self.assertEqual([v['V_NUMBER'] for v in page['VOLUMES']], [1, 2, 3])
        self.assertEqual([c['C_BRANCH'] for c in page['CANDIDATES']], ['buch/garten'])
        self.assertIn('| 2 | **Strolchi im Schnee** (`buch/strolchi-2`)', self.view('series', 'Strolchi und Opi', '--library', str(lib), '--text'))
        # Formular „Neues Buch in dieser Serie“: nächster Band, Autor des letzten Bandes
        _, form = self.widget('book-create', '--library', str(lib), '--draft', '{"series_id":"ser-strolchi-und-opi"}')
        self.assertEqual((form['SERIES_TEXT'], form['AUTHOR']), ('Band 4 der Serie „Strolchi und Opi“', 'Opa Karl'))
        name, edit = self.widget('series-edit', 'ser-strolchi-und-opi', '--library', str(lib))
        self.assertEqual((name, edit['SERIES_KIND']), ('serie-bearbeiten', 'continuous'))
        # Projektübersicht eines Bandes (Serie vom Standard-Branch gelesen)
        _, ov = self.widget('project', branch='buch/strolchi-2')
        self.assertEqual(ov['SERIES_TEXT'], 'Band 2 der Serie „Strolchi und Opi“')
        _, ov = self.widget('project', branch='buch/garten')
        self.assertNotIn('SERIES_ID', ov)


if __name__ == '__main__':
    unittest.main()
