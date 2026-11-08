"""Tests für die Ausgabeoptionen (#68, Teil 1): Vorgaben wie bisher, Satzoptionen, Impressum, Formate."""
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
import build_edition  # noqa: E402
import validate_project  # noqa: E402
from render_view import TYPESETTING_DEFAULT  # noqa: E402
from test_matter import approve_chapter_1  # noqa: E402

OPTIONS = """typesetting:
  font: termes
  heading_font: sans
  margins: classic
  line_spacing: 1.3
  paragraph: spacing
  hyphenation: false
  chapter_start: right
  running_heads: book
  page_numbers: footer_outer
  initials: true
  formats: [pdf, epub]
publication:
  publisher: Selbstverlag
  isbn_print: 978-3-16-148410-0
  isbn_ebook: 978-3-16-148411-7
  rights: Alle Rechte vorbehalten.
"""


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def set_options(self, text=OPTIONS):
        path = self.base / 'ghostwriter.yml'
        path.write_text(path.read_text(encoding='utf-8') + text, encoding='utf-8')

    def view(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args, '--text'],
                              capture_output=True, text=True, check=True).stdout


class OutputOptionsTest(Base):
    def test_defaults_look_like_before(self):
        ts = dict(TYPESETTING_DEFAULT)
        self.assertEqual(build_edition.layout_tex(ts, {'title': 'T'}), '')
        self.assertEqual(build_edition.epub_css(ts), '')
        for v in ('serif', 'pagella'):
            self.assertEqual(build_edition.FONTS[v][0], 'TeX Gyre Pagella')

    def test_layout_tex_for_options(self):
        ts = dict(TYPESETTING_DEFAULT, font='heros', running_heads='book', page_numbers='footer_center',
                  hyphenation=False, initials=True)
        tex = build_edition.layout_tex(ts, {'title': 'A & B'})
        self.assertIn('\\sffamily', tex)
        self.assertIn('\\lehead{A \\& B}\\rohead{\\leftmark}', tex)
        self.assertIn('\\cfoot*{\\pagemark}', tex)
        self.assertIn('\\hyphenpenalty=10000', tex)
        self.assertIn('\\usepackage{lettrine}', tex)
        css = build_edition.epub_css(dict(TYPESETTING_DEFAULT, font='heros', paragraph='spacing', line_spacing=1.5))
        self.assertIn('font-family: sans-serif', css)
        self.assertIn('text-indent: 0', css)
        self.assertIn('line-height: 1.98', css)

    def test_latex_plain_text_special_characters(self):
        self.assertEqual(build_edition.latex_escape('OpenAI image_gen'), r'OpenAI image\_gen')
        self.assertEqual(build_edition.latex_escape('A & 50% #1 $2 {x} ~ ^ ' + chr(92)),
                         r'A \& 50\% \#1 \$2 \{x\} \textasciitilde{} \textasciicircum{} \textbackslash{}')
        ts = dict(TYPESETTING_DEFAULT, running_heads='book')
        self.assertIn(r'\lehead{Titel\_1}', build_edition.layout_tex(ts, {'title': 'Titel_1'}))

    def test_schema_and_isbn(self):
        self.set_options()
        self.assertEqual(validate_project.check_project(self.base), [])
        self.assertTrue(validate_project.isbn_ok('3-16-148410-X'))   # ISBN-10 mit X als Prüfziffer
        self.assertFalse(validate_project.isbn_ok('3-16-148410-0'))
        self.assertFalse(validate_project.isbn_ok('978-3-16'))
        self.set_options('  # Tippfehler in der Prüfziffer\n')
        path = self.base / 'ghostwriter.yml'
        path.write_text(path.read_text(encoding='utf-8').replace('148410-0', '148410-1'), encoding='utf-8')
        errors = validate_project.check_project(self.base)
        self.assertEqual(len(errors), 1)
        self.assertIn('publication.isbn_print', errors[0])

    def test_imprint_lines(self):
        meta = {'title': 'T', 'date': '2026-11-03', 'edition_text': '1. Auflage', 'author': 'A'}
        lines = build_edition.imprint_markdown(meta, 'T – Auflage 1', '', {
            'publisher': 'Selbstverlag', 'isbn_print': '978-3-16-148410-0', 'rights': 'Alle Rechte vorbehalten.'})
        self.assertEqual(lines[3:], ['Alle Rechte vorbehalten.', 'Selbstverlag', 'ISBN 978-3-16-148410-0 (Druckausgabe)'])
        self.assertEqual(build_edition.imprint_markdown(meta, 'x', '', {'publisher': 'Muster Verlag'})[3], 'Verlag: Muster Verlag')
        self.assertEqual(len(build_edition.imprint_markdown(meta, 'x', '')), 3)   # ohne Angaben wie bisher

    def test_views(self):
        default = self.view('output')
        self.assertIn('| Ränder | Standard |', default)
        self.assertIn('| Formate einer Auflage | PDF (Bildschirm), DOCX, EPUB |', default)
        self.set_options()
        form = self.view('output')
        self.assertIn('| Kolumnentitel | Buch- und Kapiteltitel |', form)
        self.assertIn('| ISBN E-Book | 978-3-16-148411-7 |', form)
        self.assertIn('| Formate | PDF, EPUB |', self.view('edition-create'))
        self.assertIn('Formular `Ausgabe`', self.view('project-settings'))


