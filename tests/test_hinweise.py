"""Hinweisdurchsicht (#367, Teil 1): Befunde sammeln, Dialogdatei prüfen, Entscheidungen speichern."""
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
import hinweise  # noqa: E402
import checks  # noqa: E402
import validate_project  # noqa: E402
from render_view import load, section_file  # noqa: E402


def render_status(path):
    return yaml.safe_load(path.read_text(encoding='utf-8').split('---')[1])['status']


class HinweiseTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.ch1 = self.config['structure']['chapters'][0]
        self.s11 = self.ch1['sections'][0]
        text = checks.manuscript(self.base, self.config, self.s11['id'])
        words = [w for w in text.split() if text.count(w) == 1 and w.isalpha() and len(w) > 6]
        self.unique = words[0]
        self.common = max((' ' + w + ' ' for w in set(text.split())), key=text.count)
        self.assertGreater(text.count(self.common), 1)
        (self.base / 'editorial').mkdir(exist_ok=True)
        findings = {'bericht': 'editorial/sprache-kap-01.md', 'befunde': [
            {'id': 'b-001', 'abschnitt': self.s11['id'], 'art': 'rechtschreibung', 'befund': 'Tippfehler',
             'alt': self.unique, 'neu': self.unique + 'x', 'status': 'offen'},
            {'id': 'b-002', 'abschnitt': self.s11['id'], 'art': 'ton', 'befund': 'Ton zu flapsig',
             'richtung': 'sachlicher', 'status': 'offen'},
            {'id': 'b-003', 'abschnitt': self.s11['id'], 'art': 'grammatik', 'befund': 'mehrdeutig',
             'alt': self.common, 'neu': ' sowie ', 'status': 'offen'},
            {'id': 'b-004', 'abschnitt': self.s11['id'], 'art': 'grammatik', 'befund': 'schon behoben',
             'status': 'erledigt'},
            {'id': 'b-005', 'abschnitt': self.s11['id'], 'art': 'zeichensetzung', 'befund': 'ohne Vorschlag',
             'alt': self.unique, 'status': 'offen'}]}
        (self.base / 'editorial/sprache-kap-01.yml').write_text(yaml.safe_dump(findings, allow_unicode=True), encoding='utf-8')

    def test_collect_groups_and_checks(self):
        path, data = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        self.assertEqual(path.name, 'durchsicht-2026-11-20.yml')
        self.assertEqual([e['befund'].split('#')[1] for e in data['ohne_autor']], ['b-001'])
        e = data['ohne_autor'][0]
        self.assertEqual((e['id'], e['abschnitt'], e['entscheidung']), ('e-001', '1.1', 'offen'))
        self.assertIn(self.unique, e['kontext'])
        self.assertGreater(len(e['kontext']), len(self.unique) + 20)
        author = {x['befund'].split('#')[1]: x for x in data['autorenentscheidung']}
        self.assertEqual(sorted(author), ['b-002', 'b-005'])
        self.assertEqual(author['b-002']['frage'], 'sachlicher')
        self.assertEqual([s['befund'].split('#')[1] for s in data['ausgelassen']], ['b-003'])
        self.assertFalse(validate_project.check_project(self.base))

    def test_collect_twice_same_day_keeps_decisions(self):
        """#438: zweite Durchsicht am selben Tag überschreibt nichts."""
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-21', commit='abcdef1')
        hinweise.decide(path, 'e-001', 'geändert', 'Eigene Fassung')
        before = path.read_text(encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '--merge'):
            hinweise.collect(self.base, self.config, date='2026-11-21')
        self.assertEqual(path.read_text(encoding='utf-8'), before)
        # neuer Befund kommt dazu, die Entscheidung bleibt
        f = self.base / 'editorial/sprache-kap-01.yml'
        data = yaml.safe_load(f.read_text(encoding='utf-8'))
        data['befunde'].append({'id': 'b-006', 'abschnitt': self.s11['id'], 'art': 'ton', 'befund': 'neu',
                                'status': 'offen'})
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
        same, merged = hinweise.collect(self.base, self.config, date='2026-11-21', mode='merge')
        self.assertEqual(same, path)
        e1 = next(e for e in merged['ohne_autor'] if e['id'] == 'e-001')
        self.assertEqual((e1['entscheidung'], e1['neu']), ('geändert', 'Eigene Fassung'))
        ids = [e['id'] for _, e in hinweise.entries(merged)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([e['befund'].split('#')[1] for _, e in hinweise.entries(merged)].count('b-006'), 1)
        # weitere Datei für denselben Tag; sie ist dann die neueste
        second, _ = hinweise.collect(self.base, self.config, date='2026-11-21', mode='new')
        self.assertEqual(second.name, 'durchsicht-2026-11-21-2.yml')
        self.assertEqual(hinweise.latest(self.base), second)
        third, _ = hinweise.collect(self.base, self.config, date='2026-11-21', mode='new')
        self.assertEqual(third.name, 'durchsicht-2026-11-21-3.yml')

    def test_decide_and_show(self):
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        hinweise.decide(path, 'e-001', 'geändert', 'Eigene Fassung')
        with self.assertRaises(ValueError):
            hinweise.decide(path, 'e-001', 'geändert')
        with self.assertRaises(ValueError):
            hinweise.decide(path, 'e-999', 'ja')
        data = hinweise.read_yaml(path)
        self.assertEqual((data['ohne_autor'][0]['entscheidung'], data['ohne_autor'][0]['neu']), ('geändert', 'Eigene Fassung'))
        out = hinweise.show(data)
        self.assertIn('#### Ohne Autor lösbar', out)
        self.assertIn('#### Autorenentscheidung', out)
        self.assertIn('1 entschieden', out)
        self.assertNotIn('`e-001`', hinweise.show(data, only_open=True))
        self.assertFalse(validate_project.check_project(self.base))

    def test_chapter_filter_and_validation(self):
        with self.assertRaises(ValueError):
            hinweise.collect(self.base, self.config, chapters=['kap-x'])
        other = self.config['structure']['chapters'][1]['id']
        _, data = hinweise.collect(self.base, self.config, chapters=[other], date='2026-11-20', commit='abcdef1')
        self.assertEqual(data['ohne_autor'] + data['autorenentscheidung'], [])
        bad = yaml.safe_load((self.base / 'editorial/sprache-kap-01.yml').read_text(encoding='utf-8'))
        bad['befunde'][1]['id'] = 'b-001'
        bad['befunde'][2]['abschnitt'] = 'sec-gibtsnicht'
        (self.base / 'editorial/sprache-kap-01.yml').write_text(yaml.safe_dump(bad, allow_unicode=True), encoding='utf-8')
        errs = hinweise.errors(self.base, self.config)
        self.assertTrue(any('ID doppelt: b-001' in e for e in errs), errs)
        self.assertTrue(any('sec-gibtsnicht unbekannt' in e for e in errs), errs)

    def test_schema_author_reason_further_places_and_note(self):
        """YAWA #357: Begründung, weitere Stellen und Umsetzungsvermerk sind erlaubt; „so belassen“ nicht."""
        import json
        from jsonschema import Draft202012Validator
        schema = json.loads((ROOT / 'schemas/notes-review.schema.json').read_text(encoding='utf-8'))
        _, data = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        entry = (data['autorenentscheidung'] or data['ohne_autor'])[0]
        entry.update(entscheidung='geändert', begruendung='bewusst so', notiz='story/chronologie.md angepasst',
                     weitere_ersetzungen=[{'alt': 'a', 'neu': 'b', 'datei': 'x.md'}])
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(data)), [])
        entry['eigene_angabe'] = 'bleibt erhalten'   # weitere Angaben erlaubt
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(data)), [])
        for bad in ({'entscheidung': 'so belassen'}, {'umgesetzt': 'in der Chronologie'},
                    {'weitere_ersetzungen': [{'alt': 'a'}]}):
            with self.subTest(bad=bad):
                broken = {**entry, **bad}
                group = 'autorenentscheidung' if data['autorenentscheidung'] else 'ohne_autor'
                self.assertTrue(list(Draft202012Validator(schema).iter_errors({**data, group: [broken]})))

    def test_plan_apply_and_write_back(self):
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        hinweise.decide(path, 'e-001', 'ja')
        hinweise.decide(path, 'e-002', 'nein')
        items = hinweise.plan(self.base, self.config, hinweise.read_yaml(path))
        self.assertEqual([(m, e['id']) for m, e, _ in items], [('✅', 'e-001')])
        res = hinweise.apply(self.base, self.config, path)
        self.assertEqual([e['id'] for e in res['applied']], ['e-001'])
        text = checks.manuscript(self.base, self.config, self.s11['id'])
        self.assertIn(self.unique + 'x', text)
        self.assertEqual(res['chapters'], [self.ch1['id']])
        self.assertIn('Nachprüfung', hinweise.apply_text(res))
        states = {b['id']: b['status'] for b in yaml.safe_load((self.base / 'editorial/sprache-kap-01.yml').read_text(encoding='utf-8'))['befunde']}
        self.assertEqual((states['b-001'], states['b-005'], states['b-003']), ('erledigt', 'offen', 'offen'))
        author = {e['befund'].split('#')[1]: e for e in hinweise.read_yaml(path)['autorenentscheidung']}
        self.assertEqual(states[author[next(k for k in author if author[k]['id'] == 'e-002')]['befund'].split('#')[1]], 'entschieden')
        with self.assertRaises(ValueError):
            hinweise.decide(path, 'e-001', 'nein')
        self.assertEqual(hinweise.apply(self.base, self.config, path)['applied'], [])
        self.assertFalse(validate_project.check_project(self.base))

    def test_wording_with_ellipsis_other_section_and_messages(self):   # #522
        s12 = self.ch1['sections'][1]
        text12 = checks.manuscript(self.base, self.config, s12['id'])
        everything = ' '.join(checks.manuscript(self.base, self.config, sid) or '' for sid in
                              [s['id'] for c in self.config['structure']['chapters'] for s in c['sections']])
        words12 = [w for w in text12.split() if everything.count(w) == 1 and w.isalpha() and len(w) > 6]
        other = words12[0]
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        data = hinweise.read_yaml(path)
        base_entry = dict(data['ohne_autor'][0])
        mk = lambda i, alt, neu: dict(base_entry, id=f'e-9{i}', alt=alt, neu=neu, entscheidung='ja', befund=f'x#{i}')
        data['ohne_autor'] = [
            mk(1, '… ' + self.unique + ' …', '… ' + self.unique + 'x …'),    # Auslassungspunkte aus dem Befund
            mk(2, other, other + 'y'),                                       # steht in 1.2, Befund nennt 1.1
            mk(3, 'dieser Wortlaut kommt nirgends vor', 'egal'),               # gar nicht
            mk(4, self.common.strip(), 'egal'),                               # mehrfach
        ]
        hinweise.write_yaml(path, data)
        plan = {e['id']: (m, why) for m, e, why in hinweise.plan(self.base, self.config, hinweise.read_yaml(path))}
        self.assertEqual(plan['e-91'][0], '✅')
        self.assertEqual(plan['e-92'][0], '⚠️')
        self.assertIn('steht in 1.2 statt 1.1', plan['e-92'][1])
        self.assertEqual(plan['e-93'], ('⛔', 'Wortlaut nicht gefunden: Text oder Befund prüfen'))
        self.assertEqual(plan['e-94'][0], '⛔')
        self.assertIn('-mal in 1.1 vor', plan['e-94'][1])
        for _, why in plan.values():
            self.assertNotIn('Text hat sich geändert', why)               # das Skript prüft keine Änderung
        res = hinweise.apply(self.base, self.config, path)
        self.assertEqual([e['id'] for e in res['applied']], ['e-91'])
        text = checks.manuscript(self.base, self.config, self.s11['id'])
        self.assertIn(self.unique + 'x', text)
        self.assertNotIn('…', text.split(self.unique + 'x')[1][:3])        # keine Punkte in den Text übernommen
        self.assertIn(self.unique + 'x', res['context'][0][1])
        # unverändert zuerst: steht der Wortlaut mit Punkten wirklich im Text, bleibt er wie er ist
        self.assertEqual(hinweise.wording('Er sagte: Und dann… ging er.', 'Und dann…', 'Und danach…'), ('Und dann…', 'Und danach…'))
        self.assertEqual(hinweise.wording('Er sagte: Und dann ging er.', '… Und dann …', '… Und danach …'), ('Und dann', 'Und danach'))
        self.assertIsNone(hinweise.wording('abc', '…', 'x'))

    def test_matter_and_book_findings(self):   # #423
        import matter
        matter.add(self.base, 'afterword')
        _, self.config = load(self.base)
        item = next(i for i in self.config['structure']['back_matter'] if i['kind'] == 'afterword')
        mp = self.base / item['path']
        mp.write_text(mp.read_text(encoding='utf-8').replace('Noch nicht begonnen.', 'Danke fuer das Lesen dieses Buches.'),
                      encoding='utf-8')
        findings = {'bericht': 'editorial/sprache-buch.md', 'befunde': [
            {'id': 'b-001', 'abschnitt': item['id'], 'art': 'rechtschreibung', 'befund': 'Umlaut',
             'alt': 'fuer', 'neu': 'für', 'status': 'offen'},
            {'id': 'b-002', 'abschnitt': 'book', 'art': 'kontinuitaet', 'befund': 'Name wechselt die Schreibung',
             'status': 'offen'}]}
        (self.base / 'editorial/sprache-buch.yml').write_text(yaml.safe_dump(findings, allow_unicode=True), encoding='utf-8')
        self.assertEqual(hinweise.errors(self.base, self.config), [])
        path, data = hinweise.collect(self.base, self.config, date='2026-11-21', commit='abcdef1')
        mine = {e['befund']: e for e in data['ohne_autor'] + data['autorenentscheidung'] if 'sprache-buch' in e['befund']}
        m = mine['editorial/sprache-buch.yml#b-001']
        self.assertEqual((m['abschnitt'], m['chapter_id']), (item['title'], ''))
        b = mine['editorial/sprache-buch.yml#b-002']
        self.assertEqual((b['abschnitt'], b['art']), ('Buch', 'kontinuitaet'))
        self.assertIn(b, data['autorenentscheidung'])
        self.assertIn(f'**{item["title"]}**', hinweise.show(data))
        self.assertFalse(validate_project.check_project(self.base))
        hinweise.decide(path, m['id'], 'ja')
        hinweise.decide(path, b['id'], 'ja')
        res = hinweise.apply(self.base, self.config, path)
        self.assertEqual([e['id'] for e in res['applied']], [m['id']])
        self.assertIn('Danke für das Lesen', checks.manuscript(self.base, self.config, item['id']))
        self.assertIn(item['id'], res['chapters'])
        self.assertTrue(any('buchweit' in w for _, _, w in res['skipped']))
        hinweise.widget_values(self.base, path)
        _, only = hinweise.collect(self.base, self.config, chapters=[self.ch1['id']], date='2026-11-22', commit='abcdef1')
        self.assertFalse([e for e in only['autorenentscheidung'] if 'sprache-buch' in e['befund']])

    def test_apply_without_befund_reference(self):
        """Dialog aus Markdown-Lektorat ohne `befund` (#386): Ersetzung ja, Rückschreiben überspringen."""
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        hinweise.decide(path, 'e-001', 'ja')
        hinweise.decide(path, 'e-002', 'nein')
        data = hinweise.read_yaml(path)
        for _, e in hinweise.entries(data):
            e.pop('befund', None)
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
        res = hinweise.apply(self.base, self.config, path)
        self.assertEqual([e['id'] for e in res['applied']], ['e-001'])
        self.assertIn(self.unique + 'x', checks.manuscript(self.base, self.config, self.s11['id']))
        states = {b['id']: b['status'] for b in yaml.safe_load((self.base / 'editorial/sprache-kap-01.yml').read_text(encoding='utf-8'))['befunde']}
        self.assertEqual(states['b-001'], 'offen')

    def test_plan_blocks_approved_section(self):
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        hinweise.decide(path, 'e-001', 'ja')
        f = self.base / self.s11['path']
        f.write_text(f.read_text(encoding='utf-8').replace('status: ' + render_status(f), 'status: approved', 1), encoding='utf-8')
        items = hinweise.plan(self.base, self.config, hinweise.read_yaml(path))
        self.assertEqual(items[0][0], '⛔')
        self.assertIn('wieder öffnen', hinweise.plan_text(items))
        self.assertEqual(hinweise.apply(self.base, self.config, path)['applied'], [])
        self.assertNotIn(self.unique + 'x', checks.manuscript(self.base, self.config, self.s11['id']))

    def test_blocking_first_with_variants(self):   # #447
        f = self.base / 'editorial/sprache-kap-01.yml'
        data = yaml.safe_load(f.read_text(encoding='utf-8'))
        data['befunde'].append({'id': 'b-006', 'abschnitt': self.s11['id'], 'art': 'rechtschreibung',
                                'schweregrad': 'blockierend', 'befund': 'Alter der Figur unklar',
                                'alt': self.unique, 'neu': self.unique + 'y', 'frage': 'Wie alt ist sie?',
                                'varianten': ['Alter nennen', 'Szene streichen'], 'status': 'offen'})
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
        path, out = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        self.assertNotIn('b-006', [e['befund'].split('#')[1] for e in out['ohne_autor']])
        first = out['autorenentscheidung'][0]
        self.assertEqual((first['befund'].split('#')[1], first['schweregrad']), ('b-006', 'blockierend'))
        self.assertEqual(first['varianten'], ['Alter nennen', 'Szene streichen'])
        text = hinweise.show(out)
        self.assertIn('⛔ blockierend', text)
        self.assertIn('> Variante 2: Szene streichen', text)
        _, blocks = hinweise.widget_values(self.base, path)
        self.assertTrue(blocks['AUTHOR'][0]['E_REASON'].startswith('⛔ blockierend: '))
        self.assertIn('Variante 1: Alter nennen', blocks['AUTHOR'][0]['E_QUESTION'])
        self.assertEqual(json.loads(blocks['AUTHOR'][0]['E_VARIANTS_JSON']), ['Alter nennen', 'Szene streichen'])   # Knopf je Variante (#630)
        self.assertFalse(validate_project.check_project(self.base))

    def test_full_chapter_check_chain(self):   # #447: Speichern, Nachprüfung, nur „ohne Autor“ umsetzen
        (self.base / 'editorial/sprache-kap-01.md').write_text('# Rundumprüfung Kapitel 1\n', encoding='utf-8')
        for kind in ('structure', 'language', 'proofreading', 'story_memory'):
            checks.record(self.base, self.config, kind, [self.ch1['id']], 'passed_with_notes',
                          report='editorial/sprache-kap-01.md', notes=3)
        path, data = hinweise.collect(self.base, self.config, chapters=[self.ch1['id']], date='2026-11-20',
                                      commit='abcdef1')
        for e in data['ohne_autor']:
            hinweise.decide(path, e['id'], 'ja')
        res = hinweise.apply(self.base, self.config, path, [self.ch1['id']])
        self.assertEqual([e['id'] for e in res['applied']], [e['id'] for e in data['ohne_autor']])
        undecided = hinweise.read_yaml(path)['autorenentscheidung']
        self.assertTrue(undecided and all(e['entscheidung'] == 'offen' for e in undecided))
        for kind in ('proofreading', 'quality_correction'):
            checks.record(self.base, self.config, kind, [self.ch1['id']], 'passed_with_notes', notes=len(undecided))
        log = yaml.safe_load((self.base / 'editorial/checks.yml').read_text(encoding='utf-8'))
        kinds = [e['kind'] for e in log['checks']]
        self.assertEqual(kinds[-6:], ['structure', 'language', 'proofreading', 'story_memory', 'proofreading',
                                      'quality_correction'])
        self.assertFalse(validate_project.check_project(self.base))

    def test_accept_proposals_full_chapter_check(self):   # #565: Vorschläge auch bei Autorenentscheidungen annehmen
        text = checks.manuscript(self.base, self.config, self.s11['id'])
        other = [w for w in text.split() if text.count(w) == 1 and w.isalpha() and len(w) > 6 and w != self.unique][0]
        f = self.base / 'editorial/sprache-kap-01.yml'
        data = yaml.safe_load(f.read_text(encoding='utf-8'))
        data['befunde'] += [
            {'id': 'b-006', 'abschnitt': self.s11['id'], 'art': 'ton', 'befund': 'zu flapsig',
             'alt': other, 'neu': other + 'z', 'status': 'offen'},
            {'id': 'b-007', 'abschnitt': self.s11['id'], 'art': 'ton', 'befund': 'zwei Wege', 'alt': other,
             'neu': other + 'v', 'varianten': ['A', 'B'], 'status': 'offen'},
            {'id': 'b-008', 'abschnitt': self.s11['id'], 'art': 'fakt', 'schweregrad': 'blockierend',
             'befund': 'Alter unklar', 'alt': other, 'neu': other + 'w', 'status': 'offen'},
            {'id': 'b-009', 'abschnitt': 'book', 'art': 'buchweit', 'befund': 'überall', 'alt': 'x', 'neu': 'y',
             'status': 'offen'}]
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
        path, out = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        ref = lambda e: e['befund'].split('#')[1]
        self.assertIn('b-006', [ref(e) for e in out['autorenentscheidung']])
        taken = hinweise.accept(path, [self.ch1['id']])
        self.assertEqual(sorted(ref(e) for e in taken), ['b-001', 'b-006'])
        saved = {ref(e): e for _, e in hinweise.entries(hinweise.read_yaml(path))}
        self.assertEqual((saved['b-006']['entscheidung'], saved['b-006']['angenommen']), ('ja', 'rundumpruefung'))
        for b in ('b-002', 'b-005', 'b-007', 'b-008'):
            self.assertEqual(saved[b]['entscheidung'], 'offen', b)
        self.assertEqual(hinweise.accept(path), [])   # schon entschieden: nichts doppelt
        res = hinweise.apply(self.base, self.config, path, [self.ch1['id']])
        self.assertEqual(sorted(ref(e) for e in res['applied']), ['b-001', 'b-006'])
        self.assertIn(other + 'z', checks.manuscript(self.base, self.config, self.s11['id']))
        self.assertFalse(validate_project.check_project(self.base))

    def test_accept_keeps_approved_sections(self):   # #565: Abgeschlossenes bleibt unverändert
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        self.assertTrue(hinweise.accept(path))
        f = self.base / self.s11['path']
        f.write_text(f.read_text(encoding='utf-8').replace('status: ' + render_status(f), 'status: approved', 1), encoding='utf-8')
        signs = {e['id']: sign for sign, e, _ in hinweise.plan(self.base, self.config, hinweise.read_yaml(path))}
        self.assertEqual(signs, {'e-001': '⛔'})

    def test_widget_and_view(self):
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        hinweise.decide(path, 'e-002', 'nein')
        values, blocks = hinweise.widget_values(self.base, path)
        self.assertEqual(values['REVIEW_FILE'], 'editorial/durchsicht-2026-11-20.yml')
        self.assertEqual(values['REVIEW_DATE_TEXT'], 'Stand 20.11.2026')
        self.assertIn('1 entschieden', values['REVIEW_COUNT_TEXT'])
        self.assertEqual(blocks['AUTO'][0]['E_ID'], 'e-001')
        self.assertTrue(blocks['AUTO'][0]['E_CHAPTER_TEXT'].startswith('Kapitel 1 · '))
        self.assertIn('E_QUESTION', blocks['AUTHOR'][0])
        self.assertEqual(blocks['SKIPPED'][0]['SK_REASON'][:10], 'alter Wort')
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'notes-review', *a,
                                         '--repo', 'o/r'], capture_output=True, text=True, check=True).stdout
        html = run()
        page = json.loads(re.search(r'GW\.render\("hinweisdurchsicht",(.*)\)</script>', html).group(1))
        self.assertEqual(page['AUTO'][0]['E_ID'], 'e-001')
        self.assertIn('#### Ohne Autor lösbar', run('editorial/durchsicht-2026-11-20.yml', '--text'))

    def test_cli(self):
        self.assertEqual(hinweise.main(['collect', str(self.base), '--date', '2026-11-20']), 0)
        self.assertEqual(hinweise.main(['decide', str(self.base), 'e-001', '--decision', 'ja']), 0)
        self.assertEqual(hinweise.main(['show', str(self.base), '--open']), 0)
        self.assertEqual(hinweise.main(['accept', str(self.base)]), 0)
        self.assertEqual(hinweise.main(['plan', str(self.base)]), 0)
        self.assertEqual(hinweise.main(['apply', str(self.base)]), 0)


if __name__ == '__main__':
    unittest.main()


class DocumentedCallsTest(unittest.TestCase):
    """#383: dokumentierte Aufrufe von hinweise.py passen zur CLI, auch in der Reihenfolge <buch> <befehl>."""

    def test_documented_order(self):
        import re as _re
        text = (ROOT / 'templates/ui/BEFUELLUNG.md').read_text(encoding='utf-8')
        calls = _re.findall(r'hinweise\.py (\S+) (\S+)', text)
        self.assertTrue(calls)
        for cmd, project in calls:
            self.assertIn(cmd, ('collect', 'show', 'decide', 'accept', 'plan', 'apply', 'propose', 'ask', 'checkpoint'), (cmd, project))

    def test_both_orders_parse(self):
        import subprocess
        for args in (['show', str(ROOT / 'tests/fixtures/adhs')], [str(ROOT / 'tests/fixtures/adhs'), 'show']):
            r = subprocess.run([sys.executable, str(ROOT / 'scripts/hinweise.py'), *args], capture_output=True, text=True)
            self.assertNotIn('invalid choice', r.stderr, args)
