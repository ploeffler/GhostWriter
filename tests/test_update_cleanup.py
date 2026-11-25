"""#664: Der tägliche Update-Lauf räumt am Ende Branches auf, nur in Forks und nur nach fehlerfreiem Update."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    data = yaml.safe_load((ROOT / '.github/workflows' / name).read_text(encoding='utf-8'))
    data['_on'] = data.get('on', data.get(True))
    return data


class UpdateCleanupTest(unittest.TestCase):
    def setUp(self):
        self.update = load('update.yml')
        self.cleanup = load('cleanup.yml')
        self.job = self.update['jobs']['cleanup']
        self.cond = ' '.join(str(self.job['if']).split())

    def test_cleanup_is_reusable_and_still_manual(self):
        self.assertIn('workflow_dispatch', self.cleanup['_on'])
        self.assertIn('dry_run', self.cleanup['_on']['workflow_call']['inputs'])

    def test_job_runs_after_update_through_the_same_checked_logic(self):
        self.assertEqual(self.job['needs'], 'update')
        self.assertEqual(self.job['uses'], './.github/workflows/cleanup.yml')
        self.assertEqual(self.job['with'], {'dry_run': False})
        self.assertEqual(self.job['permissions'], {'contents': 'write', 'pull-requests': 'read'})

    def test_conditions_cover_error_dry_run_pause_single_branch_program_and_opt_out(self):
        for part in ("needs.update.result == 'success'", "needs.update.outputs.applied == 'success'",
                     "needs.update.outputs.program != 'true'", "needs.update.outputs.paused != 'true'",
                     'inputs.dry_run != true', "inputs.branch == ''", "vars.GHOSTWRITER_AUTO_CLEANUP != 'false'"):
            self.assertIn(part, self.cond)

    def test_update_job_exposes_what_the_condition_reads(self):
        out = self.update['jobs']['update']['outputs']
        self.assertEqual(set(out), {'program', 'paused', 'applied'})
        self.assertIn('steps.apply.outcome', out['applied'])

    def where(self, repository, upstream):
        step = next(s for s in self.update['jobs']['update']['steps'] if s.get('id') == 'where')
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'ghostwriter-manifest.yml').write_text(yaml.safe_dump({'upstream': {'repo': upstream}}) if upstream else '', encoding='utf-8')
            out = Path(d) / 'out'
            env = {**os.environ, 'GITHUB_REPOSITORY': repository, 'GITHUB_OUTPUT': str(out)}
            r = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', step['run']], cwd=d, env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return out.read_text(encoding='utf-8').strip()

    def test_program_repository_is_recognised(self):
        self.assertEqual(self.where('ploeffler/GhostWriter', 'ploeffler/GhostWriter'), 'program=true')
        self.assertEqual(self.where('Ploeffler/ghostwriter', 'ploeffler/GhostWriter'), 'program=true')
        self.assertEqual(self.where('chillyconcane/YAWA', 'ploeffler/GhostWriter'), 'program=false')
        self.assertEqual(self.where('chillyconcane/YAWA', None), 'program=false')

    def test_where_step_runs_after_dependencies(self):
        names = [s.get('name') for s in self.update['jobs']['update']['steps']]
        self.assertLess(names.index('Abhängigkeiten installieren'), names.index('Programm-Repository erkennen'))


if __name__ == '__main__':
    unittest.main()
