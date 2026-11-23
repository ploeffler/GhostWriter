"""Tests für Umschlag und Druck (#68, Teil 2): Maße je Profil, EAN-13, Prüfung, Satz."""
from tests.authority_helpers import fake_github

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
        self.add('  front: cover/fehlt.pdf\n')
        errors = validate_project.check_project(self.base)
        self.assertTrue(any('cover.front: cover/fehlt.pdf fehlt' in e for e in errors), errors)
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
        self.assertIn('| Vorderseite im PDF | nur im Probedruck |', out)   # #324
        self.assertIn('| Eigene Vorderseite | – |', out)

    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('pdfinfo') and shutil.which('pdftoppm')
                         and shutil.which('pandoc'), 'xelatex, pandoc oder poppler-utils fehlen')
    def test_edition_with_cover(self):
        approve_chapter_1(self.base)
        self.add('typesetting:\n  formats: [pdf_print, cover, epub]\nprint:\n  profile: kdp\n  paper: cream\n'
                 '  crop_marks: true\ncover:\n  template: modern\n  image: cover/vorderseite.png\n'
                 'publication:\n  isbn_print: 978-3-16-148410-0\n')
        self.assertEqual(validate_project.check_project(self.base), [])
        out = Path(self.base.parent) / 'out'
        fake_github(self, self.base, edition=1)
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


class TemplateTitleTest(unittest.TestCase):
    """Vorlagentexte (#326): echter Flatterrand und Schriftverkleinerung bei überlangen Wörtern."""
    def tex(self, template, title):
        config = {'project': {'title': title, 'author': 'A'}, 'typesetting': {'page_size': 'a5'},
                  'print': {'profile': 'custom', 'spine_mm': 0}, 'cover': {'template': template}}
        return config, build_cover.cover_tex(Path('.'), config, build_cover.dimensions(config, 100))

    def test_flush_alignment_and_measure(self):
        for template, align in (('modern', 'flush left'), ('classic', 'flush center'), ('plain', 'flush center')):
            tex = self.tex(template, 'ADHS im Erwachsenenleben')[1]
            self.assertIn(f'align={align}', tex)
            self.assertNotIn('align=left,', tex)
            self.assertIn('\\gwmeasure{Erwachsenenleben}', tex)
            self.assertIn('\\gwfit{', tex)

    @unittest.skipUnless(shutil.which('xelatex'), 'xelatex fehlt')
    def test_long_word_shrinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.tex('modern', 'x')[0]
            dim = build_cover.build(Path(tmp), config, 100, Path(tmp) / 'u.pdf')
            self.assertFalse([n for n in dim['notes'] if n.startswith('Covertext')])
            config['project']['title'] = 'ADHS im Erwachsenenleben'   # #326: bricht um, ohne Verkleinerung
            dim = build_cover.build(Path(tmp), config, 100, Path(tmp) / 'u.pdf')
            self.assertFalse([n for n in dim['notes'] if n.startswith('Covertext') or 'ragt' in n], dim['notes'])
            config['project']['title'] = 'Donaudampfschifffahrtsgesellschaftskapitänsmütze'
            dim = build_cover.build(Path(tmp), config, 100, Path(tmp) / 'u.pdf')
            self.assertTrue(any(n.startswith('Covertext Titel: Schrift auf') for n in dim['notes']), dim['notes'])


def pdf_front(path, w, h, bleed=0.0, three_sided=False):
    """Fertige Vorderseite als PDF (#324): Beschnitt rot, Endformat grün."""
    pw, ph = w + (bleed if three_sided else 2 * bleed), h + 2 * bleed
    tex = ('\\documentclass{article}\\usepackage[paperwidth=%smm,paperheight=%smm,margin=0pt]{geometry}'
           '\\usepackage{xcolor,eso-pic}\\pagestyle{empty}\\AddToShipoutPictureBG{\\AtPageLowerLeft{'
           '\\color{red}\\rule{%smm}{%smm}}\\put(\\LenToUnit{%smm},\\LenToUnit{%smm}){\\color{green!50!black}'
           '\\rule{%smm}{%smm}}}\\begin{document}\\null\\end{document}\n'
           % (pw, ph, pw, ph, 0 if three_sided else bleed, bleed, w, h))
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'f.tex').write_text(tex, encoding='utf-8')
        subprocess.run(['xelatex', '-interaction=nonstopmode', 'f.tex'], cwd=tmp, capture_output=True, check=True)
        path.write_bytes((Path(tmp) / 'f.pdf').read_bytes())


