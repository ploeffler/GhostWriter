"""Sperre durch Checkout in der Warteschlange und Probelauf des Auscheckens (#572)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import checkout  # noqa: E402
import jobs  # noqa: E402
from render_view import load  # noqa: E402


class CheckoutJobsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'b'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.ch1, self.ch2 = self.config['structure']['chapters'][:2]

    def request(self, chapter, n=1):
        s = chapter['sections'][0]
        path = self.base / chapter['path'] / 'research' / s['id'] / f'request-00{n}.yml'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({'section_id': s['id'], 'question': 'Frage?', 'requested_at': '2026-11-25T08:00:00+00:00'}), encoding='utf-8')
        return path

    def test_job_waits_while_its_section_is_checked_out(self):
        locked, free = self.request(self.ch1), self.request(self.ch2)
        before = [j['path'] for j in jobs.queue(self.base, self.config)]
        self.assertEqual(len(before), 2)
        entry = checkout.start(self.base, self.config, 'anna', chapters='1', by='ploeffler')
        ready = [j['path'] for j in jobs.queue(self.base, self.config)]
        self.assertEqual(ready, [free])   # Kapitel 2 läuft weiter, Kapitel 1 wartet
        row = next(x for x in jobs.listing(self.base) if x['request'].endswith(str(locked.relative_to(self.base))))
        self.assertEqual((row['state'], row['locked_by']), ('open', entry['id']))
        results, remaining = jobs.process(self.base, commit=False, limit=0)   # nichts abarbeiten, nur zählen
        self.assertEqual(remaining, 1)
        checkout.end(self.base, self.config, entry['id'], 'fertig')
        self.assertEqual(len(jobs.queue(self.base, self.config)), 2)   # nach dem Beenden läuft er wieder

    def test_queue_view_names_the_lock(self):
        import queue_view
        self.request(self.ch1)
        entry = checkout.start(self.base, self.config, 'anna', chapters='1')
        values, blocks = queue_view.widget_values(self.base, self.config, 'de')
        row = blocks['PENDING'][0]
        self.assertIn(f'ausgecheckt ({entry["id"]})', row['J_BLOCKED_TEXT'])
        self.assertIn('ausgecheckt', queue_view.text_view(self.base, self.config, 'de'))
        self.assertIn('checked out', queue_view.text_view(self.base, self.config, 'en'))

    def test_dry_run_builds_but_neither_saves_nor_locks(self):
        built = []
        entry = checkout.start(self.base, self.config, 'anna', chapters='1', build=lambda e: built.append(e['id']) or ['x.docx'], dry_run=True)
        self.assertEqual((built, entry['dateien']), ([entry['id']], ['x.docx']))
        self.assertFalse((self.base / 'checkouts.yml').exists())
        self.assertIsNone(checkout.locked_by_checkout(self.base, self.config, self.ch1['sections'][0]['id']))
        real = checkout.start(self.base, self.config, 'anna', chapters='1')   # danach geht ein echter Checkout
        self.assertTrue((self.base / 'checkouts.yml').exists())
        self.assertTrue(checkout.locked_by_checkout(self.base, self.config, self.ch1['sections'][0]['id']))
        self.assertTrue(real['id'])


if __name__ == '__main__':
    unittest.main()
