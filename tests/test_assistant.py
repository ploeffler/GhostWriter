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

    def test_skill_text_does_not_depend_on_the_branch_or_the_structure(self):   # #706
        import subprocess
        g = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=self.d, check=True, capture_output=True, text=True)
        g('init', '-q', '-b', 'main')
        assistant.set_profile(self.d, PROFILE)
        base_skill = (self.d / '.claude/skills/cyberlefl325-auf-yawa/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('Arbeit an der GhostWriter-Bibliothek chillyconcane/YAWA', base_skill)
        g('add', '.'); g('commit', '-qm', 'x')
        g('switch', '-q', '-c', 'buch/neu')
        cfg = yaml.safe_load((self.d / 'ghostwriter.yml').read_text(encoding='utf-8'))
        cfg.setdefault('structure', {})['chapters'] = [{'id': 'ch-1', 'title': 'K', 'path': 'chapters/ch-1', 'sections': []}]
        (self.d / 'ghostwriter.yml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
        self.assertTrue(assistant.is_library(self.d))                  # Buch-Branch mit Struktur gilt weiter als Bibliothek
        self.assertEqual(assistant.check(self.d), [])                   # Skill unverändert gültig
        g('switch', '-q', '-c', 'einzelbuch')                           # ohne Bibliotheksmerkmale ist es ein Buch
        self.assertFalse(assistant.is_library(self.d))
        self.assertIn('Arbeit am GhostWriter-Buch chillyconcane/YAWA', assistant.render(self.d, assistant.load(self.d)))

    def test_update_merges_and_keeps_name(self):
        assistant.set_profile(self.d, PROFILE)
        prof, errs, res = assistant.set_profile(self.d, {'author': 'Anna Berg', 'voice': {'tense': 'Präteritum'}})
        self.assertEqual(errs, [])
        self.assertEqual(res['message'], 'Assistenten-Profil gespeichert')
        self.assertEqual(prof['skill'], 'cyberlefl325-auf-yawa')          # Name bleibt stabil
        self.assertEqual(prof['voice']['perspective'], 'ich')              # zusammengeführt
        self.assertEqual(prof['voice']['tense'], 'Präteritum')
        self.assertIn('Autor: Anna Berg', (self.d / '.claude/skills/cyberlefl325-auf-yawa/SKILL.md').read_text(encoding='utf-8'))

    def test_interface_language_is_optional_and_persisted(self):
        assistant.set_profile(self.d, PROFILE)
        prof, errs, _ = assistant.set_profile(self.d, {'interface_language': 'en'})
        self.assertEqual(errs, [])
        self.assertEqual(assistant.load(self.d)['interface_language'], 'en')
        self.assertEqual(prof['voice'], PROFILE['voice'])
        _, errs, _ = assistant.set_profile(self.d, {'interface_language': 'fr'})
        self.assertTrue(errs)
        self.assertEqual(assistant.load(self.d)['interface_language'], 'en')

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

    def test_long_voice_and_features_as_bullets(self):   # #330
        voice = {'text': 'Absatz eins.\n\n' + 'Lange Beschreibung. ' * 200, 'tone': ['warm', 'trocken'],
                 'features': ['Kurze Sätze, oft ohne Verb', 'Running Gags, die wiederkehren']}
        prof, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'voice': voice})
        self.assertEqual(errs, [])
        self.assertGreater(len(prof['voice']['text']), 2000)
        skill = assistant.skill_path(self.d, prof).read_text(encoding='utf-8')
        self.assertIn('- Stilmittel:\n  - Kurze Sätze, oft ohne Verb\n  - Running Gags, die wiederkehren', skill)
        self.assertIn('- Ton: warm, trocken', skill)
        prof, _, _ = assistant.set_profile(self.d, {'voice': {'tone': ['warm, aber nie kitschig', 'trocken']}})
        self.assertIn('- Ton:\n  - warm, aber nie kitschig\n  - trocken', assistant.skill_path(self.d, prof).read_text(encoding='utf-8'))

    def test_handwritten_skill_is_not_overwritten(self):   # #330
        p = self.d / '.claude/skills/cyberlefl325-auf-yawa/SKILL.md'
        p.parent.mkdir(parents=True)
        p.write_text('---\nname: cyberlefl325-auf-yawa\n---\n\nErprobte Werkzeugwege.\n', encoding='utf-8')
        prof, errs, res = assistant.set_profile(self.d, PROFILE)
        self.assertIsNone(prof)
        self.assertTrue(any('von Hand geschrieben' in e and '--force' in e for e in errs), errs)
        self.assertFalse((self.d / 'assistant.yml').exists())
        self.assertIn('Erprobte Werkzeugwege', p.read_text(encoding='utf-8'))
        prof, errs, res = assistant.set_profile(self.d, PROFILE, force=True)
        self.assertEqual(errs, [])
        self.assertIn('Erprobte Werkzeugwege', p.with_name('SKILL.md.bak').read_text(encoding='utf-8'))
        self.assertIn('.claude/skills/cyberlefl325-auf-yawa/SKILL.md.bak', res['files'])
        self.assertIn(assistant.MARKER, p.read_text(encoding='utf-8'))
        p.write_text('handgeschrieben\n', encoding='utf-8')
        self.assertTrue(any('von Hand geschrieben' in e for e in assistant.check(self.d)))
        with self.assertRaises(assistant.HandwrittenSkill):
            assistant.write_skill(self.d, prof)

    def test_own_additions_survive_regeneration(self):   # #330
        prof, _, _ = assistant.set_profile(self.d, PROFILE)
        p = assistant.skill_path(self.d, prof)
        text = p.read_text(encoding='utf-8')
        self.assertIn(assistant.OWN_START + '\n' + assistant.OWN_END, text)
        p.write_text(text.replace(assistant.OWN_END, '- Eigener Werkzeugweg: gh api …\n' + assistant.OWN_END), encoding='utf-8')
        self.assertEqual(assistant.check(self.d), [])
        assistant.set_profile(self.d, {'author': 'Neu'})
        self.assertIn('- Eigener Werkzeugweg: gh api …', p.read_text(encoding='utf-8'))
        self.assertIn('- Autor: Neu', p.read_text(encoding='utf-8'))

    def test_answer_backup_in_background(self):   # #487
        prof, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'answer_backup': 'hintergrund'})
        self.assertEqual(errs, [])
        skill = assistant.skill_path(self.d, prof).read_text(encoding='utf-8')
        self.assertIn('--background', skill)
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'answer_backup': 'irgendwann'})
        self.assertTrue(errs)

    def test_answer_style_kurz_und_klar(self):   # #698
        prof, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'answer_style': 'kurz-und-klar'})
        self.assertEqual(errs, [])
        skill = assistant.skill_path(self.d, prof).read_text(encoding='utf-8')
        self.assertIn('ghostwriter-kurz-und-klar', skill)
        prof, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'answer_style': 'standard'})
        self.assertNotIn('ghostwriter-kurz-und-klar', assistant.skill_path(self.d, prof).read_text(encoding='utf-8'))
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'answer_style': 'einfach'})
        self.assertTrue(errs)

    def test_display_and_answers(self):   # #330
        prof, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'display': 'erweitert', 'answers': 'erweitert'})
        self.assertEqual(errs, [])
        skill = assistant.skill_path(self.d, prof).read_text(encoding='utf-8')
        self.assertIn('„Darstellung: erweitert“ ist der Standard dieses Repositorys', skill)
        self.assertIn('- Antwortmodus: erweiterte Antworten', skill)
        self.assertNotIn('Darstellungsmodus in Claude: Widget', skill)
        _, errs, _ = assistant.set_profile(self.d, {'display': 'bunt'})
        self.assertTrue(errs)
        import build_start
        text = build_start.render((ROOT / 'START.md').read_text(encoding='utf-8'),
                                  (ROOT / 'templates/start/de.md').read_text(encoding='utf-8'),
                                  repo='chillyconcane/YAWA', branch='main', default_branch='main', config={},
                                  profile={**PROFILE, 'display': 'erweitert', 'answers': 'erweitert'})['START.md']
        self.assertIn('Standard: erweitert, Antworten erweitert', text)

    def test_subagent_models(self):   # #418
        prof, errs, _ = assistant.set_profile(self.d, PROFILE)
        skill = assistant.skill_path(self.d, prof).read_text(encoding='utf-8')
        self.assertNotIn('Hilfsagenten', skill)
        prof, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'subagent_models': {'language': 'small'}})
        self.assertEqual(errs, [])
        skill = assistant.skill_path(self.d, prof).read_text(encoding='utf-8')
        self.assertIn('Sprachlektorat klein', skill)
        self.assertIn('Strukturlektorat groß', skill)
        self.assertIn('klein = haiku', skill)
        _, errs, _ = assistant.set_profile(self.d, {'subagent_models': {'language': 'riesig'}})
        self.assertTrue(errs)

    def test_subagent_models_research(self):   # #449
        prof, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'subagent_models': {'research_search': 'medium'}})
        self.assertEqual(errs, [])
        skill = assistant.skill_path(self.d, prof).read_text(encoding='utf-8')
        self.assertIn('Recherche: Suche mittel', skill)
        self.assertIn('Recherche: Abgleich mittel', skill)
        self.assertIn('Kapitelrecherche mittel', skill)

    def test_invalid(self):
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'git': {'name': 'x', 'email': 'kein-mail'}})
        self.assertTrue(errs)
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'skill': 'ghostwriter'})
        self.assertTrue(any('allgemeine Skill' in e for e in errs))
        _, errs, _ = assistant.set_profile(self.d, {**PROFILE, 'voice': {'text': 'x' * 6001}})
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
        for p in ('CLAUDE.md', 'AGENTS.md'):
            self.assertIn(p, managed)
            self.assertTrue((ROOT / p).exists(), p)
        self.assertIn('.claude/skills/ghostwriter/', managed)         # entfällt (#569): das Update entfernt die alte Kopie
        self.assertFalse((ROOT / '.claude/skills/ghostwriter').exists())
        self.assertIn('assistant.yml', book)
        self.assertFalse(any(p.rstrip('/') in ('.claude', '.claude/skills') for p in managed + book))

    def test_start_carries_the_flow_of_the_removed_skill(self):
        """#569: Was früher nur im Skill `ghostwriter` stand, steht in START.md; der Skill hat keine Kopie im Hauptrepo mehr."""
        text = (ROOT / 'START.md').read_text(encoding='utf-8')
        for s in ('--repo', 'permissions.push', 'user.email', 'zz-schreibtest', 'Fall 1', 'Fall 2', 'Fall 3', '„Speichern“',
                  '„Zusammenführen“', 'issue_write', 'Anforderungen zuordnen', 'Fall 1b', 'could not read Username', 'Fähigkeiten getrennt feststellen'):
            self.assertIn(s, text)
        for f in ('CLAUDE.md', 'AGENTS.md'):
            t = (ROOT / f).read_text(encoding='utf-8')
            self.assertIn('START.md', t)
            self.assertIn('--repo', t)
            self.assertIn('assistant.yml', t)
            self.assertNotIn('.claude/skills/ghostwriter/SKILL.md', t)

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
            gen.unlink()                       # entfällt im Hauptrepo (#569)
            Path(d, 'CLAUDE.md').write_text('neu\n', encoding='utf-8')
            git(d, 'add', '-A')
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
            self.assertFalse(gen.exists())     # die alte Kopie wird beim Update entfernt
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
            Path(d, '.claude/skills/ghostwriter-lektorat').mkdir(parents=True)
            Path(d, '.claude/skills/ghostwriter-lektorat/SKILL.md').write_text('x', encoding='utf-8')
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


