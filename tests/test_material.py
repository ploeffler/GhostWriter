"""Material einbringen (#574)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import material  # noqa: E402

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None


def skewed_page(path):
    """Helles Blatt mit Text, schräg auf dunklem Tisch, Ecken ungleichmäßig beleuchtet."""
    img = np.full((900, 1200, 3), 40, dtype='uint8')
    page = np.full((600, 420, 3), 235, dtype='uint8')
    for k in range(8):
        cv2.putText(page, f'Zeile {k} Text', (30, 70 + k * 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    src = np.float32([[0, 0], [419, 0], [419, 599], [0, 599]])
    dst = np.float32([[300, 120], [800, 160], [830, 800], [260, 760]])
    warped = cv2.warpPerspective(page, cv2.getPerspectiveTransform(src, dst), (1200, 900))
    mask = cv2.warpPerspective(np.full(page.shape[:2], 255, 'uint8'), cv2.getPerspectiveTransform(src, dst), (1200, 900))
    img[mask > 0] = warped[mask > 0]
    shade = np.tile(np.linspace(0.6, 1.0, 1200, dtype='float32'), (900, 1))[..., None]
    cv2.imwrite(str(path), np.clip(img * shade, 0, 255).astype('uint8'))


class MaterialTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        self.base.mkdir()
        self.upload = Path(tmp.name) / 'Foto 1.JPG'
        self.upload.write_bytes(b'\xff\xd8original-bytes')

    def test_add_keeps_original_unchanged_and_never_overwrites(self):
        f = material.add(self.base, self.upload, 'foto', 'Familie am See', '2026-11-24')
        self.assertEqual(f.name, '2026-11-24-familie-am-see')
        self.assertEqual((f / 'original.jpg').read_bytes(), self.upload.read_bytes())
        meta = material.read(f)
        self.assertEqual((meta['art'], meta['minderjaehrige'], meta['personen']), ('foto', False, []))
        with self.assertRaisesRegex(ValueError, 'gibt es schon'):
            material.add(self.base, self.upload, 'foto', 'Familie am See', '2026-11-24')
        with self.assertRaises(ValueError):
            material.add(self.base, self.upload, 'film', 'x')
        self.assertFalse(material.problems(self.base))

    def test_external_limits(self):
        self.assertFalse(material.external_allowed({'art': 'foto', 'minderjaehrige': True})[0])
        self.assertFalse(material.external_allowed({'art': 'foto'})[0])                 # unklar = nein
        self.assertFalse(material.external_allowed({'art': 'dokument', 'minderjaehrige': False})[0])
        self.assertTrue(material.external_allowed({'art': 'foto', 'minderjaehrige': False})[0])

    def test_problems_report_missing_files_and_schema(self):
        f = material.add(self.base, self.upload, 'dokument', 'Urkunde', '2026-11-24')
        (f / 'original.jpg').unlink()
        self.assertTrue(any('original' in e for e in material.problems(self.base)))
        data = material.read(f)
        data['art'] = 'quatsch'
        material.write(f, data)
        self.assertTrue(any('art' in e for e in material.problems(self.base)))

    def test_listing(self):
        material.add(self.base, self.upload, 'foto', 'A', '2026-11-24', minors=True)
        text = material.listing(self.base)
        self.assertIn('2026-11-24-a', text)
        self.assertIn('| ja |', text)

    @unittest.skipIf(cv2 is None, 'OpenCV nötig')
    def test_prepare_straightens_and_mark_draws_legend(self):
        page = self.base.parent / 'seite.jpg'
        skewed_page(page)
        f = material.add(self.base, page, 'foto-vom-foto', 'Seite', '2026-11-24')
        original = (f / 'original.jpg').read_bytes()
        steps = material.prepare(f)
        self.assertTrue(any('gerade' in s for s in steps))
        self.assertEqual((f / 'original.jpg').read_bytes(), original)                 # Original unverändert
        out = cv2.imread(str(f / 'bearbeitet.jpg'))
        h, w = out.shape[:2]
        self.assertTrue(1.1 < h / w < 1.8, h / w)                                     # Hochformat wie das Blatt
        for corner in (out[:20, :20], out[:20, -20:], out[-20:, :20], out[-20:, -20:]):
            self.assertGreater(float(corner.mean()), 150)                             # Ecken hell: kein dunkler Tisch mehr
        items = [{'nr': 1, 'name': 'Oma', 'rahmen': [10, 10, 80, 80], 'sicher': 'ja', 'quelle': 'Autor'},
                 {'nr': 2, 'rahmen': [120, 40, 60, 60], 'sicher': 'unbekannt'}]
        marked = cv2.imread(str(material.mark(f, items)))
        self.assertGreater(marked.shape[0], h)                                        # Legende unten angehängt
        meta = material.read(f)
        self.assertEqual([p['nr'] for p in meta['personen']], [1, 2])
        self.assertFalse(material.problems(self.base))

    def test_cli(self):
        def run(*a):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/material.py'), str(self.base), *a], capture_output=True, text=True)
        r = run('add', str(self.upload), '--art', 'foto', '--name', 'Test', '--date', '2026-11-24', '--minors')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Test', run('list').stdout)
        self.assertEqual(run('list', '--write').returncode, 0)
        self.assertTrue((self.base / 'quellen/verzeichnis.md').is_file())


if __name__ == '__main__':
    unittest.main()
