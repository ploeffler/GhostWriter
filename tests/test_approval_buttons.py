"""Knopftexte der Bestätigungsansicht (#292): Abschließen/Wieder öffnen statt „Freigeben“/„Zurücknehmen“."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ApprovalButtonTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def values(self, *args):
        cmd = [sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args, '--repo', 'o/r']
        r = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = re.search(r'GW\.render\("freigabe-bestaetigen",(\{.*\})\)</script>', r.stdout)
        self.assertIsNotNone(m, r.stdout)
        return json.loads(m.group(1))

    def test_section_buttons(self):
        v = self.values('approval-section', '1.1')
        self.assertEqual((v['APPROVAL_TITLE'], v['APPROVAL_BUTTON']), ('Abschnitt abschließen', 'Abschließen'))
        v = self.values('approval-section', '1.1', '--revoke')
        self.assertEqual((v['APPROVAL_TITLE'], v['APPROVAL_BUTTON']), ('Abschnitt wieder öffnen', 'Wieder öffnen'))

    def test_writing_buttons(self):
        v = self.values('approval-writing', '1.1')
        self.assertEqual(v['APPROVAL_BUTTON'], 'Schreiben erlauben')
        v = self.values('approval-writing', '1.1', '--revoke')
        self.assertEqual(v['APPROVAL_BUTTON'], 'Schreiben sperren')

    def test_no_generic_approve_for_finalizing(self):
        for args in (('approval-section', '1.1'), ('approval-writing', '1.1')):
            v = self.values(*args)
            self.assertNotIn(v['APPROVAL_BUTTON'], ('Freigeben', 'Zurücknehmen'))


if __name__ == '__main__':
    unittest.main()
