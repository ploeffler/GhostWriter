"""Schutz vor dem Commit und Reparaturweg im Update-Issue für abgeschlossene Abschnitte mit geändertem Text (#595, #563)."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import update_from_upstream as up  # noqa: E402
import workflow_support as ws  # noqa: E402
from render_view import load, section_file  # noqa: E402


class ApprovedDriftTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'b'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.sec = self.config['structure']['chapters'][0]['sections'][0]
        self.path = self.base / self.sec['path']

    def approve(self):
        text = self.path.read_text(encoding='utf-8')
        text = re.sub(r'(?m)^status: .*$', 'status: approved', text, count=1)
        text = re.sub(r'(?m)^(\s+section:) .*$', r'\1 true', text, count=1)
        text = re.sub(r'(?m)^(\s+writing:) .*$', r'\1 true', text, count=1)
        self.path.write_text(text, encoding='utf-8')
        ms = section_file(self.base, self.sec)[3]
        entry = {'kind': 'section', 'id': self.sec['id'], 'action': 'granted', 'at': '2026-11-01T10:00:00+01:00', 'by': 'chat',
                 'commit': 'a' * 40, 'note': 'content_sha256=' + hashlib.sha256(ms.encode('utf-8')).hexdigest()}
        (self.base / 'approvals.yml').write_text(yaml.safe_dump({'entries': [entry]}, allow_unicode=True), encoding='utf-8')

    def cli(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/workflow_support.py'), str(self.base), *args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_unchanged_approved_section_is_fine(self):
        self.approve()
        self.assertEqual(ws.approved_drift(self.base), [])
        self.assertTrue(self.cli('approved-drift')['ok'])

    def test_changed_text_is_reported_before_the_commit(self):
        self.approve()
        self.path.write_text(self.path.read_text(encoding='utf-8') + '\nNachträglich geändert.\n', encoding='utf-8')
        found = ws.approved_drift(self.base)
        self.assertEqual([(f['id'], f['number']) for f in found], [(self.sec['id'], '1.1')])
        self.assertEqual(found[0]['command'], 'python3 scripts/render_view.py . approval-section 1.1')
        out = self.cli('approved-drift', self.sec['path'])
        self.assertFalse(out['ok'])
        self.assertIn('Geänderten Text neu abschließen', out['hint'])
        self.assertTrue(self.cli('approved-drift', 'chapters/other.md')['ok'])   # andere Dateien: nichts zu melden

    def test_not_approved_sections_are_not_reported(self):
        self.path.write_text(self.path.read_text(encoding='utf-8') + '\nGeändert.\n', encoding='utf-8')
        self.assertEqual(ws.approved_drift(self.base), [])

    def test_guard_names_approved_changes_too(self):
        self.approve()
        subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=self.base, check=True)
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '-A'], cwd=self.base, check=True)
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x'], cwd=self.base, check=True)
        self.path.write_text(self.path.read_text(encoding='utf-8') + '\nGeändert.\n', encoding='utf-8')
        out = self.cli('guard', 'HEAD', 'HEAD', self.sec['path'])
        self.assertEqual(out['state'], 'unchanged')
        self.assertEqual(out['approved_changes'][0]['number'], '1.1')


class RepairHintsTest(unittest.TestCase):
    OUT = ('chapters/01/sections/x.md: Manuskript-Fingerabdruck weicht von der letzten Freigabe in approvals.yml ab; Ausweg: '
           '`render_view.py . approval-section 1.2` zeigt „Geänderten Text neu abschließen“ (#563)\n'
           'chapters/02/sections/y.md: Manuskript-Fingerabdruck weicht von der letzten Freigabe in approvals.yml ab; Ausweg: '
           '`render_view.py . approval-section 2.1` zeigt „Geänderten Text neu abschließen“ (#563)\n'
           'matter/vorwort.md: Manuskript-Fingerabdruck weicht von der letzten Freigabe ab; Ausweg: `render_view.py . approval-section '
           'vorwort` zeigt „Geänderten Text neu abschließen“ (#595)\n')

    def test_hints_name_each_section_with_the_command(self):
        text = up.repair_hints(self.OUT)
        self.assertIn('**Reparaturweg:**', text)
        for number in ('1.2', '2.1'):
            self.assertIn(f'`python3 scripts/render_view.py . approval-section {number}`', text)
        self.assertIn('approval-section vorwort', text)
        self.assertIn('danach das Update erneut starten', text)
        self.assertEqual(text.count('approval-section'), 3)

    def test_no_hint_without_fingerprint_message(self):
        self.assertEqual(up.repair_hints('x.md: Titel fehlt\n'), '')


if __name__ == '__main__':
    unittest.main()
