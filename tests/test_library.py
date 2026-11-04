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
# Leere Starter-Konfiguration für Testrepositorys. Nicht ROOT/ghostwriter.yml: In einem
# Buch-Repository steht dort das Buch, nicht der Starter.
STARTER_FILE = ROOT / 'templates/ghostwriter-starter.yml'
_ROOT_CFG = yaml.safe_load((ROOT / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
# Buch-Repository (Fork oder Template mit eigenem Buch): Prüfungen, die nur für das
# Programm-Repository gelten, werden dort übersprungen.
IN_BOOK_REPO = bool((_ROOT_CFG.get('structure') or {}).get('chapters')
                    or (_ROOT_CFG.get('project') or {}).get('title'))
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
        Path(d, 'ghostwriter.yml').write_text(STARTER_FILE.read_text(encoding='utf-8'), encoding='utf-8')
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
        Path(d, 'ghostwriter.yml').write_text(STARTER_FILE.read_text(encoding='utf-8'), encoding='utf-8')
        self.g('add', '.')
        self.g('commit', '-qm', 'Starter')

    def tearDown(self):
        self.tmp.cleanup()

    def test_set_fields_keeps_comments(self):
        text = STARTER_FILE.read_text(encoding='utf-8')
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
        Path(self.d, 'assistant.yml').write_text('format: 1\nrepo: a/b\nskill: anna-auf-b\nauthor: Anna Profil\n', encoding='utf-8')
        self.assertIn('"AUTHOR":"Anna Profil"', run())   # Assistenten-Profil (#136) geht vor dem letzten Buch


class DefaultBranchAndUpdateTest(unittest.TestCase):
    """#39: Standard-Branch mit Kapiteln ist ein Buch (Einzelbuch); Update im Fork: Standard-Branch zuerst, dann Bücher."""

    def test_default_branch_rule(self):
        self.assertTrue(library.is_book('main', book('X'), MANIFEST, default='main'))      # Einzelbuch, trotz skip
        self.assertFalse(library.is_book('main', STARTER, MANIFEST, default='main'))       # Bibliothek
        self.assertFalse(library.is_book('main', book('X'), MANIFEST))                     # Hauptrepository ohne Angabe

    def test_is_command(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'ghostwriter.yml').write_text(yaml.safe_dump(book('X')), encoding='utf-8')
            run = lambda b, env: subprocess.run([sys.executable, str(ROOT / 'scripts/library.py'), 'is', b, '--dir', d],
                                                capture_output=True, env=env).returncode
            import os
            env = dict(os.environ, GHOSTWRITER_DEFAULT_BRANCH='main')
            self.assertEqual(run('main', env), 0)
            self.assertEqual(run('buch/x', env), 0)
            self.assertEqual(run('ghostwriter/buch/x', env), 1)
            Path(d, 'ghostwriter.yml').write_text(yaml.safe_dump(STARTER), encoding='utf-8')
            self.assertEqual(run('main', env), 1)

    def test_update_branch_selection_in_fork(self):
        import os
        import update_from_upstream as up
        with tempfile.TemporaryDirectory() as d:
            g = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True,
                                          capture_output=True, text=True).stdout
            g('init', '-q', '-b', 'main')
            for name, cfg in [('main', STARTER), ('buch/a', book('A')), ('buch/neu', STARTER), ('ghostwriter/buch/a', book('A')),
                              ('feature/x', STARTER), ('alt', book('Alt'))]:
                Path(d, 'ghostwriter.yml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
                g('add', '.')
                g('commit', '-q', '--allow-empty', '-m', name)
                g('update-ref', f'refs/remotes/origin/{name}', 'HEAD')
            old, env = os.getcwd(), dict(os.environ)
            try:
                os.chdir(d)
                os.environ['GITHUB_EVENT_PATH'] = str(Path(d, 'event.json'))
                Path(d, 'event.json').write_text(json.dumps({'repository': {'default_branch': 'main'}}), encoding='utf-8')
                self.assertEqual(up.branches(MANIFEST, False, 'main', None), ['main', 'alt', 'buch/a', 'buch/neu'])
                self.assertEqual(up.branches(MANIFEST, True, 'main', None), ['alt', 'buch/a', 'buch/neu'])
            finally:
                os.chdir(old)
                os.environ.clear()
                os.environ.update(env)


class DataPageTest(unittest.TestCase):
    """Seite „Daten“ (#71, Teil 1): library.json mit Programm- und Buchstand, Secrets nur als Namen, Ansicht mit und ohne GitHub-Daten."""

    @classmethod
    def setUpClass(cls):
        import os
        import shutil
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = cls.tmp.name
        g = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True, capture_output=True)
        g('init', '-q', '-b', 'main')
        Path(d, 'ghostwriter.yml').write_text(STARTER_FILE.read_text(encoding='utf-8'), encoding='utf-8')
        shutil.copytree(ROOT / 'templates/ui', Path(d, 'templates/ui'))
        g('add', '.')
        g('commit', '-qm', 'Starter')
        g('checkout', '-q', '-b', 'buch/adhs')
        shutil.copytree(ROOT / 'tests/fixtures/adhs', d, dirs_exist_ok=True)
        g('add', '.')
        g('commit', '-qm', 'Kapitel 1 überarbeitet')
        g('tag', 'adhs-im-erwachsenenleben-auflage-1')
        g('tag', 'adhs-im-erwachsenenleben-auflage-2')
        g('checkout', '-q', 'main')
        env = dict(os.environ, SECRETS_PRESENT=json.dumps({'GHOSTWRITER_UPDATE_TOKEN': True, 'OTHER': False}))
        cls.lib = Path(d, 'library.json')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/library.py'), 'build', '--namespace', 'refs/heads',
                            '--repo', d, '--out', str(cls.lib)], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        cls.data = json.loads(cls.lib.read_text(encoding='utf-8'))
        cls.gh = Path(d, 'github.json')
        cls.gh.write_text(json.dumps({
            'repo': {'private': True, 'size': 2048}, 'branches': ['main', 'buch/adhs', 'ghostwriter/buch/adhs'],
            'pulls': [{'number': 7, 'head': {'ref': 'ghostwriter/buch/adhs'}}],
            'rate_limit': {'resources': {'core': {'limit': 5000, 'remaining': 300}}},
            'runs': [{'name': 'Probedruck', 'head_branch': 'buch/adhs', 'conclusion': 'success', 'created_at': '2026-11-01T10:00:00Z', 'html_url': 'u1'},
                     {'name': 'Projektdateien prüfen', 'head_branch': 'buch/adhs', 'conclusion': 'failure', 'created_at': '2026-11-02T10:00:00Z', 'html_url': 'u2'}]}),
            encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def view(self, *a):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), self.d, 'data', '--library', str(self.lib), *a],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_library_json(self):
        b = self.data['books'][0]
        self.assertEqual(b['last_commit'], 'Kapitel 1 überarbeitet')
        self.assertEqual(b['last_edition']['number'], 2)
        self.assertEqual(b['data_version'], 0)
        self.assertTrue(b['migration_pending'])
        self.assertNotIn('secret_names', b)
        self.assertEqual(self.data['program']['ui_commit'], yaml.safe_load((ROOT / 'templates/ui/ghostwriter-ui.yml').read_text())['commit'])
        self.assertEqual(self.data['secrets'], {'GHOSTWRITER_UPDATE_TOKEN': True})
        self.assertNotIn('***', self.lib.read_text(encoding='utf-8'))

    def test_secrets_kept_without_secrets_json(self):
        import os
        env = {k: v for k, v in os.environ.items() if k != 'SECRETS_PRESENT'}
        subprocess.run([sys.executable, str(ROOT / 'scripts/library.py'), 'build', '--namespace', 'refs/heads',
                        '--repo', self.d, '--out', str(self.lib)], capture_output=True, env=env, check=True)
        self.assertEqual(json.loads(self.lib.read_text(encoding='utf-8'))['secrets'], {'GHOSTWRITER_UPDATE_TOKEN': True})

    def test_view_with_github(self):
        t = self.view('--github', str(self.gh), '--text')
        self.assertIn('privat · 2,0 MB · 3 Branches', t)
        self.assertIn('Probedruck vom 01.11.2026, Download bis 15.11.2026', t)
        self.assertIn('❌ Prüfung beim letzten Push: fehlgeschlagen', t)
        self.assertIn('Migration steht aus', t)
        self.assertIn('`GHOSTWRITER_UPDATE_TOKEN` ✅ hinterlegt', t)
        self.assertIn('| GitHub-API | 🔴 6 % übrig (4700 von 5000 verbraucht) |', t)   # Nutzungsgrenzen (#62)
        self.assertIn('> ⏸ Update-Automatik pausiert: GitHub-API 6 % übrig', t)
        w = self.view('--github', str(self.gh))
        self.assertIn('"LIMITS":[{"L_LABEL":"GitHub-API","L_STATE":"pause"', w)
        self.assertIn('GW.render("daten"', w)
        self.assertIn('"GITHUB_KNOWN":"1"', w)

    def test_view_without_github(self):
        w = self.view()
        self.assertIn('"GITHUB_KNOWN":""', w)
        self.assertNotIn('"LIMITS"', w)
        self.assertIn('Prüfung: unbekannt', self.view('--text'))