def pixel(pdf, page, fx, fy):
    """Farbe (r, g, b) einer Seite an der relativen Stelle fx, fy (0–1, ab links oben), über pdftoppm."""
    data = subprocess.run(['pdftoppm', '-r', '40', '-f', str(page), '-l', str(page), '-singlefile', str(pdf)],
                          capture_output=True, check=True).stdout
    head = re.match(rb'P6\s+(\d+)\s+(\d+)\s+\d+\s', data)   # Bilddaten beginnen nach genau einem Leerzeichen
    w, h, raw = int(head.group(1)), int(head.group(2)), data[head.end():]
    x, y = min(w - 1, int(fx * w)), min(h - 1, int(fy * h))
    return tuple(raw[(y * w + x) * 3:(y * w + x) * 3 + 3])


def pages(pdf):
    return int(subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True).stdout.split('Pages:')[1].split()[0])


class FrontFitTest(unittest.TestCase):
    """Vorderseite im PDF (#324): Beschnitt erkennen, leicht abweichende Formate skalieren, nie verzerren."""
    def test_exact_and_bleed(self):
        self.assertEqual(build_cover.front_fit(148, 210, 148, 210), ((0, 0, 0, 0), ''))
        trim, note = build_cover.front_fit(154, 216, 148, 210)
        self.assertEqual(trim, (3, 3, 3, 3))
        self.assertIn('Beschnitt 3,0 mm ringsum', note)
        trim, note = build_cover.front_fit(151.2, 216.4, 148, 210)   # Umschlag-Vorderseite: am Rücken kein Beschnitt
        self.assertEqual(trim[0], 0)
        self.assertAlmostEqual(trim[2], 3.2)
        self.assertIn('oben, unten und außen', note)

    def test_scale_or_stop(self):
        trim, note = build_cover.front_fit(210, 297, 148, 210)   # A4 auf A5: gleiches Seitenverhältnis bis auf 0,3 %
        self.assertIn('auf 148 × 210 mm skaliert', note)
        self.assertGreater(trim[0], 0)   # etwas zu breit: links und rechts gleich viel weg
        self.assertEqual(trim[0], trim[2])
        with self.assertRaises(SystemExit) as e:
            build_cover.front_fit(148, 148, 148, 210, name='Vorderseite cover/quadrat.pdf')
        self.assertIn('Seitenverhältnis', str(e.exception))
        self.assertIn('cover/quadrat.pdf', str(e.exception))
        self.assertEqual(build_cover.front_fit(1748, 2480, 148, 210, physical=False)[1], '')   # Bild, 300 dpi
        with self.assertRaises(SystemExit):
            build_cover.front_fit(1000, 1000, 148, 210, physical=False)

    def test_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'cover').mkdir()
            (base / 'cover/vorne.pdf').write_bytes(b'%PDF-1.4')
            self.assertEqual(build_cover.front_source(base, {})[0], None)
            self.assertEqual(build_cover.front_source(base, {'cover': {'template': 'plain'}})[0], 'template')
            kind, path, notes = build_cover.front_source(base, {'cover': {'front': 'cover/vorne.pdf'}})
            self.assertEqual((kind, path.name, notes), ('file', 'vorne.pdf', []))
            kind, _, notes = build_cover.front_source(base, {'cover': {'front': 'cover/fehlt.pdf', 'template': 'modern'}})
            self.assertEqual(kind, 'template')
            self.assertIn('cover/fehlt.pdf fehlt', notes[0])
            with self.assertRaises(SystemExit):
                build_cover.build_front(base, {'cover': {'front': 'cover/fehlt.pdf'}}, 100, base / 'x.pdf')


@unittest.skipUnless(all(shutil.which(t) for t in ('xelatex', 'pandoc', 'pdfinfo', 'pdftoppm')),
                     'xelatex, pandoc oder poppler-utils fehlen')
