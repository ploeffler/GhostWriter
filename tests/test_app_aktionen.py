"""Knopf-Inventar der Claude-Web-App (#662, #597): kein Knopf ohne Behandlung oder Eintrag."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import check_docs  # noqa: E402

APP = ROOT / 'apps' / 'claude'


class AppAktionen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = set(check_docs.action_table(check_docs.read('templates/ui/BEFUELLUNG.md')))
        html = (APP / 'index.html').read_text(encoding='utf-8')
        cls.handled = set(re.findall(r'case "([a-z_]+(?:\.[a-z_]+)+)"', html))
        cls.inventory = json.loads((APP / 'aktionen.json').read_text(encoding='utf-8'))['actions']

    def test_jede_aktion_hat_behandlung_oder_eintrag(self):
        missing = sorted(self.table - self.handled - set(self.inventory))
        self.assertEqual(missing, [], 'Aktionen ohne Behandlung in apps/claude/index.html und ohne Eintrag in aktionen.json')

    def test_eintrag_nur_fuer_unbehandelte_bekannte_aktionen(self):
        self.assertEqual(sorted(set(self.inventory) & self.handled), [], 'Aktion ist behandelt, Eintrag streichen')
        self.assertEqual(sorted(set(self.inventory) - self.table), [], 'Eintrag für unbekannte Aktion')

    def test_eingebettete_liste_entspricht_aktionen_json(self):
        html = (APP / 'index.html').read_text(encoding='utf-8')
        m = re.search(r'/\*GW-NA\*/(.*?)/\*GW-NA-END\*/', html, re.S)
        self.assertTrue(m, 'Marke /*GW-NA*/ in index.html fehlt')
        embedded = json.loads(m.group(1))
        expected = {k: v['reason']['de'] for k, v in self.inventory.items()}
        self.assertEqual(embedded, expected, 'index.html neu aus aktionen.json erzeugen (Liste zwischen /*GW-NA*/ und /*GW-NA-END*/)')

    def test_eintraege_vollstaendig(self):
        for name, e in self.inventory.items():
            self.assertIn(e['state'], ('chat', 'spaeter'), name)
            self.assertTrue(e['reason']['de'] and e['reason']['en'], name)


if __name__ == '__main__':
    unittest.main()
