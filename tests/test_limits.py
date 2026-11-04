"""Tests für die Limitwarnung (#62): 9 % übrig pausiert, 15 % warnt, 50 % ist ok, neuer Monat setzt zurück."""
import json
import os
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
import limits  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402


class LimitTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def setup(self, spent, budget=10, extra=None):
        cfg = self.base / 'ghostwriter.yml'
        lim = {'ai_budget_monthly': budget, **(extra or {})}
        cfg.write_text(cfg.read_text(encoding='utf-8') + yaml.safe_dump({'limits': lim}), encoding='utf-8')
        entry = lambda aid, when, amount, source='backend_api': {
            'activity_id': aid, 'occurred_at': when, 'source': source, 'provider': 'openai', 'model': 'gpt-5',
            'activity_type': 'research', 'currency': 'EUR', 'cost_amount': amount, 'cost_status': 'actual'}
        (self.base / 'costs').mkdir(exist_ok=True)
        (self.base / 'costs/project.yml').write_text(yaml.safe_dump({'scope': 'project', 'entries': [
            entry('act-1', '2026-11-02T10:00:00+01:00', spent),
            entry('act-2', '2026-10-30T10:00:00+01:00', 50),                          # Vormonat
            entry('act-3', '2026-11-03T10:00:00+01:00', 99, 'legacy_chat_estimate'),  # zählt nicht
        ]}, allow_unicode=True), encoding='utf-8')
        return load(self.base)[1]

    def state(self, spent, month='2026-11', **kw):
        config = self.setup(spent, **kw)
        return limits.summary(limits.evaluate(self.base, config, month))

    def test_levels(self):
        self.assertEqual(self.state(9.1), ('pause', 'Automatik pausiert: KI-Budget 9 % übrig (9,10 von 10,00 € verbraucht)'))
        self.assertEqual(validate_project.check_project(self.base), [])

    def test_warn(self):
        self.assertEqual(self.state(8.5), ('warn', 'Vorwarnung: KI-Budget 15 % übrig (8,50 von 10,00 € verbraucht)'))

    def test_ok(self):
        self.assertEqual(self.state(5), ('ok', ''))

    def test_over_budget_and_new_month(self):
        self.assertEqual(self.state(12)[0], 'pause')
        config = load(self.base)[1]
        self.assertEqual(limits.summary(limits.evaluate(self.base, config, '2026-12')), ('ok', ''))

    def test_no_limits(self):
        self.assertEqual(limits.evaluate(self.base, load(self.base)[1], '2026-11'), [])

    def test_live_rows(self):
        config = self.setup(1, extra={'actions_minutes_monthly': 2000})
        rows = limits.evaluate(self.base, config, '2026-11', {'actions_minutes_used': 1850, 'api_rate': (4900, 5000)})
        self.assertEqual([(r['key'], r['state']) for r in rows],
                         [('ai_budget', 'ok'), ('actions_minutes', 'pause'), ('api_rate', 'pause')])
        self.assertEqual(rows[1]['text'], 'Actions-Minuten 8 % übrig (1850 von 2000 min verbraucht)')

    def test_automation_output(self):
        self.setup(9.5)
        out = self.tmp / 'out.txt'
        env = dict(os.environ, GITHUB_OUTPUT=str(out))
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/limits.py'), str(self.base), 'check', '--automation',
                            '--month', '2026-11'], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('paused=true', out.read_text(encoding='utf-8'))
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/limits.py'), str(self.base), 'check', '--month', '2026-11'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 3)

    def run_view(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args],
                              capture_output=True, text=True, check=True).stdout

    def widget(self, *args):
        m = re.search(r'GW\.render\("([^"]+)",(.*)\)</script>', self.run_view(*args))
        return json.loads(m.group(2).replace('<\\/', '</'))

    def test_views(self):
        self.setup(9.5)
        j = self.tmp / 'lim.json'
        subprocess.run([sys.executable, str(ROOT / 'scripts/limits.py'), str(self.base), 'check', '--month', '2026-11',
                        '--json', str(j)], capture_output=True)
        data = self.widget('project', '--limits', str(j))
        self.assertEqual(data['LIMIT_STATE'], 'pause')
        self.assertIn('KI-Budget 5 % übrig', data['LIMIT_TEXT'])
        self.assertIn('> ⏸ **Automatik pausiert', self.run_view('project', '--limits', str(j), '--text'))
        j.write_text(json.dumps({'state': 'ok', 'text': ''}), encoding='utf-8')
        self.assertNotIn('LIMIT_STATE', self.widget('project', '--limits', str(j)))
        s = self.widget('project-settings')
        self.assertEqual((s['LIMIT_BUDGET'], s['LIMIT_MINUTES']), ('10', ''))
        self.assertIn('| KI-Budget je Monat | 10 |', self.run_view('project-settings', '--text'))


if __name__ == '__main__':
    unittest.main()
