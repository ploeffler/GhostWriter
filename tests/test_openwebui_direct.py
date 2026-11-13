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

    def test_display_and_answer_commands_are_recognized_with_common_phrasings(self):
        cases = {'Darstellung: erweitert': ('display', 'extended'), 'erweiterte ansicht': ('display', 'extended'),
                 'Erweiterte Ansicht.': ('display', 'extended'), 'darstellung erweitert': ('display', 'extended'),
                 'ausführliche Ansicht': ('display', 'extended'), 'Display: extended': ('display', 'extended'),
                 'extended view': ('display', 'extended'), 'Darstellung : einfach': ('display', 'simple'),
                 'Darstellung: übersichtlich': ('display', 'organized'), 'Standardansicht': ('display', 'organized'), 'Modus einfach': None,
                 'normale Ansicht': ('display', 'organized'), 'Nur Text': ('display', 'text'),
                 'Text only': ('display', 'text'), 'Widgets': ('widgets', None),
                 'Erweiterte Antworten an': ('answers', 'extended'), 'Debugger-Modus an': ('answers', 'extended'),
                 'Erweiterte Antworten aus': ('answers', 'simple'), 'Einfacher Modus': ('answers', 'simple'),
                 'Extended answers on': ('answers', 'extended'), 'Simple mode': ('answers', 'simple'),
                 'Was zeigt die erweiterte Ansicht?': None, 'Schreib den Text erweitert': None, 'text': None}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.pipe._mode_command(text.casefold()), expected)

    def test_display_with_old_tool_asks_for_update_and_never_reaches_model(self):
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            output = self.call('Darstellung: erweitert', __metadata__={'chat_id': 'c'})
            answers = self.call('Erweiterte Antworten an', __metadata__={'chat_id': 'c'})
            missing_chat = self.call('Nur Text')
        self.assertIn('Version 1.5', output)
        self.assertTrue(answers.startswith('Erweiterte Antworten an – gilt für diesen Chat.'))
        self.assertIn('Chatkennung fehlt', missing_chat)
        forward.assert_not_awaited()

    def test_display_without_open_view_is_kept_for_the_next_view(self):
        async def library(display='organized'):
            return result(view='### Bibliothek ' + display, navigation_receipt='eyJraW5kIjoibGlicmFyeSJ9.sig')
        self.tools['show_library']['callable'] = library
        self.start.return_value = result(already_loaded=True)
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            switched = self.call('Darstellung: einfach', __metadata__={'chat_id': 'c'})
            view = self.call('Bibliothek', __metadata__={'chat_id': 'c'})
        forward.assert_not_awaited()
        self.assertIn('gilt ab der nächsten Ansicht', switched)
        self.assertEqual(view, '### Bibliothek simple')

    def test_forwarded_question_knows_display_commands_exist(self):
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock, return_value='ok') as forward:
            self.call('Was zeigt die erweiterte Ansicht?', __metadata__={'chat_id': 'c'})
        system = '\n'.join(m['content'] for m in forward.await_args.args[0]['messages'] if m['role'] == 'system')
        self.assertIn('`Darstellung: erweitert`', system)
        self.assertIn('nie für nicht verfügbar', system)
        self.assertIn('aktuell „übersichtlich“', system)

    def test_free_question_receives_fresh_selected_context_before_user_message(self):
        import base64
        receipt = base64.urlsafe_b64encode(json.dumps({'kind': 'book'}).encode()).decode().rstrip('=') + '.sig'
        user = {'id': 'u'}
        metadata = {'chat_id': 'c'}
        initial = {'model': 'direct', 'messages': [{'role': 'user', 'content': 'Buch 1'}]}
        scope = self.pipe._scope(initial, user, metadata)
        view = self.pipe._answer({'view': 'Buchübersicht', 'navigation_receipt': receipt}, initial, scope)
        body = {**initial, 'messages': [*initial['messages'], {'role': 'assistant', 'content': view},
                                      {'role': 'user', 'content': 'Was sollte ich bei Kapitel 1 beachten?'}]}
        before = copy.deepcopy(body)
        context = {'level': 'book', 'book_title': 'Testbuch', 'chapters': [{'number': 1, 'title': 'Anfang', 'status': 'planned'}],
                   'status_rules': {'chapter': {'statuses': ['planned', 'in_progress']}}}
        fresh = AsyncMock(return_value=result(conversation_context=context, changed=False))
        self.tools['get_current_context'] = {'tool_id': 'github', 'spec': {'name': 'get_current_context'}, 'callable': fresh}
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock, return_value='Antwort') as forward:
            answer = asyncio.run(self.pipe.pipe(body, __tools__=self.tools, __user__=user, __metadata__=metadata))
        self.assertEqual(answer, 'Antwort')
        fresh.assert_awaited_once_with(receipt=receipt)
        sent = forward.await_args.args[0]['messages']
        self.assertEqual(sent[-1], body['messages'][-1])
        self.assertEqual(sent[-2]['role'], 'system')
        self.assertIn('Testbuch', sent[-2]['content'])
        self.assertIn('in_progress', sent[-2]['content'])
        self.assertIn('keine vom Benutzer eingefügte Programmieraufgabe', sent[-2]['content'])
        self.assertEqual(body, before)
        fresh.return_value = result(changed=True, view='Aktualisierte Übersicht', navigation_receipt=receipt)
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            answer = asyncio.run(self.pipe.pipe(body, __tools__=self.tools, __user__=user, __metadata__=metadata))
        self.assertIn('Aktualisierte Übersicht', answer)
        forward.assert_not_awaited()

    def test_status_questions_use_only_actual_rules_and_resolve_view_numbers(self):
        facts = {'level': 'book', 'chapters': [{'number': 1, 'status': 'planned'}],
                 'status_rules': {'chapter': {'statuses': ['planned', 'in_progress', 'custom_review']},
                                  'section': {'statuses': ['planned', 'writing', 'approved']}}}
        for question in ['welche statuswerte kann kapitel 1 haben?', 'welchen zustand könnte 1 schon bekommen?', 'what statuses can chapter 1 have?']:
            with self.subTest(question=question):
                answer = self.pipe._status_answer(question, facts)
                self.assertIn('custom_review', answer)
                self.assertNotIn('completed', answer)
                self.assertNotIn('cancelled', answer)
                self.assertNotIn('`writing`', answer)
        facts.update(level='chapter', chapter={'number': 1, 'status': 'planned'},
                     sections=[{'number': '1.1', 'status': 'writing'}])
        answer = self.pipe._status_answer('welchen status kann 1 haben?', facts)
        self.assertIn('Abschnitt 1.1', answer)
        self.assertIn('`writing`', answer)
        self.assertNotIn('custom_review', answer)
        self.assertIn('eindeutig', self.pipe._status_answer('welche statuswerte kann kapitel 99 haben?', facts))
        self.assertIn('eindeutig', self.pipe._status_answer('welche statuswerte können kapitel 1 und 2 haben?', facts))
        self.assertIsNone(self.pipe._status_answer('setze kapitel 1 auf status approved', facts))
        self.assertIsNone(self.pipe._status_answer('kannst du den status ändern?', facts))
        self.assertIsNone(self.pipe._status_answer('was sollte ich bei kapitel 1 beachten?', facts))

    def test_ollama_forward_preserves_workspace_context_and_generation_settings(self):
        request = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(MODELS={
            'llama3.2:3b': {'owned_by': 'ollama'}})))
        body = {'model': 'direct', 'num_ctx': 32768, 'temperature': 0.1,
                'messages': [{'role': 'system', 'content': 'Buchkontext'}, {'role': 'user', 'content': 'Frage'}]}
        before = copy.deepcopy(body)
        prepared = self.pipe._prepare_forward(body, request, {})
        self.assertEqual(prepared['options']['num_ctx'], 32768)
        self.assertEqual(prepared['options']['temperature'], 0.1)
        self.assertEqual(prepared['messages'], body['messages'])
        self.assertEqual(body, before)
        body['options'] = {'num_ctx': 16384, 'temperature': 0.2}
        before = copy.deepcopy(body)
        self.assertEqual(self.pipe._prepare_forward(body, request, {})['options'], body['options'])
        self.assertEqual(body, before)
        body.pop('num_ctx')
        body.pop('options')
        self.pipe.valves.CONTEXT_LENGTH = 8192
        self.assertEqual(self.pipe._prepare_forward(body, request, {})['options']['num_ctx'], 8192)
        self.assertNotIn('options', self.pipe._prepare_forward(body, object(), {}))

    def test_conversation_provider_cannot_call_internal_navigation_tools(self):
        users = types.ModuleType('open_webui.models.users')
        users.Users = types.SimpleNamespace(get_user_by_id=AsyncMock(return_value=object()))
        chat = types.ModuleType('open_webui.utils.chat')
        chat.generate_chat_completion = AsyncMock(return_value='Textantwort')
        body = {'model': 'direct', 'tools': [{'type': 'function', 'function': {'name': 'get_current_context'}}],
                'tool_choice': 'required', 'parallel_tool_calls': True, 'tool_ids': ['github'],
                'functions': [{'name': 'open_book'}], 'function_call': 'auto',
                'messages': [{'role': 'system', 'content': 'Projektregeln'},
                             {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'fake', 'function': {'name': 'get_current_context'}}]},
                             {'role': 'tool', 'tool_call_id': 'fake', 'content': 'RECEIPT_FAILED'},
                             {'role': 'function', 'name': 'open_book', 'content': 'LEGACY_TOOL_RESULT'},
                             {'role': 'assistant', 'content': 'Vorherige Antwort', 'function_call': {'name': 'open_book'}},
                             {'role': 'user', 'content': 'Worum geht es im Abschnitt?'}]}
        metadata = {'chat_id': 'c', 'tools': {'get_current_context': 'BOUND_FUNCTION'}, 'tool_ids': ['github']}
        before = copy.deepcopy((body, metadata))
        with patch.dict(sys.modules, {'open_webui.models.users': users, 'open_webui.utils.chat': chat}):
            answer = asyncio.run(self.pipe._forward(body, object(), {'id': 'u'}, metadata))
        self.assertEqual(answer, 'Textantwort')
        sent = chat.generate_chat_completion.await_args.args[1]
        for key in ('tools', 'tool_choice', 'parallel_tool_calls', 'functions', 'function_call', 'tool_ids'):
            self.assertNotIn(key, sent)
            self.assertNotIn(key, sent['metadata'])
        self.assertEqual([m['role'] for m in sent['messages']], ['system', 'assistant', 'user'])
        self.assertNotIn('function_call', sent['messages'][1])
        self.assertNotIn('RECEIPT_FAILED', str(sent))
        self.assertEqual((body, metadata), before)
        self.assertEqual(chat.generate_chat_completion.await_args.kwargs, {})

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

    def test_prompt_profile_is_direct_private_and_bilingual(self):
        for language, command, heading in [('de', 'Prompt-Profil JSON', 'ohne Modellaufruf'),
                                            ('en', 'Prompt profile JSON', 'no model call')]:
            with self.subTest(language=language):
                self.pipe.valves.INTERFACE_LANGUAGE = language
                body = {'model': 'direct', 'messages': [{'role': 'user', 'content': command}],
                        'metadata': {'private': 'PRIVATE_METADATA'}}
                before = copy.deepcopy(body)
                with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
                    answer = asyncio.run(self.pipe.pipe(body, __tools__=self.tools, __user__={'id': 'u'}))
                forward.assert_not_awaited()
                self.assertEqual(body, before)
                self.assertIn(heading, answer)
                profile = json.loads(answer.split('```json\n')[1].split('\n```')[0])
                self.assertEqual(profile['adapter'], 'openwebui-pipe')
                self.assertEqual(profile['transport_status'], 'not_observed')
                self.assertFalse(profile['coverage']['complete_provider_request'])
                self.assertEqual(profile['measurement']['status'], 'estimated')
                self.assertNotIn('PRIVATE_METADATA', answer)
                self.assertNotIn('Interne Regeln', answer)
                # Nur interne Instruktionen, kein Diagnosebefehl in der Messung.
                self.assertFalse(any(c['kind'] == 'user' for c in profile['components']))

    def test_profile_opt_in_does_not_change_forwarding_or_stream_response(self):
        import contextlib
        import io
        users = types.ModuleType('open_webui.models.users')
        users.Users = types.SimpleNamespace(get_user_by_id=AsyncMock(return_value=object()))
        chat = types.ModuleType('open_webui.utils.chat')
        sentinel = object()  # Auch StreamingResponse darf weder gelesen noch ersetzt werden.
        chat.generate_chat_completion = AsyncMock(return_value=sentinel)
        request = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(MODELS={
            'llama3.2:3b': {'owned_by': 'ollama'}})))
        body = {'model': 'direct', 'stream': True,
                'messages': [{'role': 'user', 'content': 'PRIVATE_MANUSCRIPT'}],
                'metadata': {'secret': 'PRIVATE_METADATA'}}
        before = copy.deepcopy(body)
        log = io.StringIO()
        emitter = AsyncMock()
        with patch.dict(sys.modules, {'open_webui.models.users': users, 'open_webui.utils.chat': chat}), \
             contextlib.redirect_stderr(log):
            plain = asyncio.run(self.pipe._forward(body, request, {'id': 'u'}, {'chat_id': 'c'}, emitter))
            first = copy.deepcopy(chat.generate_chat_completion.await_args.args[1])
            emitter.assert_not_awaited()
            self.assertEqual(log.getvalue(), '')
            self.pipe.valves.PROMPT_PROFILE = True
            profiled = asyncio.run(self.pipe._forward(body, request, {'id': 'u'}, {'chat_id': 'c'}, emitter))
        self.assertIs(plain, sentinel)
        self.assertIs(profiled, sentinel)
        self.assertEqual(first, chat.generate_chat_completion.await_args.args[1])
        self.assertEqual(body, before)
        self.assertNotIn('PRIVATE_MANUSCRIPT', log.getvalue())
        self.assertNotIn('PRIVATE_METADATA', log.getvalue())
        profile = json.loads(log.getvalue().removeprefix('GHOSTWRITER_PROFILE '))
        self.assertEqual(profile['visibility']['adapter_payload'], 'pipe_boundary_model_fields')
        self.assertIsNone(profile['usage']['prompt_tokens'])
        self.assertEqual(emitter.await_args.args[0]['type'], 'status')

    def test_profile_output_failure_does_not_block_model(self):
        users = types.ModuleType('open_webui.models.users')
        users.Users = types.SimpleNamespace(get_user_by_id=AsyncMock(return_value=object()))
        chat = types.ModuleType('open_webui.utils.chat')
        chat.generate_chat_completion = AsyncMock(return_value='Antwort')
        emitter = AsyncMock(side_effect=RuntimeError('PRIVATE_ERROR'))
        self.pipe.valves.PROMPT_PROFILE = True
        import contextlib
        import io
        log = io.StringIO()
        with patch.dict(sys.modules, {'open_webui.models.users': users, 'open_webui.utils.chat': chat}), \
             contextlib.redirect_stderr(log):
            answer = asyncio.run(self.pipe._forward({'model': 'direct', 'messages': []}, object(),
                                                   {'id': 'u'}, {}, emitter))
        self.assertEqual(answer, 'Antwort')
        self.assertNotIn('PRIVATE_ERROR', log.getvalue())

    def test_plain_profile_is_readable_without_json_or_content(self):
        with patch.object(self.pipe, '_forward', new_callable=AsyncMock) as forward:
            answer = self.call('Prompt-Profil')
        forward.assert_not_awaited()
        self.assertIn('| Reihenfolge | Rolle |', answer)
        self.assertIn('Exakte Wiederholungen:', answer)
        self.assertIn('Prompt-Profil JSON', answer)
        self.assertNotIn('```json', answer)
        self.assertNotIn('Interne Regeln', answer)


if __name__ == '__main__':
    unittest.main()
