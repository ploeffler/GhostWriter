"""Gesamtsicherung (#489): erstellen, prüfen, wiederherstellen – offline mit nachgebildeter GitHub-Antwort."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import sicherung  # noqa: E402

HAVE = bool(shutil.which('pandoc') and shutil.which('git') and shutil.which('sha256sum'))
FAKE_TOKEN = 'ghp_' + 'A1b2C3d4' * 5


def git(cwd, *args):
    return subprocess.run(['git', '-C', str(cwd), '-c', 'user.name=t', '-c', 'user.email=t@t', *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def fake_fetch(path):
    """Nachgebildete GitHub-API: Secrets nur mit Namen (wie die echte API), Variablen mit Wert."""
    if path.endswith('/actions/secrets'):
        return {'secrets': [{'name': 'GOOGLE_API_KEY'}, {'name': 'GHOSTWRITER_UPDATE_TOKEN'}]}
    if path.endswith('/actions/variables'):
        return {'variables': [{'name': 'GHOSTWRITER_UPDATE_CHANNEL', 'value': 'release'}]}
    if path.endswith('/actions/permissions/workflow'):
        return {'default_workflow_permissions': 'write', 'can_approve_pull_request_reviews': True}
    if path.endswith('/actions/permissions'):
        return {'enabled': True}
    if path.endswith('/actions/workflows'):
        return {'workflows': [{'name': 'Projektdateien prüfen', 'path': '.github/workflows/validate.yml', 'state': 'active'}]}
    if path.endswith('/collaborators'):
        return [{'login': 'anna', 'role_name': 'admin'}]
    if path.endswith('/pages') or path.endswith('/protection'):
        raise RuntimeError('404 Not Found')
    if path.endswith('/environments'):
        return {'environments': []}
    if '/issues/comments' in path:
        return [{'issue_url': 'x/issues/1', 'user': {'login': 'anna'}, 'created_at': '2026-11-01T00:00:00Z', 'body': 'Ein Kommentar'}]
    if '/pulls/comments' in path:
        return []
    if '/pulls' in path:
        return [{'number': 2, 'title': 'PR', 'state': 'closed', 'user': {'login': 'anna'}, 'head': {'ref': 'a'}, 'base': {'ref': 'main'},
                 'merged_at': '2026-11-02T00:00:00Z', 'created_at': '2026-11-01T00:00:00Z', 'body': 'PR-Text'}]
    if '/issues' in path:
        return [{'number': 1, 'title': 'Ein Issue', 'state': 'open', 'user': {'login': 'anna'}, 'labels': [{'name': 'bug'}],
                 'created_at': '2026-11-01T00:00:00Z', 'body': 'Issue-Text'}]
    if path.count('/') == 2:
        return {'full_name': 'o/r', 'private': True, 'default_branch': 'main', 'has_issues': True}
    return []


@unittest.skipUnless(HAVE, 'pandoc, git und sha256sum nötig')
class SicherungTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / 'repo'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.repo)
        git(self.repo, 'init', '-q', '-b', 'main')
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-qm', 'start')
        git(self.repo, 'branch', 'buch/zweites')
        git(self.repo, 'tag', 'v1')

    def make(self, **kw):
        return sicherung.erstellen(self.repo, self.tmp / 'sicherung.zip', 'o/r', fetch=fake_fetch, today='2026-11-25', **kw)

    def test_create_check_and_restore_keeps_branches_tags_and_commits(self):
        out, info = self.make()
        self.assertEqual(sicherung.pruefen(out), [])
        names = zipfile.ZipFile(out).namelist()
        top = names[0].split('/')[0]
        for need in ('LIESMICH.html', 'repository.bundle', 'github-einstellungen.json', 'github-daten/lesbar.md', 'pruefsummen.txt',
                     'wiederherstellen/auf-github.sh', 'wiederherstellen/lokal-oeffnen.bat'):
            self.assertIn(f'{top}/{need}', names)
        self.assertTrue(any(n.endswith('/buch.html') for n in names) and any(n.endswith('/buch.epub') for n in names))
        self.assertEqual(len(info['buecher']), 2)                   # buch/zweites und der Standard-Branch mit Kapiteln
        # Wiederherstellen: gleiche Branches, Tags und Commit-Stände
        out_dir = self.tmp / 'entpackt'
        zipfile.ZipFile(out).extractall(out_dir)
        root = out_dir / top
        target = self.tmp / 'ziel.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(target)], check=True)
        script = root / 'wiederherstellen' / 'auf-github.sh'
        r = subprocess.run(['bash', str(script), str(target), 'nur-git'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        refs = lambda p: sorted(git(p, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/tags').splitlines())   # noqa: E731
        self.assertEqual(refs(target), refs(self.repo))
        local = self.tmp / 'lokal'
        subprocess.run(['git', 'clone', '-q', str(root / 'repository.bundle'), str(local)], check=True)
        self.assertTrue((local / 'ghostwriter.yml').is_file())

    def test_reading_version_has_all_chapters_and_settings_hold_no_secret_values(self):
        out, _ = self.make()
        z = zipfile.ZipFile(out)
        html = next(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('/buch.html'))
        self.assertIn('Endlich eine Erklärung', html)
        settings = json.loads(next(z.read(n) for n in z.namelist() if n.endswith('github-einstellungen.json')))
        self.assertEqual(settings['secrets_namen'], ['GHOSTWRITER_UPDATE_TOKEN', 'GOOGLE_API_KEY'])
        self.assertEqual(settings['variablen'], [{'name': 'GHOSTWRITER_UPDATE_CHANNEL', 'wert': 'release'}])
        self.assertIn('pages', settings['nicht_lesbar'])
        text = next(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('github-daten/lesbar.md'))
        self.assertIn('Ein Issue', text)
        self.assertIn('Ein Kommentar', text)
        self.assertIn('PR-Text', text)

    def test_tampering_missing_file_and_secret_are_found(self):
        out, _ = self.make()
        bad = self.tmp / 'bad.zip'
        with zipfile.ZipFile(out) as zin, zipfile.ZipFile(bad, 'w') as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith('LIESMICH.html'):
                    data = data + b'<!-- manipuliert -->'
                if item.filename.endswith('wiederherstellen/lokal-oeffnen.sh'):
                    continue
                zout.writestr(item, data)
        problems = sicherung.pruefen(bad)
        self.assertTrue(any('lokal-oeffnen.sh' in p for p in problems))
        # Secret-ähnlicher Wert in einem Issue: die Sicherung wird nicht ausgeliefert
        def leaky(path):
            data = fake_fetch(path)
            if '/issues?' in path:
                data[0]['body'] = f'Mein Schlüssel {FAKE_TOKEN}'
            return data
        with self.assertRaisesRegex(RuntimeError, 'eigene Prüfung'):
            sicherung.erstellen(self.repo, self.tmp / 'leak.zip', 'o/r', fetch=leaky, today='2026-11-25')
        self.assertFalse((self.tmp / 'leak.zip').exists())

    def test_without_github_access_the_backup_is_still_valid(self):
        def broken(path):
            raise RuntimeError('401 Bad credentials')
        out, info = sicherung.erstellen(self.repo, self.tmp / 'ohne.zip', 'o/r', fetch=broken, today='2026-11-25')
        self.assertEqual(sicherung.pruefen(out), [])
        self.assertTrue(any('nicht lesbar' in n or 'nicht gesichert' in n for n in info['hinweise']))
        self.assertFalse(info['github'])

    def test_shallow_clone_is_refused(self):
        shallow = self.tmp / 'flach'
        subprocess.run(['git', 'clone', '-q', '--depth', '1', f'file://{self.repo}', str(shallow)], check=True, capture_output=True)
        git(self.repo, 'commit', '--allow-empty', '-qm', 'zwei')
        shallow2 = self.tmp / 'flach2'
        subprocess.run(['git', 'clone', '-q', '--depth', '1', f'file://{self.repo}', str(shallow2)], check=True, capture_output=True)
        with self.assertRaisesRegex(RuntimeError, 'flach'):
            sicherung.erstellen(shallow2, self.tmp / 'x.zip', 'o/r', github=False, today='2026-11-25')

    def test_cli_creates_and_checks(self):
        out = self.tmp / 'cli.zip'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/sicherung.py'), 'erstellen', str(self.repo), '-o', str(out), '--repo', 'o/r',
                            '--ohne-github'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Sicherung erstellt', r.stdout)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/sicherung.py'), 'pruefen', str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == '__main__':
    unittest.main()
