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


class TeamGateTest(unittest.TestCase):
    """#455 Teil 2: Rollen in validate durchsetzen."""
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        cfg['team'] = TEAM
        self.write_cfg(cfg)
        self.git('init', '-q'); self.git('add', '-A'); self.commit('Ausgang')
        self.start = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.base, check=True, capture_output=True, text=True).stdout

    def commit(self, msg):
        self.git('-c', 'user.name=t', '-c', 'user.email=t@x', 'commit', '-qam' if msg != 'Ausgang' else '-qm', msg)

    def write_cfg(self, cfg):
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')

    def touch_approvals(self):
        p = self.base / 'approvals.yml'
        p.write_text((p.read_text(encoding='utf-8') if p.is_file() else '') + '\n# geändert\n', encoding='utf-8')
        self.git('add', '-A'); self.commit('abschließen')

    def test_editor_without_approve_may_not_finalize(self):
        self.touch_approvals()
        errs = team.gate(self.base, self.start, 'ben')
        self.assertTrue(errs and 'approvals.yml' in errs[0])
        self.assertEqual(team.gate(self.base, self.start, 'dora'), [])
        self.assertEqual(team.gate(self.base, self.start, 'ANNA'), [])
        self.assertTrue(team.gate(self.base, self.start, 'fremd'))   # nicht im Team: Leser

    def test_new_edition_needs_approval_right(self):
        (self.base / 'editions').mkdir(exist_ok=True)
        (self.base / 'editions/neu.yml').write_text('x: 1\n', encoding='utf-8')
        self.git('add', '-A'); self.commit('Auflage')
        self.assertTrue(team.gate(self.base, self.start, 'ben'))
        self.assertEqual(team.gate(self.base, self.start, 'dora'), [])

    def test_only_owner_changes_team_and_base_team_counts(self):
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        cfg['team'][1]['approve'] = True        # ben befördert sich selbst
        self.write_cfg(cfg); self.commit('Team')
        self.touch_approvals()
        errs = ' '.join(team.gate(self.base, self.start, 'ben'))
        self.assertIn('Team-Liste', errs)
        self.assertIn('abschließen', errs)       # zählt das alte Team, nicht das neue
        self.assertTrue(team.gate(self.base, self.start, 'dora'))   # Freigabeberechtigt, aber kein Eigentümer
        self.assertEqual(team.gate(self.base, self.start, 'anna'), [])

    def test_text_changes_allowed_for_editor_and_no_team_unchanged(self):
        chapter = next((self.base / 'chapters').rglob('*.md'))
        chapter.write_text(chapter.read_text(encoding='utf-8') + '\nNeu.\n', encoding='utf-8')
        self.commit('Text')
        self.assertEqual(team.gate(self.base, self.start, 'ben'), [])
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        del cfg['team']; self.write_cfg(cfg); self.git('add', '-A'); self.commit('ohne')
        plain = self.git('rev-parse', 'HEAD').strip()
        self.touch_approvals()
        self.assertEqual(team.gate(self.base, plain, 'irgendwer'), [])

    def test_cli_gate_exit_code(self):
        self.touch_approvals()
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/team.py'), str(self.base), 'gate',
                              '--base', self.start, '--actor', 'ben'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn('::error::', out.stdout)

    def test_validate_runs_gate_for_books_only(self):
        wf = (ROOT / '.github/workflows/validate.yml').read_text(encoding='utf-8')
        self.assertIn('team.py . gate', wf)
        self.assertIn("steps.kind.outputs.program != '1'", wf)
