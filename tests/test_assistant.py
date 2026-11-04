"""Assistenten-Profil, persönlicher Skill und Einstiegsdateien (#136)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assistant  # noqa: E402

MANIFEST = yaml.safe_load((ROOT / 'ghostwriter-manifest.yml').read_text(encoding='utf-8'))
STARTER_FILE = ROOT / 'templates/ghostwriter-starter.yml'
PROFILE = {'repo': 'chillyconcane/YAWA', 'author': 'Cyberlefl325',
           'git': {'name': 'chillyconcane', 'email': '1+chillyconcane@users.noreply.github.com'},
           'voice': {'text': 'Selbstironischer Ich-Erzähler.', 'perspective': 'ich', 'tone': ['warm', 'trocken']}}


def git(d, *a):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True,
                          capture_output=True, text=True).stdout.strip()


class SkillNameTest(unittest.TestCase):
    def test_names(self):
        self.assertEqual(assistant.skill_name('Cyberlefl325', 'chillyconcane/YAWA'), 'cyberlefl325-auf-yawa')
        self.assertEqual(assistant.skill_name('', 'chillyconcane/YAWA'), 'chillyconcane-auf-yawa')
        self.assertEqual(assistant.skill_name('Jörg Müßig', 'x/Meine Bücher'), 'joerg-muessig-auf-meine-buecher')
        self.assertNotIn('claude', assistant.skill_name('Claude', 'a/b'))
        self.assertLessEqual(len(assistant.skill_name('a' * 80, 'b/' + 'c' * 80)), 64)


class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        shutil.copyfile(STARTER_FILE, self.d / 'ghostwriter.yml')
        import os
        self.env = dict(os.environ)

    def tearDown(self):
        import os
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def test_set_creates_profile_and_skill(self):
        prof, errs, res = assistant.set_profile(self.d, PROFILE)
        self.assertEqual(errs, [])
        self.assertEqual(res['message'], 'Assistenten-Profil angelegt')
        self.assertEqual(prof['skill'], 'cyberlefl325-auf-yawa')
        skill = (self.d / '.claude/skills/cyberlefl325-auf-yawa/SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(skill.startswith('---\nname: cyberlefl325-auf-yawa\ndescription: Cyberlefl325 auf YAWA: '))
        self.assertIn('GhostWriter-Bibliothek chillyconcane/YAWA', skill)
        self.assertIn('`--repo chillyconcane/YAWA`', skill)
        self.assertIn('git config user.email "1+chillyconcane@users.noreply.github.com"', skill)
        self.assertIn('> Selbstironischer Ich-Erzähler.', skill)
        self.assertIn('- Ton: warm, trocken', skill)
        self.assertIn('Hauptrepo `ploeffler/GhostWriter`', skill)
        self.assertNotIn('{{', skill)
        self.assertEqual(assistant.check(self.d), [])

    def test_update_merges_and_keeps_name(self):
        assistant.set_profile(self.d, PROFILE)
        prof, errs, res = assistant.set_profile(self.d, {'author': 'Anna Berg', 'voice': {'tense': 'Präteritum'}})
        self.assertEqual(errs, [])
        self.assertEqual(res['message'], 'Assistenten-Profil gespeichert')
        self.assertEqual(prof['skill'], 'cyberlefl325-auf-yawa')          # Name bleibt stabil
        self.assertEqual(prof['voice']['perspective'], 'ich')              # zusammengeführt
        self.assertEqual(prof['voice']['tense'], 'Präteritum')
        self.assertIn('Autor: Anna Berg', (self.d / '.claude/skills/cyberlefl325-auf-yawa/SKILL.md').read_text(encoding='utf-8'))

    def test_rename_removes_only_generated_skill(self):
        assistant.set_profile(self.d, PROFILE)
        own = self.d / '.claude/skills/mein-eigener/SKILL.md'
        own.parent.mkdir(parents=True)
        own.write_text('---\nname: mein-eigener\n---\nvon Hand\n', encoding='utf-8')
        prof, errs, res = assistant.set_profile(self.d, {'skill': 'anna-auf-yawa'})
        self.assertEqual(errs, [])
        self.assertFalse((self.d / '.claude/skills/cyberlefl325-auf-yawa').exists())
        self.assertTrue((self.d / '.claude/skills/anna-auf-yawa/SKILL.md').is_file())
        self.assertTrue(own.is_file(), 'ein von Hand angelegter Skill bleibt')
        self.assertIn('.claude/skills/cyberlefl325-auf-yawa/SKILL.md', res['files'])

    def test_invalid(self):
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'git': {'name': 'x', 'email': 'kein-mail'}})
        self.assertTrue(errs)
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'skill': 'ghostwriter'})
        self.assertTrue(any('allgemeine Skill' in e for e in errs))
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'voice': {'text': 'x' * 2001}})
        self.assertTrue(errs, 'Stimme ist eine Beschreibung, kein Manuskripttext')
        self.assertFalse((self.d / 'assistant.yml').exists())

    def test_check_detects_drift_and_validate_uses_it(self):
        assistant.set_profile(self.d, PROFILE)
        skill = self.d / '.claude/skills/cyberlefl325-auf-yawa/SKILL.md'
        skill.write_text(skill.read_text(encoding='utf-8') + '\nvon Hand ergänzt\n', encoding='utf-8')
        self.assertTrue(assistant.check(self.d))
        import validate_project
        self.assertTrue(any('passt nicht' in e for e in validate_project.check_project(self.d)))
        subprocess.run([sys.executable, str(ROOT / 'scripts/assistant.py'), str(self.d), 'skill'], check=True, capture_output=True)
        self.assertEqual(assistant.check(self.d), [])

    def test_kind_and_draft(self):
        assistant.set_profile(self.d, PROFILE)
        self.assertIn('(Bibliothek)', (self.d / '.claude/skills/cyberlefl325-auf-yawa/SKILL.md').read_text(encoding='utf-8'))
        shutil.copyfile(ROOT / 'tests/fixtures/adhs/ghostwriter.yml', self.d / 'ghostwriter.yml')
        self.assertIn('(Buch)', assistant.render(self.d, assistant.load(self.d)))
        (self.d / 'assistant.yml').unlink()
        import os
        os.environ.pop('GITHUB_REPOSITORY', None)   # in Actions gesetzt; hier zählt die Remote-Adresse
        subprocess.run(['git', 'init', '-q', str(self.d)], check=True)
        subprocess.run(['git', '-C', str(self.d), 'remote', 'add', 'origin', 'git@github.com:anna/romane.git'], check=True)
        cfg = yaml.safe_load((self.d / 'ghostwriter.yml').read_text(encoding='utf-8'))
        cfg['project']['author'] = 'Anna Berg'
        (self.d / 'ghostwriter.yml').write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding='utf-8')
        d = assistant.draft(self.d)
        self.assertEqual(d['repo'], 'anna/romane')
        self.assertEqual(d['author'], 'Anna Berg')
        self.assertEqual(d['skill'], 'anna-berg-auf-romane')
        self.assertNotIn('git', d)

    def test_cli(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/assistant.py'), str(self.d), 'set', json.dumps(PROFILE)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('✓ Assistenten-Profil angelegt', r.stdout)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/assistant.py'), str(self.d), 'check'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


class EntryFilesTest(unittest.TestCase):
    """CLAUDE.md, AGENTS.md und der allgemeine Skill kommen mit dem Update; der persönliche Skill bleibt."""

    def test_manifest(self):
        managed, book = MANIFEST['managed'], MANIFEST['book']
        for p in ('CLAUDE.md', 'AGENTS.md', '.claude/skills/ghostwriter/'):
            self.assertIn(p, managed)
            self.assertTrue((ROOT / p).exists(), p)
        self.assertIn('assistant.yml', book)
        self.assertFalse(any(p.rstrip('/') in ('.claude', '.claude/skills') for p in managed + book))

    def test_general_skill(self):
        text = (ROOT / '.claude/skills/ghostwriter/SKILL.md').read_text(encoding='utf-8')
        head = yaml.safe_load(text.split('---')[1])
        self.assertEqual(head['name'], 'ghostwriter')
        self.assertTrue(head['description'])
        for s in ('--repo', 'permissions.push', 'user.email', 'assistant.py . check', 'Widget'):
            self.assertIn(s, text)
        for f in ('CLAUDE.md', 'AGENTS.md'):
            t = (ROOT / f).read_text(encoding='utf-8')
            self.assertIn('START.md', t)
            self.assertIn('--repo', t)
            self.assertIn('assistant.yml', t)

    def test_update_keeps_personal_skill(self):
        import update_from_upstream as up
        with tempfile.TemporaryDirectory() as d:
            git(d, 'init', '-q', '-b', 'main')
            gen = Path(d, '.claude/skills/ghostwriter/SKILL.md')
            gen.parent.mkdir(parents=True)
            gen.write_text('alt\n', encoding='utf-8')
            Path(d, 'CLAUDE.md').write_text('alt\n', encoding='utf-8')
            git(d, 'add', '.')
            git(d, 'commit', '-qm', 'Programm alt')
            git(d, 'branch', 'upstream')
            git(d, 'switch', '-q', 'upstream')
            gen.write_text('neu\n', encoding='utf-8')
            Path(d, 'CLAUDE.md').write_text('neu\n', encoding='utf-8')
            git(d, 'commit', '-qam', 'Programm neu')
            git(d, 'switch', '-q', 'main')
            own = Path(d, '.claude/skills/anna-auf-romane/SKILL.md')
            own.parent.mkdir(parents=True)
            own.write_text('persönlich\n', encoding='utf-8')
            Path(d, 'assistant.yml').write_text('format: 1\n', encoding='utf-8')
            git(d, 'add', '.')
            git(d, 'commit', '-qm', 'Profil')
            git(d, 'merge', '-q', '--no-commit', '--no-ff', 'upstream')
            unresolved, _ = up.resolve_paths(d, 'upstream', MANIFEST, True)
            self.assertEqual(unresolved, [])
            self.assertEqual(gen.read_text(encoding='utf-8'), 'neu\n')
            self.assertEqual(Path(d, 'CLAUDE.md').read_text(encoding='utf-8'), 'neu\n')
            self.assertEqual(own.read_text(encoding='utf-8'), 'persönlich\n')
            self.assertEqual(Path(d, 'assistant.yml').read_text(encoding='utf-8'), 'format: 1\n')


class ProgramRepoTest(unittest.TestCase):
    def test_no_profile_in_program_repo(self):
        import os
        import library
        with tempfile.TemporaryDirectory() as d:
            git(d, 'init', '-q', '-b', 'main')
            shutil.copyfile(STARTER_FILE, Path(d, 'ghostwriter.yml'))
            Path(d, '.claude/skills/ghostwriter').mkdir(parents=True)
            Path(d, '.claude/skills/ghostwriter/SKILL.md').write_text('x', encoding='utf-8')
            git(d, 'add', '.')
            git(d, 'commit', '-qm', 'Programm')
            env, os.environ['GHOSTWRITER_DEFAULT_BRANCH'] = dict(os.environ), 'main'
            try:
                self.assertEqual(library.program_problems(d, 'refs/heads', MANIFEST)[0], [])
                Path(d, 'assistant.yml').write_text('format: 1\n', encoding='utf-8')
                Path(d, '.claude/skills/anna-auf-x').mkdir()
                errors = library.program_problems(d, 'refs/heads', MANIFEST)[0]
                self.assertEqual(len(errors), 2, errors)
            finally:
                os.environ.clear()
                os.environ.update(env)


if __name__ == '__main__':
    unittest.main()
