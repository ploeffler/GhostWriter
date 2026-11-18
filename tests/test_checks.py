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
        self.assertIn('| # | Kapitel | Kosten | Status | |', out)

    def test_project_chapter_section_views(self):
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed_with_notes', date='2026-11-17',
                      report=None)
        checks.record(self.base, self.config, 'proofreading', ['book'], 'passed', date='2026-11-16')
        out = render_view.project_view(self.base, self.config, args())
        self.assertIn('🧪 **Letzte Prüfungen:** Sprache ✓· 2026-11-17 · Korrektur ✓ 2026-11-16', out)
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
        sec = render_view.section_view(self.base, self.config, args(text=False), 1, 1)
        self.assertEqual([t['CK_TAG'] for t in sec.data['CHECKS']], ['L✓·', 'K✓'])

    def test_english_text(self):
        import render_view_en
        checks.record(self.base, self.config, 'language', [self.ch1['id']], 'passed', date='2026-11-17')
        widget = render_view.project_view(self.base, self.config, args(text=False))
        data = render_view_en.prepare('projektuebersicht', widget.data, self.config, args())
        self.assertEqual(data['CHECKS_RECENT_TEXT'], 'Language ✓ 2026-11-17')
        self.assertIn('A tag is not an approval.', data['CHECKS_LEGEND'])
        self.assertEqual(data['CHAPTERS'][0]['CHAPTER_CHECKS'][0]['CK_TEXT'], 'Language: passed, 2026-11-17 · current')

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
