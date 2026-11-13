"""Kurzer Instanz-Einstieg: Inhalt, Kontext und atomarer Update-Lauf (#178)."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_start
import update_from_upstream as update

SOURCE = (ROOT / 'START.md').read_text(encoding='utf-8')
TEMPLATE = (ROOT / 'templates/start/de.md').read_text(encoding='utf-8')


class StartContentTest(unittest.TestCase):
    def render(self, **kw):
        args = dict(repo='owner/books', branch='main', default_branch='main', config={})
        args.update(kw)
        return build_start.render(SOURCE, TEMPLATE, **args)

    def test_setup_resume_and_library_are_distinct(self):
        self.assertIn('`setup`', self.render()['START.md'])
        self.assertIn('`resume`', self.render(profile={'repo': 'owner/books'})['START.md'])
        book = self.render(branch='buch/neu', profile={'repo': 'owner/books'})['START.md']
        self.assertIn('`book`', book)
        self.assertIn('`setup`', book, 'Bibliotheksprofil schließt einen neuen Buch-Wizard nicht ab')
        self.assertIn('`resume`', self.render(branch='buch/neu', config={'workflow': {'current_phase': 'writing'}})['START.md'])
        self.assertIn('`resume`', self.render(library_present=True)['START.md'])

    def test_customization_and_safeguards_without_full_source(self):
        profile = {'repo': 'owner/books', 'startup': {'client': 'openwebui',
                   'tools': {'read_start': 'read_start_md', 'read_file': 'read_file'}}}
        outputs = self.render(profile=profile)
        text = outputs['START.md']
        self.assertLess(len(text), 6500)
        self.assertLess(len(text), len(SOURCE) // 5)
        for required in ('owner/books', 'read_start_md', 'openwebui', 'Bibliothek', 'Übersicht',
                         'nicht bei jeder Nachricht', 'Head-SHA', 'ausdrücklicher Bestätigung'):
            self.assertIn(required, text)
        self.assertNotIn('chillyconcane', text)
        self.assertNotIn('GITHUB_TOKEN', text)
        self.assertEqual(outputs, self.render(profile=profile))
        for link in re.findall(r'\]\((docs/start/[^)]+)\)', text):
            self.assertIn(link, outputs)
        self.assertIn('genau einen', outputs['docs/start/schreiben-ins-repository.md'])
        self.assertIn('../../docs/ARBEITSABLAEUFE.md', outputs['docs/start/schreiben-ins-repository.md'])
        # Alle Quellabschnitte bleiben vollständig erhalten, auch der letzte.
        self.assertEqual(len(outputs), len(build_start.sections(SOURCE)) + 2)
        self.assertIn('was noch ungeprüft oder unsicher ist', '\n'.join(outputs.values()))

    def test_openwebui_start_has_only_rules_that_apply_there(self):
        for language in ('de', 'en'):
            with self.subTest(language=language):
                main_name, openwebui_name = build_start.template_names(language)
                outputs = build_start.render(
                    SOURCE, (ROOT / main_name).read_text(encoding='utf-8'), repo='owner/books', branch='main',
                    default_branch='main', config={'interface': {'language': language}},
                    openwebui_template=(ROOT / openwebui_name).read_text(encoding='utf-8'))
                text = outputs[build_start.OPENWEBUI]
                self.assertIn(build_start.MARKER, text)
                self.assertIn('owner/books', text)
                # Klein genug für MAX_START_BYTES (16 KB) und deutlich kürzer als START.md.
                self.assertLess(len(text.encode('utf-8')), 6000)
                self.assertLess(len(text), len(outputs['START.md']))
                for absent in ('render_view', 'Widget-', '](', 'Head-SHA', 'commit', 'assistant.yml', 'GITHUB_TOKEN'):
                    self.assertNotIn(absent, text)
                for required in (('nie für nicht verfügbar', 'Never call these functions unavailable'),
                                 ('weder Freigabe noch Speicherung', 'neither an approval nor a save'),
                                 ('höchstens einen Abschnitt', 'at most one section'),
                                 ('Nichts erfinden', 'Do not invent')):
                    self.assertIn(required[language == 'en'], text)
        self.assertNotIn(build_start.OPENWEBUI, self.render())

    def test_openwebui_start_lists_only_commands_the_pipe_runs_itself(self):
        import importlib.util
        try:
            import pydantic  # noqa: F401
        except ImportError:
            self.skipTest('Optionale Open-WebUI-Abhängigkeit pydantic fehlt')
        spec = importlib.util.spec_from_file_location('gw_direct_start', ROOT / 'integrations/openwebui/ghostwriter_direct.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        pipe = module.Pipe()
        navigation = re.compile(r'start|bibliothek|library|(?:buch|book) n|eine nummer|a number|übersicht|overview|'
                                r'(?:kapitel|chapter) n|(?:abschnitt|section) n\.m|kontext prüfen|check context|'
                                r'prompt-profil|prompt profile')
        for language in ('de', 'en'):
            text = (ROOT / build_start.template_names(language)[1]).read_text(encoding='utf-8')
            block = text.split('\n## ')[2]
            commands = re.findall(r'`([^`]+)`', block)
            self.assertGreater(len(commands), 15)
            for command in commands:
                with self.subTest(language=language, command=command):
                    lowered = command.casefold()
                    status = pipe._status_answer(lowered.replace(' n', ' 1'), {'chapters': [{'number': 1}]})
                    self.assertTrue(navigation.fullmatch(lowered) or pipe._mode_command(lowered) or status is not None,
                                    command)

    def test_missing_client_and_invalid_instance(self):
        self.assertIn('`unknown`', self.render()['START.md'])
        for kw in ({'repo': ''}, {'profile': {'repo': 'other/book'}},
                   {'profile': {'startup': {'tools': {'read_start': 'x\ninjection'}}}}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.render(**kw)
        with self.assertRaises(ValueError):
            build_start.render(build_start.MARKER, TEMPLATE, repo='o/r', branch='main',
                               default_branch='main', config={})

    def test_english_and_book_language_precedence(self):
        template = (ROOT / 'templates/start/en.md').read_text(encoding='utf-8')
        text = build_start.render(SOURCE, template, repo='o/r', branch='main', default_branch='main',
                                  config={'interface': {'language': 'en-GB'}},
                                  profile={'interface_language': 'de'})['START.md']
        self.assertIn('`en-GB`', text)
        self.assertIn('**Overview:**', text)
        self.assertIn('Never read or disclose secret values', text)

    def test_profile_schema_and_saving_preserve_startup(self):
        import assistant
        with tempfile.TemporaryDirectory() as folder:
            startup = {'client': 'openwebui', 'tools': {'read_start': 'read_start_md'}}
            prof, errors, _ = assistant.set_profile(Path(folder), {'repo': 'o/r', 'startup': startup})
            self.assertEqual(errors, [])
            self.assertEqual(assistant.load(folder)['startup'], startup)
            self.assertTrue(assistant.errors({**prof, 'startup': {'client': 'invented'}}))

    def test_program_default_branch_keeps_canonical_source(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / 'ghostwriter-manifest.yml').write_text('upstream:\n  repo: owner/program\n')
            (base / 'START.md').write_text(SOURCE, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'vollständige Quelle'):
                build_start.generate(base, repo='owner/program', branch='main', default_branch='main')
            self.assertEqual((base / 'START.md').read_text(encoding='utf-8'), SOURCE)


def git(folder, *args):
    result = subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.org', *args],
                            cwd=folder, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class StartUpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'work'
        self.repo.mkdir()
        self.remote = self.base / 'origin.git'
        git(self.base, 'init', '--bare', '-q', str(self.remote))
        git(self.repo, 'init', '-q', '-b', 'main')
        git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        self.manifest = {'version': '0.6.0', 'managed': ['START.md', 'scripts/', 'templates/', 'docs/'],
                         'book': ['ghostwriter.yml', 'assistant.yml', '.ghostwriter/']}
        (self.repo / 'ghostwriter-manifest.yml').write_text(yaml.safe_dump(self.manifest))
        (self.repo / 'START.md').write_text(SOURCE, encoding='utf-8')
        (self.repo / 'scripts').mkdir()
        shutil.copy(ROOT / 'scripts/build_start.py', self.repo / 'scripts/build_start.py')
        shutil.copytree(ROOT / 'templates/start', self.repo / 'templates/start')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'Zentrale Vorlage')
        git(self.repo, 'branch', 'upstream')
        git(self.repo, 'push', '-q', '-u', 'origin', 'main')
        git(self.repo, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
        previous = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        env = patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/books', 'GITHUB_EVENT_PATH': '',
                                      'GITHUB_REF_NAME': 'main'})
        env.start()
        self.addCleanup(env.stop)

    def apply(self, dry=False):
        return update.update_branch('main', 'upstream', 'upstream:main', self.manifest,
                                    argparse.Namespace(dry_run=dry), True)

    def test_first_generation_replaces_fast_forward_and_is_idempotent(self):
        before = git(self.repo, 'rev-parse', 'origin/main')
        result = self.apply()
        self.assertEqual(result['status'], 'updated', result)
        head = git(self.repo, 'rev-parse', 'origin/main')
        self.assertNotEqual(head, before)
        self.assertEqual(git(self.repo, 'rev-list', '--count', f'{before}..{head}'), '1')
        text = git(self.repo, 'show', f'{head}:START.md')
        self.assertIn(build_start.MARKER, text)
        self.assertIn('GhostWriter in Open WebUI', git(self.repo, 'show', f'{head}:{build_start.OPENWEBUI}'))
        self.assertIn('owner/books', text)
        self.assertIn('`setup`', text)
        self.assertEqual(self.apply()['status'], 'current')
        self.assertEqual(git(self.repo, 'rev-parse', 'origin/main'), head)

    def test_dry_run_does_not_publish_or_modify_working_copy(self):
        head = git(self.repo, 'rev-parse', 'origin/main')
        self.assertEqual(self.apply(dry=True)['status'], 'updated')
        self.assertEqual(git(self.repo, 'rev-parse', 'origin/main'), head)
        self.assertEqual((self.repo / 'START.md').read_text(encoding='utf-8'), SOURCE)
        self.assertFalse((self.repo / 'docs/start').exists())

    def test_profile_change_regenerates_even_without_new_upstream_commit(self):
        self.apply()
        git(self.repo, 'reset', '--hard', 'origin/main')
        profile = {'repo': 'owner/books', 'interface_language': 'en', 'startup': {'client': 'openwebui'}}
        (self.repo / 'assistant.yml').write_text(yaml.safe_dump(profile))
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'Profil eingerichtet')
        git(self.repo, 'push', '-q', 'origin', 'main')
        self.assertEqual(self.apply()['status'], 'updated')
        text = git(self.repo, 'show', 'origin/main:START.md')
        self.assertIn('`resume`', text)
        self.assertIn('`openwebui`', text)
        self.assertIn('**Library:**', text.replace('**Home / Library:**', '**Library:**'))
        self.assertEqual(self.apply()['status'], 'current')

    def test_merge_preserves_book_and_keeps_generation_in_update_commit(self):
        (self.repo / 'ghostwriter.yml').write_text('workflow:\n  current_phase: writing\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'Buch eingerichtet')
        git(self.repo, 'push', '-q', 'origin', 'main')
        git(self.repo, 'switch', '-q', 'upstream')
        (self.repo / 'START.md').write_text(SOURCE + '\nZentrale Ergänzung.\n', encoding='utf-8')
        git(self.repo, 'commit', '-qam', 'Neue Anleitung')
        git(self.repo, 'switch', '-q', 'main')
        result = self.apply()
        self.assertEqual(result['status'], 'updated', result)
        head = git(self.repo, 'rev-parse', 'origin/main')
        self.assertEqual(len(git(self.repo, 'rev-list', '--parents', '-n', '1', head).split()), 3)
        self.assertIn('writing', git(self.repo, 'show', f'{head}:ghostwriter.yml'))
        self.assertIn('Zentrale Ergänzung.', git(self.repo, 'show', f'{head}:docs/start/10-transparenz.md'))
        self.assertIn('GhostWriter-Aktion: update', git(self.repo, 'show', '-s', '--format=%B', head))
        self.assertEqual(self.apply()['status'], 'current')

    def test_generation_failure_does_not_push(self):
        git(self.repo, 'switch', '-q', 'upstream')
        (self.repo / 'scripts/build_start.py').write_text('raise SystemExit("Generator-Testfehler")\n')
        git(self.repo, 'commit', '-qam', 'Defekter Generator')
        git(self.repo, 'switch', '-q', 'main')
        head = git(self.repo, 'rev-parse', 'origin/main')
        result = self.apply()
        self.assertEqual(result['status'], 'failed', result)
        self.assertIn('Generator-Testfehler', result['text'])
        self.assertEqual(git(self.repo, 'rev-parse', 'origin/main'), head)

    def test_template_repository_without_shared_history(self):
        git(self.repo, 'checkout', '-q', '--orphan', 'independent')
        git(self.repo, 'rm', '-r', '-q', '--cached', '.')
        (self.repo / 'ghostwriter.yml').write_text('workflow:\n  current_phase: writing\n')
        git(self.repo, 'add', 'ghostwriter-manifest.yml', 'ghostwriter.yml')
        git(self.repo, 'commit', '-qm', 'Eigenes Template-Repository')
        git(self.repo, 'push', '-q', '--force', 'origin', 'HEAD:main')
        result = self.apply()
        self.assertEqual(result['status'], 'updated', result)
        self.assertIn(build_start.MARKER, git(self.repo, 'show', 'origin/main:START.md'))
        self.assertEqual(self.apply()['status'], 'current')

    def test_book_uses_default_branch_profile_and_remains_in_setup(self):
        (self.repo / 'assistant.yml').write_text('repo: owner/books\nstartup:\n  client: openwebui\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'Bibliotheksprofil')
        git(self.repo, 'push', '-q', 'origin', 'main')
        git(self.repo, 'switch', '-qc', 'buch/neu')
        (self.repo / 'assistant.yml').write_text('repo: owner/books\nstartup:\n  client: claude\n')
        git(self.repo, 'commit', '-qam', 'Altes Buchprofil')
        git(self.repo, 'push', '-q', 'origin', 'buch/neu')
        result = update.update_branch('buch/neu', 'upstream', 'upstream:main', self.manifest,
                                      argparse.Namespace(dry_run=False), True)
        self.assertEqual(result['status'], 'updated', result)
        text = git(self.repo, 'show', 'origin/buch/neu:START.md')
        self.assertIn('`openwebui`', text)
        self.assertIn('`setup`', text)
        # Nur der Einstieg übernimmt das Standardprofil; Buchdateien bleiben erhalten.
        self.assertIn('claude', git(self.repo, 'show', 'origin/buch/neu:assistant.yml'))
        self.assertEqual(self.apply()['status'], 'updated')
        self.assertIn('`resume`', git(self.repo, 'show', 'origin/main:START.md'))


if __name__ == '__main__':
    unittest.main()
