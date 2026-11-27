"""YAML schreiben ohne Kommentare und unveränderte Einträge zu verlieren (#717)."""
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from yaml_keep import dump_keep  # noqa: E402

OLD = """# GESPERRT: kein apply
# zweite Zeile

datum: '2026-11-25'
# Kommentar vor der Liste
hinweise:
- id: e-001
  alt: "absichtlich anders umbrochen als safe_dump, damit sichtbar ist, ob der alte Text bleibt"
  neu: x
- id: e-002   # Zeilenkommentar
  alt: b
  neu: ''
fassung: 3
"""


class YamlKeepTest(unittest.TestCase):
    def test_unchanged_is_identical(self):
        self.assertEqual(dump_keep(OLD, yaml.safe_load(OLD)), OLD)

    def test_changed_entry_only(self):
        data = yaml.safe_load(OLD)
        data['hinweise'][1]['neu'] = 'neu'
        data['hinweise'].append({'id': 'e-003', 'alt': 'c'})
        out = dump_keep(OLD, data)
        self.assertEqual(yaml.safe_load(out), data)
        for keep in ('# GESPERRT: kein apply', '# zweite Zeile', '# Kommentar vor der Liste',
                     '  alt: "absichtlich anders umbrochen als safe_dump, damit sichtbar ist, ob der alte Text bleibt"'):
            self.assertIn(keep, out.splitlines())
        self.assertIn('- id: e-003', out)

    def test_scalar_change_keeps_rest(self):
        data = yaml.safe_load(OLD)
        data['fassung'] = 4
        self.assertEqual(dump_keep(OLD, data), OLD.replace('fassung: 3', 'fassung: 4'))

    def test_new_and_removed_keys(self):
        data = yaml.safe_load(OLD)
        del data['datum']
        data['gesperrt'] = 'Autor prüft noch'
        out = dump_keep(OLD, data)
        self.assertEqual(yaml.safe_load(out), data)
        self.assertTrue(out.startswith('# GESPERRT: kein apply\n# zweite Zeile\n'))

    def test_fallback_keeps_header(self):
        out = dump_keep('# Kopf\n[1, 2]\n', {'a': 1})
        self.assertEqual(out, '# Kopf\na: 1\n')
        self.assertEqual(dump_keep(None, {'a': 1}), 'a: 1\n')


if __name__ == '__main__':
    unittest.main()
