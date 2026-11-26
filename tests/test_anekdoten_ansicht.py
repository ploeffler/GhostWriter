"""#643: Anekdoten-Ansicht (Vorlage anekdoten) und Marke in der Kapitelansicht – Liste, Vorschläge je Abschnitt, Textfassung,
kein Originaltext im Widget, Abschnittsnummer statt Kennung."""
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
import anekdoten  # noqa: E402
from tests.widget_helpers import widget_json  # noqa: E402

SEC1 = 'sec-01-01-der-brief-der-sechs-monate'
SEC2 = 'sec-01-02-die-etiketten-die-wir-kennen'


class AnecdoteViewTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.a = anekdoten.add(self.base, 'Der Brief vom Amt', 'Geheimer Originaltext mit Herrn Huber aus Linz.',
                                  themen=['Brief', 'Warten'], personen=['Herr Huber:Sachbearbeiter'])
        _, self.b = anekdoten.add(self.base, 'Etiketten im Supermarkt', 'Noch ein Original.', themen=['Etiketten'])

    def run_view(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args, '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def data(self, template, *args):
        return widget_json(re.search(r'GW\.render\("' + template + r'",(.*)\)</script>', self.run_view(*args)).group(1))

    def test_list_shows_states_and_never_the_original(self):
        anekdoten.plan(self.base, self.b['id'], '1.2')
        out = self.run_view('anecdotes')
        self.assertNotIn('Geheimer Originaltext', out)
        d = self.data('anekdoten', 'anecdotes')
        self.assertEqual(d['ANEC_MODE'], 'list')
        states = {r['A_ID']: r['A_STATE'] for r in d['ANECDOTES']}
        self.assertEqual(states, {self.a['id']: 'frei', self.b['id']: 'eingeplant'})
        planned = next(r for r in d['ANECDOTES'] if r['A_ID'] == self.b['id'])
        self.assertEqual(planned['A_PLANNED_TEXT'], 'eingeplant für 1.2')
        self.assertIn('2 Anekdoten', d['ANEC_COUNT_TEXT'])

    def test_section_mode_accepts_number_and_ranks(self):
        d = self.data('anekdoten', 'anecdotes', '1.1')
        self.assertEqual(d['ANEC_MODE'], 'section')
        self.assertEqual(d['ANEC_SECTION_ID'], SEC1)
        self.assertEqual(d['ANEC_SECTION_NUMBER'], '1.1')
        self.assertEqual(d['ANECDOTES'][0]['A_ID'], self.a['id'])
        self.assertIn('brief', d['ANECDOTES'][0]['A_MATCH_TEXT'])

    def test_text_version(self):
        out = self.run_view('anecdotes', '--text')
        self.assertIn('### 💬 Anekdoten', out)
        self.assertIn(self.a['id'], out)
        self.assertNotIn('GW.render', out)

    def test_unknown_section(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'anecdotes', '1.99', '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)

    def test_hints_from_check(self):
        anekdoten.use(self.base, self.a['id'], '1.1', 'original', 'woertlich', 'liegt_vor', notiz='mündlich')
        p = next((self.base / 'anekdoten').glob(self.a['id'] + '.yml'))
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        d['verwendungen'][0]['einverstaendnis'] = {'stand': 'offen'}
        p.write_text(yaml.safe_dump(d, allow_unicode=True), encoding='utf-8')
        self.assertEqual(len(self.data('anekdoten', 'anecdotes')['HINTS']), 1)

    def test_chapter_view_marks_sections(self):
        anekdoten.plan(self.base, self.b['id'], SEC2)
        anekdoten.use(self.base, self.a['id'], SEC1, 'anonymisiert', 'frei', 'anonymisiert')
        d = self.data('kapitelansicht', 'chapter', '1')
        rows = d['SECTIONS']
        if isinstance(rows, dict):   # gepackte Zeilen (#674)
            rows = [dict(zip(rows['k'], r)) for r in rows['r']]
        by = {r['SECTION_ID']: r for r in rows}
        self.assertEqual(by[SEC1].get('SECTION_ANECDOTE_TEXT'), 'enthält Anekdote')
        self.assertEqual(by[SEC1].get('SECTION_ANECDOTE_HINT'), 'Der Brief vom Amt')
        self.assertEqual(by[SEC2].get('SECTION_ANECDOTE_TEXT'), 'Anekdote eingeplant')

    def test_plan_with_section_number(self):
        e = anekdoten.plan(self.base, self.a['id'], '1.2')
        self.assertEqual(e['eingeplant_fuer'], SEC2)


if __name__ == '__main__':
    unittest.main()
