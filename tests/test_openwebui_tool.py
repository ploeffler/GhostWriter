"""GitHub-Werkzeug mit simulierten Antworten, ohne Token und Netzwerkzugriff prüfen."""
import asyncio
import base64
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import AsyncMock, patch

try:
    import pydantic
except ImportError:
    pydantic = None


@unittest.skipIf(pydantic is None, "Optionale Open-WebUI-Abhängigkeit pydantic fehlt")
class OpenWebUIToolTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "integrations/openwebui/ghostwriter_github.py"
        spec = importlib.util.spec_from_file_location("ghostwriter_openwebui", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.tool = self.module.Tools()
        self.tool.valves.GITHUB_TOKEN = "TEST_TOKEN_NO_CREDENTIAL"
        self.tool.valves.ALLOWED_REPOS = "owner/book"
        self.state = tempfile.TemporaryDirectory()
        self.addCleanup(self.state.cleanup)
        self.tool.valves.START_STATE_DIR = self.state.name
        self.head = "a" * 40

    def run_tool(self, coroutine):
        return json.loads(asyncio.run(coroutine))

    def test_url_and_debug_without_token(self):
        class Response:
            status_code = 200
            headers = {"X-GitHub-Request-Id": "example"}
            content = b"{}"
            def json(self):
                return {"full_name": "owner/book", "default_branch": "main"}
        self.tool.valves.DEBUG = True
        with patch.object(self.module.requests, "request", return_value=Response()) as request:
            result = self.run_tool(self.tool.get_repo("owner/book"))
        self.assertTrue(result["ok"])
        self.assertEqual(request.call_args.args[1], "https://api.github.com/repos/owner/book")
        self.assertEqual(result["debug"][0]["status"], 200)
        self.assertNotIn(self.tool.valves.GITHUB_TOKEN, json.dumps(result))

    def test_disallowed_repo_never_calls_network(self):
        with patch.object(self.module.requests, "request") as request:
            result = self.run_tool(self.tool.get_repo("other/book"))
        self.assertFalse(result["ok"])
        request.assert_not_called()

    def test_conflict_never_uploads(self):
        with patch.object(self.tool, "_http", return_value={"object": {"sha": "b" * 40}}) as http:
            result = self.run_tool(self.tool.commit_files("owner/book", "ghostwriter/buch/test", '[{"path":"a.md","content":"Text"}]', "Text geändert", self.head))
        self.assertFalse(result["ok"])
        self.assertEqual(http.call_count, 1)

    def test_multifile_commit_one_commit_no_force(self):
        replies = [{"object": {"sha": self.head}}, {"tree": {"sha": "old-tree"}},
                   {"sha": "blob1"}, {"sha": "blob2"}, {"sha": "new-tree"},
                   {"sha": "new-commit"}, {"object": {"sha": self.head}}, {}]
        files = json.dumps([{"path": "a.md", "content": "A"}, {"path": "b.md", "content": "B"}])
        with patch.object(self.tool, "_http", side_effect=replies) as http:
            result = self.run_tool(self.tool.commit_files("owner/book", "ghostwriter/buch/test", files, "Text geändert", self.head))
        self.assertTrue(result["ok"])
        commits = [c for c in http.call_args_list if c.args[1] == "POST" and c.args[2].endswith("/git/commits")]
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].kwargs["data"]["parents"], [self.head])
        self.assertEqual(http.call_args_list[-1].kwargs["data"], {"sha": "new-commit", "force": False})

    def test_unchanged_tree_no_commit(self):
        replies = [{"object": {"sha": self.head}}, {"tree": {"sha": "same"}}, {"sha": "blob"}, {"sha": "same"}]
        with patch.object(self.tool, "_http", side_effect=replies) as http:
            result = self.run_tool(self.tool.commit_files("owner/book", "ghostwriter/buch/test", '[{"path":"a.md","content":"A"}]', "Text geändert", self.head))
        self.assertFalse(result["result"]["changed"])
        self.assertFalse(any(c.args[1] == "PATCH" for c in http.call_args_list))

    def test_changed_head_before_publish_no_patch(self):
        replies = [{"object": {"sha": self.head}}, {"tree": {"sha": "old"}}, {"sha": "blob"},
                   {"sha": "new"}, {"sha": "commit"}, {"object": {"sha": "b" * 40}}]
        with patch.object(self.tool, "_http", side_effect=replies) as http:
            result = self.run_tool(self.tool.commit_files("owner/book", "ghostwriter/buch/test", '[{"path":"a.md","content":"A"}]', "Text geändert", self.head))
        self.assertFalse(result["ok"])
        self.assertFalse(any(c.args[1] == "PATCH" for c in http.call_args_list))

    def test_merge_false_is_failure(self):
        with patch.object(self.tool, "_http", return_value={"merged": False}):
            result = self.run_tool(self.tool.merge_pull_request("owner/book", 1, self.head))
        self.assertFalse(result["ok"])

    def test_branch_pagination(self):
        page = [{"name": "main", "commit": {"sha": self.head}}] * 100
        with patch.object(self.tool, "_http", side_effect=[page, []]) as http:
            result = self.run_tool(self.tool.get_branches("owner/book"))
        self.assertEqual(len(result["result"]), 100)
        self.assertEqual(http.call_args_list[1].args[3]["page"], 2)

    def test_workflow_allowlist(self):
        self.tool.valves.ALLOW_WORKFLOW_DISPATCH = True
        with patch.object(self.tool, "_http") as http:
            result = self.run_tool(self.tool.dispatch_workflow("owner/book", "convert.yml", "main"))
        self.assertFalse(result["ok"])
        http.assert_not_called()

    def start(self, tool=None, chat="chat-1", user="user-1", messages=None, metadata=None):
        return (tool or self.tool).read_start_md(__chat_id__=chat, __user__={"id": user},
                                                __messages__=messages if messages is not None else [],
                                                __metadata__=metadata or {})

    def start_response(self, text="# Kurzer Einstieg\nBibliothek und Übersicht lesen."):
        return {"type": "file", "sha": self.head, "encoding": "base64", "size": len(text.encode()),
                "content": base64.b64encode(text.encode()).decode()}

    def start_http(self, trace, method, path, params=None, **kwargs):
        self.assertEqual(method, "GET", "Einstieg darf keine Schreibzugriffe auslösen")
        if path.endswith("/contents/START.md"):
            return self.start_response()
        if path.endswith("/contents/library.json"):
            return self.start_response(json.dumps({"books": [
                {"branch": "buch/erstes", "title": "Erstes Buch", "status": "ready", "chapters_total": 15, "sections_total": 45},
                {"branch": "buch/zweites", "title": "Zweites Buch", "status": "setup", "chapters_total": 0, "sections_total": 0}]}))
        return {"default_branch": "main"}

    def test_start_first_read_then_short_status_without_network(self):
        with patch.object(self.tool, "_http", side_effect=self.start_http) as http:
            first = self.run_tool(self.start())
            self.assertTrue(first["ok"], first)
            self.assertTrue(first["result"]["fetched"])
            self.assertEqual(http.call_count, 3)
            self.assertIn("| 1 | Erstes Buch | 15 | 45 | eingerichtet |", first["result"]["view"])
            self.assertEqual(first["result"]["books"][1]["branch"], "buch/zweites")
            history = [{"role": "tool", "content": json.dumps(first)}]
            second = self.run_tool(self.start(messages=history))
            self.assertTrue(second["ok"], second)
            self.assertTrue(second["result"]["already_loaded"])
            self.assertFalse(second["result"]["context_restored"])
            self.assertNotIn("content", second["result"])
            self.assertNotIn("view", second["result"])
            self.assertEqual(http.call_count, 3)

    def test_start_survives_new_tools_instance_and_restores_lost_context(self):
        with patch.object(self.tool, "_http", side_effect=self.start_http):
            first = self.run_tool(self.start())
        replacement = self.module.Tools()
        replacement.valves = self.tool.valves
        with patch.object(replacement, "_http") as http:
            restored = self.run_tool(self.start(tool=replacement))
        self.assertTrue(restored["result"]["context_restored"])
        self.assertFalse(restored["result"]["fetched"])
        self.assertEqual(restored["result"]["content"], first["result"]["content"])
        http.assert_not_called()

    def test_start_users_chats_repositories_branches_and_tokens_are_isolated(self):
        with patch.object(self.tool, "_http", side_effect=self.start_http) as http:
            self.assertTrue(self.run_tool(self.start())["ok"])
            self.assertTrue(self.run_tool(self.start(chat="chat-2"))["result"]["fetched"])
            self.assertTrue(self.run_tool(self.start(user="user-2"))["result"]["fetched"])
            self.tool.valves.ALLOWED_REPOS = "owner/book,owner/other"
            self.tool.valves.START_REPO = "owner/other"
            self.assertTrue(self.run_tool(self.start())["result"]["fetched"])
            self.tool.valves.START_REPO = "owner/book"
            self.tool.valves.START_BRANCH = "buch/test"
            self.assertTrue(self.run_tool(self.start())["result"]["fetched"])
            self.assertTrue(any(c.args[2].endswith("/contents/START.md") and c.args[3] == {"ref": "buch/test"}
                                for c in http.call_args_list))
            self.assertEqual(http.call_args.args[3], {"ref": "main"}, "Bibliothek kommt auch auf Buchbranches vom Standard-Branch")
            self.tool.valves.START_BRANCH = ""
            self.tool.valves.GITHUB_TOKEN = "ANOTHER_TEST_PLACEHOLDER"
            self.assertTrue(self.run_tool(self.start())["result"]["fetched"])
            # Jede Initialisierung liest START.md und die Bibliotheksdatei.
            self.assertEqual(http.call_count, 18)

    def test_missing_identity_or_ambiguous_repository_never_fetches(self):
        with patch.object(self.tool, "_http") as http:
            self.assertFalse(self.run_tool(self.start(chat=None))["ok"])
            self.assertFalse(self.run_tool(self.start(user=None))["ok"])
            self.tool.valves.ALLOWED_REPOS = "owner/book,owner/other"
            self.assertFalse(self.run_tool(self.start())["ok"])
        http.assert_not_called()

    def test_failed_initialization_can_be_retried(self):
        with patch.object(self.tool, "_http", side_effect=ValueError("GitHub HTTP 403")):
            self.assertFalse(self.run_tool(self.start())["ok"])
        with patch.object(self.tool, "_http", side_effect=self.start_http):
            success = self.run_tool(self.start())
        self.assertTrue(success["result"]["fetched"])

    def test_start_reload_requires_exact_user_command_and_only_once_per_message(self):
        with patch.object(self.tool, "_http", side_effect=self.start_http) as http:
            first = self.run_tool(self.start())
            ordinary = {"user_message": {"content": "Bibliothek"}, "user_message_id": "message-2"}
            second = self.run_tool(self.start(metadata=ordinary))
            self.assertFalse(second["result"]["fetched"])
            meta = {"user_message": {"content": "Start neu laden"}, "user_message_id": "message-3"}
            refreshed = self.run_tool(self.start(metadata=meta))
            self.assertTrue(refreshed["result"]["fetched"])
            repeated = self.run_tool(self.start(metadata=meta, messages=[{"role": "tool", "content": json.dumps(refreshed)}]))
            self.assertFalse(repeated["result"]["fetched"])
            self.assertNotIn("content", repeated["result"])
            self.assertEqual(http.call_count, 6)

    def test_start_rejects_long_source_and_does_not_persist_token(self):
        self.tool.valves.MAX_START_BYTES = 1024
        for content in ("x" * 1100, self.tool.valves.GITHUB_TOKEN):
            with self.subTest(content_length=len(content)):
                with patch.object(self.tool, "_http", side_effect=[{"default_branch": "main"}, self.start_response(content)]):
                    result = self.run_tool(self.start())
                self.assertFalse(result["ok"], result)
                self.assertNotIn(self.tool.valves.GITHUB_TOKEN, json.dumps(result))
        data = Path(self.state.name, "startup.sqlite3").read_bytes()
        self.assertNotIn(self.tool.valves.GITHUB_TOKEN.encode(), data)

    def test_user_quote_is_not_a_loaded_tool_result(self):
        with patch.object(self.tool, "_http", side_effect=self.start_http) as http:
            first = self.run_tool(self.start())
            result = self.run_tool(self.start(messages=[{"role": "user", "content": json.dumps(first)}]))
            self.assertTrue(result["result"]["context_restored"])
            self.assertEqual(http.call_count, 3)

    def test_parallel_calls_fetch_only_once_across_tool_instances(self):
        replacement = self.module.Tools()
        replacement.valves = self.tool.valves
        async def run():
            return await asyncio.gather(self.start(), self.start(tool=replacement), self.start())
        with patch.object(self.tool, "_http", side_effect=self.start_http) as first_http, \
             patch.object(replacement, "_http", side_effect=self.start_http) as second_http:
            results = [json.loads(value) for value in asyncio.run(run())]
        self.assertTrue(all(value["ok"] for value in results), results)
        self.assertEqual(sum(value["result"]["fetched"] for value in results), 1)
        self.assertEqual(first_http.call_count + second_http.call_count, 3)

    def test_library_is_fresh_and_uses_default_branch_independent_of_start_branch(self):
        self.tool.valves.START_BRANCH = "buch/erstes"
        libraries = [{"books": [{"branch": "buch/erstes", "title": title, "chapters_total": 2, "sections_total": 3}]}
                     for title in ("Vorher", "Nachher")]
        with patch.object(self.tool, "_http", side_effect=[{"default_branch": "stable"}, self.start_response(json.dumps(libraries[0])),
                                                         {"default_branch": "stable"}, self.start_response(json.dumps(libraries[1]))]) as http:
            first = self.run_tool(self.tool.show_library())
            second = self.run_tool(self.tool.show_library())
        self.assertTrue(first["ok"], first)
        self.assertTrue(second["ok"], second)
        self.assertIn("Nachher", second["result"]["view"])
        self.assertNotIn("Vorher", second["result"]["view"])
        self.assertEqual(http.call_count, 4)
        self.assertEqual(http.call_args.args[3], {"ref": "stable"})

    def test_empty_library_is_not_an_error_and_single_book_remains_a_library(self):
        for books in ([], [{"branch": "buch/einzeln", "title": "Ein Buch"}]):
            with self.subTest(books=len(books)), patch.object(self.tool, "_http", side_effect=[{"default_branch": "main"}, self.start_response(json.dumps({"books": books}))]):
                result = self.run_tool(self.tool.show_library())
            self.assertTrue(result["ok"], result)
            self.assertIn("Bibliothek", result["result"]["view"])
            if books:
                self.assertIn("| 1 | Ein Buch | – | – |", result["result"]["view"])
            else:
                self.assertIn("Noch keine Bücher", result["result"]["view"])

    def test_invalid_or_missing_library_does_not_become_empty_or_zero_values(self):
        examples = ({}, {"books": {}}, {"books": [0]}, {"books": [{"title": "Kein Branch"}]},
                    {"books": [{"branch": "buch/a", "chapters_total": []}]},
                    {"books": [{"branch": "buch/a", "title": ["Kein Text"]}]},
                    {"books": [{"branch": "buch/a", "title": 0}]},
                    {"books": [{"branch": "buch/a"}, {"branch": "buch/a"}]})
        for data in examples:
            with self.subTest(data=data), patch.object(self.tool, "_http", side_effect=[{"default_branch": "main"}, self.start_response(json.dumps(data))]):
                result = self.run_tool(self.tool.show_library())
            self.assertFalse(result["ok"], result)
            self.assertNotIn("view", result)
            self.assertNotIn("Noch keine Bücher", json.dumps(result))
        with patch.object(self.tool, "_http", side_effect=ValueError("GitHub HTTP 404")):
            result = self.run_tool(self.tool.show_library())
        self.assertFalse(result["ok"])

    def test_start_reports_library_failure_and_library_can_be_retried(self):
        with patch.object(self.tool, "_http", side_effect=[{"default_branch": "main"}, self.start_response(), ValueError("GitHub HTTP 404")]):
            result = self.run_tool(self.start())
        self.assertTrue(result["ok"], result)
        self.assertIn("library_error", result["result"])
        self.assertNotIn("view", result["result"])
        with patch.object(self.tool, "_http", side_effect=self.start_http):
            retry = self.run_tool(self.tool.show_library())
        self.assertTrue(retry["ok"])
        self.assertIn("Erstes Buch", retry["result"]["view"])

    def test_library_escapes_table_data_and_supports_english_without_translating_titles(self):
        self.tool.valves.INTERFACE_LANGUAGE = "en"
        data = {"books": [{"branch": "buch/test", "title": "Buch | [Titel]\nZweite Zeile", "status": "ready", "pending": 2}]}
        with patch.object(self.tool, "_http", side_effect=[{"default_branch": "main"}, self.start_response(json.dumps(data))]):
            result = self.run_tool(self.tool.show_library())
        self.assertTrue(result["ok"], result)
        self.assertIn("Library", result["result"]["view"])
        self.assertIn(r"Buch \| \[Titel\] Zweite Zeile", result["result"]["view"])
        self.assertIn("2 pending changes", result["result"]["view"])
        self.assertEqual(result["result"]["books"][0]["title"], data["books"][0]["title"])

    def test_cached_start_still_requires_repository_permission(self):
        with patch.object(self.tool, "_http", side_effect=self.start_http):
            self.run_tool(self.start())
        self.tool.valves.START_REPO = "owner/book"
        self.tool.valves.ALLOWED_REPOS = "other/book"
        with patch.object(self.tool, "_http") as http:
            result = self.run_tool(self.start())
        self.assertFalse(result["ok"])
        self.assertNotIn("content", result)
        http.assert_not_called()

    def navigation_fixture(self):
        self.nav_head = self.head
        self.nav_work = None
        self.nav_pulls = []
        self.nav_books = [
            {"branch": "buch/erstes", "title": "Erstes Buch", "status": "ready", "chapters_total": 15, "sections_total": 45},
            {"branch": "buch/zweites", "title": "Zweites Buch", "status": "ready"}]
        self.nav_config = {"project": {"title": "Tatsächlicher Buchtitel", "author": "Testautor"}, "structure": {"chapters": [
            {"id": "ch-1", "title": "Erstes Kapitel", "path": "chapters/01-erstes", "status": "in_progress", "sections": [
                {"id": "sec-1", "title": "Erster Abschnitt", "path": "chapters/01-erstes/sections/01.md"}]},
            {"id": "ch-2", "title": "Zweites Kapitel", "path": "chapters/02-zweites", "status": "planned", "sections": [{"id": "sec-2", "title": "Zweiter Abschnitt", "path": "chapters/02-zweites/sections/01.md"}]}]}}

    def navigation_http(self, trace, method, path, params=None, **kw):
        self.assertEqual(method, "GET", "Navigation darf keine Schreibzugriffe ausführen")
        if path.endswith('/contents/START.md'):
            return self.start_response()
        if path.endswith('/contents/library.json'):
            return self.start_response(json.dumps({'books': self.nav_books}))
        if path.endswith('/branches'):
            values = [{'name': b['branch'], 'commit': {'sha': self.nav_head}} for b in self.nav_books]
            if self.nav_work:
                values.append({'name': 'ghostwriter/buch/erstes', 'commit': {'sha': self.nav_work}})
            return values
        if path.endswith('/pulls'):
            return self.nav_pulls
        if path.endswith('/contents/workflow.yml'):
            self.assertIn(params['ref'], [self.nav_head, self.nav_work])
            return self.start_response((Path(__file__).resolve().parents[1] / 'workflow.yml').read_text())
        if path.endswith('/contents/ghostwriter.yml'):
            self.assertIn(params['ref'], [self.nav_head, self.nav_work])
            return self.start_response(self.module.yaml.safe_dump(self.nav_config))
        if '/contents/chapters/' in path:
            self.assertIn(params['ref'], [self.nav_head, self.nav_work])
            return self.start_response('---\nstatus: writing\n---\n## Manuskript\nNur dieser eine Abschnitt.')
        return {'default_branch': 'main'}

    def receipt(self, branches=None):
        scope = self.tool._navigation_scope('owner/book', 'chat-1', {'id': 'user-1'}, {}, None)
        view = self.tool._navigation_view({'view': 'Bibliothek'},
            {'kind': 'library', 'branches': branches or ['buch/erstes', 'buch/zweites'], 'sha': self.head}, scope)
        return view['navigation_receipt']

    def open_navigation(self, selection, receipt, chat='chat-1', user='user-1'):
        return self.run_tool(self.tool.open_book(selection, receipt, __chat_id__=chat, __user__={'id': user}))

    def test_book_number_uses_displayed_branch_even_after_library_reordering(self):
        self.navigation_fixture()
        receipt = self.receipt()
        self.nav_books.reverse()
        with patch.object(self.tool, '_http', side_effect=self.navigation_http):
            result = self.open_navigation('1', receipt)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['result']['book_branch'], 'buch/erstes')
        self.assertEqual(result['result']['branch'], 'buch/erstes')
        self.assertIn('Tatsächlicher Buchtitel', result['result']['view'])
        self.assertIn('| 1 | Erstes Kapitel | 1 |', result['result']['view'])
        self.assertNotIn('Nur dieser eine Abschnitt', result['result']['view'])

    def test_book_uses_only_matching_open_work_pr_and_pins_file_reads(self):
        self.navigation_fixture()
        self.nav_work = 'b' * 40
        pr = {'number': 7, 'base': {'ref': 'buch/erstes'},
              'head': {'ref': 'ghostwriter/buch/erstes', 'sha': self.nav_work, 'repo': {'full_name': 'owner/book'}}}
        self.nav_pulls = [pr]
        with patch.object(self.tool, '_http', side_effect=self.navigation_http) as http:
            result = self.open_navigation('Buch 1', self.receipt())
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['result']['sha'], self.nav_work)
        self.assertIn('Noch nicht übernommene Änderungen · PR #7', result['result']['view'])
        cfg_call = next(c for c in http.call_args_list if c.args[2].endswith('/contents/ghostwriter.yml'))
        self.assertEqual(cfg_call.args[3], {'ref': self.nav_work})
        self.nav_pulls = [{**pr, 'head': {**pr['head'], 'repo': {'full_name': 'other/book'}}}]
        with patch.object(self.tool, '_http', side_effect=self.navigation_http):
            result = self.open_navigation('1', self.receipt())
        self.assertEqual(result['result']['branch'], 'buch/erstes')

    def test_receipt_tampering_cross_session_and_invalid_numbers_never_open(self):
        self.navigation_fixture()
        receipt = self.receipt()
        with patch.object(self.tool, '_http') as http:
            self.assertFalse(self.open_navigation('1', receipt + 'a')['ok'])
            self.assertFalse(self.open_navigation('1', receipt, chat='other-chat')['ok'])
            self.assertFalse(self.open_navigation('1', receipt, user='other-user')['ok'])
            self.assertFalse(self.open_navigation('9', receipt)['ok'])
            self.assertFalse(self.open_navigation('Freigeben', receipt)['ok'])
            http.assert_not_called()

    def test_deleted_book_does_not_select_new_book_at_same_number(self):
        self.navigation_fixture()
        self.nav_books.pop(0)
        with patch.object(self.tool, '_http', side_effect=self.navigation_http) as http:
            result = self.open_navigation('1', self.receipt())
        self.assertFalse(result['ok'], result)
        self.assertFalse(any(c.args[2].endswith('/contents/ghostwriter.yml') for c in http.call_args_list))

    def test_changed_head_refreshes_overview_instead_of_reusing_chapter_number(self):
        self.navigation_fixture()
        with patch.object(self.tool, '_http', side_effect=self.navigation_http):
            book = self.open_navigation('1', self.receipt())['result']
            self.nav_head = 'c' * 40
            self.nav_config['structure']['chapters'].reverse()
            result = self.open_navigation('1', book['navigation_receipt'])
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['result']['changed'])
        self.assertEqual(result['result']['chapter'], 0)
        self.assertIn('inzwischen geändert', result['result']['view'])

    def test_chapter_table_and_single_section_are_read_from_same_commit(self):
        self.navigation_fixture()
        with patch.object(self.tool, '_http', side_effect=self.navigation_http) as http:
            book = self.open_navigation('1', self.receipt())['result']
            chapter = self.open_navigation('Kapitel 1', book['navigation_receipt'])['result']
            section = self.open_navigation('1', chapter['navigation_receipt'])['result']
            overview = self.open_navigation('Übersicht', section['navigation_receipt'])['result']
        self.assertIn('| 1.1 | Erster Abschnitt | Entwurf |', chapter['view'])
        self.assertNotIn('Nur dieser eine Abschnitt', chapter['view'])
        self.assertEqual(section['section'], 1)
        self.assertEqual(section['view'].count('Nur dieser eine Abschnitt'), 1)
        self.assertEqual(overview['chapter'], 0)
        pinned = [c.args[3]['ref'] for c in http.call_args_list if '/contents/chapters/' in c.args[2]]
        self.assertTrue(pinned)
        self.assertEqual(set(pinned), {self.head})

    def test_path_outside_section_directory_is_rejected(self):
        self.navigation_fixture()
        self.nav_config['structure']['chapters'][0]['sections'][0]['path'] = '.env'
        with patch.object(self.tool, '_http', side_effect=self.navigation_http) as http:
            book = self.open_navigation('1', self.receipt())['result']
            result = self.open_navigation('Abschnitt 1.1', book['navigation_receipt'])
        self.assertFalse(result['ok'])
        self.assertFalse(any('/contents/.env' in c.args[2] for c in http.call_args_list))

    def current_context(self, receipt, **kwargs):
        return self.run_tool(self.tool.get_current_context(receipt, __chat_id__='chat-1',
                             __user__={'id': 'user-1'}, **kwargs))

    def test_fresh_conversation_context_has_separate_statuses_and_one_selected_section(self):
        self.navigation_fixture()
        with patch.object(self.tool, '_http', side_effect=self.navigation_http):
            book = self.open_navigation('1', self.receipt())['result']
            context = self.current_context(book['navigation_receipt'])['result']['conversation_context']
            self.assertEqual(context['level'], 'book')
            self.assertEqual(context['chapters'][0]['status'], 'in_progress')
            self.assertIn('assembly', context['status_rules']['chapter']['statuses'])
            self.assertNotIn('writing', context['status_rules']['chapter']['statuses'])
            self.assertIn('writing', context['status_rules']['section']['statuses'])
            self.assertTrue(context['status_rules']['section']['transitions'])
            chapter = self.open_navigation('Kapitel 1', book['navigation_receipt'])['result']
            data = self.current_context(chapter['navigation_receipt'])['result']
            self.assertEqual(data['conversation_context']['chapter']['number'], 1)
            self.assertEqual(data['conversation_context']['sections'][0]['number'], '1.1')
            self.assertNotIn('Nur dieser eine Abschnitt', data['view'])
            section = self.open_navigation('1', chapter['navigation_receipt'])['result']
            data = self.current_context(section['navigation_receipt'])['result']
            self.assertEqual(data['conversation_context']['level'], 'section')
            self.assertEqual(data['conversation_context']['section']['status'], 'writing')
            self.assertEqual(data['view'].count('Nur dieser eine Abschnitt'), 1)

    def test_context_refreshes_on_changed_head_and_rejects_tampered_receipt(self):
        self.navigation_fixture()
        with patch.object(self.tool, '_http', side_effect=self.navigation_http):
            book = self.open_navigation('1', self.receipt())['result']
            chapter = self.open_navigation('Kapitel 1', book['navigation_receipt'])['result']
            self.nav_head = 'c' * 40
            context = self.current_context(chapter['navigation_receipt'])['result']
            self.assertTrue(context['changed'])
            self.assertEqual(context['conversation_context']['level'], 'book')
        with patch.object(self.tool, '_http') as http:
            self.assertFalse(self.current_context(chapter['navigation_receipt'] + 'x')['ok'])
            http.assert_not_called()

    def test_start_number_book_chapter_section_path_without_any_model_call(self):
        from functools import partial
        self.navigation_fixture()
        path = Path(__file__).resolve().parents[1] / 'integrations/openwebui/ghostwriter_direct.py'
        spec = importlib.util.spec_from_file_location('navigation_pipe', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        pipe = module.Pipe()
        pipe._state_dir = Path(self.state.name)
        tools = {name: {'tool_id': 'github', 'spec': {'name': name}, 'callable': partial(getattr(self.tool, name),
                         __chat_id__='chat-1', __user__={'id': 'user-1'}, __id__='github')}
                 for name in ['read_start_md', 'show_library', 'open_book', 'get_current_context']}
        messages = []
        outputs = []
        with patch.object(self.tool, '_http', side_effect=self.navigation_http), patch.object(pipe, '_forward', new_callable=AsyncMock) as forward:
            for command in ['Start', '1', '1', '1', 'Übersicht', 'Buch 2']:
                messages.append({'role': 'user', 'content': command})
                output = asyncio.run(pipe.pipe({'model': 'direct', 'messages': messages}, __tools__=tools, __user__={'id': 'user-1'}, __metadata__={'chat_id': 'chat-1'}))
                messages.append({'role': 'assistant', 'content': output})
                outputs.append(output)
            forward.assert_not_awaited()
        self.assertNotIn('ghostwriter-nav:', '\n'.join(outputs))
        self.assertNotIn('Lesestand:', '\n'.join(outputs))
        self.assertIn('Herzlich willkommen', outputs[0])
        self.assertIn('| 1 | Erstes Kapitel |', outputs[1])
        self.assertIn('| 1.1 | Erster Abschnitt |', outputs[2])
        self.assertIn('Nur dieser eine Abschnitt', outputs[3])
        section_messages = messages[:8] + [{'role': 'user', 'content': 'Kontext prüfen'}]
        request = type('Request', (), {'app': type('App', (), {'state': type('State', (), {'MODELS': {'llama3.2:3b': {'owned_by': 'ollama'}}})()})()})()
        with patch.object(self.tool, '_http', side_effect=self.navigation_http), patch.object(pipe, '_forward', new_callable=AsyncMock) as forward:
            diagnostic = asyncio.run(pipe.pipe({'model': 'direct', 'num_ctx': 32768, 'messages': section_messages}, __tools__=tools,
                                 __user__={'id': 'user-1'}, __metadata__={'chat_id': 'chat-1'}, __request__=request))
        forward.assert_not_awaited()
        self.assertIn('Erster Abschnitt', diagnostic)
        self.assertIn('num_ctx: 32768', diagnostic)
        self.assertIn('Abschnittsansicht im Modellkontext: ja', diagnostic)
        self.assertNotIn('Nur dieser eine Abschnitt', diagnostic)
        self.assertNotIn('ghostwriter-nav', diagnostic)

        self.assertIn('| 1 | Erstes Kapitel |', outputs[4])
        self.assertNotIn('✗', '\n'.join(outputs))
        messages.append({'role': 'user', 'content': 'Was sollte ich bei Kapitel 1 beachten?'})
        with patch.object(self.tool, '_http', side_effect=self.navigation_http), patch.object(pipe, '_forward', new_callable=AsyncMock, return_value='Antwort mit Kontext') as forward:
            answer = asyncio.run(pipe.pipe({'model': 'direct', 'messages': messages}, __tools__=tools,
                                 __user__={'id': 'user-1'}, __metadata__={'chat_id': 'chat-1'}))
        self.assertEqual(answer, 'Antwort mit Kontext')
        context_message = forward.await_args.args[0]['messages'][-2]
        facts = json.loads(context_message['content'].split('Aktueller Kontext / Current context:\n')[1])
        self.assertEqual(facts['book_branch'], 'buch/zweites')
        self.assertEqual(facts['chapters'][0]['number'], 1)
        self.assertEqual(facts['chapters'][0]['status'], 'in_progress')
        self.assertIn('assembly', facts['status_rules']['chapter']['statuses'])
        self.assertNotIn('ghostwriter-nav:', context_message['content'])
        messages.append({'role': 'assistant', 'content': answer})
        messages.append({'role': 'user', 'content': 'Welche Statuswerte kann Kapitel 1 haben?'})
        with patch.object(self.tool, '_http', side_effect=self.navigation_http), patch.object(pipe, '_forward', new_callable=AsyncMock) as forward:
            answer = asyncio.run(pipe.pipe({'model': 'direct', 'messages': messages}, __tools__=tools,
                                 __user__={'id': 'user-1'}, __metadata__={'chat_id': 'chat-1'}))
        forward.assert_not_awaited()
        self.assertIn('`ready_for_assembly`', answer)
        self.assertIn('`approved`', answer)
        self.assertNotIn('`completed`', answer)
        self.assertNotIn('`cancelled`', answer)




if __name__ == "__main__":
    unittest.main()
