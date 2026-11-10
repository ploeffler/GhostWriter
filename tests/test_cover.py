"""Tests für Umschlag und Druck (#68, Teil 2): Maße je Profil, EAN-13, Prüfung, Satz."""
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import build_cover  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402
from test_matter import approve_chapter_1  # noqa: E402


def png(path, w, h, rgb=(40, 90, 120)):
    """Kleines einfarbiges PNG ohne Pillow."""
    raw = b''.join(b'\x00' + bytes(rgb) * w for _ in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def cfg(print_=None, cover=None, page='a5'):
    return {'project': {'title': 'T', 'author': 'A'}, 'typesetting': {'page_size': page},
            'print': print_ or {}, 'cover': cover or {}}


class DimensionTest(unittest.TestCase):
    def test_kdp_spine_and_size(self):
        d = build_cover.dimensions(cfg({'profile': 'kdp', 'paper': 'white'}), 200)
        self.assertAlmostEqual(d['spine'], 200 * 0.0572)
        self.assertAlmostEqual(d['total_w'], 2 * 3.2 + 2 * 148 + 200 * 0.0572)
        self.assertAlmostEqual(d['total_h'], 2 * 3.2 + 210)
        self.assertTrue(d['spine_text'])
        cream = build_cover.dimensions(cfg({'profile': 'kdp', 'paper': 'cream'}), 200)
        self.assertAlmostEqual(cream['spine'], 200 * 0.0635)

    def test_kdp_no_spine_text_below_79_pages(self):
        d = build_cover.dimensions(cfg({'profile': 'kdp', 'paper': 'cream'}), 78)
        self.assertFalse(d['spine_text'])
        self.assertIn('erst ab 79 Seiten', d['notes'][0])

    def test_bod_needs_spine(self):
        with self.assertRaises(SystemExit) as e:
            build_cover.dimensions(cfg({'profile': 'bod'}), 120)
        self.assertIn('spine_mm', str(e.exception))
        d = build_cover.dimensions(cfg({'profile': 'bod', 'spine_mm': 9.4, 'crop_marks': True}), 120)
        self.assertEqual((d['bleed'], d['spine'], d['slug']), (5.0, 9.4, 8.0))
        custom = build_cover.dimensions(cfg({'profile': 'custom', 'paper_mm_per_page': 0.05, 'bleed_mm': 4}), 100)
        self.assertAlmostEqual(custom['spine'], 5.0)
        self.assertFalse(custom['spine_text'])   # unter 6 mm

    def test_no_profile(self):
        with self.assertRaises(SystemExit):
            build_cover.dimensions(cfg(), 100)


class Ean13Test(unittest.TestCase):
    def decode(self, bits):
        """Unabhängige Gegenprobe: Ziffern aus den 95 Modulen zurücklesen."""
        self.assertEqual(len(bits), 95)
        self.assertEqual((bits[:3], bits[45:50], bits[92:]), ('101', '01010', '101'))
        L = {c: str(i) for i, c in enumerate(build_cover.L_CODES)}
        G = {c: str(i) for i, c in enumerate(build_cover.G_CODES)}
        R = {c: str(i) for i, c in enumerate(build_cover.R_CODES)}
        left, parity = '', ''
        for k in range(6):
            c = bits[3 + 7 * k:10 + 7 * k]
            left += L.get(c) or G[c]
            parity += 'L' if c in L else 'G'
        right = ''.join(R[bits[50 + 7 * k:57 + 7 * k]] for k in range(6))
        return str(build_cover.PARITY.index(parity)) + left + right

    def test_roundtrip_and_known_codes(self):
        for isbn in ('978-3-16-148410-0', '9781861972712', '4006381333931'):
            d = build_cover.isbn13(isbn)
            self.assertEqual(self.decode(build_cover.ean13_modules(d)[0]), d)
        # Standard-Tabellen (GS1): L-Code der 0 und 9, Parität der 9
        self.assertEqual((build_cover.L_CODES[0], build_cover.L_CODES[9]), ('0001101', '0001011'))
        self.assertEqual(build_cover.PARITY[9], 'LGGLGL')
        self.assertEqual(build_cover.isbn13('3-16-148410-X'), '9783161484100')   # ISBN-10 → 13
        self.assertIsNone(build_cover.isbn13('978-3-16-148410-1'))
        self.assertIn('ISBN 978-3-16-148410-0', build_cover.barcode_tikz('978-3-16-148410-0', 0, 0))


class CoverProjectTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        (self.base / 'cover').mkdir()
        png(self.base / 'cover/vorderseite.png', 60, 90)
        text = (ROOT / 'templates/cover-rueckseite.md').read_text(encoding='utf-8')
        text = text.replace('<Worum geht es, für wen ist das Buch, was nimmt man mit? Etwa 80–150 Wörter.>',
                            'Ein Buch über *Aufschieben* und was hilft.')
        (self.base / 'cover/rueckseite.md').write_text(text, encoding='utf-8')

    def add(self, text):
        path = self.base / 'ghostwriter.yml'
        path.write_text(path.read_text(encoding='utf-8') + text, encoding='utf-8')

    def test_texts_and_image_size(self):
        blurb, bio = build_cover.back_texts(self.base)
        self.assertEqual(blurb, 'Ein Buch über *Aufschieben* und was hilft.')
        self.assertEqual(bio, '')   # Platzhalter der Vorlage wird nicht gesetzt
        self.assertEqual(build_cover.image_size(self.base / 'cover/vorderseite.png'), (60, 90))

    def test_validation(self):
        self.add('typesetting:\n  formats: [pdf, cover]\ncover:\n  image: cover/fehlt.jpg\n')
        errors = validate_project.check_project(self.base)
        self.assertTrue(any('print.profile fehlt' in e for e in errors), errors)
        self.assertTrue(any('cover.image: cover/fehlt.jpg fehlt' in e for e in errors), errors)
        self.add('print:\n  profile: bod\n  paper: cream\n')
        errors = validate_project.check_project(self.base)
        self.assertTrue(any('Rückenbreite angeben' in e for e in errors), errors)
        self.assertTrue(any('print.paper gilt nur für das Profil kdp' in e for e in errors), errors)

    def test_form_text(self):
        self.add('print:\n  profile: kdp\n  paper: cream\ncover:\n  template: modern\n  price: 9,99 €\n')
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'output', '--text'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('| Druckprofil | Amazon KDP |', out)
        self.assertIn('| Papier | creme |', out)
        self.assertIn('| Vorlage | modern |', out)
        self.assertIn('| Preis | 9,99 € |', out)

    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('pdfinfo') and shutil.which('pdftoppm')
                         and shutil.which('pandoc'), 'xelatex, pandoc oder poppler-utils fehlen')
    def test_edition_with_cover(self):
        approve_chapter_1(self.base)
        self.add('typesetting:\n  formats: [pdf_print, cover, epub]\nprint:\n  profile: kdp\n  paper: cream\n'
                 '  crop_marks: true\ncover:\n  template: modern\n  image: cover/vorderseite.png\n'
                 'publication:\n  isbn_print: 978-3-16-148410-0\n')
        self.assertEqual(validate_project.check_project(self.base), [])
        out = Path(self.base.parent) / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--edition', '1',
                            '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ed = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))
        tag = ed['tag']
        self.assertEqual(ed['files'], [f'{tag}-druck.pdf', f'{tag}-umschlag.pdf', f'{tag}.epub'])
        info = lambda p: subprocess.run(['pdfinfo', str(p)], capture_output=True, text=True).stdout
        pages = int(info(out / f'{tag}-druck.pdf').split('Pages:')[1].split()[0])
        size = info(out / f'{tag}-druck.pdf').split('Page size:')[1].split()
        self.assertAlmostEqual(float(size[0]) / 72 * 25.4, 148 + 16, delta=0.2)   # Schnittmarken: 8 mm Rand
        w, h = (float(x) / 72 * 25.4 for x in info(out / f'{tag}-umschlag.pdf').split('Page size:')[1].split()[:3:2])
        self.assertAlmostEqual(w, 2 * 3.2 + 2 * 148 + pages * 0.0635 + 16, delta=0.2)
        self.assertAlmostEqual(h, 2 * 3.2 + 210 + 16, delta=0.2)
        self.assertIn(f'Rücken {pages * 0.0635:.1f} mm bei {pages} Seiten', r.stdout)
        import zipfile
        with zipfile.ZipFile(out / f'{tag}.epub') as z:
            # Titelbild als EPUB-3-cover-image; den Dateinamen vergibt pandoc (ab 3.6 „file0.jpg“)
            opf = next(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.opf'))
            item = re.search(r'<item\b[^>]*properties="cover-image"[^>]*>', opf)
            self.assertIsNotNone(item, 'Titelbild fehlt im EPUB')
            self.assertIn('media-type="image/jpeg"', item.group(0))


if __name__ == '__main__':
    unittest.main()
