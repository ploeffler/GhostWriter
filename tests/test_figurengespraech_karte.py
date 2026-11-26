"""#431: Steuerkarte für das Figurengespräch – Daten für das Widget, Textfassung, nichts vorangehakt, nichts geändert."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import characters  # noqa: E402
from tests.widget_helpers import widget_json  # noqa: E402


class TalkCardTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        characters.add(self.base, 'Strolchi', 'main', 'Ein neugieriger kleiner Hund')
        characters.add(self.base, 'Opi', 'supporting')
        characters.update(self.base, 'opi', {'traits': ['brummig']})

    def view(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'character-talk', *args, '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def data(self, *args):
        return widget_json(re.search(r'GW\.render\("figurengespraech",(.*)\)</script>', self.view(*args)).group(1))

    def test_start_lists_figures_and_places(self):
        d = self.data()
        self.assertEqual(d['TALK_PHASE'], 'start')
        self.assertEqual([f['F_NAME'] for f in d['FIGURES']], ['Strolchi', 'Opi'])
        values = [p['P_VALUE'] for p in d['PLACES']]
        self.assertIn('1', values)
        self.assertIn('1.1', values)

    def test_active_shows_knowledge_source_and_validates_place(self):
        d = self.data('Opi', '--draft', json.dumps({'phase': 'active', 'until': '1.1'}))
        self.assertEqual((d['TALK_FIGURE_ID'], d['TALK_UNTIL']), ('char-opi', '1.1'))
        self.assertIn('Ereignis', d['TALK_KNOWLEDGE_TEXT'])
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'character-talk', 'Opi', '--draft',
                            json.dumps({'until': '99.9'}), '--repo', 'o/r'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'character-talk', 'Gibtsnicht', '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)

    def test_insights_are_suggestions_with_current_value_and_change_nothing(self):
        before = (self.base / 'characters/char-opi.md').read_text()
        d = self.data('Opi', '--draft', json.dumps({'phase': 'insights', 'insights': [
            {'field': 'traits', 'text': 'geduldig'}, {'field': 'voice', 'text': 'leise'}]}))
        self.assertEqual([(i['I_FIELD'], i['I_CURRENT']) for i in d['INSIGHTS']], [('traits', 'brummig'), ('voice', '–')])
        self.assertEqual((self.base / 'characters/char-opi.md').read_text(), before)      # nichts übernommen
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'character-talk', 'Opi', '--draft',
                            json.dumps({'phase': 'insights', 'insights': [{'field': 'nonsense', 'text': 'x'}]}), '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)                                                  # unbekanntes Feld

    def test_text_versions_in_both_languages(self):
        draft = json.dumps({'phase': 'insights', 'insights': [{'field': 'traits', 'text': 'geduldig'}]})
        de = self.view('Opi', '--text', '--draft', draft)
        en = self.view('Opi', '--text', '--language', 'en', '--draft', draft)
        self.assertIn('Erkenntnisse', de)
        self.assertIn('Insights', en)
        self.assertIn('nichts ist übernommen', de)
        self.assertIn('nothing is applied', en)
        self.assertNotIn('{{', de + en)
        self.assertIn('Gespräch beenden', self.view('Opi', '--text', '--draft', json.dumps({'phase': 'active'})))

    def test_card_mentioned_in_docs(self):
        start = (ROOT / 'START.md').read_text(encoding='utf-8')
        befuellung = (ROOT / 'templates/ui/BEFUELLUNG.md').read_text(encoding='utf-8')
        for action in ('character.talk.start', 'character.talk.end', 'character.talk.until', 'character.talk.switch', 'character.talk.apply'):
            self.assertIn(action, befuellung)
        self.assertIn('character-talk', start)


if __name__ == '__main__':
    unittest.main()
