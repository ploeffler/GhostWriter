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

    def test_library_series_omnibus_and_sections(self):
        """Teil 2: Bibliothek, Serie, Sammelband, Abweichungen je Abschnitt, Englisch."""
        import shutil
        import tempfile
        import types
        from unittest.mock import patch
        import yaml
        rows = {r['key']: r for r in so.profile_rows({'display': 'erweitert', 'git': {'name': 'a'}, 'answer_backup': 'hintergrund'})}
        self.assertEqual((rows['display']['origin'], rows['display']['differs'], rows['display']['form']), ('own', True, 'display'))
        self.assertEqual(rows['answers']['origin'], 'default')
        self.assertIn('answer_backup', rows)
        self.assertNotIn('skill', rows)
        fake = types.SimpleNamespace(get=lambda base, sid: ({'id': 'ser-a', 'title': 'Reihe', 'issn': '1234-5678'}, None),
                                     omnibus=lambda base, sid: {'title': 'Sammelband A', 'typesetting': {'font_size': 10},
                                                                'publication': {'publisher': 'V'}})
        with patch.dict(sys.modules, {'series': fake}):
            kind, title, data = so.page(Path('.'), {}, {}, 'serie ser-a')
            self.assertEqual((kind, {r['key']: r['origin'] for r in data}['issn']), ('series', 'own'))
            kind, title, data = so.page(Path('.'), {}, {}, 'sammelband ser-a')
            data = {r['key']: r for r in data}
            self.assertEqual((data['typesetting.font_size']['origin'], data['typesetting.font_size']['differs']), ('omnibus', True))
            self.assertEqual(data['typesetting.toc']['origin'], 'default')
            self.assertEqual(data['publication.publisher']['origin'], 'omnibus')
        rows = {r['key']: r for r in so.rows({'_series': {'title': 'Reihe', 'volume': 2}})}
        self.assertEqual((rows['series.volume']['value'], rows['series.volume']['origin']), (2, 'series'))
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / 'buch'
            shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
            config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
            section = config['structure']['chapters'][0]['sections'][0]
            path = base / section['path']
            text = path.read_text(encoding='utf-8')
            path.write_text(re.sub(r'(?m)^fact_check:.*$', 'fact_check: requested', text, count=1)
                            if re.search(r'(?m)^fact_check:', text) else text.replace('---\n', '---\nfact_check: requested\n', 1),
                            encoding='utf-8')
            sections = so.section_rows(base, config)
            self.assertEqual([(r['key'], r['value']) for r in sections], [('1.1', 'requested')])
            out = so.markdown(base, config, {}, None, 'en')
            self.assertIn('#### Different from the book', out)
            self.assertIn('| Setting | Value | Origin | Change in |', out)
            values, blocks = so.widget_values(base, config, {}, None, 'de')
            self.assertEqual(values['SETTINGS_KIND'], 'book')
            self.assertEqual(blocks['GROUPS'][-1]['G_KEY'], 'sections')

    def test_markdown_view_through_render_view(self):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(ROOT / 'tests/fixtures/adhs'),
                              'settings-overview', '--repo', 'x/y', '--text'], capture_output=True, text=True, check=True).stdout
        self.assertIn('### Alle Einstellungen', out)
        self.assertIn('| `typesetting.page_size` |', out)
        self.assertIn('nur in der Datei', out)
        self.assertNotIn('<script', out)
        widget = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(ROOT / 'tests/fixtures/adhs'),
                                 'settings-overview', '--repo', 'x/y'], capture_output=True, text=True, check=True).stdout
        self.assertIn('GW.render("einstellungen"', widget)


if __name__ == '__main__':
    unittest.main()
