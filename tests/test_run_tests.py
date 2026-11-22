"""#485: Testmodule parallel ausführen und Laufzeiten melden."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import run_tests


class RunTestsTest(unittest.TestCase):
    def test_typesetting_modules_first(self):
        ordered = run_tests.order(['test_select_tests', 'test_cover', 'test_workflow_pipefail'])
        self.assertEqual(ordered[0], 'test_cover')

    def test_runs_modules_and_reports(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/run_tests.py'), 'test_workflow_pipefail',
                            'test_select_tests', '--jobs', '2'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('in 2 Modulen', r.stdout)
        self.assertIn('Langsamste Module:', r.stdout)
        self.assertTrue(r.stdout.rstrip().endswith('OK'))

    def test_unknown_module_fails(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/run_tests.py'), 'test_gibt_es_nicht'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('Unbekannte Testmodule', r.stderr)

    def test_count_reads_unittest_summary(self):
        self.assertEqual(run_tests.count('...\nRan 12 tests in 0.3s\n\nOK\n'), 12)


if __name__ == '__main__':
    unittest.main()
