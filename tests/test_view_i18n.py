"""Verträge für die sprachgleichen Freigabe- und Formulartexte."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import view_i18n


class ViewTranslationTest(unittest.TestCase):
    def test_catalogs_and_consumers_match(self):
        self.assertEqual(view_i18n.validate_resources(), [])

    def test_user_data_is_formatted_once_and_unknown_language_falls_back(self):
        title = 'Beschreibung {p_a} {{chapter}} <b>'
        self.assertEqual(view_i18n.translate('image', 'en-GB', p_a=title), 'Image “' + title + '”')
        self.assertEqual(view_i18n.translate('image', 'fr', p_a=title), 'Bild „' + title + '“')

    def test_missing_unused_empty_and_mismatched_fields_are_rejected(self):
        originals = {language: json.loads((view_i18n.RESOURCE / (language + '.json')).read_text()) for language in ('de', 'en')}
        for change in ('missing', 'unused', 'empty', 'fields'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                resources = {language: dict(texts) for language, texts in originals.items()}
                if change == 'missing':
                    resources['en'].pop('image')
                elif change == 'unused':
                    for texts in resources.values():
                        texts['unused'] = 'unused'
                elif change == 'empty':
                    resources['en']['image'] = ''
                else:
                    resources['en']['image'] = 'Image {other}'
                for language, texts in resources.items():
                    Path(folder, language + '.json').write_text(json.dumps(texts))
                with patch.object(view_i18n, 'RESOURCE', Path(folder)):
                    self.assertTrue(view_i18n.validate_resources())
