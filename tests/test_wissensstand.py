"""Wissensstand beim Wechsel ins Buch (#369): Figuren, Orte, Begriffe, Zeitpunkte und frühere Gespräche."""
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
import wissensstand  # noqa: E402


class WissensstandTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def add_character(self):
        cfg_path = self.base / 'ghostwriter.yml'
        cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
        cfg['characters'] = [{'id': 'char-anna', 'name': 'Anna', 'path': 'characters/char-anna.md'}]
        cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')
        (self.base / 'characters').mkdir()
        (self.base / 'characters/char-anna.md').write_text(
            '---\nid: char-anna\nname: "Anna"\nrole: main\nshort: "Lehrerin in Graz"\n---\n\n# Anna\n', encoding='utf-8')

    def add_story(self):
        (self.base / 'story').mkdir()
        (self.base / 'story/places.yml').write_text(yaml.safe_dump({'places': [
            {'id': 'pl-graz', 'name': 'Graz', 'aliases': ['die Stadt'], 'kind': 'Stadt', 'short': 'Wohnort'}]},
            allow_unicode=True), encoding='utf-8')
        (self.base / 'story/chronology.yml').write_text(yaml.safe_dump({'entries': [
            {'id': 'chr-001', 'kind': 'event', 'date': '1948-06', 'what': 'Hochzeit', 'status': 'documented'}]},
            allow_unicode=True), encoding='utf-8')

    def add_session(self, name, at, decisions, brainstorming=None):
        root = self.base / 'conversations' / name
        info = {'session': name, 'base': 'main', 'format_version': 1, 'context': {},
                'last_saved': {'at': at, 'origin': {}}}
        root.mkdir(parents=True)
        (root / 'session.json').write_text(json.dumps(info), encoding='utf-8')
        for topic, value in (('decisions', decisions), ('brainstorming', brainstorming)):
            if value is not None:
                (root / topic).mkdir()
                (root / topic / 'latest.json').write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def test_empty_book_says_nothing_saved(self):
        out = wissensstand.text(wissensstand.collect(self.base))
        self.assertIn('Noch nichts gespeichert', out)

    def test_collects_book_knowledge(self):
        self.add_character()
        self.add_story()
        data = wissensstand.collect(self.base)
        self.assertEqual([(c['name'], c['role'], c['short']) for c in data['characters']],
                         [('Anna', 'main', 'Lehrerin in Graz')])
        self.assertEqual(data['places'][0]['aliases'], ['die Stadt'])
        self.assertEqual(data['chronology'][0]['when'], '1948-06')
        out = wissensstand.text(data)
        self.assertIn('- Anna (Hauptfigur): Lehrerin in Graz', out)
        self.assertIn('- Graz (Stadt) – auch: die Stadt: Wohnort', out)
        self.assertIn('- 1948-06: Hochzeit', out)

    def test_sessions_newest_first_with_limit_and_structured_topics(self):
        self.add_session('2026-01-01-alt', '2026-01-01T10:00:00Z', 'Titel bleibt „Malta“')
        self.add_session('2026-02-01-neu', '2026-02-01T10:00:00Z', ['Ich-Erzählerin', 'Präsens'],
                         {'text': 'Idee Fähre verworfen: zu kitschig'})
        data = wissensstand.collect(self.base, limit=0)
        self.assertEqual([s['session'] for s in data['sessions']], ['2026-02-01-neu', '2026-01-01-alt'])
        self.assertEqual(data['sessions'][0]['topics']['decisions'], 'Ich-Erzählerin · Präsens')
        self.assertIn('verworfen', data['sessions'][0]['topics']['brainstorming'])
        self.assertEqual(len(wissensstand.collect(self.base, limit=1)['sessions']), 1)
        self.assertIn('### 2026-02-01-neu (2026-02-01)', wissensstand.text(data))

    def test_long_text_is_shortened(self):
        self.assertEqual(wissensstand.short('a ' * 50, 10), 'a a a a a…')

    def test_read_only_cli(self):
        self.add_character()
        before = sorted(str(p) for p in self.base.rglob('*'))
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/wissensstand.py'), str(self.base), '--json'],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out)['characters'][0]['id'], 'char-anna')
        self.assertEqual(sorted(str(p) for p in self.base.rglob('*')), before)


if __name__ == '__main__':
    unittest.main()


class TitleFallbackTest(unittest.TestCase):
    def test_working_title_when_title_empty(self):
        """#397: leerer project.title → Arbeitstitel statt „Buch“."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
        cfg = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        cfg['project']['title'] = ''
        cfg['project']['working_title'] = 'Flucht in die Zukunft'
        (base / 'ghostwriter.yml').write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')
        import wissensstand
        self.assertEqual(wissensstand.collect(base)['title'], 'Flucht in die Zukunft')
