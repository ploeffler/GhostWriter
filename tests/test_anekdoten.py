"""#643: Anekdoten sammeln, vorschlagen und anonymisiert einbauen – Buch- und Reihenebene, Rollen, Warnungen."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import anekdoten  # noqa: E402
import series  # noqa: E402

SECTION = '---\nid: sec-01-01\ntitle: Der Streit am Gartenzaun\nstatus: planned\n---\n\n# 1.1\n\n[PLATZHALTER-ANEKDOTE: Konflikt mit dem Nachbarn]\n'


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        (self.base / 'chapters/ch-01/sections').mkdir(parents=True)
        (self.base / 'chapters/ch-01/sections/sec-01-01.md').write_text(SECTION, encoding='utf-8')
        self.write_config({})

    def write_config(self, extra):
        cfg = {'project': {'title_short': 'Band1'}, 'structure': {'chapters': [{'id': 'ch-01', 'title': 'K', 'path': 'chapters/ch-01', 'sections': [
            {'id': 'sec-01-01', 'title': 'Der Streit am Gartenzaun', 'path': 'chapters/ch-01/sections/sec-01-01.md'}]}]}}
        cfg.update(extra)
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding='utf-8')

    def add(self, **kw):
        args = dict(titel='Streit mit dem Nachbarn Herrn Huber', text='Herr Huber aus Linz schüttete 1987 Wasser über den Zaun.\nIch lachte.',
                    personen=['Herr Huber:Nachbar'], ort='Linz', zeit='Sommer 1987', themen=['Nachbarschaft', 'Konflikt'])
        args.update(kw)
        return anekdoten.add(self.base, **args)


class CollectTest(Base):
    def test_add_keeps_original_text_and_validates(self):
        path, data = self.add()
        self.assertEqual(path, self.base / 'anekdoten' / (data['id'] + '.yml'))
        self.assertRegex(data['id'], r'^anek-001-streit-mit-dem-nachbarn')
        saved = yaml.safe_load(path.read_text(encoding='utf-8'))
        self.assertEqual(saved['text'], 'Herr Huber aus Linz schüttete 1987 Wasser über den Zaun.\nIch lachte.')
        self.assertEqual(saved['personen'], [{'name': 'Herr Huber', 'rolle': 'Nachbar'}])
        jsonschema.validate(saved, json.loads((ROOT / 'schemas/anecdote.schema.json').read_text(encoding='utf-8')))
        self.assertEqual(self.add(titel='Zweite')[1]['id'][:8], 'anek-002')
        with self.assertRaises(ValueError):
            anekdoten.add(self.base, titel='', text='x')

    def test_states_free_planned_used(self):
        _, a = self.add()
        self.assertEqual([anekdoten.state(e) for e, _ in anekdoten.entries(self.base)], ['frei'])
        anekdoten.plan(self.base, a['id'], 'sec-01-01')
        self.assertEqual(anekdoten.state(anekdoten.entries(self.base)[0][0]), 'eingeplant')
        anekdoten.plan(self.base, a['id'], clear=True)
        self.assertEqual(anekdoten.state(anekdoten.entries(self.base)[0][0]), 'frei')

    def test_readers_cannot_edit(self):
        self.write_config({'team': [{'github': 'anna', 'role': 'owner'}, {'github': 'ben', 'role': 'editor'}, {'github': 'cleo', 'role': 'reader'}]})
        self.add(actor='ben')
        with self.assertRaisesRegex(ValueError, 'Eigentümer und Bearbeiter'):
            self.add(actor='cleo', titel='X')
        with self.assertRaises(ValueError):
            self.add(actor='unbekannt', titel='Y')


class SuggestAndUseTest(Base):
    def test_suggest_by_marker_and_theme_skips_used(self):
        _, a = self.add()
        _, b = self.add(titel='Der Hund im Kornfeld', text='Ein Hund.', personen=[], ort='Wels', zeit='1990', themen=['Tiere'])
        rows = anekdoten.suggest(self.base, 'sec-01-01')
        self.assertEqual([r['id'] for r in rows], [a['id']])
        self.assertIn('nachbar', ' '.join(rows[0]['passt']).lower())
        self.assertEqual(anekdoten.suggest(self.base, text='[PLATZHALTER-ANEKDOTE: Tiere im Feld]')[0]['id'], b['id'])
        anekdoten.use(self.base, a['id'], 'sec-01-01', 'anonymisiert', 'frei', 'anonymisiert', ['Herr Huber=Herr Maier', 'Linz=Steyr'])
        self.assertEqual(anekdoten.suggest(self.base, 'sec-01-01'), [])

    def test_use_records_replacements_truth_and_consent(self):
        _, a = self.add()
        entry, warnings = anekdoten.use(self.base, a['id'], 'sec-01-01', 'anonymisiert', 'frei', 'anonymisiert',
                                        ['Herr Huber=Herr Maier', 'Linz=Steyr'])
        self.assertEqual(warnings, [])
        u = yaml.safe_load(next((self.base / 'anekdoten').glob('*.yml')).read_text(encoding='utf-8'))['verwendungen'][0]
        self.assertEqual((u['abschnitt'], u['buch'], u['fassung'], u['wahrheit'], u['einverstaendnis']['stand']),
                         ('sec-01-01', 'Band1', 'anonymisiert', 'frei', 'anonymisiert'))
        self.assertEqual(u['ersetzungen'], [{'original': 'Herr Huber', 'im_buch': 'Herr Maier'}, {'original': 'Linz', 'im_buch': 'Steyr'}])
        self.assertEqual(anekdoten.state(entry), 'verwendet')
        self.assertIsNone(entry['eingeplant_fuer'])
        with self.assertRaisesRegex(ValueError, 'Schon in sec-01-01 verwendet'):
            anekdoten.use(self.base, a['id'], 'sec-01-01', 'abgewandelt', 'anlass', 'nicht_noetig', notiz='x')

    def test_second_use_warns_and_inputs_are_checked(self):
        _, a = self.add()
        anekdoten.use(self.base, a['id'], 'sec-01-01', 'abgewandelt', 'anlass', 'nicht_noetig', ['Herr Huber=Herr Maier'], notiz='frei erfunden')
        _, warnings = anekdoten.use(self.base, a['id'], 'sec-02-03', 'abgewandelt', 'anlass', 'nicht_noetig', ['Herr Huber=X'], notiz='ok')
        self.assertTrue(any('Schon verwendet: Band1, sec-01-01' in w for w in warnings))
        for kw in ({'fassung': 'kaputt'}, {'wahrheit': 'kaputt'}, {'einverstaendnis': 'kaputt'}):
            args = dict(fassung='anonymisiert', wahrheit='frei', einverstaendnis='anonymisiert')
            args.update(kw)
            with self.assertRaises(ValueError):
                anekdoten.use(self.base, a['id'], 'sec-09-09', **args)
        with self.assertRaisesRegex(ValueError, 'Begründung'):
            anekdoten.use(self.base, a['id'], 'sec-09-09', 'abgewandelt', 'frei', 'nicht_noetig')
        with self.assertRaisesRegex(ValueError, 'Ersetzung'):
            anekdoten.use(self.base, a['id'], 'sec-09-09', 'abgewandelt', 'frei', 'liegt_vor', ['ohne gleich'])

    def test_missing_replacements_warn_when_persons_named(self):
        _, a = self.add()
        _, warnings = anekdoten.use(self.base, a['id'], 'sec-01-01', 'anonymisiert', 'frei', 'anonymisiert')
        self.assertTrue(any('Keine Ersetzungen' in w for w in warnings))

    def test_check_flags_original_without_consent(self):
        _, a = self.add()
        self.assertEqual(anekdoten.check(self.base), [])
        anekdoten.use(self.base, a['id'], 'sec-01-01', 'original', 'woertlich', 'liegt_vor', notiz='mündlich 24.11.')
        self.assertEqual(anekdoten.check(self.base), [])
        p = next((self.base / 'anekdoten').glob('*.yml'))
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        d['verwendungen'][0]['einverstaendnis'] = {'stand': 'anonymisiert'}
        p.write_text(yaml.safe_dump(d, allow_unicode=True), encoding='utf-8')
        self.assertEqual(len(anekdoten.check(self.base)), 1)
        self.assertEqual(anekdoten.main([str(self.base), 'check']), 1)


class SeriesTest(Base):
    """Reihen-Anekdote liegt auf dem Standard-Branch und ist in jedem Band sichtbar; Doppelverwendung wird gemeldet."""

    def setUp(self):
        super().setUp()
        self.lib = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(self.lib, ignore_errors=True))
        (self.lib / 'series/ser-x').mkdir(parents=True)
        (self.lib / 'series/ser-x/series.yml').write_text(yaml.safe_dump(
            {'id': 'ser-x', 'title': 'Reihe', 'kind': 'standalone', 'volumes': ['buch/b1', 'buch/b2']}), encoding='utf-8')

    def test_series_entry_visible_in_both_volumes_and_double_use_reported(self):
        path, data = anekdoten.add(self.lib, titel='Familienfest', text='Alle stritten.', series_id='ser-x')
        self.assertEqual(path, self.lib / 'series/ser-x/anekdoten' / (data['id'] + '.yml'))
        env = {'GHOSTWRITER_SERIES_DIR': str(self.lib / 'series')}
        with mock.patch.dict(os.environ, env), mock.patch.object(series, 'branch_of', return_value='buch/b1'):
            self.assertEqual([e['id'] for e, _ in anekdoten.entries(self.base)], [data['id']])
            self.assertEqual(anekdoten.entries(self.base)[0][0]['_series'], 'ser-x')
        # Verwendung in Band 1 wird auf dem Standard-Branch festgehalten
        anekdoten.use(self.lib, data['id'], 'sec-01-01', 'anonymisiert', 'frei', 'anonymisiert', series_id='ser-x')
        with mock.patch.dict(os.environ, env), mock.patch.object(series, 'branch_of', return_value='buch/b2'):
            rows = anekdoten.suggest(self.base, text='[PLATZHALTER-ANEKDOTE: Familienfest]')
            self.assertEqual(rows, [])   # schon verwendet: nicht mehr vorgeschlagen
            (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump({'project': {'title_short': 'Band2'}, 'structure': {'chapters': []}}), encoding='utf-8')
            entry, _ = anekdoten.find(self.base, data['id'])
            self.assertEqual(anekdoten.state(entry), 'verwendet')

    def test_series_unknown_and_book_files_untouched(self):
        with self.assertRaisesRegex(ValueError, 'nicht gefunden'):
            anekdoten.add(self.lib, titel='X', text='Y', series_id='ser-nope')
        self.assertFalse((self.base / 'anekdoten').exists())


class CliTest(Base):
    def test_cli_roundtrip(self):
        self.assertEqual(anekdoten.main([str(self.base), 'add', '--titel', 'Kaffee', '--text', 'Der Kaffee war kalt.', '--thema', 'Alltag']), 0)
        self.assertEqual(anekdoten.main([str(self.base), 'list', '--state', 'frei', '--json']), 0)
        self.assertEqual(anekdoten.main([str(self.base), 'use', 'anek-001', '--section', 'sec-01-01', '--fassung', 'abgewandelt',
                                         '--wahrheit', 'anlass', '--einverstaendnis', 'nicht_noetig', '--notiz', 'erfunden']), 0)
        self.assertEqual(anekdoten.main([str(self.base), 'use', 'anek-009', '--section', 's', '--fassung', 'abgewandelt',
                                         '--wahrheit', 'anlass', '--einverstaendnis', 'nicht_noetig', '--notiz', 'x']), 2)


if __name__ == '__main__':
    unittest.main()
