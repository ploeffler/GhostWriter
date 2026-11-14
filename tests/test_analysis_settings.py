"""Formular „Analyse-Einstellungen“ (#299): Ansicht, Speichern mit Prüfung, Vorgaben."""
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
import analyze  # noqa: E402
import validate_project  # noqa: E402


class AnalysisSettingsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def config(self):
        return yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))

    def view(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-settings',
                            '--repo', 'o/r', *args], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_save_and_view(self):
        before = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        analyze.settings_set(self.base, {'provider': 'openai', 'model': ' mini ', 'merge_model': '',
                                         'price_input_per_mtok': '0,25', 'price_output_per_mtok': 2, 'parallel': 6,
                                         'languagetool': {'language': 'de-AT', 'words': ['Opa Karl', 'Opa Karl', ' '],
                                                          'disabled_rules': []}})
        a = self.config()['analysis']
        self.assertEqual(a, {'provider': 'openai', 'model': 'mini', 'price_input_per_mtok': 0.25,
                             'price_output_per_mtok': 2, 'parallel': 6,
                             'languagetool': {'language': 'de-AT', 'words': ['Opa Karl']}})
        self.assertEqual(validate_project.check_project(self.base), [])
        after = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        self.assertTrue(after.startswith(before.rstrip('\n')))   # Rest der Datei unverändert
        data = json.loads(re.search(r'GW\.render\("analyse-einstellungen",(\{.*\})\)', self.view()).group(1))
        self.assertEqual((data['ANALYSIS_PROVIDER'], data['PRICE_INPUT'], data['PARALLEL'], data['LT_WORDS']),
                         ('openai', '0.25', '6', 'Opa Karl'))
        self.assertEqual(data['DEFAULT_MODEL_OPENAI'], analyze.PROVIDERS['openai']['model'])
        text = self.view('--text')
        self.assertIn('| Anbieter | openai |', text)
        self.assertIn('| Eigene Wörter | Opa Karl |', text)
        self.assertIn('| Provider | openai |', self.view('--text', '--language', 'en'))
        # Zurück auf Vorgaben: Block entfällt
        analyze.settings_set(self.base, {})
        self.assertNotIn('analysis', self.config())
        self.assertIn('Vorgabe (de-DE)', self.view('--text'))

    def test_invalid_values(self):
        for bad in ({'provider': 'mistral'}, {'parallel': 0}, {'parallel': 2.5}, {'price_input_per_mtok': -1},
                    {'languagetool': {'language': 'Deutsch'}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                analyze.settings_set(self.base, bad)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/analyze.py'), str(self.base), 'settings-set', '{"parallel": 20}'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn('analysis', self.config())

    def test_settings_row(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'project-settings',
                            '--repo', 'o/r', '--text'], capture_output=True, text=True)
        self.assertIn('Formular `Analyse-Einstellungen`', r.stdout)


if __name__ == '__main__':
    unittest.main()