class RepoNameTest(unittest.TestCase):
    """#134: Bücherregal, Serie und Daten zeigen das eigene Repository, nie das Hauptrepository als Vorgabe."""

    def setUp(self):
        import os
        import render_view
        self.rv = render_view
        self.env = dict(os.environ)
        os.environ.pop('GITHUB_REPOSITORY', None)
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        subprocess.run(['git', 'init', '-q', self.d], check=True)

    def tearDown(self):
        import os
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def remote(self, url):
        subprocess.run(['git', '-C', self.d, 'remote', 'add', 'origin', url], check=True)

    def test_detect_from_remote(self):
        for url in ('https://github.com/someone/YAWA.git', 'git@github.com:someone/YAWA.git',
                    'http://local_proxy@127.0.0.1:41733/git/someone/YAWA', 'https://github.com/someone/YAWA/'):
            subprocess.run(['git', '-C', self.d, 'remote', 'remove', 'origin'], capture_output=True)
            self.remote(url)
            self.assertEqual(self.rv.detect_repo(self.d), 'someone/YAWA', url)

    def test_env_wins_and_unknown(self):
        import os
        self.assertEqual(self.rv.detect_repo(self.d), '')
        os.environ['GITHUB_REPOSITORY'] = 'other/books'
        self.assertEqual(self.rv.detect_repo(self.d), 'other/books')

    def render(self, *a):
        import os
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), self.d, 'library', '--text', *a],
                           capture_output=True, text=True, env=dict(os.environ))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_library_view(self):
        import shutil
        shutil.copyfile(STARTER_FILE, Path(self.d, 'ghostwriter.yml'))
        out = self.render()
        self.assertNotIn('ploeffler/GhostWriter ·', out)
        self.assertIn('unbekanntes Repository ·', out)
        self.remote('https://github.com/someone/YAWA.git')
        self.assertIn('someone/YAWA ·', self.render())
        self.assertIn('given/name ·', self.render('--repo', 'given/name'))


