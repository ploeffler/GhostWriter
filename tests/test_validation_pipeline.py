"""Regressionstests für die Validierung vor dem Aufbau der Buchübersicht."""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/adhs'


class MissingSectionFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = __import__('tempfile').TemporaryDirectory()
        self.project = Path(self.tmp.name)
        shutil.copytree(FIXTURE, self.project, dirs_exist_ok=True)
        self.config_path = self.project / 'ghostwriter.yml'
        self.config = yaml.safe_load(self.config_path.read_text(encoding='utf-8'))
        self.missing = self.project / 'chapters' / '01-einleitung' / 'sections' / 'nicht-vorhanden.md'
        self.config['structure']['chapters'][0]['sections'][0]['path'] = str(
            self.missing.relative_to(self.project)).replace('\\\\', '/')
        self.config_path.write_text(yaml.safe_dump(self.config, allow_unicode=True, sort_keys=False),
                                    encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_validator_reports_missing_section_file(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import validate_project
        errors = validate_project.check_project(self.project)
        self.assertTrue(any(str(self.missing) in error and 'fehlt' in error for error in errors), errors)

    def test_index_builder_reports_missing_file_without_traceback(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/build_index.py'), str(self.project)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('benötigte Projektdatei fehlt', result.stdout)
        self.assertIn(str(self.missing), result.stdout)
        self.assertNotIn('Traceback', result.stderr)

    def test_update_pipeline_validates_before_building_index(self):
        source = (ROOT / 'scripts/update_from_upstream.py').read_text(encoding='utf-8')
        migration = source.index("['scripts/migrate_project.py', '.']")
        validation = source.index("['scripts/validate_project.py', '.']")
        index = source.index("['scripts/build_index.py', '.']")
        self.assertLess(migration, validation)
        self.assertLess(validation, index)


if __name__ == '__main__':
    unittest.main()
