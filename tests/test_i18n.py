"""Sprachwahl, Ressourcenprüfung und lokalisierte Berichte ohne externe Schreibzugriffe."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from scripts import daily_summary as report, i18n


class LanguageTests(unittest.TestCase):
    def test_precedence_and_manuscript_independence(self):
        config = {'project': {'language': 'en'}, 'interface': {'language': 'de'}}
        self.assertEqual(i18n.resolve_language('en-GB', config, {'interface_language': 'de'}), 'en')
        self.assertEqual(i18n.resolve_language(None, config, {'interface_language': 'en'}), 'de')
        self.assertEqual(i18n.resolve_language(None, {'project': {'language': 'de'}}, {'interface_language': 'en'}), 'en')
        self.assertEqual(i18n.resolve_language(None, {'project': {'language': 'en'}}), 'de')
        self.assertEqual(i18n.resolve_language('fr', config, {'interface_language': 'en'}), 'de')
        self.assertEqual(i18n.normalize_language('EN_us'), 'en')

    def test_schema_remains_optional_and_validates_unknown_language(self):
        import yaml
        schema = json.loads(Path('schemas/ghostwriter.schema.json').read_text())
        config = yaml.safe_load(Path('ghostwriter.yml').read_text())
        validator = Draft202012Validator(schema)
        self.assertEqual(list(validator.iter_errors(config)), [])
        config['interface'] = {'language': 'en-GB'}
        self.assertEqual(list(validator.iter_errors(config)), [])
        config['interface']['language'] = 'fr'
        self.assertTrue(list(validator.iter_errors(config)))

    def test_catalog_parity_and_placeholders(self):
        self.assertEqual(i18n.validate_catalogs(), [])
        with tempfile.TemporaryDirectory() as folder:
            de = {'title': 'Bericht {day}'}
            en = {'extra': 'Extra', 'title': 'Report {date}'}
            for lang, data in [('de', de), ('en', en)]:
                (Path(folder) / (lang + '.json')).write_text(json.dumps(data))
            errors = '\n'.join(i18n.validate_catalogs(folder))
            self.assertIn('extra', errors)
            self.assertIn('title', errors)
            (Path(folder) / 'en.json').write_text('{}')
            self.assertIn('Übersetzung fehlt: title', '\n'.join(i18n.validate_catalogs(folder)))

    def test_english_report_preserves_dynamic_titles_and_identifiers(self):
        token = report.LANGUAGE.set('en')
        self.addCleanup(report.LANGUAGE.reset, token)
        pr = {'number': 4, 'title': 'Unveränderter deutscher Buchtitel', 'state': 'closed',
              'merged_at': True, 'updated_at': '2099-01-01'}
        with patch.object(report, '_pages', side_effect=[[pr], []]):
            lines = []
            report._pulls(lines, 'owner/book', '2026-01-01')
        text = '\n'.join(lines)
        self.assertIn('Decisions and open items', text)
        self.assertIn('merged', text)
        self.assertIn(pr['title'], text)
        self.assertIn('https://github.com/owner/book/pull/4', text)
        self.assertNotIn('Keine offenen', text)

    def test_english_delivery_and_cross_language_deduplication(self):
        token = report.LANGUAGE.set('en')
        self.addCleanup(report.LANGUAGE.reset, token)
        with patch.object(report, '_pages', return_value=[]), patch.object(report, '_api', side_effect=[{'number': 12}, {}]) as api:
            report.publish_daily_report('o/r', 'Book report', 'owner', '2026-11-06')
            self.assertEqual(api.call_args_list[0].kwargs['data']['title'], 'GhostWriter: daily update report')
            self.assertIn('Subscribe', api.call_args_list[0].kwargs['data']['body'])
            self.assertNotIn('Hier erscheint', api.call_args_list[0].kwargs['data']['body'])
            self.assertIn('Daily report 2026-11-06', api.call_args.kwargs['data']['body'])
        issue = {'number': 12, 'body': report.REPORT_ISSUE_MARKER, 'state': 'open'}
        with patch.object(report, '_pages', side_effect=[[issue], [{'body': '<!-- ghostwriter:daily-report:2026-11-06 -->'}]]), patch.object(report, '_api') as api:
            report.publish_daily_report('o/r', 'Report', 'owner', '2026-11-06')
            api.assert_not_called()

    def test_main_restores_language_after_call(self):
        with patch.object(report, '_git', return_value='interface_language: en'), patch.object(report, '_main') as main, patch.dict(os.environ, {}, clear=True):
            seen = []
            main.side_effect = lambda: seen.append(report.LANGUAGE.get())
            report.main()
            report.main('de')
            self.assertEqual(seen, ['en', 'de'])
            self.assertEqual(report.LANGUAGE.get(), 'de')


if __name__ == '__main__':
    unittest.main()
