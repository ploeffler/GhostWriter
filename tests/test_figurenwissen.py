"""#430: Figurengespräch Stufe 2 – Wissensstand einer Figur bis zu einer gewählten Stelle (belegt/angenähert, Kurzform, Serienfigur)."""
import json
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze  # noqa: E402
import characters  # noqa: E402
from render_view import load  # noqa: E402

S11, S12, S21 = 'sec-01-01-der-brief-der-sechs-monate', 'sec-01-02-die-etiketten-die-wir-kennen', 'sec-02-01-der-fragebogen-bei-dem-ich'


class InterviewTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        characters.add(self.base, 'Strolchi', 'main', 'Ein neugieriger kleiner Hund')
        characters.add(self.base, 'Opi', 'supporting')
        characters.assign(self.base, '1.1', ['Strolchi'])
        characters.assign(self.base, '2.1', ['Strolchi', 'Opi'])
        (self.base / 'story').mkdir(exist_ok=True)
        self.events([
            {'id': 'ev-001', 'section': S11, 'when': 'Sommer 1989', 'what': 'Strolchi findet den Brief', 'characters': ['char-strolchi']},
            {'id': 'ev-002', 'section': S11, 'what': 'Der Postbote geht, ohne dass Strolchi ihn sieht', 'characters': ['char-opi']},
            {'id': 'ev-003', 'section': S12, 'what': 'Ein Gespräch in der Küche'},                 # Abschnitt ohne Strolchi: nichts
            {'id': 'ev-004', 'section': S21, 'when': 'Winter', 'what': 'Opi erzählt vom Krieg'},    # ohne Feld, Strolchi kommt vor: angenähert
        ])

    def events(self, events):
        (self.base / 'story/timeline.yml').write_text(yaml.safe_dump({'events': events}, allow_unicode=True), encoding='utf-8')

    def test_knowledge_ends_at_the_chosen_place(self):
        text = characters.interview(self.base, 'Strolchi', '1.2')
        self.assertIn('Wissensstand bis 1.2', text)
        self.assertIn('Strolchi findet den Brief (Quelle: ev-001, 1.1, belegt)', text)
        self.assertNotIn('Postbote', text)         # Ereignis nennt eine andere Figur
        self.assertNotIn('Gespräch in der Küche', text)   # Abschnitt ohne Auftritt der Figur
        self.assertNotIn('Opi erzählt vom Krieg', text)   # nach der Stelle
        later = characters.interview(self.base, 'Strolchi', '2.1')
        self.assertIn('Opi erzählt vom Krieg (Quelle: ev-004, 2.1, angenähert)', later)
        self.assertIn('Quelle: sec-02-01', later)

    def test_before_first_appearance_and_unknown_place(self):
        text = characters.interview(self.base, 'Opi', '1.3')
        self.assertIn('nicht aufgetreten', text)
        self.assertIn('Der Postbote geht (Quelle: ev-002, 1.1, belegt)'.replace('geht (', 'geht, ohne dass Strolchi ihn sieht ('), text)   # Ereignis nennt Opi ausdrücklich
        self.assertNotIn('Strolchi findet den Brief', text)   # nennt nur Strolchi: Opi weiß davon nichts
        with self.assertRaises(SystemExit):
            characters.interview(self.base, 'Strolchi', '99.9')
        with self.assertRaises(SystemExit):
            characters.interview(self.base, 'Gibtsnicht', '1.1')

    def test_chapter_number_means_end_of_that_chapter(self):
        self.assertIn('Wissensstand bis 1.9', characters.interview(self.base, 'Strolchi', '1'))
        self.assertIn('Wissensstand bis 2.1', characters.interview(self.base, 'Strolchi', S21))

    def test_without_timeline_and_figure_without_appearance(self):
        (self.base / 'story/timeline.yml').unlink()
        text = characters.interview(self.base, 'Strolchi', '2.1')
        self.assertIn('Keine Ereignisse in story/timeline.yml', text)
        characters.add(self.base, 'Wolf', 'minor')
        self.assertIn('nicht aufgetreten', characters.interview(self.base, 'Wolf', '2.1'))

    def test_large_output_falls_back_to_short_form_and_says_so(self):
        self.events([{'id': f'ev-{i:03d}', 'section': S11, 'when': 'Sommer 1989', 'characters': ['char-strolchi'],
                      'what': 'Strolchi erlebt etwas sehr Langes ' + 'und Ausführliches ' * 12} for i in range(1, 41)])
        full = characters.interview(self.base, 'Strolchi', '2.1', max_chars=10**6)
        short = characters.interview(self.base, 'Strolchi', '2.1', max_chars=200)
        self.assertLess(len(short), len(full))
        self.assertIn('Kurzform', short)
        self.assertIn('Wegen des Umfangs', short)
        self.assertIn('ev-001', short)

    def test_series_character_uses_series_version(self):
        _, config = load(self.base)
        item = characters.find_character(config, 'Strolchi')
        item['_series'] = 'ser-x'
        with unittest.mock.patch.object(characters, 'find_character', return_value=item):
            self.assertIn('Figur der Serie', characters.interview(self.base, 'Strolchi', '1.1'))

    def test_cli(self):
        self.assertEqual(characters.main(['characters.py', str(self.base), 'interview', 'Strolchi', '--bis', '1.1']), 0)


