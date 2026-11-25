"""#478: Reihenfolge der Hintergrund-Warteschlange – Vorrang, Abhängigkeit, Vorziehen, Abbrechen."""
import json
import sys
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_jobs import Base, jobs, ROOT  # noqa: E402

AT = '2026-11-22T20:00:00+00:00'


def rel(base, path):
    return str(Path(path).relative_to(base))


class OrderTest(Base):
    def ran(self, **kw):
        with self.fake_run(), mock.patch.object(jobs, 'budget_low', return_value=kw.get('low', False)):
            results, remaining = jobs.process(self.base, commit=False)
        return [c[0] for c in self.calls], results, remaining

    def test_priority_runs_before_book_order(self):
        self.add('sec-01-01', AT)
        self.add('sec-02-02', AT, priority=True)
        self.assertEqual([j['section_id'] for j in jobs.queue(self.base)], ['sec-02-02', 'sec-01-01'])

    def test_after_waits_for_target_even_if_earlier_in_book(self):
        a = self.add('sec-02-01', AT)
        self.add('sec-01-01', AT, after=rel(self.base, a))   # im Buch vor A, soll aber nach A laufen
        self.assertEqual([j['section_id'] for j in jobs.queue(self.base)], ['sec-02-01'])   # B ist blockiert
        self.assertEqual([j['section_id'] for j in jobs.jobs(self.base)], ['sec-02-01', 'sec-01-01'])
        order, results, remaining = self.ran()
        self.assertEqual(order, ['sec-02-01', 'sec-01-01'])   # B läuft im selben Lauf nach A
        self.assertEqual([r['ok'] for r in results], [True, True])
        self.assertEqual(remaining, 0)

    def test_after_by_file_name_in_same_folder(self):
        a = self.add('sec-01-01', AT)
        self.add('sec-01-01', AT, after=a.stem)
        self.assertEqual(len(jobs.queue(self.base)), 1)

    def test_target_waiting_for_budget_keeps_dependent_blocked(self):
        a = self.add('sec-01-01', AT)
        self.add('sec-01-02', AT, after=rel(self.base, a))
        order, results, remaining = self.ran(low=True)
        self.assertEqual(order, [])
        self.assertEqual([r.get('waiting') for r in results], [True])
        self.assertEqual(remaining, 0)
        self.assertEqual([j['state'] for j in jobs.jobs(self.base)], ['waiting_budget', 'open'])
        self.assertEqual(jobs.jobs(self.base)[1]['blocked_by'], rel(self.base, a))

    def test_failed_target_releases_dependent(self):
        a = self.add('sec-01-01', AT)
        self.add('sec-01-02', AT, after=rel(self.base, a))
        with self.fake_run(fail='sec-01-01'), mock.patch.object(jobs, 'budget_low', return_value=False):
            results, remaining = jobs.process(self.base, commit=False)
        self.assertEqual([r['ok'] for r in results], [False, True])
        self.assertEqual(self.calls[1][0], 'sec-01-02')

    def test_cycle_ignored_and_reported(self):
        a = self.add('sec-01-01', AT)
        b = self.add('sec-01-02', AT, after=rel(self.base, a))
        data = yaml.safe_load(a.read_text())
        data['after'] = rel(self.base, b)
        a.write_text(yaml.safe_dump(data))
        listing = jobs.listing(self.base)
        self.assertTrue(all('Ring' in x['note'] for x in listing))
        order, _, _ = self.ran()
        self.assertEqual(order, ['sec-01-01', 'sec-01-02'])   # Buchreihenfolge, nichts hängt

    def test_missing_target_does_not_block(self):
        self.add('sec-01-01', AT, after='chapters/ch-01/research/sec-01-01/request-099.yml')
        self.assertEqual(len(jobs.queue(self.base)), 1)
        self.assertIn('nicht mehr vorhanden', jobs.listing(self.base)[0]['note'])

    def test_prioritize_and_cancel(self):
        a = self.add('sec-02-01', AT)
        b = self.add('sec-01-01', AT)
        jobs.prioritize(self.base, rel(self.base, a))
        self.assertEqual([j['section_id'] for j in jobs.queue(self.base)], ['sec-02-01', 'sec-01-01'])
        self.assertTrue(jobs.listing(self.base)[0]['priority'])
        jobs.cancel(self.base, rel(self.base, b))
        self.assertEqual([j['section_id'] for j in jobs.queue(self.base)], ['sec-02-01'])
        self.assertFalse(b.exists())

    def test_only_waiting_jobs_can_be_changed(self):
        a = self.add('sec-01-01', AT)
        data = yaml.safe_load(a.read_text())
        data['error'] = 'kaputt'
        a.write_text(yaml.safe_dump(data))
        with self.assertRaises(ValueError):
            jobs.prioritize(self.base, rel(self.base, a))
        with self.assertRaises(ValueError):
            jobs.cancel(self.base, rel(self.base, a))
        with self.assertRaises(ValueError):
            jobs.cancel(self.base, 'gibt-es-nicht.yml')

    def test_cli_and_schema(self):
        from jsonschema import Draft202012Validator
        schema = Draft202012Validator(json.loads((ROOT / 'schemas/job.schema.json').read_text()))
        a = self.add('sec-01-01', AT)
        self.assertEqual(jobs.main([str(self.base), 'enqueue', '--section', 'sec-01-02', '--priority', '--after', rel(self.base, a)]), 0)
        files = jobs.files(self.base)
        data = yaml.safe_load(files[1].read_text())
        self.assertEqual((data['priority'], data['after']), (True, rel(self.base, a)))
        self.assertEqual(list(schema.iter_errors(data)), [])
        self.assertEqual(jobs.main([str(self.base), 'prioritize', '--request', rel(self.base, a)]), 0)
        self.assertEqual(jobs.main([str(self.base), 'cancel', '--request', rel(self.base, files[1])]), 0)
        self.assertEqual(jobs.main([str(self.base), 'cancel', '--request', 'nix']), 2)
        self.assertEqual(len(jobs.files(self.base)), 1)


