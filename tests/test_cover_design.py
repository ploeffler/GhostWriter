"""Covergestaltung: Speicherung, Farbauswahl, dynamische Texte und echter Satz."""
from pathlib import Path
import shutil
import json
import subprocess
import sys
import tempfile
import unittest

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import build_cover
import cover_design


class CoverDesignTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        (self.base / 'cover').mkdir()
        im = Image.new('RGB', (600, 900), '#EEDDCB')
        for y in range(400, 900):
            for x in range(600):
                im.putpixel((x, y), (40, 70, 100))
        im.save(self.base / 'cover/motif.png')
        self.image_bytes = (self.base / 'cover/motif.png').read_bytes()
        self.box = dict(x=12, y=12, width=124, height=24, font_size=24, color='#312A24')
        self.config = {'project': {'title': 'Der Abwasch bleibt', 'subtitle': 'Ein neuer Blick', 'author': 'Ada Beispiel'},
                       'cover': {'image': 'cover/motif.png', 'background': '#EEDDCB',
                                 'text_boxes': {'title': self.box}},
                       'print': {'profile': 'custom', 'spine_mm': 10}}
        self.path = self.base / 'ghostwriter.yml'
        self.path.write_text(yaml.safe_dump(self.config))

    def tex(self, config=None):
        config = config or self.config
        return build_cover.cover_tex(self.base, config, build_cover.dimensions(config, 200))

    def test_colors_are_readonly_and_include_free_background(self):
        before = self.path.read_bytes()
        self.assertEqual(cover_design.image_colors(self.base, self.config['cover'], (.5, .1)), ['#EEDDCB'])
        self.assertIn('#EEDDCB', cover_design.image_colors(self.base, self.config['cover']))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual((self.base / 'cover/motif.png').read_bytes(), self.image_bytes)
        with self.assertRaises(ValueError):
            cover_design.image_colors(self.base, self.config['cover'], (-.1, 0))

    def test_patch_roundtrip_preserves_project_and_other_colors(self):
        cover_design.save(self.base, {'panel_backgrounds': {'back': '#123456'}, 'background_targets': ['spine'],
                                      'text_boxes': {'title': {'y': 15}, 'author': dict(self.box, y=50)}})
        loaded = yaml.safe_load(self.path.read_text())
        self.assertEqual(loaded['project'], self.config['project'])
        self.assertEqual(loaded['cover']['background'], '#EEDDCB')
        self.assertEqual(loaded['cover']['text_boxes']['title']['y'], 15)
        tex = self.tex(loaded)
        self.assertIn('123456', tex)
        self.assertIn('(173.00mm,198.00mm)', tex)  # 148 + spine 10 + bleed 3 + x 12; y 3+210-15
        self.assertEqual((self.base / 'cover/motif.png').read_bytes(), self.image_bytes)

    def test_invalid_layout_does_not_write(self):
        before = self.path.read_bytes()
        for patch in ({'text_boxes': {'title': {'width': 200}}}, {'image_mode': 'unknown'},
                      {'text_boxes': {'title': {'font_size': 0}}}, {'text_boxes': {'title': {'x': float('nan')}}}):
            with self.assertRaises(ValueError):
                cover_design.save(self.base, patch)
            self.assertEqual(self.path.read_bytes(), before)

    def test_metadata_is_dynamic_and_finished_image_omits_front_text_only(self):
        self.assertEqual(self.tex().count('Der Abwasch bleibt'), 2)  # front and spine
        self.config['project']['title'] = 'Geänderter Titel'
        self.assertNotIn('Der Abwasch bleibt', self.tex())
        self.assertEqual(self.tex().count('Geänderter Titel'), 2)
        self.config['cover']['image_mode'] = 'finished'
        tex = self.tex()
        self.assertEqual(tex.count('Geänderter Titel'), 1)  # spine remains dynamic
        self.assertNotIn('Ein neuer Blick', tex)
        self.assertNotIn('\\sbox{\\gwtextbox}', tex)

    def test_missing_settings_keep_all_templates(self):
        self.config['cover'].pop('text_boxes')
        for template in ('classic', 'modern', 'plain'):
            self.config['cover']['template'] = template
            tex = self.tex()
            self.assertIn('Der Abwasch bleibt', tex)
            self.assertIn('Ein neuer Blick', tex)
            self.assertNotIn('\\sbox{\\gwtextbox}', tex)

    def test_line_breaks_and_original_image_protection(self):
        self.config['cover']['text_boxes']['title']['break_after'] = [2]
        self.assertIn('Der Abwasch\\\\ bleibt', self.tex())
        self.config['project']['title'] = 'Kurz'
        with self.assertRaisesRegex(SystemExit, 'Umbruchposition'):
            self.tex()
        with self.assertRaisesRegex(SystemExit, 'Originalbild'):
            build_cover.build(self.base, self.config, 200, self.base / 'cover/motif.png')
        self.assertEqual((self.base / 'cover/motif.png').read_bytes(), self.image_bytes)

    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('pdftoppm'),
                         'TeX und Poppler fehlen')
    def test_real_pdf_and_preview_and_overflow(self):
        # All texts lie in the free upper portion; proof uses the actual export renderer.
        self.config['cover']['text_boxes']['subtitle'] = dict(self.box, y=39, height=12, font_size=13)
        self.config['cover']['text_boxes']['author'] = dict(self.box, y=55, height=12, font_size=14)
        out, jpg = self.base / 'cover.pdf', self.base / 'front.jpg'
        build_cover.build(self.base, self.config, 200, out, jpg)
        self.assertTrue(out.read_bytes().startswith(b'%PDF'))
        if shutil.which('pdftotext'):
            text = subprocess.run(['pdftotext', str(out), '-'], capture_output=True, text=True, check=True).stdout
            self.assertIn('Der Abwasch bleibt', text)
            self.assertIn('Ein neuer Blick', text)
            self.assertIn('Ada Beispiel', text)
        with Image.open(jpg) as im:
            self.assertAlmostEqual(im.width / im.height, 148 / 210, places=2)
        before = self.path.read_bytes()
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/cover_design.py'), str(self.base), 'preview',
                            json.dumps({'text_boxes': self.config['cover']['text_boxes']}),
                            '--out', str(self.base / 'preview.pdf'), '--front-jpg', str(self.base / 'preview.jpg')],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue((self.base / 'preview.jpg').exists())
        # A long title must be rejected, never silently clipped.
        self.config['project']['title'] = 'Ein sehr langer Buchtitel ' * 12
        self.config['cover']['text_boxes']['title']['height'] = 5
        with self.assertRaisesRegex(SystemExit, 'overflow|Textbereich'):
            build_cover.build(self.base, self.config, 200, self.base / 'overflow.pdf')
        self.assertFalse((self.base / 'overflow.pdf').exists())


if __name__ == '__main__':
    unittest.main()
