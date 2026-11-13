"""Analyse im Hintergrund (#123): Figuren über das ganze Buch mit festen KI-Antworten (GHOSTWRITER_FAKE_LLM)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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
                chs[0]['sections'][0]['id']: {'items': [
                    {'name': 'Opi', 'role': 'supporting', 'age': '78', 'appearance': 'grüner Hut', 'sections': ['1.1'],
                     'evidence': [{'field': 'name', 'where': '1.1', 'quote': q1}, {'field': 'age', 'where': '1.1', 'quote': q1},
                                  {'field': 'appearance', 'where': '1.1', 'quote': 'trug einen grünen Hut'}]},
                    {'name': 'Geist', 'evidence': [{'field': 'name', 'where': '1.1', 'quote': 'Der Geist erschien um Mitternacht'}]}]},
                chs[1]['sections'][0]['id']: {'items': [
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
        scoped = analyze.plan(self.base, config, scope='1')
        self.assertEqual(scoped['todo'], 0)
        self.assertGreater(scoped['input_tokens'], 0)  # anderer Umfang braucht neues Zusammenführen
        with patch.object(analyze, 'call_llm', wraps=analyze.call_llm) as call:
            head2 = analyze.run(self.base)
        call.assert_not_called()
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
        # Auch beim tatsächlichen Lauf wird nur der geänderte Kapitelblock extrahiert.
        with patch.object(analyze, 'call_llm', wraps=analyze.call_llm) as call:
            head3 = analyze.run(self.base)
        extracts = [c for c in call.call_args_list if len(c.args) < 7 or c.args[6] != 'merge']
        self.assertEqual(head3['blocks_analysed'], 1)
        self.assertEqual(len(extracts), 1)
        self.assertIn(config['structure']['chapters'][1]['sections'][0]['id'], extracts[0].args[4])

    def test_summaries(self):
        _, config = load(self.base)
        chs = config['structure']['chapters']
        s11 = section_file(self.base, chs[0]['sections'][0])[3]
        s12 = section_file(self.base, chs[0]['sections'][1])[3]
        q11 = ' '.join(s11.split()[10:18])
        q12 = ' '.join(s12.split()[10:18])
        data = json.loads(self.fake.read_text(encoding='utf-8'))
        data['summaries'] = {'extract': {chs[0]['sections'][0]['id']: {
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
            chs[0]['sections'][0]['id']: {'perspective': 'ich', 'tense': 'Präsens', 'tone': 'warm, direkt', 'register': 'gehoben',
                           'evidence': [{'field': 'perspective', 'where': '1.1', 'quote': q1},
                                        {'field': 'tense', 'where': '1.1', 'quote': q1},
                                        {'field': 'tone', 'where': '1.1', 'quote': q1},
                                        {'field': 'register', 'where': '1.1', 'quote': 'nicht im Text vorhanden'}]},
            chs[1]['sections'][0]['id']: {'perspective': 'ich', 'tense': 'Präteritum', 'tone': 'warm',
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
            chs[0]['sections'][0]['id']: {'items': [{'name': w, 'kind': 'Raum', 'short': 'erfunden', 'sections': ['1.1', '1.2'],
                                      'evidence': [{'field': 'name', 'where': '1.1', 'quote': q1}]},
                                     {'name': 'Atlantis', 'evidence': [{'where': '1.1', 'quote': 'Atlantis liegt am Meer'}]}]}},
            'merge': {'groups': []}}
        data['timeline'] = {'extract': {
            chs[0]['sections'][0]['id']: {'events': [{'where': '1.1', 'when': 'eines Morgens', 'what': 'Ein Brief kommt.', 'evidence': [{'where': '1.1', 'quote': q1}]},
                                      {'where': '1.2', 'when': '', 'what': 'Erfunden.', 'evidence': [{'where': '1.2', 'quote': 'gibt es nicht'}]}]},
            chs[1]['sections'][0]['id']: {'events': [{'where': '2.1', 'when': 'sechs Monate später', 'what': 'Der Termin.', 'evidence': [{'where': '2.1', 'quote': q2}]}]}},
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

    def test_continuity(self):
        _, config = load(self.base)
        chs = config['structure']['chapters']
        t11 = section_file(self.base, chs[0]['sections'][0])[3]
        t21 = section_file(self.base, chs[1]['sections'][0])[3]
        q1 = ' '.join(t11.split()[10:18])
        q2 = ' '.join(t21.split()[10:18])
        data = json.loads(self.fake.read_text(encoding='utf-8'))
        data['continuity'] = {'extract': {
            chs[0]['sections'][0]['id']: {'facts': [{'about': 'Brief', 'fact': 'lag sechs Monate', 'where': '1.1', 'quote': q1},
                                     {'about': 'X', 'fact': 'erfunden', 'where': '1.1', 'quote': 'steht nicht im Text'}]},
            chs[1]['sections'][0]['id']: {'facts': [{'about': 'Brief', 'fact': 'lag ein Jahr', 'where': '2.1', 'quote': q2}]}},
            'merge': {'conflicts': [{'facts': [1, 2], 'text': 'Wie lange lag der Brief?'}, {'facts': [2], 'text': 'nur eine'},
                                    {'facts': [1, 7], 'text': 'ins Leere'}]}}
        self.fake.write_text(json.dumps(data), encoding='utf-8')
        head = analyze.run(self.base, 'continuity', now='2026-11-04T01:00:00+01:00')
        res = json.loads((self.base / 'analysis/continuity/run-001.json').read_text(encoding='utf-8'))
        self.assertEqual([c['text'] for c in res['items']], ['Wie lange lag der Brief?'])
        self.assertEqual(res['facts'], 2)
        self.assertEqual(head['dropped_without_evidence'], 1)
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest',
                              '--draft', 'analysis/continuity/run-001.json'], capture_output=True, text=True, check=True).stdout
        page = json.loads(re.search(r'GW\.render\("widerspruch-vorschlag",(.*)\)</script>', out).group(1))
        self.assertEqual([f['F_ON'] for f in page['FACTS']], ['', '1'])   # vorgewählt: die letzte Fundstelle
        sec = self.base / chs[1]['sections'][0]['path']
        before = sec.read_text(encoding='utf-8')
        changed = analyze.apply(self.base, 'run-001', 'continuity', [{'index': 0, 'text': 'Wie lange [lag] der Brief?'}])
        after = sec.read_text(encoding='utf-8')
        self.assertEqual(changed, [chs[1]['sections'][0]['path']])
        self.assertIn('[KONTINUITÄT PRÜFEN: Wie lange (lag) der Brief?]', after)
        self.assertEqual(after.replace(' [KONTINUITÄT PRÜFEN: Wie lange (lag) der Brief?]', ''), before)   # sonst nichts geändert
        self.assertEqual(validate_project.check_project(self.base), [])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'section', '2.1', '--text'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('Kontinuität', out)

    def test_language(self):
        os.environ.pop('GHOSTWRITER_FAKE_LLM')                         # ohne KI: kein Schlüssel nötig
        os.environ.pop(analyze.LT_ENV, None)                           # ohne LanguageTool wie bisher
        env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY')}
        _, config = load(self.base)
        sec = self.base / config['structure']['chapters'][0]['sections'][0]['path']
        long = ' '.join(['wort'] * 45)
        sec.write_text(sec.read_text(encoding='utf-8').rstrip('\n') + f'\n\nDer Garten war groß. Der Garten war still. '
                       f'Der Garten war leer. Ein {long} Ende.\n', encoding='utf-8')
        p = analyze.plan(self.base, config, 'language')
        self.assertEqual((p['input_tokens'], p['output_tokens']), (0, 0))
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/analyze.py'), str(self.base), 'run', '--kind', 'language'],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads((self.base / 'analysis/language/run-001.json').read_text(encoding='utf-8'))
        mine = [h for h in res['items'] if h['where'] == '1.1']
        kinds = {h['kind'] for h in mine}
        self.assertTrue({'long_sentence', 'same_start', 'repetition'} <= kinds, kinds)
        texts = {k: section_file(self.base, x)[3] for k, x in [('1.1', config['structure']['chapters'][0]['sections'][0])]}
        for h in mine:                                                  # Fundstellen stehen wörtlich im Text
            self.assertIn(analyze.norm(h['quote']), analyze.norm(texts['1.1']))
        head = yaml.safe_load(re.match(r'---\n(.*?)\n---', (self.base / 'analysis/language/run-001.md').read_text(encoding='utf-8'), re.S).group(1))
        self.assertIsNone(head['model'])
        self.assertFalse((self.base / 'costs/project.yml').is_file() and any(
            'Sprache' in (e.get('note') or '') for e in yaml.safe_load((self.base / 'costs/project.yml').read_text(encoding='utf-8'))['entries']))
        before = sec.read_text(encoding='utf-8')
        idx = [i for i, h in enumerate(res['items']) if h['where'] == '1.1']
        analyze.apply(self.base, 'run-001', 'language', [{'index': i} for i in idx])
        self.assertEqual(sec.read_text(encoding='utf-8'), before)       # Text unverändert
        hints = yaml.safe_load((self.base / 'story/hints.yml').read_text(encoding='utf-8'))['hints']
        self.assertEqual(len(hints), len(idx))
        self.assertEqual(validate_project.check_project(self.base), [])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'section', '1.1'],
                             capture_output=True, text=True, check=True).stdout
        page = json.loads(re.search(r'GW\.render\("abschnitt-bearbeiten",(.*)\)</script>', out).group(1))
        self.assertEqual(len(page['HINTS']), len(idx))
        # ein neuer Lauf ersetzt die Hinweise der gelesenen Abschnitte
        analyze.run(self.base, 'language')
        analyze.apply(self.base, 'run-002', 'language', [])
        self.assertFalse(yaml.safe_load((self.base / 'story/hints.yml').read_text(encoding='utf-8'))['hints'])

    def test_languagetool_hints(self):
        text = '# Titel\n\nAnna ging ins Hauss. [QUELLE PRÜFEN: Hauss] Das Hauss war , leer und *schön* .\n'
        plain = analyze.lt_plain(text)
        self.assertEqual(len(plain), len(text))                         # Stellen bleiben gleich
        self.assertNotIn('QUELLE', plain)
        self.assertNotIn('#', plain)
        self.assertNotIn('*', plain)

        def hit(word, cat, rule='R', nth=0, reps=()):
            off = [i for i in range(len(text)) if text.startswith(word, i)][nth]
            return {'offset': off, 'length': len(word), 'message': f'Meldung zu {word}.',
                    'replacements': [{'value': r} for r in reps], 'rule': {'id': rule, 'category': {'id': cat}}}
        matches = [hit('Anna', 'TYPOS', 'SPELL'), hit('Hauss', 'TYPOS', 'SPELL', reps=('Haus', 'Hausse')),
                   hit('Hauss', 'TYPOS', 'SPELL', nth=2),               # gleicher Fehler: nur einmal
                   hit(' ,', 'PUNCTUATION', 'COMMA'), hit('schön', 'STYLE', 'STYLE'),   # Stil: nicht gemeldet
                   {'offset': 10 ** 6, 'length': 3, 'rule': {'id': 'X', 'category': {'id': 'GRAMMAR'}}}]
        hints = analyze.languagetool_hints(text, matches, ['Anna'])
        self.assertEqual([h['kind'] for h in hints], ['spelling', 'punctuation'])
        self.assertIn('„Hauss“ → „Haus“ / „Hausse“', hints[0]['text'])
        for h in hints:                                                 # Fundstelle wörtlich aus dem Text
            self.assertIn(analyze.norm(h['quote']), analyze.norm(text))
        self.assertIn('Hauss', hints[0]['quote'])

    def test_languagetool_settings(self):
        _, config = load(self.base)
        self.assertEqual(analyze.lt_language(config), 'de-DE')
        config = dict(config, project=dict(config['project'], language='de-at'))
        self.assertEqual(analyze.lt_language(config), 'de-AT')
        config = dict(config, analysis={'languagetool': {'language': 'de-CH', 'words': ['Quasselstrippe'], 'disabled_rules': ['B', 'A']}})
        self.assertEqual(analyze.lt_language(config), 'de-CH')
        (self.base / 'story').mkdir(exist_ok=True)
        (self.base / 'story/places.yml').write_text(yaml.safe_dump({'places': [
            {'id': 'pl-hof', 'name': 'Gut Lindenhof', 'aliases': ['Lindenhof']}]}, allow_unicode=True), encoding='utf-8')
        words = analyze.lt_words(self.base, config)
        self.assertTrue({'Gut Lindenhof', 'Lindenhof', 'Quasselstrippe'} <= set(words), words)
        with patch.dict(os.environ, {analyze.LT_ENV: ''}):
            self.assertIsNone(analyze.languagetool_options(self.base, config))
            self.assertEqual(analyze.language_context(self.base, config), '')
        with patch.dict(os.environ, {analyze.LT_ENV: 'http://localhost:1'}):
            opts = analyze.languagetool_options(self.base, config)
            self.assertEqual(opts['disabled_rules'], ['A', 'B'])
            self.assertTrue(analyze.language_context(self.base, config).startswith('languagetool:'))
        self.assertEqual(validate_project.check_project(self.base), [])

    def test_language_with_languagetool(self):
        import http.server
        import threading
        import urllib.parse
        os.environ.pop('GHOSTWRITER_FAKE_LLM')
        _, config = load(self.base)
        sec = self.base / config['structure']['chapters'][0]['sections'][0]['path']
        sec.write_text(sec.read_text(encoding='utf-8').rstrip('\n') + '\n\nDas Hauss am Lindenhof war leer.\n', encoding='utf-8')
        (self.base / 'story').mkdir(exist_ok=True)
        (self.base / 'story/places.yml').write_text(yaml.safe_dump({'places': [{'id': 'pl-hof', 'name': 'Lindenhof'}]},
                                                                   allow_unicode=True), encoding='utf-8')
        seen = []

        class Fake(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                form = urllib.parse.parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))
                text = form['text'][0]
                seen.append(form['language'][0])
                matches = [{'offset': m.start(), 'length': len(m.group()), 'message': 'Möglicher Tippfehler gefunden.',
                            'replacements': [{'value': 'Haus'}] if m.group() == 'Hauss' else [],
                            'rule': {'id': 'GERMAN_SPELLER_RULE', 'category': {'id': 'TYPOS'}}}
                           for m in re.finditer(r'Hauss|Lindenhof', text)]
                body = json.dumps({'matches': matches}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        analyze.run(self.base, 'language')                              # ohne LanguageTool
        with patch.dict(os.environ, {analyze.LT_ENV: f'http://127.0.0.1:{server.server_address[1]}'}):
            head = analyze.run(self.base, 'language')
            self.assertEqual(head['blocks_cached'], 0)                  # andere Prüfung: Zwischenspeicher nicht genutzt
            res = json.loads((self.base / 'analysis/language/run-002.json').read_text(encoding='utf-8'))
            spell = [h for h in res['items'] if h['kind'] == 'spelling']
            self.assertEqual([h['where'] for h in spell], ['1.1'])      # „Lindenhof“ ist ein eigenes Wort
            self.assertIn('„Hauss“ → „Haus“', spell[0]['text'])
            self.assertEqual(set(seen), {'de-DE'})
            self.assertIn('LanguageTool (de-DE)', (self.base / 'analysis/language/run-002.md').read_text(encoding='utf-8'))
            n = len(seen)
            self.assertEqual(analyze.run(self.base, 'language')['blocks_analysed'], 0)   # unverändert: kein neuer Aufruf
            self.assertEqual(len(seen), n)
            idx = [i for i, h in enumerate(res['items']) if h['kind'] == 'spelling']
            analyze.apply(self.base, 'run-002', 'language', [{'index': i} for i in idx])
        hints = yaml.safe_load((self.base / 'story/hints.yml').read_text(encoding='utf-8'))['hints']
        self.assertEqual([h['kind'] for h in hints], ['spelling'])
        self.assertEqual(validate_project.check_project(self.base), [])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'section', '1.1', '--text'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('Rechtschreibung', out)
        with patch.dict(os.environ, {analyze.LT_ENV: 'http://127.0.0.1:9'}):   # Server fehlt: klarer Fehler
            sec.write_text(sec.read_text(encoding='utf-8') + '\nNoch ein Satz.\n', encoding='utf-8')
            with self.assertRaises(RuntimeError):
                analyze.run(self.base, 'language')

    def test_section_isolation_and_bounded_requests(self):
        _, config = load(self.base)
        chapter = config['structure']['chapters'][0]
        sections = chapter['sections']
        blocks = list(analyze.blocks(self.base, config, scope='1'))
        self.assertTrue(all(len(texts) == 1 for _, _, texts in blocks))
        self.assertEqual([key for key, _, _ in blocks], [s['id'] for s in sections
                         if section_file(self.base, s)[3].strip() not in ('', 'Noch nicht begonnen.')])
        # A change in one section does not invalidate its siblings.
        analyze.run(self.base, 'style', scope='1')
        path = self.base / sections[0]['path']
        path.write_text(path.read_text() + '\nEin zusätzlicher Satz.\n')
        plan = analyze.plan(self.base, config, 'style', scope='1')
        self.assertEqual(plan['todo'], 1)
        self.assertEqual([b['key'] for b in plan['blocks'] if not b['cached']], [sections[0]['id']])
        # Long sections are losslessly split, every original character is covered.
        long = ('Eine lange Szene. ' * 1700) + '\n\n' + ('Weitere Szene. ' * 1400)
        path.write_text(path.read_text().split('## Manuskript')[0] + '## Manuskript\n\n' + long)
        parts = [(key, texts) for key, _, texts in analyze.blocks(self.base, config, scope='1')
                 if key.startswith(sections[0]['id'] + '--part-')]
        self.assertGreater(len(parts), 1)
        self.assertEqual(''.join(next(iter(texts.values())) for _, texts in parts), long.strip())
        self.assertTrue(all(len(next(iter(texts.values()))) <= analyze.MAX_BLOCK_CHARS for _, texts in parts))
        with patch.object(analyze, 'call_llm', wraps=analyze.call_llm) as call:
            analyze.run(self.base, 'style', scope='1')
        requests = [c.args[4] for c in call.call_args_list]
        self.assertTrue(requests)
        self.assertTrue(all(len(r) < analyze.MAX_BLOCK_CHARS + 500 for r in requests))
        # Parts must remain included in the final weighted statistics.
        result = json.loads((self.base / 'analysis/style/run-002.json').read_text())
        expected = sum(analyze.text_stats(texts)['words'] for _, _, texts in analyze.blocks(self.base, config, scope='1'))
        self.assertEqual(result['stats']['words'], expected)
        # Prompt/model changes invalidate results as well.
        updated = dict(config, analysis={'model': 'another-model'})
        self.assertEqual(analyze.plan(self.base, updated, 'style', scope='1')['cached'], 0)

    def test_bounded_merge_compares_distant_results(self):
        _, config = load(self.base)
        limit = analyze.MAX_BLOCK_CHARS
        seen = []
        def fake(provider, key, model, system, user, kind='characters', step='extract'):
            if step == 'extract':
                return '{}', 0, 0
            seen.append(user)
            return '{"conflicts": []}', 0, 0
        # Use many verified facts to exercise batching rather than manuscript loading.
        facts = [{'about': 'Person ' + str(i), 'fact': 'x' * 1000, 'where': '1.1', 'quote': 'Zitat'}
                 for i in range(20)]
        with patch.object(analyze, 'call_llm', side_effect=fake), patch.object(analyze, 'verify_continuity'):
            spec = dict(analyze.KINDS['continuity'], verify=lambda answer, texts: (facts, 0))
            with patch.dict(analyze.KINDS, {'continuity': spec}):
                analyze.run(self.base, 'continuity', scope='1')
        self.assertGreater(len(seen), 1)
        self.assertTrue(all(len(request) <= limit for request in seen))
        self.assertTrue(any('Person 0:' in request and 'Person 19:' in request for request in seen))

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
