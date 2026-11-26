"""#462: Recherche mit Internet über den eingestellten Anbieter – Auswahl, Antworten, Ablage, Kosten, Action."""
import datetime
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import research  # noqa: E402

NOW = datetime.datetime(2026, 11, 21, 20, 0, tzinfo=datetime.timezone.utc)
SECTION = """---
id: sec-01-01-start
number: "1.1"
title: Start
status: planned
approvals:
  writing: false
  section: false
---

# 1.1 Start

## Ziel des Abschnitts

Die Ankunft in Valletta 1957.

## Kurzbeschreibung

Schiff, Hafen, erste Eindrücke.

## Manuskript

Offen.
"""


def book(ai=None, section=SECTION):
    tmp = tempfile.TemporaryDirectory()
    base = Path(tmp.name)
    ch = base / 'chapters' / 'ch-01-anfang'
    (ch / 'sections').mkdir(parents=True)
    (ch / 'sections' / 'sec-01-01-start.md').write_text(section, encoding='utf-8')
    config = {'project': {'title': 'Malta', 'language': 'de'},
              'ai_providers': ai if ai is not None else {'available': ['google'], 'services': {
                  'google': {'access': 'api', 'api_key_secret': 'GEMINI_API_KEY'}}},
              'structure': {'chapters': [{'id': 'ch-01-anfang', 'title': 'Anfang', 'path': 'chapters/ch-01-anfang',
                                          'sections': [{'id': 'sec-01-01-start', 'title': 'Start',
                                                        'path': 'chapters/ch-01-anfang/sections/sec-01-01-start.md'}]}]}}
    (base / 'ghostwriter.yml').write_text(yaml.safe_dump(config, allow_unicode=True), encoding='utf-8')
    return tmp, base


GEMINI = {'responseId': 'r1', 'candidates': [{'content': {'parts': [{'text':
          'Kurz.\n\n## Fragestellung und Suchumfang\n\nHafen.\n\n## Rechercheergebnisse\n\nFakt.\n\n'
          '## Quellen\n\n- erfunden https://falsch.example\n\n## Widersprüche und Unsicherheiten\n\nKeine.\n\n'
          '## Offene Fragen\n\n-\n\n## Relevanz für den Abschnitt\n\nHoch.'}]},
          'groundingMetadata': {'webSearchQueries': ['valletta 1957', 'grand harbour'],
                                'groundingChunks': [{'web': {'uri': 'https://a.example/x', 'title': 'a.example'}},
                                                    {'web': {'uri': 'https://a.example/x', 'title': 'doppelt'}},
                                                    {'web': {'uri': 'https://b.example', 'title': 'B'}}]}}],
          'usageMetadata': {'promptTokenCount': 1000, 'candidatesTokenCount': 400, 'thoughtsTokenCount': 100}}
ANTHROPIC = {'id': 'msg_1', 'content': [
    {'type': 'server_tool_use', 'name': 'web_search'},
    {'type': 'web_search_tool_result', 'content': [{'type': 'web_search_result', 'url': 'https://c.example', 'title': 'C'}]},
    {'type': 'text', 'text': '## Rechercheergebnisse\n\nFakt', 'citations': [
        {'type': 'web_search_result_location', 'url': 'https://c.example', 'title': 'C'}]}],
    'usage': {'input_tokens': 2000, 'output_tokens': 500, 'server_tool_use': {'web_search_requests': 3}}}
OPENAI = {'id': 'resp_1', 'output': [{'type': 'web_search_call'}, {'type': 'message', 'content': [
    {'type': 'output_text', 'text': '## Rechercheergebnisse\n\nFakt',
     'annotations': [{'type': 'url_citation', 'url': 'https://d.example', 'title': 'D'}]}]}],
    'usage': {'input_tokens': 10, 'output_tokens': 5}}


