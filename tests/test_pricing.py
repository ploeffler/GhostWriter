"""#66: Preistabelle, EZB-Kurs, automatische Schätzung je Aufruf, Auswertungen. Feste Preise und Kurse, keine Netzabfrage."""
import datetime
import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import costs  # noqa: E402
import limits  # noqa: E402
import pricing  # noqa: E402
import research  # noqa: E402
from test_research import ANTHROPIC, NOW, book  # noqa: E402

PRICES = {'anthropic': {'claude-test': {'currency': 'USD', 'input_per_mtok': 2, 'output_per_mtok': 10, 'search_per_1k': 10,
                                        'source': 'https://example.test/preise', 'checked_at': '2026-11-26'}},
          'nosearch': {'m': {'currency': 'USD', 'input_per_mtok': 1, 'output_per_mtok': 4}}}
DAILY = ('<?xml version="1.0"?><gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" '
         'xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref"><Cube><Cube time="2026-11-26">'
         '<Cube currency="USD" rate="1.2500"/><Cube currency="GBP" rate="0.8000"/></Cube></Cube></gesmes:Envelope>')
HIST = DAILY.replace('<Cube time="2026-11-26">', '<Cube time="2026-11-26"><Cube currency="USD" rate="1.2500"/></Cube>'
                     '<Cube time="2026-11-20">').replace('1.2500"/><Cube currency="GBP"', '1.1000"/><Cube currency="GBP"', 1)


def fetcher(daily=DAILY, hist=HIST):
    def fetch(url):
        return {pricing.ECB_DAILY: daily, pricing.ECB_HIST: hist}[url]
    return fetch


class PriceTableTest(unittest.TestCase):
    def test_every_entry_has_source_date_and_prices(self):
        for provider, models in pricing.table().items():
            for model, e in models.items():
                self.assertTrue(str(e.get('source')).startswith('https://'), (provider, model))
                self.assertGreaterEqual(str(e.get('checked_at')), '2026-11-26', (provider, model))
                self.assertGreater(e['input_per_mtok'], 0)
                self.assertGreater(e['output_per_mtok'], 0)

    def test_estimate_with_fixed_prices(self):
        est = pricing.estimate('anthropic', 'claude-test', 12000, 3000, 4, PRICES)
        self.assertEqual(est['amount'], Decimal('0.024') + Decimal('0.03') + Decimal('0.04'))   # 0,094 USD
        self.assertEqual((est['currency'], est['search_priced']), ('USD', True))
        self.assertEqual(pricing.estimate('anthropic', 'claude-test-20261126', 1000000, 0, 0, PRICES)['amount'], Decimal(2))

    def test_unknown_model_stays_unknown_never_zero(self):
        self.assertIsNone(pricing.estimate('anthropic', 'claude-anders', 1000, 1000, 0, PRICES))
        self.assertIsNone(pricing.estimate('google', 'gemini-x', 1000, 1000, 0, PRICES))
        self.assertIsNone(pricing.estimate('anthropic', 'claude-test-x', 1, 1, 0, PRICES))   # kein ähnliches Modell

    def test_searches_without_search_price_are_flagged(self):
        est = pricing.estimate('nosearch', 'm', 1000000, 0, 5, PRICES)
        self.assertEqual((est['amount'], est['search_priced']), (Decimal(1), False))

    def test_openai_terra_has_no_standard_price_yet(self):   # offene Frage an Peter (#66)
        self.assertIsNone(pricing.lookup('openai', 'gpt-6.1-terra'))


