from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_docs_wiki as wiki


class WikiBuildTests(unittest.TestCase):
    def test_build_and_stale_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'wiki'
            wiki.build(output)
            self.assertEqual(len(list(output.glob('*.md'))), 43)
            guide = next(p for p in wiki.config(ROOT)['pages'] if p['id'] == 'guide')
            self.assertIn('[English](' + wiki.page_link(guide, 'en') + ')',
                          (output/(wiki.slug(guide, 'de')+'.md')).read_text())
            self.assertFalse((output/'assets').exists())
            import json
            info = json.loads((output/'build-info.json').read_text())
            info['version'] = 'invalid'
            (output/'build-info.json').write_text(json.dumps(info))
            with self.assertRaisesRegex(ValueError, 'Veraltete Version'):
                wiki.check(output)

    def test_titles_links_and_single_global_credits(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'wiki'
            wiki.build(output)
            settings = next(p for p in wiki.config(ROOT)['pages'] if p['id'] == 'settings')
            self.assertEqual(wiki.slug(settings, 'de'), 'Einstellungen-und-Ausgabe')
            self.assertEqual(wiki.slug(settings, 'en'), 'Settings-and-output')
            self.assertFalse(list(output.glob('de-*.md')))
            self.assertFalse(list(output.glob('en-*.md')))
            for path in output.glob('*.md'):
                text = path.read_text()
                self.assertEqual(text.count('Developed with support from Claude (Anthropic)'), 1 if path.name == '_Footer.md' else 0)
                self.assertEqual(text.count('Developed with support from Codex (OpenAI)'), 1 if path.name == '_Footer.md' else 0)
            footer = (output/'_Footer.md').read_text()
            self.assertEqual(footer.count('Claude (Anthropic)'), 1)
            self.assertEqual(footer.count('Codex (OpenAI)'), 1)
            self.assertNotIn('Entwickelt mit Unterstützung', footer)
            self.assertIn('[↗](https://claude.ai "Claude")', footer)
            self.assertIn('[↗](https://openai.com/codex/ "Codex")', footer)
            # A reintroduced duplicate must fail validation.
            home = output/'Home.md'
            home.write_text(home.read_text() + '\nEntwickelt mit Unterstützung von Codex (OpenAI)\n')
            with self.assertRaisesRegex(ValueError, 'KI-Hinweis'):
                wiki.check(output)

    def test_foreign_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output/'keep.md').write_text('keep')
            with self.assertRaises(ValueError):
                wiki.build(output)
            self.assertEqual((output/'keep.md').read_text(), 'keep')

    def test_missing_page_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'wiki'
            wiki.build(output)
            guide = next(p for p in wiki.config(ROOT)['pages'] if p['id'] == 'guide')
            (output/(wiki.slug(guide, 'en')+'.md')).unlink()
            with self.assertRaisesRegex(ValueError, 'Seitenauswahl'):
                wiki.check(output)
