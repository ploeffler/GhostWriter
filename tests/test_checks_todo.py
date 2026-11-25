"""Projektübersicht: „Handlungsbedarf“ statt Prüfhistorie als Erstes (#538)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import checks  # noqa: E402


def row(n, tags=(), notes=0):
    return {'CHAPTER_NUMBER': n, 'CHAPTER_CHECKS': [dict(zip(('CK_LABEL', 'CK_RESULT', 'CK_STATE'), t)) for t in tags],
            'CHAPTER_NOTES': notes}


class TodoTest(unittest.TestCase):
    def test_only_what_needs_action(self):
        rows = [row(1, [('Sprache', 'passed', 'current')]), row(2, [('Sprache', 'passed', 'changed')], 3),
                row(3, [('Struktur', 'failed', 'current')], 1), row(4)]
        lines = checks.todo(rows)
        self.assertEqual(lines[0], '**Handlungsbedarf:**')
        self.assertEqual(lines[1], '- Kapitel 2: Sprache: Text seit der Prüfung geändert, neu prüfen · 3 offene Hinweise')
        self.assertEqual(lines[2], '- Kapitel 3: Struktur nicht bestanden · 1 offener Hinweis')
        self.assertEqual(len(lines), 4)   # Kapitel 1 und 4: kein Bedarf; letzte Zeile leer
        self.assertIn('Chapter 2: Sprache: text changed since the check', ' '.join(checks.todo(rows, 'en')))

    def test_nothing_to_do_no_lines(self):
        self.assertEqual(checks.todo([row(1, [('Sprache', 'passed', 'current')])]), [])

    def test_capped(self):
        lines = checks.todo([row(i, notes=1) for i in range(1, 12)])
        self.assertEqual(len(lines), 1 + checks.TODO_MAX + 1 + 1)
        self.assertIn('… 3 weitere Kapitel', lines[-2])

    def test_book_wide_check_needs_recheck(self):
        book = [{'kind': 'language', 'label': {'de': 'Sprache', 'en': 'Language'}}]
        lines = checks.todo([row(1)], 'de', book)
        self.assertEqual(lines[:2], ['**Handlungsbedarf:**', '- Buch neu prüfen (Sprache)'])
        self.assertIn('Check the book again (Language)', ' '.join(checks.todo([], 'en', book)))
        self.assertEqual(checks.todo([row(1)], 'de', []), [])

    def test_book_stale_follows_the_text(self):
        import yaml
        from render_view import load, section_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / 'b'
            shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
            _, config = load(base)
            checks.record(base, config, 'language', ['book'], 'passed', date='2026-11-20')
            checks.record(base, config, 'proofreading', ['book'], 'passed', date='2026-11-20')
            self.assertEqual(checks.Index(base, config).book_stale(), [])
            path = base / config['structure']['chapters'][0]['sections'][0]['path']
            path.write_text(path.read_text(encoding='utf-8') + '\nNeuer Satz nach der Prüfung.\n', encoding='utf-8')
            stale = checks.Index(base, config).book_stale()
            self.assertEqual(sorted(x['kind'] for x in stale), ['language', 'proofreading'])
            out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(base), 'project', '--text',
                                  '--repo', 'o/r'], capture_output=True, text=True).stdout
            self.assertIn('- Buch neu prüfen (Sprache)', out)
            self.assertNotIn('Letzte Prüfungen', out)
            en = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(base), 'project', '--text',
                                 '--repo', 'o/r', '--language', 'en'], capture_output=True, text=True).stdout
            self.assertIn('Check the book again (Language)', en)
            widget = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(base), 'project',
                                     '--repo', 'o/r'], capture_output=True, text=True).stdout
            self.assertNotIn('CHECKS_BOOK_STALE', widget)   # nicht ins Widget geschickt

    def test_overview_text(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / 'b'
            shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
            (base / 'editorial').mkdir(exist_ok=True)
            import yaml
            sys.path.insert(0, str(ROOT / 'scripts'))
            from render_view import load
            _, config = load(base)
            ch = config['structure']['chapters'][0]
            entries = [{'id': 'pr-001', 'kind': 'language', 'scope': [ch['id']], 'date': '2026-11-20', 'result': 'failed',
                        'commit': 'abcdef1', 'digests': {s['id']: 'sha256:0000000000000000' for s in ch['sections']}}]
            (base / 'editorial/checks.yml').write_text(yaml.safe_dump({'checks': entries}), encoding='utf-8')
            for lang, head in (('de', 'Handlungsbedarf'), ('en', 'Needs attention')):
                out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(base), 'project', '--text',
                                      '--repo', 'o/r', '--language', lang], capture_output=True, text=True)
                self.assertEqual(out.returncode, 0, out.stderr)
                self.assertIn(head, out.stdout)


if __name__ == '__main__':
    unittest.main()