class StartConditionTest(Base):
    """#65: Startbedingungen am Auftrag – feste Zeit, freies Budget, Ereignis; alle müssen erfüllt sein."""
    T0 = __import__('datetime').datetime.fromisoformat('2026-11-26T10:00:00+00:00')

    def ready(self, now=None, low=False):
        with mock.patch.object(jobs, 'budget_low', return_value=low):
            return [j['section_id'] for j in jobs.queue(self.base, now=now or self.T0)]

    def approve_chapter(self, chapter, at):
        p = self.base / 'approvals.yml'
        data = yaml.safe_load(p.read_text(encoding='utf-8')) if p.is_file() else {'entries': []}
        data['entries'].append({'kind': 'chapter', 'id': chapter, 'action': 'granted', 'at': at, 'by': 'x', 'commit': 'abc1234'})
        p.write_text(yaml.safe_dump(data), encoding='utf-8')

    def test_not_before_waits_and_then_starts(self):
        self.add('sec-01-01', AT, not_before='2026-11-27T02:00:00+00:00')
        self.assertEqual(self.ready(), [])
        j = jobs.jobs(self.base, now=self.T0)[0]
        self.assertIn('nicht vor 2026-11-27T02:00:00+00:00', j['start_wait'])
        self.assertEqual(j['state'], 'open')
        later = self.T0 + __import__('datetime').timedelta(days=1)
        self.assertEqual(self.ready(later), ['sec-01-01'])

    def test_not_before_stays_after_a_run_without_it(self):   # process arbeitet nur Fälliges ab
        self.add('sec-01-01', AT, not_before='2026-11-27T02:00:00+00:00')
        self.add('sec-02-01', AT)
        with self.fake_run(), mock.patch.object(jobs, 'budget_low', return_value=False):
            results, remaining = jobs.process(self.base, commit=False, now=self.T0)
        self.assertEqual([c[0] for c in self.calls], ['sec-02-01'])
        self.assertEqual((len(results), remaining), (1, 0))
        self.assertEqual(len(list(self.base.glob('chapters/*/research/sec-01-01/request-*.yml'))), 1)

    def test_budget_free_waits_while_low_and_runs_when_free(self):
        self.add('sec-01-01', AT, when='budget_free')
        self.assertEqual(self.ready(low=True), [])
        self.assertIn('KI-Budget', self._wait(low=True))
        self.assertEqual(self.ready(low=False), ['sec-01-01'])

    def _wait(self, low):
        with mock.patch.object(jobs, 'budget_low', return_value=low):
            return jobs.jobs(self.base, now=self.T0)[0]['start_wait']

    def test_budget_free_ignores_the_confirmation_override_but_plain_jobs_do_not_wait(self):
        self.add('sec-01-01', AT)
        self.assertEqual(self.ready(low=True), ['sec-01-01'])   # ohne Bedingung entscheidet wie bisher die Budgetprüfung beim Lauf

    def test_event_chapter_approved_after_enqueue(self):
        self.approve_chapter('ch-01', '2026-11-20T08:00:00+00:00')   # vor dem Einreihen: zählt nicht
        self.add('sec-02-01', '2026-11-25T09:00:00+00:00', after_event='chapter_approved:ch-01')
        self.assertEqual(self.ready(), [])
        self.approve_chapter('ch-02', '2026-11-26T08:00:00+00:00')   # anderes Kapitel: zählt nicht
        self.assertEqual(self.ready(), [])
        self.approve_chapter('ch-01', '2026-11-26T09:00:00+00:00')
        self.assertEqual(self.ready(), ['sec-02-01'])

    def test_event_edition_and_material_use_baseline(self):
        self.add('sec-01-01', AT, after_event='edition_created')
        self.add('sec-02-01', AT, after_event='material_added')
        self.assertEqual(self.ready(), [])
        config = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        config.setdefault('project', {})['current_edition'] = 1
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(config), encoding='utf-8')
        self.assertEqual(self.ready(), ['sec-01-01'])
        (self.base / 'quellen/2026-11-26-foto').mkdir(parents=True)
        (self.base / 'quellen/2026-11-26-foto/material.yml').write_text('art: foto\n', encoding='utf-8')
        self.assertEqual(sorted(self.ready()), ['sec-01-01', 'sec-02-01'])

    def test_conditions_combine_all_must_hold(self):
        self.add('sec-01-01', AT, not_before='2026-11-26T09:00:00+00:00', when='budget_free')
        self.assertEqual(self.ready(low=True), [])    # Zeit erreicht, Budget knapp
        self.assertEqual(self.ready(low=False), ['sec-01-01'])
        j = jobs.jobs(self.base, now=self.T0 - __import__('datetime').timedelta(hours=2))
        self.assertIn('nicht vor', j[0]['start_wait'])

    def test_enqueue_validates_and_cli_lists_condition(self):
        for bad in ({'not_before': 'gestern'}, {'when': 'immer'}, {'after_event': 'regen'}):
            with self.assertRaises(ValueError):
                self.add('sec-01-01', AT, **bad)
        self.add('sec-01-01', AT, after_event='edition_created')
        data = yaml.safe_load(next(self.base.glob('chapters/*/research/sec-01-01/request-*.yml')).read_text(encoding='utf-8'))
        self.assertEqual((data['after_event'], data['event_baseline']), ('edition_created', {'edition': 0, 'material': 0}))
        import jsonschema
        jsonschema.validate(data, json.loads((ROOT / 'schemas/job.schema.json').read_text(encoding='utf-8')))
        with mock.patch('builtins.print') as out:
            jobs.main([str(self.base), 'list', '--json'])
        self.assertIn('Ereignis', json.loads(out.call_args[0][0])[0]['start_wait'])

    def test_remote_pending_skips_future_not_before(self):
        future = (__import__('datetime').datetime.now(__import__('datetime').timezone.utc) + __import__('datetime').timedelta(days=2)).isoformat()
        self.add('sec-01-01', AT, not_before=future)
        self.add('sec-01-02', AT)
        from test_jobs import git
        git(self.base, 'add', '.')
        git(self.base, 'commit', '-qm', 'Auftraege')
        git(self.base, 'push', '-q', 'origin', 'HEAD:refs/heads/ghostwriter/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        pending = jobs.remote_pending(self.base)
        self.assertEqual(sum(sum(w.values()) for w in pending.values()), 1)