@unittest.skipUnless(shutil.which('pandoc') and shutil.which('xelatex') and shutil.which('pdffonts'),
                     'pandoc, xelatex oder pdffonts fehlen')
class OutputTypesettingTest(Base):
    def build(self, *extra):
        out = Path(self.base.parent) / ('out' + '-'.join(extra))
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--edition', '1',
                            '--out', str(out), *extra], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return out, yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))

    def test_pdf_imprint_with_provider_underscore(self):
        approve_chapter_1(self.base)
        self.set_options('ai_disclosure:\n  mode: custom\n  placement: imprint\n'
                         '  text: "Bildnachweis: OpenAI image_gen"\n')
        out, ed = self.build('--formats', 'pdf')
        text = subprocess.run(['pdftotext', str(out / f'{ed["tag"]}.pdf'), '-'],
                              capture_output=True, text=True, check=True).stdout
        self.assertIn('OpenAI image_gen', text)

    def test_options_in_pdf_and_epub(self):
        approve_chapter_1(self.base)
        _, plain = self.build('--formats', 'pdf')
        pages_before = int(subprocess.run(['pdfinfo', str(Path(self.base.parent) / 'out--formats-pdf' / f'{plain["tag"]}.pdf')],
                                          capture_output=True, text=True).stdout.split('Pages:')[1].split()[0])
        self.set_options()
        out, ed = self.build()
        self.assertEqual(ed['files'], [f'{ed["tag"]}.pdf', f'{ed["tag"]}.epub'])   # Formate aus typesetting
        pdf = out / f'{ed["tag"]}.pdf'
        fonts = subprocess.run(['pdffonts', str(pdf)], capture_output=True, text=True).stdout
        self.assertIn('TeXGyreTermes', fonts)
        self.assertIn('TeXGyreHeros-Bold', fonts)       # Überschriften serifenlos
        self.assertNotIn('Pagella', fonts)
        text = subprocess.run(['pdftotext', str(pdf), '-'], capture_output=True, text=True).stdout
        self.assertIn('ISBN 978-3-16-148410-0 (Druckausgabe)', text)
        self.assertIn('Selbstverlag', text)
        pages = int(subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True).stdout.split('Pages:')[1].split()[0])
        self.assertGreater(pages, pages_before)          # breitere Ränder, größerer Zeilenabstand, rechte Seiten
        import zipfile
        with zipfile.ZipFile(out / f'{ed["tag"]}.epub') as z:
            names = z.namelist()
            css = ''.join(z.read(n).decode('utf-8') for n in names if n.endswith('.css'))
            opf = z.read('EPUB/content.opf').decode('utf-8')
            xhtml = ''.join(z.read(n).decode('utf-8') for n in names if n.endswith('.xhtml'))
        self.assertIn('p { text-indent: 0; margin-bottom: 0.7em; }', css)   # Absätze mit Abstand
        self.assertIn('urn:isbn:9783161484117', opf)
        self.assertIn('class="initial"', xhtml)


if __name__ == '__main__':
    unittest.main()


class OutputWidgetTest(Base):
    def test_widget_json(self):
        import json
        import re
        self.set_options(OPTIONS + 'print:\n  profile: kdp\n')
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'output'],
                             capture_output=True, text=True, check=True).stdout
        m = re.search(r'GW\.render\("([^"]+)",(.*)\)</script>', out)
        self.assertEqual(m.group(1), 'ausgabeoptionen')
        data = json.loads(json.loads(m.group(2).replace('<\\/', '</'))['OUTPUT_JSON'])
        self.assertEqual(data['typesetting']['margins'], 'classic')
        self.assertEqual(data['typesetting']['toc_depth'], 1)          # Vorgaben ergänzt
        self.assertEqual(data['publication']['publisher'], 'Selbstverlag')
        self.assertEqual(data['print'], {'profile': 'kdp'})
        self.assertEqual((data['cover'], data['blurb'], data['author_bio']), ({}, '', ''))
