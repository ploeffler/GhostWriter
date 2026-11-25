"""Material einbringen: Colorieren über colorize.py, Programmgrenzen bleiben (#574, #452)."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import colorize  # noqa: E402
import material  # noqa: E402
from test_colorize import gray, tinted  # noqa: E402


class MaterialColorizeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'b'
        self.base.mkdir()
        self.upload = Path(tmp.name) / 'u.jpg'
        gray().save(self.upload, quality=92)

    def folder(self, art='foto', minors=False, name='Paar'):
        f = material.add(self.base, self.upload, art, name, '2026-11-25', minors=minors)
        gray().save(f / 'bearbeitet.jpg', quality=92)     # wie nach `material.py prepare`
        meta = material.read(f)
        meta['bearbeitet'] = 'bearbeitet.jpg'
        material.write(f, meta)
        return f

    def proposal(self):
        path = self.base.parent / 'vorschlag.png'
        tinted(gray()).save(path)
        return path

    def run_cli(self, folder, *extra):
        return material.main([str(self.base), 'colorize', str(folder.relative_to(self.base)), *extra])

    def test_photo_is_colorized_from_the_prepared_image_and_entry_goes_to_material_yml(self):
        f = self.folder()
        self.assertEqual(self.run_cli(f, '--proposal', str(self.proposal()), '--tool', 'Testdienst'), 0)
        out = np.asarray(Image.open(f / 'coloriert.jpg').convert('RGB'))
        self.assertGreater(float(np.abs(out[..., 0].astype(int) - out[..., 2].astype(int)).mean()), 5)   # Farbe ist da
        meta = yaml.safe_load((f / 'material.yml').read_text(encoding='utf-8'))
        self.assertTrue(any('Farbkanäle' in str(x) for x in meta['bearbeitung']), meta['bearbeitung'])
        self.assertFalse((f / 'bild.yml').exists())
        row = material.listing(self.base).split('\n')[4]
        self.assertEqual(row.split(' | ')[5], 'ja')   # Spalte „Coloriert“

    def test_check_uses_the_same_locks(self):
        self.assertEqual(self.run_cli(self.folder(), '--check'), 0)
        doc = material.add(self.base, self.upload, 'dokument', 'Urkunde', '2026-11-25')
        gray().save(doc / 'bearbeitet.jpg')
        self.assertEqual(self.run_cli(doc, '--check'), 1)        # Dokumente nie
        kids = self.folder('foto', minors=True, name='Kinder')
        self.assertEqual(self.run_cli(kids, '--proposal', str(self.proposal()), '--tool', 'x'), 1)   # Minderjährige nie ohne Ausnahme
        self.assertFalse((kids / 'coloriert.jpg').exists())

    def test_bild_yml_folders_still_work(self):
        folder = self.base / 'quellen' / 'bilder' / 'x'
        folder.mkdir(parents=True)
        gray().save(folder / 'aufbereitet.jpg', quality=92)
        (folder / 'bild.yml').write_text('art: foto\nminderjaehrige: false\nbearbeitung: []\n', encoding='utf-8')
        self.assertEqual(colorize.meta_path(folder).name, 'bild.yml')
        r = colorize.colorize(self.base, 'quellen/bilder/x', proposal=str(self.proposal()), tool='T')
        self.assertTrue((self.base / r['target']).is_file())


if __name__ == '__main__':
    unittest.main()
