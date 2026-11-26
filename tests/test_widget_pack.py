"""Kompakte Widget-Daten (#674): pack_payload/unpack_payload und die Ausgabe von render_view.fill."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import render_view as rv  # noqa: E402


class PackPayloadTest(unittest.TestCase):
    def test_leere_felder_entfallen_werte_bleiben(self):
        p = rv.pack_payload({'A': '', 'B': [], 'C': None, 'D': 0, 'E': False, 'F': 'x'})
        self.assertEqual(p, {'_PACK': 1, 'D': 0, 'E': False, 'F': 'x'})

    def test_gleichartige_bloecke_werden_kompakt(self):
        rows = [{'C_ID': f'ch-{i}', 'C_TITLE': f'Kapitel {i}', 'C_NOTE': ''} for i in range(5)]
        p = rv.pack_payload({'CHAPTERS': rows})
        self.assertEqual(p['CHAPTERS']['k'], ['C_ID', 'C_TITLE', 'C_NOTE'])
        self.assertEqual(p['CHAPTERS']['r'][0], ['ch-0', 'Kapitel 0'])   # leerer Wert am Ende entfällt
        self.assertEqual(rv.unpack_payload(p), {'CHAPTERS': rows})
        self.assertLess(len(json.dumps(p)), len(json.dumps({'CHAPTERS': rows})))

    def test_ungleiche_zeilen_bleiben_objekte(self):
        rows = [{'A': '1', 'B': '2'}, {'A': '3'}]
        self.assertEqual(rv.pack_payload({'X': rows})['X'], rows)

    def test_kurzer_block_bleibt_wenn_kompakt_nicht_kuerzer(self):
        rows = [{'A': '1'}]
        self.assertEqual(rv.pack_payload({'X': rows})['X'], rows)

    def test_ohne_pack_unveraendert(self):
        d = {'A': ''}
        self.assertIs(rv.unpack_payload(d), d)

    def test_fill_schickt_kompakte_daten_rohdaten_bleiben(self):
        rv.UI.update({'repo': 'ploeffler/ghostwriter-ui', 'ref': 'abc', 'language': 'de', 'head': ''})
        out = rv.fill('kapitelansicht.html', {'CHAPTER_TITLE': 'T', 'CHAPTER_NOTE': ''},
                      {'SECTIONS': [{'S_ID': 'sec-1', 'S_TITLE': 'A'}, {'S_ID': 'sec-2', 'S_TITLE': 'B'}]})
        payload = json.loads(re.search(r'GW\.render\("kapitelansicht",(.*)\)</script>', out).group(1))
        self.assertEqual(payload['_PACK'], 1)
        self.assertNotIn('CHAPTER_NOTE', payload)
        self.assertEqual(out.data['CHAPTER_NOTE'], '')   # Rohdaten für native Ansichten vollständig
        self.assertEqual(rv.unpack_payload(payload)['SECTIONS'], out.data['SECTIONS'])


if __name__ == '__main__':
    unittest.main()
