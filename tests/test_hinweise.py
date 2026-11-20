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
            self.assertIn(cmd, ('collect', 'show', 'decide', 'plan', 'apply'), (cmd, project))

    def test_both_orders_parse(self):
        import subprocess
        for args in (['show', str(ROOT / 'tests/fixtures/adhs')], [str(ROOT / 'tests/fixtures/adhs'), 'show']):
            r = subprocess.run([sys.executable, str(ROOT / 'scripts/hinweise.py'), *args], capture_output=True, text=True)
            self.assertNotIn('invalid choice', r.stderr, args)


class MatterAndBookFindingsTest(unittest.TestCase):
    """#423: Befunde zum Nachwort (mat-*) und buchweite Befunde (book) lassen sich ablegen und durchsehen."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        subprocess.run([sys.executable, str(ROOT / 'scripts/matter.py'), str(self.base), 'add', 'afterword'],
                       check=True, capture_output=True)
        _, self.config = load(self.base)
        nachwort = self.base / 'matter/nachwort.md'
        text = nachwort.read_text(encoding='utf-8')
        head, sep, _ = text.partition('\n## Manuskript\n')
        nachwort.write_text(head + sep + '\nDieser Dank geht an alle Leserinnnen und Leser.\n', encoding='utf-8')
        (self.base / 'editorial').mkdir(exist_ok=True)
        findings = {'befunde': [
            {'id': 'b-001', 'abschnitt': 'mat-nachwort', 'art': 'rechtschreibung', 'befund': 'Tippfehler',
             'alt': 'Leserinnnen', 'neu': 'Leserinnen', 'status': 'offen'},
            {'id': 'b-002', 'abschnitt': 'book', 'art': 'wiederholung', 'befund': 'Lieblingswort zu oft',
             'alt': 'eigentlich', 'neu': 'ehrlich gesagt', 'status': 'offen'},
            {'id': 'b-003', 'abschnitt': 'book', 'art': 'kontinuitaet', 'befund': 'Alter der Figur schwankt',
             'status': 'offen'}]}
        (self.base / 'editorial/sprache-buch.yml').write_text(yaml.safe_dump(findings, allow_unicode=True),
                                                              encoding='utf-8')

    def test_validate_accepts_matter_and_book(self):
        self.assertFalse(hinweise.errors(self.base, self.config))
        self.assertFalse([e for e in validate_project.check_project(self.base) if 'editorial' in e])

    def test_collect_show_plan_apply(self):
        path, data = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        self.assertFalse(data.get('ausgelassen'))
        auto = data['ohne_autor']
        self.assertEqual([(e['section_id'], e['abschnitt']) for e in auto], [('mat-nachwort', 'Nachwort')])
        author = {e['befund'].split('#')[1]: e for e in data['autorenentscheidung']}
        self.assertEqual(sorted(author), ['b-002', 'b-003'])
        self.assertEqual(author['b-002']['art'], 'buchweit')       # sprachlich, aber buchweit: Autor entscheidet
        self.assertEqual(author['b-003']['art'], 'kontinuitaet')
        self.assertFalse(hinweise.errors(self.base, self.config))  # Dialogdatei passt zum Schema
        text = hinweise.show(data)
        self.assertIn('**Vor- und Nachspann**', text)
        self.assertNotIn('Kapitel Nachwort', text)
        values, blocks = hinweise.widget_values(self.base, path)
        self.assertEqual(blocks['AUTO'][0]['E_CHAPTER_TEXT'], 'Vor- und Nachspann')
        self.assertEqual(blocks['AUTHOR'][0]['E_CHAPTER_TEXT'], 'Ganzes Buch')
        for e in ('e-001', 'e-002'):
            hinweise.decide(path, e, 'ja')
        items = {e['id']: (mark, why) for mark, e, why in hinweise.plan(self.base, self.config, hinweise.read_yaml(path))}
        self.assertEqual(items['e-001'][0], '✅')
        self.assertEqual(items['e-002'], ('⚠️', 'buchweit: von Hand umsetzen'))
        result = hinweise.apply(self.base, self.config, path)
        self.assertEqual([e['id'] for e in result['applied']], ['e-001'])
        self.assertEqual(result['chapters'], ['mat-nachwort'])
        self.assertIn('Leserinnen und', checks.manuscript(self.base, self.config, 'mat-nachwort'))
        status = {b['id']: b['status'] for b in hinweise.read_yaml(self.base / 'editorial/sprache-buch.yml')['befunde']}
        self.assertEqual(status['b-001'], 'erledigt')

    def test_approved_matter_blocks(self):
        path, _ = hinweise.collect(self.base, self.config, date='2026-11-20', commit='abcdef1')
        hinweise.decide(path, 'e-001', 'ja')
        f = self.base / 'matter/nachwort.md'
        f.write_text(re.sub(r'(?m)^status: .*$', 'status: approved', f.read_text(encoding='utf-8'), count=1),
                     encoding='utf-8')
        items = hinweise.plan(self.base, self.config, hinweise.read_yaml(path))
        self.assertEqual(items[0][0], '⛔')
        self.assertIn('Nachwort ist abgeschlossen', items[0][2])
