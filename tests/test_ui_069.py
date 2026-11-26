"""Daten für ghostwriter-ui 0.69.0: Veraltet-Marken, Handlungsbedarf, Checkouts, Erneut versuchen (#592, #593, #572, #596)."""
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
import checkout  # noqa: E402
import checks  # noqa: E402
import matter  # noqa: E402
import stale  # noqa: E402
from render_view import load  # noqa: E402
from tests.widget_helpers import widget_json  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'b'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.ch = self.config['structure']['chapters'][0]

    def payload(self, *args, name=None):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args, '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = re.search(r'GW\.render\("([a-z-]+)",(\{.*\})\)</script>', r.stdout)
        self.assertIsNotNone(m, r.stdout[:300])
        return widget_json(m.group(2).replace('<\\/', '</'))

    def text(self, *args):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args, '--text', '--repo', 'o/r'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def write_checkout(self, frist=None):
        sec_ids = [s['id'] for s in self.ch['sections']]
        entry = {'id': 'GW-7F3A', 'status': 'ausgecheckt', 'bereich': {'chapters': [self.ch['id']]}, 'gegenleser': 'Anna',
                 'ausgecheckt_von': 'ploeffler', 'zeit': '2026-11-24T21:20:00+01:00', 'commit': 'a' * 40,
                 'abschnitte': {s: 'x' for s in sec_ids}, 'dateien': []}
        if frist:
            entry['frist'] = frist
        (self.base / 'checkouts.yml').write_text(yaml.safe_dump({'checkouts': [entry]}, allow_unicode=True), encoding='utf-8')


class StaleDataTest(Base):
    def test_marks_are_own_fields_not_part_of_the_title(self):
        matter.add(self.base, 'foreword')
        _, self.config = load(self.base)
        stale.mark(self.base, self.config, '1.1', 'Zeitzeugin widerspricht', date='2026-11-25')
        stale.mark(self.base, self.config, 'mat-vorwort', 'überholt', date='2026-11-25')
        ov = self.payload('project')
        row = ov['CHAPTERS'][0]
        self.assertEqual((row['CHAPTER_STALE_TEXT'], row['CHAPTER_TITLE']), ('veraltet', self.ch['title']))
        self.assertIn('1.1: Als veraltet markiert seit 2026-11-25: Zeitzeugin widerspricht', row['CHAPTER_STALE_HINT'])
        self.assertEqual(ov['STALE_TEXT'], '2 veraltet')
        self.assertEqual(ov['MATTER_FRONT'][0]['MATTER_STALE_TEXT'], 'veraltet')
        self.assertEqual(ov['MATTER_FRONT'][0]['MATTER_TITLE'], 'Vorwort')
        kap = self.payload('chapter', '1')
        first = kap['SECTIONS'][0]
        self.assertEqual((first['SECTION_STALE_TEXT'], first['SECTION_TITLE']), ('veraltet', self.ch['sections'][0]['title']))
        self.assertIn('Zeitzeugin widerspricht', first['SECTION_STALE_HINT'])
        self.assertEqual(kap['SECTIONS'][1]['SECTION_STALE_TEXT'], '')
        self.assertIn('⚠ veraltet', self.text('chapter', '1'))
        self.assertIn('⚠ veraltet', self.text('project'))
        self.assertIn('2 veraltet', self.text('project'))

    def test_edit_forms_carry_the_buttons_data(self):
        sec = self.payload('section', '1.1')
        self.assertEqual((sec['STALE_TEXT'], sec['STALE_NONE']), ('', '1'))
        self.assertEqual(json.loads(sec['STALE_ARGS']), {'section_id': self.ch['sections'][0]['id']})
        stale.mark(self.base, self.config, '1.1', 'Grund', date='2026-11-25')
        sec = self.payload('section', '1.1')
        self.assertEqual((sec['STALE_NONE'], sec['STALE_TEXT']), ('', 'Als veraltet markiert seit 2026-11-25: Grund'))
        matter.add(self.base, 'foreword')
        part = self.payload('matter', 'mat-vorwort')
        self.assertEqual(json.loads(part['STALE_ARGS']), {'section_id': 'mat-vorwort'})


