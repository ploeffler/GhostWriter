"""Abschnitte als „veraltet“ kennzeichnen, ohne die Freigabe zu ändern (#510)."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import matter  # noqa: E402
import stale  # noqa: E402
import validate_project  # noqa: E402
from render_view import load, section_file  # noqa: E402


class StaleTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.section = self.config['structure']['chapters'][0]['sections'][0]

    def view(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args, '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_mark_keeps_everything_else(self):
        head0, _, _, ms0 = section_file(self.base, self.section)
        stale.mark(self.base, self.config, '1.1', 'Zeitzeugin widerspricht', 'editorial/x.md', '2026-11-24')
        head, _, _, ms = section_file(self.base, self.section)
        self.assertEqual(head['stale'], {'since': '2026-11-24', 'reason': 'Zeitzeugin widerspricht', 'source': 'editorial/x.md'})
        self.assertEqual({k: v for k, v in head.items() if k != 'stale'}, head0)   # Status und approvals unverändert
        self.assertEqual(ms, ms0)                                                  # Fingerabdruck unverändert
        self.assertFalse(validate_project.check_project(self.base))
        stale.mark(self.base, self.config, '1.1', 'neuer Grund', date='2026-11-25')   # ersetzt, kein zweiter Block
        text = (self.base / self.section['path']).read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r'(?m)^stale:', text)), 1)
        self.assertEqual(section_file(self.base, self.section)[0]['stale']['reason'], 'neuer Grund')
        self.assertTrue(stale.clear(self.base, self.config, '1.1'))
        self.assertFalse(stale.clear(self.base, self.config, '1.1'))
        self.assertEqual(section_file(self.base, self.section)[0], head0)
        self.assertEqual((self.base / self.section['path']).read_text(encoding='utf-8').count('stale'), 0)

    def test_errors(self):
        with self.assertRaises(ValueError):
            stale.mark(self.base, self.config, '1.1', '  ')
        with self.assertRaises(ValueError):
            stale.mark(self.base, self.config, '99.99', 'x')

    def test_views_show_the_marker(self):
        stale.mark(self.base, self.config, '1.1', 'Zeitzeugin widerspricht', date='2026-11-24')
        self.assertIn('⚠ veraltet', self.view('chapter', '1', '--text'))
        self.assertIn('Als veraltet markiert seit 2026-11-24: Zeitzeugin widerspricht', self.view('section', '1.1', '--text'))
        self.assertIn('veraltet', self.view('chapter', '1'))   # Widget: Marke im Titel

    def test_chapter_approval_warns(self):
        stale.mark(self.base, self.config, '1.1', 'x', date='2026-11-24')
        out = self.view('approval-chapter', '1', '--text')
        self.assertIn('als veraltet markiert', out)
        self.assertIn('1.1', out)

    def add_matter(self):
        matter.add(self.base, 'foreword')
        _, self.config = load(self.base)
        return self.config['structure']['front_matter'][0] if 'front_matter' in self.config['structure'] \
            else next(i for _, i in __import__('render_view').matter_items(self.config))

    def test_matter_mark_clear_and_views(self):
        item = self.add_matter()
        stale.mark(self.base, self.config, item['id'], 'Vorwort überholt', date='2026-11-25')
        head = section_file(self.base, item)[0]
        self.assertEqual(head['stale']['reason'], 'Vorwort überholt')
        self.assertFalse(validate_project.check_project(self.base))
        self.assertIn(item['id'], stale.stale_sections(self.base, self.config)[0][0])
        self.assertIn('veraltet', self.view('matter', '--text') + self.view('matter'))
        self.assertIn('Seit 2026-11-25: Vorwort überholt', self.view('matter', item['id'], '--text'))
        self.assertTrue(stale.clear(self.base, self.config, item['id']))
        self.assertEqual(stale.stale_sections(self.base, self.config), [])

    def test_edition_warns_but_does_not_block(self):
        item = self.add_matter()
        stale.mark(self.base, self.config, '1.1', 'Zeitzeugin widerspricht', date='2026-11-25')
        stale.mark(self.base, self.config, item['id'], 'überholt', date='2026-11-25')
        lines = stale.warning_lines(self.base, self.config)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith('1.1 ') and 'Zeitzeugin widerspricht' in lines[0])
        out = self.view('edition-create', '--text')
        self.assertIn('Als veraltet markiert', out)
        self.assertIn('1.1', out)


if __name__ == '__main__':
    unittest.main()
