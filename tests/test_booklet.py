"""Tests für die Broschüre zum Selbstdrucken (Format `booklet`): Seitenfolge, Bogen, Satz."""
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
from test_matter import approve_chapter_1  # noqa: E402


class OrderTest(unittest.TestCase):
    def test_eight_pages(self):
        # Bogen 1: vorne 8|1, hinten 2|7; Bogen 2: vorne 6|3, hinten 4|5
        self.assertEqual(build_edition.booklet_order(8), [8, 1, 2, 7, 6, 3, 4, 5])

    def test_padding_to_multiple_of_four(self):
        order = build_edition.booklet_order(5)
        self.assertEqual(len(order), 8)
        self.assertEqual(order, [0, 1, 2, 0, 0, 3, 4, 5])
        self.assertEqual(sorted(p for p in order if p), [1, 2, 3, 4, 5])
        self.assertEqual(build_edition.booklet_order(0), [0, 0, 0, 0])

    def test_every_page_once(self):
        for n in range(1, 41):
            order = build_edition.booklet_order(n)
            self.assertEqual(len(order) % 4, 0)
            self.assertEqual(sorted(p for p in order if p), list(range(1, n + 1)))

    def test_sheet(self):
        self.assertEqual(build_edition.booklet_sheet('a5'), 'a4')
        self.assertEqual(build_edition.booklet_sheet('12x19'), 'a4')
        self.assertEqual(build_edition.booklet_sheet('13.5x21.5'), 'a4')
        self.assertEqual(build_edition.booklet_sheet('a4'), 'a3')
        tex = build_edition.booklet_tex('innen.pdf', 3, 'a5')
        self.assertIn('paperwidth=297mm,paperheight=210mm', tex)
        self.assertIn('pages={{},1,2,3}', tex)   # 3 Seiten: vorne leer|1, hinten 2|3
        self.assertIn('nup=2x1', tex)


class BookletBuildTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def test_schema_accepts_booklet(self):
        path = self.base / 'ghostwriter.yml'
        path.write_text(path.read_text(encoding='utf-8') + 'typesetting:\n  formats: [pdf, booklet]\n', encoding='utf-8')
        self.assertEqual(validate_project.check_project(self.base), [])

    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('pdfinfo') and shutil.which('pandoc'),
                         'xelatex, pandoc oder poppler-utils fehlen')
    def test_edition_with_booklet(self):
        approve_chapter_1(self.base)
        path = self.base / 'ghostwriter.yml'
        path.write_text(path.read_text(encoding='utf-8') + 'print:\n  crop_marks: true\n', encoding='utf-8')
        out = Path(self.base.parent) / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--edition', '1',
                            '--out', str(out), '--formats', 'pdf,booklet'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tag = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))['tag']
        self.assertEqual(sorted(p.name for p in out.glob('*.pdf')), [f'{tag}-broschuere.pdf', f'{tag}.pdf'])
        info = lambda p: subprocess.run(['pdfinfo', str(p)], capture_output=True, text=True).stdout
        pages = int(info(out / f'{tag}.pdf').split('Pages:')[1].split()[0])
        b = info(out / f'{tag}-broschuere.pdf')
        sheets = -(-pages // 4)
        self.assertEqual(int(b.split('Pages:')[1].split()[0]), 2 * sheets)   # Vorder- und Rückseite je Blatt
        w, h = (float(x) / 72 * 25.4 for x in b.split('Page size:')[1].split()[:3:2])
        self.assertAlmostEqual(w, 297, delta=0.5)   # A4 quer, ohne Schnittmarken-Rand
        self.assertAlmostEqual(h, 210, delta=0.5)
        self.assertIn('beidseitig über die kurze Kante', r.stdout)


if __name__ == '__main__':
    unittest.main()
