"""Manuskript-Import ohne KI (#124): umwandeln, Gliederung erkennen, ändern, anlegen, Aufbewahrung."""
import datetime
import json
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
import import_book  # noqa: E402
import validate_project  # noqa: E402

SOURCE = """---
title: Strolchi und der Wald
author: Karl Löffler
---

Für Mia.

# Prolog

Es war einmal ein kleiner Hund, der hieß Strolchi.

# Kapitel 1: Der Zaun

Strolchi stand am Zaun. Opi rief ihn.

\\* \\* \\*

Am Abend saßen beide auf der Bank. Morgen gehen wir in den Wald, sagte Opi.

# Kapitel 2: Die Höhle

## Der Eingang

Die Höhle war dunkel.

## Drinnen

Strolchi bellte[^1].

[^1]: Er bellte laut.

# Danksagung

Danke an alle Hunde.
"""


@unittest.skipUnless(shutil.which('pandoc'), 'pandoc fehlt')
class ImportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.book = self.tmp / 'buch'
        self.book.mkdir()
        shutil.copyfile(ROOT / 'templates/ghostwriter-starter.yml', self.book / 'ghostwriter.yml')
        (self.tmp / 'src.md').write_text(SOURCE, encoding='utf-8')
        subprocess.run(['pandoc', str(self.tmp / 'src.md'), '-o', str(self.tmp / 'Strolchi.docx')], check=True)

    def test_docx(self):
        p = import_book.convert(self.book, self.tmp / 'Strolchi.docx', '30', datetime.date(2026, 11, 4))
        self.assertTrue((self.book / 'import/original/Strolchi.docx').is_file())
        self.assertEqual((p['title'], p['author']), ('Strolchi und der Wald', 'Karl Löffler'))
        self.assertEqual([x['kind'] for x in p['parts']], ['dedication', 'prologue', 'acknowledgments'])
        self.assertEqual([c['title'] for c in p['chapters']], ['Der Zaun', 'Die Höhle'])
        self.assertEqual([s['title'] for s in p['chapters'][0]['sections']], ['Der Zaun (1)', 'Der Zaun (2)'])   # Szenen
        self.assertEqual([s['title'] for s in p['chapters'][1]['sections']], ['Der Eingang', 'Drinnen'])
        self.assertTrue(p['stats']['lossless'])
        self.assertTrue(any('Fußnote' in w for w in p['warnings']))
        self.assertFalse((self.book / 'chapters').exists())          # am Buch ändert sich noch nichts
        # ändern
        p = import_book.edit(self.book, [{'op': 'rename_chapter', 'chapter': 1, 'title': 'Am Zaun'},
                                         {'op': 'merge_sections', 'chapter': 1, 'section': 1}])
        self.assertEqual(p['chapters'][0]['sections'][0]['title'], 'Der Zaun')
        self.assertTrue(p['stats']['lossless'])
        # Vorschau
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.book), 'import-preview'],
                             capture_output=True, text=True, check=True).stdout
        data = json.loads(re.search(r'GW\.render\("import-vorschau",(.*)\)</script>', out).group(1))
        self.assertEqual([r['R_LABEL'] for r in data['ROWS']], ['Kapitel 1', '1.1', 'Kapitel 2', '2.1', '2.2'])
        self.assertEqual(data['KEEP_TEXT'], '30 Tage')
        # anlegen, ohne Schreibfreigabe
        info = import_book.apply(self.book)
        self.assertEqual((info['chapters'], info['sections'], info['writing_approval']), (2, 3, False))
        self.assertEqual(validate_project.check_project(self.book), [])
        cfg = yaml.safe_load((self.book / 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.assertEqual((cfg['project']['working_title'], cfg['project']['author']), ('Strolchi und der Wald', 'Karl Löffler'))
        self.assertEqual(cfg['workflow']['current_phase'], 'writing')
        self.assertEqual([i['kind'] for i in cfg['structure']['front_matter']], ['dedication', 'prologue'])
        sec = (self.book / cfg['structure']['chapters'][1]['sections'][1]['path']).read_text(encoding='utf-8')
        self.assertIn('status: revision', sec)
        self.assertIn('  writing: false', sec)
        self.assertIn('Strolchi bellte[^1].', sec)
        self.assertFalse((self.book / 'approvals.yml').exists())
        with self.assertRaisesRegex(SystemExit, 'schon Kapitel'):
            import_book.apply(self.book)
        # Aufbewahrung: 30 Tage
        self.assertFalse(import_book.status(self.book, datetime.date(2026, 11, 20))['soon'])
        self.assertTrue(import_book.status(self.book, datetime.date(2026, 11, 30))['soon'])
        self.assertFalse(import_book.expire(self.book, datetime.date(2026, 12, 3)))
        self.assertTrue(import_book.expire(self.book, datetime.date(2026, 12, 4)))
        self.assertFalse((self.book / 'import/original').exists())
        self.assertTrue(import_book.status(self.book)['removed'])

    def test_writing_approval(self):
        import_book.convert(self.book, self.tmp / 'Strolchi.docx')
        import_book.apply(self.book, writing_approval=True, by='ploeffler', commit='abc1234')
        self.assertEqual(validate_project.check_project(self.book), [])
        entries = yaml.safe_load((self.book / 'approvals.yml').read_text(encoding='utf-8'))['entries']
        self.assertEqual(len(entries), 4 + 3)                           # 4 Abschnitte, 3 Teile
        self.assertEqual({(e['kind'], e['action'], e['by']) for e in entries}, {('writing', 'granted', 'ploeffler')})
        self.assertEqual(import_book.status(self.book)['keep'], 'first_edition')

    def test_plain_text_and_pdf(self):
        txt = self.tmp / 'roh.txt'
        txt.write_text('Kapitel 1\n\nEs begann.\n\nKapitel 2\n\nEs endete.\n', encoding='utf-8')
        p = import_book.convert(self.book, txt)
        self.assertEqual(len(p['chapters']), 2)
        none = self.tmp / 'ohne.txt'
        none.write_text('Nur ein langer Text ohne jede Gliederung.\n', encoding='utf-8')
        p = import_book.convert(self.book, none)
        self.assertTrue(any('Keine Gliederung' in w for w in p['warnings']))
        if shutil.which('pdftotext') and shutil.which('xelatex'):
            pdf = self.tmp / 'Strolchi.pdf'
            subprocess.run(['pandoc', str(self.tmp / 'src.md'), '-o', str(pdf), '--pdf-engine=xelatex'], check=True,
                           capture_output=True)
            p = import_book.convert(self.book, pdf)
            self.assertEqual(p['format'], 'pdf')
            self.assertTrue(p['warnings'][0].startswith('PDF:'))


if __name__ == '__main__':
    unittest.main()
