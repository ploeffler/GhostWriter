"""Tests für den Standabgleich zwischen Chats und Apps (#179, Teil 1)."""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_index  # noqa: E402
import plan_context  # noqa: E402
import standabgleich as sa  # noqa: E402
from unittest import mock  # noqa: E402


def git(base, *args):
    return subprocess.run(['git', '-C', str(base), '-c', 'user.name=t', '-c', 'user.email=t@example.org', *args],
                          capture_output=True, text=True, check=True).stdout.strip()


class StandabgleichTest(unittest.TestCase):
    """Bibliothek: Programm auf main, Buch auf buch/adhs, Arbeit auf ghostwriter/arbeit."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'repo'
        self.base.mkdir()
        git(self.base, 'init', '-q', '-b', 'main')
        for name in ('ghostwriter-manifest.yml', 'START.md', 'CLAUDE.md', 'AGENTS.md'):
            shutil.copy(ROOT / name, self.base / name)
        (self.base / 'schemas').mkdir()
        shutil.copy(ROOT / 'schemas/data-version.yml', self.base / 'schemas/data-version.yml')
        self.write('assistant.yml', 'format: 1\n')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'Programm')
        git(self.base, 'switch', '-q', '--orphan', 'buch/adhs')
        git(self.base, 'clean', '-fdxq')
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base, dirs_exist_ok=True)
        config = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        self.write('ghostwriter.yml', 'data_version: 1\n' + config)
        with redirect_stdout(io.StringIO()):
            build_index.main(['build_index.py', str(self.base)])
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'Buch')
        git(self.base, 'switch', '-q', '-c', 'ghostwriter/arbeit')
        self.commit('notiz.md', 'Arbeit')
        git(self.base, 'switch', '-q', 'main')

    def write(self, path, text):
        (self.base / path).parent.mkdir(parents=True, exist_ok=True)
        (self.base / path).write_text(text, encoding='utf-8')

    def commit(self, path, text, branch=None):
        if branch:
            git(self.base, 'switch', '-q', branch)
        self.write(path, text)
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', text)
        if branch:
            git(self.base, 'switch', '-q', 'main')

    def book_version(self, version):
        for branch in ('buch/adhs', 'ghostwriter/arbeit'):
            config = git(self.base, 'show', f'{branch}:ghostwriter.yml').replace('data_version: 1', f'data_version: {version}', 1)
            self.commit('ghostwriter.yml', config + '\n', branch=branch)

    def stand(self, work='ghostwriter/arbeit'):
        return sa.collect(self.base, 'buch/adhs', work, 'main', repo='owner/bibliothek')

    def states(self, old):
        return {area: state for area, state, _ in sa.compare(self.base, json.loads(json.dumps(old)))}

    def test_unchanged(self):
        old = self.stand()
        self.assertEqual(old['program']['ref'], 'main')
        self.assertTrue(old['instructions'] and old['profile'])
        self.assertEqual(set(self.states(old).values()), {'ok'})
        self.assertEqual(sa.verdict(sa.compare(self.base, old)), 'ok')

    def test_other_app_saved_newer_work(self):
        old = self.stand()
        self.commit('notiz.md', 'Aus der anderen App', branch='ghostwriter/arbeit')
        self.assertEqual(self.states(old)['Arbeit'], 'neuer')
        self.assertEqual(self.states(old)['Buch'], 'ok')

    def test_work_merged_and_branch_removed(self):
        old = self.stand()
        git(self.base, 'switch', '-q', 'buch/adhs')
        git(self.base, 'merge', '-q', '--no-ff', '-m', 'Übernahme', 'ghostwriter/arbeit')
        git(self.base, 'switch', '-q', 'main')
        git(self.base, 'branch', '-qD', 'ghostwriter/arbeit')
        st = self.states(old)
        self.assertEqual((st['Buch'], st['Arbeit']), ('neuer', 'neuer'))
        text = dict((a, t) for a, _, t in sa.compare(self.base, old))['Arbeit']
        self.assertIn('übernommen', text)

    def test_work_diverged_or_lost(self):
        old = self.stand()
        git(self.base, 'switch', '-q', 'ghostwriter/arbeit')
        git(self.base, 'reset', '-q', '--hard', 'buch/adhs')
        git(self.base, 'switch', '-q', 'main')
        self.commit('anders.md', 'Andere Fassung', branch='ghostwriter/arbeit')
        self.assertEqual(self.states(old)['Arbeit'], 'konflikt')
        git(self.base, 'branch', '-qD', 'ghostwriter/arbeit')
        self.assertEqual(self.states(old)['Arbeit'], 'konflikt')   # verschwunden, nicht im Buch

    def test_book_branch_switched_or_rewritten(self):
        old = self.stand(work=None)
        git(self.base, 'branch', '-qf', 'buch/adhs', 'main')   # Buch-Branch zeigt woandershin
        self.assertEqual(self.states(old)['Buch'], 'konflikt')
        git(self.base, 'branch', '-qD', 'buch/adhs')
        self.assertEqual(self.states(old)['Buch'], 'konflikt')

    def test_program_update_makes_instructions_stale(self):
        old = self.stand()
        self.write('START.md', (self.base / 'START.md').read_text(encoding='utf-8') + '\nNeu\n')
        self.write('.ghostwriter/update.yml', 'commit: abc\nversion: 9.9.9\n')
        git(self.base, 'commit', '-qam', 'x')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'Update')
        st = self.states(old)
        self.assertEqual((st['Programm'], st['Anweisungen'], st['Profil']), ('neuer', 'neuer', 'ok'))

    def test_profile_change(self):
        old = self.stand()
        self.commit('assistant.yml', 'format: 1\nwork_modes: auto\n')
        st = self.states(old)
        self.assertEqual((st['Profil'], st['Anweisungen']), ('neuer', 'ok'))

    def test_program_change_without_version_bump_requires_refresh(self):
        old = self.stand()
        self.commit('scripts/test_program.py', 'print("Neue Programmlogik")\n')
        states = self.states(old)
        self.assertEqual(states['Programm'], 'neuer')
        self.assertEqual(states['Anweisungen'], 'ok')
        old = self.stand()
        self.commit('scripts/test_program.py', 'print("Geänderte Programmlogik")\n')
        self.assertEqual(self.states(old)['Programm'], 'neuer')
        old = self.stand()
        git(self.base, 'rm', 'scripts/test_program.py')
        git(self.base, 'commit', '-qm', 'Programmdatei entfernt')
        self.assertEqual(self.states(old)['Programm'], 'neuer')

    def test_legacy_snapshot_without_program_fingerprint_requires_refresh(self):
        old = self.stand()
        old['program'].pop('content', None)
        self.assertEqual(self.states(old)['Programm'], 'neuer')

    def test_runtime_resources_and_workflows_are_part_of_program_fingerprint(self):
        for path in ('schemas/test.json', 'integrations/test.py', 'templates/test.md',
                     'assets/test.svg', '.github/workflows/test.yml',
                     'workflow.yml', 'providers.yml'):
            with self.subTest(path=path):
                old = self.stand()
                self.commit(path, 'Geänderter Programmstand')
                self.assertEqual(self.states(old)['Programm'], 'neuer')

    def test_unrelated_program_branch_note_does_not_require_program_refresh(self):
        old = self.stand()
        self.commit('notiz.md', 'Nur eine Notiz')
        self.assertEqual(self.states(old)['Programm'], 'ok')

    def test_personal_skill_add_change_and_removal_make_instructions_stale(self):
        path = '.claude/skills/autor-auf-bibliothek/SKILL.md'
        old = self.stand()
        self.commit(path, 'Persönliche Schreibregeln')
        self.assertEqual(self.states(old)['Anweisungen'], 'neuer')
        old = self.stand()
        self.commit(path, 'Geänderte persönliche Schreibregeln')
        states = self.states(old)
        self.assertEqual(states['Anweisungen'], 'neuer')
        self.assertEqual(states['Profil'], 'ok')
        old = self.stand()
        git(self.base, 'rm', path)
        git(self.base, 'commit', '-qm', 'Persönlichen Skill entfernt')
        self.assertEqual(self.states(old)['Anweisungen'], 'neuer')

    def test_note_outside_skill_directory_does_not_invalidate_instructions(self):
        old = self.stand()
        self.commit('.claude/skills-notes.md', 'Nur eine Notiz')
        self.assertEqual(self.states(old)['Anweisungen'], 'ok')

    def test_changed_skill_source_commit_invalidates_instructions(self):
        old = self.stand()
        self.commit('ghostwriter-skills.yml', 'commit: ' + 'a' * 40 + '\n')
        self.assertEqual(self.states(old)['Anweisungen'], 'neuer')

    def test_incompatible_data_version_blocks_writing(self):
        old = self.stand()
        self.book_version(99)   # Buch in einer neueren App migriert, Programm hier älter
        self.assertEqual(self.states(old)['Daten'], 'konflikt')
        self.assertEqual(sa.verdict(sa.compare(self.base, old)), 'konflikt')

    def test_older_book_data_is_a_hint(self):
        old = self.stand(work=None)
        config = git(self.base, 'show', 'buch/adhs:ghostwriter.yml').replace('data_version: 1\n', '', 1)
        self.commit('ghostwriter.yml', config + '\n', branch='buch/adhs')
        self.assertEqual(self.states(old)['Daten'], 'neuer')

    def test_stale_index_is_only_a_hint(self):
        old = self.stand(work=None)
        self.assertEqual(self.states(old)['Abgeleitet'], 'ok')
        self.commit('ghostwriter-index.json', '{}\n', branch='buch/adhs')
        st = self.states(old)
        self.assertEqual((st['Buch'], st['Abgeleitet']), ('neuer', 'hinweis'))
        git(self.base, 'switch', '-q', 'buch/adhs')
        git(self.base, 'reset', '-q', '--hard', old['book']['head'])
        git(self.base, 'switch', '-q', 'main')
        self.commit('ghostwriter-index.json', '{}\n', branch='ghostwriter/arbeit')
        old = self.stand()
        result = sa.compare(self.base, old)
        self.assertEqual(dict((a, s) for a, s, _ in result)['Abgeleitet'], 'hinweis')
        self.assertEqual(sa.verdict(result), 'ok')   # sperrt nichts, ändert den Exit-Code nicht
        self.assertIn('⚠ Abgeleitet: Übersichtsdatei', sa.report(old, result))

    def test_stale_summaries_in_summary_mode(self):
        old = self.stand(work=None)
        real = plan_context.plan

        def summaries(path, limited_context=False):
            ctx = real(path, limited_context)
            ctx['mode'] = 'summaries'
            return ctx
        with mock.patch.object(plan_context, 'plan', summaries):
            d = dict((a, t) for a, _, t in sa.compare(self.base, old))['Abgeleitet']
        self.assertIn('Zusammenfassungen veraltet oder fehlend: context/book.md', d)
        self.assertIn('weitere', d)

    def test_cli_exit_codes_and_report(self):
        path = self.base.parent / 'stand.json'
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(sa.main([str(self.base), 'stand', '--book', 'buch/adhs', '--work', 'ghostwriter/arbeit',
                                      '--program-ref', 'main']), 0)
        path.write_text(out.getvalue(), encoding='utf-8')
        status = git(self.base, 'status', '--porcelain')
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(sa.main([str(self.base), 'check', str(path)]), 0)
        self.assertIn('Nicht abgeglichen:', out.getvalue())
        self.assertNotIn('synchron', out.getvalue())
        self.commit('notiz.md', 'B', branch='ghostwriter/arbeit')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(sa.main([str(self.base), 'check', str(path)]), 1)
        self.book_version(99)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(sa.main([str(self.base), 'check', str(path), '--json']), 2)
        self.assertEqual(json.loads(out.getvalue())['state'], 'konflikt')
        self.assertEqual(git(self.base, 'status', '--porcelain'), status)   # liest nur

    def test_wrong_format(self):
        with self.assertRaises(ValueError):
            sa.compare(self.base, {'format': 0})


if __name__ == '__main__':
    unittest.main()
