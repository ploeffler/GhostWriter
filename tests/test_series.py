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


class SharedBase(unittest.TestCase):
    """Bibliothek mit zwei Bänden (Testbuch) in der Serie „Strolchi und Opi“, Figur und Begriff der Serie."""

    def setUp(self):
        import shutil
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name, 'repo')
        self.d.mkdir()
        self.g('init', '-q', '-b', 'main')
        (self.d / 'ghostwriter.yml').write_text(STARTER_FILE.read_text(encoding='utf-8'), encoding='utf-8')
        self.g('add', '.')
        self.g('commit', '-qm', 'Starter')
        for br, short in (('buch/eins', 'Eins'), ('buch/zwei', 'Zwei')):
            self.g('checkout', '-q', '-b', br, 'main')
            shutil.copytree(ROOT / 'tests/fixtures/adhs', self.d, dirs_exist_ok=True)
            cfg = self.d / 'ghostwriter.yml'
            cfg.write_text(re.sub(r'(?m)^(  title_short:).*$', rf'\1 "{short}"', cfg.read_text(encoding='utf-8')), encoding='utf-8')
            self.g('add', '-A')
            self.g('commit', '-qm', f'Buch {short}')
        self.g('checkout', '-q', 'main')
        import characters
        series.create(self.d, 'Strolchi und Opi', books=['buch/eins', 'buch/zwei'])
        characters.series_add(self.d, 'ser-strolchi-und-opi', 'Strolchi', 'main', 'Ein neugieriger Hund')
        series.term_set(self.d, 'ser-strolchi-und-opi', 'Waldhütte', 'Opis Hütte am Waldrand')
        self.g('add', '-A')
        self.g('commit', '-qm', 'Serie')
        self.g('checkout', '-q', 'buch/eins')
        self.main = Path(self.tmp.name, 'main')
        self.g('worktree', 'add', '-q', str(self.main), 'main')   # Standard-Branch zum Schreiben

    def g(self, *a):
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=self.d,
                              check=True, capture_output=True, text=True).stdout

    def widget(self, *a):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.d), *a],
                             capture_output=True, text=True, check=True).stdout
        m = re.search(r'GW\.render\("([^"]+)",(.*)\)</script>', out)
        return json.loads(m.group(2).replace('<\\/', '</'))



