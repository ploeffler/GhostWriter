"""#498: Textfassungen enthalten kein HTML wie <sub>, das Chats roh anzeigen."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / 'tests/fixtures/adhs'
sys.path.insert(0, str(ROOT / 'scripts'))


class TextOutputMarkdownTest(unittest.TestCase):
    def run_view(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(BOOK), *args, '--repo', 'x/y', '--text'],
                              capture_output=True, text=True, check=True).stdout

    def test_text_views_without_sub_tags(self):
        for args in (['project'], ['chapter', '1'], ['section', '1.1'], ['project-settings'], ['analysis-settings'],
                     ['ai-disclosure'], ['project', '--language', 'en'], ['chapter', '1', '--language', 'en']):
            with self.subTest(args=args):
                out = self.run_view(*args)
                self.assertNotRegex(out, r'</?sub>', args)

    def test_no_sub_tag_left_in_text_renderers(self):
        for name in ('render_view.py', 'render_view_en.py'):
            code = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
            code = re.sub(r'"""[\s\S]*?"""', '', code)   # Docstrings nennen das alte Tag
            self.assertNotIn('<sub>', code, name)

    def test_small_is_markdown(self):
        import render_view
        self.assertEqual(render_view.small('Entwickelt mit Claude'), '_Entwickelt mit Claude_')
        self.assertEqual(render_view.small('Datei `x_y`'), 'Datei `x_y`')   # kein kaputtes Kursiv


if __name__ == '__main__':
    unittest.main()