class RateTest(unittest.TestCase):
    def test_parse_and_day_lookup(self):
        data = pricing.parse_ecb(DAILY)
        self.assertEqual(data['2026-11-26']['USD'], Decimal('1.2500'))
        day, rates = pricing.rates_for('2026-11-26', fetcher())
        self.assertEqual((day, rates['USD']), ('2026-11-26', Decimal('1.2500')))
        day, rates = pricing.rates_for('2026-11-22', fetcher())   # Wochenende: letzter Kurs davor
        self.assertEqual((day, rates['USD']), ('2026-11-20', Decimal('1.1000')))

    def test_convert_via_eur(self):
        rates = {'USD': Decimal('1.25'), 'GBP': Decimal('0.8')}
        self.assertEqual(pricing.convert(10, 'USD', 'EUR', rates)[0], Decimal(8))
        self.assertEqual(pricing.convert(10, 'EUR', 'USD', rates)[0], Decimal('12.5'))
        self.assertEqual(pricing.convert(10, 'USD', 'GBP', rates)[0], Decimal('6.4'))
        self.assertIsNone(pricing.convert(10, 'USD', 'CHF', rates))

    def test_cost_fields_converted_with_rate_and_date(self):
        est = pricing.estimate('anthropic', 'claude-test', 1000000, 0, 0, PRICES)   # 2 USD
        f = pricing.cost_fields(est, 'EUR', '2026-11-26', fetcher())
        self.assertEqual((f['currency'], f['cost_amount'], f['cost_status']), ('EUR', 1.6, 'estimated'))
        self.assertEqual((f['original_currency'], f['original_amount'], f['exchange_rate'], f['exchange_rate_date'],
                          f['exchange_rate_source'], f['exchange_rate_status']), ('USD', 2.0, 0.8, '2026-11-26', 'ECB', 'applied'))
        self.assertEqual((f['pricing_source'], f['pricing_checked_at']), ('https://example.test/preise', '2026-11-26'))

    def test_offline_keeps_original_currency_marked(self):
        est = pricing.estimate('anthropic', 'claude-test', 1000000, 0, 0, PRICES)

        def boom(url):
            raise OSError('offline')
        f = pricing.cost_fields(est, 'EUR', '2026-11-26', boom)
        self.assertEqual((f['currency'], f['cost_amount'], f['exchange_rate_status']), ('USD', 2.0, 'unavailable'))
        self.assertNotIn('exchange_rate', f)
        broken = pricing.cost_fields(est, 'EUR', '2026-11-26', lambda u: '<kaputt')
        self.assertEqual(broken['exchange_rate_status'], 'unavailable')

    def test_same_currency_needs_no_rate(self):
        est = pricing.estimate('anthropic', 'claude-test', 1000000, 0, 0, PRICES)
        f = pricing.cost_fields(est, 'USD', '2026-11-26', lambda u: 1 / 0)
        self.assertEqual((f['currency'], f['cost_amount']), ('USD', 2.0))
        self.assertNotIn('exchange_rate_status', f)


class RunIntegrationTest(unittest.TestCase):
    def run_research(self, ecb=True):
        tmp, base = book({'research': {'provider': 'anthropic'}, 'available': ['anthropic'],
                          'services': {'anthropic': {'access': 'api', 'api_key_secret': 'ANTHROPIC_API_KEY'}}})
        self.addCleanup(tmp.cleanup)
        fetch = fetcher() if ecb else mock.Mock(side_effect=OSError('offline'))
        with mock.patch.object(research, 'post_json', return_value=ANTHROPIC), \
                mock.patch.object(pricing, 'table', return_value=PRICES), \
                mock.patch.object(pricing, 'fetch_url', side_effect=fetch), \
                mock.patch.dict(os.environ, {research.KEY_ENV: 'k'}):
            head = research.run(base, 'sec-01-01-start', model='claude-test', now=datetime.datetime(2026, 11, 26, 10, tzinfo=datetime.timezone.utc))
        cost = yaml.safe_load((base / 'chapters/ch-01-anfang/costs/sec-01-01-start.yml').read_text())
        return base, head, cost['entries'][0]

    def test_entry_without_hand_input_is_converted_and_valid(self):
        base, head, e = self.run_research()
        usd = 2000 / 1e6 * 2 + 500 / 1e6 * 10 + 3 / 1000 * 10    # 0,039 USD
        self.assertEqual((e['cost_status'], e['currency'], e['original_currency']), ('estimated', 'EUR', 'USD'))
        self.assertAlmostEqual(e['original_amount'], usd, places=4)
        self.assertAlmostEqual(e['cost_amount'], usd * 0.8, places=4)
        self.assertEqual((e['exchange_rate'], e['exchange_rate_date']), (0.8, '2026-11-26'))
        self.assertEqual(head['cost'], e['cost_amount'])
        jsonschema.validate({'section_id': 'sec-01-01-start', 'entries': [e]},
                            json.loads((ROOT / 'schemas/costs.schema.json').read_text(encoding='utf-8')))

    def test_offline_entry_is_estimated_but_not_converted(self):
        _, _, e = self.run_research(ecb=False)
        self.assertEqual((e['cost_status'], e['currency'], e['exchange_rate_status']), ('estimated', 'USD', 'unavailable'))
        info = costs.summary(self.run_research(ecb=False)[0])
        self.assertEqual(info['unconverted'], 1)
        self.assertIn('Nicht umgerechnet', costs.text(info))

    def test_book_price_wins_over_table(self):
        tmp, base = book({'research': {'provider': 'anthropic'}, 'available': ['anthropic'], 'services': {'anthropic': {
            'access': 'api', 'api_key_secret': 'ANTHROPIC_API_KEY', 'price_input_per_mtok': 1, 'price_output_per_mtok': 1}}})
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(research, 'post_json', return_value=ANTHROPIC), mock.patch.object(pricing, 'table', return_value=PRICES), \
                mock.patch.object(pricing, 'fetch_url', side_effect=OSError), mock.patch.dict(os.environ, {research.KEY_ENV: 'k'}):
            research.run(base, 'sec-01-01-start', model='claude-test', now=NOW)
        e = yaml.safe_load((base / 'chapters/ch-01-anfang/costs/sec-01-01-start.yml').read_text())['entries'][0]
        self.assertNotIn('original_currency', e)
        self.assertAlmostEqual(e['cost_amount'], 2500 / 1e6 + 3 / 1000 * 0, places=4)   # nur Tokens: kein Suchpreis im Buch


class ReportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        config = {'project': {'title': 'B'}, 'structure': {'chapters': [
            {'id': 'ch-1', 'title': 'K', 'path': 'chapters/ch-1', 'sections': [{'id': 'sec-1', 'title': 'T', 'path': 'x'}]}]}}
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(config), encoding='utf-8')

        def e(i, month, status, amount, provider='p', activity='research', section='sec-1', cur='EUR'):
            d = {'activity_id': f'a{i}', 'occurred_at': f'{month}-05T10:00:00Z', 'source': 'action_api', 'provider': provider,
                 'model': 'm', 'activity_type': activity, 'currency': cur, 'cost_amount': amount, 'cost_status': status}
            if section:
                d['section_id'] = section
            return d
        (self.base / 'chapters/ch-1/costs').mkdir(parents=True)
        (self.base / 'chapters/ch-1/costs/sec-1.yml').write_text(yaml.safe_dump({'section_id': 'sec-1', 'entries': [
            e(1, '2026-10', 'estimated', 1.0), e(2, '2026-11', 'estimated', 0.5), e(3, '2026-11', 'actual', 2.0, provider='q'),
            e(4, '2026-11', 'unavailable', None, activity='writing')]}), encoding='utf-8')
        (self.base / 'costs').mkdir()
        (self.base / 'costs/project.yml').write_text(yaml.safe_dump({'scope': 'project', 'entries': [
            e(5, '2026-11', 'manually_entered', 4.0, section=None, activity='other')]}), encoding='utf-8')

    def test_breakdowns_keep_statuses_apart_and_add_up(self):
        total = costs.summary(self.base)
        for by in costs.BY:
            rows = costs.breakdown(self.base, by)
            self.assertEqual(sum(r['calls'] for r in rows), total['calls'], by)
            self.assertEqual(sum(r['unavailable'] for r in rows), 1, by)
            for status in ('estimated', 'actual', 'manually_entered'):
                got = sum((a for r in rows for a in r['amounts'][status].values()), Decimal(0))
                self.assertEqual(got, total['by_status'][status]['amounts'].get('EUR', Decimal(0)), (by, status))
        month = {r['key']: r for r in costs.breakdown(self.base, 'month')}
        self.assertEqual(month['2026-11']['amounts']['estimated'], {'EUR': Decimal('0.5')})
        chapter = {r['key']: r for r in costs.breakdown(self.base, 'chapter')}
        self.assertEqual(set(chapter), {'ch-1', '(Projekt)'})
        self.assertEqual(chapter['(Projekt)']['amounts']['manually_entered'], {'EUR': Decimal('4.0')})
        self.assertIn('Kosten je Monat', costs.breakdown_text(costs.breakdown(self.base, 'month'), 'month'))
        with self.assertRaises(ValueError):
            costs.breakdown(self.base, 'weekday')

    def test_month_sum_matches_budget_figure(self):   # Akzeptanz: Monatssumme und Restbudget stimmen mit den Einträgen überein
        info = costs.summary(self.base, '2026-11')
        self.assertEqual(Decimal(str(limits.month_costs(self.base, '2026-11'))), sum(info['known_total'].values()))
        self.assertEqual(costs.main([str(self.base), 'summary', '--by', 'provider']), 0)