class SharedTest(SharedBase):
    """Stufe 2: gemeinsame Figuren und Begriffe, Kopie je Band, Kontinuität."""

    def test_series_character_in_book(self):
        import characters
        from render_view import load
        _, config = load(self.d)
        self.assertEqual(config['_series']['id'], 'ser-strolchi-und-opi')
        self.assertIn('char-strolchi', [c['id'] for c in config['characters']])
        characters.assign(self.d, '1.1', ['Strolchi'])
        self.assertNotIn('characters:', (self.d / 'ghostwriter.yml').read_text(encoding='utf-8'))   # Buch speichert sie nicht
        self.assertEqual(validate_project.check_project(self.d), [])
        self.assertIn('### Strolchi (Hauptfigur)', characters.context(self.d, '1.1'))
        with self.assertRaisesRegex(SystemExit, 'gehört zur Serie'):
            characters.update(self.d, 'Strolchi', {'age': '3'})
        self.assertEqual(self.widget('characters')['CHARACTERS'][0]['C_SOURCE'], 'series')
        # Kopie nur für dieses Buch, dann abweichend
        characters.detach(self.d, 'Strolchi')
        characters.update(self.d, 'Strolchi', {'age': '3'})
        row = self.widget('characters')['CHARACTERS'][0]
        self.assertEqual((row['C_SOURCE'], row['C_SOURCE_TEXT']), ('copy_diff', 'Kopie, weicht von der Serie ab'))
        self.assertEqual(self.widget('characters', 'Strolchi')['CHARACTER_SOURCE'], 'copy_diff')
        self.assertEqual(validate_project.check_project(self.d), [])
        # angleichen: Kopie weg, wieder die Figur der Serie
        characters.align(self.d, 'Strolchi')
        self.assertFalse((self.d / 'characters/char-strolchi.md').exists())
        self.assertEqual(self.widget('characters')['CHARACTERS'][0]['C_SOURCE'], 'series')
        # eigene Figur in die Serie übernehmen
        characters.add(self.d, 'Opi', 'supporting')
        self.assertEqual(self.widget('characters', 'Opi')['CHARACTER_SOURCE'], 'own')
        characters.adopt(self.d, self.main, 'Opi')
        self.assertTrue((self.main / 'series/ser-strolchi-und-opi/characters/char-opi.md').is_file())
        self.assertEqual(series.problems(self.main), [])
        # Figur der Serie bearbeiten (Standard-Branch)
        characters.series_update(self.main, 'ser-strolchi-und-opi', 'Strolchi', {'age': '4'})
        self.assertIn("age: '4'", (self.main / 'series/ser-strolchi-und-opi/characters/char-strolchi.md').read_text(encoding='utf-8'))

    def test_suggest_on_series_level(self):
        text, k, n = series.scan_texts(self.main, 'ser-strolchi-und-opi', size=5000)
        self.assertIn('- Strolchi (`char-strolchi`, Serie)', text)
        self.assertIn('### Band 1 (ADHS im Erwachsenenleben), 1.1', text)
        f = Path(self.tmp.name, 'v.json')
        f.write_text(json.dumps({'scope': 'ser-strolchi-und-opi', 'items': [
            {'name': 'Strolchi', 'age': '3'}, {'name': 'Wolf', 'role': 'minor', 'short': 'lebt im Wald'}]}), encoding='utf-8')
        page = json.loads(re.search(r'GW\.render\("figuren-vorschlag",(.*)\)</script>', subprocess.run(
            [sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.main), 'character-suggest', '--draft', str(f)],
            capture_output=True, text=True, check=True).stdout).group(1))
        self.assertEqual((page['SERIES_LEVEL'], [s['S_STATE'] for s in page['SUGGESTIONS']]), ('1', ['series', 'new']))
        created, updated = series.apply_characters(self.main, 'ser-strolchi-und-opi', json.loads(f.read_text(encoding='utf-8')))
        self.assertEqual((created, updated), (['Wolf'], ['Strolchi']))
        self.assertEqual(series.problems(self.main), [])

    def test_terms_and_continuity(self):
        import matter
        matter.add(self.d, 'glossary')
        matter.glossary_set(self.d, 'Waldhütte', 'Eine kleine Hütte')
        matter.glossary_set(self.d, 'Leine', 'Was Strolchi nicht mag')
        st = {x['T_TERM']: x['T_STATE'] for x in self.widget('matter', 'Glossar')['SERIES_TERMS']}
        self.assertEqual(st, {'Waldhütte': 'differs', 'Leine': 'own'})
        matter.glossary_from_series(self.d, 'Waldhütte')   # angleichen
        st = {x['T_TERM']: x['T_STATE'] for x in self.widget('matter', 'Glossar')['SERIES_TERMS']}
        self.assertEqual(st['Waldhütte'], 'same')
        matter.glossary_to_series(self.d, self.main, 'Leine')
        self.assertEqual([x['term'] for x in series.glossary(self.main, 'ser-strolchi-und-opi')], ['Leine', 'Waldhütte'])
        # Kontinuität: Band 2 bekommt die Kurzfassung von Band 1
        self.assertEqual(series.continuity_context(self.d, 'buch/eins'), '')
        ctx = series.continuity_context(self.d, 'buch/zwei')
        self.assertIn('## Was bisher geschah – Serie „Strolchi und Opi“', ctx)
        self.assertIn('### Band 1: ADHS im Erwachsenenleben', ctx)
        self.assertIn('[KONTINUITÄT PRÜFEN: …]', ctx)
        from render_view import marker_counts
        self.assertEqual(marker_counts('Text [KONTINUITÄT PRÜFEN: In Band 1 war Opi 78] weiter')['kontinuitaet'], 1)


class EditionTest(SharedBase):
    """Stufe 3: Reihe und Band in der Auflage, „Ebenfalls in dieser Reihe“, Begriffe der Serie per Verweis."""

    def test_series_in_edition(self):
        import shutil
        if not (shutil.which('pandoc') and shutil.which('xelatex') and shutil.which('pdftotext')):
            self.skipTest('pandoc, xelatex oder poppler-utils fehlen')
        import matter
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_matter import approve_chapter_1
        self.g('tag', 'eins-auflage-1', 'buch/eins')   # Band 1 ist erschienen
        self.g('checkout', '-q', 'buch/zwei')
        approve_chapter_1(self.d)
        from render_view import load
        _, config = load(self.d)
        sec = self.d / config['structure']['chapters'][0]['sections'][0]['path']
        sec.write_text(sec.read_text(encoding='utf-8').replace('Der Brief lag dort sechs Monate.',
                                                              'Der Brief lag in der [Waldhütte]{.glossar}.', 1), encoding='utf-8')
        item = matter.add(self.d, 'glossary')
        matter.glossary_set(self.d, 'Leine', 'Was Strolchi nicht mag')
        gp = self.d / item['path']
        gp.write_text(re.sub(r'(?m)^status: \w+', 'status: approved', gp.read_text(encoding='utf-8'), count=1), encoding='utf-8')
        out = Path(self.tmp.name, 'out')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.d), '--edition', '1',
                            '--out', str(out), '--formats', 'pdf,epub'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tag = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))['tag']
        text = subprocess.run(['pdftotext', str(out / f'{tag}.pdf'), '-'], capture_output=True, text=True).stdout
        self.assertIn('Strolchi und Opi · Band 2', text)            # über dem Titel
        self.assertIn('Reihe „Strolchi und Opi“, Band 2', text)     # Impressum
        self.assertIn('Ebenfalls in dieser Reihe', text)
        self.assertIn('Band 1: ADHS im Erwachsenenleben', text)
        self.assertIn('Opis Hütte am Waldrand', text)               # Begriff der Serie per Verweis im Glossar
        import zipfile
        with zipfile.ZipFile(out / f'{tag}.epub') as z:
            opf = next(z.read(n).decode() for n in z.namelist() if n.endswith('.opf'))
        self.assertIn('belongs-to-collection', opf)
        self.assertIn('Strolchi und Opi', opf)


