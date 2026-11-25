"""Hinweisdurchsicht einzeln vorlegen, Varianten wählen, Zusammenhang ohne alten Wortlaut, Themen (#473, #570)."""
import copy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import checks  # noqa: E402
import hinweise  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402


def card(n, **kw):
    e = {'id': f'e-{n:03d}', 'abschnitt': '1.1', 'chapter_id': 'kap-01', 'art': 'aufbau', 'grund': f'Grund {n}',
         'schweregrad': 'mittel', 'entscheidung': 'offen', 'kontext': '', 'alt': '', 'neu': '',
         'befund': f'editorial/x.yml#b-{n:03d}', 'frage': 'Wie?'}
    e.update(kw)
    return e


class SingleTest(unittest.TestCase):
    def data(self):
        return {'buch': 'x', 'erstellt': '2026-11-24', 'ohne_autor': [],
                'autorenentscheidung': [card(1, schweregrad='gering'), card(2),
                                        card(3, schweregrad='blockierend', varianten=['Jahr 1953', 'Jahr 1954'],
                                             kontext='Er kam 1953 an.')]}

    def test_order_progress_and_next(self):
        data = self.data()
        e, n, total, opened = hinweise.single(data)
        self.assertEqual((e['id'], n, total, opened), ('e-003', 1, 3, 3))   # Blockierendes zuerst, Geringes zuletzt
        e['entscheidung'] = 'nein'
        e, n, total, opened = hinweise.single(data)
        self.assertEqual((e['id'], n, opened), ('e-002', 2, 2))
        self.assertEqual(hinweise.single(data, 'e-001')[1], 3)

    def test_text_card(self):
        text = hinweise.show_single(self.data())
        self.assertIn('Eintrag 1 von 3 · noch 3 offen', text)
        self.assertIn('Zusammenhang: Er kam 1953 an.', text)
        self.assertIn('`e-003 variante 1`', text)
        self.assertNotIn('e-002', text)   # genau eine Karte
        done = self.data()
        for _, e in hinweise.entries(done):
            e['entscheidung'] = 'nein'
        self.assertIn('Umsetzen prüfen', hinweise.show_single(done))

    def test_choose_variant(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, 'durchsicht-2026-11-24.yml')
            path.write_text(yaml.safe_dump(self.data(), allow_unicode=True), encoding='utf-8')
            e = hinweise.decide(path, 'e-003', 'ja', variant=2)
            self.assertEqual((e['entscheidung'], e['neu'], e['variante']), ('geändert', 'Jahr 1954', 2))
            with self.assertRaisesRegex(ValueError, 'Variante 3 gibt es nicht'):
                hinweise.decide(path, 'e-003', 'ja', variant=3)

    def test_widget_shows_one_card(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'editorial').mkdir()
            path = base / 'editorial' / 'durchsicht-2026-11-24.yml'
            path.write_text(yaml.safe_dump(self.data(), allow_unicode=True), encoding='utf-8')
            values, blocks = hinweise.widget_values(base, path, entry='next')
            self.assertEqual(values['REVIEW_COUNT_TEXT'], 'Eintrag 1 von 3 · noch 3 offen')
            rows = blocks.get('AUTHOR', []) + blocks.get('AUTO', [])
            self.assertEqual([r['E_ID'] for r in rows], ['e-003'])
            self.assertIn('Variante 2: Jahr 1954', rows[0]['E_QUESTION'])


class ThemesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.sid = self.config['structure']['chapters'][0]['sections'][0]['id']
        self.text = checks.manuscript(self.base, self.config, self.sid)
        (self.base / 'editorial').mkdir(exist_ok=True)

    def write(self, name, data):
        (self.base / 'editorial' / name).write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')

    def finding(self, n, **kw):
        f = {'id': f'b-{n:03d}', 'abschnitt': self.sid, 'art': 'aufbau', 'befund': f'Befund {n}', 'status': 'offen'}
        f.update(kw)
        return f

    def test_themes_across_reports_and_paragraph_context(self):
        self.write('bericht-a-2026-11-21.yml', {'befunde': [self.finding(1), self.finding(2, absatz=1)]})
        self.write('bericht-b-2026-11-24.yml', {
            'befunde': [self.finding(1, muster='dreierreihe'), self.finding(2), self.finding(3, art='sprache', alt='x', neu='y')][:2],
            'themen': [{'id': 'bogen', 'titel': 'Kapitelziel und Bogen klären', 'befunde': ['b-001', 'bericht-a-2026-11-21.yml#b-001']},
                       {'id': 'feinschliff', 'titel': 'Sprachlicher Feinschliff', 'befunde': ['b-002']}]})
        path, data = hinweise.collect(self.base, self.config, date='2026-11-24', commit='abcdef1')
        self.assertEqual([t['id'] for t in data['themen']], ['bogen', 'feinschliff'])
        by = {e['befund']: e for _, e in hinweise.entries(data)}
        self.assertEqual(by['editorial/bericht-a-2026-11-21.yml#b-001']['thema'], 'bogen')   # älterer Bericht zugeordnet
        self.assertEqual(by['editorial/bericht-b-2026-11-24.yml#b-001']['thema'], 'bogen')
        self.assertEqual(by['editorial/bericht-b-2026-11-24.yml#b-001']['muster'], 'dreierreihe')
        self.assertEqual(by['editorial/bericht-b-2026-11-24.yml#b-002']['thema'], 'feinschliff')
        self.assertNotIn('thema', by['editorial/bericht-a-2026-11-21.yml#b-002'])
        self.assertTrue(by['editorial/bericht-a-2026-11-21.yml#b-002']['kontext'])           # #473: Absatz als Zusammenhang
        self.assertFalse(validate_project.check_project(self.base))
        # Stufen: Themen in Reihenfolge, je Thema eine Runde
        name, items, head = hinweise.current(data)
        self.assertEqual(name, 'thema')
        self.assertEqual({e['thema'] for e in items}, {'bogen'})
        self.assertIn('Thema 1 von 2: Kapitelziel und Bogen klären', head)
        for e in items:
            e['entscheidung'] = 'nein'
        name, items, head = hinweise.current(data)
        self.assertEqual((name, [e['thema'] for e in items]), ('thema', ['feinschliff']))
        self.assertIn('Thema 2 von 2', head)
        self.assertIn('hängen zusammen', hinweise.show_stufen(data))

    def test_theme_order_follows_chapters_not_file_names(self):
        """#606: Kapitel 1 zuerst, buchweite Themen ganz vorn, im selben Kapitel die neueste Datei nach Datum."""
        ch = self.config['structure']['chapters']
        s1, s2 = ch[0]['sections'][0]['id'], ch[1]['sections'][0]['id']

        def finding(n, sid):
            return {'id': f'b-{n:03d}', 'abschnitt': sid, 'art': 'aufbau', 'befund': f'Befund {n}', 'status': 'offen'}

        def theme(i, *ids):
            return {'id': i, 'titel': f'Thema {i}', 'befunde': list(ids)}
        # Namenssortierung (a < b < c) widerspricht der Kapitelreihenfolge (Kapitel 2 steht in der alphabetisch ersten Datei)
        self.write('a-kap2-2026-11-21.yml', {'befunde': [finding(1, s2)], 'themen': [theme('kap2', 'b-001')]})
        self.write('b-kap1-2026-11-21.yml', {'befunde': [finding(1, s1)], 'themen': [theme('kap1-alt', 'b-001')]})
        self.write('c-kap1-2026-11-24.yml', {'befunde': [finding(1, s1), finding(2, 'book')],
                                              'themen': [theme('kap1-neu', 'b-001'), theme('buchweit', 'b-002')]})
        self.assertEqual([t['id'] for t in hinweise.collect_themes(self.base, self.config)[0]],
                         ['buchweit', 'kap1-neu', 'kap1-alt', 'kap2'])
        _, data = hinweise.collect(self.base, self.config, date='2026-11-25', commit='abcdef1')
        self.assertEqual([t['id'] for t in data['themen']][0], 'buchweit')
        self.assertLess([t['id'] for t in data['themen']].index('kap1-neu'), [t['id'] for t in data['themen']].index('kap2'))

    def test_minor_findings_stay_in_their_theme(self):
        """#607: geringe Befunde gehören zur Themenrunde (am Ende zugeklappt); ein Thema nur aus Geringem erscheint; Blockierendes bleibt vorn."""
        def e(n, sev, thema):
            return {'id': f'e-{n:03d}', 'befund': f'x#{n}', 'abschnitt': '1.1', 'chapter_id': 'k', 'art': 'aufbau', 'grund': f'g{n}',
                    'schweregrad': sev, 'entscheidung': 'offen', 'thema': thema, 'alt': '', 'neu': '', 'frage': '?'}
        data = {'buch': 'x', 'erstellt': '2026-11-25', 'ohne_autor': [],
                'themen': [{'id': 'a', 'titel': 'Thema A'}, {'id': 'b', 'titel': 'Nur Geringes'}],
                'autorenentscheidung': [e(1, 'blockierend', 'a'), e(2, 'mittel', 'a'), e(3, 'gering', 'a'), e(4, 'gering', 'a'),
                                        e(5, 'gering', 'b'), e(6, 'gering', 'b'), e(7, 'gering', None)]}
        name, items, head = hinweise.current(data)
        self.assertEqual((name, [x['id'] for x in items]), ('blockierend', ['e-001']))
        data['autorenentscheidung'][0]['entscheidung'] = 'ja'
        name, items, head = hinweise.current(data)
        self.assertEqual((name, [x['id'] for x in items]), ('thema', ['e-002']))
        self.assertIn('Thema 1 von 2: Thema A', head)
        self.assertIn('+ 2 geringe zu diesem Thema', head)
        self.assertIn('Blockierendes dazu: e-001', head)
        self.assertIn('2 geringe zu diesem Thema zugeklappt', hinweise.show_stufen(data))
        self.assertEqual([x['id'] for x in hinweise.current(data, gering=True)[1]], ['e-002', 'e-003', 'e-004'])
        for x in data['autorenentscheidung'][1:4]:
            x['entscheidung'] = 'nein'
        name, items, head = hinweise.current(data)   # Thema nur aus Geringem erscheint als Runde
        self.assertEqual((name, [x['id'] for x in items]), ('thema', ['e-005', 'e-006']))
        self.assertIn('Thema 2 von 2: Nur Geringes', head)
        for x in items:
            x['entscheidung'] = 'nein'
        self.assertEqual(hinweise.current(data)[0], 'gering-zu')   # nur das ungeordnete Geringe bleibt zugeklappt
        order = [x['id'] for x in hinweise.ordered(data)]
        self.assertEqual(order[:3], ['e-001', 'e-002', 'e-003'])   # Geringes am Ende seines Themas
        self.assertEqual(order[-1], 'e-007')

    def test_without_themes_nothing_changes(self):
        self.write('bericht-a.yml', {'befunde': [self.finding(1)]})
        _, data = hinweise.collect(self.base, self.config, date='2026-11-24', commit='abcdef1')
        self.assertNotIn('themen', data)
        self.assertEqual(hinweise.current(copy.deepcopy(data))[0], 'runde')


if __name__ == '__main__':
    unittest.main()
