"""Englische Dialoge: Inhalte und Freigaben bleiben Daten, Vorschauen schreiben nichts."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import characters
import import_book
import matter
import series
import render_view


class RemainingViewsEnglishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'book'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        self.config_path = self.base / 'ghostwriter.yml'
        config = yaml.safe_load(self.config_path.read_text())
        config['project']['language'] = 'de'
        config['limits'] = {'ai_budget_monthly': 12.5}
        self.config_path.write_text(yaml.safe_dump(config, allow_unicode=True))
        self.library = {'books': [], 'series': []}
        self.save_library()

    def save_library(self):
        (self.base / 'library.json').write_text(json.dumps(self.library))

    def run_view(self, *args, language='en', widget=False):
        command = [sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base),
                   *args, '--repo', 'owner/book', '--language', language]
        if widget:
            command += ['--ui-ref', 'a' * 40]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        if widget:
            return json.loads(re.search(r'GW.render\("[^"]+",(.*?)\)</script>', result.stdout).group(1))
        self.assertNotIn('<script', result.stdout)
        self.assertNotIn('Was möchtest du tun?', result.stdout)
        return result.stdout

    def snapshot(self):
        return {str(p.relative_to(self.base)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.base.rglob('*') if p.is_file()}

    def test_localized_fixed_tables_keep_the_german_source_contract(self):
        names = ('OUTPUT_LABELS', 'FIXED_TEXT', 'FC_TEXT', 'FIXED_RULES', 'OUTPUT_GROUPS', 'PUBLICATION_LABELS',
                 'TEMPLATE_DE', 'ROLE_DE', 'SOURCE_DE', 'TERM_STATE_DE', 'WEB_TEXT', 'ACCESS_TEXT', 'KEEP_DE',
                 'FIELD_DE', 'MARKER_LABEL', 'MATTER_HINTS')
        with patch.dict(render_view.UI, {'language': 'de'}):
            for name in names:
                with self.subTest(name=name):
                    self.assertEqual(render_view.view_labels(name), getattr(render_view, name))
            self.assertEqual(render_view.view_role_info(), render_view.ROLE_INFO)
            catalog = yaml.safe_load((ROOT / 'providers.yml').read_text())
            self.assertEqual(render_view.view_provider_catalog(catalog), catalog)

    def test_settings_output_providers_and_disclosure_are_read_only(self):
        before = self.snapshot()
        for view, expected in [('project-settings', 'Fixed rules'), ('output', 'Output options'),
                               ('providers-edit', 'AI services'), ('ai-disclosure', 'AI disclosure')]:
            with self.subTest(view=view):
                text = self.run_view(view)
                self.assertIn(expected, text)
                self.assertNotIn('Schriftgröße', text)
                self.assertNotIn('keine', text)
                self.run_view(view, widget=True)
        settings = self.run_view('project-settings')
        self.assertIn('AI budget 100% remaining (0.00 of 12.50 € used)', settings)
        self.assertIn('explicit confirmation', settings)
        self.assertEqual(before, self.snapshot())

    def test_all_builtin_choices_preserve_values_and_selections(self):
        before = self.snapshot()
        canonical = yaml.safe_load((ROOT / 'templates/wizard-choices.yml').read_text())
        for step in ('4', '5', '6', '12', '13', '14'):
            with self.subTest(step=step):
                text = self.run_view('choice', 'wizard.' + step)
                self.assertIn('New book · Step ' + step + ' of 14', text)
                en = self.run_view('choice', 'wizard.' + step, widget=True)
                de = self.run_view('choice', 'wizard.' + step, language='de', widget=True)
                spec = canonical['steps']['wizard.' + step]
                self.assertEqual(de['TITLE'], spec['title'].format(step=step, steps=canonical['steps_total']))
                self.assertEqual([row['Q_TEXT'] for row in de['QUESTIONS']], [q['text'] for q in spec['questions']])
                self.assertEqual([row['OPT_LABEL'] for row in de['OPTIONS']],
                                 [option['label'] for q in spec['questions'] for option in q['options']])
                for collection in ('QUESTIONS', 'OPTIONS'):
                    fields = ('Q_INDEX', 'Q_KEY', 'Q_MULTI') if collection == 'QUESTIONS' else ('OPT_Q', 'OPT_VALUE', 'OPT_RECOMMENDED', 'OPT_SELECTED')
                    self.assertEqual([{k: row[k] for k in fields} for row in en[collection]],
                                     [{k: row[k] for k in fields} for row in de[collection]])
        spec = {'title': 'Eigene Frage {title}', 'questions': [{'key': 'x', 'text': 'Unveränderter Fragetext',
                  'options': [{'value': 'ja', 'label': 'Ja als Nutztext'}, {'value': 'nein', 'label': 'Nein als Nutztext'}]}]}
        text = self.run_view('choice', '--spec', json.dumps(spec))
        self.assertIn('Unveränderter Fragetext', text)
        self.assertIn('Ja als Nutztext', text)
        self.assertEqual(before, self.snapshot())

    def test_matter_characters_images_and_research_preserve_book_text(self):
        characters.add(self.base, 'Figur {name}', 'supporting')
        part = matter.add(self.base, 'foreword')
        before = self.snapshot()
        self.assertIn('Front and back matter', self.run_view('matter'))
        self.assertIn('Writing approval', self.run_view('matter', 'foreword'))
        self.assertIn('Figur {name}', self.run_view('characters'))
        text = self.run_view('characters', 'Figur {name}')
        self.assertIn('Supporting character', text)
        self.assertIn('Age', text)
        self.assertIn('Images', self.run_view('images', '1.1'))
        self.assertIn('Chapter research', self.run_view('chapter-research', '1'))
        preview = self.run_view('chapter-research', '1', widget=True)
        self.assertEqual(preview['RESEARCH_TASK'], 'goal' if not preview['CHAPTER_GOAL'] else '')
        self.assertEqual(before, self.snapshot())

    def test_series_omnibus_and_data_keep_names_and_unknown_state(self):
        entry = {'id': 'ser-test', 'title': 'Reihe {series}', 'kind': 'continuous', 'volumes': []}
        series.save(self.base, entry)
        self.library['series'] = [entry]
        self.save_library()
        before = self.snapshot()
        self.assertIn('Series “Reihe {series}”', self.run_view('series', 'ser-test'))
        self.assertIn('Omnibus', self.run_view('omnibus-edit', 'ser-test'))
        data = self.run_view('data')
        self.assertIn('unknown (without a GitHub query)', data)
        self.assertNotIn('unbekannt', data)
        self.assertEqual(before, self.snapshot())

    def test_all_analysis_panels_show_english_controls_without_writing(self):
        headings = {'characters': 'Characters from the text', 'summaries': 'Summary and goal',
                    'style': 'Style profile', 'places': 'Places from the text', 'timeline': 'Timeline',
                    'continuity': 'Possible contradictions', 'language': 'Language notes'}
        for kind, heading in headings.items():
            with self.subTest(kind=kind):
                draft = self.base / ('draft-' + kind + '.json')
                draft.write_text(json.dumps({'kind': kind, 'run': 'run-001', 'scope': 'book', 'items': []}))
                before = self.snapshot()
                text = self.run_view('analysis-suggest', '--draft', str(draft))
                self.assertIn(heading, text)
                self.assertIn('discard', text)
                self.assertNotIn('Hintergrundlauf', text)
                self.run_view('analysis-suggest', '--draft', str(draft), widget=True)
                self.assertEqual(before, self.snapshot())

    def test_disclosure_keeps_confirmed_wording_and_analysis_keeps_evidence(self):
        config = yaml.safe_load(self.config_path.read_text())
        wording = 'Mein unveränderter Wortlaut {mode}.'
        config['ai_disclosure'] = {'mode': 'custom', 'placement': 'imprint', 'text': wording}
        self.config_path.write_text(yaml.safe_dump(config, allow_unicode=True))
        before = self.snapshot()
        text = self.run_view('ai-disclosure')
        self.assertIn(wording, text)
        self.assertIn('confirmed', text)
        widget = self.run_view('ai-disclosure', widget=True)
        self.assertEqual(widget['AI_TEXT'], wording)
        self.assertEqual(widget['AI_MODE'], 'custom')
        self.assertEqual(before, self.snapshot())
        quote = 'Unveränderte Fundstelle {quote}.'
        for kind, item, label in [
            ('language', {'kind': 'long_sentence', 'where': '1.1', 'text': 'Hinweis bleibt erhalten.', 'quote': quote}, 'Long sentence'),
            ('style', {'field': 'tense', 'value': 'Präteritum {tense}', 'evidence': [{'where': '1.1', 'quote': quote}]}, 'Tense'),
            ('characters', {'name': 'Neue Figur {name}', 'role': 'supporting', 'evidence': [{'where': '1.1', 'quote': quote}]}, 'Supporting character')]:
            with self.subTest(kind=kind):
                draft = self.base / ('populated-' + kind + '.json')
                draft.write_text(json.dumps({'kind': kind, 'scope': 'book', 'items': [item]}))
                before = self.snapshot()
                text = self.run_view('analysis-suggest', '--draft', str(draft))
                self.assertIn(label, text)
                if kind != 'characters':
                    self.assertIn(quote if kind == 'language' else 'Präteritum {tense}', text)
                payload = self.run_view('analysis-suggest', '--draft', str(draft), widget=True)
                self.assertIn(quote, json.dumps(payload, ensure_ascii=False))
                self.assertEqual(before, self.snapshot())

    def test_import_preserves_titles_quotes_and_requires_confirmation(self):
        proposal = import_book.detect('# Kapitel 1: Originaltitel\n\nOriginaltext bleibt unverändert.\n', fmt='md')
        import_book.save_proposal(self.base, proposal)
        outline = {'status': 'open', 'run': 'outline-001', 'created_at': '2026-11-06', 'paragraphs': 1, 'dropped': 0,
                   'chapters': [{'title': 'Originaltitel {chapter}', 'start': 1, 'words': 3, 'quote': 'Originaltext bleibt unverändert.',
                                 'sections': [{'title': 'Abschnittstitel', 'start': 1, 'words': 3, 'quote': 'Originaltext bleibt unverändert.'}]}]}
        import_book.outline_path(self.base).write_text(json.dumps(outline))
        before = self.snapshot()
        self.assertIn('Create book as shown', self.run_view('import-preview'))
        text = self.run_view('import-outline')
        self.assertIn('Originaltitel {chapter}', text)
        self.assertIn('Originaltext bleibt unverändert.', text)
        self.assertIn('requires confirmation', text)
        self.assertEqual(before, self.snapshot())
