"""Schreibfreie Ermittlung von Arbeitsmaterial und Divergenz."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from workflow_support import chapter_material, compare_book_work, historical_candidates, assess_write


class MaterialTest(unittest.TestCase):
    def test_related_files_and_historical_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'chapters/a').mkdir(parents=True)
            (root / 'planning').mkdir()
            (root / 'chapters/a/README.md').write_text('Kapitel', encoding='utf-8')
            (root / 'planning/notes.md').write_text('Hier steht Kapitel Eins.', encoding='utf-8')
            (root / 'planning/other.md').write_text('Andere Dinge', encoding='utf-8')
            ch = {'id': 'ch-1', 'title': 'Kapitel Eins', 'path': 'chapters/a',
                  'sections': [{'id': 'sec-1'}]}
            files = chapter_material(root, ch)
            self.assertEqual({x['path'] for x in files}, {'chapters/a/README.md', 'planning/notes.md'})
            approvals = {'entries': [{'kind': 'writing', 'id': 'sec-old', 'commit': 'abc1234'},
                                     {'kind': 'writing', 'id': 'sec-1'},
                                     {'kind': 'writing', 'id': 'mat-prolog'}]}
            candidates = historical_candidates({'structure': {'chapters': [ch]}}, approvals)
            self.assertEqual([x['entry'] for x in candidates], [1])
            approvals['historical_references'] = [{'entry': 1}]
            self.assertEqual(historical_candidates({'structure': {'chapters': [ch]}}, approvals), [])


class CompareTest(unittest.TestCase):
    def test_three_way_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            def git(*args):
                return subprocess.run(['git', '-C', tmp, *args], check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            for name in ('same', 'both', 'work'):
                (base / name).write_text('alt', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'Basis')
            common = git('rev-parse', 'HEAD')
            for name in ('same', 'both'):
                (base / name).write_text('Buch', encoding='utf-8')
            git('commit', '-qam', 'Buch')
            book = git('rev-parse', 'HEAD')
            git('checkout', '-q', '--detach', common)
            (base / 'same').write_text('Buch', encoding='utf-8')
            (base / 'both').write_text('Arbeit', encoding='utf-8')
            (base / 'work').unlink()
            git('add', '-A')
            git('commit', '-qm', 'Arbeit')
            work = git('rev-parse', 'HEAD')
            rows = {x['path']: x for x in compare_book_work(base, book, work)['files']}
            self.assertEqual(rows['same']['state'], 'bereits_identisch')
            self.assertEqual(rows['both']['state'], 'beide_geaendert')
            self.assertEqual(rows['work']['state'], 'nur_arbeitsfassung')
            self.assertTrue(rows['work']['work_deleted'])
            with self.assertRaises(ValueError):
                compare_book_work(base, '--help', work)


class StaleWriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.root / 'text.md').write_text('Ausgangstext')
        (self.root / 'other.md').write_text('Andere Datei')
        (self.root / 'ghostwriter.yml').write_text('Profil')
        self.git('add', '.')
        self.git('commit', '-qm', 'Basis')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def change(self, path, value='neu'):
        (self.root / path).write_text(value)
        self.git('add', '.')
        self.git('commit', '-qm', 'Geändert')
        return self.git('rev-parse', 'HEAD')

    def test_unchanged_and_other_file_changes_are_safe_to_prepare(self):
        same = assess_write(self.root, self.base, self.base, ['text.md'])
        self.assertEqual(same['state'], 'unchanged')
        current = self.change('other.md')
        before = self.git('status', '--porcelain')
        result = assess_write(self.root, self.base, current, ['text.md'])
        self.assertTrue(result['safe_to_prepare'])
        self.assertEqual(result['state'], 'unrelated_changes')
        self.assertEqual(result['current_head'], current)
        self.assertEqual(before, self.git('status', '--porcelain'))

    def test_changed_target_and_deleted_target_require_refresh(self):
        current = self.change('text.md')
        self.assertFalse(assess_write(self.root, self.base, current, ['text.md'])['safe_to_prepare'])
        (self.root / 'text.md').unlink()
        self.git('commit', '-qam', 'Entfernt')
        result = assess_write(self.root, current, 'HEAD', ['text.md'])
        self.assertEqual(result['affected_files'], ['text.md'])

    def test_changed_context_requires_refresh_even_for_other_target(self):
        current = self.change('ghostwriter.yml')
        result = assess_write(self.root, self.base, current, ['text.md'])
        self.assertEqual(result['state'], 'refresh_required')
        self.assertEqual(result['context_changes'], ['ghostwriter.yml'])
        self.assertFalse(result['safe_to_prepare'])

    def test_diverged_branch_must_not_be_used_as_current_basis(self):
        first = self.change('other.md')
        self.git('checkout', '-q', '--detach', self.base)
        second = self.change('text.md')
        result = assess_write(self.root, first, second, ['new.md'])
        self.assertEqual(result['state'], 'diverged')
        self.assertFalse(result['safe_to_prepare'])

    def test_directory_targets_include_changed_children_and_renames(self):
        (self.root / 'folder').mkdir()
        new = self.change('folder/child.md')
        result = assess_write(self.root, self.base, new, ['folder'])
        self.assertEqual(result['affected_files'], ['folder/child.md'])
        self.git('mv', 'text.md', 'renamed.md')
        self.git('commit', '-qm', 'Verschoben')
        self.assertFalse(assess_write(self.root, new, 'HEAD', ['text.md'])['safe_to_prepare'])

    def test_invalid_paths_and_options_are_rejected(self):
        for paths in ([], ['../outside'], ['/tmp/file'], ['a//b'], ['a/./b']):
            with self.assertRaises(ValueError):
                assess_write(self.root, self.base, self.base, paths)
        with self.assertRaises(ValueError):
            assess_write(self.root, '--help', self.base, ['text.md'])


if __name__ == '__main__':
    unittest.main()
