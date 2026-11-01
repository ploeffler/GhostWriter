import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

spec = importlib.util.spec_from_file_location('context', Path(__file__).resolve().parents[1] / 'scripts/plan_context.py')
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.section = self.base / 'section.md'
        config = {'structure': {'chapters': [{'id': 'ch-one', 'title': 'One', 'sections': [
            {'id': 'sec-one', 'path': 'section.md'}]}]}}
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(config))

    def write_words(self, n):
        self.section.write_text('---\nid: sec-one\n---\n## Ziel des Abschnitts\nNicht mitzählen\n## Manuskript\n' + 'Wort ' * n + '\n## Notizen\nNicht mitzählen\n')

    def test_boundary_and_limited_context(self):
        self.write_words(15000)
        self.assertEqual(context.plan(self.base)['mode'], 'full')
        self.assertEqual(context.plan(self.base)['word_count'], 15000)
        self.assertEqual(context.plan(self.base, True)['mode'], 'summaries')
        self.write_words(15001)
        result = context.plan(self.base)
        self.assertEqual(result['mode'], 'summaries')
        self.assertEqual(result['manuscript_paths'], [])
        self.assertEqual(result['reload_required'], ['ch-one'])

    def test_summary_invalidated_after_edit(self):
        self.write_words(3)
        first = context.plan(self.base)
        self.assertEqual(first['book_summary']['state'], 'missing')
        (self.base / 'context').mkdir()
        for item in [first['book_summary'], *first['chapter_summaries']]:
            (self.base / item['path']).write_text('---\nsource_commit: "' + 'a' * 40 + '"\nsource_digest: ' + item['source_digest'] + '\n---\nInhaltszusammenfassung\n')
        self.assertEqual(context.plan(self.base)['book_summary']['state'], 'current')
        self.assertEqual(context.plan(self.base)['reload_required'], [])
        self.write_words(4)
        self.assertEqual(context.plan(self.base)['book_summary']['state'], 'stale')
        self.assertEqual(context.plan(self.base)['reload_required'], ['ch-one'])

    def test_empty_and_unicode(self):
        self.section.write_text('## Manuskript\nNoch nicht begonnen.\n')
        self.assertEqual(context.plan(self.base)['word_count'], 0)
        self.assertEqual(context.word_count('Überblick: ADHS-Alltag, Gefühle!'), 3)


if __name__ == '__main__':
    unittest.main()
