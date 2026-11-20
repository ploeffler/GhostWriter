"""Abschnitte zusammenlegen, entfernen, verschieben (#293, scripts/sections.py)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import sections  # noqa: E402
import validate_project  # noqa: E402

CH1 = 'chapters/01-endlich-eine-erklaerung'
S2 = 'sec-01-02-die-etiketten-die-wir-kennen'
S3 = 'sec-01-03-was-hinter-den-etiketten-steckt'


class SectionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def config(self):
        return yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))

    def ids(self, ch=0):
        return [s['id'] for s in self.config()['structure']['chapters'][ch]['sections']]

    def valid(self):
        self.assertEqual(validate_project.check_project(self.base), [])

    def blank(self, sid, goal='Offen.'):
        cfg = self.config()
        sec = next(s for ch in cfg['structure']['chapters'] for s in ch['sections'] if s['id'] == sid)
        path = self.base / sec['path']
        text = path.read_text(encoding='utf-8')
        text = text.split('\n## Manuskript\n')[0] + '\n## Manuskript\n\nNoch nicht begonnen.\n'
        text = text.replace('## Ziel des Abschnitts\n\nOffen.', f'## Ziel des Abschnitts\n\n{goal}', 1)
        path.write_text(text, encoding='utf-8')
        return path

    def test_merge_without_manuscript(self):
        self.blank(S3, goal='Etiketten einordnen.')
        (self.base / CH1 / 'research' / S3).mkdir(parents=True)
        (self.base / CH1 / 'research' / S3 / 'run-001.md').write_text('# Lauf\n', encoding='utf-8')
        note = self.base / 'brainstorming.md'
        note.write_text(f'Siehe [{S3}]({CH1}/sections/03-was-hinter-den-etiketten-steckt.md)\n', encoding='utf-8')
        before = self.ids()
        out = sections.cmd_merge(self.base, '1.3', '1.2')
        self.assertIn('übernommen', out)
        self.assertNotIn(S3, self.ids())
        self.assertEqual(len(self.ids()), len(before) - 1)
        target = (self.base / CH1 / 'sections/02-die-etiketten-die-wir-kennen.md').read_text(encoding='utf-8')
        self.assertIn('## Übernommenes Material aus dem früheren Abschnitt 1.3', target)
        self.assertIn('Etiketten einordnen.', target)
        self.assertTrue((self.base / CH1 / 'research' / S2 / 'run-001.md').is_file())
        self.assertFalse((self.base / CH1 / 'sections/03-was-hinter-den-etiketten-steckt.md').exists())
        self.assertIn('02-die-etiketten-die-wir-kennen.md', note.read_text(encoding='utf-8'))
        nxt = (self.base / CH1 / 'sections/04-die-uhr-die-bei-mir.md').read_text(encoding='utf-8')
        self.assertIn('number: "1.3"', nxt)
        self.assertIn('# 1.3 Die Uhr', nxt)
        readme = (self.base / CH1 / 'README.md').read_text(encoding='utf-8')
        self.assertIn('| 1.3 | Die Uhr, die bei mir anders tickt |', readme)
        self.assertEqual(self.config()['structure']['retired'][0]['merged_into'], S2)
        self.valid()

    def test_manuscript_needs_choice(self):
        with self.assertRaises(SystemExit) as e:
            sections.cmd_merge(self.base, '1.3', '1.2')
        self.assertIn('--manuscript', str(e.exception))
        sections.cmd_merge(self.base, '1.3', '1.2', 'archive')
        self.assertTrue((self.base / 'archiv/01-endlich-eine-erklaerung/03-was-hinter-den-etiketten-steckt.md').is_file())
        self.valid()

    def test_merge_append_manuscript(self):
        src = (self.base / CH1 / 'sections/03-was-hinter-den-etiketten-steckt.md').read_text(encoding='utf-8')
        sample = sections.manuscript(src).splitlines()[0]
        sections.cmd_merge(self.base, S3, S2, 'append')
        target = (self.base / CH1 / 'sections/02-die-etiketten-die-wir-kennen.md').read_text(encoding='utf-8')
        self.assertIn(sample, sections.manuscript(target))
        self.valid()

    def test_history_in_approvals_stays_valid(self):
        """Abschnitt mit Schreibfreigabe im Protokoll zusammenlegen → validate grün (#293)."""
        self.blank(S3)
        (self.base / 'approvals.yml').write_text(yaml.safe_dump({'entries': [
            {'kind': 'writing', 'id': S3, 'action': 'granted', 'at': '2026-11-01T10:00:00Z', 'by': 'autor', 'commit': 'abc1234'}]}),
            encoding='utf-8')
        self.valid()
        sections.cmd_merge(self.base, S3, S2)
        self.valid()

    def test_locked_section_refused(self):
        path = self.blank(S3)
        path.write_text(path.read_text(encoding='utf-8').replace('  section: false', '  section: true'), encoding='utf-8')
        with self.assertRaises(SystemExit) as e:
            sections.cmd_merge(self.base, S3, S2)
        self.assertIn('Freigabe', str(e.exception))

    def test_remove_archives(self):
        with self.assertRaises(SystemExit):
            sections.cmd_remove(self.base, '1.3')
        out = sections.cmd_remove(self.base, '1.3', confirm=True)
        self.assertIn('entfernt', out)
        self.assertNotIn(S3, self.ids())
        self.assertTrue((self.base / 'archiv/01-endlich-eine-erklaerung/03-was-hinter-den-etiketten-steckt.md').is_file())
        self.assertEqual(self.config()['structure']['retired'][0]['action'], 'removed')
        self.valid()

    def test_move_to_other_chapter(self):
        cfg = self.config()
        ch2 = cfg['structure']['chapters'][1]
        n2 = len(ch2['sections'])
        out = sections.cmd_move(self.base, '1.3', '2', position=1)
        self.assertIn('jetzt 2.1', out)
        self.assertNotIn(S3, self.ids(0))
        self.assertEqual(self.ids(1)[0], S3)
        self.assertEqual(len(self.ids(1)), n2 + 1)
        moved = self.base / ch2['path'] / 'sections/01-was-hinter-den-etiketten-steckt.md'
        self.assertIn('number: "2.1"', moved.read_text(encoding='utf-8'))
        self.valid()

    def test_yaml_rest_unchanged(self):
        self.blank(S3)
        before = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        sections.cmd_merge(self.base, S3, S2)
        after = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        self.assertEqual(before.split('  chapters:')[0], after.split('  retired:')[0])


if __name__ == '__main__':
    unittest.main()
