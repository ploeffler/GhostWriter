"""#470: Das Update zieht offene Änderungspakete (ghostwriter/<buch>) auf den neuen Buchstand."""
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import update_from_upstream as up  # noqa: E402

BOOK, WORK = 'buch/a', 'ghostwriter/buch/a'


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@t', *args], cwd=cwd, check=True,
                          text=True, capture_output=True).stdout.strip()


def write(cwd, name, text):
    path = Path(cwd, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


class WorkBranchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.origin = Path(tmp.name, 'origin.git')
        self.dev = Path(tmp.name, 'dev')
        self.clone = Path(tmp.name, 'clone')
        git(tmp.name, 'init', '-q', '--bare', '-b', 'main', str(self.origin))
        git(tmp.name, 'clone', '-q', str(self.origin), str(self.dev))
        write(self.dev, 'kapitel/01.md', 'Text\n')
        write(self.dev, 'scripts/tool.py', 'alt\n')
        git(self.dev, 'add', '.')
        git(self.dev, 'commit', '-qm', 'Buch')
        git(self.dev, 'push', '-q', 'origin', f'HEAD:{BOOK}')
        git(self.dev, 'switch', '-q', '-c', WORK)
        write(self.dev, 'kapitel/02.md', 'Neuer Abschnitt\n')
        git(self.dev, 'add', '.')
        git(self.dev, 'commit', '-qm', 'Arbeit')
        git(self.dev, 'push', '-q', 'origin', f'HEAD:{WORK}')
        git(self.dev, 'switch', '-q', '--detach', f'origin/{BOOK}')
        write(self.dev, 'scripts/tool.py', 'neu\n')   # das Update hat das Buch auf den neuen Programmstand gebracht
        git(self.dev, 'commit', '-qam', 'GhostWriter aktualisiert')
        git(self.dev, 'push', '-q', 'origin', f'HEAD:{BOOK}')
        git(tmp.name, 'clone', '-q', str(self.origin), str(self.clone))
        old = os.getcwd()
        os.chdir(self.clone)
        self.addCleanup(os.chdir, old)
        git(self.clone, 'fetch', '-q', 'origin', '+refs/heads/*:refs/remotes/origin/*')

    def follow(self, pr=7, dry_run=False, workflows=True):
        return up.follow_work_branch(BOOK, types.SimpleNamespace(dry_run=dry_run), workflows, lambda w, b: pr)

    def remote(self, ref, path):
        return git(self.clone, 'show', f'{ref}:{path}')

    def test_open_change_package_gets_book_state(self):
        res = self.follow()
        self.assertEqual(res['status'], 'updated', res)
        self.assertIn('Änderungspaket #7', res['text'])
        git(self.clone, 'fetch', '-q', 'origin')
        self.assertEqual(self.remote(f'origin/{WORK}', 'scripts/tool.py'), 'neu')        # neuer Programmstand
        self.assertEqual(self.remote(f'origin/{WORK}', 'kapitel/02.md'), 'Neuer Abschnitt')   # Arbeit bleibt
        self.assertIsNone(self.follow())   # danach aktuell: nichts zu tun

    def test_without_pull_request_or_in_dry_run_nothing_changes(self):
        before = git(self.clone, 'rev-parse', f'origin/{WORK}')
        self.assertEqual(self.follow(pr=None)['status'], 'skipped')
        res = self.follow(dry_run=True)
        self.assertIn('Probelauf', res['text'])
        git(self.clone, 'fetch', '-q', 'origin')
        self.assertEqual(git(self.clone, 'rev-parse', f'origin/{WORK}'), before)

    def test_conflict_leaves_change_package_unchanged(self):
        git(self.dev, 'switch', '-q', '--detach', f'origin/{WORK}')
        write(self.dev, 'scripts/tool.py', 'im Paket geändert\n')
        git(self.dev, 'commit', '-qam', 'Konflikt')
        git(self.dev, 'push', '-q', 'origin', f'HEAD:{WORK}')
        git(self.clone, 'fetch', '-q', 'origin')
        before = git(self.clone, 'rev-parse', f'origin/{WORK}')
        res = self.follow()
        self.assertEqual(res['status'], 'conflict')
        self.assertIn('scripts/tool.py', res['text'])
        git(self.clone, 'fetch', '-q', 'origin')
        self.assertEqual(git(self.clone, 'rev-parse', f'origin/{WORK}'), before)

    def test_workflow_changes_need_update_token(self):
        git(self.dev, 'switch', '-q', '--detach', f'origin/{BOOK}')
        write(self.dev, '.github/workflows/x.yml', 'on: push\n')
        git(self.dev, 'add', '.')
        git(self.dev, 'commit', '-qm', 'Workflow')
        git(self.dev, 'push', '-q', 'origin', f'HEAD:{BOOK}')
        res = self.follow(workflows=False)
        self.assertEqual(res['status'], 'skipped')
        self.assertIn('GHOSTWRITER_UPDATE_TOKEN', res['text'])

    def test_no_work_branch(self):
        self.assertIsNone(up.follow_work_branch('buch/b', types.SimpleNamespace(dry_run=False), True, lambda w, b: 1))

    def test_test_override_for_open_pull_requests(self):
        os.environ['GHOSTWRITER_OPEN_PRS'] = '{"ghostwriter/buch/a": 12}'
        self.addCleanup(os.environ.pop, 'GHOSTWRITER_OPEN_PRS', None)
        self.assertEqual(up.open_change_package(WORK, BOOK), 12)
        self.assertIsNone(up.open_change_package('ghostwriter/buch/b', 'buch/b'))


if __name__ == '__main__':
    unittest.main()
