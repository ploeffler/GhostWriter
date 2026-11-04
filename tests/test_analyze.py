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
        self.assertEqual([a['A_RUN'] for a in ov['ANALYSES']], ['analysis/characters/run-002.json'])
        self.assertIn('liegen bereit (1)', ov['ANALYSES'][0]['A_TEXT'])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest',
                              '--draft', ov['ANALYSES'][0]['A_RUN']], capture_output=True, text=True, cwd=self.base); self.assertEqual(out.returncode, 0, out.stderr); out = out.stdout
        page = json.loads(re.search(r'GW\.render\("figuren-vorschlag",(.*)\)</script>', out).group(1))
        self.assertEqual(page['RUN_ID'], 'run-002')
        self.assertIn('Alter: 78 / 80', page['CONFLICTS_TEXT'])
        analyze.mark_applied(self.base, 'run-002')
        self.assertNotIn('ANALYSES', view())
        # nach einer Änderung im Text: nur dieses Kapitel neu
        _, config = load(self.base)
        sec = self.base / config['structure']['chapters'][1]['sections'][0]['path']
        sec.write_text(sec.read_text(encoding='utf-8') + '\nNoch ein Satz.\n', encoding='utf-8')
        self.assertEqual(analyze.plan(self.base, config)['todo'], 1)

    def test_summaries(self):
        _, config = load(self.base)
        chs = config['structure']['chapters']
        s11 = section_file(self.base, chs[0]['sections'][0])[3]
        s12 = section_file(self.base, chs[0]['sections'][1])[3]
        q11 = ' '.join(s11.split()[10:18])
        q12 = ' '.join(s12.split()[10:18])
        data = json.loads(self.fake.read_text(encoding='utf-8'))
        data['summaries'] = {'extract': {chs[0]['id']: {
            'sections': [{'where': '1.1', 'short': 'Ein Brief bleibt liegen.', 'goal': 'Der Leser erkennt sich wieder.',
                          'evidence': [{'field': 'short', 'where': '1.1', 'quote': q11}]},
                         {'where': '1.2', 'short': 'Erfunden.', 'evidence': [{'where': '1.2', 'quote': 'steht so nirgends im Text'}]},
                         {'where': '1.3', 'short': 'Zitat aus dem falschen Abschnitt.', 'evidence': [{'where': '1.3', 'quote': q12}]},
                         {'where': '9.9', 'short': 'Gibt es nicht.', 'evidence': [{'quote': q11}]}],
            'chapter': {'short': 'Die Diagnose kommt.', 'goal': 'Etiketten verstehen.', 'evidence': [{'where': '1.2', 'quote': q12}]}}}}
        self.fake.write_text(json.dumps(data), encoding='utf-8')
        plans = analyze.plan(self.base, config, 'summaries')
        self.assertNotIn('matter', [b['key'] for b in plans['blocks']])     # Vor- und Nachspann nicht
        head = analyze.run(self.base, 'summaries', now='2026-11-04T01:00:00+01:00')
        self.assertIsNone(head['merge_model'])
        self.assertEqual(head['blocks_analysed'], len(plans['blocks']))
        res = json.loads((self.base / 'analysis/summaries/run-001.json').read_text(encoding='utf-8'))
        self.assertEqual(res['kind'], 'summaries')
        self.assertEqual([(i['level'], i['number']) for i in res['items']], [('chapter', '1'), ('section', '1.1')])
        self.assertGreaterEqual(head['dropped_without_evidence'], 3)
        self.assertEqual(validate_project.check_project(self.base), [])
        # Übersicht: Hinweis für Kurzbeschreibungen, Vorlage mit bisherigem Text
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'project'],
                             capture_output=True, text=True, check=True).stdout
        ov = json.loads(re.search(r'GW\.render\("projektuebersicht",(.*)\)</script>', out).group(1))
        self.assertEqual([a['A_KIND'] for a in ov['ANALYSES']], ['summaries'])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest',
                              '--draft', 'analysis/summaries/run-001.json'], capture_output=True, text=True, check=True).stdout
        page = json.loads(re.search(r'GW\.render\("kurzbeschreibung-vorschlag",(.*)\)</script>', out).group(1))
        sec = page['SUGGESTIONS'][1]
        _, goal_now, short_now, _ = section_file(self.base, chs[0]['sections'][0])
        self.assertEqual(sec['S_GOAL_NOW'], goal_now)
        self.assertEqual(sec['S_GOAL_ON'], '' if goal_now else '1')
        txt = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest',
                              '--draft', 'analysis/summaries/run-001.json', '--text'], capture_output=True, text=True, check=True).stdout
        self.assertIn('Kurzbeschreibung und Ziel', txt)
        # Übernehmen: nur gewählte Felder, Text bleibt
        before = section_file(self.base, chs[0]['sections'][0])[3]
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/analyze.py'), str(self.base), 'apply', 'run-001', '--kind', 'summaries',
                            json.dumps({'choices': [{'index': 0, 'goal': 'Kapitelziel neu.'}, {'index': 1, 'short': 'Kurz neu.', 'goal': ''}]})],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        head1, goal1, short1, ms1 = section_file(self.base, chs[0]['sections'][0])
        self.assertEqual((goal1, short1, ms1), (goal_now, 'Kurz neu.', before))
        from render_view import chapter_readme
        _, ch_short, ch_goal = chapter_readme(self.base, chs[0])
        self.assertEqual(ch_goal, 'Kapitelziel neu.')
        self.assertIn('## Abschnitte', (self.base / chs[0]['path'] / 'README.md').read_text(encoding='utf-8'))
        self.assertIsNone(analyze.latest(self.base, 'summaries'))
        self.assertEqual(validate_project.check_project(self.base), [])

    def test_style(self):
        _, config = load(self.base)
        chs = config['structure']['chapters']
        q1 = ' '.join(section_file(self.base, chs[0]['sections'][0])[3].split()[10:16])
        q2 = ' '.join(section_file(self.base, chs[1]['sections'][0])[3].split()[10:16])
        data = json.loads(self.fake.read_text(encoding='utf-8'))
        data['style'] = {'extract': {
            chs[0]['id']: {'perspective': 'ich', 'tense': 'Präsens', 'tone': 'warm, direkt', 'register': 'gehoben',
                           'evidence': [{'field': 'perspective', 'where': '1.1', 'quote': q1},
                                        {'field': 'tense', 'where': '1.1', 'quote': q1},
                                        {'field': 'tone', 'where': '1.1', 'quote': q1},
                                        {'field': 'register', 'where': '1.1', 'quote': 'nicht im Text vorhanden'}]},
            chs[1]['id']: {'perspective': 'ich', 'tense': 'Präteritum', 'tone': 'warm',
                           'evidence': [{'field': 'perspective', 'where': '2.1', 'quote': q2},
                                        {'field': 'tense', 'where': '2.1', 'quote': q2},
                                        {'field': 'tone', 'where': '2.1', 'quote': q2}]}}}
        self.fake.write_text(json.dumps(data), encoding='utf-8')
        head = analyze.run(self.base, 'style', now='2026-11-04T01:00:00+01:00')
        res = json.loads((self.base / 'analysis/style/run-001.json').read_text(encoding='utf-8'))
        fields = {i['field']: i for i in res['items']}
        self.assertNotIn('register', fields)                             # ohne gültige Fundstelle
        self.assertEqual(fields['perspective']['value'], 'ich')
        self.assertEqual(len(fields['tense']['variants']), 1)            # abweichendes Kapitel
        self.assertTrue(fields['tone']['value'].startswith('warm'))
        self.assertGreater(res['stats']['sentence_length_avg'], 0)
        self.assertGreaterEqual(head['dropped_without_evidence'], 1)
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest',
                              '--draft', 'analysis/style/run-001.json'], capture_output=True, text=True, check=True).stdout
        page = json.loads(re.search(r'GW\.render\("stilprofil-vorschlag",(.*)\)</script>', out).group(1))
        self.assertIn('Wörter je Satz', page['STATS_TEXT'])
        self.assertTrue(all(r['S_ON'] == '1' for r in page['SUGGESTIONS']))
        cfg_before = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        idx = [i for i, it in enumerate(res['items']) if it['field'] in ('perspective', 'tone')]
        changed = analyze.apply(self.base, 'run-001', 'style', [{'index': idx[0]}, {'index': idx[1], 'value': 'warm, klar'}])
        self.assertEqual(changed, ['ghostwriter.yml'])
        cfg_after = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        self.assertTrue(cfg_after.startswith(cfg_before.rstrip('\n')))  # Rest bleibt Zeichen für Zeichen
        _, config = load(self.base)
        self.assertEqual(config['style']['perspective'], 'ich')
        self.assertEqual(config['style']['tone'], ['warm', 'klar'])
        self.assertEqual(config['style']['source'], 'analysis/style/run-001')
        self.assertEqual(validate_project.check_project(self.base), [])
        self.assertIsNone(analyze.latest(self.base, 'style'))

    def test_places_timeline(self):
        _, config = load(self.base)
        chs = config['structure']['chapters']
        t11 = section_file(self.base, chs[0]['sections'][0])[3]
        t21 = section_file(self.base, chs[1]['sections'][0])[3]
        w = re.findall(r'[A-ZÄÖÜ][a-zäöüß]{4,}', t11)[0]   # ein Wort aus dem Text als „Ort“
        q1 = next(x for x in re.split(r'(?<=[.!?])\s+', t11) if w in x)[:120].strip()
        q1 = ' '.join(q1.split()[:12])
        if w not in q1:
            q1 = w
        q2 = ' '.join(t21.split()[10:18])
        data = json.loads(self.fake.read_text(encoding='utf-8'))
        data['places'] = {'extract': {
            chs[0]['id']: {'items': [{'name': w, 'kind': 'Raum', 'short': 'erfunden', 'sections': ['1.1', '1.2'],
                                      'evidence': [{'field': 'name', 'where': '1.1', 'quote': q1}]},
                                     {'name': 'Atlantis', 'evidence': [{'where': '1.1', 'quote': 'Atlantis liegt am Meer'}]}]}},
            'merge': {'groups': []}}
        data['timeline'] = {'extract': {
            chs[0]['id']: {'events': [{'where': '1.1', 'when': 'eines Morgens', 'what': 'Ein Brief kommt.', 'evidence': [{'where': '1.1', 'quote': q1}]},
                                      {'where': '1.2', 'when': '', 'what': 'Erfunden.', 'evidence': [{'where': '1.2', 'quote': 'gibt es nicht'}]}]},
            chs[1]['id']: {'events': [{'where': '2.1', 'when': 'sechs Monate später', 'what': 'Der Termin.', 'evidence': [{'where': '2.1', 'quote': q2}]}]}},
            'merge': {'issues': [{'kind': 'jump', 'events': [1, 2], 'text': 'Sechs Monate ohne Übergang.'},
                                 {'kind': 'contradiction', 'events': [99], 'text': 'verweist ins Leere'}]}}
        self.fake.write_text(json.dumps(data), encoding='utf-8')
        analyze.run(self.base, 'places', now='2026-11-04T01:00:00+01:00')
        res = json.loads((self.base / 'analysis/places/run-001.json').read_text(encoding='utf-8'))
        self.assertEqual([i['name'] for i in res['items']], [w])           # Atlantis ohne Fundstelle
        self.assertNotIn('short', res['items'][0])                         # Beschreibung ohne eigene Fundstelle
        self.assertEqual(res['items'][0]['kind'], 'Raum')
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest',
                              '--draft', 'analysis/places/run-001.json'], capture_output=True, text=True, check=True).stdout
        self.assertIn('GW.render("orte-vorschlag"', out)
        analyze.apply(self.base, 'run-001', 'places', [{'index': 0, 'short': 'Ein Raum im Haus.'}])
        pl = yaml.safe_load((self.base / 'story/places.yml').read_text(encoding='utf-8'))['places']
        self.assertEqual((pl[0]['name'], pl[0]['short'], pl[0]['sections']), (w, 'Ein Raum im Haus.', [chs[0]['sections'][0]['id']]))
        # Zeitleiste
        head = analyze.run(self.base, 'timeline', now='2026-11-04T01:00:00+01:00')
        res = json.loads((self.base / 'analysis/timeline/run-001.json').read_text(encoding='utf-8'))
        self.assertEqual([e['n'] for e in res['items']], [1, 2])
        self.assertEqual(res['issues'], [{'kind': 'jump', 'events': [1, 2], 'text': 'Sechs Monate ohne Übergang.'}])
        self.assertEqual(head['blocks_analysed'] + 1, len([e for e in yaml.safe_load(
            (self.base / 'costs/project.yml').read_text(encoding='utf-8'))['entries'] if e['note'].startswith('Zeitleiste')]))
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest',
                              '--draft', 'analysis/timeline/run-001.json'], capture_output=True, text=True, check=True).stdout
        page = json.loads(re.search(r'GW\.render\("zeitleiste-vorschlag",(.*)\)</script>', out).group(1))
        self.assertEqual([e['E_FLAG'] for e in page['EVENTS']], ['1', '1'])
        analyze.apply(self.base, 'run-001', 'timeline', [{'index': 0, 'when': 'eines Morgens', 'what': 'Ein Brief kommt.'},
                                                          {'index': 1}, {'issue': 0}])
        tl = yaml.safe_load((self.base / 'story/timeline.yml').read_text(encoding='utf-8'))
        self.assertEqual([e['id'] for e in tl['events']], ['ev-001', 'ev-002'])
        self.assertEqual(tl['notes'][0]['events'], ['ev-001', 'ev-002'])
        self.assertEqual(validate_project.check_project(self.base), [])
        # ungültige Verweise fallen bei der Prüfung auf
        tl['events'][0]['section'] = 'sec-gibt-es-nicht'
        (self.base / 'story/timeline.yml').write_text(yaml.safe_dump(tl, allow_unicode=True), encoding='utf-8')
        self.assertTrue(any('unbekannt' in e for e in validate_project.check_project(self.base)))

    def test_set_part(self):
        t = '# T\n\n## Ziel des Abschnitts\n\nOffen.\n\n## Kurzbeschreibung\n\nalt\n\n## Manuskript\n\nText\n'
        t = analyze.set_part(t, 'Kurzbeschreibung', 'neu')
        self.assertIn('## Kurzbeschreibung\n\nneu\n\n## Manuskript\n\nText\n', t)
        t = analyze.set_part(t, 'Neu', 'x')
        self.assertIn('## Neu\n\nx\n\n## Manuskript', t)
        self.assertTrue(analyze.set_part('# K\n\n## Ziel des Kapitels\n\nOffen.\n', 'Ziel des Kapitels', 'z').endswith('## Ziel des Kapitels\n\nz\n'))

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
