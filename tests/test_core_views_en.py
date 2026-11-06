"""Englische Kernansichten: keine Übersetzung von Buchdaten, keine geänderten Freigabegrenzen."""
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from scripts import render_view_en

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'scripts' / 'render_view.py'


class EnglishCoreViewsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'book'
        shutil.copytree(ROOT / 'tests/fixtures/leeres-projekt', self.base)
        self.config = yaml.safe_load((self.base / 'ghostwriter.yml').read_text())
        self.config['project']['title'] = 'Beschreibung – Kapitel'
        self.save()

    def save(self):
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(self.config, allow_unicode=True))

    def run_view(self, *args, check=True):
        r = subprocess.run([sys.executable, str(RENDER), str(self.base), *args, '--repo', 'owner/book'], capture_output=True, text=True)
        if check:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_english_default_is_native_and_preserves_title(self):
        before = (self.base / 'ghostwriter.yml').read_bytes()
        text = self.run_view('project', '--language', 'en').stdout
        self.assertIn('Beschreibung – Kapitel', text)
        self.assertIn('Author:', text)
        self.assertIn('No chapters yet', text)
        self.assertIn('`N` Add a new chapter', text)
        self.assertNotIn('<script', text)
        self.assertEqual(before, (self.base / 'ghostwriter.yml').read_bytes())

    def test_book_language_does_not_select_interface(self):
        self.config['project']['language'] = 'en'
        self.save()
        self.assertIn('Noch keine Kapitel', self.run_view('project', '--text').stdout)
        self.config['project']['language'] = 'de'
        self.config['interface'] = {'language': 'en-GB'}
        self.save()
        self.assertIn('No chapters yet', self.run_view('project').stdout)
        self.assertIn('Noch keine Kapitel', self.run_view('project', '--text', '--language', 'de').stdout)

    def test_ui_preview_carries_language_and_raw_status(self):
        text = self.run_view('project', '--language', 'en', '--ui-ref', 'a' * 40).stdout
        data = json.loads(re.search(r'GW.render\("projektuebersicht",(.*?)\)</script>', text).group(1))
        self.assertEqual(data['LANGUAGE'], 'en')
        self.assertEqual(data['PROJECT_TITLE'], self.config['project']['title'])
        self.assertEqual(data['PROJECT_EDITION_TEXT'], 'no edition yet')
        self.assertIn('a' * 40, text)

    def test_untranslated_forms_do_not_silently_return_german_as_english(self):
        r = self.run_view('project-edit', '--text', '--language', 'en', check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('English output is not yet available', r.stderr)
        self.assertIn('Projektdaten', self.run_view('project-edit', '--text', '--language', 'de').stdout)

    def test_library_cards_are_localized_without_changing_titles(self):
        data = {'books': [{'branch': 'buch/test', 'title': 'Kapitel Beschreibung', 'title_short': 'TEST', 'author': 'Autor', 'status': 'ready', 'sections_total': 2, 'sections_approved': 1, 'chapters_total': 1, 'chapters_approved': 0, 'current_edition': 2, 'pending': 1}], 'series': []}
        (self.base / 'library.json').write_text(json.dumps(data))
        before = copy.deepcopy(data)
        text = self.run_view('library', '--text', '--language', 'en').stdout
        self.assertIn('Library', text)
        self.assertIn('Kapitel Beschreibung', text)
        self.assertIn('1 of 2 sections approved', text)
        self.assertIn('Edition 2', text)
        self.assertIn('1 pending change', text)
        self.assertNotIn('1 pending changes', text)
        self.assertEqual(json.loads((self.base / 'library.json').read_text()), before)

    def chapter(self, complete):
        section = self.base / 'chapters' / '01' / 'sections' / '01.md'
        section.parent.mkdir(parents=True)
        section.write_text('---\nid: s1\nstatus: writing\n---\n\n## Manuskript\n\n' + ('Originaltext mit [QUELLE PRÜFEN].' if complete else 'Noch nicht begonnen.') + '\n')
        (section.parent.parent / 'README.md').write_text('# Kapitel 1\n\n## Ziel des Kapitels\n\nDeutsches Ziel.\n\n## Kurzbeschreibung\n\nDeutsche Kurzbeschreibung.\n')
        self.config['structure']['chapters'] = [{'id': 'c1', 'title': 'Kapitel Beschreibung', 'path': 'chapters/01', 'status': 'in_progress', 'sections': [{'id': 's1', 'title': 'Beschreibung Kapitel', 'path': 'chapters/01/sections/01.md', 'status': 'writing'}]}]
        self.save()
        return section

    def test_chapter_preserves_goals_and_respects_revision_readiness(self):
        self.chapter(False)
        text = self.run_view('chapter', '1', '--text', '--language', 'en').stdout
        self.assertIn('Chapter goal', text)
        self.assertIn('1 section', text)
        self.assertNotIn('1 sections', text)
        self.assertIn('Deutsches Ziel.', text)
        self.assertIn('Deutsche Kurzbeschreibung.', text)
        self.assertIn('Beschreibung Kapitel', text)
        self.assertNotIn('`KU`', text)
        self.assertNotIn('`FK`', text)

    def test_ready_chapter_retains_revision_action_and_raw_manuscript(self):
        section = self.chapter(True)
        before = section.read_bytes()
        text = self.run_view('chapter', '1', '--text', '--language', 'en').stdout
        self.assertIn('`KU` Revise chapter', text)
        self.assertIn('writing', text)
        self.assertNotIn('`FK`', text)
        self.assertEqual(section.read_bytes(), before)
        self.assertNotIn('Originaltext', text)

    def test_approved_chapter_offers_confirmation_without_changing_approval(self):
        section = self.chapter(True)
        section.write_text(section.read_text().replace('status: writing', 'status: approved'))
        self.config['structure']['chapters'][0]['status'] = 'ready_for_approval'
        self.config['structure']['chapters'][0]['sections'][0]['status'] = 'approved'
        self.save()
        before = section.read_bytes()
        text = self.run_view('chapter', '1', '--text', '--language', 'en').stdout
        self.assertIn('`FK` Approve chapter', text)
        self.assertEqual(section.read_bytes(), before)
        self.assertEqual(yaml.safe_load((self.base / 'ghostwriter.yml').read_text())['structure']['chapters'][0]['status'], 'ready_for_approval')

    def test_project_highlights_last_edited_chapter(self):
        self.chapter(True)
        self.config['workflow']['current_chapter_id'] = 'c1'
        self.config['workflow']['current_section_id'] = 's1'
        self.save()
        text = self.run_view('project', '--language', 'en').stdout
        self.assertIn('**`1`**', text)
        self.assertIn('`1.1` open (last edited)', text)

    def test_library_series_uses_raw_volume_number(self):
        data = {'books': [{'branch': 'buch/test', 'title': 'Deutsches Buch', 'title_short': 'TEST', 'status': 'ready'}],
                'series': [{'id': 'ser-test', 'title': 'Deutsche Serie', 'volumes': ['buch/test']}]}
        (self.base / 'library.json').write_text(json.dumps(data))
        text = self.run_view('library', '--language', 'en').stdout
        self.assertIn('Series “Deutsche Serie”', text)
        self.assertIn('Volume 1: Deutsches Buch', text)
        self.assertIn('1 book', text)
        self.assertNotIn('1 books', text)

    def test_shared_resource_contract(self):
        self.assertEqual(render_view_en.validate_resources(), [])


if __name__ == '__main__':
    unittest.main()
