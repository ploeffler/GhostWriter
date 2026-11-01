"""Bibliothek (#36): Erkennungsregel, Namen, Eindeutigkeit der Kurztitel, Git-Auflistung."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import library  # noqa: E402

MANIFEST = yaml.safe_load((ROOT / 'ghostwriter-manifest.yml').read_text(encoding='utf-8'))
STARTER = {'project': {'title': '', 'title_short': ''}, 'structure': {'chapters': []}}


def book(short, chapters=True):
    return {'project': {'title': short + ' – das Buch', 'title_short': short},
            'structure': {'chapters': [{'id': 'ch-01'}] if chapters else []}}


class RuleTest(unittest.TestCase):
    def test_rule(self):
        cases = {
            ('buch/adhs', 'starter'): True,           # neu angelegt, Wizard läuft
            ('buch/adhs', 'book'): True,
            ('buch/ohne-datei', None): False,         # keine ghostwriter.yml
            ('test/test-book', 'book'): True,         # Altbestand mit Kapiteln
            ('feature/x', 'starter'): False,          # anderer Branch ohne Kapitel
            ('main', 'book'): False,                  # skip_branches (Hauptrepository)
            ('ghostwriter/buch/adhs', 'book'): False, # Arbeits-Branch
            ('v0.5', 'book'): False,
        }
        cfgs = {'starter': STARTER, 'book': book('ADHS'), None: None}
        for (name, kind), want in cases.items():
            with self.subTest(name=name, kind=kind):
                self.assertEqual(library.is_book(name, cfgs[kind], MANIFEST), want)

    def test_single_book_default_branch(self):
        # Im eigenen Buch-Repository (Fork) ist der Standard-Branch selbst ein Buch, wenn er nicht in skip steht
        m = dict(MANIFEST, update={'skip_branches': ['ghostwriter/*']})
        self.assertTrue(library.is_book('main', book('X'), m))
        self.assertFalse(library.is_book('main', STARTER, m))   # Bibliotheksmodus: main nur Programm

    def test_names(self):
        self.assertEqual(library.slug('Über Mut & Größe'), 'ueber-mut-groesse')
        self.assertEqual(library.book_branch('ADHS im Alltag', MANIFEST), 'buch/adhs-im-alltag')
        self.assertEqual(library.work_branch('buch/adhs', MANIFEST), 'ghostwriter/buch/adhs')

    def test_name_check_and_duplicates(self):
        found = library.books({'buch/adhs': book('ADHS'), 'test/test-book': book('Mut'), 'main': book('Z')}, MANIFEST)
        self.assertEqual([b['branch'] for b in found], ['buch/adhs', 'test/test-book'])
        self.assertEqual(library.name_check('Neu', found, MANIFEST)['taken'], [])
        self.assertTrue(library.name_check('ADHS', found, MANIFEST)['taken'])          # Branch vergeben
        self.assertTrue(library.name_check('mut', found, MANIFEST)['taken'])           # Tag-Slug vergeben
        self.assertTrue(library.name_check('!!!', found, MANIFEST)['taken'])
        self.assertEqual(library.duplicates(found), {})
        found.append(library.describe('buch/mut', book('MUT'), MANIFEST))
        self.assertEqual(library.duplicates(found), {'mut': ['test/test-book', 'buch/mut']})

    def test_status(self):
        self.assertEqual(library.describe('buch/a', STARTER, MANIFEST)['status'], 'setup')
        self.assertEqual(library.describe('buch/a', book('A'), MANIFEST)['status'], 'ready')


class GitTest(unittest.TestCase):
    def test_list_and_check_in_repo(self):
        with tempfile.TemporaryDirectory() as d:
            def g(*a):
                subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True, capture_output=True)

            def commit(branch, cfg):
                g('checkout', '-q', '-B', branch, 'main') if branch != 'main' else None
                Path(d, 'ghostwriter.yml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
                g('add', '.')
                g('commit', '-q', '--allow-empty', '-m', branch)
            g('init', '-q', '-b', 'main')
            commit('main', STARTER)
            commit('buch/adhs', book('ADHS'))
            commit('buch/neu', STARTER)
            commit('buch/zweit', book('adhs'))
            run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/library.py'), *a,
                                             '--namespace', 'refs/heads', '--repo', d], capture_output=True, text=True)
            r = run('list', '--json')
            self.assertEqual([b['branch'] for b in json.loads(r.stdout)], ['buch/adhs', 'buch/neu', 'buch/zweit'])
            c = run('check')
            self.assertEqual(c.returncode, 1)
            self.assertIn('adhs', c.stdout)
            self.assertEqual(run('name', 'Ganz neu').returncode, 0)
            self.assertEqual(run('name', 'ADHS').returncode, 1)


if __name__ == '__main__':
    unittest.main()


class ShelfTest(unittest.TestCase):
    """Bücherregal (#37): library.json aus den Branches, Ansicht und Link in der Projektübersicht."""

    @classmethod
    def setUpClass(cls):
        import shutil
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = cls.tmp.name

        def g(*a):
            subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True, capture_output=True)
        g('init', '-q', '-b', 'main')
        Path(d, 'ghostwriter.yml').write_text((ROOT / 'ghostwriter.yml').read_text(encoding='utf-8'), encoding='utf-8')
        g('add', '.')
        g('commit', '-qm', 'Starter')
        g('checkout', '-q', '-b', 'buch/adhs')
        shutil.copytree(ROOT / 'tests/fixtures/adhs', d, dirs_exist_ok=True)
        g('add', '.')
        g('commit', '-qm', 'Buch')
        g('checkout', '-q', '-b', 'ghostwriter/buch/adhs')
        g('commit', '-q', '--allow-empty', '-m', 'offene Änderung')
        g('checkout', '-q', '-b', 'buch/garten', 'main')
        g('checkout', '-q', 'main')
        cls.data = library.build_library('refs/heads', d, MANIFEST)
        cls.lib = Path(d, 'library.json')
        cls.lib.write_text(json.dumps(cls.data, ensure_ascii=False), encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def view(self, *a):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), *a], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_build(self):
        books = {b['branch']: b for b in self.data['books']}
        self.assertEqual(sorted(books), ['buch/adhs', 'buch/garten'])
        a, g = books['buch/adhs'], books['buch/garten']
        self.assertEqual(a['status'], 'ready')
        self.assertGreater(a['sections_total'], 0)
        self.assertEqual(a['pending'], 1)
        self.assertEqual(g['status'], 'setup')
        self.assertEqual(g['sections_total'], 0)
        self.assertNotIn('manuscript', json.dumps(self.data))
        out = subprocess.run(['git', 'worktree', 'list'], cwd=self.d, capture_output=True, text=True).stdout
        self.assertEqual(len(out.strip().splitlines()), 1, 'temporäre Worktrees bleiben übrig')

    def test_shelf_views(self):
        text = self.view(self.d, 'library', '--library', str(self.lib), '--text')
        self.assertIn('2 Bücher', text)
        self.assertIn('🚧 im Aufbau', text)
        self.assertIn('`1–2` Buch öffnen', text)
        widget = self.view(self.d, 'library', '--library', str(self.lib))
        self.assertIn('GW.render("buecherregal"', widget)
        self.assertIn('"BOOK_PENDING_TEXT":"1 Änderung offen"', widget)

    def test_project_link_from_two_books(self):
        fx = str(ROOT / 'tests/fixtures/adhs')
        self.assertIn('"LIBRARY_COUNT":2', self.view(fx, 'project', '--library', str(self.lib)))
        self.assertIn('`L` Bücherregal', self.view(fx, 'project', '--library', str(self.lib), '--text'))
        self.assertNotIn('LIBRARY_COUNT', self.view(fx, 'project'))


