"""Tests für scripts/assemble.py (#14) mit dem ADHS-Projekt aus tests/fixtures/adhs."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assemble  # noqa: E402
from render_view import load  # noqa: E402


class AssembleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / 'adhs'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def approve(self, chapter_no, sections=None, strip_markers=True):
        """Kapitel und Abschnitte freigeben (Status approved), optional Marker entfernen."""
        cfg_path = self.base / 'ghostwriter.yml'
        cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
        ch = cfg['structure']['chapters'][chapter_no - 1]
        ch['status'] = 'approved'
        cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')
        for i, s in enumerate(ch['sections'], start=1):
            if sections is not None and i not in sections:
                continue
            path = self.base / s['path']
            text = path.read_text(encoding='utf-8')
            text = re.sub(r'(?m)^status: \w+', 'status: approved', text, count=1)
            if strip_markers:
                text = re.sub(r'\*?\[(PLATZHALTER-ANEKDOTE|QUELLE PRÜFEN|MEDIZIN PRÜFEN|RECHT PRÜFEN)[^\]]*\]\*?', '', text)
            path.write_text(text, encoding='utf-8')
        readme = self.base / ch['path'] / 'README.md'
        if strip_markers:
            readme.write_text(re.sub(r'\[(QUELLE PRÜFEN|MEDIZIN PRÜFEN)[^\]]*\]', '', readme.read_text(encoding='utf-8')),
                              encoding='utf-8')
        return ch

    def test_nothing_approved_blocks_edition(self):
        _, config = load(self.base)
        found = assemble.problems(assemble.book_parts(self.base, config), config)
        self.assertTrue(found and found[0].startswith('Kein Kapitel ist freigegeben'))

    def test_chapter_contains_only_approved_sections_in_order(self):
        ch = self.approve(1, sections={1, 3})
        _, config = load(self.base)
        md, skipped, markers = assemble.chapter_markdown(self.base, config['structure']['chapters'][0], 1)
        titles = re.findall(r'(?m)^## (.+)$', md)
        self.assertEqual(titles[:2], [ch['sections'][0]['title'], ch['sections'][2]['title']])
        self.assertEqual(len(skipped), len(ch['sections']) - 2)
        self.assertEqual(markers, [])
        self.assertNotIn('## Manuskript', md)
        self.assertNotIn('Vorspann', md)

    def test_markers_block_and_clean_chapter_passes(self):
        self.approve(1, strip_markers=False)
        _, config = load(self.base)
        found = assemble.problems(assemble.book_parts(self.base, config), config)
        self.assertTrue(any(f.startswith('Offener Marker') for f in found))
        self.approve(1, strip_markers=True)
        _, config = load(self.base)
        self.assertEqual(assemble.problems(assemble.book_parts(self.base, config), config), [])

    def test_book_has_metadata_and_cli_check(self):
        self.approve(1)
        out = Path(self.temp.name) / 'book.md'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base), 'book', '--edition', '3',
                            '-o', str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        head = yaml.safe_load(out.read_text(encoding='utf-8').split('---')[1])
        self.assertEqual(head['edition'], 3)
        self.assertEqual(head['typesetting']['page_size'], 'a5')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base), 'check'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == '__main__':
    unittest.main()
