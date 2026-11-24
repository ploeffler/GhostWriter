"""Hinweisdurchsicht in Stufen (#570): Blockierendes, Gruppen, Fünferrunden, „gering“ zugeklappt."""
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import hinweise  # noqa: E402


def entry(n, art='sprache', grund='Dreierreihe', schwere='mittel', alt='a', neu='b', **kw):
    e = {'id': f'e-{n:03d}', 'abschnitt': '1.1', 'chapter_id': 'kap-01', 'art': art, 'grund': grund,
         'schweregrad': schwere, 'entscheidung': 'offen', 'kontext': 'k', 'befund': 'editorial/x.yml#b-%03d' % n}
    if alt is not None:
        e['alt'] = alt
    if neu is not None:
        e['neu'] = neu
    e.update(kw)
    return e


def sample():
    n = iter(range(1, 100))
    author = [entry(next(n), 'fakt', 'Datum widerspricht', 'blockierend', frage='Welches Jahr?')]
    auto = [entry(next(n), grund=f'Dreierreihe von Adjektiven ({i})') for i in range(4)]       # Gruppe (Zahl ignoriert)
    words = ['Bezug unklar', 'Zeitform wechselt', 'Kasus falsch', 'Satz abgebrochen', 'Doppelte Verneinung',
             'Artikel fehlt', 'Pronomen falsch']
    auto += [entry(next(n), art='grammatik', grund=w, schwere='wesentlich' if i == 0 else 'mittel')
             for i, w in enumerate(words)]
    auto += [entry(next(n), art='zeichensetzung', grund=f'Komma {i}', schwere='gering') for i in range(2)]
    return {'buch': 'x', 'erstellt': '2026-11-24', 'ohne_autor': auto, 'autorenentscheidung': author}


class StufenTest(unittest.TestCase):
    def test_stage_order(self):
        data = sample()
        self.assertEqual(hinweise.current(data)[0], 'blockierend')
        data['autorenentscheidung'][0]['entscheidung'] = 'nein'
        name, groups, head = hinweise.current(data)
        self.assertEqual((name, len(groups)), ('gruppen', 1))
        self.assertEqual(len(next(iter(groups.values()))), 4)
        self.assertIn('Stufe 2', head)

    def test_rounds_of_five_by_severity_with_progress(self):
        data = sample()
        data['autorenentscheidung'][0]['entscheidung'] = 'nein'
        for e in data['ohne_autor'][:4]:
            e['entscheidung'] = 'nein'          # Gruppe entschieden
        name, items, head = hinweise.current(data)
        self.assertEqual(name, 'runde')
        self.assertEqual(len(items), 5)
        self.assertEqual(items[0]['schweregrad'], 'wesentlich')
        self.assertIn('Runde 1 von 2', head)
        for e in items:
            e['entscheidung'] = 'ja'
        name, items, head = hinweise.current(data)
        self.assertEqual(len(items), 2)
        self.assertIn('Runde 2 von 2', head)

    def test_gering_collapsed_then_opened(self):
        data = sample()
        for _, e in hinweise.entries(data):
            if e['schweregrad'] != 'gering':
                e['entscheidung'] = 'nein'
        name, items, head = hinweise.current(data)
        self.assertEqual((name, items), ('gering-zu', []))
        self.assertIn('2 geringe', head)
        self.assertEqual(hinweise.current(data, gering=True)[0], 'gering')

    def test_auto_staging_threshold_and_text(self):
        data = sample()
        self.assertTrue(hinweise.staged(data))            # 14 offen
        self.assertFalse(hinweise.staged({'ohne_autor': data['ohne_autor'][:3], 'autorenentscheidung': []}))
        text = hinweise.show_stufen(data)
        self.assertIn('Stufe 1', text)
        self.assertIn('Welches Jahr?', text)
        self.assertNotIn('Dreierreihe', text)             # erst in Stufe 2

    def test_group_decision_and_skipped_without_proposal(self):
        data = sample()
        data['ohne_autor'][3]['neu'] = ''                 # kein Vorschlag
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'durchsicht.yml'
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
            key = hinweise.group_key(data['ohne_autor'][0])
            changed, skipped = hinweise.decide_group(path, hinweise.GROUP_PREFIX + key, 'ja')
            self.assertEqual((len(changed), len(skipped)), (3, 1))
            saved = hinweise.read_yaml(path)
            self.assertEqual([e['entscheidung'] for e in saved['ohne_autor'][:4]], ['ja', 'ja', 'ja', 'offen'])
            self.assertEqual(saved['autorenentscheidung'][0]['entscheidung'], 'offen')   # Blockierendes unberührt
            with self.assertRaises(ValueError):
                hinweise.decide_group(path, key, 'geändert')
            lassen = hinweise.decide_gering(path)
            self.assertEqual(len(lassen), 2)
            self.assertTrue(all(e['entscheidung'] == 'nein' for e in lassen))

    def test_group_open_individually(self):
        data = sample()
        key = hinweise.group_key(data['ohne_autor'][0])
        name, items, _ = hinweise.current(data, group=hinweise.GROUP_PREFIX + key)
        self.assertEqual((name, len(items)), ('gruppe', 4))

    def test_widget_values_follow_stage(self):
        data = sample()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'editorial').mkdir()
            path = base / 'editorial/durchsicht-2026-11-24.yml'
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
            values, blocks = hinweise.widget_values(base, path)
            self.assertEqual([r['E_ID'] for r in blocks['AUTHOR']], ['e-001'])
            self.assertNotIn('AUTO', blocks)
            self.assertIn('Stufe 1', values['REVIEW_COUNT_TEXT'])
            data['autorenentscheidung'][0]['entscheidung'] = 'nein'
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
            values, blocks = hinweise.widget_values(base, path)
            row = blocks['AUTHOR'][0]
            self.assertTrue(row['E_ID'].startswith('gruppe:'))
            self.assertIn('4 Stellen', row['E_WHERE'])
            values, blocks = hinweise.widget_values(base, path, False)     # --alle
            self.assertEqual(len(blocks['AUTO']), 13)


if __name__ == '__main__':
    unittest.main()
