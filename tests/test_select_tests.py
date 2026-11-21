"""#439: Tests für einen Pull Request nach den geänderten Dateien auswählen."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import select_tests


# Suchwörter zusammengesetzt, damit diese Datei sich nicht selbst als Doku- oder Satztest auswählt
DOCS = 'do' + 'cs'
TEX = 'pan' + 'doc'


class SelectTestsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / 'test_docs_a.py').write_text(f"ROOT / '{DOCS}' / 'X.md'\n", encoding='utf-8')
        (self.tmp / 'test_tool.py').write_text('import tool\n', encoding='utf-8')
        (self.tmp / 'test_pdf.py').write_text(f'import tool\nshutil.which("{TEX}")\n', encoding='utf-8')
        for i in range(5):
            (self.tmp / f'test_other{i}.py').write_text('pass\n', encoding='utf-8')
        self.files = sorted(self.tmp.glob('test_*.py'))

    def sel(self, changed, removed=()):
        return select_tests.select(changed, removed, self.files)

    def test_docs_only_runs_doc_tests_without_typesetting(self):
        self.assertEqual(self.sel([f'{DOCS}/NEU.md', 'README.md']), ('subset', ['test_docs_a'], False))

    def test_changed_test_runs_itself(self):
        self.assertEqual(self.sel(['tests/test_other1.py']), ('subset', ['test_other1'], False))

    def test_script_runs_its_users_and_typesetting_when_needed(self):
        self.assertEqual(self.sel(['scripts/tool.py']), ('subset', ['test_pdf', 'test_tool'], True))

    def test_doubt_means_full_suite(self):
        for changed in (['START.md'], ['workflow.yml'], ['schemas/x.schema.json'], ['templates/ui/a.md'],
                        ['.github/workflows/validate.yml'], ['scripts/unbekannt.py'], ['Makefile'], []):
            self.assertEqual(self.sel(changed)[0], 'full', changed)
        self.assertEqual(self.sel([f'{DOCS}/a.md'], removed=['scripts/tool.py'])[0], 'full')

    def test_large_selection_becomes_full(self):
        changed = [f'tests/test_other{i}.py' for i in range(5)]
        self.assertEqual(self.sel(changed)[0], 'full')

    def test_importers_are_transitive(self):
        d = Path(tempfile.mkdtemp())
        (d / 'a.py').write_text('x = 1\n', encoding='utf-8')
        (d / 'b.py').write_text('import os, a\n', encoding='utf-8')
        (d / 'c.py').write_text('from b import y\n', encoding='utf-8')
        (d / 'd.py').write_text('# nennt a nur im Kommentar\n', encoding='utf-8')
        self.assertEqual(select_tests.importers('a', sorted(d.glob('*.py'))), {'a', 'b', 'c'})

    def test_real_repository_docs_change_is_small(self):
        mode, tests, satz = select_tests.select([f'{DOCS}/MARKTVERGLEICH-v1.0.md'])
        self.assertEqual(mode, 'subset')
        self.assertIn('test_check_docs', tests)
        self.assertFalse(satz)

    def test_cli_writes_github_output(self):
        files = self.tmp / 'changed.txt'
        files.write_text(f'{DOCS}/a.md\n', encoding='utf-8')
        out = self.tmp / 'out.txt'
        subprocess.run([sys.executable, str(ROOT / 'scripts/select_tests.py'), '--files', str(files),
                        '--github-output', str(out)], check=True, capture_output=True)
        text = out.read_text(encoding='utf-8')
        self.assertIn('mode=subset', text)
        self.assertIn('satz=0', text)


if __name__ == '__main__':
    unittest.main()
