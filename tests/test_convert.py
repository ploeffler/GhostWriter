"""Umwandlung Einzelbuch → Bibliothek (#40): Probelauf ändert nichts, Hindernisse brechen ab,
Umwandlung behält Historie und Tags, Standard-Branch wird Starter, Bücherregal entsteht;
danach ein zweites Buch anlegen."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import convert_to_library  # noqa: E402
import library  # noqa: E402

PROGRAM = ['scripts', 'schemas', 'templates', 'ghostwriter-manifest.yml', 'workflow.yml', 'providers.yml']


class ConvertTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.origin, self.repo = t / 'origin.git', t / 'buch'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(self.origin)], check=True)
        self.repo.mkdir()
        for name in PROGRAM:
            src = ROOT / name
            (shutil.copytree(src, self.repo / name, ignore=shutil.ignore_patterns('__pycache__'))
             if src.is_dir() else shutil.copyfile(src, self.repo / name))
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.repo, dirs_exist_ok=True)
        subprocess.run([sys.executable, str(ROOT / 'scripts/migrate_project.py'), str(self.repo)], capture_output=True)
        self.g('init', '-q', '-b', 'main')
        self.g('add', '.')
        self.g('commit', '-qm', 'Buch')
        self.g('tag', 'adhs-auflage-1')
        self.g('remote', 'add', 'origin', str(self.origin))
        self.g('push', '-q', 'origin', 'main', '--tags')
        self.env = dict(os.environ)
        os.environ.pop('GITHUB_REPOSITORY', None)
        os.environ['GHOSTWRITER_DEFAULT_BRANCH'] = 'main'

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def g(self, *a, cwd=None):
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=cwd or self.repo,
                              check=True, capture_output=True, text=True).stdout.strip()

    def remote_branches(self):
        return sorted(r.split('refs/heads/')[1] for r in self.g('ls-remote', '--heads', str(self.origin)).splitlines())

    def test_dry_run_changes_nothing(self):
        head = self.g('rev-parse', 'HEAD')
        code, lines = convert_to_library.convert(self.repo, dry_run=True)
        self.assertEqual(code, 0, lines)
        self.assertEqual(self.remote_branches(), ['main'])
        self.assertEqual(self.g('rev-parse', 'HEAD'), head)
        self.assertIn('Neuer Buch-Branch: buch/adhs-im-erwachsenenleben', '\n'.join(lines))

    def test_pending_changes_block(self):
        self.g('checkout', '-q', '-b', 'ghostwriter/main')
        self.g('commit', '-q', '--allow-empty', '-m', 'offen')
        self.g('push', '-q', 'origin', 'ghostwriter/main')
        self.g('checkout', '-q', 'main')
        code, lines = convert_to_library.convert(self.repo)
        self.assertEqual(code, 1)
        self.assertIn('Änderungen übernehmen', '\n'.join(lines))
        self.assertEqual(self.remote_branches(), ['ghostwriter/main', 'main'])

    def test_convert_then_second_book(self):
        old_head = self.g('rev-parse', 'HEAD')
        code, lines = convert_to_library.convert(self.repo)
        self.assertEqual(code, 0, lines)
        book = 'buch/adhs-im-erwachsenenleben'
        self.assertEqual(self.remote_branches(), [book, 'main'])
        # Buch-Branch = alter Stand mit vollständiger Historie, Tag bleibt gültig
        self.assertEqual(self.g('rev-parse', f'origin/{book}'), old_head)
        self.assertEqual(self.g('rev-parse', 'adhs-auflage-1^{commit}'), old_head)
        # Standard-Branch: Starter, keine Buchdateien, Bücherregal; alter Stand in der Historie
        self.g('fetch', '-q', 'origin')
        self.assertEqual(self.g('rev-parse', 'origin/main^'), old_head)
        self.assertFalse((self.repo / 'chapters').exists())
        self.assertEqual((self.repo / 'ghostwriter.yml').read_text(encoding='utf-8'),
                         (ROOT / 'templates/ghostwriter-starter.yml').read_text(encoding='utf-8'))
        lib = json.loads((self.repo / 'library.json').read_text(encoding='utf-8'))
        self.assertEqual([b['branch'] for b in lib['books']], [book])
        self.assertIn('GhostWriter-Aktion: library.convert', self.g('log', '-1', '--format=%B'))
        # zweimal geht nicht
        self.assertEqual(convert_to_library.convert(self.repo)[0], 1)
        # zweites Buch anlegen; die Bibliothek erkennt beide
        r = library.create_book('Mein Gartenjahr', 'Gartenjahr', '', self.repo, 'refs/remotes/origin', base='main')
        self.assertEqual(r['taken'], [])
        self.g('push', '-q', 'origin', 'buch/gartenjahr')
        self.g('fetch', '-q', 'origin')
        found = library.books(library.branch_configs('refs/remotes/origin', self.repo), None, 'main')
        self.assertEqual([(b['branch'], b['status']) for b in found], [(book, 'ready'), ('buch/gartenjahr', 'setup')])
        # Rückweg: Revert stellt den Einzelbuch-Stand wieder her
        self.g('checkout', '-q', 'main')
        self.g('reset', '-q', '--hard', 'origin/main')
        self.g('revert', '--no-edit', 'HEAD')
        self.assertEqual(self.g('diff', old_head, 'HEAD', '--stat'), '')

    def test_starter_matches_template(self):
        self.assertEqual((ROOT / 'templates/ghostwriter-starter.yml').read_text(encoding='utf-8'),
                         (ROOT / 'ghostwriter.yml').read_text(encoding='utf-8'),
                         'templates/ghostwriter-starter.yml muss der ghostwriter.yml des Hauptrepositorys entsprechen')


if __name__ == '__main__':
    unittest.main()
