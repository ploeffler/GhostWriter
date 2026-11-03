"""Analyse im Hintergrund (#123): Figuren über das ganze Buch mit festen KI-Antworten (GHOSTWRITER_FAKE_LLM)."""
import json
import os
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
import analyze  # noqa: E402
import validate_project  # noqa: E402
from render_view import load, section_file  # noqa: E402


class AnalyzeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, config = load(self.base)
        chs = config['structure']['chapters']
        q1 = ' '.join(section_file(self.base, chs[0]['sections'][0])[3].split()[:6])
        q2 = ' '.join(section_file(self.base, chs[1]['sections'][0])[3].split()[:6])
        self.fake = self.tmp / 'fake.json'
        self.fake.write_text(json.dumps({
            'extract': {
                chs[0]['id']: {'items': [
                    {'name': 'Opi', 'role': 'supporting', 'age': '78', 'appearance': 'grüner Hut', 'sections': ['1.1'],
                     'evidence': [{'field': 'name', 'where': '1.1', 'quote': q1}, {'field': 'age', 'where': '1.1', 'quote': q1},
                                  {'field': 'appearance', 'where': '1.1', 'quote': 'trug einen grünen Hut'}]},
                    {'name': 'Geist', 'evidence': [{'field': 'name', 'where': '1.1', 'quote': 'Der Geist erschien um Mitternacht'}]}]},
                chs[1]['id']: {'items': [
                    {'name': 'Opa Karl', 'age': '80', 'evidence': [{'field': 'name', 'where': '2.1', 'quote': q2},
                                                                   {'field': 'age', 'where': '2.1', 'quote': q2}]}]}},
            'merge': {'groups': [['Opi', 'Opa Karl']]}}), encoding='utf-8')
        os.environ['GHOSTWRITER_FAKE_LLM'] = str(self.fake)
        self.addCleanup(os.environ.pop, 'GHOSTWRITER_FAKE_LLM', None)

    def test_plan_run_cache(self):
        _, config = load(self.base)
        p = analyze.plan(self.base, config)
        self.assertEqual((p['cached'], p['todo']), (0, len(p['blocks'])))
        self.assertIsNone(p['cost_estimate'])
        head = analyze.run(self.base, now='2026-11-03T22:00:00+01:00')
        self.assertEqual(head['id'], 'run-001')
        data = json.loads((self.base / 'analysis/characters/run-001.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['items']), 1)                         # Geist ohne Fundstelle verworfen, Opi = Opa Karl
        opi = data['items'][0]
        self.assertEqual(sorted([opi['name']] + opi['aliases']), ['Opa Karl', 'Opi'])
        self.assertNotIn('appearance', opi)                             # Zitat steht nicht im Text
        self.assertEqual(data['conflicts'], [{'name': opi['name'], 'field': 'age', 'values': ['78', '80']}])
        self.assertGreaterEqual(head['dropped_without_evidence'], 2)
        costs = yaml.safe_load((self.base / 'costs/project.yml').read_text(encoding='utf-8'))['entries']
        mine = [e for e in costs if e.get('run_id') == 'run-001']
        self.assertEqual({e['source'] for e in mine}, {'action_api'})
        self.assertEqual(len(mine), head['blocks_analysed'] + 1)        # je Block ein Aufruf, dazu Zusammenführen
        self.assertEqual(validate_project.check_project(self.base), [])
        # zweiter Lauf ohne Änderung: alles aus dem Zwischenspeicher, keine Aufrufe
        _, config = load(self.base)
        self.assertEqual(analyze.plan(self.base, config)['todo'], 0)
        head2 = analyze.run(self.base)
        self.assertEqual((head2['blocks_analysed'], head2['input_tokens']), (0, 0))
        # Hinweis in der Übersicht, bis übernommen
        view = lambda: json.loads(re.search(r'GW\.render\("projektuebersicht",(.*)\)</script>', subprocess.run(
            [sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'project'],
            capture_output=True, text=True, check=True).stdout).group(1))
        ov = view()
        self.assertEqual(ov['ANALYSIS_RUN'], 'analysis/characters/run-002.json')
        self.assertIn('liegen bereit (1)', ov['ANALYSIS_TEXT'])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'character-suggest',
                              '--draft', str(self.base / ov['ANALYSIS_RUN'])], capture_output=True, text=True, check=True).stdout
        page = json.loads(re.search(r'GW\.render\("figuren-vorschlag",(.*)\)</script>', out).group(1))
        self.assertEqual(page['RUN_ID'], 'run-002')
        self.assertIn('Alter: 78 / 80', page['CONFLICTS_TEXT'])
        analyze.mark_applied(self.base, 'run-002')
        self.assertNotIn('ANALYSIS_TEXT', view())
        # nach einer Änderung im Text: nur dieses Kapitel neu
        _, config = load(self.base)
        sec = self.base / config['structure']['chapters'][1]['sections'][0]['path']
        sec.write_text(sec.read_text(encoding='utf-8') + '\nNoch ein Satz.\n', encoding='utf-8')
        self.assertEqual(analyze.plan(self.base, config)['todo'], 1)

    def test_no_key(self):
        os.environ.pop('GHOSTWRITER_FAKE_LLM')
        env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY')}
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/analyze.py'), str(self.base), 'run'], capture_output=True,
                           text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('ANTHROPIC_API_KEY', r.stderr)

    def test_prices(self):
        cfg = self.base / 'ghostwriter.yml'
        cfg.write_text(cfg.read_text(encoding='utf-8') + 'analysis:\n  price_input_per_mtok: 1\n  price_output_per_mtok: 5\n',
                       encoding='utf-8')
        _, config = load(self.base)
        self.assertGreater(analyze.plan(self.base, config)['cost_estimate'], 0)
        self.assertEqual(validate_project.check_project(self.base), [])


if __name__ == '__main__':
    unittest.main()