class NewBookTest(unittest.TestCase):
    """Neues Buch (#38): Felder setzen ohne Formatverlust, Branch und ein Commit, Namensprüfung, Formular."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.d = self.tmp.name
        self.g = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True,
                                           capture_output=True, text=True).stdout
        self.g('init', '-q', '-b', 'main')
        Path(d, 'ghostwriter.yml').write_text((ROOT / 'ghostwriter.yml').read_text(encoding='utf-8'), encoding='utf-8')
        self.g('add', '.')
        self.g('commit', '-qm', 'Starter')

    def tearDown(self):
        self.tmp.cleanup()

    def test_set_fields_keeps_comments(self):
        text = (ROOT / 'ghostwriter.yml').read_text(encoding='utf-8')
        new = library.set_project_fields(text, {'working_title': 'Mein "Garten"jahr', 'title_short': 'Garten', 'author': 'A'})
        cfg = yaml.safe_load(new)
        self.assertEqual(cfg['project']['working_title'], 'Mein "Garten"jahr')
        self.assertEqual(cfg['project']['title_short'], 'Garten')
        self.assertEqual(sum(l.count('#') for l in text.splitlines()), sum(l.count('#') for l in new.splitlines()))
        self.assertEqual(len(text.splitlines()), len(new.splitlines()))
        self.assertEqual({k: v for k, v in cfg.items() if k != 'project'}, {k: v for k, v in yaml.safe_load(text).items() if k != 'project'})

    def test_create(self):
        r = library.create_book('Mein Gartenjahr', 'Gartenjahr', 'Max', self.d, 'refs/heads', MANIFEST, base='main')
        self.assertEqual(r['taken'], [])
        self.assertEqual(self.g('rev-parse', '--abbrev-ref', 'HEAD').strip(), 'buch/gartenjahr')
        self.assertEqual(self.g('rev-list', '--count', 'main..buch/gartenjahr').strip(), '1')
        msg = self.g('log', '-1', '--format=%B')
        self.assertIn('Neues Buch angelegt: Mein Gartenjahr', msg)
        self.assertIn('GhostWriter-Aktion: library.book.create', msg)
        cfg = yaml.safe_load(Path(self.d, 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.assertEqual((cfg['project']['working_title'], cfg['project']['author']), ('Mein Gartenjahr', 'Max'))
        state = yaml.safe_load(Path(self.d, '.ghostwriter/update.yml').read_text(encoding='utf-8'))
        self.assertEqual(state['version'], str(MANIFEST['version']))
        # Erkennung: neues Buch im Aufbau
        found = library.books(library.branch_configs('refs/heads', self.d), MANIFEST)
        self.assertEqual([(b['branch'], b['status']) for b in found], [('buch/gartenjahr', 'setup')])
        # zweites Mal: vergeben, nichts angelegt
        self.g('checkout', '-q', 'main')
        r2 = library.create_book('Gartenjahr', '', '', self.d, 'refs/heads', MANIFEST, base='main')
        self.assertTrue(r2['taken'])
        self.assertEqual(self.g('rev-parse', '--abbrev-ref', 'HEAD').strip(), 'main')

    def test_new_requires_title(self):
        self.assertIn('Arbeitstitel fehlt', library.new_book('', 'X', '', [], MANIFEST)['taken'])

    def test_form(self):
        lib = Path(self.d, 'library.json')
        lib.write_text(json.dumps({'books': [{'branch': 'buch/adhs', 'slug': 'adhs', 'author': 'Alt', 'updated_at': '2026-01-01'},
                                             {'branch': 'buch/b', 'slug': 'b', 'author': 'Neu', 'updated_at': '2026-11-01'}]}),
                       encoding='utf-8')
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), self.d, 'book-create',
                                         '--library', str(lib), *a], capture_output=True, text=True).stdout
        w = run()
        self.assertIn('GW.render("buch-anlegen"', w)
        self.assertIn('"AUTHOR":"Neu"', w)
        self.assertIn('{"TAKEN_SLUG":"adhs","TAKEN_BRANCH":"buch/adhs"}', w)
        t = run('--text', '--draft', json.dumps({'working_title': 'X', 'error': 'Name vergeben'}))
        self.assertIn('✗ Name vergeben', t)
        self.assertIn('`adhs` (buch/adhs)', t)
