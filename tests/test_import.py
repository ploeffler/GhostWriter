"""Manuskript-Import ohne KI (#124): umwandeln, Gliederung erkennen, ändern, anlegen, Aufbewahrung."""
import datetime
import json
import os
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
        before = {p.relative_to(self.book): p.read_bytes()
                  for p in (self.book / 'import').rglob('*') if p.is_file()}
        self.assertFalse(import_book.expire(self.book, datetime.date(2026, 12, 4)))
        self.assertEqual(before, {p.relative_to(self.book): p.read_bytes()
                                 for p in (self.book / 'import').rglob('*') if p.is_file()})
        self.assertTrue(import_book.expire(self.book, datetime.date(2026, 12, 4), confirmed=True))
        self.assertFalse((self.book / 'import/original').exists())
        self.assertTrue(import_book.status(self.book)['removed'])

    def test_overview_keeps_original_after_old_deadline(self):
        """D21: Nach Ablauf einer früheren Frist kündigt die Übersicht keine Entfernung an."""
        import_book.convert(self.book, self.tmp / 'Strolchi.docx')
        import_book.apply(self.book)
        p = self.book / 'import' / 'import.yml'
        info = yaml.safe_load(p.read_text(encoding='utf-8'))
        info['keep_until'] = '2020-01-01'
        p.write_text(yaml.safe_dump(info, allow_unicode=True, sort_keys=False), encoding='utf-8')
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.book), 'project', '--text'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('bleibt erhalten, auch nach der früheren Frist (bis 01.01.2020)', out)
        self.assertIn('nur auf ausdrücklichen Auftrag', out)
        self.assertNotIn('entfernt (Aufbewahrung', out)
        self.assertTrue((self.book / 'import' / 'original').is_dir())
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.book), 'project', '--text',
                              '--language', 'en'], capture_output=True, text=True, check=True).stdout
        self.assertIn('is kept, even after the earlier retention period (until 2020-01-01)', out)
        self.assertNotIn('will be removed', out)

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

    def test_outline(self):
        paras = ['Am Morgen weckte Opi den kleinen Strolchi.', 'Sie frühstückten in der Küche.',
                 'Am Nachmittag gingen sie in den Wald.', 'Im Wald fanden sie eine Höhle.',
                 'Abends kamen beide müde nach Hause.', 'Strolchi schlief sofort ein.']
        src = self.tmp / 'ohne.txt'
        src.write_text('\n\n'.join(paras) + '\n', encoding='utf-8')
        p = import_book.convert(self.book, src)
        self.assertEqual(p['structure'], 'none')
        words0 = p['stats']['words_proposal']
        fake = self.tmp / 'fake.json'
        fake.write_text(json.dumps({'outline': {'answer': {'chapters': [
            {'title': 'Der Morgen', 'start': 1, 'quote': 'Am Morgen weckte Opi', 'reason': 'Beginn',
             'sections': [{'title': 'Wecken', 'start': 1, 'quote': 'Am Morgen'},
                          {'title': 'Frühstück', 'start': 2, 'quote': 'Sie frühstückten'}]},
            {'title': 'Erfunden', 'start': 3, 'quote': 'steht so nicht im Text', 'reason': 'falsch zitiert'},
            {'title': 'Im Wald', 'start': 4, 'quote': 'Im Wald fanden sie', 'reason': 'Ortswechsel',
             'sections': [{'title': 'Rückwärts', 'start': 2, 'quote': 'Sie frühstückten'}]},
            {'title': 'Zurück', 'start': 3, 'quote': 'Am Nachmittag', 'reason': 'Reihenfolge falsch'},
            {'title': 'Der Abend', 'start': 5, 'quote': 'Abends kamen beide', 'reason': 'Zeitsprung'}]}}}), encoding='utf-8')
        env = dict(os.environ, GHOSTWRITER_FAKE_LLM=str(fake))
        env.pop('ANTHROPIC_API_KEY', None)
        env.pop('OPENAI_API_KEY', None)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/import_book.py'), str(self.book), 'outline', '--plan'],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('6 Absätze', r.stdout)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/import_book.py'), str(self.book), 'outline'],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads((self.book / 'import/outline.json').read_text(encoding='utf-8'))
        self.assertEqual(o['status'], 'open')
        self.assertEqual([(c['title'], c['start']) for c in o['chapters']], [('Der Morgen', 1), ('Im Wald', 4), ('Der Abend', 5)])
        self.assertEqual([s['start'] for s in o['chapters'][1]['sections']], [4])        # Rückwärts verworfen
        self.assertEqual(o['dropped'], 3)
        self.assertEqual(sum(c['words'] for c in o['chapters']), words0)
        costs = yaml.safe_load((self.book / 'costs/project.yml').read_text(encoding='utf-8'))['entries']
        self.assertEqual([e['run_id'] for e in costs], ['outline-001'])
        # am Vorschlag ändert sich nichts, bis bestätigt
        self.assertEqual(len(import_book.load_proposal(self.book)['chapters']), 1)
        # Ansicht
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.book), 'import-outline'],
                             capture_output=True, text=True, check=True).stdout
        page = json.loads(re.search(r'GW\.render\("gliederung-vorschlag",(.*)\)</script>', out).group(1))
        self.assertEqual([r['O_TYPE'] for r in page['ROWS']], ['chapter', 'section', 'section', 'chapter', 'section', 'chapter', 'section'])
        prev = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.book), 'import-preview'],
                              capture_output=True, text=True, check=True).stdout
        self.assertIn('OUTLINE_TEXT', prev)
        txt = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.book), 'import-outline', '--text'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('Ortswechsel', txt)
        # übernehmen mit Änderung: Abend gehört noch zu Kapitel 2, neuer Titel
        with self.assertRaisesRegex(SystemExit, 'ungültig'):
            import_book.edit(self.book, [{'op': 'outline', 'chapters': [{'title': 'X', 'start': 2}]}])
        p = import_book.edit(self.book, [{'op': 'outline', 'chapters': [
            {'title': 'Morgens', 'start': 1, 'sections': [{'title': 'Wecken', 'start': 1}, {'title': 'Frühstück', 'start': 2}]},
            {'title': 'Im Wald', 'start': 4, 'sections': [{'title': 'Höhle', 'start': 4}, {'title': 'Heimweg', 'start': 5}]}]}])
        self.assertEqual([c['title'] for c in p['chapters']], ['Morgens', 'Im Wald'])
        self.assertEqual([s['title'] for s in p['chapters'][1]['sections']], ['Höhle', 'Heimweg'])
        self.assertIn('Am Nachmittag', p['chapters'][0]['sections'][1]['text'])          # Absatz 3 bleibt in 1.2
        self.assertTrue(p['stats']['lossless'])
        self.assertEqual(p['structure'], 'ai')
        self.assertFalse(any('Keine Gliederung' in w for w in p['warnings']))
        self.assertIsNone(import_book.open_outline(self.book))
        import_book.apply(self.book)
        self.assertEqual(validate_project.check_project(self.book), [])

    def test_outline_needs_no_structure(self):
        import_book.convert(self.book, self.tmp / 'Strolchi.docx')
        with self.assertRaisesRegex(SystemExit, 'schon eine Gliederung'):
            import_book.outline_plan(self.book)


class OriginalRetentionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.book = Path(self.tmp.name)
        original = self.book / 'import/original'
        original.mkdir(parents=True)
        (original / 'source.txt').write_bytes(b'Original unveraendert')
        (self.book / 'ghostwriter.yml').write_text('project: {current_edition: 1}\n')

    def set_info(self, **values):
        info = {'source': 'import/original/source.txt', **values}
        (self.book / 'import/import.yml').write_text(yaml.safe_dump(info))

    def test_first_edition_never_deletes_without_current_confirmation(self):
        self.set_info(keep='first_edition')
        before = (self.book / 'import/import.yml').read_bytes()
        self.assertTrue(import_book.status(self.book)['due'])
        self.assertFalse(import_book.expire(self.book))
        self.assertEqual(before, (self.book / 'import/import.yml').read_bytes())
        self.assertEqual((self.book / 'import/original/source.txt').read_bytes(), b'Original unveraendert')

    def test_legacy_expire_cli_is_read_only_without_confirmation(self):
        self.set_info(keep='30', keep_until='2020-01-01')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/import_book.py'),
                                 str(self.book), 'expire'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.book / 'import/original/source.txt').exists())
        self.assertNotIn('removed_at', yaml.safe_load((self.book / 'import/import.yml').read_text()))

    def test_confirmed_removal_does_not_follow_original_folder_symlink(self):
        self.set_info(keep='30', keep_until='2020-01-01')
        original = self.book / 'import/original'
        outside = self.book / 'outside'
        original.rename(outside)
        original.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symbolischer Link'):
            import_book.expire(self.book, confirmed=True)
        self.assertTrue((outside / 'source.txt').exists())


if __name__ == '__main__':
    unittest.main()
