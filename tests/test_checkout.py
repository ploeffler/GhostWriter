"""Bereich zum Gegenlesen auschecken und sperren (#572, Teil 1)."""
import random
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
import hinweise  # noqa: E402
import sections  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402


def git(base, *args):
    return subprocess.run(['git', '-C', str(base), *args], check=True, capture_output=True, text=True,
                          env={'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
                               'GIT_COMMITTER_EMAIL': 't@t', 'PATH': '/usr/bin:/bin:/usr/local/bin'}).stdout


class CheckoutTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.chapters = checkout.chapter_ids(self.config)
        self.assertGreaterEqual(len(self.chapters), 2)
        self.ch1_sections = checkout.sections_of(self.config, [self.chapters[0]])

    def start(self, chapters='1', **kw):
        return checkout.start(self.base, self.config, 'Anna', chapters, by='ploeffler', commit='abc', **kw)

    def test_id_format_and_uniqueness(self):
        rng = random.Random(1)
        ids = []
        for _ in range(50):
            ids.append(checkout.new_id([{'id': i} for i in ids], rng.choice))
        self.assertEqual(len(set(ids)), 50)
        self.assertTrue(all(checkout.ID_RE.match(i) for i in ids))
        self.assertFalse(any(c in i[3:] for i in ids for c in '01OI'))

    def test_start_locks_only_the_area(self):
        e = self.start('1')
        self.assertTrue(checkout.ID_RE.match(e['id']))
        self.assertEqual(e['status'], 'ausgecheckt')
        self.assertEqual(sorted(e['abschnitte']), sorted(self.ch1_sections))
        self.assertTrue(checkout.locked_by_checkout(self.base, self.config, self.ch1_sections[0]))
        other = checkout.sections_of(self.config, [self.chapters[1]])[0]
        self.assertIsNone(checkout.locked_by_checkout(self.base, self.config, other))
        self.assertEqual(checkout.check_sections(self.base, self.config, other), [])
        self.assertIn(e['id'], checkout.check_sections(self.base, self.config, self.ch1_sections[0])[0])
        self.assertFalse(checkout.problems(self.base, self.config))

    def test_second_checkout_of_same_area_refused(self):
        self.start('1')
        with self.assertRaisesRegex(ValueError, 'Schon ausgecheckt'):
            self.start('1-2')
        self.start('2')                                   # anderer Bereich geht

    def test_book_locks_everything(self):
        checkout.start(self.base, self.config, 'Anna', book=True, by='x', commit='abc')
        for c in self.chapters:
            self.assertTrue(checkout.locked_by_checkout(self.base, self.config, checkout.sections_of(self.config, [c])[0]))
        with self.assertRaises(ValueError):
            self.start('1')

    def test_parse_and_text(self):
        self.assertEqual(checkout.parse_chapters(self.config, '1-2'), self.chapters[:2])
        self.assertEqual(checkout.parse_chapters(self.config, self.chapters[0]), self.chapters[:1])
        with self.assertRaises(ValueError):
            checkout.parse_chapters(self.config, '99')
        e = self.start('1-2')
        self.assertEqual(checkout.scope_text(self.config, e), 'Kapitel 1–2')

    def test_end_abort_keeps_history_and_unlocks(self):
        e = self.start('1')
        with self.assertRaises(ValueError):
            checkout.end(self.base, self.config, e['id'], '')
        done = checkout.end(self.base, self.config, e['id'], 'Gegenlesen fertig', by='ploeffler')
        self.assertEqual(done['status'], 'beendet')
        self.assertIsNone(checkout.locked_by_checkout(self.base, self.config, self.ch1_sections[0]))
        self.assertEqual(len(checkout.load(self.base)['checkouts']), 1)          # bleibt als Verlauf
        with self.assertRaisesRegex(ValueError, 'schon'):
            checkout.end(self.base, self.config, e['id'], 'nochmal')
        e2 = self.start('1')
        ab = checkout.end(self.base, self.config, e2['id'], 'Leser meldet sich nicht', abort=True)
        self.assertEqual((ab['status'], ab['beendet']['grund']), ('abgebrochen', 'Leser meldet sich nicht'))

    def test_release_part_keeps_rest_locked(self):
        e = self.start('1-2')
        checkout.release(self.base, self.config, e['id'], '2', by='ploeffler')
        sec2 = checkout.sections_of(self.config, [self.chapters[1]])[0]
        self.assertIsNone(checkout.locked_by_checkout(self.base, self.config, sec2))
        self.assertTrue(checkout.locked_by_checkout(self.base, self.config, self.ch1_sections[0]))
        done = checkout.release(self.base, self.config, e['id'], '1')
        self.assertEqual(done['status'], 'beendet')

    def test_overdue_never_unlocks(self):
        e = self.start('1', until='2026-12-01')
        self.assertEqual(checkout.overdue(self.base, '2026-11-30'), [])
        rows = checkout.overdue(self.base, '2026-12-11')
        self.assertEqual((rows[0][0]['id'], rows[0][1]), (e['id'], 10))
        self.assertTrue(checkout.locked_by_checkout(self.base, self.config, self.ch1_sections[0]))
        checkout.extend(self.base, self.config, e['id'], '2027-01-01')
        self.assertEqual(checkout.overdue(self.base, '2026-12-11'), [])

    def test_may_manage_only_owner_or_who_checked_out(self):
        cfg = self.base / 'ghostwriter.yml'
        text = cfg.read_text(encoding='utf-8') + "\nteam:\n  - {github: boss, role: owner}\n  - {github: ben, role: editor}\n  - {github: cleo, role: editor}\n"
        cfg.write_text(text, encoding='utf-8')
        _, config = load(self.base)
        e = checkout.start(self.base, config, 'Anna', '1', by='ben', commit='abc')
        with self.assertRaisesRegex(ValueError, 'darf'):
            checkout.end(self.base, config, e['id'], 'x', by='cleo')
        checkout.extend(self.base, config, e['id'], '2027-01-01', by='ben')      # wer ausgecheckt hat
        checkout.end(self.base, config, e['id'], 'x', by='boss')                  # Eigentümer

    def test_verify_detects_change(self):
        e = self.start('1')
        self.assertEqual(checkout.verify(self.base, self.config), [])
        _, sec = [(c, s) for c, s in ((c, s) for c in self.config['structure']['chapters'] for s in c['sections'])][0]
        p = self.base / sec['path']
        p.write_text(p.read_text(encoding='utf-8') + '\nNachträglich eingefügt.\n', encoding='utf-8')
        found = checkout.verify(self.base, self.config)
        self.assertEqual([(x['id'], c) for x, c in found], [(e['id'], [sec['id']])])
        self.assertTrue(validate_project.checkout_warnings(self.base))

    def test_sections_write_path_refuses(self):
        self.start('1')
        sec = self.config['structure']['chapters'][0]['sections'][0]
        with self.assertRaises(SystemExit) as cm:
            sections.check_unlocked(self.base, sec)
        self.assertIn('ausgecheckt', str(cm.exception))
        sections.check_unlocked(self.base, self.config['structure']['chapters'][1]['sections'][0])   # frei

    def test_hinweise_plan_blocks_and_accept_skips(self):
        self.start('1')
        sec = self.config['structure']['chapters'][0]['sections'][0]
        text = (self.base / sec['path']).read_text(encoding='utf-8')
        word = next(w for w in text.split() if text.count(w) == 1 and w.isalpha() and len(w) > 6)
        entry = {'id': 'e-001', 'abschnitt': '1.1', 'section_id': sec['id'], 'chapter_id': self.chapters[0], 'art': 'sprache',
                 'grund': 'x', 'alt': word, 'neu': word + 'x', 'entscheidung': 'ja', 'befund': 'x#b-001'}
        data = {'buch': 'x', 'erstellt': '2026-11-24', 'ohne_autor': [entry], 'autorenentscheidung': []}
        mark, _, why = hinweise.plan(self.base, self.config, data)[0]
        self.assertEqual(mark, '⛔')
        self.assertIn('ausgecheckt', why)
        entry['entscheidung'] = 'offen'
        path = self.base / 'durchsicht.yml'
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf-8')
        self.assertEqual(hinweise.accept(path, skip={sec['id']}), [])
        self.assertEqual(len(hinweise.accept(path)), 1)

    def test_gate_against_base_commit(self):
        git(self.base, 'init', '-q')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'start')
        e = checkout.start(self.base, self.config, 'Anna', '1', by='x', commit=git(self.base, 'rev-parse', 'HEAD').strip())
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'checkout')
        base_ref = git(self.base, 'rev-parse', 'HEAD').strip()
        self.assertEqual(checkout.changed_locked(self.base, self.config, base_ref), [])
        sec = self.config['structure']['chapters'][0]['sections'][0]
        other = self.config['structure']['chapters'][1]['sections'][0]
        (self.base / other['path']).write_text((self.base / other['path']).read_text(encoding='utf-8') + '\nNeu.\n', encoding='utf-8')
        self.assertEqual(checkout.changed_locked(self.base, self.config, base_ref), [])      # anderes Kapitel: grün
        (self.base / sec['path']).write_text((self.base / sec['path']).read_text(encoding='utf-8') + '\nNeu.\n', encoding='utf-8')
        self.assertEqual(checkout.changed_locked(self.base, self.config, base_ref), [(e['id'], sec['id'])])
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/checkout.py'), str(self.base), 'gate', '--base', base_ref],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn(e['id'], r.stderr)

    def test_problems_detect_overlap_and_unknown_chapter(self):
        self.start('1')
        data = checkout.load(self.base)
        data['checkouts'].append({**data['checkouts'][0], 'id': 'GW-2222'})
        data['checkouts'].append({'id': 'GW-3333', 'status': 'beendet', 'zeit': 'x', 'bereich': {'chapters': ['kap-99']}})
        checkout.save(self.base, data)
        errs = checkout.problems(self.base, self.config)
        self.assertTrue(any('doppelt ausgecheckt' in e for e in errs))
        self.assertTrue(any('kap-99' in e for e in errs))

    def test_cli(self):
        def run(*a):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/checkout.py'), str(self.base), *a], capture_output=True, text=True)
        r = run('start', '--chapters', '1', '--reader', 'Anna')
        self.assertEqual(r.returncode, 0, r.stderr)
        cid = r.stdout.split(':')[0]
        self.assertIn('ausgecheckt', run('status').stdout)
        self.assertEqual(run('check', self.ch1_sections[0]).returncode, 1)
        self.assertEqual(run('verify').returncode, 0)
        self.assertEqual(run('end', cid, '--reason', 'fertig').returncode, 0)
        self.assertEqual(run('check', self.ch1_sections[0]).returncode, 0)


if __name__ == '__main__':
    unittest.main()
