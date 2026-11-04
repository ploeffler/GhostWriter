"""Tests für projektweite visuelle Referenzen."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reference_images  # noqa: E402
import validate_project  # noqa: E402
from test_cover import png  # noqa: E402


class ReferenceImageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.project = self.tmp / "book"
        shutil.copytree(ROOT / "tests/fixtures/adhs", self.project)
        self.source = self.tmp / "portrait.png"
        png(self.source, 120, 80)

    def add(self, **kwargs):
        values = dict(caption="Opi Referenz", description="Weißer Bart und grüner Hut",
                      purpose="Aussehen bei späteren Illustrationen beibehalten",
                      roles=["visual_reference"], origin="provided",
                      links=[{"kind": "person", "id": "char-opi"}], consent="Vom Benutzer zur Referenz freigegeben")
        values.update(kwargs)
        return reference_images.add(self.project, self.source, **values)

    def test_upload_is_not_automatically_approved(self):
        meta = self.add()
        self.assertEqual(meta["status"], "stored")
        with self.assertRaisesRegex(SystemExit, "nicht als visuelle Referenz freigegeben"):
            reference_images.select(self.project, [meta["id"]])

    def test_explicit_approval_enables_selection(self):
        meta = self.add()
        approved = reference_images.set_status(self.project, meta["id"], "approved")
        selected = reference_images.select(self.project, [meta["id"]])
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(selected[0]["id"], meta["id"])
        self.assertTrue(Path(selected[0]["file"]).is_file())

    def test_withdrawal_blocks_new_selection_but_keeps_history(self):
        meta = self.add()
        reference_images.set_status(self.project, meta["id"], "approved")
        reference_images.set_status(self.project, meta["id"], "withdrawn")
        with self.assertRaisesRegex(SystemExit, "nicht als visuelle Referenz freigegeben"):
            reference_images.select(self.project, [meta["id"]])
        self.assertIn(meta["id"], reference_images.all_references(self.project))

    def test_project_wide_registry_and_multiple_links(self):
        meta = self.add(links=[{"kind": "person", "id": "char-opi"},
                               {"kind": "scene", "id": "szene-hafen"}])
        stored = reference_images.all_references(self.project)[meta["id"]][0]
        self.assertEqual(len(stored["links"]), 2)
        self.assertTrue((self.project / "reference-images" / meta["file"]).is_file())

    def test_project_validation_checks_reference_metadata_and_file(self):
        self.add(links=[{"kind": "scene", "id": "szene-hafen"}])
        self.assertEqual(validate_project.check_project(self.project), [])

    def test_duplicate_captions_get_unique_ids(self):
        first = self.add()
        second = self.add()
        self.assertNotEqual(first["id"], second["id"])


if __name__ == "__main__":
    unittest.main()
