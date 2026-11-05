"""Tests für scripts/assemble.py (#14) mit dem ADHS-Projekt aus tests/fixtures/adhs."""
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assemble  # noqa: E402
from render_view import load  # noqa: E402


class AssembleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / 'adhs'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)

    def approve(self, chapter_no, sections=None, strip_markers=True):
        """Kapitel und Abschnitte freigeben (Status approved), optional Marker entfernen."""
        cfg_path = self.base / 'ghostwriter.yml'
        cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
        ch = cfg['structure']['chapters'][chapter_no - 1]
        ch['status'] = 'approved'
        cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding='utf-8')
        ledger_path = self.base / 'approvals.yml'
        ledger = yaml.safe_load(ledger_path.read_text(encoding='utf-8')) if ledger_path.is_file() else {'entries': []}
        for i, section in enumerate(ch['sections'], start=1):
            if sections is not None and i not in sections:
                continue
            path = self.base / section['path']
            text = path.read_text(encoding='utf-8')
            text = re.sub(r'(?m)^status: \w+', 'status: approved', text, count=1)
            if strip_markers:
                text = re.sub(r'\*?\[(PLATZHALTER-ANEKDOTE|QUELLE PRÜFEN|MEDIZIN PRÜFEN|RECHT PRÜFEN)[^\]]*\]\*?', '', text)
            manuscript = text.split('## Manuskript\n', 1)[1].strip()
            digest = hashlib.sha256(manuscript.encode('utf-8')).hexdigest()
            text = re.sub(r'(?m)^  section: \w+', f'  section: true\n  section_content_sha256: {digest}', text, count=1)
            path.write_text(text, encoding='utf-8')
            ledger['entries'].append({'kind': 'section', 'id': section['id'], 'action': 'granted',
                'at': '2026-11-05T12:00:00Z', 'by': 'test', 'commit': '1234567', 'content_sha256': digest})
        ledger['entries'].append({'kind': 'chapter', 'id': ch['id'], 'action': 'granted',
            'at': '2026-11-05T12:00:00Z', 'by': 'test', 'commit': '1234567'})
        ledger_path.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False), encoding='utf-8')
        readme = self.base / ch['path'] / 'README.md'
        if strip_markers:
            readme.write_text(re.sub(r'\[(QUELLE PRÜFEN|MEDIZIN PRÜFEN)[^\]]*\]', '', readme.read_text(encoding='utf-8')),
                              encoding='utf-8')
        return ch

    def test_nothing_approved_blocks_edition(self):
        _, config = load(self.base)
        found = assemble.problems(assemble.book_parts(self.base, config), config)
        self.assertTrue(found and found[0].startswith('Kein Kapitel ist freigegeben'))

    def test_chapter_contains_only_approved_sections_in_order(self):
        ch = self.approve(1, sections={1, 3})
        _, config = load(self.base)
        md, skipped, markers = assemble.chapter_markdown(self.base, config['structure']['chapters'][0], 1)
        titles = re.findall(r'(?m)^## (.+)$', md)
        self.assertEqual(titles[:2], [ch['sections'][0]['title'], ch['sections'][2]['title']])
        self.assertEqual(len(skipped), len(ch['sections']) - 2)
        self.assertEqual(markers, [])
        self.assertNotIn('## Manuskript', md)
        self.assertNotIn('Vorspann', md)

    def test_post_approval_manuscript_change_is_excluded(self):
        chapter = self.approve(1)
        section = chapter['sections'][0]
        path = self.base / section['path']
        text = path.read_text(encoding='utf-8')
        text = text.replace('## Manuskript\n', '## Manuskript\n\nNach der Freigabe eingefügter Text.\n', 1)
        path.write_text(text, encoding='utf-8')
        _, config = load(self.base)
        md, skipped, _ = assemble.chapter_markdown(self.base, config['structure']['chapters'][0], 1)
        self.assertNotIn('Nach der Freigabe eingefügter Text.', md)
        self.assertTrue(any('Freigabe fehlt oder Manuskript seit Freigabe geändert' in item for item in skipped))
        found = assemble.problems(assemble.book_parts(self.base, config), config)
        self.assertTrue(any('nicht freigegebene Abschnitte' in item for item in found), found)

    def test_markers_block_and_clean_chapter_passes(self):
        self.approve(1, strip_markers=False)
        _, config = load(self.base)
        found = assemble.problems(assemble.book_parts(self.base, config), config)
        self.assertTrue(any(f.startswith('Offener Marker') for f in found))
        self.approve(1, strip_markers=True)
        _, config = load(self.base)
        self.assertEqual(assemble.problems(assemble.book_parts(self.base, config), config), [])

    def test_book_has_metadata_and_cli_check(self):
        self.approve(1)
        out = Path(self.temp.name) / 'book.md'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base), 'book', '--edition', '3',
                            '-o', str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        head = yaml.safe_load(out.read_text(encoding='utf-8').split('---')[1])
        self.assertEqual(head['edition'], 3)
        self.assertEqual(head['typesetting']['page_size'], 'a5')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base), 'check'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == '__main__':
    unittest.main()


class EmptyProjectTest(unittest.TestCase):
    """Leeres Projekt (Abnahme #18): Auflage und Probedruck melden klar, was fehlt."""
    EMPTY = ROOT / 'tests/fixtures/leeres-projekt'

    def test_check_names_title_and_chapters(self):
        _, config = load(self.EMPTY)
        found = assemble.problems(assemble.book_parts(self.EMPTY, config), config)
        self.assertTrue(any(x.startswith('Das Buch hat noch keinen Titel') for x in found))
        self.assertTrue(any(x.startswith('Kein Kapitel ist freigegeben') for x in found))

    def test_edition_form_blocks_without_junk_name(self):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.EMPTY), 'edition-create', '--text'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('Ohne Titel – Auflage 1', out)
        self.assertIn('`ohne-titel-auflage-1`', out)
        self.assertIn('noch keine Kapitel', out)
        self.assertIn('So kann die Auflage nicht gebaut werden', out)

    def test_proof_refuses_without_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.EMPTY), '--proof',
                                '--out', tmp], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('noch keine Kapitel', r.stderr + r.stdout)


class CreditNotInBookTest(unittest.TestCase):
    """Der Hinweis auf die Entwicklung von GhostWriter steht nie im Buch.
    Eine buchspezifische KI-Angabe (wie bei diesem Buch KI genutzt wurde) ist etwas
    anderes und darf Dienste wie Claude nennen; sie steuert der Autor je Buch."""

    def test_book_and_proof_without_credit(self):
        text = yaml.safe_load((ROOT / 'templates/branding.yml').read_text(encoding='utf-8'))['credit']['text']
        base, config = load(ROOT / 'tests/fixtures/adhs')
        for proof in (False, True):
            parts = assemble.book_parts(base, config, proof=proof)
            meta = assemble.metadata(config, 1, '2026-11-01')
            book = yaml.safe_dump(meta, allow_unicode=True) + ''.join(p[2] for p in parts)
            self.assertNotIn(text, book)
        for name in ('header.tex', 'merkkasten.lua', 'epub.css'):
            path = ROOT / 'templates/book' / name
            if path.is_file():
                self.assertNotIn(text, path.read_text(encoding='utf-8'))