class FrontCoverBuildTest(CoverProjectTest):
    """Vorderseite als Seite 1 im Bildschirm-PDF (#324), mit Probedruck, Auflage und EPUB."""
    def build(self, *args):
        out = self.base.parent / 'out'
        shutil.rmtree(out, ignore_errors=True)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--out', str(out),
                            *args], capture_output=True, text=True)
        files = {}
        if r.returncode == 0:
            ed = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))
            files = {f[len(ed['tag']):]: out / f for f in ed['files']}
        return r, files

    def test_proof_with_template_and_own_front(self):
        self.add('cover:\n  template: plain\n  background: "#2050A0"\n')
        r, files = self.build('--proof', '--formats', 'pdf,pdf_print')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Vorderseite als Seite 1 im PDF', r.stdout)
        pdf = files['.pdf']
        self.assertEqual(pages(pdf), pages(files['-druck.pdf']) + 2)   # Vorderseite und Leerseite, Druck-PDF ohne
        red, green, blue = pixel(pdf, 1, 0.1, 0.9)   # Covervorlage: Hintergrundfarbe
        self.assertTrue(blue > 120 and red < 80, (red, green, blue))
        self.assertEqual(pixel(pdf, 2, 0.5, 0.5), (255, 255, 255))   # Leerseite ohne Probedruck-Vermerk in der Mitte
        if shutil.which('qpdf'):   # Lesezeichen des Innenteils bleiben erhalten
            js = subprocess.run(['qpdf', '--json', '--json-key=outlines', str(pdf)], capture_output=True, text=True).stdout
            self.assertGreater(len(__import__('json').loads(js)['outlines']), 0)

        pdf_front(self.base / 'cover/vorderseite.pdf', 148, 210, bleed=3)
        self.add('  front: cover/vorderseite.pdf\n')
        self.assertEqual(validate_project.check_project(self.base), [])
        r, files = self.build('--proof', '--formats', 'pdf,epub')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Beschnitt 3,0 mm ringsum weggelassen', r.stdout)
        for fx, fy in ((0.01, 0.01), (0.99, 0.99), (0.5, 0.5)):   # Endformat grün, kein roter Beschnitt (3 mm ≈ 2 %)
            red, green, _ = pixel(files['.pdf'], 1, fx, fy)
            self.assertTrue(green > 100 and red < 60, (fx, fy, red, green))
        import zipfile
        with zipfile.ZipFile(files['.epub']) as z:
            opf = next(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.opf'))
            self.assertIn('properties="cover-image"', opf)

    def test_edition_manuscript_and_wrong_format(self):
        approve_chapter_1(self.base)
        self.add('cover:\n  template: plain\n  background: "#2050A0"\n')
        r, files = self.build('--edition', '1', '--formats', 'pdf')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('Vorderseite', r.stdout)   # Vorgabe proof: Auflagen ohne Vorderseite
        self.assertEqual(pixel(files['.pdf'], 1, 0.1, 0.9), (255, 255, 255))

        png(self.base / 'cover/quadrat.png', 80, 80)
        self.add('  front: cover/quadrat.png\ntypesetting:\n  pdf_cover: always\n')
        r, _ = self.build('--edition', '2', '--formats', 'pdf')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)   # nicht verzerren: Auflage bricht ab
        self.assertIn('Seitenverhältnis', r.stdout + r.stderr)
        r, files = self.build('--proof', '--formats', 'pdf')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)   # Probedruck entsteht, ohne Vorderseite
        self.assertIn('⚠ Vorderseite nicht eingebunden', r.stdout)
        self.assertEqual(pixel(files['.pdf'], 1, 0.1, 0.9), (255, 255, 255))
        r, _ = self.build('--manuscript')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('Vorderseite', r.stdout)   # „Manuskript ausgeben“ nie mit Vorderseite


if __name__ == '__main__':
    unittest.main()


class BackBlurbPositionTest(unittest.TestCase):
    """Lage des Klappentexts auf der Rückseite (#416)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / 'cover').mkdir()
        (self.base / 'cover/rueckseite.md').write_text(
            '## Klappentext\n\nEin Sommer am Meer.\n\n## Über den Autor\n\nA schreibt.\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def tex(self, **cover):
        config = {'project': {'title': 'T', 'author': 'A'}, 'typesetting': {'page_size': 'a5'},
                  'print': {'profile': 'custom', 'spine_mm': 0}, 'cover': dict(template='modern', **cover)}
        return config, build_cover.cover_tex(self.base, config, build_cover.dimensions(config, 100))

    def blurb_line(self, tex):
        return next(l for l in tex.splitlines() if 'Ein Sommer am Meer' in l)

    def test_positions(self):
        self.assertIn('anchor=north west', self.blurb_line(self.tex()[1]))
        self.assertIn('anchor=west', self.blurb_line(self.tex(back_blurb_position='middle')[1]))
        line = self.blurb_line(self.tex(back_blurb_position='bottom')[1])
        self.assertIn('let \\p1=(gwbio.north)', line)
        self.assertIn('anchor=south west', line)

    def test_schema(self):
        import cover_design
        self.assertEqual(cover_design.validate({'back_blurb_position': 'bottom'}, 148, 210), [])
        self.assertTrue(cover_design.validate({'back_blurb_position': 'links'}, 148, 210))

    @unittest.skipUnless(shutil.which('xelatex'), 'xelatex fehlt')
    def test_bottom_compiles(self):
        config = self.tex(back_blurb_position='bottom')[0]
        out = self.base / 'u.pdf'
        build_cover.build(self.base, config, 100, out)
        self.assertTrue(out.is_file())
