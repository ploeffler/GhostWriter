"""#462 Teil 2 und #65 Punkt 2: Recherche über Perplexity (Agent API), xAI (Responses API) und OpenRouter (openrouter:web_search)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pricing  # noqa: E402
import research  # noqa: E402


def message(text, annotations=()):
    return {'type': 'message', 'content': [{'type': 'output_text', 'text': text, 'annotations': list(annotations)}]}


class ProviderCallsTest(unittest.TestCase):
    def call(self, fn, response, *args):
        sent = {}

        def fake(url, body, headers, provider='', model=''):
            sent.update(url=url, body=body, headers=headers, provider=provider)
            return response
        with mock.patch.object(research, 'post_json', fake):
            return fn('KEY', 'm', 'SYS', 'USER', *args), sent

    def test_perplexity_agent_api(self):
        data = {'id': 'r1', 'output': [
            {'type': 'search_results', 'results': [{'id': 1, 'title': 'A', 'url': 'https://a.example', 'snippet': ''}, {'id': 2, 'title': 'B', 'url': 'https://b.example'}]},
            message('Antwort [1]')],
            'usage': {'input_tokens': 100, 'output_tokens': 50, 'tool_calls_details': {'search_web': {'invocation': 2}}}}
        res, sent = self.call(research.call_perplexity, data)
        self.assertEqual(sent['url'], 'https://api.perplexity.ai/v1/agent')            # Agent API, nicht Sonar über Chat Completions
        self.assertEqual(sent['body']['tools'], [{'type': 'web_search'}])
        self.assertEqual((sent['body']['instructions'], sent['body']['input']), ('SYS', 'USER'))
        self.assertEqual(sent['headers']['authorization'], 'Bearer KEY')
        self.assertEqual((res['text'], res['searches'], res['input_tokens'], res['output_tokens']), ('Antwort [1]', 2, 100, 50))
        self.assertEqual([s['url'] for s in res['sources']], ['https://a.example', 'https://b.example'])   # Quellen aus search_results

    def test_xai_responses_api(self):
        data = {'id': 'x1', 'output': [{'type': 'web_search_call'}, {'type': 'web_search_call'},
                                       message('Text', [{'type': 'url_citation', 'title': 'T', 'url': 'https://x.example'}])],
                'usage': {'input_tokens': 10, 'output_tokens': 5}}
        res, sent = self.call(research.call_xai, data)
        self.assertEqual(sent['url'], 'https://api.x.ai/v1/responses')
        self.assertEqual(sent['body']['tools'], [{'type': 'web_search'}])
        self.assertEqual((res['searches'], [s['url'] for s in res['sources']]), (2, ['https://x.example']))

    def test_openrouter_server_tool_and_usage_counter(self):
        data = {'output': [message('T', [{'type': 'url_citation', 'title': 'Q', 'url': 'https://q.example'}])],
                'usage': {'input_tokens': 7, 'output_tokens': 3, 'server_tool_use_details': {'web_search_requests': 3}}}
        res, sent = self.call(research.call_openrouter, data)
        self.assertEqual(sent['url'], 'https://openrouter.ai/api/v1/responses')
        self.assertEqual(sent['body']['tools'][0]['type'], 'openrouter:web_search')       # nicht :online und nicht das Plugin „web“
        self.assertNotIn('plugins', sent['body'])
        self.assertEqual(res['searches'], 3)
        self.assertEqual(res['sources'][0]['url'], 'https://q.example')

    def test_registered_and_prices_from_the_provider_pages(self):
        for pid in ('perplexity', 'xai', 'openrouter'):
            self.assertIn(pid, research.PROVIDERS)
            self.assertIn(pid, research.CALLS)
        e = pricing.estimate('perplexity', 'perplexity/sonar', 1_000_000, 1_000_000, 1000)
        self.assertEqual(float(e['amount']), 0.25 + 2.5 + 2.5)                              # Tokens plus 2,50 $ je 1.000 Suchaufrufe
        e = pricing.estimate('xai', 'grok-4.3', 1_000_000, 1_000_000, 1000)
        self.assertEqual(float(e['amount']), 1.25 + 2.5 + 5)                                # web_search 5 $ je 1.000 Aufrufe
        e = pricing.estimate('openrouter', 'openai/gpt-5.6-luna', 0, 0, 1000)
        self.assertEqual(float(e['amount']), 7.0)                                           # Exa 0,007 $ je Anfrage
        self.assertTrue(e['search_priced'])


if __name__ == '__main__':
    unittest.main()