class ResolveTest(unittest.TestCase):
    def test_first_available_api_provider(self):
        tmp, base = book()
        with tmp:
            c = research.resolve(base)
            self.assertEqual((c['provider'], c['secret'], c['model']), ('google', 'GEMINI_API_KEY', 'gemini-3.8-flash'))

    def test_research_role_wins_and_model_from_settings(self):
        tmp, base = book({'available': ['google', 'anthropic'], 'research': {'provider': 'anthropic', 'model': 'm1'},
                          'services': {'anthropic': {'access': 'api', 'api_key_secret': 'MY_ANTHROPIC_API_KEY'}}})
        with tmp:
            c = research.resolve(base)
            self.assertEqual((c['provider'], c['secret'], c['model']), ('anthropic', 'MY_ANTHROPIC_API_KEY', 'm1'))

    def test_image_model_of_service_is_not_used(self):
        tmp, base = book({'available': ['google'], 'services': {'google': {'access': 'api', 'model': 'gemini-2.5-flash-image'}}})
        with tmp:
            self.assertEqual(research.resolve(base)['model'], 'gemini-3.8-flash')

    def test_library_defaults(self):
        tmp, base = book({'available': [], 'research': {'provider': ''}})
        with tmp:
            d = base / 'defaults.yml'
            d.write_text(yaml.safe_dump({'ai_providers': {'available': ['openai'], 'services': {'openai': {'access': 'api'}}}}))
            c = research.resolve(base, d)
            self.assertEqual((c['provider'], c['from'], c['secret']), ('openai', 'bibliothek', 'OPENAI_API_KEY'))

    def test_messages(self):
        for ai, text in [({'available': [], 'default': {'provider': 'chat'}}, 'kein Anbieter'),
                         ({'research': {'provider': 'chat'}}, 'kein Anbieter'),
                         ({'research': {'provider': 'mistral'}}, 'noch nicht recherchieren'),
                         ({'research': {'provider': 'microsoft_copilot'}}, 'Chat-App'),
                         ({'research': {'provider': 'google'}, 'services': {'google': {'api_key_secret': 'GHOSTWRITER_UPDATE_TOKEN'}}},
                          'Ungültiger Secret-Name')]:
            tmp, base = book(ai)
            with tmp, self.subTest(ai=ai):
                with self.assertRaisesRegex(research.ResearchError, text):
                    research.resolve(base)


