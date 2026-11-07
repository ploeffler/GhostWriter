"""Doku-Abgleich: die Prüfung selbst läuft und findet nichts (ohne ghostwriter-ui)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_docs
import build_start


class CheckDocsTest(unittest.TestCase):
    def test_data_model_runs_links(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/check_docs.py')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class GeneratedStartTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ui = self.root / 'ui'
        self.write('ui/templates/test.html', '<button data-a="section.update">')
        self.write('templates/ui/BEFUELLUNG.md', '| `section.update` | `PATCH /v1/example` |\n')
        self.write('docs/API-CONTRACT.md', '`/v1/example`\n')
        self.write('templates/branding.yml', 'credit:\n  text: Beispielhinweis\n')
        self.root_patch = patch.object(check_docs, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def test_generated_start_checks_actions_in_modules(self):
        self.write('START.md', check_docs.GENERATED_START_MARKER + '\nEinstieg\n')
        self.write('docs/start/schreiben-ins-repository.md', 'Ablauf `section.update`\n')
        problems = []
        check_docs.check_actions(self.ui, problems)
        self.assertEqual(problems, [])
        self.write('docs/start/schreiben-ins-repository.md', 'Aktion fehlt\n')
        check_docs.check_actions(self.ui, problems)
        self.assertTrue(any('section.update' in message for message in problems))

    def test_real_generated_starts_preserve_action_checks(self):
        source = (ROOT / 'START.md').read_text(encoding='utf-8')
        table = (ROOT / 'templates/ui/BEFUELLUNG.md').read_text(encoding='utf-8')
        api = (ROOT / 'docs/API-CONTRACT.md').read_text(encoding='utf-8')
        self.write('templates/ui/BEFUELLUNG.md', table)
        self.write('docs/API-CONTRACT.md', api)
        buttons = '\n'.join(f'<button data-a="{name}">'
                            for name in check_docs.action_table(table))
        self.write('ui/templates/test.html', buttons)
        self.write('START.md', source)
        canonical = []
        check_docs.check_actions(self.ui, canonical)
        for language in ('de', 'en'):
            with self.subTest(language=language):
                template = (ROOT / f'templates/start/{language}.md').read_text(encoding='utf-8')
                outputs = build_start.render(source, template, repo='owner/books',
                                             branch='buch/test', default_branch='main', config={})
                for name, content in outputs.items():
                    self.write(name, content)
                problems = []
                check_docs.check_actions(self.ui, problems)
                self.assertEqual(problems, canonical)

    def test_missing_generated_write_instructions_are_reported(self):
        self.write('START.md', check_docs.GENERATED_START_MARKER + '\nEinstieg\n')
        problems = []
        check_docs.check_actions(self.ui, problems)
        self.assertTrue(any('schreiben-ins-repository.md fehlt' in message for message in problems))

    def test_full_start_still_requires_actions(self):
        self.write('START.md', '# Vollständige Anleitung\n')
        self.write('docs/start/schreiben-ins-repository.md', '`section.update`\n')
        problems = []
        check_docs.check_actions(self.ui, problems)
        self.assertTrue(any('section.update' in message for message in problems))

    def test_credit_exemption_applies_only_to_generated_start(self):
        self.write('START.md', check_docs.GENERATED_START_MARKER + '\nEinstieg\n')
        self.write('README.md', '# Ohne Fußzeile\n')
        with patch.object(check_docs, 'DOCS', ['START.md', 'README.md']):
            problems = []
            check_docs.check_credit(problems)
            self.assertFalse(any('START.md' in message for message in problems))
            self.assertTrue(any('README.md' in message for message in problems))
            self.write('START.md', '# Vollständige Anleitung\n')
            problems = []
            check_docs.check_credit(problems)
            self.assertTrue(any('START.md' in message for message in problems))


if __name__ == '__main__':
    unittest.main()
