"""#299: Ansicht „Alle Einstellungen“ mit Wert, Herkunft und Formular."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import settings_overview as so  # noqa: E402


class SettingsOverviewTest(unittest.TestCase):
    def test_every_setting_has_a_form_or_is_marked_file_only(self):
        """Neue Schema-Einstellung ohne Formular und ohne Vermerk „nur in der Datei“ fällt hier auf."""
        source = (ROOT / 'scripts/render_view.py').read_text(encoding='utf-8')
        keys = [k for k, _ in so.leaves()]
        self.assertGreater(len(keys), 80)
        for key in keys:
            with self.subTest(key=key):
                if so.form_for(key):
                    self.assertIn(so.form_for(key), so.FORM_NAMES)
                    self.assertRegex(source, re.escape(key.split('.')[1]),
                                     f'{key}: Formular {so.form_for(key)} nennt die Einstellung nicht; in FILE_ONLY aufnehmen')
                else:
                    self.assertTrue(key in so.FILE_ONLY or key.split('.')[0] not in so.GROUP_FORM, key)
        self.assertEqual(so.FILE_ONLY - set(keys), set(), 'FILE_ONLY nennt Einstellungen, die es nicht mehr gibt')

    def test_origin_book_library_default_unset(self):
        config = {'typesetting': {'font_size': 12, 'page_size': 'a5'}, 'project': {'title': 'T'}}
        profile = {'interface_language': 'en', 'voice': {'tone': 'warm'}}
        rows = {r['key']: r for r in so.rows(config, profile)}
        self.assertEqual((rows['typesetting.font_size']['origin'], rows['typesetting.font_size']['differs']), ('book', True))
        self.assertEqual((rows['typesetting.page_size']['origin'], rows['typesetting.page_size']['differs']), ('book', False))
        self.assertEqual((rows['typesetting.toc']['origin'], rows['typesetting.toc']['value']), ('default', True))
        self.assertEqual((rows['interface.language']['origin'], rows['interface.language']['value']), ('library', 'en'))
        self.assertEqual(rows['style.tone']['origin'], 'library')
        self.assertEqual(rows['publication.isbn_print']['origin'], 'unset')
        self.assertNotIn('structure', {r['group'] for r in rows.values()})
        self.assertEqual(rows['analysis.price_input_per_mtok']['form'], 'analysis-settings')
        self.assertIsNone(rows['images.max_px']['form'])

    def test_markdown_view_through_render_view(self):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(ROOT / 'tests/fixtures/adhs'),
                              'settings-overview', '--repo', 'x/y'], capture_output=True, text=True, check=True).stdout
        self.assertIn('### Alle Einstellungen', out)
        self.assertIn('| `typesetting.page_size` |', out)
        self.assertIn('nur in der Datei', out)
        self.assertNotIn('<script', out)


if __name__ == '__main__':
    unittest.main()
