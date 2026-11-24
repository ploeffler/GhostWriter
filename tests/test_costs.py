"""#66 (v1.0-Umfang): Kostenarten unterscheiden, manuelle Einträge."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import costs  # noqa: E402

SCHEMA = json.loads((ROOT / 'schemas/costs.schema.json').read_text(encoding='utf-8'))


def entry(status, amount, source='action_api', month='2026-11', cur='EUR'):
    return {'activity_id': f'a-{status}-{amount}', 'occurred_at': f'{month}-02T10:00:00Z', 'source': source,
            'provider': 'p', 'model': 'm', 'activity_type': 'research', 'currency': cur,
            'cost_amount': amount, 'cost_status': status}


class CostsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        shutil.rmtree(self.base / 'costs', ignore_errors=True)
        for p in self.base.glob('chapters/*/costs'):
            shutil.rmtree(p)

    def write(self, rows):
        (self.base / 'costs').mkdir(exist_ok=True)
        (self.base / 'costs/project.yml').write_text(yaml.safe_dump({'scope': 'project', 'entries': rows}), encoding='utf-8')

    def test_statuses_are_separated_and_unknown_never_zero(self):
        self.write([entry('actual', 1.0), entry('estimated', 0.5), entry('manually_entered', 2.0),
                    entry('unavailable', None), entry('estimated', 9.0, source='legacy_chat_estimate'),
                    entry('actual', 4.0, month='2026-10')])
        info = costs.summary(self.base, '2026-11')
        by = info['by_status']
        self.assertEqual(by['actual']['amounts'], {'EUR': Decimal('1.0')})
        self.assertEqual(by['estimated']['amounts'], {'EUR': Decimal('0.5')})
        self.assertEqual(by['manually_entered']['count'], 1)
        self.assertEqual(by['unavailable']['count'], 1)
        self.assertEqual(info['known_total'], {'EUR': Decimal('3.5')})
        self.assertFalse(info['complete'])
        out = costs.text(info)
        self.assertIn('unbekannt: 1 · Betrag unbekannt', out)
        self.assertIn('ohne 1 Aufrufe', out)
        self.assertEqual(costs.summary(self.base)['calls'], 5)   # legacy zählt nicht

    def test_manual_entry_is_valid_and_counted(self):
        path, e = costs.add(self.base, '1.20', 'openai', 'gpt-x', note='Rechnung 42', at='2026-11-24')
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        jsonschema.validate(data, SCHEMA)
        self.assertEqual(e['cost_status'], 'manually_entered')
        self.assertEqual(costs.summary(self.base, '2026-11')['by_status']['manually_entered']['amounts'],
                         {'EUR': Decimal('1.2')})
        with self.assertRaises(ValueError):
            costs.add(self.base, '-1', 'p')
        with self.assertRaises(ValueError):
            costs.add(self.base, '1', 'p', section='sec-gibts-nicht')

    def test_cli(self):
        self.write([entry('unavailable', None)])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/costs.py'), str(self.base), 'summary'],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('Bekannte Summe: –', out.stdout)


if __name__ == '__main__':
    unittest.main()
