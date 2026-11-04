"""Tests für Illustrationen (#54): Bild-Auftrag, Ablegen, Prüfung, Satz („Strolchi und Opi“)."""
import hashlib
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
sys.path.insert(0, str(ROOT / 'tests'))
import assemble  # noqa: E402
import build_edition  # noqa: E402
import characters  # noqa: E402
import images  # noqa: E402
import reference_images  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402
from test_cover import png  # noqa: E402
from test_matter import approve_chapter_1  # noqa: E402


class ImageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        cfg = self.base / 'ghostwriter.yml'
        cfg.write_text(cfg.read_text(encoding='utf-8') + 'images:\n  style: Aquarell, weiche Farben\n', encoding='utf-8')
        characters.add(self.base, 'Strolchi', 'main')
        characters.add(self.base, 'Opi', 'supporting')
        characters.update(self.base, 'strolchi', {'visual': 'rotbrauner Mischling, weißer Fleck am rechten Ohr'})
        characters.update(self.base, 'opi', {'appearance': 'weißer Bart, grüner Hut'})
        characters.assign(self.base, '1.1', ['Strolchi', 'Opi'])
        png(self.tmp / 'bild.png', 120, 80)

    def add(self, **kw):
        args = dict(caption='Opi und Strolchi auf der Bank', source='copy', provider='openai', prompt='Stil: …', variants=3)
        args.update(kw)
        return images.add(self.base, '1.1', self.tmp / 'bild.png', **args)

    def place(self, iid):
        _, config = load(self.base)
        p = self.base / config['structure']['chapters'][0]['sections'][0]['path']
        t = p.read_text(encoding='utf-8')
        p.write_text(t.replace('Der Brief lag dort sechs Monate.', f'![](bild:{iid})\n\nDer Brief lag dort sechs Monate.', 1),
                     encoding='utf-8')

    def approve(self, meta):
        _, config = load(self.base)
        hit = images.all_images(self.base, config)[meta['id']]
        hit[3].write_text(hit[3].read_text(encoding='utf-8').replace('status: draft', 'status: approved'), encoding='utf-8')

    def test_prompt_uses_style_and_character_looks(self):
        _, config = load(self.base)
        prompt, ids = images.build_prompt(self.base, config, '1.1', 'Beide sitzen auf der Bank, Abendlicht')
        self.assertEqual(ids, ['char-strolchi', 'char-opi'])
        self.assertTrue(prompt.startswith('Stil: Aquarell, weiche Farben\n\nSzene: Beide sitzen auf der Bank'))
        self.assertIn('- Strolchi: rotbrauner Mischling, weißer Fleck am rechten Ohr', prompt)
        self.assertIn('- Opi: weißer Bart, grüner Hut', prompt)   # ohne visual: appearance
        # zwei Aufträge: dieselbe Figur, dieselben Merkmale
        other, _ = images.build_prompt(self.base, config, '1.1', 'Strolchi jagt einen Schmetterling', ['Strolchi'])
        self.assertIn('- Strolchi: rotbrauner Mischling, weißer Fleck am rechten Ohr', other)
        self.assertNotIn('Opi', other)

    def test_prompt_requires_explicitly_approved_visual_references(self):
        ref = reference_images.add(
            self.base, self.tmp / 'bild.png', 'Opi Porträt',
            description='Weißer Bart, grüner Hut',
            roles=['visual_reference'], origin='provided',
            links=[{'kind': 'person', 'id': 'char-opi'}])
        with self.assertRaisesRegex(SystemExit, 'nicht als visuelle Referenz freigegeben'):
            images.build_prompt(self.base, load(self.base)[1], '1.1', 'Opi am Hafen',
                                reference_ids=[ref['id']])
        reference_images.set_status(self.base, ref['id'], 'approved')
        prompt, _ = images.build_prompt(self.base, load(self.base)[1], '1.1', 'Opi am Hafen',
                                        reference_ids=[ref['id']])
        self.assertIn('Ausdrücklich ausgewählte visuelle Referenzen', prompt)
        self.assertIn('Weißer Bart, grüner Hut', prompt)
        self.assertIn('Bilddateien zusätzlich an den Bilddienst übergeben', prompt)

    def test_add_records_selected_reference_ids_and_exact_file_hash(self):
        ref = reference_images.add(
            self.base, self.tmp / 'bild.png', 'Opi Referenz',
            description='Weißer Bart, grüner Hut',
            roles=['visual_reference'], origin='provided',
            links=[{'kind': 'person', 'id': 'char-opi'}])
        reference_images.set_status(self.base, ref['id'], 'approved')
        meta, folder = self.add(reference_ids=[ref['id']])
        run = (self.base / folder / 'run-001.md').read_text(encoding='utf-8')
        frontmatter = run.split('---\n', 2)[1]
        record = yaml.safe_load(frontmatter)['visual_references'][0]
        self.assertEqual(record['id'], ref['id'])
        self.assertEqual(record['file'], ref['file'])
        expected = hashlib.sha256((self.base / 'reference-images' / ref['file']).read_bytes()).hexdigest()
        self.assertEqual(record['sha256'], expected)
        self.assertIn('Verwendete visuelle Referenzen', run)
        self.assertIn(expected, run)

    def test_add_rejects_unapproved_reference(self):
        ref = reference_images.add(self.base, self.tmp / 'bild.png', 'Nicht freigegeben')
        with self.assertRaisesRegex(SystemExit, 'nicht als visuelle Referenz freigegeben'):
            self.add(reference_ids=[ref['id']])

    def test_add_writes_meta_and_run(self):
        meta, folder = self.add(names=['Opi'])
        self.assertEqual(meta['id'], 'img-opi-und-strolchi-auf-der-bank')
        self.assertEqual((meta['status'], meta['ai_generated'], meta['width_px']), ('draft', True, 120))
        run = (self.base / folder / 'run-001.md').read_text(encoding='utf-8')
        self.assertIn('type: illustration', run)
        self.assertIn('variants: 3', run)
        second, _ = self.add(source='own', provider='')
        self.assertEqual(second['id'], 'img-opi-und-strolchi-auf-der-bank-2')
        self.assertFalse(second['ai_generated'])
        self.assertNotIn('run', second)
        self.assertEqual(validate_project.check_project(self.base), [])

    def test_validation(self):
        meta, folder = self.add()
        self.place('img-gibt-es-nicht')
        errors = validate_project.check_project(self.base)
        self.assertTrue(any('Bild img-gibt-es-nicht gibt es nicht' in e for e in errors), errors)
        y = self.base / folder / f'{meta["id"]}.yml'
        y.write_text(y.read_text(encoding='utf-8').replace('section_id: sec-01-01', 'section_id: sec-01-02'), encoding='utf-8')
        self.assertTrue(any('(Ordner)' in e for e in validate_project.check_project(self.base)))

    def test_draft_blocks_approved_passes(self):
        meta, _ = self.add()
        self.place(meta['id'])
        approve_chapter_1(self.base)
        _, config = load(self.base)
        parts, mparts = assemble.book_parts(self.base, config), assemble.matter_parts(self.base, config)
        self.assertEqual(assemble.problems(parts, config, mparts, self.base),
                         ['Bild „Opi und Strolchi auf der Bank“ in Kapitel 1 ist nicht freigegeben'])
        md, used = assemble.resolve_images(self.base, config, assemble.book_body(parts, mparts), proof=True)
        self.assertIn('[Bild: Entwurf, nicht freigegeben]{.gwstatus}', md)
        self.approve(meta)
        self.assertEqual(assemble.problems(parts, config, mparts, self.base), [])
        md, used = assemble.resolve_images(self.base, config, assemble.book_body(parts, mparts))
        self.assertRegex(md, r'!\[Opi und Strolchi auf der Bank\]\(/[^)]+/img-opi-und-strolchi-auf-der-bank\.png\)'
                             r'\{#img-opi-und-strolchi-auf-der-bank width=100%\}')
        self.assertEqual([m['id'] for m in used], [meta['id']])
        self.assertEqual(build_edition.image_credit(used, config), 'Die Abbildung ist mit KI erzeugt (OpenAI ChatGPT).')
        self.assertIn('120 px Breite', build_edition.image_notes(used, {'page_size': 'a5'})[0])
        config['images']['credit_in_imprint'] = False
        self.assertEqual(build_edition.image_credit(used, config), '')

    def test_views(self):
        meta, _ = self.add()
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *a, '--text'],
                                        capture_output=True, text=True, check=True).stdout
        out = run('images', '1.1')
        self.assertIn('Bildstil des Buchs: Aquarell, weiche Farben · Figuren im Abschnitt: Strolchi, Opi', out)
        self.assertIn('✏️ Entwurf | Auftrag kopiert | nein |', out)
        conf = run('approval-image', meta['id'])
        self.assertIn('Bild freigeben', conf)
        self.assertIn('⚠️ 120 px breit.', conf)
        self.assertIn('`BI` Bilder', run('section', '1.1'))

    @unittest.skipUnless(shutil.which('pandoc') and shutil.which('xelatex') and shutil.which('pdfimages'),
                         'pandoc, xelatex oder poppler-utils fehlen')
    def test_edition_with_image(self):
        png(self.tmp / 'bild.png', 2000, 1400)
        meta, _ = self.add()
        self.place(meta['id'])
        approve_chapter_1(self.base)
        self.approve(meta)
        out = self.tmp / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--edition', '1',
                            '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tag = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))['tag']
        listing = subprocess.run(['pdfimages', '-list', str(out / f'{tag}.pdf')], capture_output=True, text=True).stdout
        self.assertIn(' 2000  1400 ', listing)
        text = subprocess.run(['pdftotext', str(out / f'{tag}.pdf'), '-'], capture_output=True, text=True).stdout
        self.assertIn('Opi und Strolchi auf der Bank', text)
        self.assertIn('Die Abbildung ist mit KI erzeugt', text)
        import zipfile
        with zipfile.ZipFile(out / f'{tag}.epub') as z:
            self.assertTrue(any(n.endswith('.png') for n in z.namelist()))
        from docx import Document
        self.assertEqual(len(Document(str(out / f'{tag}.docx')).inline_shapes), 1)


if __name__ == '__main__':
    unittest.main()