class ReportRuleTest(unittest.TestCase):
    """Melderegel für Programmfehler in jedem Einstieg (#330), auch ohne persönlichen Skill."""

    def test_every_entry_contains_rule(self):
        import build_start
        de = {'CLAUDE.md': 'ohne Rückfrage als Issue im Hauptrepository', 'AGENTS.md': 'ohne Rückfrage als Issue im Hauptrepository',
              'START.md': '**ohne Rückfrage** als Issue ins Hauptrepository',
              'templates/assistant-skill.md': 'ohne Rückfrage als Issue im Hauptrepo'}
        for name, phrase in de.items():
            self.assertIn(phrase, (ROOT / name).read_text(encoding='utf-8'), name)
        for name in ('CLAUDE.md', 'AGENTS.md'):   # Zugriff und Bucharbeit (aus CHATGPT.md in YAWA übernommen)
            text = (ROOT / name).read_text(encoding='utf-8')
            for phrase in ('nie durch eine Websuche ersetzen', 'vollständigen Dateiinhalte mit Zielpfad',
                           'keine Programmdateien ändern', '„keine Codeänderungen“'):
                self.assertIn(phrase, text, name)
        for name in ('CLAUDE.md', 'AGENTS.md'):   # Skills für jeden Assistenten laden
            text = (ROOT / name).read_text(encoding='utf-8')
            for phrase in ('Skills aus dem Repository laden (für jeden Assistenten)', '`.claude/skills/<name>/SKILL.md`', 'liest dessen `SKILL.md` vollständig'):
                self.assertIn(phrase, text, name)
        self.assertIn('eine eigene `CHATGPT.md` ist nicht nötig', (ROOT / 'AGENTS.md').read_text(encoding='utf-8'))
        source = (ROOT / 'START.md').read_text(encoding='utf-8')
        for lang, phrase in (('de', 'Programmfehler ungefragt als Issue im Hauptrepo melden'),
                             ('en', 'Report program bugs upstream as an issue without asking')):
            main, webui = build_start.template_names(lang)
            out = build_start.render(source, (ROOT / main).read_text(encoding='utf-8'), repo='o/b', branch='main',
                                     default_branch='main', config={}, openwebui_template=(ROOT / webui).read_text(encoding='utf-8'),
                                     upstream='ploeffler/GhostWriter')
            self.assertIn(phrase, out['START.md'], lang)
            webui_text = out[build_start.OPENWEBUI]
            self.assertIn('https://github.com/ploeffler/GhostWriter/issues/new', webui_text, lang)
