"""Tests für die Prüfschleife vor dem Pull Request (#390)."""
import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify  # noqa: E402


def args(**kw):
    base = dict(base='origin/main', ui=None, skip=[], abnahme='nicht durchgeführt', abnahme_beleg='', next='')
    base.update(kw)
    return argparse.Namespace(**base)


class VerifyTest(unittest.TestCase):
    def test_secrets_report_pattern_and_place_only(self):
        token = 'ghp_' + 'A1b2C3d4' * 5
        hits = verify.scan_secrets([('a.py', 3, f'TOKEN = "{token}"'), ('b.md', 1, 'harmlos')])
        self.assertEqual(hits, [('a.py', 3, 'GitHub-Token')])
        self.assertNotIn(token, repr(hits))

    def test_stops_at_first_failure(self):
        calls = []
        def ok(a):
            calls.append('ok')
            return 'ok', ''
        def bad(a):
            calls.append('bad')
            return 'fail', 'kaputt'
        steps = [('a', 'A', ok), ('b', 'B', bad), ('c', 'C', ok)]
        res = verify.verify(args(), steps)
        self.assertEqual([s for _, s, _ in res], ['ok', 'fail', 'todo'])
        self.assertEqual(calls, ['ok', 'bad'])
        text, ready = verify.report(args(), res)
        self.assertFalse(ready)
        self.assertIn('Gesamturteil: nicht bereit', text)
        self.assertIn('Abnahme im Buch: nicht durchgeführt', text)

    def test_ready_with_skip_and_acceptance(self):
        steps = [('a', 'A', lambda a: ('ok', '')), ('tests', 'Tests', lambda a: ('fail', ''))]
        a = args(skip=['tests'], abnahme='geprüft', abnahme_beleg='chillyconcane/YAWA, 0.7.0')
        text, ready = verify.report(a, verify.verify(a, steps))
        self.assertTrue(ready)
        self.assertIn('bereit für PR', text)
        self.assertIn('Abnahme im Buch: geprüft (chillyconcane/YAWA, 0.7.0)', text)
        self.assertIn('Ausgelassen: Tests', text)

    def test_added_lines_parses_diff(self):
        lines = list(verify.added_lines('HEAD'))   # Arbeitsstand gegen HEAD; darf leer sein
        self.assertTrue(all(len(x) == 3 for x in lines))


if __name__ == '__main__':
    unittest.main()
