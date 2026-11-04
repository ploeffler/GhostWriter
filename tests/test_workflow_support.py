"""Schreibfreie Ermittlung von Arbeitsmaterial und Divergenz."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from workflow_support import chapter_material, compare_book_work, historical_candidates


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


if __name__ == '__main__':
    unittest.main()
