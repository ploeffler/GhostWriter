"""Chronologie aus Unterlagen (#354): Schema, Prüfung ohne KI, Textansicht."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import chronology as chr_  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402


def entry(i, kind='event', **kw):
    return dict({'id': f'chr-{i:03d}', 'kind': kind, 'what': kw.pop('what', f'Eintrag {i}'),
                 'status': kw.pop('status', 'documented')}, **kw)


def kinds(found):
    return sorted(f['kind'] for f in found)


class FindingsTest(unittest.TestCase):
    def test_partial_dates_are_ranges(self):
        self.assertEqual([str(d) for d in chr_.interval('1944')], ['1944-01-01', '1944-12-31'])
        self.assertEqual([str(d) for d in chr_.interval('2024-02')], ['2024-02-01', '2024-02-29'])
        self.assertIsNone(chr_.interval(''))

    def test_spans_overlap_only_at_different_places_and_gaps(self):
        data = {'entries': [
            entry(1, 'span', what='Kindheit', characters=['char-anna'], place='Graz', **{'from': '1930', 'to': '1944'}),
            entry(2, 'span', what='Lehre', characters=['char-anna'], place='Wien', **{'from': '1943', 'to': '1946'}),
            entry(3, 'span', what='Ehe', characters=['char-anna'], place='Linz', **{'from': '1950'}),
            # gleicher Ort darf sich überschneiden; Grenzjahr 1944/1944 ist keine sichere Überschneidung
            entry(4, 'span', what='Schule', characters=['char-anna'], place='Graz', **{'from': '1936', 'to': '1940'}),
            entry(5, 'span', what='Hof', characters=['char-ben'], place='Graz', **{'from': '1930', 'to': '1944'}),
            entry(6, 'span', what='Krieg', characters=['char-ben'], place='Front', **{'from': '1944', 'to': '1945'}),
        ]}
        found = chr_.findings(data, {'char-anna': 'Anna'})
        self.assertEqual(kinds(found), ['gap', 'overlap'])
        self.assertIn('Anna', found[0]['text'] + found[1]['text'])
        self.assertEqual([f['entries'] for f in found if f['kind'] == 'overlap'], [['chr-001', 'chr-002']])
        self.assertEqual([f['entries'] for f in found if f['kind'] == 'gap'], [['chr-002', 'chr-003']])
        self.assertNotIn(['chr-005', 'chr-006'], [f['entries'] for f in found])

    def test_two_dates_source_conflict_and_same_as(self):
        data = {'entries': [
            entry(1, what='Hochzeit in Graz', date='1948-06'),
            entry(2, what='Hochzeit  in graz', date='1949', status='reported', source='Gespräch mit Tante Maria'),
            entry(3, what='Umzug', date='1952', status='reported'),
            entry(4, what='Umzug nach Linz', date='1953', status='uncertain', same_as='chr-003'),
            entry(5, what='Taufe', date='1949-03', status='reported'),
            entry(6, what='Taufe', date='1949', status='reported'),   # passt zusammen
        ]}
        found = chr_.findings(data)
        self.assertEqual(kinds(found), ['source', 'two_dates'])
        self.assertIn('gegen belegt 1948-06', found[1]['text'] if found[1]['kind'] == 'source' else found[0]['text'])

    def test_birth_death_and_age(self):
        data = {'entries': [
            entry(1, 'birth', characters=['char-anna'], date='1930-05-10'),
            entry(2, 'death', characters=['char-anna'], date='1990'),
            entry(3, what='Brief an Anna', characters=['char-anna'], date='1992'),
            entry(4, what='Erste Schule', characters=['char-anna'], date='1929'),
            entry(5, what='Firmung', characters=['char-anna'], date='1942', age=12),
            entry(6, what='Matura', characters=['char-anna'], date='1948', age=12),
            entry(7, 'span', what='Pension', characters=['char-anna'], **{'from': '1985', 'to': '1995'}),
            entry(8, what='Notiz ohne Datum'),
        ]}
        found = chr_.findings(data)
        self.assertEqual(kinds(found), ['after_death', 'after_death', 'age', 'before_birth', 'undated'])
        self.assertIn('nach dem Geburtsdatum (1930-05-10) 17–18', [f for f in found if f['kind'] == 'age'][0]['text'])

    def test_empty_and_missing(self):
        self.assertEqual(chr_.findings({'entries': []}), [])
        self.assertEqual(chr_.findings(None), [])


class BookTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.chapter = self.config['structure']['chapters'][0]['id']

    def write(self, entries):
        (self.base / 'story').mkdir(exist_ok=True)
        (self.base / 'story/chronology.yml').write_text(yaml.safe_dump({'entries': entries}, allow_unicode=True), encoding='utf-8')

    def errors(self):
        _, config = load(self.base)
        return validate_project.story_errors(self.base, config)

    def view(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'timeline', '--text', *args,
                            '--repo', 'o/r'], capture_output=True, text=True, check=True)
        return r.stdout

    def test_validation(self):
        self.write([entry(1, date='1944', chapter=self.chapter, source='research/sources.md'),
                    entry(2, 'span', **{'from': '1950', 'to': '1948'}),
                    entry(3, date='1944-13'),
                    entry(4, 'birth', date='1930', characters=['char-niemand']),
                    entry(5, date='1950', same_as='chr-099', place='pl-unbekannt', chapter='ch-gibt-es-nicht')])
        errs = self.errors()
        self.assertTrue(any('chr-003' in e or '1944-13' in e for e in errs), errs)   # Schema: ungültiger Monat
        self.write([entry(1, date='1944', chapter=self.chapter, source='research/sources.md'),
                    entry(2, 'span', **{'from': '1950', 'to': '1948'}),
                    entry(4, 'birth', date='1930', characters=['char-niemand']),
                    entry(5, date='1950', same_as='chr-099', place='pl-unbekannt', chapter='ch-gibt-es-nicht'),
                    entry(6, 'event', **{'from': '1950'}), entry(6, date='1951')])
        errs = '\n'.join(self.errors())
        for text in ('chr-002: Ende vor dem Beginn', 'Figur char-niemand unbekannt', 'same_as chr-099 unbekannt',
                     'Ort pl-unbekannt unbekannt', 'Kapitel ch-gibt-es-nicht unbekannt', 'from/to nur bei kind: span',
                     'ID doppelt: chr-006'):
            self.assertIn(text, errs)
        self.write([entry(1, date='1944', chapter=self.chapter, source='research/sources.md', date_text='um 1944', estimated=True)])
        self.assertEqual(self.errors(), [])

    def test_text_view(self):
        self.assertIn('Noch keine Chronologie', self.view())
        self.write([entry(1, what='Kriegsende', date='1945-05-08', source='Archiv'),
                    entry(2, what='Kriegsende', date='1946', status='reported'),
                    entry(3, 'span', what='Lehre', place='Wien', status='uncertain', date_text='um 1950', **{'from': '1949', 'to': '1952'}),
                    entry(4, what='Erfunden', status='invented', estimated=True, date='1951')])
        out = self.view()
        self.assertIn('**4 Einträge**', out)
        self.assertIn('Angabe gegen Beleg: „Kriegsende“', out)
        self.assertIn('*1945*', out)
        self.assertIn('- 1945-05-08 ● Kriegsende – Quelle: Archiv `chr-001`', out)
        self.assertIn('um 1950 ◌ Lehre (Wien)', out)
        self.assertIn('~1951 ✎ Erfunden', out)
        overview = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'project', '--text'],
                                  capture_output=True, text=True, check=True).stdout
        self.assertIn('🕰️ Chronologie: 4 Einträge, 1 Hinweis · `Zeitleiste` ansehen', overview)
        only = self.view('--status', 'reported')
        self.assertIn('(nur Angabe)', only)
        self.assertNotIn('`chr-004`', only)
        self.assertIn('`chr-002`', only)


    def test_widget_values(self):
        import json
        values, blocks = chr_.widget_values(self.base, self.config)
        self.assertTrue(values['EMPTY_TEXT'])
        self.write([entry(1, 'span', what='Lehre', place='Wien', chapter=self.chapter, **{'from': '1943', 'to': '1946-06'}),
                    entry(2, what='Kriegsende', date='1945-05-08'),
                    entry(3, what='Kriegsende', date='1946', status='reported'),
                    entry(4, 'span', what='Ehe', estimated=True, **{'from': '1950'}),
                    entry(5, what='Ohne Datum')])
        values, blocks = chr_.widget_values(self.base, self.config)
        data = json.loads(values['TIMELINE_JSON'])
        self.assertEqual(values['COUNT_TEXT'], '5 Einträge · 1 Hinweis')
        self.assertEqual(values['EMPTY_TEXT'], '')
        self.assertEqual([b['F_KIND_TEXT'] for b in blocks['FINDINGS']], ['Angabe gegen Beleg'])
        first = data['entries'][0]
        self.assertEqual((first['lo'], first['hi'], first['end_lo'], first['end_hi'], first['open'], first['chapter'][:2]),
                         ('1943-01-01', '1943-12-31', '1946-06-01', '1946-06-30', False, '1:'))
        self.assertEqual(data['chapters'], [{'label': 'K1', 'lo': '1943-01-01', 'hi': '1946-06-30'}])
        self.assertEqual(data['lanes'], [{'key': '@none', 'label': 'Ohne Figur'}])
        by = {e['id']: e for e in data['entries']}
        self.assertTrue(by['chr-002']['flag'] and by['chr-003']['flag'] and not by['chr-001']['flag'])
        self.assertTrue(by['chr-004']['open'])
        self.assertEqual(by['chr-005']['lo'], '')
        html = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'timeline', '--repo', 'o/r'],
                              capture_output=True, text=True, check=True).stdout
        self.assertIn('GW.render("zeitleiste"', html)


if __name__ == '__main__':
    unittest.main()



class TimelineLinkTest(BookTest):
    """Abgleich Text-Zeitleiste ↔ Chronologie, Ausgabe als Datei, englische Textfassung (#364)."""

    def timeline(self, events):
        (self.base / 'story').mkdir(exist_ok=True)
        (self.base / 'story/timeline.yml').write_text(yaml.safe_dump({'events': events}, allow_unicode=True), encoding='utf-8')

    def test_text_interval(self):
        self.assertEqual([str(d) for d in chr_.text_interval('im Mai 1945')], ['1945-01-01', '1945-12-31'])
        self.assertEqual([str(d) for d in chr_.text_interval('am 8. 5. 1945')], ['1945-05-08', '1945-05-08'])
        self.assertIsNone(chr_.text_interval('drei Tage später'))
        self.assertIsNone(chr_.text_interval('zwischen 1944 und 1946'))

    def test_link_findings_and_validation(self):
        ch2 = self.config['structure']['chapters'][1]['id']
        sec1 = self.config['structure']['chapters'][0]['sections'][0]['id']
        self.write([entry(1, what='Kriegsende', date='1945-05-08', chapter=ch2),
                    entry(2, 'span', what='Lehre', **{'from': '1949', 'to': '1952'})])
        self.timeline([{'id': 'ev-001', 'section': sec1, 'what': 'Kriegsende', 'when': 'im Sommer 1946', 'chronology': 'chr-001'},
                       {'id': 'ev-002', 'section': sec1, 'what': 'Lehre', 'when': '1950', 'chronology': 'chr-002'},
                       {'id': 'ev-003', 'section': sec1, 'what': 'Später', 'when': 'drei Tage später', 'chronology': 'chr-002'}])
        _, config = load(self.base)
        found = chr_.text_findings(self.base, config, chr_.read(self.base))
        texts = [f['text'] for f in found]
        self.assertEqual(len(found), 2, texts)
        self.assertIn('im Text „im Sommer 1946“', texts[0])
        self.assertIn('steht in Kapitel 1, die Chronologie ordnet es Kapitel 2 zu', texts[1])
        self.assertIn('Text gegen Chronologie', self.view())
        self.assertEqual(self.errors(), [])
        self.timeline([{'id': 'ev-001', 'section': sec1, 'what': 'x', 'chronology': 'chr-099'}])
        self.assertIn('Chronologie-Eintrag chr-099 unbekannt', '\n'.join(self.errors()))

    def test_export_html(self):
        self.write([entry(1, what='Kriegsende <Wien>', date='1945-05-08', characters=[]),
                    entry(2, 'span', what='Lehre', status='reported', **{'from': '1949', 'to': '1952'}),
                    entry(3, what='Ohne Datum')])
        subprocess.run([sys.executable, str(ROOT / 'scripts/chronology.py'), str(self.base), 'export'], check=True, capture_output=True)
        page = (self.base / 'story/zeitleiste.html').read_text(encoding='utf-8')
        self.assertTrue(page.startswith('<!DOCTYPE html>'))
        self.assertIn('<svg', page)
        self.assertIn('Kriegsende &lt;Wien&gt;', page)
        self.assertNotIn('<script', page)
        self.assertNotIn('http://', page.replace('http://www.w3.org/2000/svg', ''))
        self.assertNotIn('https://', page)
        en = chr_.export_html(self.base, self.config, 'en')
        self.assertIn('Where the dates do not fit', en)

    def test_english_text_view(self):
        self.write([entry(1, what='War ends', date='1945-05-08'), entry(2, what='War ends', date='1946', status='reported')])
        out = self.view('--language', 'en')
        self.assertIn('### 🕰️ Chronology', out)
        self.assertIn('report against record: “War ends”', out)
        self.assertNotIn('Einträge', out)


class NarrativeTimeTest(BookTest):
    """Erzählzeit ohne Kalenderjahr: epoch, day, time, Import aus story/chronologie.md (#379)."""

    MD = ('# Chronologie\n\n| Abstand zum Fund | Wochentag / Zeit | Ereignis | Abschnitt |\n|---|---|---|---|\n'
          '| −1 Tag | Dienstag, 21:31–21:44 Uhr | Wagen am Hotel | 1.2 |\n'
          '| Tag 0 | Mittwoch, 6:42 Uhr | Notruf nach dem Fund | 1.1 |\n'
          '| Tag 0 | Mittwoch, gegen 16 Uhr | Zettel am Wohnmobil | 2.1 |\n'
          '| +14 Tage | Mittwochfrüh | Name in der Zeitung | 2.1 |\n'
          '| Monate später | April | Urteil | 3.1 |\n')

    def test_labels_validation_and_text(self):
        data = {'epoch': {'label': 'Fundtag', 'weekday': 'wednesday'}, 'entries': [
            entry(1, what='Notruf', day=0, time='06:42', status='invented'),
            entry(2, what='Wagen am Hotel', day=-1, time='21:31', time_to='21:44', status='invented'),
            entry(3, 'span', what='Ermittlung', day=0, day_to=15, status='invented'),
            entry(4, what='Urteil', date_text='Monate später', status='invented')]}
        (self.base / 'story').mkdir(exist_ok=True)
        (self.base / 'story/chronology.yml').write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
        self.assertEqual(self.errors(), [])
        self.assertEqual(chr_.date_label(data['entries'][1]), 'Tag −1, 21:31–21:44')
        self.assertEqual(chr_.date_label(data['entries'][2]), 'Tag 0–+15')
        self.assertEqual([e['id'] for e in sorted(data['entries'], key=chr_.sort_key)], ['chr-002', 'chr-001', 'chr-003', 'chr-004'])
        out = self.view()
        self.assertIn('Erzählzeit: Tag 0 = Fundtag (Mittwoch)', out)
        self.assertIn('*Tag −1 (Dienstag)*', out)
        self.assertNotIn('2001', out)
        page = chr_.export_html(self.base, self.config)
        self.assertIn('Tag 0', page)
        self.assertNotIn('>2001<', page)
        del data['epoch']
        data['entries'].append(entry(5, day=1, date='1944'))
        (self.base / 'story/chronology.yml').write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
        errs = '\n'.join(self.errors())
        self.assertIn('brauchen epoch', errs)
        self.assertIn('day und Kalenderdatum zugleich', errs)

    def test_import_md(self):
        import analyze
        (self.base / 'story').mkdir(exist_ok=True)
        (self.base / 'story/chronologie.md').write_text(self.MD, encoding='utf-8')
        run_id, data = chr_.import_md_run(self.base, self.config)
        self.assertEqual(data['epoch'], {'label': 'Fund', 'weekday': 'wednesday'})
        items = data['items']
        self.assertEqual([it.get('day') for it in items], [-1, 0, 0, 14, None])
        self.assertEqual((items[0]['time'], items[0]['time_to']), ('21:31', '21:44'))
        self.assertEqual(items[2]['time'], '16:00')
        self.assertEqual(items[4]['date_text'], 'Monate später · April')
        self.assertEqual(items[1]['chapter'], self.config['structure']['chapters'][0]['id'])
        analyze.apply(self.base, run_id, 'chronology', [{'index': i} for i in range(len(items))])
        saved = chr_.read(self.base)
        self.assertEqual(saved['epoch']['label'], 'Fund')
        self.assertEqual(len(saved['entries']), 5)
        self.assertEqual(self.errors(), [])
