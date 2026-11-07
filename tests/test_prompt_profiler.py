import copy
import json
import sys
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import prompt_profiler as profiler


class PromptProfilerTests(unittest.TestCase):
    def test_read_only_no_content_in_report(self):
        for adapter in ('openai-chat', 'anthropic-messages'):
            with self.subTest(adapter=adapter):
                payload = {'model': 'test', 'system': 'Vertraulicher Manuskripttext',
                           'messages': [{'role': 'user', 'content': 'Geheime Unterhaltung'}],
                           'tools': [{'name': 'private_tool', 'description': 'Vertrauliches Werkzeug'}]}
                before = copy.deepcopy(payload)
                plan = profiler.request_plan(payload, adapter)
                plan_before = copy.deepcopy(plan)
                result = profiler.report(plan, payload)
                self.assertEqual(payload, before)
                self.assertEqual(plan, plan_before)
                serialized = json.dumps(result)
                for private in ('Vertraulicher Manuskripttext', 'Geheime Unterhaltung', 'private_tool'):
                    self.assertNotIn(private, serialized)
                self.assertEqual(result['visibility']['provider_internal'], 'unknown')
                self.assertIsNone(result['usage']['cost'])
                self.assertEqual(result['measurement']['status'], 'estimated')

    def test_duplicates_preserve_order_and_sources(self):
        message = {'role': 'system', 'content': 'Regel beibehalten'}
        payload = {'model': 'test', 'messages': [message, message, {'role': 'user', 'content': 'Aufgabe'}]}
        result = profiler.report(profiler.request_plan(payload, 'openai-chat'), payload)
        self.assertEqual(result['findings'][0]['sources'], ['$.messages[0]', '$.messages[1]'])
        self.assertEqual([r['position'] for r in result['components']], [0, 1, 2])
        self.assertEqual(len(payload['messages']), 3)

    def test_multimodal_is_not_claimed_measured(self):
        payload = {'messages': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': 'secret'}}]}]}
        result = profiler.report(profiler.request_plan(payload, 'openai-chat'), payload)
        self.assertEqual(result['measurement']['multimodal_tokens'], 'unknown')
        self.assertNotIn('secret', json.dumps(result))

    def test_changed_content_changes_fingerprint(self):
        def fingerprint(text):
            payload = {'messages': [{'role': 'user', 'content': text}]}
            return profiler.report(profiler.request_plan(payload, 'openai-chat'), payload)['visible_request']['fingerprint']
        self.assertNotEqual(fingerprint('eins'), fingerprint('zwei'))

    def test_cli_rejects_invalid_input_without_echo(self):
        result = subprocess.run(
            [sys.executable, str(Path(profiler.__file__)), '--adapter', 'openai-chat'],
            input='{"private": "Manuskript-geheim", broken}', text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Manuskript-geheim', result.stdout + result.stderr)
        self.assertEqual(result.stdout, '')

    def test_core_metadata_is_preserved_without_original_text(self):
        part = profiler.component('Quellen nennen', source='START.md#3', kind='rule',
                                  scope='global', priority='required', activation='research', layer='core')
        plan = {'adapter': 'openai-chat', 'model': 'test', 'components': [part]}
        result = profiler.report(plan, {'messages': []})
        row = result['components'][0]
        self.assertEqual(row['source'], 'START.md#3')
        self.assertEqual(row['priority'], 'required')
        self.assertEqual(row['activation'], 'research')
        self.assertEqual(row['layer'], 'core')
        self.assertNotIn('Quellen nennen', json.dumps(result))

    def test_usage_semantics_and_missing_fields(self):
        usage = profiler.provider_usage({'usage': {'input_tokens': 7, 'output_tokens': 2,
            'cache_creation_input_tokens': 11, 'cache_read_input_tokens': 13}}, 'anthropic-messages')
        self.assertEqual(usage['prompt_tokens'], 31)
        self.assertEqual(usage['uncached_input_tokens'], 7)
        self.assertIsNone(profiler.provider_usage({'usage': {'input_tokens': 7}},
                                                'anthropic-messages')['prompt_tokens'])
        usage = profiler.provider_usage({'usage': {'prompt_tokens': 31, 'completion_tokens': 2,
            'prompt_tokens_details': {'cached_tokens': 13}}}, 'openai-chat')
        self.assertEqual(usage['prompt_tokens'], 31)
        self.assertEqual(usage['cache_read_tokens'], 13)
        self.assertIsNone(usage['cache_write_tokens'])
        self.assertIsNone(profiler.count(True))
        self.assertIsNone(profiler.count(-1))

    def test_aggregation_preserves_unknown_and_tracks_retransmission(self):
        payload = {'model': 'test', 'messages': [{'role': 'system', 'content': 'Regel'}]}
        first = profiler.Capture(payload, 'openai-chat').finish({'usage': {'prompt_tokens': 12}})
        second = profiler.Capture(payload, 'openai-chat').finish()
        summary = profiler.aggregate([first, second])
        self.assertEqual(summary['usage']['prompt_tokens'],
                         {'known_sum': 12, 'known_calls': 1, 'unknown_calls': 1})
        self.assertEqual(len(summary['repeated_components']), 1)
        self.assertEqual(summary['cache_savings'], 'unknown')
        self.assertNotIn('Regel', json.dumps(summary))

    def test_transport_capture_is_opt_in_and_preserves_request_and_result(self):
        import contextlib
        import io
        from unittest.mock import patch, MagicMock
        import analyze
        for provider in ('openai', 'anthropic'):
            with self.subTest(provider=provider):
                response = {'choices': [{'message': {'content': 'Antwort-geheim'}}],
                            'content': [{'type': 'text', 'text': 'Antwort-geheim'}],
                            'usage': {'prompt_tokens': 20, 'completion_tokens': 3,
                                      'input_tokens': 20, 'output_tokens': 3}}
                sent = []
                def transport(req, **kwargs):
                    sent.append((req.full_url, req.data, dict(req.headers), kwargs))
                    result = MagicMock()
                    result.__enter__.return_value.read.return_value = json.dumps(response).encode()
                    return result
                with patch.dict('os.environ', {}, clear=True), patch.object(analyze.urllib.request, 'urlopen', transport):
                    plain_log, profile_log = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stderr(plain_log):
                        plain = analyze.call_llm(provider, 'FAKE-TEST-KEY', 'test-model', 'System-geheim', 'Buch-geheim')
                    with patch.dict('os.environ', {'GHOSTWRITER_PROMPT_PROFILE': '1'}), contextlib.redirect_stderr(profile_log):
                        profiled = analyze.call_llm(provider, 'FAKE-TEST-KEY', 'test-model', 'System-geheim', 'Buch-geheim')
                self.assertEqual(plain, profiled)
                self.assertEqual(sent[0], sent[1])
                self.assertEqual(plain_log.getvalue(), '')
                text = profile_log.getvalue()
                for secret in ('FAKE-TEST-KEY', 'System-geheim', 'Buch-geheim', 'Antwort-geheim'):
                    self.assertNotIn(secret, text)
                entry = json.loads(text.removeprefix('GHOSTWRITER_PROFILE '))
                self.assertEqual(entry['transport_status'], 'response_received')
                self.assertEqual(entry['transport_body']['bytes'], len(sent[1][1]))
                import hashlib
                self.assertEqual(entry['transport_body']['fingerprint'], hashlib.sha256(sent[1][1]).hexdigest())
                self.assertEqual(len(entry['core_components']), 2)
                self.assertEqual(entry['visibility']['ghostwriter_core'], 'captured_call_arguments')
                self.assertEqual(entry['usage']['status'], 'provider_reported')

    def test_transport_failure_keeps_exception_and_omits_error_content(self):
        import contextlib
        import io
        import urllib.request
        from unittest.mock import patch
        import analyze
        log = io.StringIO()
        failure = RuntimeError('Vertraulicher-Providerfehler')
        req = urllib.request.Request('https://example.invalid', data=b'{"messages": []}')
        with patch.dict('os.environ', {'GHOSTWRITER_PROMPT_PROFILE': '1'}), \
             patch.object(analyze.urllib.request, 'urlopen', side_effect=failure), \
             contextlib.redirect_stderr(log):
            with self.assertRaises(RuntimeError) as caught:
                analyze.send_llm(req, 'openai-chat')
        self.assertIs(caught.exception, failure)
        self.assertNotIn('Vertraulicher-Providerfehler', log.getvalue())
        entry = json.loads(log.getvalue().removeprefix('GHOSTWRITER_PROFILE '))
        self.assertEqual(entry['transport_status'], 'failed')
        self.assertEqual(entry['usage']['status'], 'unavailable')

    def test_profiler_failure_does_not_change_transport_result(self):
        import contextlib
        import io
        from unittest.mock import patch, MagicMock
        import analyze
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"ok"}}]}'
        log = io.StringIO()
        with patch.dict('os.environ', {'GHOSTWRITER_PROMPT_PROFILE': '1'}, clear=True), \
             patch.object(profiler, 'component', side_effect=RuntimeError('Nicht-ausgeben')), \
             patch.object(analyze.urllib.request, 'urlopen', return_value=response), \
             contextlib.redirect_stderr(log):
            self.assertEqual(analyze.call_llm('openai', 'FAKE', 'test', 'Regel', 'Aufgabe'), ('ok', 0, 0))
        self.assertNotIn('Nicht-ausgeben', log.getvalue())
        self.assertIn('konnte nicht vorbereitet werden', log.getvalue())

    def test_aggregate_cli_reads_prefixed_reports(self):
        payload = {'messages': [{'role': 'user', 'content': 'Nicht-im-Report'}]}
        report = profiler.Capture(payload, 'openai-chat').finish({'usage': {'prompt_tokens': 9}})
        result = subprocess.run(
            [sys.executable, str(Path(profiler.__file__)), '--aggregate'],
            input='GHOSTWRITER_PROFILE ' + json.dumps(report) + '\n', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary['calls'], 1)
        self.assertEqual(summary['usage']['prompt_tokens']['known_sum'], 9)
        self.assertEqual(summary['usage']['cache_read_tokens']['unknown_calls'], 1)
        self.assertNotIn('Nicht-im-Report', result.stdout)

    def test_pipe_projection_excludes_non_model_metadata(self):
        payload = {'model': 'local', 'messages': [{'role': 'user', 'content': 'PRIVATE'}],
                   'metadata': {'callable': lambda: None, 'secret': 'DO_NOT_DISPLAY'},
                   'options': {'num_ctx': 32768}}
        before_messages = copy.deepcopy(payload['messages'])
        result = profiler.openwebui_report(payload)
        self.assertEqual(payload['messages'], before_messages)
        self.assertEqual(result['coverage']['excluded_top_level_fields'], 1)
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('DO_NOT_DISPLAY', json.dumps(result))
        self.assertIsNone(result['usage']['cost'])

    def test_single_file_pipe_uses_current_shared_core(self):
        import build_openwebui_profiler
        self.assertTrue(build_openwebui_profiler.build(check=True))
