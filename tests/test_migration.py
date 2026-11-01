"""Datenmigration (#59): Beispielbücher der Datenversion 0 werden migriert, ein zweiter Lauf
ändert nichts, ein neueres Buch bleibt unverändert, der Fingerabdruck passt zum Schema."""
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import migrate_project  # noqa: E402

FIXTURES = ['adhs', 'leeres-projekt']


def tree_hash(base):
    h = hashlib.sha256()
    for p in sorted(base.rglob('*')):
        if p.is_file():
            h.update(str(p.relative_to(base)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/migrate_project.py'), *map(str, args)],
                          capture_output=True, text=True)


class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def copy(self, name):
        dst = Path(self.tmp.name) / name
        shutil.copytree(ROOT / 'tests/fixtures' / name, dst)
        return dst

    def test_fixtures_migrate_validate_and_are_idempotent(self):
        for name in FIXTURES:
            with self.subTest(name):
                base = self.copy(name)
                self.assertEqual(migrate_project.get_version(base), 0)
                r = run(base)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(migrate_project.get_version(base), migrate_project.DATA_VERSION)
                v = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_project.py'), str(base)],
                                   capture_output=True, text=True)
                self.assertEqual(v.returncode, 0, v.stdout + v.stderr)
                before = tree_hash(base)
                r2 = run(base)
                self.assertEqual(r2.returncode, 0)
                self.assertEqual(tree_hash(base), before, 'zweiter Lauf hat etwas geändert')
                self.assertEqual(run(base, '--check').returncode, 0)

    def test_content_untouched(self):
        base = self.copy('adhs')
        chapters = {p: p.read_bytes() for p in base.glob('chapters/**/*.md')}
        run(base)
        for p, data in chapters.items():
            self.assertEqual(p.read_bytes(), data, f'{p} wurde verändert')

    def test_newer_book_is_refused_and_unchanged(self):
        base = self.copy('adhs')
        text = (base / 'ghostwriter.yml').read_text(encoding='utf-8')
        (base / 'ghostwriter.yml').write_text(f'data_version: {migrate_project.DATA_VERSION + 5}\n' + text, encoding='utf-8')
        before = tree_hash(base)
        r = run(base)
        self.assertEqual(r.returncode, 2)
        self.assertIn('Kein Zurücksetzen', r.stdout)
        self.assertEqual(tree_hash(base), before)

    def test_check_reports_pending(self):
        base = self.copy('leeres-projekt')
        self.assertEqual(run(base, '--check').returncode, 1)

    def test_version_line_keeps_file_format(self):
        base = self.copy('adhs')
        before = (base / 'ghostwriter.yml').read_text(encoding='utf-8')
        run(base)
        after = (base / 'ghostwriter.yml').read_text(encoding='utf-8')
        self.assertTrue(after.splitlines()[0].startswith('data_version:') or 'data_version:' in after)
        self.assertEqual(yaml.safe_load(after)['project'], yaml.safe_load(before)['project'])
        # Kommentare der Datei bleiben erhalten
        self.assertEqual(sum(l.lstrip().startswith('#') for l in before.splitlines()),
                         sum(l.lstrip().startswith('#') for l in after.splitlines()))

    def test_schema_fingerprint_matches(self):
        self.assertIsNone(migrate_project.fingerprint_problem())


if __name__ == '__main__':
    unittest.main()