class PushErrorTest(unittest.TestCase):
    def test_workflow_scope_hint(self):
        import update_from_upstream as u
        err = ' ! [remote rejected] HEAD -> main (refusing to allow a Personal Access Token to create or update workflow `.github/workflows/edition.yml` without `workflow` scope)'
        text = u.push_error('main', err)
        self.assertTrue(text.startswith('Push nach main abgelehnt: Token ohne Workflow-Recht.'))
        self.assertIn('Workflows: Read and write', text)
        self.assertIn('der nächste Lauf versucht es erneut', u.push_error('main', 'non-fast-forward'))

    def test_push_kinds_and_retry(self):
        """GitHub-Serverfehler beim Push werden wiederholt, ein inzwischen weitergewanderter Branch neu eingespielt."""
        import update_from_upstream as u
        err500 = 'remote: Internal Server Error\n ! [remote rejected] HEAD -> main (Internal Server Error)'
        self.assertEqual(u.push_kind(err500), 'transient')
        self.assertEqual(u.push_kind(' ! [rejected] HEAD -> main (fetch first)'), 'stale')
        self.assertEqual(u.push_kind(' ! [rejected] HEAD -> main (non-fast-forward)'), 'stale')
        self.assertEqual(u.push_kind('without `workflow` scope'), 'other')
        self.assertIn('GitHub-Serverfehler', u.push_error('main', err500))
        calls = []

        class R:
            def __init__(self, code, err):
                self.returncode, self.stderr = code, err

        answers = [R(1, err500), R(1, err500), R(0, '')]
        orig_run, orig_sleep = u.subprocess.run, __import__('time').sleep
        try:
            u.subprocess.run = lambda cmd, **kw: (calls.append(cmd), answers.pop(0))[1]
            __import__('time').sleep = lambda s: None
            self.assertEqual(u.push('HEAD:refs/heads/main'), (0, ''))
            self.assertEqual(len(calls), 3)
            answers[:] = [R(1, ' ! [rejected] (fetch first)')]
            calls.clear()
            code, err = u.push('HEAD:refs/heads/main')
            self.assertEqual((code, len(calls)), (1, 1), 'veralteter Stand: kein blindes Wiederholen')
        finally:
            u.subprocess.run, __import__('time').sleep = orig_run, orig_sleep


