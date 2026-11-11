"""Tests für „Manuskript ausgeben“ (#260): scripts/assemble.py manuscript und scripts/fetch_artifact.py."""
import io
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assemble  # noqa: E402
import fetch_artifact  # noqa: E402
from render_view import load  # noqa: E402


class ManuscriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / 'adhs'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.chapter = cfg['structure']['chapters'][0]
        self.sections = self.chapter['sections']

    def set_section(self, idx, goal='Offen.', summary='Offen.', manuscript='Noch nicht begonnen.', status='planned'):
        s = self.sections[idx]
        path = self.base / s['path']
        head = path.read_text(encoding='utf-8').split('## Ziel des Abschnitts')[0]
        head = re.sub(r'(?m)^status: \w+', f'status: {status}', head, count=1)
        path.write_text(head + f'## Ziel des Abschnitts\n\n{goal}\n\n## Kurzbeschreibung\n\n{summary}\n\n'
                               f'## Manuskript\n\n{manuscript}\n', encoding='utf-8')
        return s

    def run_file(self, kind, folder, body, section_id=None, date='2026-11-05'):
        d = self.base / self.chapter['path'] / kind / folder
        d.mkdir(parents=True, exist_ok=True)
        n = len(list(d.glob('run-*.md'))) + 1
        sid = f'section_id: {section_id}\n' if section_id else 'section_id: <SECTION-ID>\n'
        (d / f'run-{n:03d}.md').write_text(f'---\nid: run-{n:03d}\ntype: {kind}\n{sid}status: completed\ndate: {date}\n---\n\n'
                                           f'# Lauf\n\n{body}', encoding='utf-8')

    def chapter_md(self):
        _, config = load(self.base)
        return assemble.chapter_markdown(self.base, config['structure']['chapters'][0], 1, proof=True, plan=True)[0]

    def block(self, md, title):
        part = md.split(f'## {title}\n', 1)[1]
        return part.split('\n## ', 1)[0]

    def test_text_is_kept_and_empty_section_becomes_planned(self):
        s = self.set_section(1, goal='Der Leser versteht die Etiketten. Er kennt drei Kernsymptome.',
                             summary='- Unaufmerksamkeit\n- Impulsivität')
        md = self.chapter_md()
        planned = self.block(md, s['title'])
        self.assertIn('::: geplant', planned)
        self.assertIn('- Der Leser versteht die Etiketten.\n- Er kennt drei Kernsymptome.', planned)
        self.assertIn('- Unaufmerksamkeit\n- Impulsivität', planned)
        self.assertNotIn('Noch nicht begonnen', planned)
        first = self.block(md, self.sections[0]['title'])
        self.assertNotIn('::: geplant', first)
        self.assertIn('Küchentisch', first)

    def test_nothing_planned(self):
        s = self.set_section(2)
        self.assertIn('**Geplant** – noch ohne Beschreibung', self.block(self.chapter_md(), s['title']))

    def test_runs_done_and_open_points(self):
        s = self.set_section(3, status='brainstorming')
        self.run_file('brainstorming', s['id'], '## Offene Fragen\n\n- Welche Studie?\n\n## Ausgewählte Ergebnisse\n\n- Alltag als Einstieg\n',
                      section_id=s['id'])
        self.run_file('research', Path(s['path']).stem, '## Offene Fragen\n\nQuelle zur Häufigkeit fehlt.\n', date='2026-11-07')
        self.run_file('research', 'kapitel', '## Offene Fragen\n\n- Gehört nicht zum Abschnitt\n')
        self.run_file('brainstorming', 'anderer', '## Offene Fragen\n\n- Fremd\n', section_id='sec-anderer')
        planned = self.block(self.chapter_md(), s['title'])
        self.assertIn('Stand: Ideensammlung', planned)
        self.assertIn('- 1 Recherchelauf (zuletzt 2026-11-07)', planned)
        self.assertIn('- 1 Brainstorminglauf (zuletzt 2026-11-05)', planned)
        self.assertIn('- Ausgewählt: Alltag als Einstieg', planned)
        self.assertIn('- Ziel noch nicht beschrieben', planned)
        self.assertIn('- Welche Studie?', planned)
        self.assertIn('- Quelle zur Häufigkeit fehlt.', planned)
        self.assertNotIn('Gehört nicht', planned)
        self.assertNotIn('Fremd', planned)

    def test_keywords_are_verbatim(self):
        self.assertEqual(assemble.keywords('Offen.'), [])
        self.assertEqual(assemble.keywords('<Was soll dieser Abschnitt leisten?>'), [])
        self.assertEqual(assemble.keywords('Erstens dies. Zweitens das!'), ['Erstens dies.', 'Zweitens das!'])
        self.assertEqual(assemble.keywords('1. Eins\n2) Zwei'), ['Eins', 'Zwei'])

    def test_overview_counts_and_chapter_filter(self):
        self.set_section(1)
        self.set_section(2)
        _, config = load(self.base)
        md, total = assemble.manuscript_overview(self.base, config, only=1, date='2026-11-11', commit='abcdef123')
        self.assertEqual(total['planned'], 2)
        self.assertEqual(total['text'], len(self.sections) - 2)
        self.assertIn('Manuskript vom 11.11.2026, Commit abcdef1', md)
        self.assertEqual(len(re.findall(r'(?m)^\| \d+ \|', md)), 1)
        parts = assemble.book_parts(self.base, config, plan=True, only=2)
        self.assertEqual([p[0] for p in parts], [2])

    def test_cli_manuscript(self):
        self.set_section(1)
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base), 'manuscript', '1',
                              '--date', '2026-11-11'], capture_output=True, text=True, check=True).stdout
        self.assertTrue(out.startswith('# Arbeitsstand'))
        self.assertIn('::: geplant', out)

    def test_proof_and_edition_unchanged(self):
        self.set_section(1)
        _, config = load(self.base)
        proof = ''.join(p[2] for p in assemble.book_parts(self.base, config, proof=True))
        self.assertNotIn('::: geplant', proof)
        self.assertEqual(assemble.book_parts(self.base, config), [])

    def test_build_edition_rejects_chapter_without_manuscript(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--proof', '--chapter', '1'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--chapter nur mit --manuscript', r.stderr)

    @unittest.skipUnless(shutil.which('pandoc') and shutil.which('xelatex'), 'pandoc/xelatex fehlen')
    def test_build_pdf(self):
        self.set_section(1, goal='Ziel in einem Satz.')
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--manuscript',
                                '--chapter', '1', '--out', tmp, '--date', '2026-11-11'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            pdfs = list(Path(tmp).glob('*.pdf'))
            self.assertEqual([p.name for p in pdfs], ['adhs-im-erwachsenenleben-manuskript-2026-11-11-kapitel-1.pdf'])


