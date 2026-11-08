"""Datei-/Kopierweg ohne Anbieter, Basisprüfung und reine Vorschläge (D07/D16)."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import chat_analysis as ca


class ChatAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.book = self.root / 'book'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.book)
        self.request = self.root / 'request.json'
        self.response = self.root / 'response.json'

    def prepare(self, kind='image_ideas', **kw):
        with patch.object(ca.analyze, 'call_llm', side_effect=AssertionError('Kein Anbieteraufruf')), \
             patch.object(ca.analyze, 'pick_provider', side_effect=AssertionError('Kein Schlüssel nötig')):
            return ca.prepare(self.book, kind, 1, 'a' * 40, self.request, **kw)

    def answer(self, request, answer):
        self.response.write_text(ca.canonical({'request_id': request['request_id'],
                                             'kind': request['kind'], 'answer': answer}))

    def evidence(self, request):
        where, text = next(iter(request['snapshot']['texts'].items()))
        return {'where': where, 'quote': text[:40]}

    def test_all_kinds_prepare_without_key_or_network_and_only_one_chapter(self):
        for kind in sorted(ca.KINDS):
            self.request = self.root / (kind + '.json')
            request = self.prepare(kind)
            self.assertTrue(all(key.startswith('1.') for key in request['snapshot']['texts']))
            self.assertNotIn('2.1', request['snapshot']['texts'])
            self.assertEqual(ca.prepare(self.book, kind, 1, 'a' * 40, self.request), request)
        self.assertFalse((self.book / 'costs/project.yml').exists())

    def test_return_is_idempotent_proposal_and_does_not_change_manuscript(self):
        request = self.prepare()
        before = {p.relative_to(self.book): p.read_bytes() for p in (self.book / 'chapters').rglob('*.md')}
        self.answer(request, {'items': [{'text': 'Bildidee', 'evidence': [self.evidence(request)]}]})
        first, result = ca.accept(self.book, self.request, self.response)
        second, _ = ca.accept(self.book, self.request, self.response)
        self.assertEqual(first, second)
        self.assertEqual(result['status'], 'proposal')
        self.assertEqual(len(result['verified']), 1)
        self.assertEqual(before, {p.relative_to(self.book): p.read_bytes() for p in (self.book / 'chapters').rglob('*.md')})
        self.assertFalse((self.book / 'costs/project.yml').exists())
        self.assertFalse((self.book / 'approvals.yml').exists())

    def test_wrong_section_quote_and_missing_evidence_are_dropped(self):
        request = self.prepare()
        quote = self.evidence(request)
        self.answer(request, {'items': [
            {'text': 'Falsche Stelle', 'evidence': [{**quote, 'where': '9.9'}]},
            {'text': 'Keine Quelle', 'evidence': []},
            {'text': 'Erfunden', 'evidence': [{**quote, 'quote': 'Nicht vorhandenes Originalzitat'}]}]})
        _, result = ca.accept(self.book, self.request, self.response)
        self.assertEqual(result['verified'], [])
        self.assertGreater(result['dropped_without_evidence'], 0)

    def test_changed_profile_or_manuscript_rejects_before_saving(self):
        request = self.prepare()
        self.answer(request, {'items': []})
        path = self.book / 'ghostwriter.yml'
        path.write_text(path.read_text().replace('language: de', 'language: en'))
        with self.assertRaisesRegex(ValueError, 'inzwischen geändert'):
            ca.accept(self.book, self.request, self.response)
        self.assertFalse((self.book / 'analysis/chat-returns').exists())

    def test_wrong_request_id_and_changed_request_are_rejected(self):
        request = self.prepare()
        self.answer({**request, 'request_id': 'b' * 64}, {'items': []})
        with self.assertRaisesRegex(ValueError, 'passt nicht'):
            ca.accept(self.book, self.request, self.response)
        request['prompt'] = 'Verändert'
        self.request.write_text(ca.canonical(request))
        with self.assertRaisesRegex(ValueError, 'Auftragsdatei wurde verändert'):
            ca.accept(self.book, self.request, self.response)

    def test_series_reference_is_explicit_and_part_of_source_check(self):
        folder = self.book / 'series'
        folder.mkdir()
        reference = folder / 'test.md'
        reference.write_text('In dieser Serie ist Opi ein alter Mann.')
        request = self.prepare('series', references=['series/test.md'])
        self.assertIn('reference:series/test.md', request['snapshot']['texts'])
        self.answer(request, {'items': [{'text': 'Vergleichsvorschlag', 'evidence': [self.evidence(request)]}]})
        _, result = ca.accept(self.book, self.request, self.response)
        self.assertEqual(result['warnings'], [])
        reference.write_text('Geänderte Serienbasis')
        with self.assertRaisesRegex(ValueError, 'inzwischen geändert'):
            ca.accept(self.book, self.request, self.response)

    def test_missing_series_reference_is_never_claimed_as_compared(self):
        request = self.prepare('series')
        self.answer(request, {'items': []})
        _, result = ca.accept(self.book, self.request, self.response)
        self.assertTrue(result['warnings'])

    def test_changed_request_file_and_invalid_scope_are_not_overwritten(self):
        request = self.prepare()
        original = self.request.read_bytes()
        with self.assertRaisesRegex(ValueError, 'nicht überschrieben'):
            ca.prepare(self.book, 'blurb', 1, 'a' * 40, self.request)
        self.assertEqual(self.request.read_bytes(), original)
        with self.assertRaises(ValueError):
            ca.prepare(self.book, 'blurb', 0, 'a' * 40, self.root / 'invalid.json')

    def test_rule_change_rejects_return_and_preserves_input(self):
        request = self.prepare()
        self.answer(request, {'items': []})
        before = self.response.read_bytes()
        (self.book / 'workflow.yml').write_text('version: changed')
        with self.assertRaisesRegex(ValueError, 'inzwischen geändert'):
            ca.accept(self.book, self.request, self.response)
        self.assertEqual(self.response.read_bytes(), before)
        self.assertFalse((self.book / 'analysis/chat-returns').exists())

    def test_original_manuscript_change_rejects_return(self):
        request = self.prepare()
        self.answer(request, {'items': []})
        _, config = ca.load(self.book)
        path = self.book / config['structure']['chapters'][0]['sections'][0]['path']
        path.write_text(path.read_text().replace('Der Brief lag dort sechs Monate.', 'Ein neuer Textstand.'))
        with self.assertRaisesRegex(ValueError, 'inzwischen geändert'):
            ca.accept(self.book, self.request, self.response)


if __name__ == '__main__':
    unittest.main()
