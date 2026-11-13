"""Lesefassung zur Kapitel- und Abschnittsansicht (#289): scripts/assemble.py reading."""
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


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / 'adhs'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.chapter = cfg['structure']['chapters'][0]
        self.sections = self.chapter['sections']

    def set_manuscript(self, idx, text, status='writing'):
        path = self.base / self.sections[idx]['path']
        body = path.read_text(encoding='utf-8')
        body = re.sub(r'(?m)^status: \w+', f'status: {status}', body, count=1)
        path.write_text(body.split('\n## Manuskript\n')[0] + f'\n## Manuskript\n\n{text}\n', encoding='utf-8')

    def reading(self, key):
        _, config = load(self.base)
        return assemble.reading_markdown(self.base, config, key, '2026-11-13')

    def test_chapter_has_numbers_status_and_no_pandoc_attributes(self):
        self.set_manuscript(1, 'Text mit [Etikett]{.glossar} und [QUELLE PRÜFEN: Studie].\n\n# Zwischentitel\n\nWeiter.')
        self.set_manuscript(2, 'Noch nicht begonnen.', status='planned')
        name, md = self.reading('1')
        self.assertEqual(name, 'Kapitel-01-endlich-eine-erklaerung.md')
        self.assertTrue(md.startswith('# 1 Endlich eine Erklärung\n'))
        self.assertIn(f'## 1.2 {self.sections[1]["title"]}', md)
        self.assertIn('0 von 9 Abschnitten freigegeben · Stand 2026-11-13', md)
        self.assertIn('> *Stand: Entwurf, nicht freigegeben*', md)
        self.assertIn('**[QUELLE PRÜFEN: Studie]**', md)
        self.assertIn('Text mit Etikett und', md)
        self.assertIn('### Zwischentitel', md)
        self.assertIn('**Geplant**', md)
        self.assertNotRegex(md, r'\{\.[a-z]')
        self.assertNotIn(':::', md)

    def test_section_file(self):
        self.set_manuscript(0, 'Erster Satz.[^1]\n\n[^1]: Fußnote.', status='revision')
        name, md = self.reading('1.1')
        self.assertTrue(name.startswith('Abschnitt-1.1-'))
        lines = md.splitlines()
        self.assertEqual(lines[0], f'# 1.1 {self.sections[0]["title"]}')
        self.assertIn('Kapitel 1 „Endlich eine Erklärung“ · Überarbeitung, nicht freigegeben · Stand 2026-11-13', lines[2])
        self.assertIn('## Manuskript', md)
        self.assertIn('[^1]: Fußnote.', md)

    def test_empty_section(self):
        self.set_manuscript(3, 'Noch nicht begonnen.', status='planned')
        self.assertIn('*(noch kein Text)*', self.reading('1.4')[1])

    def test_unknown_section(self):
        with self.assertRaises(SystemExit):
            self.reading('1.99')

    def test_cli_writes_into_folder(self):
        out = Path(self.temp.name) / 'out'
        out.mkdir()
        subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base), 'reading', '1.2', '-o', str(out)],
                       check=True, capture_output=True)
        files = list(out.glob('Abschnitt-1.2-*.md'))
        self.assertEqual(len(files), 1)

    def test_section_view_without_manuscript(self):
        self.set_manuscript(0, 'Einzigartiger Satz im Manuskript.')
        args = [sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'section', '1.1', '--text', '--repo', 'o/r']
        full = subprocess.run(args, check=True, capture_output=True, text=True).stdout
        short = subprocess.run(args + ['--ohne-manuskript'], check=True, capture_output=True, text=True).stdout
        self.assertIn('Einzigartiger Satz', full)
        self.assertNotIn('Einzigartiger Satz', short)
        self.assertIn('Lesefassung', short)


if __name__ == '__main__':
    unittest.main()
