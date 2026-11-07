"""Vollständigkeit und Schreibfreiheit des Nachzieh-Kontexts."""
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from catch_up import prepare


class CatchUpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.config = {'structure': {'chapters': [
            {'id': 'ch-a', 'title': 'A', 'sections': [
                {'id': 's1', 'path': 'a.md'}, {'id': 's2', 'path': 'b.md'}]},
            {'id': 'ch-b', 'title': 'B', 'sections': [{'id': 's3', 'path': 'c.md'}]}]}}
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(self.config))
        for name in ('a.md', 'b.md', 'c.md'):
            (self.base / name).write_text('---\nstatus: writing\n---\n\n## Manuskript\n\nText ' + name)

    def test_all_sections_and_full_text_without_mutation(self):
        before = {p.name: p.read_bytes() for p in self.base.iterdir()}
        result = prepare(self.base, material='Neue Anekdote')
        self.assertTrue(result['complete'])
        self.assertEqual([len(c['sections']) for c in result['chapters']], [2, 1])
        self.assertEqual(result['material'], 'Neue Anekdote')
        self.assertIn('Text a.md', result['chapters'][0]['sections'][0]['document'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.base.iterdir()})

    def test_scope_and_stale_input_fingerprint(self):
        first = prepare(self.base, '1')
        self.assertEqual(first, prepare(self.base, 'ch-a') | {'scope': '1'})
        (self.base / 'a.md').write_text('---\nstatus: writing\n---\n\n## Manuskript\n\nNeu')
        newer = prepare(self.base, '1')
        self.assertNotEqual(first['chapters'][0]['sections'][0]['sha256'], newer['chapters'][0]['sections'][0]['sha256'])
        with self.assertRaises(ValueError):
            prepare(self.base, '99')

    def test_missing_unreadable_and_empty_are_not_silently_skipped(self):
        for text in (None, 'kein Abschnitt', '---\nstatus: planned\n---\n\n## Manuskript\n\nNoch nicht begonnen.'):
            with self.subTest(text=text):
                path = self.base / 'b.md'
                if text is None:
                    path.unlink()
                else:
                    path.write_text(text)
                result = prepare(self.base, '1')
                self.assertEqual(len(result['chapters'][0]['sections']), 2)
                self.assertFalse(result['chapters'][0]['revision_readiness']['ready'])
                if text is None or text == 'kein Abschnitt':
                    self.assertFalse(result['complete'])
