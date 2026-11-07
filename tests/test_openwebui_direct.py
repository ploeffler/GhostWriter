"""Direkte Chat-Ausgabe: Start/Bibliothek dürfen keinen Modellaufruf benötigen."""
import tempfile
import asyncio
import copy
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

try:
    import pydantic
except ImportError:
    pydantic = None

ROOT = Path(__file__).resolve().parents[1]
VIEW = '### Bibliothek\n\n| Nr. | Buch |\n|---|---|\n| 1 | Unveränderter Buchtitel |'


def result(**values):
    return json.dumps({'ok': True, 'result': values}, ensure_ascii=False)


@unittest.skipIf(pydantic is None, 'Optionale Open-WebUI-Abhängigkeit pydantic fehlt')
class DirectPipeTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('ghostwriter_direct', ROOT / 'integrations/openwebui/ghostwriter_direct.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.pipe = self.module.Pipe()
        self.state = tempfile.TemporaryDirectory()
        self.addCleanup(self.state.cleanup)
        self.pipe._state_dir = Path(self.state.name)
        self.start = AsyncMock(return_value=result(view=VIEW, content='Interne Regeln'))
        self.library = AsyncMock(return_value=result(view=VIEW))
        self.tools = self.bindings('github', self.start, self.library)

    def bindings(self, tool_id, start, library):
        return {method: {'tool_id': tool_id, 'spec': {'name': method}, 'callable': function}
                for method, function in [('read_start_md', start), ('show_library', library)]}

    def call(self, text='Start', **extra):
        body = {'model': 'ghostwriter_direct', 'messages': [{'role': 'user', 'content': text}]}
        return asyncio.run(self.pipe.pipe(body, __tools__=self.tools, __user__={'id': 'user-1'}, **extra))

    def test_start_is_exact_greeting_and_view_without_model(self):
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            output = self.call()
        self.assertEqual(output, 'Herzlich willkommen, dein Schreibassistent ist geladen und bereit.\n\n' + VIEW)
        self.start.assert_awaited_once_with()
        self.library.assert_not_awaited()
        forward.assert_not_awaited()
        self.assertNotIn('Interne Regeln', output)
        self.assertNotIn('"name": "answer"', output)

    def test_library_commands_return_view_verbatim_and_fetch_when_not_in_start(self):
        self.start.return_value = result(already_loaded=True)
        for command in ['Bibliothek', 'Library', 'Home', '  BIBLIOTHEK  ']:
            with self.subTest(command=command), patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
                self.assertEqual(self.call(command), VIEW)
                forward.assert_not_awaited()
        self.assertEqual(self.library.await_count, 4)

    def test_book_request_with_old_tool_is_not_sent_to_model(self):
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            output = self.call('Buch 1')
        self.assertIn('Version 1.3', output)
        forward.assert_not_awaited()

    def test_number_without_view_context_refreshes_library_instead_of_guessing(self):
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            output = self.call('1')
        self.assertIn('Bitte aus dieser Bibliothek wählen', output)
        self.assertIn(VIEW, output)
        forward.assert_not_awaited()

    def test_clean_view_navigation_survives_restart_and_is_bound_to_chat_and_history(self):
        receipt = 'eyJraW5kIjoiYm9vayJ9.signature'
        body = {'model': 'direct', 'messages': [{'role': 'user', 'content': 'Buch 1'}]}
        metadata = {'chat_id': 'chat-1'}
        scope = self.pipe._scope(body, {'id': 'u'}, metadata)
        result = {'view': '### Buch\n\nLesestand: `buch/test` · `abcdefg`\n\nKapitel\n\n<!-- ghostwriter-nav:' + receipt + ' -->',
                  'navigation_receipt': receipt}
        clean = self.pipe._answer(result, body, scope)
        self.assertEqual(clean, '### Buch\n\n\nKapitel')
        self.assertNotIn('ghostwriter-nav', clean)
        history = {**body, 'messages': [*body['messages'], {'role': 'assistant', 'content': clean}, {'role': 'user', 'content': '1'}]}
        restarted = self.module.Pipe()
        restarted._state_dir = Path(self.state.name)
        self.assertEqual(restarted._receipt(history, scope, latest_only=True), receipt)
        other_scope = self.pipe._scope(body, {'id': 'u'}, {'chat_id': 'other'})
        self.assertIsNone(restarted._receipt(history, other_scope))
        changed = copy.deepcopy(history)
        changed['messages'][0]['content'] = 'Buch 2'
        self.assertIsNone(restarted._receipt(changed, scope))
        changed = copy.deepcopy(history)
        changed['messages'].insert(-1, {'role': 'assistant', 'content': 'Welche Zahl meinst du?'})
        self.assertIsNone(restarted._receipt(changed, scope, latest_only=True))

    def test_navigation_storage_failure_is_visible_without_leaking_receipt(self):
        self.start.return_value = result(view=VIEW, navigation_receipt='eyJraW5kIjoibGlicmFyeSJ9.signature')
        with patch.object(self.pipe, '_state', side_effect=OSError('PRIVATE_PATH')):
            answer = self.call(__metadata__={'chat_id': 'c'})
        self.assertIn('Navigation konnte nicht gespeichert werden', answer)
        self.assertNotIn('signature', answer)
        self.assertNotIn('PRIVATE_PATH', answer)

    def test_reload_passes_trusted_metadata_to_already_bound_tool(self):
        self.assertTrue(self.call('Start neu laden').endswith(VIEW))
        self.start.assert_awaited_once_with()

    def test_error_is_visible_and_never_replaced_by_model_or_empty_library(self):
        self.start.return_value = result(library_error='GitHub HTTP 404')
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            output = self.call()
        self.assertEqual(output, '✗ GitHub HTTP 404')
        self.library.assert_not_awaited()
        forward.assert_not_awaited()

    def test_missing_or_malformed_tool_result_is_not_success(self):
        for value in ['{"name":"answer","parameters":{}}', 'not JSON', '{"ok":false,"error":"Kein Zugriff"}']:
            self.start.return_value = value
            with self.subTest(value=value), patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
                self.assertTrue(self.call().startswith('✗ '))
                forward.assert_not_awaited()

    def test_no_mixing_of_tools_and_explicit_id_resolves_duplicates(self):
        duplicate = {**self.tools, **{'second_' + name: entry for name, entry in self.bindings('other', self.start, self.library).items()}}
        body = {'model': 'ghostwriter_direct', 'messages': [{'role': 'user', 'content': 'Start'}]}
        output = asyncio.run(self.pipe.pipe(body, __tools__=duplicate))
        self.assertTrue(output.startswith('✗ '))
        self.start.assert_not_awaited()
        self.pipe.valves.TOOL_ID = 'github'
        output = asyncio.run(self.pipe.pipe(body, __tools__=duplicate))
        self.assertTrue(output.endswith(VIEW))
        split = {'read_start_md': self.tools['read_start_md'], 'show_library': {**self.tools['show_library'], 'tool_id': 'other'}}
        self.pipe.valves.TOOL_ID = ''
        self.assertTrue(asyncio.run(self.pipe.pipe(body, __tools__=split)).startswith('✗ '))

    def test_model_output_cannot_choose_arbitrary_functions(self):
        self.tools['answer'] = {'tool_id': 'github', 'spec': {'name': 'answer'}, 'callable': AsyncMock()}
        self.call()
        self.tools['answer']['callable'].assert_not_awaited()

    def test_ordinary_message_forwards_with_internal_instructions_and_unchanged_body(self):
        body = {'model': 'ghostwriter_direct', 'messages': [{'role': 'user', 'content': 'Bitte überarbeite meinen Satz.'}]}
        before = copy.deepcopy(body)
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock, return_value='Modellantwort') as forward:
            output = asyncio.run(self.pipe.pipe(body, __tools__=self.tools, __user__={'id': 'u'}))
        self.assertEqual(output, 'Modellantwort')
        sent = forward.await_args.args[0]
        self.assertEqual(sent['messages'][0]['role'], 'system')
        self.assertIn('Interne Regeln', sent['messages'][0]['content'])
        self.assertEqual(body, before)

    def test_background_tasks_do_not_initialize_or_route_last_user_command(self):
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock, return_value='Titel') as forward:
            self.assertEqual(self.call('Start', __task__='title_generation'), 'Titel')
        self.start.assert_not_awaited()
        self.library.assert_not_awaited()
        forward.assert_awaited_once()

    def test_forward_uses_internal_provider_without_permission_bypass(self):
        users = types.ModuleType('open_webui.models.users')
        users.Users = types.SimpleNamespace(get_user_by_id=AsyncMock(return_value=object()))
        chat = types.ModuleType('open_webui.utils.chat')
        chat.generate_chat_completion = AsyncMock(return_value='Providerantwort')
        body = {'model': 'ghostwriter_direct', 'messages': [
            {'role': 'assistant', 'content': 'Ansicht\n\n<!-- ghostwriter-nav:eyJraW5kIjoiYm9vayJ9.signature -->'},
            {'role': 'user', 'content': 'Text'}], 'stream': True}
        before = copy.deepcopy(body)
        request = object()
        with patch.dict(sys.modules, {'open_webui.models.users': users, 'open_webui.utils.chat': chat}):
            output = asyncio.run(self.pipe._forward(body, request, {'id': 'u'}, {'chat_id': 'c'}))
        self.assertEqual(output, 'Providerantwort')
        args = chat.generate_chat_completion.await_args
        self.assertEqual(args.args[1]['model'], 'llama3.2:3b')
        self.assertEqual(args.args[1]['metadata'], {'chat_id': 'c'})
        self.assertNotIn('ghostwriter-nav:', args.args[1]['messages'][0]['content'])
        self.assertEqual(args.kwargs, {})
        self.assertEqual(body, before)

    def test_provider_value_error_cannot_leak_credentials(self):
        users = types.ModuleType('open_webui.models.users')
        users.Users = types.SimpleNamespace(get_user_by_id=AsyncMock(return_value=object()))
        chat = types.ModuleType('open_webui.utils.chat')
        chat.generate_chat_completion = AsyncMock(side_effect=ValueError('TEST_PROVIDER_SECRET_DO_NOT_DISPLAY'))
        body = {'model': 'ghostwriter_direct', 'messages': [{'role': 'user', 'content': 'Bitte schreibe.'}]}
        with patch.dict(sys.modules, {'open_webui.models.users': users, 'open_webui.utils.chat': chat}):
            output = asyncio.run(self.pipe.pipe(body, __tools__=self.tools, __user__={'id': 'u'}, __request__=object()))
        self.assertTrue(output.startswith('✗ '))
        self.assertNotIn('TEST_PROVIDER_SECRET_DO_NOT_DISPLAY', output)

    def test_other_pipe_is_not_an_allowed_base_model(self):
        users = types.ModuleType('open_webui.models.users')
        users.Users = types.SimpleNamespace(get_user_by_id=AsyncMock())
        chat = types.ModuleType('open_webui.utils.chat')
        chat.generate_chat_completion = AsyncMock()
        self.pipe.valves.BASE_MODEL = 'other_pipe'
        request = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(MODELS={'other_pipe': {'pipe': {'type': 'pipe'}}})))
        body = {'model': 'ghostwriter_direct', 'messages': [{'role': 'user', 'content': 'Text'}]}
        with patch.dict(sys.modules, {'open_webui.models.users': users, 'open_webui.utils.chat': chat}):
            output = asyncio.run(self.pipe.pipe(body, __tools__=self.tools, __user__={'id': 'u'}, __request__=request))
        self.assertIn('keine weitere Pipe', output)
        chat.generate_chat_completion.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
