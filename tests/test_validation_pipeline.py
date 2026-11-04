"""Regressionstests für die Validierung vor dem Aufbau der Buchübersicht."""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/adhs'


class HistoricalApprovalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = __import__('tempfile').TemporaryDirectory()
        self.project = Path(self.tmp.name)
        shutil.copytree(FIXTURE, self.project, dirs_exist_ok=True)
        sys.path.insert(0, str(ROOT / 'scripts'))
        import validate_project
        self.validate = validate_project.check_project
        self.entry = {'kind': 'writing', 'id': 'sec-alte-id', 'action': 'granted',
                      'at': '2026-11-04T11:58:24Z', 'by': 'chat', 'commit': '1234567'}
        self.ref = {'entry': 1, 'kind': 'writing', 'id': 'sec-alte-id', 'reason': 'Abschnitt aufgeteilt'}

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, refs, entries=None):
        data = {'entries': entries if entries is not None else [self.entry], 'historical_references': refs}
        (self.project / 'approvals.yml').write_text(yaml.safe_dump(data), encoding='utf-8')
        return self.validate(self.project)

    def test_only_exact_documented_entry_is_exempt(self):
        self.assertFalse(any('sec-alte-id unbekannt' in e for e in self.check([self.ref])))
        errors = self.check([self.ref], [self.entry, self.entry])
        self.assertTrue(any('Eintrag 2:' in e and 'unbekannt' in e for e in errors), errors)
        self.assertTrue(any('unbekannt' in e for e in self.check([])))

    def test_bad_references_are_rejected(self):
        for ref in ({**self.ref, 'id': 'sec-andere-id'}, {**self.ref, 'entry': 2},
                    {**self.ref, 'reason': ' '}):
            with self.subTest(ref=ref):
                self.assertTrue(self.check([ref]))
        self.assertTrue(any('doppelt' in e for e in self.check([self.ref, self.ref])))


class MissingSectionFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = __import__('tempfile').TemporaryDirectory()
        self.project = Path(self.tmp.name)
        shutil.copytree(FIXTURE, self.project, dirs_exist_ok=True)
        self.config_path = self.project / 'ghostwriter.yml'
        self.config = yaml.safe_load(self.config_path.read_text(encoding='utf-8'))
        chapter_path = Path(self.config['structure']['chapters'][0]['path'])
        self.missing = self.project / chapter_path / 'sections' / 'nicht-vorhanden.md'
        self.config['structure']['chapters'][0]['sections'][0]['path'] = self.missing.relative_to(self.project).as_posix()
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
