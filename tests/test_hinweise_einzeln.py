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


def themed_data():
    def e(n, sev, thema):
        return {'id': f'e-{n:03d}', 'befund': f'x#{n}', 'abschnitt': '1.1', 'chapter_id': 'k', 'chapter_status': '', 'datei': '', 'art': 'aufbau',
                'grund': f'g{n}', 'schweregrad': sev, 'entscheidung': 'offen', 'alt': '', 'neu': '', 'kontext': '', 'frage': '?',
                **({'thema': thema} if thema else {})}
    return {'buch': 'x', 'erstellt': '2026-11-25', 'quelle': [], 'anleitung': '', 'ohne_autor': [],
            'themen': [{'id': 'a', 'titel': 'Handlungsjahr'}, {'id': 'b', 'titel': 'Figuren'}],
            'autorenentscheidung': [e(1, 'blockierend', 'a'), e(2, 'mittel', 'a'), e(3, 'mittel', 'a'), e(4, 'mittel', 'b'), e(5, 'gering', None)]}


class CardHeadTest(unittest.TestCase):
    """#608: Stufe, Thema und Fortschritt im Thema auf der Einzelkarte."""

    def test_head_names_stage_theme_and_progress(self):
        data = themed_data()
        by = {e['id']: e for _, e in hinweise.entries(data)}
        self.assertEqual(hinweise.card_head(data, by['e-001']), 'Stufe 1 · Blockierendes, einzeln · 1 offen')
        self.assertEqual(hinweise.card_head(data, by['e-003']), 'Stufe 2 · Thema 1 von 2: Handlungsjahr · 2 von 2 in diesem Thema')
        self.assertEqual(hinweise.card_head(data, by['e-004']), 'Stufe 2 · Thema 2 von 2: Figuren · 1 von 1 in diesem Thema')
        self.assertEqual(hinweise.card_head(data, by['e-005']), 'Stufe 4 · Geringes')
        self.assertIn('Stufe 2 · Thema 1 von 2: Handlungsjahr · 1 von 2 in diesem Thema · Eintrag 2 von 5',
                      hinweise.show_single(data, 'e-002'))
        self.assertEqual(hinweise.card_head({'ohne_autor': [], 'autorenentscheidung': [card(1)]}, card(1)), '')   # ohne Themen wie bisher

    def test_widget_count_text_has_the_head(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'editorial').mkdir()
            path = base / 'editorial' / 'durchsicht-2026-11-25.yml'
            path.write_text(yaml.safe_dump(themed_data(), allow_unicode=True), encoding='utf-8')
            values, _ = hinweise.widget_values(base, path, entry='e-003')
            self.assertTrue(values['REVIEW_COUNT_TEXT'].startswith('Stufe 2 · Thema 1 von 2: Handlungsjahr · 2 von 2 in diesem Thema · Eintrag'))


