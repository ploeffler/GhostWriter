"""Update-Kanal (#604): Bücher holen nur Releases, Ausnahmen über GHOSTWRITER_UPDATE_CHANNEL bzw. --channel."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import update_from_upstream as up  # noqa: E402


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


class PickTagTest(unittest.TestCase):
    def test_release_ignores_candidates_and_sorts_by_version(self):
        names = ['v0.9', 'v1.0', 'v1.0-rc.1', 'v1.0.1', 'v1.1-rc.2', 'latest', 'v1.10', 'v1.9']
        self.assertEqual(up.pick_tag(names, 'release'), 'v1.10')   # nach Version, nicht als Text
        self.assertEqual(up.pick_tag(['v1.0', 'v1.1-rc.1'], 'release'), 'v1.0')
        self.assertIsNone(up.pick_tag(['v1.1-rc.1', 'x'], 'release'))

    def test_rc_includes_candidates_and_release_beats_its_candidates(self):
        self.assertEqual(up.pick_tag(['v1.0', 'v1.1-rc.1', 'v1.1-rc.2'], 'rc'), 'v1.1-rc.2')
        self.assertEqual(up.pick_tag(['v1.1', 'v1.1-rc.2'], 'rc'), 'v1.1')

    def test_channel_names(self):
        self.assertEqual(up.channel_of(None), 'release')
        self.assertEqual(up.channel_of(' RC '), 'rc')
        self.assertEqual(up.channel_of('main'), 'main')
        with self.assertRaises(ValueError):
            up.channel_of('beta')


class ChannelRunTest(unittest.TestCase):
    """Attrappe des Hauptrepositorys: c1 = 1.0.0 (v1.0), c2 = 1.1.0 (v1.1-rc.1), c3 = main ohne Tag."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.up = self.tmp / 'upstream'
        self.up.mkdir()
        git(self.up, 'init', '-q', '-b', 'main')
        self.commit(self.up, '1.0.0', 'eins')
        git(self.up, 'tag', 'v1.0')
        self.commit(self.up, '1.1.0', 'zwei')
        git(self.up, 'tag', 'v1.1-rc.1')
        self.commit(self.up, '1.1.0', 'drei')
        self.book_old = self.clone('book-old', 'v1.0')    # Buch auf dem Stand des Releases
        self.book_main = self.clone('book-main', 'main')  # Buch mit neuerem main-Stand

    def commit(self, repo, version, text):
        (Path(repo) / 'ghostwriter-manifest.yml').write_text(
            f'name: GhostWriter\nversion: {version}\nupstream:\n  repo: ploeffler/GhostWriter\n  ref: main\n'
            'managed:\n  - START.md\nbook:\n  - ghostwriter.yml\n', encoding='utf-8')
        (Path(repo) / 'START.md').write_text(text + '\n', encoding='utf-8')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-qm', text)

    def clone(self, name, rev):
        """Buch-Repository mit eigenem origin (bare), dessen main auf `rev` des Hauptrepositorys steht."""
        origin = self.tmp / f'{name}.git'
        git(self.tmp, 'init', '-q', '--bare', '-b', 'main', str(origin))
        git(self.up, 'push', '-q', str(origin), f'{rev}:refs/heads/main')
        path = self.tmp / name
        git(self.tmp, 'clone', '-q', str(origin), str(path))
        git(path, 'remote', 'set-head', 'origin', 'main')
        return path

    def run_update(self, book, channel=None, arg=None, upstream=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith(('GITHUB_', 'GHOSTWRITER_'))}
        env.update(GITHUB_REPOSITORY='me/book', GHOSTWRITER_UPSTREAM_URL=str(upstream or self.up))
        if channel is not None:
            env['GHOSTWRITER_UPDATE_CHANNEL'] = channel
        status = self.tmp / 'status.json'
        status.unlink(missing_ok=True)
        cmd = [sys.executable, str(ROOT / 'scripts/update_from_upstream.py'), '--dry-run', '--status', str(status)]
        if arg:
            cmd += ['--channel', arg]
        r = subprocess.run(cmd, cwd=book, env=env, capture_output=True, text=True)
        results = json.loads(status.read_text(encoding='utf-8')) if status.exists() else []
        return r, results

    def test_default_is_the_latest_release_not_main(self):
        r, res = self.run_update(self.book_old)   # Variable fehlt: Vorgabe release
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([x['status'] for x in res], ['current'], res)   # main (c3) wird nicht geholt
        self.assertIn('ploeffler/GhostWriter@v1.0', res[0]['upstream'])
        self.assertIn('Kanal `release`', r.stdout)
        self.assertIn('Release 1.0.0 (Tag `v1.0`', r.stdout)
        self.assertIn('releases/tag/v1.0', r.stdout)

    def test_rc_channel_via_variable_and_manual_override(self):
        r, res = self.run_update(self.book_old, channel='rc')
        self.assertEqual((r.returncode, res[0]['status']), (0, 'updated'), r.stdout + r.stderr)
        self.assertIn('@v1.1-rc.1', res[0]['upstream'])
        r, res = self.run_update(self.book_old, channel='main', arg='release')   # --channel gewinnt
        self.assertEqual(res[0]['status'], 'current')
        self.assertIn('@v1.0', res[0]['upstream'])

    def test_main_channel_as_before(self):
        r, res = self.run_update(self.book_old, channel='main')
        self.assertEqual(res[0]['status'], 'updated', r.stdout + r.stderr)
        self.assertEqual(res[0]['upstream'], 'ploeffler/GhostWriter:main')
        self.assertEqual(res[0]['behind'], 2)

    def test_no_step_back_for_a_book_on_main(self):
        r, res = self.run_update(self.book_main)
        self.assertEqual((r.returncode, res[0]['status']), (0, 'current'), r.stdout + r.stderr)
        self.assertIn('Stand von main (1.1.0+', res[0]['text'])
        self.assertIn('wartet auf das nächste Release', res[0]['text'])

    def test_higher_release_is_taken_after_a_main_book(self):
        git(self.up, 'checkout', '-q', 'main')
        self.commit(self.up, '1.2.0', 'vier')
        git(self.up, 'tag', 'v1.2')
        r, res = self.run_update(self.book_main)
        self.assertEqual(res[0]['status'], 'updated', r.stdout + r.stderr)
        self.assertIn('@v1.2', res[0]['upstream'])

    def test_no_tag_means_no_update(self):
        bare = self.tmp / 'notags'
        bare.mkdir()
        git(bare, 'init', '-q', '-b', 'main')
        self.commit(bare, '1.0.0', 'x')
        r, res = self.run_update(self.book_old, upstream=bare)
        self.assertEqual((r.returncode, res), (0, []))
        self.assertIn('noch keinen Release-Tag', r.stdout)
        self.assertIn('GHOSTWRITER_UPDATE_CHANNEL', r.stdout)

    def test_unknown_channel_is_refused(self):
        r, res = self.run_update(self.book_old, channel='beta')
        self.assertEqual((r.returncode, res), (1, []))
        self.assertIn('Unbekannter Update-Kanal', r.stdout)


if __name__ == '__main__':
    unittest.main()
