"""DOCX und PDF zum Gegenlesen mit QR-Kennung (#572, Teil 2)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import checkout  # noqa: E402
from render_view import load  # noqa: E402

try:
    import segno  # noqa: F401
    import docx  # noqa: F401
    HAVE = bool(shutil.which('pandoc'))
except ImportError:
    HAVE = False
try:
    import cv2
except ImportError:
    cv2 = None


@unittest.skipUnless(HAVE, 'pandoc, python-docx und segno nötig')
class CheckoutFilesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        import checkout_files
        self.cf = checkout_files

    def entry(self, chapters='1-2'):
        return checkout.start(self.base, self.config, 'Anna', chapters, by='x', commit='abcdef1234')

    def test_payload_is_short_and_without_secrets(self):
        self.assertEqual(self.cf.payload('o/r', 'buch/x', 'GW-ABCD'), 'GW1|o/r|buch/x|GW-ABCD')
        self.assertEqual(self.cf.payload('o/r', 'buch/x', 'GW-ABCD', 'ch-01'), 'GW1|o/r|buch/x|GW-ABCD|ch-01')

    def test_docx_has_properties_bookmarks_sections_and_footers(self):
        e = self.entry()
        out = self.tmp / 'out'
        files = self.cf.build(self.base, self.config, e, out, 'o/r', 'buch/x', 'abcdef1234', '2026-11-24', pdf=False)
        self.assertEqual(len(files), 1)
        self.assertIn(e['id'], files[0])
        path = out / files[0]
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            self.assertEqual(names.count('docProps/custom.xml'), 1)
            custom = z.read('docProps/custom.xml').decode()
            document = z.read('word/document.xml').decode()
            self.assertEqual(len([n for n in names if n.startswith('word/footer')]), 3)       # Titelblatt + 2 Kapitel
        self.assertIn('ghostwriter_checkout', custom)
        self.assertIn(e['id'], custom)
        self.assertEqual(document.count('<w:sectPr'), 3)
        mapping = json.loads(custom.split('ghostwriter_sections')[1].split('<vt:lpwstr>')[1].split('</vt:lpwstr>')[0]
                             .replace('&quot;', '"'))
        wanted = {s['id'] for c in self.config['structure']['chapters'][:2] for s in c['sections']}
        self.assertEqual(set(mapping.values()), wanted)
        for name in mapping:
            self.assertIn(f'w:name="{name}"', document)
        self.assertIn('PAGE', document + ''.join(zipfile.ZipFile(path).read(n).decode() for n in names if 'footer' in n))
        d = docx.Document(str(path))
        text = '\n'.join(p.text for p in d.paragraphs)
        self.assertIn('Zum Gegenlesen', text)
        self.assertIn(e['id'], text)
        self.assertIn('1.1 ', text)               # Abschnittsnummer in der Überschrift

    def test_only_the_area_is_in_the_file(self):
        e = self.entry('2')
        out = self.tmp / 'out'
        files = self.cf.build(self.base, self.config, e, out, 'o/r', 'b', 'c', '2026-11-24', pdf=False)
        import docx as dx
        text = '\n'.join(p.text for p in dx.Document(str(out / files[0])).paragraphs)
        self.assertIn(self.config['structure']['chapters'][1]['title'], text)
        self.assertNotIn(self.config['structure']['chapters'][0]['title'], text)

    def test_failed_build_leaves_no_entry(self):
        def boom(entry):
            raise ValueError('Bau gescheitert')
        with self.assertRaisesRegex(ValueError, 'Bau gescheitert'):
            checkout.start(self.base, self.config, 'Anna', '1', build=boom)
        self.assertEqual(checkout.load(self.base)['checkouts'], [])

    def test_start_with_out_records_files(self):
        out = self.tmp / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/checkout.py'), str(self.base), 'start', '--chapters', '1',
                            '--reader', 'Anna', '--out', str(out), '--no-pdf', '--repo', 'o/r', '--branch', 'buch/x'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        entry = checkout.load(self.base)['checkouts'][0]
        self.assertEqual(len(entry['dateien']), 1)
        self.assertTrue((out / entry['dateien'][0]).is_file())

    @unittest.skipUnless(shutil.which('soffice') and shutil.which('pdftotext'), 'LibreOffice und pdftotext nötig')
    def test_pdf_carries_the_id_on_every_page(self):
        e = self.entry()
        out = self.tmp / 'out'
        files = self.cf.build(self.base, self.config, e, out, 'o/r', 'buch/x', 'abcdef1234', '2026-11-24')
        pdf = out / next(f for f in files if f.endswith('.pdf'))
        pages = int(subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True).stdout.split('Pages:')[1].split()[0])
        self.assertGreater(pages, 2)
        for p in range(1, pages + 1):
            text = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), str(pdf), '-'], capture_output=True, text=True).stdout
            self.assertIn(e['id'], text, f'Seite {p}')

    @unittest.skipUnless(cv2 is not None and shutil.which('soffice') and shutil.which('pdftoppm'), 'OpenCV, LibreOffice, pdftoppm nötig')
    def test_qr_on_title_and_footer_can_be_decoded(self):
        e = self.entry()
        out = self.tmp / 'out'
        files = self.cf.build(self.base, self.config, e, out, 'o/r', 'buch/x', 'abcdef1234', '2026-11-24')
        pdf = out / next(f for f in files if f.endswith('.pdf'))
        det = cv2.QRCodeDetector()
        subprocess.run(['pdftoppm', '-r', '400', '-f', '1', '-l', '2', '-png', str(pdf), str(self.tmp / 'p')], check=True)
        title = cv2.imread(str(next(self.tmp.glob('p-01.png')) if list(self.tmp.glob('p-01.png')) else next(self.tmp.glob('p-1.png'))))
        self.assertEqual(det.detectAndDecode(title)[0], f'GW1|o/r|buch/x|{e["id"]}')
        page2 = cv2.imread(str(next(self.tmp.glob('p-02.png')) if list(self.tmp.glob('p-02.png')) else next(self.tmp.glob('p-2.png'))))
        h, w = page2.shape[:2]
        value = det.detectAndDecode(page2[int(h * 0.85):, :int(w * 0.4)])[0]
        self.assertEqual(value, f'GW1|o/r|buch/x|{e["id"]}|{self.config["structure"]["chapters"][0]["id"]}')


try:
    import docx  # noqa: F811
except ImportError:
    pass

if __name__ == '__main__':
    unittest.main()
