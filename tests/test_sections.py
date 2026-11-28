"""Abschnitte zusammenlegen, entfernen, verschieben (#293, scripts/sections.py)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from types import SimpleNamespace

from tests.authority_helpers import fake_github

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import sections  # noqa: E402
import images  # noqa: E402
import render_view  # noqa: E402
import validate_project  # noqa: E402
from test_cover import png  # noqa: E402

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

    def add_test_image(self, section):
        fake_github(self, self.base, seal=False)
        image_file = Path(self.tmp.name) / 'testbild.png'
        png(image_file, 120, 80)
        return images.add(self.base, section, image_file, caption='Testbild', source='own')

    def test_merge_moves_images_and_retargets_section_id(self):
        meta, _ = self.add_test_image('1.3')
        sections.cmd_merge(self.base, '1.3', '1.2', 'archive')

        config = self.config()
        folder = self.base / CH1 / 'images' / S2
        stored = yaml.safe_load((folder / f'{meta["id"]}.yml').read_text(encoding='utf-8'))
        self.assertEqual(stored['section_id'], S2)
        found = images.all_images(self.base, config)
        self.assertIn(meta['id'], found)
        self.assertEqual(found[meta['id']][0]['section_id'], S2)
        view = render_view.images_view(self.base, config, SimpleNamespace(where='1.2', text=True))
        self.assertIn(meta['id'], view)
        self.valid()

    def test_merge_moves_images_across_chapters_and_retargets_section_id(self):
        meta, _ = self.add_test_image('1.3')
        target = self.config()['structure']['chapters'][1]['sections'][0]
        target_id = target['id']
        target_chapter = target['path'].split('/')[0]
        sections.cmd_merge(self.base, '1.3', target_id, 'archive')

        config = self.config()
        folder = self.base / target_chapter / 'images' / target_id
        stored = yaml.safe_load((folder / f'{meta["id"]}.yml').read_text(encoding='utf-8'))
        self.assertEqual(stored['section_id'], target_id)
        found = images.all_images(self.base, config)
        self.assertIn(meta['id'], found)
        self.assertEqual(found[meta['id']][0]['section_id'], target_id)
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


    def test_add_rename_reorder(self):
        """#209: neuer Abschnitt, umbenennen und umstellen innerhalb des Kapitels."""
        out = sections.cmd_add(self.base, '1', 'Ein neuer Gedanke', position=2, paragraphs=['Erster Absatz.', 'Zweiter Absatz.'])
        self.assertIn('1.2', out)
        ids = self.ids()
        self.assertEqual(ids[1], 'sec-01-02-ein-neuer-gedanke')
        new = next(x for x in self.config()['structure']['chapters'][0]['sections'] if x['id'] == ids[1])
        text = (self.base / new['path']).read_text(encoding='utf-8')
        self.assertIn('number: "1.2"', text)
        self.assertTrue(text.rstrip().endswith('Erster Absatz.\n\nZweiter Absatz.'))
        self.assertEqual(ids[2], S2)                                   # der alte Abschnitt 1.2 ist jetzt 1.3
        self.valid()
        sections.cmd_rename(self.base, S2, 'Neue Überschrift')
        sec = next(x for x in self.config()['structure']['chapters'][0]['sections'] if x['id'] == S2)
        self.assertEqual(sec['title'], 'Neue Überschrift')
        self.assertIn('# 1.3 Neue Überschrift', (self.base / sec['path']).read_text(encoding='utf-8'))
        self.assertIn('| 1.3 | Neue Überschrift |', (self.base / CH1 / 'README.md').read_text(encoding='utf-8'))
        sections.cmd_reorder(self.base, S3, after=None)               # an den Anfang
        self.assertEqual(self.ids()[0], S3)
        sections.cmd_reorder(self.base, S3, after=S2)
        self.assertEqual(self.ids()[self.ids().index(S3) - 1], S2)
        self.valid()

    def test_reorder_allows_approved_section_but_not_across_chapters(self):
        cfg = self.config()
        sec = next(x for x in cfg['structure']['chapters'][0]['sections'] if x['id'] == S3)
        path = self.base / sec['path']
        path.write_text(path.read_text(encoding='utf-8').replace('section: false', 'section: true').replace('status: writing', 'status: approved'), encoding='utf-8')
        sections.cmd_reorder(self.base, S3, after=None)
        self.assertEqual(self.ids()[0], S3)
        with self.assertRaises(SystemExit):
            sections.cmd_reorder(self.base, S3, after=self.config()['structure']['chapters'][1]['sections'][0]['id'])


if __name__ == '__main__':
    unittest.main()
