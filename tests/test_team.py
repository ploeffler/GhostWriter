"""#455 Teil 1: Team und Rollen je Buch, Git-Benutzer je Person."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import team  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402

TEAM = [{'github': 'Anna', 'role': 'owner'},
        {'github': 'ben', 'role': 'editor', 'name': 'Ben Muster', 'email': '7+ben@users.noreply.github.com'},
        {'github': 'dora', 'role': 'editor', 'approve': True},
        {'github': 'cleo', 'role': 'reader'}]


class TeamTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        (self.base / 'assistant.yml').write_text(yaml.safe_dump({'git': {'name': 'Anna Eigen', 'email': 'anna@example.org'}}),
                                                 encoding='utf-8')

    def errors(self):
        return [e for e in validate_project.check_project(self.base) if 'assistant.yml' not in e]

    def set_team(self, entries):
        p = self.base / 'ghostwriter.yml'
        cfg = yaml.safe_load(p.read_text(encoding='utf-8'))
        if entries is None:
            cfg.pop('team', None)
        else:
            cfg['team'] = entries
        p.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')
        return load(self.base)[1]

    def test_without_team_unchanged(self):
        config = self.set_team(None)
        info = team.role(self.base, config, 'irgendwer')
        self.assertEqual((info['role'], info['write'], info['approve'], info['not_offered']), ('owner', True, True, []))
        self.assertEqual(info['git']['source'], 'assistant.yml')
        self.assertFalse(team.role(self.base, config, 'x', push=False)['write'])   # GitHub-Rechte begrenzen

    def test_roles(self):
        config = self.set_team(TEAM)
        owner = team.role(self.base, config, 'anna')          # Login ohne Rücksicht auf Groß-/Kleinschreibung
        self.assertEqual((owner['role'], owner['approve'], owner['git']['name']), ('owner', True, 'Anna Eigen'))
        ben = team.role(self.base, config, 'ben')
        self.assertEqual((ben['write'], ben['approve'], ben['git']['source']), (True, False, 'team'))
        self.assertIn('approval.confirm', ben['not_offered'])
        self.assertIn('edition.create', ben['not_offered'])
        self.assertIn('schreiben, nicht abschließen', team.summary(ben))
        dora = team.role(self.base, config, 'dora')
        self.assertEqual((dora['approve'], dora['git']), (True, None))   # nie unter dem Namen des Eigentümers
        cleo = team.role(self.base, config, 'cleo')
        self.assertEqual((cleo['write'], cleo['not_offered']), (False, ['alle Schreibaktionen']))
        stranger = team.role(self.base, config, 'fremd')
        self.assertEqual((stranger['role'], stranger['source']), ('reader', 'nicht im team'))
        self.assertFalse(team.role(self.base, config, 'ben', push=False)['write'])
        self.assertEqual(self.errors(), [])

    def test_problems(self):
        config = self.set_team([{'github': 'ben', 'role': 'editor'}, {'github': 'BEN', 'role': 'reader', 'approve': True}])
        errs = '\n'.join(self.errors())
        for text in ('mindestens ein Eintrag mit role: owner', 'BEN doppelt', 'approve nur bei role: editor'):
            self.assertIn(text, errs)
        self.set_team([{'github': 'ben', 'role': 'chef'}])
        self.assertTrue(self.errors())

    def test_cli(self):
        self.set_team(TEAM)
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/team.py'), str(self.base), *a],
                                        capture_output=True, text=True)
        out = run('role', 'ben', '--push', 'true')
        self.assertEqual(out.returncode, 0)
        self.assertIn('ben: Bearbeiter – schreiben, nicht abschließen · Commits als Ben Muster', out.stdout)
        self.assertIn('"role": "reader"', run('role', 'cleo', '--json').stdout)
        self.assertEqual(run('check').returncode, 0)


if __name__ == '__main__':
    unittest.main()
