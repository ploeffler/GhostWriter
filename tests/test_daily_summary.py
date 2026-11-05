import unittest

from scripts.daily_summary import content_paths, is_content_file


class DailySummaryTests(unittest.TestCase):
    def test_only_book_content_roots_are_counted(self):
        manifest = {"book": ["chapters/", "matter/", "research/", "ghostwriter.yml", "costs/"]}
        self.assertEqual(content_paths(manifest), ["chapters/", "matter/", "research/"])

    def test_program_and_status_files_are_excluded(self):
        paths = content_paths({"book": ["chapters/", "matter/", "research/"]})
        self.assertTrue(is_content_file("chapters/01/section.md", paths))
        self.assertTrue(is_content_file("matter/prologue.md", paths))
        self.assertFalse(is_content_file("scripts/update_from_upstream.py", paths))
        self.assertFalse(is_content_file(".ghostwriter/update.yml", paths))
        self.assertFalse(is_content_file("ghostwriter.yml", paths))


if __name__ == "__main__":
    unittest.main()
