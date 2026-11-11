"""Tests für Figuren (#53): „Strolchi und Opi“ mit Strolchi, Opi und Wolf – und ein Buch ohne Figuren."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_index  # noqa: E402
import characters  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402


class CharacterTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        self.original = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')

    def add_three(self):
        characters.add(self.base, 'Strolchi', 'main', 'Ein neugieriger kleiner Hund')
        characters.add(self.base, 'Opi', 'supporting')
        characters.add(self.base, 'Wolf', 'minor')

    def run_view(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args],
                              capture_output=True, text=True, check=True).stdout

    def widget(self, *args):
        m = re.search(r'GW\.render\("([^"]+)",(.*)\)</script>', self.run_view(*args))
        return m.group(1), json.loads(m.group(2).replace('<\\/', '</'))

    def test_without_characters_nothing_changes(self):
        _, config = load(self.base)
        self.assertNotIn('characters', build_index.build(self.base, config))
        _, data = self.widget('project')
        self.assertNotIn('CHARACTER_COUNT', data)
        _, data = self.widget('section', '1.1')
        self.assertNotIn('ALL_CHARACTERS', data)
        self.assertIn('*Noch keine Figuren.*', self.run_view('characters', '--text'))

    def test_add_assign_context(self):
        self.add_three()
        text = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        self.assertEqual(re.sub(r'(?ms)^characters:\n.*?(?=^structure:)', '', text), self.original)   # sonst unverändert
        _, config = load(self.base)
        self.assertEqual([c['id'] for c in config['characters']], ['char-strolchi', 'char-opi', 'char-wolf'])
        with self.assertRaises(SystemExit):
            characters.add(self.base, 'opi')
        characters.update(self.base, 'opi', {'age': '78', 'traits': 'geduldig, brummig', 'voice': 'bedächtig',
                                             'relations': [{'to': 'char-strolchi', 'kind': 'Besitzer'}],
                                             'description': 'Lebt allein am Waldrand.'})
        characters.assign(self.base, '1.1', ['Strolchi', 'char-opi'])
        self.assertEqual(validate_project.check_project(self.base), [])
        ctx = characters.context(self.base, '1.1')
        self.assertIn('### Strolchi (Hauptfigur)', ctx)
        self.assertIn('- Eigenschaften: geduldig, brummig', ctx)
        self.assertIn('- Beziehung: Besitzer von Strolchi', ctx)
        self.assertIn('Lebt allein am Waldrand.', ctx)
        self.assertNotIn('Wolf', ctx)
        self.assertEqual(characters.context(self.base, '1.2'), '')
        characters.assign(self.base, '1.1', [])   # Zuordnung entfernen
        _, config = load(self.base)
        sec = (self.base / config['structure']['chapters'][0]['sections'][0]['path']).read_text(encoding='utf-8')
        self.assertNotIn('characters:', sec)

    def test_add_long_short_and_name_stay_one_line(self):
        """#263: lange Kurzbeschreibung und langer Name nicht umbrechen."""
        name = 'Die Frau im lila Steppmantel, die jeden Morgen am Marktplatz von Valletta Tauben füttert'
        short = ('Über 80, laut, willensstark, peppig gekleidet, sehbehindert; trägt Neuigkeiten ins Viertel '
                 'und weiß alles über alle')
        item = characters.add(self.base, name, 'supporting', short)
        text = (self.base / item['path']).read_text(encoding='utf-8')
        front = yaml.safe_load(text.split('---')[1])
        self.assertEqual((front['name'], front['short']), (name, short))
        self.assertNotIn('\\\n', text)
        _, config = load(self.base)
        self.assertEqual(config['characters'][-1]['name'], name)

    def test_rename_keeps_id_and_validation(self):
        self.add_three()
        characters.update(self.base, 'char-opi', {'name': 'Opa Karl', 'short': ''})
        _, config = load(self.base)
        self.assertEqual(config['characters'][1], {'id': 'char-opi', 'name': 'Opa Karl', 'path': 'characters/char-opi.md'})
        self.assertNotIn('short:', (self.base / 'characters/char-opi.md').read_text(encoding='utf-8'))
        self.assertEqual(validate_project.check_project(self.base), [])
        # unbekannte Figur im Abschnitt und in einer Beziehung
        sec = self.base / config['structure']['chapters'][0]['sections'][1]['path']
        sec.write_text(sec.read_text(encoding='utf-8').replace('approvals:', 'characters: [char-hase]\napprovals:', 1),
                       encoding='utf-8')
        wolf = self.base / 'characters/char-wolf.md'
        wolf.write_text(wolf.read_text(encoding='utf-8').replace('role: minor', 'role: minor\nrelations:\n- to: char-fuchs\n  kind: Bruder'),
                        encoding='utf-8')
        errors = validate_project.check_project(self.base)
        self.assertTrue(any('unbekannte Figur char-hase' in e for e in errors), errors)
        self.assertTrue(any('Beziehung zu unbekannter Figur char-fuchs' in e for e in errors), errors)

    def test_index_and_views(self):
        self.add_three()
        characters.assign(self.base, '1.1', ['Strolchi', 'Opi'])
        characters.assign(self.base, '2.1', ['Strolchi'])
        _, config = load(self.base)
        data = build_index.build(self.base, config)
        self.assertEqual(data['characters'][0], {'id': 'char-strolchi', 'name': 'Strolchi', 'role': 'main',
                                                 'appears_in': ['1.1', '2.1']})
        self.assertEqual(json.loads(build_index.render(data)), data)
        _, ov = self.widget('project')
        self.assertEqual(ov['CHARACTER_COUNT'], 3)
        name, lst = self.widget('characters')
        self.assertEqual(name, 'figuren')
        self.assertEqual([c['C_USED'] for c in lst['CHARACTERS']], ['1.1, 2.1', '1.1', '–'])
        name, one = self.widget('characters', 'Opi')
        self.assertEqual(name, 'figur-bearbeiten')
        self.assertEqual([o['O_ID'] for o in one['OTHERS']], ['char-strolchi', 'char-wolf'])
        _, sec = self.widget('section', '1.1')
        self.assertEqual([c['C_ON'] for c in sec['ALL_CHARACTERS']], ['1', '1', ''])
        self.assertIn('| Figuren | Strolchi, Opi |', self.run_view('section', '1.1', '--text'))
        self.assertIn('`FI` Figuren (3)', self.run_view('project', '--text'))
        self.assertIn('| Wolf | Randfigur | – | – |', self.run_view('characters', '--text'))


