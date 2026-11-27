"""Prüfprotokoll und Prüf-Tags (#331): eintragen, veraltet erkennen, Ansichten, Validierung."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import checks  # noqa: E402
import render_view  # noqa: E402
import validate_project  # noqa: E402
from render_view import load, section_file  # noqa: E402
from tests.widget_helpers import check_list, widget_json  # noqa: E402


def args(**kw):
    base = dict(text=True, library=None, changes=None, upstream=None, no_manuscript=False)
    base.update(kw)
    return SimpleNamespace(**base)


class ChecksTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.ch1, self.ch2 = self.config['structure']['chapters'][:2]
        self.s11 = self.ch1['sections'][0]

    def edit(self, section, extra):
        p = self.base / section['path']
        p.write_text(p.read_text(encoding='utf-8').rstrip('\n') + '\n\n' + extra + '\n', encoding='utf-8')

    def test_record_writes_entry_with_digests(self):
        e = checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed_with_notes',
                          date='2026-11-17', commit='abc1234')
        self.assertEqual(e['id'], 'pr-001')
        self.assertEqual(sorted(e['digests']), sorted(s['id'] for s in self.ch1['sections']))
        data = yaml.safe_load(checks.path(self.base).read_text(encoding='utf-8'))
        self.assertEqual(data['checks'][0]['date'], '2026-11-17')
        self.assertEqual(checks.record(self.base, self.config, 'proofreading', ['book'], 'passed')['id'], 'pr-002')
        self.assertEqual(validate_project.checks_errors(self.base, self.config), [])

    def test_unknown_kind_and_scope_rejected(self):
        with self.assertRaises(ValueError):
            checks.record(self.base, self.config, 'lektorat', ['book'], 'passed')
        with self.assertRaises(ValueError):
            checks.record(self.base, self.config, 'language', ['kap-gibtsnicht'], 'passed')
        with self.assertRaises(ValueError):
            checks.record(self.base, self.config, 'language', ['book'], 'ok')

    def test_tags_latest_per_kind_and_changed(self):
        checks.record(self.base, self.config, 'language', ['book'], 'failed', date='2026-11-13')
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', date='2026-11-17')
        checks.record(self.base, self.config, 'structure', [self.s11['id']], 'passed_with_notes', date='2026-11-16')
        t1 = checks.tags(self.base, self.config, [s['id'] for s in self.ch1['sections']])
        self.assertEqual([t['CK_TAG'] for t in t1], ['S✓·', 'L✓'])     # feste Reihenfolge, neuester Lauf je Art
        self.assertEqual(t1[0]['CK_PARTIAL'], '1' if len(self.ch1['sections']) > 1 else '')
        t2 = checks.tags(self.base, self.config, [s['id'] for s in self.ch2['sections']])
        self.assertEqual([t['CK_TAG'] for t in t2], ['L✗'])
        self.edit(self.s11, 'Neuer Satz nach der Prüfung.')
        t = checks.tags(self.base, self.config, [self.s11['id']])
        self.assertEqual([x['CK_TAG'] for x in t], ['S✓·*', 'L✓*'])
        self.assertEqual(t[1]['CK_STATE_TEXT'], 'seit Prüfung geändert')

    def test_entry_without_digest_is_unknown(self):
        checks.save(self.base, [{'id': 'pr-001', 'kind': 'proofreading', 'scope': ['book'], 'date': '2026-11-17',
                                 'result': 'passed'}])
        t = checks.tags(self.base, self.config, [self.s11['id']])
        self.assertEqual((t[0]['CK_TAG'], t[0]['CK_STATE']), ('K✓?', 'unknown'))

    def test_validation_finds_problems(self):
        rep = self.base / 'editorial' / 'lektorat.md'
        (self.base / 'editorial').mkdir()
        rep.write_text('# Bericht\n', encoding='utf-8')
        checks.path(self.base).write_text(
            'checks:\n'
            '- {id: pr-001, kind: language, scope: [book], date: 2026-11-17, result: passed, report: editorial/lektorat.md}\n'
            '- {id: pr-001, kind: proofreading, scope: [kap-x], date: 2026-11-17, result: passed, report: editorial/fehlt.md}\n',
            encoding='utf-8')
        errs = validate_project.checks_errors(self.base, self.config)
        self.assertTrue(any('ID doppelt: pr-001' in e for e in errs), errs)
        self.assertTrue(any('Umfang kap-x unbekannt' in e for e in errs), errs)
        self.assertTrue(any('editorial/fehlt.md fehlt' in e for e in errs), errs)
        checks.path(self.base).write_text('checks:\n- {id: pr-001, kind: lektorat, scope: [book], date: x, result: ok}\n',
                                          encoding='utf-8')
        self.assertTrue(validate_project.checks_errors(self.base, self.config))

    def test_views_without_protocol_unchanged(self):
        out = render_view.project_view(self.base, self.config, args())
        self.assertNotIn('Prüfungen', out)
        self.assertIn('| # | Kapitel | Umfang | Fertig | Kosten | Status | |', out)

    def test_chapter_card_fields(self):   # #362
        widget = render_view.project_view(self.base, self.config, args(text=False))
        row = widget.data['CHAPTERS'][0]
        self.assertGreater(row['CHAPTER_WORDS'], 0)
        self.assertTrue(row['CHAPTER_WORDS_TEXT'].endswith(' Wörter'))
        self.assertEqual(row['CHAPTER_APPROVED_TEXT'], f'0 von {len(self.ch1["sections"])}')
        self.assertEqual(max(r['CHAPTER_WORDS_PCT'] for r in widget.data['CHAPTERS']), 100)
        self.assertNotIn('CHAPTER_NOTES', row)
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed_with_notes', date='2026-11-17', notes=3)
        checks.record(self.base, self.config, 'proofreading', [self.ch1['id']], 'passed', date='2026-11-18', notes=0)
        row = render_view.project_view(self.base, self.config, args(text=False)).data['CHAPTERS'][0]
        self.assertEqual((row['CHAPTER_NOTES'], row['CHAPTER_NOTES_TEXT']), (3, '3 offene Hinweise'))
        self.assertFalse(validate_project.checks_errors(self.base, self.config))
        with self.assertRaises(ValueError):
            checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', notes=-1)
        self.assertIn('| 3 |', render_view.project_view(self.base, self.config, args()))
        # #437: ein Bericht für mehrere Prüfarten zählt nur einmal
        report = self.base / 'editorial' / 'gesamt.md'
        report.parent.mkdir(exist_ok=True)
        report.write_text('# Bericht\n', encoding='utf-8')
        for kind in ('structure', 'language', 'proofreading'):
            checks.record(self.base, self.config, kind, [self.ch1['id']], 'passed_with_notes', date='2026-11-19',
                          notes=21, report='editorial/gesamt.md')
        row = render_view.project_view(self.base, self.config, args(text=False)).data['CHAPTERS'][0]
        self.assertEqual(row['CHAPTER_NOTES'], 21)

    def test_manuscript_words_without_footnotes(self):
        self.assertEqual(render_view.manuscript_words('Ein Satz[^1] mit <!-- x y --> vier.\n\n[^1]: Fußnote hier.'), 4)

    def test_project_chapter_section_views(self):
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed_with_notes', date='2026-11-17',
                      report=None)
        checks.record(self.base, self.config, 'proofreading', ['book'], 'passed', date='2026-11-16')
        out = render_view.project_view(self.base, self.config, args())
        self.assertNotIn('Letzte Prüfungen', out)   # #538: nur in der Darstellung „erweitert“
        detailed = render_view.project_view(self.base, self.config, args(darstellung='erweitert'))
        self.assertIn('🧪 **Letzte Prüfungen:** Sprache ✓· 2026-11-17 · Korrektur ✓ 2026-11-16', detailed)
        self.assertIn('| Prüfungen |', out)
        self.assertIn('| L✓· K✓ |', out)
        self.assertIn('Ein Tag ist keine Freigabe.', out)
        out = render_view.chapter_view(self.base, self.config, args(), 1)
        self.assertIn('🧪 **Prüfungen:** `L✓·` Sprache: bestanden mit Hinweisen, 2026-11-17 · aktuell', out)
        self.assertIn('| L✓· K✓ |', out)
        out = render_view.section_view(self.base, self.config, args(), 1, 1)
        self.assertIn('| Prüfungen | `L✓·` Sprache', out)
        widget = render_view.project_view(self.base, self.config, args(text=False))
        self.assertEqual(widget.data['CHAPTERS'][0]['CHAPTER_CHECKS_TEXT'], 'L✓· K✓')
        self.assertEqual(widget.data['CHAPTERS'][0]['CHAPTER_CHECKS'][0]['CK_KIND'], 'language')
        row = check_list(widget.data['CHAPTERS'][0]['CHAPTER_CHECKS_JSON'])
        self.assertEqual([c['CK_TAG'] for c in row], ['L✓·', 'K✓'])
        self.assertEqual(widget.data['CHAPTERS'][0]['CHAPTER_CHECKS_JSON']['k'], list(checks.COMPACT_KEYS))   # ohne CK_PILL (#360), ohne CK_TAG und CK_TEXT (#674)
        self.assertEqual(row[0]['CK_TEXT'], 'Sprache: bestanden mit Hinweisen, ' + row[0]['CK_WHEN'] + ' · aktuell')   # wie das Widget zusammensetzt
        payload = widget_json(widget.split('GW.render("projektuebersicht",', 1)[1].rsplit(')</script>', 1)[0].replace('<\\/', '</'))
        self.assertNotIn('CHAPTER_CHECKS', payload['CHAPTERS'][0])   # Liste und Textfassung nur für --text (#360)
        self.assertNotIn('CHAPTER_CHECKS_TEXT', payload['CHAPTERS'][0])
        self.assertIn('CHAPTER_CHECKS_JSON', payload['CHAPTERS'][0])
        chap = render_view.chapter_view(self.base, self.config, args(text=False), 1)
        self.assertEqual(check_list(chap.data['CHECKS_JSON'])[0]['CK_TAG'], 'L✓·')
        self.assertIn('SECTION_CHECKS_JSON', chap.data['SECTIONS'][0])
        sec = render_view.section_view(self.base, self.config, args(text=False), 1, 1)
        self.assertEqual([t['CK_TAG'] for t in sec.data['CHECKS']], ['L✓·', 'K✓'])

    def test_english_text(self):
        import render_view_en
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', date='2026-11-17')
        widget = render_view.project_view(self.base, self.config, args(text=False, darstellung='erweitert'))
        data = render_view_en.prepare('projektuebersicht', widget.data, self.config, args())
        self.assertEqual(data['CHECKS_RECENT_TEXT'], 'Language ✓ 2026-11-17')
        self.assertIn('A tag is not an approval.', data['CHECKS_LEGEND'])
        self.assertEqual(data['CHAPTERS'][0]['CHAPTER_CHECKS'][0]['CK_TEXT'], 'Language: passed, 2026-11-17 · current')
        self.assertEqual(check_list(data['CHAPTERS'][0]['CHAPTER_CHECKS_JSON'], 'en')[0]['CK_TEXT'], 'Language: passed, 2026-11-17 · current')
        approval = {'CHECKS': [{'C_TEXT': 'Prüfpunkt'}]}   # Prüfpunkte der Freigabe bleiben unberührt
        render_view_en.localize_checks(approval)
        self.assertEqual(approval, {'CHECKS': [{'C_TEXT': 'Prüfpunkt'}]})

    def test_analysis_run_recorded_and_backfill(self):
        fake = Path(self.base).parent / 'fake.json'
        fake.write_text(json.dumps({'extract': {}, 'merge': {'groups': []}}), encoding='utf-8')
        os.environ['GHOSTWRITER_FAKE_LLM'] = str(fake)
        self.addCleanup(os.environ.pop, 'GHOSTWRITER_FAKE_LLM', None)
        import analyze
        head = analyze.run(self.base, kind='language', now='2026-11-17T10:00:00+01:00')
        entries = checks.load(self.base)
        self.assertEqual([(e['kind'], e['run'], e['date']) for e in entries], [('analysis:language', head['id'], '2026-11-17')])
        self.assertEqual(entries[0]['scope'], ['book'])
        self.assertTrue(entries[0]['digests'])
        self.assertEqual(checks.backfill(self.base, self.config), [])     # schon eingetragen
        checks.path(self.base).unlink()
        added = checks.backfill(self.base, self.config)
        self.assertEqual(len(added), 1)
        t = checks.tags(self.base, self.config, [self.s11['id']])
        self.assertEqual((t[0]['CK_SHORT'], t[0]['CK_STATE']), ('ASp', 'unknown'))
        self.assertEqual(validate_project.checks_errors(self.base, self.config), [])

    def test_history_marks_checks_replaced_by_later_full_check(self):   # Nachprüfung ersetzt früheren Befund
        ids = [s['id'] for s in self.ch1['sections']]
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'failed', date='2026-11-20', time='17:10', note='Nachprüfung offen')
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', date='2026-11-20', time='17:54')
        h = checks.history(self.base, self.config, ids)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]['CK_SUPERSEDED'], '2026-11-20 17:54 ✓')
        self.assertEqual(h[0]['CK_NOTE'], 'ersetzt durch spätere Prüfung 2026-11-20 17:54 ✓ · Nachprüfung offen')
        self.assertIn('ersetzt durch 2026-11-20 17:54 ✓', '\n'.join(checks.history_text(h)))
        self.assertIn('superseded by later check 2026-11-20 17:54 ✓', checks.history_note('', h[0]['CK_SUPERSEDED'], 'en'))

    def test_history_keeps_check_not_covered_by_later_partial_check(self):
        ids = [s['id'] for s in self.ch1['sections']]
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'failed', date='2026-11-20', time='17:10')
        checks.record(self.base, self.config, 'language', [ids[0]], 'passed', date='2026-11-20', time='17:54')   # nur ein Abschnitt
        h = checks.history(self.base, self.config, ids)
        self.assertEqual((h[0]['CK_RESULT'], h[0]['CK_SUPERSEDED']), ('failed', ''))   # nicht ersetzt: der Rest des Kapitels wurde nicht nachgeprüft
        self.assertEqual(checks.history(self.base, self.config, [ids[0]])[0]['CK_SUPERSEDED'], '2026-11-20 17:54 ✓')   # für diesen Abschnitt schon

    def test_history_of_earlier_checks(self):   # #340
        for d, r in (('2026-11-17', 'failed'), ('2026-11-18', 'passed_with_notes')):
            checks.record(self.base, self.config, 'quality_correction', [self.ch1['id']], r, date=d)
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', date='2026-11-16')
        hist = checks.history(self.base, self.config, [s['id'] for s in self.ch1['sections']])
        self.assertEqual([(h['CK_KIND'], h['CK_RESULT'], h['CK_DATE']) for h in hist],
                         [('quality_correction', 'failed', '2026-11-17')])
        out = render_view.chapter_view(self.base, self.config, args(), 1)
        self.assertIn('**Frühere Prüfungen (1):**', out)
        self.assertIn('- Qualität: 2026-11-17 ✗', out)
        chap = render_view.chapter_view(self.base, self.config, args(text=False), 1)
        self.assertEqual(chap.data['CHECKS_HISTORY_COUNT'], 1)
        self.assertEqual(check_list(chap.data['CHECKS_HISTORY_JSON'])[0]['CK_MARK'], '✗')
        out = render_view.section_view(self.base, self.config, args(), 1, 1)
        self.assertIn('Frühere Prüfungen (1)', out)
        import render_view_en
        data = render_view_en.prepare('kapitelansicht', chap.data, self.config, args())
        self.assertIn('Quality: failed', check_list(data['CHECKS_HISTORY_JSON'], 'en')[0]['CK_TEXT'])

    def test_project_has_no_history_text(self):   # #497, #672
        """Viele lange Prüfungen: die Projektübersicht trägt weder Verlauf noch Fließtext; Details stehen in der Kapitelansicht."""
        long = 'Ein sehr langer Prüfhinweis mit vielen Wörtern. ' * 12
        for i in range(25):
            checks.record(self.base, self.config, 'quality_correction', [self.ch1['id']], 'passed_with_notes',
                          date=f'2026-10-{i + 1:02d}', note=long, report=f'editorial/bericht-{i:02d}-' + 'x' * 80 + '.md')
        wide = render_view.project_view(self.base, self.config, args(text=False, darstellung='erweitert'))
        row = wide.data['CHAPTERS'][0]
        for key in ('CHAPTER_HISTORY', 'CHAPTER_HISTORY_JSON', 'CHAPTER_HISTORY_COUNT'):
            self.assertNotIn(key, row)
        self.assertNotIn('CHAPTER_CHECK_DETAILS', row)   # nichts zu tun: keine Zeile
        self.assertNotIn('frühere', json.dumps(wide.data, ensure_ascii=False))
        chap = render_view.chapter_view(self.base, self.config, args(text=False), 1)   # die Kapitelansicht bleibt vollständig
        self.assertIn('Prüfhinweis', json.dumps(chap.data['CHECKS_HISTORY_JSON'], ensure_ascii=False))

    def test_project_details_extended(self):   # #398, #672
        import render_view_en
        checks.record(self.base, self.config, 'quality_correction', [self.ch1['id']], 'failed', date='2026-11-17')
        checks.record(self.base, self.config, 'quality_correction', [self.ch1['id']], 'passed_with_notes',
                      date='2026-11-18', note='2 wesentliche Punkte (W1, W2), 9 Hinweise')
        plain = render_view.project_view(self.base, self.config, args(text=False))
        self.assertNotIn('CHAPTER_HISTORY_JSON', plain.data['CHAPTERS'][0])
        self.assertNotIn('Frühere Prüfungen', plain.data['CHECKS_LEGEND'])
        self.assertNotIn('CK_NOTE', plain.data['CHAPTERS'][0]['CHAPTER_CHECKS_JSON']['k'])
        wide = render_view.project_view(self.base, self.config, args(text=False, darstellung='erweitert'))
        row = wide.data['CHAPTERS'][0]
        tag = check_list(row['CHAPTER_CHECKS_JSON'])[0]
        self.assertEqual(tag['CK_NOTE'], '2 wesentliche Punkte (W1, W2), 9 Hinweise')   # Tooltip
        self.assertTrue(tag['CK_ID'])
        self.assertNotIn('CHAPTER_HISTORY_JSON', row)
        self.assertNotIn('Frühere Prüfungen', wide.data['CHECKS_LEGEND'])
        self.assertNotIn('CHAPTER_CHECK_DETAILS', row)   # letzte Qualitätsprüfung bestanden, keine offenen Hinweise
        payload = widget_json(wide.split('GW.render("projektuebersicht",', 1)[1].rsplit(')</script>', 1)[0].replace('<\\/', '</'))
        self.assertNotIn('CHAPTER_HISTORY', payload['CHAPTERS'][0])
        self.assertNotIn('CHAPTER_HISTORY_JSON', payload['CHAPTERS'][0])
        out = render_view.project_view(self.base, self.config, args(darstellung='erweitert'))
        self.assertNotIn('**Prüfdetails**', out)
        self.assertNotIn('Frühere Prüfungen', out)
        en = render_view_en.prepare('projektuebersicht', wide.data, self.config, args())
        self.assertNotIn('Earlier checks', en['CHECKS_LEGEND'])
        self.assertIn('CK_NOTE', en['CHAPTERS'][0]['CHAPTER_CHECKS_JSON']['k'])

    def test_compact_check_payload_is_packed_and_hoists_cost_hint(self):   # #674
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed_with_notes', date='2026-11-17', report='editorial/a.md')
        checks.record(self.base, self.config, 'proofreading', [self.ch1['id']], 'passed', date='2026-11-17', report='editorial/a.md')
        widget = render_view.project_view(self.base, self.config, args(text=False))
        payload = widget_json(widget.split('GW.render("projektuebersicht",', 1)[1].rsplit(')</script>', 1)[0].replace('<\\/', '</'))
        packed = payload['CHAPTERS'][0]['CHAPTER_CHECKS_JSON']
        self.assertIsInstance(packed, dict)                       # echtes JSON, keine Zeichenkette
        self.assertEqual(packed['p'], ['editorial/a.md'])         # Berichtspfad einmal
        self.assertEqual([r[packed['k'].index('CK_REPORT')] for r in packed['r']], [0, 0])
        self.assertTrue(payload['CHAPTER_COST_HINT'])             # gleicher Hinweis steht einmal oben
        self.assertEqual({r['CHAPTER_COST_HINT'] for r in payload['CHAPTERS']}, {''})
        self.assertEqual(checks.as_payload([]), '')

    def test_project_need_line_is_short(self):   # #672
        import render_view_en
        checks.record(self.base, self.config, 'structure', [self.ch1['id']], 'failed', date='2026-11-17',
                      note='Rundumprüfung; notes = Befunde dieser Prüfart')
        checks.record(self.base, self.config, 'story_memory', [self.ch1['id']], 'failed', date='2026-11-17',
                      note='Rundumprüfung; notes = Befunde dieser Prüfart')
        wide = render_view.project_view(self.base, self.config, args(text=False, darstellung='erweitert'))
        line = wide.data['CHAPTERS'][0]['CHAPTER_CHECK_DETAILS']
        self.assertIn('nicht bestanden', line)
        self.assertNotIn('Rundumprüfung', line)
        self.assertLess(len(line.split()), 15)
        en = render_view_en.prepare('projektuebersicht', wide.data, self.config, args())
        self.assertIn('failed', en['CHAPTERS'][0]['CHAPTER_CHECK_DETAILS'])
        self.assertNotIn('nicht bestanden', en['CHAPTERS'][0]['CHAPTER_CHECK_DETAILS'])
        out = render_view.project_view(self.base, self.config, args(darstellung='erweitert'))
        self.assertIn('Handlungsbedarf', out)

    def test_time_recorded_and_shown(self):   # #340
        e = checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', date='2026-11-17', time='14:05')
        self.assertEqual(e['time'], '14:05')
        self.assertNotIn('time', checks.record(self.base, self.config, 'language', [self.ch1['id']], 'failed', date='2026-11-16'))
        self.assertIn('time', checks.record(self.base, self.config, 'structure', [self.ch1['id']], 'passed'))
        self.assertEqual(validate_project.checks_errors(self.base, self.config), [])
        hist = checks.history(self.base, self.config, [s['id'] for s in self.ch1['sections']])
        self.assertEqual([h['CK_WHEN'] for h in hist], ['2026-11-16'])
        tags = checks.tags(self.base, self.config, [s['id'] for s in self.ch1['sections']])
        self.assertIn('2026-11-17 14:05', [t for t in tags if t['CK_KIND'] == 'language'][0]['CK_TEXT'])

    def test_record_backfill_without_digests(self):   # #344
        (Path(self.base) / 'editorial').mkdir(parents=True, exist_ok=True)
        (Path(self.base) / 'editorial' / 'alt.md').write_text('# Sprachlektorat\n', encoding='utf-8')
        e = checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', report='editorial/alt.md',
                          date='2026-11-13', backfill=True)
        self.assertNotIn('digests', e)
        self.assertNotIn('commit', e)
        self.assertIn('nicht gespeichert', e['note'])
        tags = checks.tags(self.base, self.config, [s['id'] for s in self.ch1['sections']])
        self.assertEqual(tags[0]['CK_STATE'], 'unknown')
        self.assertEqual(validate_project.checks_errors(self.base, self.config), [])
        # CLI: Datum vor heute ohne --commit gilt als Nachtrag
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(checks.main(['record', str(self.base), '--kind', 'structure', '--scope', self.ch1['id'],
                                          '--result', 'passed', '--date', '2020-01-01']), 0)
        self.assertIn('ohne Fingerabdruck', out.getvalue())
        self.assertNotIn('digests', checks.load(self.base)[-1])

    def test_complete_time(self):   # #345
        e = checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', date='2026-11-18')
        self.assertEqual(checks.complete(self.base, e['id'], time='09:30'), ['time'])
        self.assertEqual(checks.complete(self.base, e['id'], time='09:30'), [])
        with self.assertRaises(ValueError):
            checks.complete(self.base, e['id'], time='10:00')
        with self.assertRaises(ValueError):
            checks.complete(self.base, e['id'], time='9 Uhr')
        rep = Path(self.base) / 'editorial' / 'lauf.md'
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text('# Qualitätssicherung\n\nStand 19.11.2026, 14:05 Uhr\n', encoding='utf-8')
        f = checks.record(self.base, self.config, 'quality_correction', [self.ch1['id']], 'passed',
                          report='editorial/lauf.md', date='2026-11-18')
        self.assertNotIn('time', f)
        checks.import_reports(self.base, self.config, apply=True)
        self.assertEqual([x for x in checks.load(self.base) if x['id'] == f['id']][0]['time'], '14:05')
        self.assertEqual(validate_project.checks_errors(self.base, self.config), [])

    def test_import_old_reports(self):   # #340
        ed = Path(self.base) / 'editorial'
        an = Path(self.base) / 'analysis'
        ed.mkdir(parents=True, exist_ok=True)
        an.mkdir(parents=True, exist_ok=True)
        ch = self.ch1['id']
        (an / f'qualitaetssicherung-{ch}-2026-11-18.md').write_text(
            '# Qualitätssicherung\n\nErgebnis: **nicht bestanden**\n', encoding='utf-8')
        (an / f'redaktionslauf-{ch}-2026-11-18.md').write_text('# Redaktionslauf\n\nViel bestanden im Text.\n',
                                                                encoding='utf-8')
        (ed / 'notizen.md').write_text('# Notizen\n', encoding='utf-8')
        found = {c['report']: c for c in checks.candidates(self.base, self.config)}
        q = found[f'analysis/qualitaetssicherung-{ch}-2026-11-18.md']
        self.assertEqual((q['kind'], q['scope'], q['result'], q['ready']), ('quality_correction', [ch], 'failed', True))
        self.assertEqual(found[f'analysis/redaktionslauf-{ch}-2026-11-18.md']['result'], 'unknown')
        self.assertFalse(found['editorial/notizen.md']['ready'])
        self.assertEqual(checks.load(self.base), [])        # Auflisten schreibt nichts
        _, added = checks.import_reports(self.base, self.config, apply=True)
        self.assertEqual(len(added), 2)
        self.assertEqual(validate_project.checks_errors(self.base, self.config), [])
        self.assertEqual([c['report'] for c in checks.candidates(self.base, self.config)], ['editorial/notizen.md'])
        tags = checks.tags(self.base, self.config, [s['id'] for s in self.ch1['sections']])
        self.assertEqual(tags[0]['CK_TAG'], 'Q?')   # gleiches Datum: später eingetragener Bericht
        self.assertEqual(len(checks.history(self.base, self.config, [s['id'] for s in self.ch1['sections']])), 1)

    def test_import_result_detection(self):   # #347, Punkte 1 und 2
        r = checks._result_from
        self.assertEqual(r('# Prüfung\n\n## Ergebnis\n\n**Bestanden mit Hinweisen.** Zwei Stellen offen.\n'),
                         ('passed_with_notes', []))
        self.assertEqual(r('## Ergebnis\n**Nicht bestanden: wesentliche Punkte offen.** Siehe unten.\n'),
                         ('failed', []))
        table = ('# Prüfung\n\n| Stelle | Ergebnis der erneuten Lektüre |\n|---|---|\n| 1.2 | bestanden |\n\n'
                 'Ergebnis: nicht bestanden\n')
        self.assertEqual(r(table), ('failed', []))
        per_chapter = ('## Ergebnisse je Kapitel\n\n| Kapitel | Ergebnis |\n|---|---|\n'
                       '| 1 | bestanden mit Hinweisen |\n| 3 | nicht bestanden |\n')
        self.assertEqual(r(per_chapter), ('unknown', []))
        self.assertEqual(r('Ergebnis: nicht bestanden, nach Korrektur bestanden.\n'),
                         ('unknown', ['failed', 'passed']))
        self.assertEqual(r('## Ergebnis\n\nKapitel 1 bestanden mit Hinweisen.\nKapitel 3 nicht bestanden.\n\nRest bestanden.'),
                         ('unknown', ['passed_with_notes', 'failed']))

    def test_import_scope_detection(self):   # #347, Punkte 3 und 4
        chapters = self.config['structure']['chapters']
        cid = [c['id'] for c in chapters]
        sec = lambda c, s: chapters[c - 1]['sections'][s - 1]['id']
        f = lambda name, text='': checks._scope_from(self.config, name, text)
        self.assertEqual(f('redaktionelle-pruefung-kapitel-1-bis-8-2026-11-10',
                           '# Redaktionelle Prüfung Kapitel 1 bis 8\n'), cid[:8])
        self.assertEqual(f('bericht', '# Prüfung Kapitel 2–4\n'), cid[1:4])
        self.assertEqual(f('bericht', '# Lektorat Kap. 3 und 5\n'), [cid[2], cid[4]])
        self.assertEqual(f('lektorat-2026-11-10-6-3-qualitaetspruefung', '# Qualitätsprüfung\n'), [sec(6, 3)])
        self.assertEqual(f('lektorat-8-2-und-8-3', '# Redaktionelle Prüfung 6.3\n'), [sec(8, 2), sec(8, 3)])
        self.assertEqual(f('bericht', '# Redaktionelle Prüfung 6.3\n'), [sec(6, 3)])
        self.assertEqual(f('bericht', '# Prüfung 6.1–6.3\n'), [sec(6, 1), sec(6, 2), sec(6, 3)])
        self.assertEqual(f('bericht', '# Kapitel 6, Abschnitt 6.3\n'), [sec(6, 3)])
        # Abschnittsbericht: im Text erwähnte Kapitel zählen nicht (früher Kapitel 1 bzw. 10)
        self.assertEqual(f('bericht', '# Redaktionelle Prüfung 6.1\n\nVergleich mit Kapitel 1 und Kapitel 10.\n'),
                         [sec(6, 1)])
        self.assertEqual(f('bericht', '# Notizen\n\nIn Kapitel 3 steht etwas.\n'), [])
        self.assertEqual(f('bericht', '# Lektorat\n\nUmfang: Kapitel 2\n'), [cid[1]])
        self.assertEqual(f('lektorat-gesamtes-buch', '# Lektorat\n'), ['book'])
        self.assertEqual(f('bericht', '# Prüfung GhostWriter 0.6.1 am 19.11.2026\n'), [])

    def test_import_only_skip_fix(self):   # #347, Punkt 4
        an = Path(self.base) / 'analysis'
        an.mkdir(parents=True, exist_ok=True)
        ch1, ch2 = self.ch1['id'], self.ch2['id']
        (an / f'qualitaetssicherung-{ch1}-2026-11-18.md').write_text('# Qualitätssicherung\n\nErgebnis: bestanden\n',
                                                                      encoding='utf-8')
        (an / f'lektorat-sprache-{ch2}-2026-11-17.md').write_text(
            '# Sprachlektorat\n\nErgebnis: nicht bestanden, nach Korrektur bestanden\n', encoding='utf-8')
        found = {c['report']: c for c in checks.candidates(self.base, self.config)}
        mixed = found[f'analysis/lektorat-sprache-{ch2}-2026-11-17.md']
        self.assertFalse(mixed['ready'])
        self.assertEqual(mixed['results'], ['failed', 'passed'])
        _, added = checks.import_reports(self.base, self.config, apply=True,
                                         skip=[f'qualitaetssicherung-{ch1}-2026-11-18.md'])
        self.assertEqual(added, [])                       # übrig ist nur der nicht eindeutige
        with self.assertRaises(ValueError):               # Berichtigen nur mit genau einem --only
            checks.import_reports(self.base, self.config, fix={'result': 'passed'})
        with self.assertRaises(ValueError):
            checks.import_reports(self.base, self.config, only=['gibtsnicht.md'])
        with self.assertRaises(ValueError):
            checks.import_reports(self.base, self.config, only=[mixed['report']], fix={'scope': ['kap-x']})
        _, added = checks.import_reports(self.base, self.config, apply=True, only=[mixed['report']],
                                         fix={'result': 'passed', 'scope': [self.s11['id']]})
        self.assertEqual((added[0]['result'], added[0]['scope']), ('passed', [self.s11['id']]))
        self.assertIn('berichtigt: result, scope', added[0]['note'])
        self.assertEqual([c['report'] for c in checks.candidates(self.base, self.config)],
                         [f'analysis/qualitaetssicherung-{ch1}-2026-11-18.md'])
        self.assertEqual(validate_project.checks_errors(self.base, self.config), [])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(checks.main(['import', str(self.base), '--only',
                                          f'qualitaetssicherung-{ch1}-2026-11-18.md']), 0)
        self.assertIn('· analysis/qualitaetssicherung', out.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checks.main(['import', str(self.base), '--result', 'passed']), 1)

    def test_cli(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            self._cli()
        self.assertIn('1. ', out.getvalue())
        self.assertIn('S✓', out.getvalue())

    def _cli(self):
        rc = checks.main(['record', str(self.base), '--kind', 'structure', '--scope', self.ch1['id'],
                          '--result', 'passed', '--date', '2026-11-15'])
        self.assertEqual(rc, 0)
        self.assertEqual(checks.main(['record', str(self.base), '--kind', 'x', '--scope', 'book', '--result', 'passed']), 1)
        self.assertEqual(checks.main(['list', str(self.base)]), 0)


if __name__ == '__main__':
    unittest.main()


class RecordAtCommitTest(unittest.TestCase):
    """#406: --commit ≠ HEAD → Fingerabdrücke aus diesem Commit, Tag „seit Prüfung geändert“."""

    def test_digests_from_given_commit(self):
        import subprocess
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
        git = lambda *a: subprocess.run(['git', '-C', str(base), '-c', 'user.name=t', '-c', 'user.email=t@t', *a],
                                        capture_output=True, text=True, check=True).stdout.strip()
        git('init', '-q'); git('add', '-A'); git('commit', '-qm', 'A')
        a = git('rev-parse', 'HEAD')
        _, config = load(base)
        sec = config['structure']['chapters'][0]['sections'][0]
        p = base / sec['path']
        p.write_text(p.read_text(encoding='utf-8') + '\nKorrigiert.\n', encoding='utf-8')
        git('commit', '-qam', 'B')
        entry = checks.record(base, config, 'language', [sec['id']], 'failed', commit=a)
        self.assertNotEqual(entry['digests'][sec['id']], checks.digests(base, config, [sec['id']])[sec['id']])
        now = checks.record(base, config, 'language', [sec['id']], 'passed')
        self.assertEqual(now['digests'][sec['id']], checks.digests(base, config, [sec['id']])[sec['id']])
