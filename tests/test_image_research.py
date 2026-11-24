"""#218 (D15, A05): Bildkandidaten mit Quelle, Urheber, Lizenz; Übernahme nur nach Bestätigung."""
from tests.authority_helpers import fake_github

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import image_research  # noqa: E402
import reference_images  # noqa: E402
from tests.test_cover import png  # noqa: E402


class ImageResearchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'book'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        self.file = self.tmp / 'bild.png'
        png(self.file, 120, 80)
        fake_github(self, self.base, seal=False)

    def clear(self):
        return image_research.propose(self.base, 'Hafen 1930', 'https://example.org/hafen.jpg',
                                      page='https://example.org/hafen', author='A. Fotograf', license_info='CC BY 4.0',
                                      links=[{'kind': 'place', 'id': 'hafen'}])

    def test_candidate_documents_source_and_flags_unclear_rights(self):
        ok = self.clear()
        self.assertEqual(ok['rights'], 'clear')
        unclear = image_research.propose(self.base, 'Ohne Lizenz', 'https://example.org/x.jpg', author='B')
        self.assertEqual(unclear['rights'], 'unclear')
        self.assertEqual([i['id'] for i in image_research.load_all(self.base)], ['cand-001', 'cand-002'])
        self.assertIn('RECHTE UNGEKLÄRT', image_research.line(unclear))
        self.assertFalse((self.base / 'reference-images').exists())   # Kandidat ist kein gespeichertes Bild
        with self.assertRaises(ValueError):
            image_research.propose(self.base, 'x', 'ftp://example.org/x.jpg')

    def test_adopt_needs_confirmation_and_stays_unapproved(self):
        c = self.clear()
        with self.assertRaisesRegex(ValueError, 'abgebrochen'):
            image_research.adopt(self.base, c['id'], self.file)
        self.assertEqual(image_research.load_all(self.base)[0]['status'], 'candidate')
        self.assertFalse((self.base / 'reference-images').exists())
        item, meta = image_research.adopt(self.base, c['id'], self.file, confirm=True)
        self.assertEqual(meta['status'], 'stored')
        self.assertEqual(meta['origin'], 'licensed')
        self.assertIn('CC BY 4.0', meta['license'])
        self.assertIn('A. Fotograf', meta['description'])
        self.assertEqual(meta['links'], [{'kind': 'place', 'id': 'hafen'}])
        self.assertEqual(item['adopted_as'], meta['id'])
        with self.assertRaises(SystemExit):           # nicht freigegeben, also nicht auswählbar
            reference_images.select(self.base, [meta['id']])
        with self.assertRaises(ValueError):
            image_research.adopt(self.base, c['id'], self.file, confirm=True)

    def test_unclear_rights_need_extra_consent_and_stay_unknown(self):
        c = image_research.propose(self.base, 'Unklar', 'https://example.org/u.jpg')
        with self.assertRaisesRegex(ValueError, 'ungeklärt'):
            image_research.adopt(self.base, c['id'], self.file, confirm=True)
        _, meta = image_research.adopt(self.base, c['id'], self.file, confirm=True, accept_unclear=True)
        self.assertEqual(meta['origin'], 'unknown')
        self.assertEqual(meta['license'], 'ungeklärt')

    def test_reject_and_cli(self):
        c = self.clear()
        image_research.reject(self.base, c['id'], 'passt nicht')
        self.assertEqual(image_research.load_all(self.base)[0]['status'], 'rejected')
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/image_research.py'), str(self.base), 'adopt', c['id'],
                              '--file', str(self.file), '--confirm'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/image_research.py'), str(self.base), 'list'],
                             capture_output=True, text=True)
        self.assertIn('rejected', out.stdout)
        data = yaml.safe_load((self.base / 'research/images/candidates.yml').read_text(encoding='utf-8'))
        self.assertEqual(data['candidates'][0]['reason'], 'passt nicht')


if __name__ == '__main__':
    unittest.main()
