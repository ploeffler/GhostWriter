"""Vorabfassung (#348): Nummer, Tag, Vermerk und Dateinamen; keine Auflage."""
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_edition  # noqa: E402
import edition_info  # noqa: E402
from render_view import load, tag_slug  # noqa: E402


def git(base, *args):
    subprocess.run(['git', '-C', str(base), *args], check=True, capture_output=True)


class PreviewTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, config = load(self.base)
        p = config['project']
        self.slug = tag_slug(p.get('title_short') or p.get('title'))
        self.edition = p.get('current_edition') or 0

    def info(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(edition_info.main(['edition_info.py', str(self.base), '--preview']), 0)
        return dict(line.split('=', 1) for line in out.getvalue().splitlines())

    def test_number_counts_on_from_tags(self):
        git(self.base, 'init', '-q')
        git(self.base, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'x')
        self.assertEqual(self.info()['tag'], f'{self.slug}-vorab-1')
        git(self.base, 'tag', f'{self.slug}-vorab-1')
        git(self.base, 'tag', f'{self.slug}-vorab-3')
        git(self.base, 'tag', f'{self.slug}-auflage-1')      # Auflagen zählen nicht mit
        git(self.base, 'tag', f'anderes-buch-vorab-9')       # anderes Buch der Bibliothek
        info = self.info()
        self.assertEqual((info['build'], info['preview'], info['tag']), ('true', '4', f'{self.slug}-vorab-4'))
        self.assertIn('Vorabfassung 4', info['name'])

    def test_draft_note_only_when_present(self):
        self.assertEqual(build_edition.draft_note('Text'), '')
        self.assertEqual(build_edition.draft_note('[Stand: Entwurf, nicht abgeschlossen]{.gwstatus}'),
                         'Enthält auch nicht abgeschlossene Abschnitte.')
        self.assertEqual(build_edition.draft_note('[[TODO]]{.gwmarker}'), 'Offene Marker sind hervorgehoben.')
        self.assertIn('nicht abgeschlossene', build_edition.draft_note('{.gwstatus} {.gwmarker}'))

    def test_build_preview_epub(self):
        if not shutil.which('pandoc'):
            self.skipTest('pandoc fehlt')
        out = Path(self.base).parent / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--preview', '2',
                            '--formats', 'epub', '--out', str(out), '--date', '2026-11-19', '--commit', 'abc1234def'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ed = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))
        self.assertEqual((ed['preview'], ed['tag'], ed['edition']), (2, f'{self.slug}-vorab-2', self.edition))
        self.assertEqual(ed['files'], [f'{self.slug}-vorab-2.epub'])
        with zipfile.ZipFile(out / ed['files'][0]) as z:
            text = ''.join(z.read(n).decode('utf-8', 'replace') for n in z.namelist() if n.endswith('.xhtml'))
        self.assertIn('Vorabfassung 2 vom 19.11.2026 – nicht zur Veröffentlichung.', text)
        self.assertNotIn('Probedruck', text)

    def test_preview_excludes_edition_and_manuscript(self):
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), \
                unittest.mock.patch('sys.stderr', io.StringIO()):
            build_edition.main(['x', str(self.base), '--preview', '1', '--edition', '1'])
        with self.assertRaises(SystemExit), unittest.mock.patch('sys.stderr', io.StringIO()):
            build_edition.main(['x', str(self.base), '--preview', '0'])


if __name__ == '__main__':
    unittest.main()