class NextCardTest(unittest.TestCase):
    """#609 Punkt 3: decide --next-card speichert und gibt die nächste Karte aus."""

    def run_cli(self, base, *args):
        import subprocess
        return subprocess.run([sys.executable, str(ROOT / 'scripts/hinweise.py'), str(base), *args], capture_output=True, text=True)

    def test_decide_and_show_next_card(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / 'b'
            shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
            (base / 'editorial').mkdir(exist_ok=True)
            path = base / 'editorial' / 'durchsicht-2026-11-25.yml'
            data = themed_data()
            for _, e in hinweise.entries(data):
                e['abschnitt'], e['section_id'] = '1.1', 'sec-01-01-der-brief-der-sechs-monate'
                e['chapter_id'] = 'ch-01-endlich-eine-erklaerung'
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
            r = self.run_cli(base, 'decide', 'e-001', '--decision', 'nein', '--file', str(path), '--next-card', '--text')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('e-001: nein', r.stdout)
            self.assertIn('Stufe 1 (Blockierendes) abgeschlossen: Zwischenstand jetzt speichern', r.stderr)
            self.assertIn('Stufe 2 · Thema 1 von 2: Handlungsjahr · 1 von 2 in diesem Thema', r.stdout)   # nächste Karte e-002
            self.assertIn('`e-002`', r.stdout)
            r = self.run_cli(base, 'decide', 'e-002', '--decision', 'ja', '--file', str(path), '--next-card', '--text')
            self.assertNotIn('abgeschlossen', r.stderr)   # Thema noch nicht fertig
            r = self.run_cli(base, 'decide', 'e-003', '--decision', 'ja', '--file', str(path), '--next-card', '--repo', 'o/r')
            self.assertIn('Thema „Handlungsjahr“ abgeschlossen', r.stderr)
            self.assertIn('GW.render("hinweisdurchsicht"', r.stdout)   # Widget für die nächste Karte (e-004), Meldung nur auf stderr
            self.assertIn('Thema 2 von 2: Figuren', r.stdout)
            self.assertNotIn('e-003: ja', r.stdout)
            self.assertEqual(yaml.safe_load(path.read_text(encoding='utf-8'))['autorenentscheidung'][2]['entscheidung'], 'ja')


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


class ProposeAskCheckpointTest(unittest.TestCase):
    """#609: Vorschlag des Assistenten auf der Karte, Rückfragen ohne Entscheidung, Zwischenstand je Thema."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'b'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        (self.base / 'editorial').mkdir(exist_ok=True)
        self.path = self.base / 'editorial' / 'durchsicht-2026-11-25.yml'
        data = themed_data()
        for _, e in hinweise.entries(data):
            e['abschnitt'], e['section_id'], e['chapter_id'] = '1.1', 'sec-01-01-der-brief-der-sechs-monate', 'ch-01-endlich-eine-erklaerung'
        self.path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')

    def cli(self, *args):
        import subprocess
        return subprocess.run([sys.executable, str(ROOT / 'scripts/hinweise.py'), str(self.base), *args], capture_output=True, text=True)

    def test_propose_shows_on_the_card_and_accept_saves_exactly_it(self):
        text = 'Die Überfahrt dauert etwa elf Stunden; Abfahrt am Morgen, Ankunft am Abend.'
        r = self.cli('propose', 'e-002', '--new', text, '--variant', 'Variante eins', '--file', str(self.path))
        self.assertEqual(r.returncode, 0, r.stderr)
        values, blocks = hinweise.widget_values(self.base, self.path, entry='e-002')
        row = blocks['AUTHOR'][0]
        self.assertEqual((row['E_NEW'], row['E_PROPOSED']), (text, '1'))
        self.assertIn('Variante 1: Variante eins', row['E_QUESTION'])
        e = hinweise.decide(self.path, 'e-002', 'ja')                 # „Übernehmen“ ändert `neu` nicht
        self.assertEqual((e['entscheidung'], e['neu'], e['vorschlag_von']), ('ja', text, 'assistent'))
        with self.assertRaisesRegex(ValueError, 'schon entschieden'):
            hinweise.propose(self.path, 'e-002', 'Anders')
        self.assertEqual(self.cli('propose', 'e-003', '--new', ' ', '--file', str(self.path)).returncode, 1)
        # Eintrag ohne Vorschlag: kein Kennzeichen
        self.assertEqual(hinweise.widget_values(self.base, self.path, entry='e-003')[1]['AUTHOR'][0]['E_PROPOSED'], '')

    def test_question_is_not_saved_as_decision(self):
        self.assertTrue(hinweise.looks_like_question('Wie lange segelt man von Trogir nach Triest?'))
        self.assertTrue(hinweise.looks_like_question('„Schätze die Zeit?“ '))
        self.assertFalse(hinweise.looks_like_question('Elf Stunden.'))
        before = self.path.read_text(encoding='utf-8')
        r = self.cli('decide', 'e-002', '--decision', 'geändert', '--new', 'Wie lange segelt man von Trogir nach Triest?',
                     '--file', str(self.path))
        self.assertEqual(r.returncode, 1)
        self.assertIn('Rückfrage', r.stderr)
        self.assertEqual(self.path.read_text(encoding='utf-8'), before)   # nichts gespeichert
        r = self.cli('ask', 'e-002', '--question', 'Wie lange segelt man von Trogir nach Triest?', '--text', '--file', str(self.path))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('nichts entschieden', r.stdout)
        self.assertIn('`e-002`', r.stdout)                                # dieselbe Karte erneut
        self.assertEqual(self.path.read_text(encoding='utf-8'), before)
        r = self.cli('decide', 'e-002', '--decision', 'geändert', '--new', 'Warum nicht?', '--as-text', '--file', str(self.path))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_checkpoint_commits_the_review_file_once(self):
        import subprocess
        g = lambda *a: subprocess.run(['git', '-C', str(self.base), '-c', 'user.name=t', '-c', 'user.email=t@t', *a],
                                      capture_output=True, text=True, check=True).stdout.strip()
        g('init', '-q', '-b', 'main')
        g('add', '-A')
        g('commit', '-qm', 'Start')
        r = self.cli('checkpoint')
        self.assertIn('Nichts zu speichern', r.stdout)
        hinweise.decide(self.path, 'e-001', 'nein')
        env_cmd = ['git', '-C', str(self.base), 'config']
        subprocess.run(env_cmd + ['user.name', 't'], check=True)
        subprocess.run(env_cmd + ['user.email', 't@t'], check=True)
        r = self.cli('checkpoint')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Zwischenstand gespeichert (1 entschieden)', r.stdout)
        self.assertEqual(g('log', '--oneline').count('\n'), 1)             # Start + ein Zwischenstand
        self.assertIn('Hinweisdurchsicht: Zwischenstand (1 von 5 entschieden)', g('log', '-1', '--format=%B'))
        self.assertIn('GhostWriter-Aktion: notes_review.checkpoint', g('log', '-1', '--format=%B'))
        self.assertEqual(g('show', '--stat', '--format=', 'HEAD').count('durchsicht-'), 1)
        self.assertIn('Nichts zu speichern', self.cli('checkpoint').stdout)


class DeletionTest(unittest.TestCase):
    """#615: Eine Streichung ist ein gültiger Vorschlag; apply entfernt den Wortlaut samt überzähligem Leerzeichen."""

    def test_tidy_deletion_mid_paragraph_and_at_the_end(self):
        t = hinweise.tidy_deletion
        self.assertEqual(t('Eins. Zwei. Drei.', 'Zwei.'), 'Eins. Drei.')           # Mitte: ein Leerzeichen bleibt
        self.assertEqual(t('Eins. Zwei.', 'Zwei.'), 'Eins.')                        # Ende: kein Leerzeichen am Schluss
        self.assertEqual(t('Eins. Zwei.\n\nNächster Absatz.', 'Zwei.'), 'Eins.\n\nNächster Absatz.')
        self.assertEqual(t('Zwei. Eins.', 'Zwei.'), 'Eins.')                        # Anfang
        self.assertEqual(t('Er kam , sagte sie.', ', sagte sie'), 'Er kam.')        # Leerzeichen vor dem Satzzeichen entfällt
        self.assertEqual(t('Es war gut (leise) und weit.', ' (leise)'), 'Es war gut und weit.')
        self.assertEqual(t('Wort extra, danach.', ' extra'), 'Wort, danach.')       # vor Satzzeichen kein Leerzeichen

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'b'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        sec = self.config['structure']['chapters'][0]['sections'][0]
        self.sec = sec
        self.file = self.base / sec['path']
        text = self.file.read_text(encoding='utf-8')
        marker = '\n## Manuskript\n'
        head, _, body = text.partition(marker)
        self.mid, self.end = 'Dieser Satz entfällt mitten im Absatz.', 'Dieser Schlusssatz entfällt am Absatzende.'
        body = f'\nAnfang des Absatzes. {self.mid} Weiter im Absatz. {self.end}\n\nNächster Absatz bleibt.\n'
        self.file.write_text(head + marker + body, encoding='utf-8')
        (self.base / 'editorial').mkdir(exist_ok=True)
        self.path = self.base / 'editorial' / 'durchsicht-2026-11-25.yml'

        def entry(n, alt):
            return {'id': f'e-{n:03d}', 'befund': f'x#{n}', 'abschnitt': '1.1', 'section_id': sec['id'], 'chapter_id': self.config['structure']['chapters'][0]['id'],
                    'chapter_status': '', 'datei': sec['path'], 'art': 'aufbau', 'grund': 'erklärender Absatzschluss', 'alt': alt, 'neu': '',
                    'frage': 'Streichen?', 'entscheidung': 'offen', 'kontext': ''}
        data = {'buch': 'x', 'erstellt': '2026-11-25', 'quelle': [], 'anleitung': '', 'ohne_autor': [],
                'autorenentscheidung': [entry(1, self.mid), entry(2, self.end), entry(3, '')]}
        self.path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')

    def test_propose_delete_plan_and_apply(self):
        self.assertEqual(hinweise.plan(self.base, self.config, hinweise.read_yaml(self.path)), [])
        hinweise.decide(self.path, 'e-001', 'ja')
        self.assertEqual(hinweise.plan(self.base, self.config, hinweise.read_yaml(self.path))[0][0], '⚠️')   # ohne Vorschlag wie bisher
        with self.assertRaises(ValueError):
            hinweise.propose(self.path, 'e-003', '')                        # leer ohne --delete bleibt ungültig
        with self.assertRaisesRegex(ValueError, 'nichts zu streichen'):
            hinweise.propose(self.path, 'e-003', '', delete=True)           # ohne alten Wortlaut
        e = hinweise.propose(self.path, 'e-002', '', delete=True)
        self.assertEqual((e['streichen'], e['neu'], e['vorschlag_von']), (True, '', 'assistent'))
        e = hinweise.decide(self.path, 'e-001', 'streichen')                # Entscheidung „streichen“
        self.assertEqual((e['entscheidung'], e['streichen']), ('ja', True))
        hinweise.decide(self.path, 'e-002', 'ja')
        plan = hinweise.plan(self.base, self.config, hinweise.read_yaml(self.path))
        self.assertEqual([(m, e['id'], why) for m, e, why in plan], [('✅', 'e-001', 'streichen'), ('✅', 'e-002', 'streichen')])
        values, blocks = hinweise.widget_values(self.base, self.path, entry='e-002')
        self.assertEqual(blocks['AUTHOR'][0]['E_NEW'], '(entfällt)')
        self.assertIn('> Vorschlag: (entfällt)', hinweise.show_single(hinweise.read_yaml(self.path), 'e-002'))
        result = hinweise.apply(self.base, self.config, self.path)
        self.assertEqual(len(result['applied']), 2)
        body = self.file.read_text(encoding='utf-8').partition('\n## Manuskript\n')[2]
        self.assertEqual(body, '\nAnfang des Absatzes. Weiter im Absatz.\n\nNächster Absatz bleibt.\n')

    def test_new_wording_replaces_an_earlier_deletion(self):
        hinweise.propose(self.path, 'e-001', '', delete=True)
        e = hinweise.propose(self.path, 'e-001', 'Ein kürzerer Satz.')
        self.assertNotIn('streichen', e)
        e = hinweise.decide(self.path, 'e-001', 'streichen')
        e = hinweise.decide(self.path, 'e-001', 'geändert', 'Doch lieber so.')
        self.assertNotIn('streichen', e)
