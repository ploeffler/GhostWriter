"""Zentrale Modellvorgaben, Fehlerklasse „Modell nicht mehr verfügbar“ und Modellprüfung (#554, #529)."""
import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import colorize  # noqa: E402
import jobs  # noqa: E402
import model_defaults as md  # noqa: E402
import research  # noqa: E402

import datetime  # noqa: E402
EARLY = datetime.date(2026, 1, 1)   # weit vor jeder angekündigten Abschaltung

# Wortlaut aus #529 (gekürzt)
GEMINI_404 = ('{"error": {"code": 404, "message": "This model models/gemini-2.5-flash is no longer available to new users. '
              'Please update your code to use models/gemini-3.8-flash for the latest features and improvements."}}')


class DefaultsTest(unittest.TestCase):
    def test_catalog_is_the_source(self):
        catalog = yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8'))['model_defaults']
        for pid, tasks in catalog.items():
            for task, e in tasks.items():
                self.assertTrue(e['model'] and e['checked_at'], (pid, task))
        for pid in research.PROVIDERS:
            self.assertEqual(research.PROVIDERS[pid]['model'], catalog[pid]['research']['model'])
        self.assertEqual(colorize.DEFAULT_MODEL, catalog['google']['image']['model'])

    def test_fallback_without_entry(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(md.default_model('google', 'research', 'fallback-1', root=d), 'fallback-1')
            Path(d, 'providers.yml').write_text('model_defaults:\n  google:\n    research: {model: neu-2, checked_at: "2026-11-24"}\n',
                                                encoding='utf-8')
            self.assertEqual(md.default_model('google', 'research', 'fallback-1', root=d), 'neu-2')
            self.assertEqual(md.default_model('google', 'image', 'fallback-1', root=d), 'fallback-1')


class ErrorClassTest(unittest.TestCase):
    def test_gemini_message_names_the_way_out(self):
        self.assertTrue(md.is_unavailable(404, GEMINI_404))
        text = md.classify_http_error(404, GEMINI_404, 'Google Gemini', 'gemini-2.5-flash')
        for part in ('gemini-2.5-flash', 'gemini-3.8-flash', 'KI-Dienste', 'erneut versuchen'):
            self.assertIn(part, text)
        self.assertNotIn('HTTP 404', text)

    def test_other_errors_stay_raw(self):
        self.assertFalse(md.is_unavailable(500, 'model not found'))
        self.assertFalse(md.is_unavailable(400, 'Invalid API key'))
        self.assertEqual(md.classify_http_error(429, 'quota', 'X', 'm'), 'Der Anbieter antwortet mit HTTP 429: quota')

    def test_research_raises_the_classified_message(self):
        err = urllib.error.HTTPError('u', 404, 'Not Found', {}, io.BytesIO(GEMINI_404.encode()))
        with mock.patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(research.ResearchError) as cm:
                research.post_json('https://example.invalid', {}, {}, 'google', 'gemini-2.5-flash')
        self.assertIn('nicht mehr verfügbar', str(cm.exception))
        self.assertIn('gemini-3.8-flash', str(cm.exception))


class CheckTest(unittest.TestCase):
    def test_check_reports_missing_models_only_with_key(self):
        def fetch(url, headers):
            return {'models': [{'name': 'models/gemini-3.8-flash'}]} if 'generativelanguage' in url else {'data': []}
        self.assertEqual(md.check(None, {}, fetch, today=EARLY), [])   # ohne Schlüssel keine Aussage
        env = {'GEMINI_API_KEY': 'x'}
        lines = md.check(None, env, fetch, today=EARLY)
        self.assertEqual(len(lines), 1, lines)               # Bildmodell fehlt in der Liste, Recherchemodell nicht
        self.assertIn('gemini-2.5-flash-image', lines[0])

    def test_network_error_is_no_statement(self):
        def fetch(url, headers):
            raise urllib.error.URLError('offline')
        self.assertEqual(md.check(None, {'GEMINI_API_KEY': 'x'}, fetch, today=EARLY), [])


class RetirementTest(unittest.TestCase):
    """#596: nahe Abschaltungen aus providers.yml, ohne Schlüssel."""

    def test_warns_from_ninety_days_before(self):
        self.assertEqual(md.retirement_lines(EARLY), [])
        lines = md.retirement_lines(datetime.date(2026, 11, 25))
        self.assertEqual(len(lines), 1, lines)
        self.assertIn('gpt-5 (openai, Recherche) wird am 2026-12-11 abgeschaltet', lines[0])
        self.assertIn('nie automatisch umgestellt', lines[0])
        later = md.retirement_lines(datetime.date(2027, 1, 5))
        self.assertTrue(any('ist seit dem 2026-12-11 abgeschaltet' in x for x in later))
        self.assertTrue(any('gemini-2.5-flash-image' in x for x in md.retirement_lines(datetime.date(2027, 2, 20))))

    def test_all_defaults_are_checked_with_a_date(self):
        catalog = yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8'))['model_defaults']
        for pid, tasks in catalog.items():
            for task, e in tasks.items():
                self.assertGreaterEqual(str(e['checked_at']), '2026-11-25', (pid, task))   # #596: echt geprüft

    def test_report_goes_into_the_daily_report(self):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            report = Path(d, 'report.md')
            env = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY')}
            env['DAILY_UPDATE_REPORT_PATH'] = str(report)
            r = subprocess.run([sys.executable, str(ROOT / 'scripts/model_defaults.py'), 'check', '--report'], env=env,
                               capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr)   # mit --report immer 0
            if report.exists():   # abhängig vom heutigen Datum: nur der Aufbau zählt
                self.assertIn('### KI-Modelle', report.read_text(encoding='utf-8'))


class RetryTest(unittest.TestCase):
    def test_retry_reopens_a_failed_job(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            req = base / 'chapters/ch-01/research/sec-01-01/request-001.yml'
            req.parent.mkdir(parents=True)
            req.write_text(yaml.safe_dump({'section_id': 'sec-01-01', 'question': 'Frage?', 'provider': 'google',
                                           'error': 'Modell weg', 'failed_at': '2026-11-23T10:00:00+00:00'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                jobs.retry(base, 'request-009.yml')
            jobs.retry(base, str(req.relative_to(base)))
            data = yaml.safe_load(req.read_text(encoding='utf-8'))
            self.assertNotIn('error', data)
            self.assertNotIn('failed_at', data)
            self.assertEqual((data['question'], data['provider']), ('Frage?', 'google'))
            self.assertEqual(len(list(req.parent.glob('request-*.yml'))), 1)   # kein zweiter Auftrag
            with self.assertRaises(ValueError):
                jobs.retry(base, str(req.relative_to(base)))   # nicht mehr fehlgeschlagen



class ReportHintTest(unittest.TestCase):
    def test_return_message_names_the_retry_for_model_errors(self):
        status = {'buch/a': {'done': 0, 'failed': 1, 'waiting': 0, 'waiting_budget': 0, 'done_sections': [],
                             'failed_reasons': ['sec-01: Das Modell x ist nicht mehr verfügbar'],
                             'model_failed': ['chapters/c/research/s/request-001.yml']}}
        text = jobs.report(status)
        self.assertIn('Modell nicht mehr verfügbar', text)
        self.assertIn('jobs.py . retry --request chapters/c/research/s/request-001.yml', text)
        self.assertIn('retry: `python3 scripts/jobs.py . retry', jobs.report(status, 'en'))


if __name__ == '__main__':
    unittest.main()
