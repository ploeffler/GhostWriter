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

    def test_section_preserves_manuscript_and_approval_state(self):
        section = self.chapter(True)
        section.write_text(section.read_text().replace('status: writing\n', 'status: writing\nfact_check: optional\napprovals:\n  writing: false\n  section: false\n'))
        before = section.read_bytes()
        text = self.run_view('section', '1.1', '--language', 'en').stdout
        self.assertIn('Originaltext mit [QUELLE PRÜFEN].', text)
        self.assertIn('Check source', text)
        self.assertIn('Writing approval', text)
        self.assertIn('`FS` Approve writing', text)
        self.assertIn('`K` To chapter', text)
        self.assertNotIn('Schreibfreigabe', text)
        self.assertEqual(before, section.read_bytes())
        self.assertEqual(text, self.run_view('section', '1.1', '--language', 'en', '--text').stdout)
        preview = self.run_view('section', '1.1', '--language', 'en', '--ui-ref', 'a' * 40).stdout
        data = json.loads(re.search(r'GW.render\("abschnitt-bearbeiten",(.*?)\)</script>', preview).group(1))
        self.assertEqual(data['MARKERS'][0]['MARKER_LABEL'], 'Check source')
        self.assertEqual(data['SECTION_MANUSCRIPT'].strip(), 'Originaltext mit [QUELLE PRÜFEN].')

    def test_edition_form_localizes_warnings_formats_and_preserves_identifiers(self):
        self.config['project']['title_short'] = 'Buch {name}'
        self.config['typesetting'] = {'formats': ['pdf_print', 'cover', 'epub']}
        self.save()
        before = (self.base / 'ghostwriter.yml').read_bytes()
        text = self.run_view('edition-create', '--language', 'en').stdout
        self.assertIn('Create a new edition · Edition 1', text)
        self.assertIn('The book has no chapters yet.', text)
        self.assertIn('no chapter has been approved yet', text)
        self.assertIn('Print PDF, Cover, EPUB', text)
        self.assertIn('`Date: YYYY-MM-DD`', text)
        self.assertIn('`Notes: …`', text)
        self.assertEqual(text, self.run_view('edition-create', '--language', 'en', '--text').stdout)
        previews = []
        for language in ('de', 'en'):
            html = self.run_view('edition-create', '--language', language, '--ui-ref', 'a' * 40).stdout
            previews.append(json.loads(re.search(r'GW.render\("auflage-erzeugen",(.*?)\)</script>', html).group(1)))
        self.assertEqual(previews[0]['EDITION_NAME'], previews[1]['EDITION_NAME'])
        self.assertEqual(previews[0]['EDITION_TAG'], previews[1]['EDITION_TAG'])
        self.assertIn('Buch {name}', previews[1]['EDITION_NAME'])
        self.assertIn('The edition cannot be built', previews[1]['APPROVAL_WARNING_TEXT'])
        self.assertEqual(previews[1]['FORMATS'][0]['FORMAT_LABEL'], 'Print PDF')
        self.assertEqual(before, (self.base / 'ghostwriter.yml').read_bytes())

    def test_edition_warning_tracks_approvals_and_markers_without_changing_them(self):
        section = self.chapter(True)
        self.config['structure']['chapters'][0]['status'] = 'approved'
        self.save()
        text = self.run_view('edition-create', '--language', 'en').stdout
        self.assertIn('approved chapters contain unapproved sections', text)
        section.write_text(section.read_text().replace('status: writing', 'status: approved'))
        before = section.read_bytes()
        text = self.run_view('edition-create', '--language', 'en').stdout
        self.assertIn('open markers in approved text: 1', text)
        self.assertNotIn('contain unapproved sections', text)
        self.assertEqual(before, section.read_bytes())
        section.write_text(section.read_text().replace('[QUELLE PRÜFEN]', 'geprüfter Quelle'))
        text = self.run_view('edition-create', '--language', 'en').stdout
        self.assertNotIn('cannot be built', text)
        self.assertNotIn('⚠️', text)

    def test_edition_missing_title_and_partial_approval_are_explained_in_english(self):
        self.config['project']['title'] = ''
        self.config['project']['language'] = 'de'
        self.save()
        self.assertIn('the book has no title yet', self.run_view('edition-create', '--language', 'en').stdout)
        self.chapter(True)
        text = self.run_view('edition-create', '--language', 'en').stdout
        self.assertIn('Chapters approved so far: 0 of 1', text)
        self.assertIn('only approved chapters are included', text)
        self.config['project']['language'] = 'en'
        self.save()
        self.assertIn('Neue Auflage erzeugen', self.run_view('edition-create', '--language', 'de', '--text').stdout)

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

    def test_project_settings_are_english_and_preserve_values_and_approval_rules(self):
        self.config['workflow']['fact_checking_default'] = 'requested'
        self.config['changes'] = {'auto_merge': True}
        self.config['typesetting'] = {'font_size': 11.5}
        self.save()
        before = (self.base / 'ghostwriter.yml').read_bytes()
        text = self.run_view('project-settings', '--text', '--language', 'en').stdout
        self.assertIn('Project settings', text)
        self.assertIn('changes require explicit confirmation', text)
        self.assertIn('| Writing approval per section | required |', text)
        self.assertIn('| Fact check | requested |', text)
        self.assertIn('| Font size | 11.5 pt |', text)
        self.assertIn('| Apply changes immediately | yes |', text)
        self.assertNotIn('Projekteinstellungen', text)
        self.assertNotIn('Mögliche Werte', text)
        self.assertEqual(before, (self.base / 'ghostwriter.yml').read_bytes())
        self.assertIn('Projektdaten', self.run_view('project-edit', '--text', '--language', 'de').stdout)

    def test_all_template_preview_keeps_raw_project_settings(self):
        before = (self.base / 'ghostwriter.yml').read_bytes()
        text = self.run_view('project-settings', '--language', 'en', '--ui-ref', 'a' * 40).stdout
        self.assertIn('GW.render("projekteinstellungen",', text)
        self.assertIn('"LANGUAGE":"en"', text)
        self.assertEqual(before, (self.base / 'ghostwriter.yml').read_bytes())

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

    def test_project_form_preserves_values_without_saving(self):
        self.config['project']['description'] = 'Beschreibung mit Kapitel | Wortlaut.'
        self.config['project']['author'] = 'Deutscher Autor'
        self.save()
        before = (self.base / 'ghostwriter.yml').read_bytes()
        text = self.run_view('project-edit', '--language', 'en').stdout
        self.assertIn('Edit project details', text)
        self.assertIn('Title (required)', text)
        self.assertIn('Deutscher Autor', text)
        self.assertIn(r'Beschreibung mit Kapitel \| Wortlaut.', text)
        self.assertIn('`X` cancels', text)
        self.assertEqual((self.base / 'ghostwriter.yml').read_bytes(), before)

    def test_chapter_form_positions_and_edit_fields(self):
        self.chapter(True)
        create = self.run_view('chapter-create', '--language', 'en').stdout
        self.assertIn('`0` At the beginning', create)
        self.assertIn('`1` At the end (after chapter 1 “Kapitel Beschreibung”) *(default)*', create)
        edit = self.run_view('chapter-edit', '1', '--language', 'en').stdout
        self.assertIn('Edit chapter 1', edit)
        self.assertIn('Deutsches Ziel.', edit)
        self.assertIn('Deutsche Kurzbeschreibung.', edit)
        self.assertIn('Subtitle', edit)

    def test_section_form_preserves_fact_check_codes_and_positions(self):
        self.chapter(True)
        self.config['workflow']['fact_checking_default'] = 'disabled'
        self.save()
        before = (self.base / 'ghostwriter.yml').read_bytes()
        text = self.run_view('section-create', '1', '--language', 'en').stdout
        self.assertIn('New section in chapter 1', text)
        self.assertIn('| Fact check | off |', text)
        self.assertIn('`1` At the end (after 1.1 “Beschreibung Kapitel”) *(default)*', text)
        html = self.run_view('section-create', '1', '--language', 'en', '--ui-ref', 'a' * 40).stdout
        data = json.loads(re.search(r'GW.render\("abschnitt-anlegen",(.*?)\)</script>', html).group(1))
        self.assertEqual(data['FACT_CHECK_DEFAULT'], 'disabled')
        self.assertEqual(data['CHAPTER_ID'], 'c1')
        self.assertEqual(data['POSITIONS'][1]['POSITION_SELECTED'], 'selected')
        self.assertEqual((self.base / 'ghostwriter.yml').read_bytes(), before)

    def test_new_book_form_keeps_draft_author_series_and_taken_names(self):
        library = {'books': [{'branch': 'buch/test', 'slug': 'test', 'title': 'Buch', 'title_short': 'TEST', 'author': 'Bestehender Autor', 'status': 'ready', 'updated_at': '2026-11-01'}],
                   'series': [{'id': 'ser-test', 'title': 'Deutsche Serie', 'volumes': ['buch/test']}]}
        (self.base / 'library.json').write_text(json.dumps(library))
        draft = {'working_title': 'Neuer deutscher Titel', 'title_short': 'NEU', 'series_id': 'ser-test'}
        before = sorted(str(path.relative_to(self.base)) for path in self.base.rglob('*'))
        text = self.run_view('book-create', '--language', 'en', '--draft', json.dumps(draft)).stdout
        self.assertIn('Working title (required)', text)
        self.assertIn('Neuer deutscher Titel', text)
        self.assertIn('Bestehender Autor', text)
        self.assertIn('Volume 2 of series “Deutsche Serie”', text)
        self.assertIn('Already in use: `test` (buch/test)', text)
        self.assertEqual(sorted(str(path.relative_to(self.base)) for path in self.base.rglob('*')), before)

    def test_empty_chapter_and_section_positions_are_zero_based(self):
        create = self.run_view('chapter-create', '--language', 'en').stdout
        self.assertIn('`0` As the first chapter *(default)*', create)
        self.chapter(True)
        self.config['structure']['chapters'][0]['sections'] = []
        self.save()
        section = self.run_view('section-create', '1', '--language', 'en').stdout
        self.assertIn('`0` As the first section *(default)*', section)

    def test_shared_resource_contract(self):
        self.assertEqual(render_view_en.validate_resources(), [])

    def preview(self, *args, language='en'):
        text = self.run_view(*args, '--language', language, '--ui-ref', 'a' * 40, '--head-sha', 'b' * 40).stdout
        return json.loads(re.search(r'GW.render\("[^"\n]+",(.*?)\)</script>', text).group(1))

    def test_approval_checks_and_confirmation_are_identical_across_languages(self):
        section = self.chapter(False)
        for manuscript, writing, approved, revoke in [
                ('Noch nicht begonnen.', False, False, False),
                ('Original [QUELLE PRÜFEN].', True, False, False),
                ('Originaltext.', True, True, False),
                ('Originaltext.', True, True, True),
                ('Originaltext.', False, False, True)]:
            state = 'approved' if approved else 'writing'
            section.write_text('---\nid: s1\nstatus: ' + state + '\napprovals:\n  writing: ' + str(writing).lower()
                               + '\n  section: ' + str(approved).lower() + '\nfact_check: requested\n---\n\n## Manuskript\n\n' + manuscript + '\n')
            before = section.read_bytes()
            args = ['approval-section', '1.1'] + (['--revoke'] if revoke else [])
            de, en = self.preview(*args, language='de'), self.preview(*args)
            for key in ['APPROVAL_KIND', 'APPROVAL_REVOKE', 'TARGET_ID', 'HEAD_SHORT', 'HEAD_SHA']:
                self.assertEqual(de[key], en[key], key)
            self.assertEqual([c['CHECK_STATE'] for c in de['CHECKS']], [c['CHECK_STATE'] for c in en['CHECKS']])
            self.assertIn('Beschreibung Kapitel', en['TARGET_LABEL'])
            text = self.run_view(*args, '--language', 'en').stdout
            blocked = any(c['CHECK_STATE'] == 'block' for c in en['CHECKS'])
            self.assertEqual('`OK` confirms' in text, not blocked)
            self.assertNotIn('freigegeben', text)
            self.assertEqual(section.read_bytes(), before)
        self.assertIn('Withdraw section approval', text)

    def test_writing_and_chapter_approvals_explain_missing_prerequisites_in_english(self):
        section = self.chapter(True)
        section.write_text(section.read_text().replace('status: writing', 'status: writing\napprovals: {writing: false, section: false}'))
        text = self.run_view('approval-writing', '1.1', '--language', 'en').stdout
        self.assertIn('Grant writing permission', text)
        self.assertIn('No research run yet', text)
        self.assertIn('No brainstorming run yet', text)
        for kind, count in [('research', 2), ('brainstorming', 1)]:
            folder = self.base / 'chapters/01' / kind / 's1'
            folder.mkdir(parents=True)
            for index in range(count):
                (folder / f'{index}.md').write_text('Laufdaten bleiben unverändert.')
        text = self.run_view('approval-writing', '1.1', '--language', 'en').stdout
        self.assertIn('2 research runs available', text)
        self.assertIn('1 brainstorming run available', text)
        chapter = self.run_view('approval-chapter', '1', '--language', 'en').stdout
        self.assertIn('Approve chapter', chapter)
        self.assertIn('in progress', chapter)
        self.assertIn('Complete the ⛔ items', chapter)
        self.assertNotIn('`OK` confirms', chapter)

    def test_matter_approval_preserves_user_title_and_blocks_empty_text(self):
        matter = self.base / 'back-matter' / 'glossar.md'
        matter.parent.mkdir()
        matter.write_text('---\nid: mat-glossary\nstatus: writing\napprovals:\n  writing: true\n  section: false\n---\n\n## Manuskript\n\nNoch nicht begonnen.\n')
        self.config['structure']['back_matter'] = [{'id': 'mat-glossary', 'kind': 'glossary', 'title': 'Eigenes Glossar', 'path': 'back-matter/glossar.md', 'status': 'writing'}]
        self.save()
        text = self.run_view('approval-matter', 'mat-glossary', '--language', 'en').stdout
        self.assertIn('Eigenes Glossar (Back matter)', text)
        self.assertIn('There is no text yet', text)
        self.assertNotIn('`OK` confirms', text)
        matter.write_text(matter.read_text().replace('Noch nicht begonnen.', '- Wort: Erklärung.'))
        text = self.run_view('approval-matter', 'mat-glossary', '--language', 'en').stdout
        self.assertIn('1 term, with no duplicates', text)
        self.assertIn('`OK` confirms', text)

    def test_changes_empty_and_populated_preserve_commit_messages(self):
        self.assertEqual(self.run_view('changes-merge', '--language', 'en').stdout, 'There are no pending changes.\n')
        data = {'pull_request': 3, 'book_branch': 'buch/original', 'work_branch': 'arbeit/original',
                'commits': [{'sha': 'b' * 40, 'message': 'Änderung {{p_a}} – Original', 'date': '2026-11-06T10:20:00Z'}]}
        changes = self.base / 'changes.json'
        changes.write_text(json.dumps(data))
        text = self.run_view('changes-merge', '--changes', str(changes), '--language', 'en').stdout
        self.assertIn('1 change', text)
        self.assertIn('Änderung {{p_a}} – Original', text)
        self.assertIn('2026-11-06, 10:20', text)
        self.assertIn('`OK` applies', text)
        self.assertIn('`buch/original`', text)
        self.assertEqual(json.loads(changes.read_text()), data)

    def test_reorder_views_preserve_ids_numbers_and_titles(self):
        self.chapter(True)
        chapter = self.run_view('chapter-reorder', '--language', 'en').stdout
        section = self.run_view('section-reorder', '1', '--language', 'en').stdout
        self.assertIn('Change chapter order', chapter)
        self.assertIn('Kapitel Beschreibung', chapter)
        self.assertIn('Change section order in chapter 1', section)
        self.assertIn('`1.1`', section)
        de, en = self.preview('section-reorder', '1', language='de'), self.preview('section-reorder', '1')
        self.assertEqual(de['ITEMS'], en['ITEMS'])
        self.assertEqual(de['CHAPTER_ID'], en['CHAPTER_ID'])
        self.assertEqual(de['REORDER_KIND'], en['REORDER_KIND'])

    def test_series_form_uses_english_labels_and_preserves_draft(self):
        draft = {'title': 'Deutsche Reihe {{p_a}}', 'subtitle': 'Untertitel', 'kind': 'standalone',
                 'description': 'Beschreibung | bleibt.', 'issn': '1234-5679', 'also_in_series': False,
                 'error': 'Originaldiagnose'}
        before = (self.base / 'ghostwriter.yml').read_bytes()
        text = self.run_view('series-edit', '--draft', json.dumps(draft), '--language', 'en').stdout
        self.assertIn('New series', text)
        self.assertIn('Deutsche Reihe {{p_a}}', text)
        self.assertIn('standalone volumes', text)
        self.assertIn('Originaldiagnose', text)
        self.assertIn('Field: new value', text)
        self.assertIn(r'Beschreibung \| bleibt.', text)
        self.assertEqual((self.base / 'ghostwriter.yml').read_bytes(), before)

    def test_image_approval_checks_missing_file_and_preserves_caption(self):
        self.chapter(True)
        folder = self.base / 'chapters/01/images/s1'
        folder.mkdir(parents=True)
        meta = {'id': 'img-test', 'file': 'img-test.png', 'caption': 'Bildtitel {{p_a}}',
                'status': 'draft', 'width_px': 1800, 'alt': 'Alternativtext', 'ai_generated': True}
        (folder / 'img-test.yml').write_text(yaml.safe_dump(meta))
        text = self.run_view('approval-image', 'img-test', '--language', 'en').stdout
        self.assertIn('The image file is missing', text)
        self.assertNotIn('`OK` confirms', text)
        (folder / 'img-test.png').write_bytes(b'fixture')
        text = self.run_view('approval-image', 'img-test', '--language', 'en').stdout
        self.assertIn('Image “Bildtitel {{p_a}}”', text)
        self.assertIn('AI-generated', text)
        self.assertIn('`OK` confirms', text)
        self.assertEqual(yaml.safe_load((folder / 'img-test.yml').read_text()), meta)


if __name__ == '__main__':
    unittest.main()
