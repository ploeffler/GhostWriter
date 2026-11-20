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

    def test_whole_chapter_with_all_sections_unsplit(self):
        # analyze.blocks liefert seit #239 Abschnitte und Teilstücke; der Auftrag bleibt ein Kapitel.
        long_text = ('Ein langer Satz für die Prüfung. ' * 600).strip()
        _, config = ca.load(self.book)
        first = config['structure']['chapters'][0]['sections'][0]
        path = self.book / first['path']
        before = path.read_text(encoding='utf-8').split('\n## Manuskript\n', 1)[0]
        path.write_text(before + '\n## Manuskript\n\n' + long_text + '\n', encoding='utf-8')
        request = self.prepare()
        texts = request['snapshot']['texts']
        self.assertEqual(sorted(texts, key=lambda k: int(k.split('.')[1])),
                         [f'1.{i}' for i in range(1, 10)])
        self.assertIn(long_text, texts['1.1'])
        self.assertTrue(request['snapshot']['title'].startswith('Kapitel 1: '))
        self.assertEqual(request['snapshot']['chapter_id'], 'ch-01-endlich-eine-erklaerung')

    def test_all_kinds_prepare_without_key_or_network_and_only_one_chapter(self):
        for kind in sorted(ca.KINDS - {'chronology'}):   # Chronologie liest Unterlagen statt Kapiteltext (test_chronology_analysis)
            self.request = self.root / (kind + '.json')
            request = self.prepare(kind)
            self.assertTrue(all(key.startswith('1.') for key in request['snapshot']['texts']))
            self.assertNotIn('2.1', request['snapshot']['texts'])
            self.assertEqual(ca.prepare(self.book, kind, 1, 'a' * 40, self.request), request)
        self.assertFalse((self.book / 'costs/project.yml').exists())

    def test_ai_pattern_rules_in_blurb_and_language_prompts(self):
        """#305: Klappentext und Sprachprüfung bekommen die Regeln gegen KI-typische Muster, andere Arten nicht."""
        for kind in ('blurb', 'language', 'image_ideas'):
            self.request = self.root / (kind + '.json')
            prompt = self.prepare(kind)['prompt']
            self.assertEqual('KI-typische Muster vermeiden' in prompt, kind != 'image_ideas', kind)
            self.assertEqual('Ankündigender Schlusssatz' in prompt, kind != 'image_ideas', kind)

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


class ChatReturnRunTest(ChatAnalysisTest):
    """#353: geprüfte Chat-Rückgaben lassen sich wie Hintergrundläufe ansehen und übernehmen."""

    def timeline_return(self):
        request = self.prepare('timeline')
        texts = request['snapshot']['texts']
        def plain(t):   # eine Zeile ohne Auszeichnung, damit das Zitat sicher wörtlich passt
            import re
            return re.search(r'(?:[A-Za-zÄÖÜäöüß]+ ){5}[A-Za-zÄÖÜäöüß]+', t).group(0)
        events = [{'where': w, 'when': 'Sommer 1989' if i == 0 else '', 'what': f'Ereignis {i + 1}',
                   'evidence': [{'where': w, 'quote': plain(t)}]} for i, (w, t) in enumerate(list(texts.items())[:3])]
        events.append({'where': '1.1', 'what': 'Ohne Beleg', 'evidence': [{'where': '1.1', 'quote': 'gibt es nicht im Text'}]})
        self.answer(request, {'events': events})
        return ca.accept(self.book, self.request, self.response)

    def view(self, *args):
        import subprocess
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.book), *args, '--repo', 'o/r'],
                           capture_output=True, text=True)
        return r

    def test_timeline_return_shows_events_and_applies(self):
        path, result = self.timeline_return()
        self.assertEqual(len(result['verified']), 3)
        run = ca.analyze.chat_run_of(self.book, result)
        self.assertEqual(run, 'run-001')
        data = json.loads((self.book / 'analysis/timeline/run-001.json').read_text(encoding='utf-8'))
        self.assertEqual((data['scope'], data['source'], [e['n'] for e in data['items']], data['issues']),
                         ('1', 'chat', [1, 2, 3], []))
        # wiederholtes accept bzw. register: derselbe Lauf, kein zweiter
        self.assertEqual(ca.accept(self.book, self.request, self.response)[0], path)
        self.assertEqual(ca.register(self.book, path), ('timeline', 'run-001'))
        self.assertFalse((self.book / 'analysis/timeline/run-002.json').exists())
        # Ansicht direkt aus der Chat-Rückgabe und aus dem Lauf, Umfang Kapitel 1
        for draft in (str(path.relative_to(self.book)), 'analysis/timeline/run-001.json'):
            out = self.view('analysis-suggest', '--draft', draft, '--text')
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn('3 Ereignisse', out.stdout)
            self.assertIn('Kapitel 1', out.stdout)
            self.assertIn('Chat-Analyse 001', out.stdout)
            self.assertIn('Sommer 1989', out.stdout)
        # Projektübersicht nennt den Lauf wie einen Hintergrundlauf
        self.assertIn('Zeitleiste', self.view('project', '--text').stdout)
        changed = ca.analyze.apply(self.book, 'run-001', 'timeline', [{'index': 0}, {'index': 2}])
        self.assertTrue(changed)
        import yaml
        tl = yaml.safe_load((self.book / 'story/timeline.yml').read_text(encoding='utf-8'))
        self.assertEqual([e['what'] for e in tl['events']], ['Ereignis 1', 'Ereignis 3'])
        self.assertIsNone(ca.analyze.latest(self.book, 'timeline'))   # erledigt

    def test_older_return_needs_register_and_other_kinds(self):
        path, result = self.timeline_return()
        for f in (self.book / 'analysis/timeline').glob('run-001.*'):
            f.unlink()   # Rückgabe von vor #353: nur analysis/chat-returns/
        out = self.view('analysis-suggest', '--draft', str(path.relative_to(self.book)), '--text')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('register', out.stderr)
        self.assertEqual(ca.register(self.book, path), ('timeline', 'run-001'))
        # Kurzbeschreibungen: je Abschnitt zugeordnet wie im Hintergrundlauf
        self.request = self.root / 'summaries.json'
        request = self.prepare('summaries')
        where, text = next(iter(request['snapshot']['texts'].items()))
        self.answer(request, {'sections': [{'where': where, 'short': 'Kurz und knapp.', 'goal': '',
                                            'evidence': [{'field': 'short', 'where': where, 'quote': ' '.join(text.split()[:6])}]}]})
        _, res = ca.accept(self.book, self.request, self.response)
        run = ca.analyze.chat_run_of(self.book, res)
        data = json.loads((self.book / 'analysis/summaries' / f'{run}.json').read_text(encoding='utf-8'))
        self.assertEqual([i['level'] for i in data['items']], ['chapter', 'section'])
        # Arten ohne Lauf (z. B. Bildideen) bleiben nur Chat-Rückgabe
        self.request = self.root / 'ideas.json'
        req = self.prepare('image_ideas')
        self.answer(req, {'items': [{'text': 'Bildidee', 'evidence': [self.evidence(req)]}]})
        p2, _ = ca.accept(self.book, self.request, self.response)
        self.assertEqual(ca.register(self.book, p2), ('image_ideas', None))
