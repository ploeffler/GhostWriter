"""#478: Ansicht der Hintergrund-Warteschlange – Widget-Daten und Textfassung, de/en."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_jobs import Base, jobs, ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / 'scripts'))
import queue_view  # noqa: E402
from tests.widget_helpers import widget_json  # noqa: E402

AT = '2026-11-22T20:00:00+00:00'


def rel(base, path):
    return str(Path(path).relative_to(base))


class QueueViewTest(Base):
    def config(self):
        return yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))

    def fill(self):
        a = self.add('sec-01-01', AT, question='Was ist <b>x</b>?')
        self.add('sec-01-02', AT, after=rel(self.base, a))
        c = self.add('sec-02-01', AT, priority=True)
        d = self.add('sec-02-02', AT)
        data = yaml.safe_load(d.read_text())
        data.update({'error': 'Anbieter antwortet nicht', 'failed_at': '2026-11-22T21:00:00+00:00'})
        d.write_text(yaml.safe_dump(data))
        return a, c, d

    def test_groups_and_values(self):
        a, c, d = self.fill()
        values, blocks = queue_view.widget_values(self.base, self.config(), 'de')
        self.assertEqual(values['QUEUE_COUNT_TEXT'], '4 Aufträge')
        self.assertEqual(values['QUEUE_EMPTY'], '')
        pend = blocks['PENDING']
        self.assertEqual([r['J_TITLE'] for r in pend], ['Recherche · 2.1 T', 'Recherche · 1.1 T', 'Recherche · 1.2 T'])
        self.assertEqual(pend[0]['J_PRIORITY_TEXT'], 'vorgezogen')
        self.assertEqual(pend[0]['J_PRIO_DISABLED'], 'disabled')
        self.assertEqual(json.loads(pend[1]['J_ARGS']), {'request': rel(self.base, a)})
        self.assertEqual(pend[2]['J_STATE'], 'blocked')
        self.assertIn(rel(self.base, a), pend[2]['J_BLOCKED_TEXT'])
        self.assertEqual(blocks['FAILED'][0]['J_DETAIL'], 'Anbieter antwortet nicht')
        self.assertEqual(blocks['DONE'], [])

    def test_waiting_budget_row(self):
        a = self.add('sec-01-01', AT)
        data = yaml.safe_load(a.read_text())
        data['waiting'] = 'budget'
        a.write_text(yaml.safe_dump(data))
        pend = queue_view.groups(self.base, self.config())[0]
        self.assertEqual(pend[0]['J_STATE'], 'waiting_budget')
        self.assertIn('Bestätigung', pend[0]['J_STATE_TEXT'])

    def test_text_view_de_en_and_empty(self):
        text = queue_view.text_view(self.base, self.config(), 'de')
        self.assertIn('Keine Aufträge in der Warteschlange.', text)
        self.fill()
        text = queue_view.text_view(self.base, self.config(), 'de')
        self.assertIn('**Hintergrund-Warteschlange** · 4 Aufträge', text)
        self.assertIn('⛓️ Recherche · 1.2 T', text)
        self.assertIn('❌ Recherche · 2.2 T – Anbieter antwortet nicht', text)
        self.assertIn('vorgezogen', text)
        en = queue_view.text_view(self.base, self.config(), 'en')
        self.assertIn('**Background queue** · 4 jobs', en)
        self.assertIn('Only after', en)
        self.assertIn('Research · 2.1 T', en)

    def test_other_types_have_titles(self):
        jobs.enqueue(self.base, 'analysis', fields={'kind': 'characters,style'})
        row = queue_view.groups(self.base, self.config())[0][0]
        self.assertEqual(row['J_TITLE'], 'Analyse · characters,style')

    def test_cli_widget_and_text(self):
        self.fill()
        base = [sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'queue', '--repo', 'o/r']
        text = subprocess.run(base + ['--text'], capture_output=True, text=True, check=True).stdout
        self.assertIn('Hintergrund-Warteschlange', text)
        widget = subprocess.run(base, capture_output=True, text=True, check=True).stdout
        self.assertIn('GW.render("warteschlange"', widget)
        payload = widget_json(widget.split('GW.render("warteschlange",', 1)[1].rsplit(')</script>', 1)[0].replace('<\\/', '</'))
        self.assertEqual(len(payload['PENDING']), 3)
        self.assertEqual(payload['QUEUE_BOOK'], 'B')
        en = subprocess.run(base + ['--language', 'en'], capture_output=True, text=True, check=True).stdout
        self.assertIn('Background queue', en)