class RunTest(unittest.TestCase):
    def run_with(self, response, ai=None, **kw):
        tmp, base = book(ai)
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(research, 'post_json', return_value=response) as post, \
                mock.patch.object(research.pricing, 'fetch_url', side_effect=OSError('offline')), \
                mock.patch.dict(os.environ, {research.KEY_ENV: 'k-secret'}):   # #66: kein Netz im Test, Wechselkurs fehlt
            head = research.run(base, 'sec-01-01-start', now=NOW, **kw)
        return base, head, post

    def test_gemini_run_file_sources_cost_status(self):
        base, head, post = self.run_with(GEMINI, {'available': ['google'], 'services': {'google': {
            'access': 'api', 'price_input_per_mtok': 0.3, 'price_output_per_mtok': 2.5, 'price_per_1k_searches': 35}}})
        body = post.call_args[0][1]
        self.assertEqual(body['tools'], [{'google_search': {}}])
        self.assertEqual(post.call_args[0][2], {'x-goog-api-key': 'k-secret'})
        run = (base / head['path']).read_text(encoding='utf-8')
        meta = yaml.safe_load(run.split('---')[1])
        self.assertEqual((meta['provider'], meta['web_research'], meta['searches'], meta['sources']), ('google', True, 2, 2))
        self.assertNotIn('falsch.example', run)
        self.assertIn('- [a.example](https://a.example/x) – abgerufen am 2026-11-21', run)
        self.assertLess(run.index('## Quellen'), run.index('## Widersprüche und Unsicherheiten'))
        self.assertEqual(run.count('## Quellen'), 1)
        cost = yaml.safe_load((base / 'chapters/ch-01-anfang/costs/sec-01-01-start.yml').read_text())
        e = cost['entries'][0]
        self.assertEqual((cost['section_id'], e['source'], e['activity_type'], e['input_tokens'], e['output_tokens'],
                          e['other_usage_quantity'], e['cost_status']),
                         ('sec-01-01-start', 'action_api', 'research', 1000, 500, 2, 'estimated'))
        self.assertAlmostEqual(e['cost_amount'], 1000 / 1e6 * 0.3 + 500 / 1e6 * 2.5 + 2 / 1000 * 35, places=4)
        self.assertEqual(meta['cost'], e['cost_amount'])
        sec = (base / 'chapters/ch-01-anfang/sections/sec-01-01-start.md').read_text()
        self.assertIn('status: research', sec)
        self.assertNotIn('k-secret', run + str(cost))

    def test_cost_schema(self):
        import jsonschema
        import json
        base, _, _ = self.run_with(GEMINI)
        schema = json.loads((ROOT / 'schemas' / 'costs.schema.json').read_text())
        data = yaml.safe_load((base / 'chapters/ch-01-anfang/costs/sec-01-01-start.yml').read_text())
        jsonschema.validate(data, schema)
        self.assertEqual(data['entries'][0]['cost_status'], 'unavailable')

    def test_anthropic_and_openai(self):
        _, head, post = self.run_with(ANTHROPIC, {'research': {'provider': 'anthropic'}})
        self.assertEqual(post.call_args[0][1]['tools'][0]['type'], 'web_search_20250305')
        self.assertEqual((head['searches'], head['sources'], head['input_tokens']), (3, 1, 2000))
        _, head, post = self.run_with(OPENAI, {'research': {'provider': 'openai'}})
        self.assertEqual(post.call_args[0][0], 'https://api.openai.com/v1/responses')
        self.assertEqual(post.call_args[0][2], {'authorization': 'Bearer k-secret'})
        self.assertEqual((head['searches'], head['sources']), (1, 1))

    def test_numbering_and_question(self):
        base, head, _ = self.run_with(GEMINI)
        with mock.patch.object(research, 'post_json', return_value=GEMINI) as post, \
                mock.patch.dict(os.environ, {research.KEY_ENV: 'k'}):
            h2 = research.run(base, 'sec-01-01-start', question='Wie hieß das Schiff?', now=NOW)
        self.assertEqual((head['id'], h2['id']), ('run-001', 'run-002'))
        self.assertIn('Wie hieß das Schiff?', post.call_args[0][1]['contents'][0]['parts'][0]['text'])

    def test_prior_knowledge_in_prompt(self):   # #478: Vorwissen weitergeben
        tmp, base = book()
        self.addCleanup(tmp.cleanup)
        folder = base / 'chapters' / 'ch-01-anfang' / 'research' / 'sec-01-01-start'
        folder.mkdir(parents=True)
        other = base / 'chapters' / 'ch-01-anfang' / 'research' / 'sec-01-02-hafen'
        other.mkdir(parents=True)

        def run_file(path, n, results, contra='Keine.', open_q='-', date='2026-11-20'):
            (path / f'run-{n:03d}.md').write_text(
                f'---\nid: run-{n:03d}\ndate: "{date}"\n---\n\n# Lauf\n\n## Fragestellung und Suchumfang\n\nF\n\n'
                f'## Rechercheergebnisse\n\n{results}\n\n## Quellen\n\n- https://nicht-ins-vorwissen.example\n\n'
                f'## Widersprüche und Unsicherheiten\n\n{contra}\n\n## Offene Fragen\n\n{open_q}\n', encoding='utf-8')
        run_file(folder, 1, 'Das Schiff hieß Valetta.', contra='Zwei Quellen nennen verschiedene Daten.', open_q='Wann lief es aus?')
        run_file(folder, 2, 'Der Hafen hatte drei Becken.', date='2026-11-21')
        run_file(other, 1, 'Anderer Abschnitt: Die Werft lag in Marsa.')
        config = research.load_config(base)
        ch, sec = config['structure']['chapters'][0], config['structure']['chapters'][0]['sections'][0]
        prior = research.prior_knowledge(base, ch, sec)
        self.assertIn('Das Schiff hieß Valetta.', prior)
        self.assertIn('Widersprüche: Zwei Quellen nennen verschiedene Daten.', prior)
        self.assertIn('Offene Fragen: Wann lief es aus?', prior)
        self.assertIn('[anderer Abschnitt] run-001', prior)
        self.assertNotIn('nicht-ins-vorwissen', prior)            # keine Quellenliste
        self.assertNotIn('Keine.', prior)                          # leere Abschnitte entfallen
        self.assertLess(prior.index('anderer Abschnitt'), prior.index('Das Schiff'))   # andere Abschnitte zuerst, älter vor neuer
        self.assertLess(prior.index('Das Schiff'), prior.index('drei Becken'))
        text = (base / 'chapters/ch-01-anfang/sections/sec-01-01-start.md').read_text(encoding='utf-8')
        _, user = research.prompts(config, ch, sec, text, '1.1', None, prior)
        self.assertIn('Vorwissen aus früheren Recherchen', user)
        self.assertIn('nicht wiederholen', user)
        with mock.patch.object(research, 'post_json', return_value=GEMINI) as post, \
                mock.patch.dict(os.environ, {research.KEY_ENV: 'k'}):
            research.run(base, 'sec-01-01-start', now=NOW)
        sent = post.call_args[0][1]['contents'][0]['parts'][0]['text']
        self.assertIn('Der Hafen hatte drei Becken.', sent)          # auch im echten Lauf
        # Obergrenze: viele lange Läufe passen nicht alle hinein, die neuesten zuerst
        for n in range(3, 12):
            run_file(folder, n, 'X' * 1700 + f' lauf{n}', date='2026-11-22')
        long_prior = research.prior_knowledge(base, ch, sec)
        self.assertLessEqual(len(long_prior), research.MAX_PRIOR + 200)
        self.assertIn('lauf11', long_prior)
        self.assertNotIn('lauf4', long_prior)
        _, user_empty = research.prompts(config, ch, sec, text, '1.1', None, '')
        self.assertNotIn('Vorwissen', user_empty)

    def test_no_key_and_closed_section(self):
        tmp, base = book()
        with tmp, mock.patch.dict(os.environ, {research.KEY_ENV: ''}):
            with self.assertRaisesRegex(research.ResearchError, 'GEMINI_API_KEY'):
                research.run(base, 'sec-01-01-start')
        tmp, base = book(section=SECTION.replace('section: false', 'section: true'))
        with tmp, mock.patch.dict(os.environ, {research.KEY_ENV: 'k'}):
            with self.assertRaisesRegex(research.ResearchError, 'abgeschlossen'):
                research.run(base, 'sec-01-01-start')

    def test_no_sources_is_said(self):
        empty = {'candidates': [{'content': {'parts': [{'text': '## Rechercheergebnisse\n\nX'}]}}], 'usageMetadata': {}}
        base, head, _ = self.run_with(empty)
        self.assertIn('keine Belege', (base / head['path']).read_text())


