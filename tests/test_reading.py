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
        self.assertIn('0 von 9 Abschnitten abgeschlossen · Stand 2026-11-13', md)
        self.assertIn('> *Stand: Entwurf, nicht abgeschlossen*', md)
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
        self.assertIn('Kapitel 1 „Endlich eine Erklärung“ · Überarbeitung, nicht abgeschlossen · Stand 2026-11-13', lines[2])
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

    def test_unsaved_proposal_refreshes_same_file_without_changing_project(self):
        original = {p.relative_to(self.base): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        draft = Path(self.temp.name) / 'vorschlag.md'
        out = Path(self.temp.name) / 'lesefassung'
        out.mkdir()
        command = [sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base),
                   'reading', '1.1', '--draft-file', str(draft), '-o', str(out)]
        for text in ('Vorschlag eins.[^1]\n\n[^1]: Fiktive Notiz.',
                     'Vorschlag zwei. [QUELLE PRÜFEN: fiktive Notiz]'):
            draft.write_text(text, encoding='utf-8')
            subprocess.run(command, check=True, capture_output=True)
            files = list(out.glob('*.md'))
            self.assertEqual(len(files), 1)
            rendered = files[0].read_text(encoding='utf-8')
            self.assertIn('nicht im Manuskript gespeichert', rendered)
            self.assertIn('## Schreibvorschlag', rendered)
            self.assertIn(assemble.readable(assemble.mark_markers(text)), rendered)
        self.assertNotIn('Vorschlag eins', rendered)
        self.assertEqual(original, {p.relative_to(self.base): p.read_bytes()
                                   for p in self.base.rglob('*') if p.is_file()})

    def test_proposal_is_restricted_to_a_single_reading_section(self):
        draft = Path(self.temp.name) / 'vorschlag.md'
        draft.write_text('Fiktiver Vorschlag.', encoding='utf-8')
        for kind, key in (('reading', '1'), ('book', '1'), ('manuscript', '1.1')):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base),
                                     kind, key, '--draft-file', str(draft)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')

    def test_preview_cannot_overwrite_a_file_inside_the_book(self):
        source = self.base / self.sections[0]['path']
        original = source.read_bytes()
        draft = Path(self.temp.name) / 'vorschlag.md'
        draft.write_text('Nur zur Durchsicht.', encoding='utf-8')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base),
                                 'reading', '1.1', '--draft-file', str(draft), '-o', str(source)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_bytes(), original)


class ManuscriptWorkflowTests(unittest.TestCase):
    """#289 Teil 2: „Manuskript ausgeben“ mit format md."""
    def setUp(self):
        self.wf = yaml.safe_load((ROOT / '.github/workflows/manuscript.yml').read_text(encoding='utf-8'))
        self.steps = self.wf['jobs']['manuscript']['steps']

    def test_format_input(self):
        on = self.wf.get('on', self.wf.get(True))
        fmt = on['workflow_dispatch']['inputs']['format']
        self.assertEqual(fmt['options'], ['pdf', 'md'])
        self.assertEqual(fmt['default'], 'pdf')

    def test_md_skips_tex_and_pdf_skips_reading(self):
        by_name = {s.get('name') or s.get('with', {}).get('name'): s for s in self.steps}
        self.assertEqual(by_name['Abhängigkeiten']['if'], "inputs.format != 'md'")
        self.assertEqual(by_name['Manuskript bauen']['if'], "inputs.format != 'md'")
        reading = by_name['Lesefassung (md)']
        self.assertEqual(reading['if'], "inputs.format == 'md'")
        self.assertIn('assemble.py . reading', reading['run'])
        self.assertIn('lesefassung/$book', reading['run'])
        self.assertIn('nie das ganze Buch', reading['run'])

    def test_key_check_rejects_book_and_garbage(self):
        run = next(s['run'] for s in self.steps if s.get('name') == 'Lesefassung (md)')
        check = run.split('mkdir -p lesefassung')[0].replace('pip install -q pyyaml', '')
        for key, ok in (('5', True), ('5.1', True), ('', False), ('5;rm', False), ('5.', False), ('.1', False), ('5.1.2', False)):
            r = subprocess.run(['bash', '-c', check], env={'KEY': key, 'PATH': '/usr/bin:/bin'}, capture_output=True)
            self.assertEqual(r.returncode == 0, ok, key)


if __name__ == '__main__':
    unittest.main()
