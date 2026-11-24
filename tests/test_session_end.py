"""Abschluss-Check beim Verabschieden bzw. am Ende einer Befragung (#298, #372)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import session_end  # noqa: E402


def git(base, *args):
    subprocess.run(['git', '-C', str(base), '-c', 'user.name=t', '-c', 'user.email=t@example.org', *args],
                   check=True, capture_output=True)


class SessionEndTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.remote = Path(tmp.name) / 'remote.git'
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        subprocess.run(['git', 'init', '-q', '--bare', str(self.remote)], check=True)
        git(self.base, 'init', '-q', '-b', 'main')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-q', '-m', 'Start')
        git(self.base, 'remote', 'add', 'origin', str(self.remote))
        git(self.base, 'push', '-q', '-u', 'origin', 'main')
        self.section = sorted(self.base.glob('chapters/*/sections/*.md'))[0]

    def test_nothing_open(self):
        data = session_end.status(self.base, 'none')
        self.assertFalse(data['open'])
        self.assertEqual(data['choices'], [])
        self.assertIn('Nichts offen', session_end.text(data))

    def test_new_chat_offers_saving_only_the_conversation(self):
        data = session_end.status(self.base, 'new')
        self.assertTrue(data['open'])
        self.assertEqual(data['choices'], ['Alles sichern und hochladen', 'Nur das Gespräch sichern', 'Nichts, bis morgen'])

    def test_local_changes_and_waiting_sections(self):
        text = self.section.read_text(encoding='utf-8').replace('status: writing', 'status: ready_for_approval', 1)
        self.section.write_text(text, encoding='utf-8')
        data = session_end.status(self.base, 'none')
        self.assertEqual(len(data['local']['uncommitted']), 1)
        self.assertEqual([w['label'] for w in data['waiting']], ['Abschnitt 1.1'])
        self.assertEqual(data['choices'], ['Alles sichern und hochladen', 'Nichts, bis morgen'])
        git(self.base, 'commit', '-q', '-am', 'Abschnitt fertig')
        data = session_end.status(self.base)
        self.assertEqual((data['local']['uncommitted'], data['local']['unpushed']), ([], 1))
        out = session_end.text(data)
        self.assertIn('1 Änderung(en) gespeichert, aber noch nicht hochgeladen', out)
        self.assertIn('1 warten auf Freigabe: Abschnitt 1.1', out)

    def test_waiting_alone_offers_no_approval_choice(self):
        text = self.section.read_text(encoding='utf-8').replace('status: writing', 'status: ready_for_approval', 1)
        self.section.write_text(text, encoding='utf-8')
        git(self.base, 'commit', '-q', '-am', 'fertig')
        git(self.base, 'push', '-q')
        data = session_end.status(self.base, 'none')
        self.assertTrue(data['open'])
        self.assertEqual(data['choices'], [])   # Freigaben nie Teil der Abschiedsauswahl

    def test_background_backup_pending_keeps_goodbye_open(self):   # #487
        import os
        from unittest.mock import patch
        sys.path.insert(0, str(ROOT / 'scripts'))
        import chat_backup
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'GHOSTWRITER_RECEIPT_DIR': d}):
            chat_backup.write_receipt(Path(d) / 's-1.json', {'state': 'failed', 'error': 'Push abgelehnt'})
            data = session_end.status(self.base, 'none')
            self.assertTrue(data['open'])
            self.assertIn('fehlgeschlagen (Session s-1)', session_end.text(data))
            self.assertIn('Alles sichern und hochladen', data['choices'])
            chat_backup.write_receipt(Path(d) / 's-1.json', {'state': 'saved', 'head': 'abc'})
            self.assertEqual(session_end.status(self.base, 'none')['background'], [])

    def test_cli_json_read_only(self):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/session_end.py'), str(self.base), 'status',
                              '--chat', 'new', '--json'], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out)['chat'], 'new')
        self.assertEqual(subprocess.run(['git', '-C', str(self.base), 'status', '--porcelain'],
                                        capture_output=True, text=True).stdout, '')


if __name__ == '__main__':
    unittest.main()