class CheckoutDataTest(Base):
    def test_overview_chapter_and_marks(self):
        self.write_checkout(frist='2026-11-20')
        _, self.config = load(self.base)
        shown = checkout.display(self.base, self.config, today='2026-11-25')
        self.assertEqual(len(shown), 1)
        self.assertIn('ausgecheckt an Anna seit 24.11. (GW-7F3A)', shown[0]['text'])
        self.assertIn('überfällig seit 5 Tagen', shown[0]['text'])
        ov = self.payload('project')
        self.assertEqual([c['CO_ID'] for c in ov['CHECKOUTS']], ['GW-7F3A'])
        self.assertEqual(json.loads(ov['CHECKOUTS'][0]['CO_ARGS']), {'id': 'GW-7F3A'})
        self.assertEqual(ov['CHAPTERS'][0]['CHAPTER_CHECKOUT_TEXT'], 'ausgecheckt (GW-7F3A)')
        self.assertEqual(ov['CHAPTERS'][1]['CHAPTER_CHECKOUT_TEXT'], '')
        kap = self.payload('chapter', '1')
        self.assertEqual([c['CO_ID'] for c in kap['CHECKOUTS']], ['GW-7F3A'])
        self.assertEqual(kap['SECTIONS'][0]['SECTION_CHECKOUT_TEXT'], 'ausgecheckt')
        self.assertNotIn('CHECKOUTS', self.payload('chapter', '2'))   # betrifft Kapitel 2 nicht
        self.assertIn('🔒', self.text('project'))
        self.assertIn('`CB` Checkout beenden', self.text('chapter', '1'))

    def test_library_reads_checkouts_from_the_branch(self):
        self.write_checkout()
        subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=self.base, check=True)
        for cmd in (['add', '-A'], ['commit', '-qm', 'x']):
            subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *cmd], cwd=self.base, check=True, capture_output=True)
        found = checkout.ref_checkouts(self.base, 'main', today='2026-11-25')
        self.assertEqual([c['id'] for c in found], ['GW-7F3A'])
        self.assertEqual(checkout.ref_checkouts(self.base, 'nicht-da'), [])


class NeedsAttentionTest(Base):
    def test_todo_block_for_the_widget(self):
        checks.record(self.base, self.config, 'language', ['book'], 'passed', date='2026-11-20')
        path = self.base / self.ch['sections'][0]['path']
        path.write_text(path.read_text(encoding='utf-8') + '\nNach der Prüfung geändert.\n', encoding='utf-8')
        checks.record(self.base, self.config, 'structure', [self.ch['id']], 'failed', date='2026-11-21', notes=2)
        ov = self.payload('project')
        todo = ov['TODO']
        self.assertEqual(todo[0]['TODO_TEXT'], 'Buch neu prüfen (Sprache)')
        self.assertEqual((todo[0]['TODO_ACTION'], todo[0]['TODO_ACTION2']), ('', ''))   # buchweit: nicht klickbar
        chapter = todo[1]
        self.assertIn('Kapitel 1: Struktur nicht bestanden', chapter['TODO_TEXT'])
        self.assertEqual((chapter['TODO_ACTION'], chapter['TODO_ACTION2']), ('view.chapter', 'view.notes_review'))
        self.assertEqual(json.loads(chapter['TODO_ARGS']), {'chapter_id': self.ch['id']})
        self.assertNotIn('CHECKS_BOOK_STALE', ov)
        self.assertNotIn('CHECKS_RECENT_TEXT', ov)   # „Letzte Prüfungen“ nur in „erweitert“


class RetryDataTest(Base):
    def test_failed_rows_carry_the_request_for_the_button(self):
        import queue_view
        req = self.base / self.ch['path'] / 'research' / 'sec-x' / 'request-001.yml'
        req.parent.mkdir(parents=True)
        req.write_text(yaml.safe_dump({'section_id': self.ch['sections'][0]['id'], 'question': 'F?', 'error': 'Modell nicht mehr verfügbar',
                                       'failed_at': '2026-11-24T10:00:00+00:00'}), encoding='utf-8')
        values, blocks = queue_view.widget_values(self.base, self.config, 'de')
        row = blocks['FAILED'][0]
        self.assertEqual(json.loads(row['J_ARGS']), {'request': row['J_PATH']})


if __name__ == '__main__':
    unittest.main()