class FetchArtifactTests(unittest.TestCase):
    def zip_bytes(self, files):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            for name, data in files.items():
                z.writestr(name, data)
        return buf.getvalue()

    def test_pick_skips_expired_and_other_names(self):
        arts = [{'name': 'manuskript', 'expired': True, 'id': 1}, {'name': 'probedruck', 'id': 2},
                {'name': 'manuskript', 'expired': False, 'id': 3}]
        self.assertEqual(fetch_artifact.pick(arts, 'manuskript')['id'], 3)
        self.assertIsNone(fetch_artifact.pick(arts[:2], 'manuskript'))

    def test_extract_flattens_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = fetch_artifact.extract(self.zip_bytes({'a/buch.pdf': b'%PDF', '../boese.pdf': b'x'}), Path(tmp))
            self.assertEqual(sorted(f.name for f in files), ['boese.pdf', 'buch.pdf'])
            self.assertTrue(all(f.parent == Path(tmp) for f in files))

    def test_main_downloads_successful_run(self):
        responses = {
            'repos/o/r/actions/runs/7': {'status': 'completed', 'conclusion': 'success', 'html_url': 'u'},
            'repos/o/r/actions/runs/7/artifacts': {'artifacts': [{'name': 'manuskript', 'id': 9, 'expired': False}]},
        }
        data = self.zip_bytes({'buch-manuskript.pdf': b'%PDF-1.7'})
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(fetch_artifact, 'get', side_effect=lambda p, raw=False: data if raw else responses[p]):
            out = io.StringIO()
            with mock.patch('sys.stdout', out):
                code = fetch_artifact.main(['x', 'o/r', '--run', '7', '--out', tmp])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / 'buch-manuskript.pdf').is_file())

    def test_main_download_blocked_gives_link(self):
        responses = {
            'repos/o/r/actions/runs/7': {'status': 'completed', 'conclusion': 'success', 'html_url': 'https://lauf'},
            'repos/o/r/actions/runs/7/artifacts': {'artifacts': [{'name': 'manuskript', 'id': 9, 'expires_at': '2026-11-25T07:59:07Z'}]},
        }
        def get(path, raw=False):
            if raw:
                raise fetch_artifact.DownloadError()
            return responses[path]
        out = io.StringIO()
        with mock.patch.object(fetch_artifact, 'get', side_effect=get), mock.patch('sys.stdout', out):
            self.assertEqual(fetch_artifact.main(['x', 'o/r', '--run', '7']), 2)
        self.assertIn('https://lauf', out.getvalue())
        self.assertIn('2026-11-25', out.getvalue())
        self.assertNotIn('blob.core', out.getvalue())

    def test_main_reports_failed_run(self):
        with mock.patch.object(fetch_artifact, 'get', return_value={'status': 'completed', 'conclusion': 'failure', 'html_url': 'u'}):
            out = io.StringIO()
            with mock.patch('sys.stdout', out):
                self.assertEqual(fetch_artifact.main(['x', 'o/r', '--run', '7']), 1)
            self.assertIn('fehlgeschlagen', out.getvalue())


if __name__ == '__main__':
    unittest.main()
