"""Doku-Abgleich: die Prüfung selbst läuft und findet nichts (ohne ghostwriter-ui)."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CheckDocsTest(unittest.TestCase):
    def test_data_model_runs_links(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/check_docs.py')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