class SourceTest(unittest.TestCase):
    def test_gemini_redirect_resolved_with_title(self):
        import urllib.error
        redirect = 'https://vertexaisearch.cloud.google.com/grounding-api-redirect/ABC'

        class Opener:
            def open(self, req, timeout=None):
                raise urllib.error.HTTPError(req.full_url, 302, 'Found', {'location': 'https://www.nih.gov/studie'}, None)
        with mock.patch.object(research.urllib.request, 'build_opener', return_value=Opener()), \
                mock.patch.object(research, '_title', return_value='Emotionale Dysregulation bei ADHS'):
            out = research.resolve_sources([{'title': 'nih.gov', 'url': redirect},
                                            {'title': 'B', 'url': 'https://b.example'}])
        self.assertEqual(out[0], {'title': 'Emotionale Dysregulation bei ADHS (nih.gov)', 'url': 'https://www.nih.gov/studie'})
        self.assertEqual(out[1]['url'], 'https://b.example')

    def test_unresolvable_redirect_kept(self):
        redirect = 'https://vertexaisearch.cloud.google.com/grounding-api-redirect/XYZ'

        class Opener:
            def open(self, req, timeout=None):
                raise OSError('offline')
        with mock.patch.object(research.urllib.request, 'build_opener', return_value=Opener()):
            out = research.resolve_sources([{'title': 'nih.gov', 'url': redirect}])
        self.assertEqual(out, [{'title': 'nih.gov', 'url': redirect}])