class TimelineSchemaTest(unittest.TestCase):
    def test_characters_field_is_optional_and_checked(self):
        schema = json.loads((ROOT / 'schemas/timeline.schema.json').read_text(encoding='utf-8'))
        ok = {'events': [{'id': 'ev-001', 'section': 'sec-1', 'what': 'x'}, {'id': 'ev-002', 'section': 'sec-1', 'what': 'y', 'characters': ['char-a']}]}
        jsonschema.validate(ok, schema)
        for bad in (['Strolchi'], 'char-a', ['char-a', 'char-a']):
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate({'events': [{'id': 'ev-001', 'section': 's', 'what': 'x', 'characters': bad}]}, schema)

    def test_verify_keeps_only_names_that_stand_in_the_section(self):
        texts = {'1.1': 'Strolchi sah den Brief. Opi schlief, als es am Sommertag klingelte.'}
        answer = {'events': [{'where': '1.1', 'when': 'Sommertag', 'what': 'Es klingelt', 'characters': ['Strolchi', 'Opi', 'Wolf', ' Opi '],
                              'evidence': [{'where': '1.1', 'quote': 'Opi schlief, als es am Sommertag klingelte'}]}]}
        items, dropped = analyze.verify_timeline(answer, texts)
        self.assertEqual(dropped, 0)
        self.assertEqual(items[0]['characters'], ['Strolchi', 'Opi'])   # „Wolf“ steht nicht im Abschnitt: entfällt

    def test_apply_maps_names_to_ids_and_drops_unknown(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
        characters.add(base, 'Strolchi', 'main')
        characters.add(base, 'Opi Karl', 'supporting')
        _, config = load(base)
        self.assertEqual(analyze.character_ids(config, ['Strolchi', 'Karl', 'Wolf', 'strolchi']), ['char-strolchi', 'char-opi-karl'])
        data = {'items': [{'n': 1, 'where': '1.1', 'when': 'Sommer', 'what': 'Es klingelt', 'characters': ['Strolchi', 'Wolf'],
                           'evidence': [{'quote': 'Es klingelt'}]}], 'issues': []}
        changed = analyze.apply_timeline(base, config, data, [{'index': 0}])
        self.assertEqual(changed, ['story/timeline.yml'])
        events = yaml.safe_load((base / 'story/timeline.yml').read_text(encoding='utf-8'))['events']
        self.assertEqual(events[0]['characters'], ['char-strolchi'])
        jsonschema.validate({'events': events}, json.loads((ROOT / 'schemas/timeline.schema.json').read_text(encoding='utf-8')))


if __name__ == '__main__':
    import unittest.mock  # noqa: F401
    unittest.main()
