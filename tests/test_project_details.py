"""Buchangaben in „Projektdaten bearbeiten“ (#299): Untertitel, Sprache, Buchtyp, Zielgruppe, Übersetzungen."""
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


class ProjectDetailsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        path = self.base / 'ghostwriter.yml'
        cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
        cfg['project'].update({'subtitle': 'Ein Untertitel', 'book_type': 'Ratgeber', 'target_audience': 'Erwachsene',
                               'translations_planned': ['en', 'fr']})
        path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')

    def run_view(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'project-edit',
                            '--repo', 'o/r', *args], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_widget_data(self):
        out = self.run_view()
        data = json.loads(re.search(r'GW\.render\("projektdaten-bearbeiten",(\{.*\})\)', out).group(1))
        self.assertEqual(data['PROJECT_SUBTITLE'], 'Ein Untertitel')
        self.assertEqual(data['PROJECT_LANGUAGE'], 'de')
        self.assertEqual(data['PROJECT_BOOK_TYPE'], 'Ratgeber')
        self.assertEqual(data['PROJECT_TARGET_AUDIENCE'], 'Erwachsene')
        self.assertEqual(data['PROJECT_TRANSLATIONS'], 'en, fr')

    def test_text_views(self):
        de = self.run_view('--text')
        for row in ('| Untertitel | Ein Untertitel |', '| Buchtyp | Ratgeber |', '| Geplante Übersetzungen | en, fr |'):
            self.assertIn(row, de)
        en = self.run_view('--text', '--language', 'en')
        self.assertIn('| Planned translations | en, fr |', en)
        self.assertIn('| Target audience | Erwachsene |', en)

    def test_ui_pin_has_fields(self):
        pin = yaml.safe_load((ROOT / 'templates/ui/ghostwriter-ui.yml').read_text(encoding='utf-8'))
        self.assertIn(pin['commit'], pin['script'])
        keys = json.loads((ROOT / 'templates/ui/i18n/de.json').read_text(encoding='utf-8'))
        self.assertIn('ui.planned_translations', keys)


if __name__ == '__main__':
    unittest.main()