class OmnibusTest(SharedBase):
    """Stufe 4: Sammelband aus beiden Bänden."""

    def test_omnibus(self):
        import shutil
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_matter import approve_chapter_1
        for br, tag in (('buch/eins', 'eins-auflage-1'), ('buch/zwei', 'zwei-auflage-1')):
            self.g('checkout', '-q', br)
            from render_view import load
            _, config = load(self.d)
            sec = self.d / config['structure']['chapters'][0]['sections'][0]['path']
            sec.write_text(sec.read_text(encoding='utf-8').replace('Der Brief lag dort sechs Monate.',
                                                                  'Der Brief lag in der [Waldhütte]{.glossar}.', 1), encoding='utf-8')
            approve_chapter_1(self.d)
            self.g('add', '-A')
            self.g('commit', '-qm', 'Kapitel 1 freigegeben')
            self.g('tag', tag)
        om = series.omnibus_update(self.main, 'ser-strolchi-und-opi', {'title': 'Strolchi und Opi – Band 1 und 2',
                                                                       'volumes': ['buch/zwei', 'buch/eins'],
                                                                       'foreword': 'Zwei Geschichten in einem Band.'})
        self.assertEqual([v['branch'] for v in om['volumes']], ['buch/eins', 'buch/zwei'])   # Bandreihenfolge
        self.assertEqual(om['status'], 'draft')
        self.assertEqual(series.problems(self.main), [])
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/build_omnibus.py'), str(self.main),
                                         'ser-strolchi-und-opi', *a], capture_output=True, text=True)
        r = run('--edition', '1', '--out', str(Path(self.tmp.name, 'o')))
        self.assertEqual(r.returncode, 1)
        self.assertIn('nicht freigegeben', r.stdout)
        self.assertEqual(run('--check').returncode, 0, run('--check').stdout)
        series.omnibus_approve(self.main, 'ser-strolchi-und-opi')
        om = series.omnibus_publish(self.main, 'ser-strolchi-und-opi')
        self.assertEqual(series.omnibus_pending(self.main), [('ser-strolchi-und-opi', 1, 'strolchi-und-opi-sammelband-auflage-1')])
        # eine Änderung setzt die Freigabe zurück
        self.assertEqual(series.omnibus_update(self.main, 'ser-strolchi-und-opi', {'subtitle': 'Neu'})['status'], 'draft')
        series.omnibus_approve(self.main, 'ser-strolchi-und-opi')
        view = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.main), *a],
                                         capture_output=True, text=True, check=True).stdout
        w = view('omnibus-edit', 'ser-strolchi-und-opi')
        data = json.loads(re.search(r'GW\.render\("sammelband",(.*)\)</script>', w).group(1).replace('<\\/', '</'))
        self.assertEqual([(v['OV_BRANCH'], v['OV_ON'], v['OV_LAST']) for v in data['OVOLUMES']],
                         [('buch/eins', '1', 1), ('buch/zwei', '1', 1)])
        self.assertEqual((data['OMNIBUS_STATE'], data['OMNIBUS_TAG']), ('approved', 'strolchi-und-opi-sammelband-auflage-2'))
        self.assertIn('**Sammelband:** „Strolchi und Opi – Band 1 und 2“ · 2 Bände · freigegeben · Auflage 1',
                      view('series', 'ser-strolchi-und-opi', '--text'))
        if not (shutil.which('pandoc') and shutil.which('xelatex') and shutil.which('pdftotext')):
            self.skipTest('pandoc, xelatex oder poppler-utils fehlen')
        out = Path(self.tmp.name, 'out')
        r = run('--edition', '1', '--out', str(out), '--formats', 'pdf,epub')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ed = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))
        self.assertEqual(ed['tag'], 'strolchi-und-opi-sammelband-auflage-1')
        self.assertEqual([v['tag'] for v in ed['volumes']], ['eins-auflage-1', 'zwei-auflage-1'])
        text = subprocess.run(['pdftotext', str(out / f'{ed["tag"]}.pdf'), '-'], capture_output=True, text=True).stdout
        self.assertIn('Strolchi und Opi – Band 1 und 2', text)
        self.assertIn('Enthält: Band 1 „ADHS im Erwachsenenleben“ (Auflage 1); Band 2', text)
        self.assertIn('Band 1: ADHS im Erwachsenenleben', text)
        self.assertIn('Band 2: ADHS im Erwachsenenleben', text)
        self.assertIn('Zwei Geschichten in einem Band.', text)
        self.assertIn('Opis Hütte am Waldrand', text)       # zusammengeführtes Glossar, Fassung der Serie
        self.assertTrue((out / f'{ed["tag"]}.epub').is_file())
        self.assertEqual(subprocess.run(['git', 'worktree', 'list'], cwd=self.d, capture_output=True, text=True).stdout.count('\n'), 2)


if __name__ == '__main__':
    unittest.main()