class SuggestTest(unittest.TestCase):
    """Figuren aus dem Text vorschlagen: lesen, zeigen, übernehmen (nur leere Felder, Zuordnung ergänzen)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        characters.add(self.base, 'Opi', 'supporting', 'Strolchis Opa')
        characters.assign(self.base, '1.2', ['Opi'])

    def suggestions(self):
        return {'scope': '1', 'items': [
            {'name': 'Strolchi', 'role': 'main', 'short': 'Ein kleiner Hund', 'age': '3', 'traits': ['neugierig'],
             'relations': [{'to': 'Opi', 'kind': 'Hund'}], 'sections': ['1.1', '1.2'],
             'evidence': [{'where': '1.1', 'quote': 'Strolchi bellte.'}]},
            {'name': 'Opa Karl', 'aliases': ['Opi'], 'role': 'supporting', 'short': 'anders', 'age': '78', 'sections': ['1.1']},
            {'name': 'Frau Meier', 'role': 'minor', 'sections': ['1.3'], 'selected': False}]}

    def test_scan(self):
        text, k, n = characters.scan(self.base, '1')
        self.assertIn('- Opi (`char-opi`, Buch)', text)
        self.assertIn('### 1.1 ', text)
        self.assertEqual((k, n), (1, 1))
        text, k, n = characters.scan(self.base, 'book', size=2000)
        self.assertGreater(n, 1)
        self.assertIn(f'Teil 1 von {n}', text)

    def test_view_and_apply(self):
        f = self.tmp / 'v.json'
        f.write_text(json.dumps(self.suggestions()), encoding='utf-8')
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'character-suggest',
                              '--draft', str(f)], capture_output=True, text=True, check=True).stdout
        data = json.loads(re.search(r'GW\.render\("figuren-vorschlag",(.*)\)</script>', out).group(1).replace('<\\/', '</'))
        self.assertEqual([(s['S_NAME'], s['S_STATE']) for s in data['SUGGESTIONS']],
                         [('Strolchi', 'new'), ('Opa Karl', 'existing'), ('Frau Meier', 'new')])
        self.assertEqual(data['SCOPE_TEXT'], 'Kapitel 1')
        text = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'character-suggest',
                               '--draft', str(f), '--text'], capture_output=True, text=True, check=True).stdout
        self.assertIn('| 2 | **Opa Karl** (Opi) | Nebenfigur |', text)
        r = characters.apply_suggestions(self.base, self.suggestions())
        self.assertEqual((r['created'], r['updated']), (['Strolchi'], ['Opi']))
        _, config = load(self.base)
        self.assertEqual([c['name'] for c in config['characters']], ['Opi', 'Strolchi'])
        opi = (self.base / 'characters/char-opi.md').read_text(encoding='utf-8')
        self.assertIn("age: '78'", opi)                       # leeres Feld gefüllt
        self.assertIn('short: Strolchis Opa', opi)            # vorhandenes bleibt
        strolchi = (self.base / 'characters/char-strolchi.md').read_text(encoding='utf-8')
        self.assertIn('- to: char-opi', strolchi)
        self.assertIn('kind: Hund', strolchi)
        heads = {k: characters.section_file(self.base, characters.find_target(config, k))[0].get('characters')
                 for k in ('1.1', '1.2', '1.3')}
        self.assertEqual(heads, {'1.1': ['char-strolchi', 'char-opi'], '1.2': ['char-opi', 'char-strolchi'], '1.3': None})
        self.assertEqual(validate_project.check_project(self.base), [])
        # zweites Mal: nichts doppelt
        r = characters.apply_suggestions(self.base, self.suggestions())
        self.assertEqual((r['created'], r['assigned']), ([], {}))


if __name__ == '__main__':
    unittest.main()
