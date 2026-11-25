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


class SuggestTest(Base):
    """#478: Vorschlag beim Einreihen (Danach einreihen / Zusammenlegen / Unabhängig); ohne Klick ändert sich nichts."""

    def snapshot(self):
        return sorted((str(p.relative_to(self.base)), p.read_text(encoding='utf-8')) for p in self.base.rglob('request-*.yml'))

    def test_empty_queue_is_independent(self):
        s = jobs.suggest(self.base, 'sec-01-01', 'Frage')
        self.assertEqual((s['recommended'], s['options'], s['candidates']), ('independent', ['independent'], []))

    def test_same_section_recommends_merge_and_changes_nothing(self):
        a = self.add('sec-01-01', AT, question='Erste Frage')
        before = self.snapshot()
        s = jobs.suggest(self.base, 'sec-01-01', 'Zweite Frage')
        self.assertEqual(s['recommended'], 'merge')
        self.assertEqual(s['options'], ['merge', 'after', 'independent'])
        self.assertEqual([(c['request'], c['relation']) for c in s['candidates']], [(rel(self.base, a), 'same_section')])
        self.assertEqual(self.snapshot(), before)

    def test_same_chapter_recommends_after_other_chapter_is_independent(self):
        self.add('sec-01-02', AT)
        s = jobs.suggest(self.base, 'sec-01-01')
        self.assertEqual((s['recommended'], s['options']), ('after', ['after', 'independent']))
        self.assertEqual(s['candidates'][0]['relation'], 'same_chapter')
        self.assertEqual(jobs.suggest(self.base, 'sec-02-01')['recommended'], 'independent')

    def test_failed_and_locked_jobs_are_not_offered(self):
        a = self.add('sec-01-01', AT)
        data = yaml.safe_load(a.read_text(encoding='utf-8'))
        data.update({'error': 'kaputt', 'failed_at': AT})
        a.write_text(yaml.safe_dump(data), encoding='utf-8')
        self.assertEqual(jobs.suggest(self.base, 'sec-01-01')['candidates'], [])

    def test_same_section_first_then_newest(self):
        self.add('sec-01-02', '2026-11-22T21:00:00+00:00')
        b = self.add('sec-01-01', AT)
        self.add('sec-01-02', '2026-11-22T22:00:00+00:00')
        s = jobs.suggest(self.base, 'sec-01-01')
        self.assertEqual(s['candidates'][0]['request'], rel(self.base, b))
        self.assertEqual([c['requested_at'] for c in s['candidates'][1:]],
                         ['2026-11-22T22:00:00+00:00', '2026-11-22T21:00:00+00:00'])

    def test_other_types_are_independent(self):
        self.add('sec-01-01', AT)
        self.assertEqual(jobs.suggest(self.base, 'sec-01-01', type_='analysis')['recommended'], 'independent')

    def test_merge_appends_question_once_only_for_pending(self):
        a = self.add('sec-01-01', AT, question='Erste Frage')
        jobs.merge(self.base, rel(self.base, a), 'Zweite Frage')
        jobs.merge(self.base, rel(self.base, a), 'Zweite Frage')   # zweimal derselbe Klick: keine Verdopplung
        self.assertEqual(yaml.safe_load(a.read_text(encoding='utf-8'))['question'], 'Erste Frage\n\nZweite Frage')
        self.assertEqual(len(self.snapshot()), 1)               # kein zweiter Auftrag
        with self.assertRaises(ValueError):
            jobs.merge(self.base, rel(self.base, a), '')
        data = yaml.safe_load(a.read_text(encoding='utf-8'))
        data['error'] = 'x'
        a.write_text(yaml.safe_dump(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            jobs.merge(self.base, rel(self.base, a), 'Dritte')

    def test_merge_without_old_question_and_cli(self):
        a = self.add('sec-01-01', AT)
        self.assertEqual(jobs.main([str(self.base), 'merge', '--request', rel(self.base, a), '--question', 'Nur diese']), 0)
        self.assertEqual(yaml.safe_load(a.read_text(encoding='utf-8'))['question'], 'Nur diese')
        with mock.patch('builtins.print') as out:
            self.assertEqual(jobs.main([str(self.base), 'suggest', '--section', 'sec-01-01', '--json']), 0)
        self.assertEqual(json.loads(out.call_args[0][0])['recommended'], 'merge')
