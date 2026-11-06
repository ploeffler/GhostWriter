"""GitHub-Werkzeug mit simulierten Antworten, ohne Token und Netzwerkzugriff prüfen."""
import asyncio
import base64
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