class ProgramRepoTest(unittest.TestCase):
    """#48: Das Programm-Repository enthält keine Buchinhalte."""

    def test_program_problems(self):
        import os
        import shutil
        with tempfile.TemporaryDirectory() as d:
            g = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True, capture_output=True)
            g('init', '-q', '-b', 'main')
            shutil.copyfile(STARTER_FILE, Path(d, 'ghostwriter.yml'))
            g('add', '.')
            g('commit', '-qm', 'Programm')
            env, os.environ['GHOSTWRITER_DEFAULT_BRANCH'] = dict(os.environ), 'main'
            try:
                self.assertEqual(library.program_problems(d, 'refs/heads', MANIFEST), ([], []))
                g('branch', 'buch/x')
                g('tag', 'x-auflage-1')
                errors, warnings = library.program_problems(d, 'refs/heads', MANIFEST)
                self.assertEqual(warnings, [])
                self.assertTrue(any('Buch-Branch buch/x' in e for e in errors))
                self.assertTrue(any('Auflagen-Tag x-auflage-1' in e for e in errors))
                r = subprocess.run([sys.executable, str(ROOT / 'scripts/library.py'), 'check-program',
                                    '--namespace', 'refs/heads', '--repo', d], capture_output=True, text=True)
                self.assertEqual(r.returncode, 1, r.stdout)
                g('branch', '-D', 'buch/x')
                g('tag', '-d', 'x-auflage-1')
                self.assertEqual(library.program_problems(d, 'refs/heads', MANIFEST), ([], []))
                shutil.copytree(ROOT / 'tests/fixtures/adhs', d, dirs_exist_ok=True)
                errors, _ = library.program_problems(d, 'refs/heads', MANIFEST)
                self.assertTrue(any('Kapitel' in e for e in errors))
                self.assertTrue(any(e.startswith('chapters/') for e in errors))
            finally:
                os.environ.clear()
                os.environ.update(env)

    @unittest.skipIf(IN_BOOK_REPO, 'nur im Programm-Repository: ein Buch-Repository hat Kapitel')
    def test_main_repo_is_clean(self):
        errors, _ = library.program_problems(ROOT, 'refs/heads', MANIFEST)
        self.assertEqual(errors, [])


class SecretCheckTest(unittest.TestCase):
    """Workflows prüfen Secrets nur einzeln nach Namen, nie mit toJSON(secrets)."""

    def test_workflows_list_all_known_names(self):
        import secret_check
        missing = [w for w in secret_check.WORKFLOWS if not (ROOT / w).exists()]
        if IN_BOOK_REPO and missing:
            # Ohne GHOSTWRITER_UPDATE_TOKEN spielt das Update keine Workflow-Dateien ein (docs/UPDATES.md)
            self.skipTest('Workflow-Dateien fehlen im Buch-Repository: ' + ', '.join(missing))
        self.assertEqual(secret_check.check(), [])
        self.assertIn('GHOSTWRITER_UPDATE_TOKEN', secret_check.known_names())

    def test_state(self):
        import os
        import secret_check
        old = os.environ.get('SECRETS_PRESENT')
        try:
            os.environ['SECRETS_PRESENT'] = '{"OPENAI_API_KEY": true, "GEMINI_API_KEY": false}'
            self.assertEqual(secret_check.state(['OPENAI_API_KEY', 'GEMINI_API_KEY', 'MEIN_KEY']),
                             {'OPENAI_API_KEY': True, 'GEMINI_API_KEY': False, 'MEIN_KEY': None})
            del os.environ['SECRETS_PRESENT']
            self.assertEqual(secret_check.state(['X'], {'X': True}), {'X': True})
        finally:
            if old is not None:
                os.environ['SECRETS_PRESENT'] = old
