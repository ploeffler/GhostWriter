"""Voraussetzungen für die redaktionelle Prüfung eines ganzen Kapitels."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from chapter_revision import readiness


class ChapterRevisionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.chapter = {'sections': [{'id': 'sec-1', 'path': 'a.md'}, {'id': 'sec-2', 'path': 'b.md'}]}
        self.write('a.md', 'writing', 'Erster Text.')
        self.write('b.md', 'revision', 'Zweiter Text.')

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, state, text):
        (self.base / name).write_text(f'---\nstatus: {state}\n---\n\n## Manuskript\n\n{text}\n', encoding='utf-8')

    def test_all_written_states_are_allowed(self):
        for state in ('writing', 'revision', 'fact_check', 'ready_for_approval', 'approved'):
            with self.subTest(state=state):
                self.write('b.md', state, 'Text')
                self.assertTrue(readiness(self.base, self.chapter)['ready'])

    def test_empty_placeholder_or_unwritten_status_blocks(self):
        for state, text in [('writing', ''), ('writing', 'Noch nicht begonnen.'), ('planned', 'Text'),
                            ('ready_to_write', 'Text'), ('unknown', 'Text')]:
            with self.subTest(state=state, text=text):
                self.write('b.md', state, text)
                result = readiness(self.base, self.chapter)
                self.assertFalse(result['ready'])
                self.assertTrue(any(i['section'] == 'sec-2' for i in result['issues']))

    def test_missing_or_invalid_file_and_empty_chapter_block(self):
        (self.base / 'b.md').unlink()
        self.assertFalse(readiness(self.base, self.chapter)['ready'])
        (self.base / 'b.md').write_text('broken', encoding='utf-8')
        self.assertFalse(readiness(self.base, self.chapter)['ready'])
        self.assertFalse(readiness(self.base, {'sections': []})['ready'])


if __name__ == '__main__':
    unittest.main()
