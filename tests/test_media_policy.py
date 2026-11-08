"""Uploadgrenzen, Bestätigungen und unveränderte Originale (D13)."""
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import images
import media_policy
import reference_images
import validate_project


class MediaPolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.book = self.root / 'book'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.book)
        self.source = self.root / 'upload.png'
        Image.new('RGB', (1200, 800), 'red').save(self.source)

    def add(self, **kwargs):
        return images.add(self.book, '1.1', self.source, 'Testbild', source='own', **kwargs)

    def snapshot(self):
        return {p.relative_to(self.book): p.read_bytes() for p in self.book.rglob('*') if p.is_file()}

    def small_limit(self):
        p = self.book / 'ghostwriter.yml'
        p.write_text(p.read_text() + '\nimages:\n  max_px: 600\n')

    def test_resize_requires_confirmation_and_leaves_no_partial_files(self):
        self.small_limit()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Verkleinerung ausdrücklich'):
            self.add()
        self.assertEqual(before, self.snapshot())

    def test_confirmed_resize_keeps_original_bytes_and_separate_book_copy(self):
        self.small_limit()
        original = self.source.read_bytes()
        meta, folder = self.add(confirm_resize=True)
        self.assertEqual((self.book / folder / meta['original_file']).read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(meta['original_sha256'], hashlib.sha256(original).hexdigest())
        self.assertNotEqual(meta['original_file'], meta['file'])
        with Image.open(self.book / folder / meta['file']) as image:
            self.assertEqual(max(image.size), 600)
        self.assertEqual(validate_project.check_project(self.book), [])

    def test_small_image_is_stored_without_reencoding(self):
        meta, folder = self.add()
        self.assertEqual(meta['original_file'], meta['file'])
        self.assertEqual((self.book / folder / meta['file']).read_bytes(), self.source.read_bytes())

    def test_oversize_rejected_before_writing(self):
        with self.source.open('r+b') as f:
            f.truncate(media_policy.MAX_UPLOAD_BYTES + 1)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, '20 MB'):
            self.add()
        self.assertEqual(before, self.snapshot())

    def test_collection_warning_counts_original_and_derivative(self):
        self.small_limit()
        with patch.object(media_policy, 'BOOK_WARNING_BYTES', len(self.source.read_bytes()) + 1):
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, '500 MB'):
                self.add(confirm_resize=True)
            self.assertEqual(before, self.snapshot())
            meta, folder = self.add(confirm_resize=True, confirm_large_collection=True)
        expected = sum((self.book / folder / name).stat().st_size for name in (meta['file'], meta['original_file']))
        self.assertEqual(media_policy.stored_image_bytes(self.book), expected)

    def test_reference_upload_obeys_same_collection_limit_and_keeps_original(self):
        with patch.object(media_policy, 'BOOK_WARNING_BYTES', 1):
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, '500 MB'):
                reference_images.add(self.book, self.source, 'Referenz')
            self.assertEqual(before, self.snapshot())
            meta = reference_images.add(self.book, self.source, 'Referenz', confirm_large_collection=True)
        self.assertEqual((self.book / 'reference-images' / meta['file']).read_bytes(), self.source.read_bytes())
        self.assertEqual(meta['status'], 'stored')

    def test_corrupt_image_rejected_before_writing(self):
        self.source.write_bytes(b'not an image')
        before = self.snapshot()
        with self.assertRaises(OSError):
            self.add()
        self.assertEqual(before, self.snapshot())

    def test_symlink_media_root_is_unknown_not_zero_or_writable(self):
        (self.book / 'reference-images').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symbolischer Link'):
            self.add()
        self.assertFalse((self.book / 'chapters/01-endlich-eine-erklaerung/images').exists())

    def test_shared_hardlink_counted_once_and_program_assets_excluded(self):
        folder = self.book / 'reference-images'
        folder.mkdir()
        shutil.copyfile(self.source, folder / 'one.png')
        os.link(folder / 'one.png', folder / 'two.png')
        (self.book / 'assets').mkdir()
        shutil.copyfile(self.source, self.book / 'assets/program.png')
        self.assertEqual(media_policy.stored_image_bytes(self.book), self.source.stat().st_size)

    def test_changed_or_missing_original_fails_project_validation(self):
        self.small_limit()
        meta, folder = self.add(confirm_resize=True)
        original = self.book / folder / meta['original_file']
        original.write_bytes(b'veraendert')
        self.assertTrue(any('Original-Fingerabdruck' in e for e in validate_project.check_project(self.book)))
        original.unlink()
        self.assertTrue(any('Originaldatei fehlt' in e for e in validate_project.check_project(self.book)))

    def test_orphan_file_is_preserved_instead_of_overwritten(self):
        from render_view import load
        folder = self.book / images.find_target(load(self.book)[1], '1.1')[1]
        folder.mkdir(parents=True)
        orphan = folder / 'img-testbild.png'
        orphan.write_bytes(b'Nicht ueberschreiben')
        meta, _ = self.add()
        self.assertEqual(orphan.read_bytes(), b'Nicht ueberschreiben')
        self.assertEqual(meta['id'], 'img-testbild-2')


if __name__ == '__main__':
    unittest.main()