class ProcessTest(unittest.TestCase):
    def test_request_done_and_failed(self):
        tmp, base = book()
        with tmp:
            folder = base / 'chapters/ch-01-anfang/research/sec-01-01-start'
            folder.mkdir(parents=True)
            (folder / 'request-001.yml').write_text(yaml.safe_dump({'section_id': 'sec-01-01-start', 'error': 'alt'}))
            (folder / 'request-002.yml').write_text(yaml.safe_dump({'section_id': 'sec-01-01-start', 'question': 'Q'}))
            with mock.patch.dict(os.environ, {research.KEY_ENV: ''}):
                res = research.process(base, now=NOW)
            self.assertFalse(res[0]['ok'])
            failed = yaml.safe_load((folder / 'request-002.yml').read_text())
            self.assertIn('GEMINI_API_KEY', failed['error'])
            self.assertEqual(research.requests(base), [])           # fehlgeschlagene laufen nicht erneut
            (folder / 'request-003.yml').write_text(yaml.safe_dump({'section_id': 'sec-01-01-start'}))
            with mock.patch.object(research, 'post_json', return_value=GEMINI), \
                    mock.patch.dict(os.environ, {research.KEY_ENV: 'k'}):
                res = research.process(base, now=NOW)
            self.assertTrue(res[0]['ok'])
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ['run-001.md'])
            self.assertIn('request: request-003', (folder / 'run-001.md').read_text())

    def test_low_budget_needs_confirmation(self):
        tmp, base = book()
        with tmp:
            folder = base / 'chapters/ch-01-anfang/research/sec-01-01-start'
            folder.mkdir(parents=True)
            (folder / 'request-001.yml').write_text(yaml.safe_dump({'section_id': 'sec-01-01-start'}))
            res = research.process(base, budget_low=True, now=NOW)
            self.assertIn('KI-Budget', res[0]['error'])


class WorkflowTest(unittest.TestCase):
    def test_workflow(self):
        text = (ROOT / '.github/workflows/research.yml').read_text(encoding='utf-8')
        data = yaml.safe_load(text)
        on = data.get('on', data.get(True))
        self.assertEqual(on['push']['paths'], ['chapters/*/research/*/request-*.yml', 'matter/research/*/request-*.yml'])
        self.assertEqual(on['push']['branches'], ['ghostwriter/**'])
        self.assertIn('secrets[steps.provider.outputs.secret_google]', text)
        self.assertNotIn('toJSON(secrets)', text)
        self.assertIn('scripts/jobs.py . process', text)   # Budget je Auftrag in jobs.py (#480)
        # Skripte vom Buch-Branch, nicht vom veralteten Arbeits-Branch
        self.assertIn('git restore --source="origin/$BOOK" --worktree -- scripts', text)
        self.assertIn('--worktree -- providers.yml', text)

    def test_workflow_python_snippets_run(self):
        # Die Einzeiler im Schritt „Buch und Arbeits-Branch“ wirklich ausführen (Fehler in YAWA, #462)
        import re
        import subprocess
        text = (ROOT / '.github/workflows/research.yml').read_text(encoding='utf-8')
        snippets = re.findall(r'python -c "([^"]+)" "\$', text)
        self.assertEqual(len(set(snippets)), 1)
        o = subprocess.run([sys.executable, '-c', snippets[0], 'buch/malta'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual((o.returncode, o.stdout.strip()), (0, 'ghostwriter/buch/malta'), o.stderr)
        # Buchname für die Concurrency-Gruppe (#480): der Shell-Schritt wirklich ausgeführt
        data = yaml.safe_load(text)
        script = next(st for st in data['jobs']['prep']['steps'] if st.get('id') == 'book')['run']
        for ref, expected in (('ghostwriter/buch/malta', 'buch/malta'), ('buch/malta', 'buch/malta')):
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / 'out'
                (Path(d) / 'ghostwriter-manifest.yml').write_text((ROOT / 'ghostwriter-manifest.yml').read_text())
                script_only = script.split('if [ "$book" = "$GHOSTWRITER_DEFAULT_BRANCH" ]')[0] + 'echo "book=$book" >> "$GITHUB_OUTPUT"'
                r = subprocess.run(['bash', '-c', script_only], cwd=d, capture_output=True, text=True,
                                   env=dict(os.environ, GITHUB_REF_NAME=ref, GITHUB_OUTPUT=str(out)))
                self.assertEqual((r.returncode, out.read_text().strip()), (0, f'book={expected}'), r.stderr)


if __name__ == '__main__':
    unittest.main()
