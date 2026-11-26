"""Knopftexte der Bestätigungsansicht (#292): Abschließen/Wieder öffnen statt „Freigeben“/„Zurücknehmen“."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tests.widget_helpers import widget_json  # noqa: E402

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
        return widget_json(m.group(1))

    def test_section_buttons(self):
        v = self.values('approval-section', '1.1')
        self.assertEqual((v['APPROVAL_TITLE'], v['APPROVAL_BUTTON']), ('Abschnitt abschließen', 'Abschließen'))
        v = self.values('approval-section', '1.1', '--revoke')
        self.assertEqual((v['APPROVAL_TITLE'], v['APPROVAL_BUTTON']), ('Abschnitt wieder öffnen', 'Wieder öffnen'))
        self.assertIn('Schreiben wird dabei gesperrt', json.dumps(v, ensure_ascii=False))   # #387

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


class ApprovalDriftTest(unittest.TestCase):
    """#563: abgeschlossen, aber Text nach der Freigabe geändert -> neu abschließen statt Hindernis."""
    setUp = ApprovalButtonTest.setUp
    values = ApprovalButtonTest.values

    def approve(self, text_in_log):
        import hashlib
        import yaml
        sec = next((self.base / 'chapters').glob('01-*/sections/01-*.md'))
        text = sec.read_text(encoding='utf-8')
        text = re.sub(r'(?m)^status: .*$', 'status: approved', text, count=1)
        text = re.sub(r'(?m)^(\s+section:) .*$', r'\1 true', text, count=1)
        text = re.sub(r'(?m)^(\s+writing:) .*$', r'\1 true', text, count=1)
        sec.write_text(text, encoding='utf-8')
        ms = text.split('\n## Manuskript\n', 1)[1].strip()
        digest = hashlib.sha256((text_in_log or ms).encode('utf-8')).hexdigest()
        data = {'entries': [{'kind': 'section', 'id': re.search(r'(?m)^id: (\S+)', text).group(1), 'action': 'granted',
                             'at': '2026-11-01T10:00:00+01:00', 'by': 'chat', 'commit': 'a' * 40, 'note': 'content_sha256=' + digest}]}
        (self.base / 'approvals.yml').write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')

    def test_matching_fingerprint_stays_blocked(self):
        self.approve(None)
        v = self.values('approval-section', '1.1')
        self.assertIn('bereits abgeschlossen', json.dumps(v, ensure_ascii=False))
        self.assertNotEqual(v['APPROVAL_TITLE'], 'Geänderten Text neu abschließen')

    def test_changed_text_offers_reapproval(self):
        self.approve('ein ganz anderer früherer Text')
        v = self.values('approval-section', '1.1')
        self.assertEqual(v['APPROVAL_TITLE'], 'Geänderten Text neu abschließen')
        blob = json.dumps(v, ensure_ascii=False)
        self.assertNotIn('bereits abgeschlossen', blob)
        self.assertNotIn('"block"', blob)
        self.assertIn('weicht vom Stand der letzten Freigabe ab', blob)
