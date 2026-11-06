"""
title: GhostWriter GitHub
description: GitHub lesen und Aufgaben als gemeinsamen Commit speichern.
version: 1.2.0
requirements: requests,pydantic
"""
import asyncio
import base64
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        GITHUB_TOKEN: str = Field(
            default="", description="GitHub-Token; niemals als Tool-Argument übergeben.",
            json_schema_extra={"input": {"type": "password"}},
        )
        ALLOWED_REPOS: str = Field(default="", description="Erlaubte owner/repo, durch Komma getrennt. Leer sperrt alle Zugriffe.")
        START_REPO: str = Field(default="", description="Repository für read_start_md; bei genau einem erlaubten Repository optional.")
        START_BRANCH: str = Field(default="", description="Branch für den Einstieg; leer verwendet den tatsächlichen Standard-Branch.")
        INTERFACE_LANGUAGE: Literal["de", "en"] = Field(default="de", description="Sprache der fertigen Bibliotheksansicht.")
        START_STATE_DIR: str = Field(default="/app/backend/data/ghostwriter", description="Persistenter Startzustand je Benutzer und Chat im Open-WebUI-Datenvolume.")
        MAX_START_BYTES: int = Field(default=16384, ge=1024, le=65536, description="Maximale Größe des kurzen Instanz-Einstiegs. Vollständige START.md vorher per GhostWriter-Update kürzen lassen.")
        DEBUG: bool = Field(default=False, description="HTTP-Status, Dauer und Request-ID ausgeben; keine Header oder Dateiinhalte.")
        TIMEOUT: int = Field(default=30, ge=5, le=120)
        MAX_FILE_BYTES: int = Field(default=1000000, ge=1024, le=1000000)
        ALLOW_WORKFLOW_DISPATCH: bool = Field(default=False, description="Start von GitHub Actions erlauben.")

    def __init__(self):
        self.valves = self.Valves()

    def _repo(self, repo):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("repo muss owner/repo sein, keine URL.")
        allowed = {v.strip().lower() for v in self.valves.ALLOWED_REPOS.split(",") if v.strip()}
        if repo.lower() not in allowed:
            raise ValueError("Repository ist nicht im Valve ALLOWED_REPOS freigegeben.")
        return "/repos/" + repo

    def _instance_repo(self):
        if not self.valves.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN im Valve fehlt.")
        allowed = {v.strip() for v in self.valves.ALLOWED_REPOS.split(",") if v.strip()}
        repo = self.valves.START_REPO.strip()
        if not repo and len(allowed) == 1:
            repo = next(iter(allowed))
        if not repo:
            raise ValueError("START_REPO im Valve festlegen; mehrere oder keine Repositorys freigegeben.")
        self._repo(repo)
        return repo

    def _library_view(self, trace, repo, default_branch=None):
        """Liest bei jedem Aufruf neu; Buchdaten werden nie im Startzustand gespeichert."""
        branch = default_branch or self._http(trace, "GET", self._repo(repo))["default_branch"]
        data = self._read_utf8(trace, repo, "library.json", branch)
        library = json.loads(data["content"])
        if not isinstance(library, dict) or not isinstance(library.get("books"), list):
            raise ValueError("library.json enthält keine gültige Bücherliste; Bibliothek nicht angezeigt.")
        english = self.valves.INTERFACE_LANGUAGE == "en"
        def cell(value):
            text = str(value).replace("\r", " ").replace("\n", " ").replace("\\", "\\\\")
            return re.sub(r"([|\[\]*_`<>])", r"\\\1", text)
        def count(book, key):
            value = book.get(key)
            if value is None:
                return "–"
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"library.json: ungültiger Wert für {key}; Bibliothek nicht angezeigt.")
            return str(value)
        books, rows, branches = [], [], set()
        for number, book in enumerate(library["books"], 1):
            if not isinstance(book, dict) or not isinstance(book.get("branch"), str) or not book["branch"].strip():
                raise ValueError("library.json: Buch ohne gültigen Branch; Bibliothek nicht angezeigt.")
            if book["branch"] in branches:
                raise ValueError("library.json: Buchbranch mehrfach vorhanden; Bibliothek nicht angezeigt.")
            branches.add(book["branch"])
            if any(book.get(key) is not None and not isinstance(book[key], str) for key in ("title", "title_short")):
                raise ValueError("library.json: ungültiger Buchtitel; Bibliothek nicht angezeigt.")
            title = book.get("title") or book.get("title_short") or ("Untitled book" if english else "Unbenanntes Buch")
            state = {"ready": "set up" if english else "eingerichtet",
                     "setup": "in setup" if english else "im Aufbau"}.get(book.get("status"), "unknown" if english else "unbekannt")
            pending = count(book, "pending")
            if pending != "–" and int(pending):
                state += (f" · {pending} pending change" + ("s" if int(pending) != 1 else "")) if english else f" · {pending} offene Änderung" + ("en" if int(pending) != 1 else "")
            rows.append(f"| {number} | {cell(title)} | {count(book, 'chapters_total')} | {count(book, 'sections_total')} | {state} |")
            books.append({"number": number, "title": title, "branch": book["branch"]})
        lines = ["### 📚 " + ("Library" if english else "Bibliothek"), "", cell(repo), ""]
        if rows:
            lines += ["| No. | Book | Chapters | Sections | Status |" if english else "| Nr. | Buch | Kapitel | Abschnitte | Stand |",
                      "|---|---|---|---|---|", *rows, "",
                      "Enter a number to open a book, or `New book`." if english else "Zum Öffnen die Nummer nennen oder `Neues Buch` wählen."]
        else:
            lines.append("No books yet. Choose `New book`." if english else "Noch keine Bücher. Wähle `Neues Buch`.")
        return {"repo": repo, "branch": branch, "path": "library.json", "sha": data["sha"],
                "books": books, "view": "\n".join(lines), "source_kind": "library_index",
                "message": "Die fertige Ansicht aus view unverändert anzeigen. Bücher und Zahlen nicht selbst erfinden. Angaben stammen aus der gelesenen Bibliotheksdatei."}

    async def show_library(self) -> str:
        """Zeigt die echte Bibliothek für START_REPO. Bei „Bibliothek“, „Library“ oder „Home“ aufrufen.
        Liest library.json jedes Mal frisch vom tatsächlichen Standard-Branch, unabhängig von START_BRANCH.
        Die fertige Markdown-Ansicht aus view unverändert anzeigen; books ordnet Nummern zu Branches zu.
        Bei einem Fehler keine leere Liste, Nullwerte oder Beispieldaten erfinden.
        """
        return await self._run(lambda trace: self._library_view(trace, self._instance_repo()))

    def _path(self, path):
        if not path or path.startswith("/") or any(p in ("", ".", "..") for p in path.split("/")):
            raise ValueError("Ungültiger relativer Dateipfad.")
        # Keine Secret-Dateien über dieses Werkzeug lesen oder schreiben.
        if any(p.lower() in (".env", ".aws", ".ssh") or p.lower().startswith(".env.") for p in path.split("/")):
            raise ValueError("Secret-Pfad gesperrt.")
        return quote(path, safe="/")

    def _http(self, trace, method, path, params=None, data=None, expected=(200,)):
        if not self.valves.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN im Valve fehlt.")
        start = time.monotonic()
        try:
            r = requests.request(
                method, "https://api.github.com" + path,
                headers={"Authorization": "Bearer " + self.valves.GITHUB_TOKEN,
                         "Accept": "application/vnd.github+json"},
                params=params, json=data, timeout=self.valves.TIMEOUT,
                allow_redirects=False,
            )
        except requests.RequestException:
            # Exception-Texte können URL/Proxy-Zugangsdaten enthalten.
            raise ValueError("Netzwerkfehler oder Timeout. Bei Schreibzugriff vor Wiederholung den aktuellen Stand prüfen.") from None
        if self.valves.DEBUG:
            trace.append({"method": method, "endpoint": path,
                          "status": r.status_code, "ms": round((time.monotonic()-start)*1000),
                          "request_id": r.headers.get("X-GitHub-Request-Id"),
                          "rate_remaining": r.headers.get("X-RateLimit-Remaining")})
        if r.status_code not in expected:
            hints = {401: "Token ungültig", 403: "Rechte, Rate-Limit oder Branch-Schutz prüfen",
                     404: "Nicht gefunden oder kein Zugriff", 409: "Konflikt: aktuellen Stand neu lesen",
                     422: "Ungültige Eingabe oder Branch inzwischen geändert"}
            raise ValueError(f"GitHub HTTP {r.status_code}: {hints.get(r.status_code, 'Anfrage fehlgeschlagen')}")
        return r.json() if r.content else {}

    def _pages(self, trace, path, params=None):
        result = []
        for page in range(1, 1001):
            items = self._http(trace, "GET", path, {**(params or {}), "per_page": 100, "page": page})
            if not isinstance(items, list):
                raise ValueError("Unerwartete Listen-Antwort.")
            result.extend(items)
            if len(items) < 100:
                return result
        raise ValueError("Liste zu groß; Ergebnis wäre unvollständig.")

    async def _run(self, operation):
        trace = []
        try:
            result = await asyncio.to_thread(operation, trace)
            payload = {"ok": True, "result": result}
        except (ValueError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
            payload = {"ok": False, "error": str(exc)}
        if self.valves.DEBUG:
            payload["debug"] = trace
        # Zusätzliche Absicherung, falls ein Token versehentlich in Eingaben stand.
        output = json.dumps(payload, ensure_ascii=False)
        if self.valves.GITHUB_TOKEN:
            output = output.replace(self.valves.GITHUB_TOKEN, "[TOKEN ENTFERNT]")
        return output

    def _read_utf8(self, trace, repo, path, branch=None, max_bytes=None):
        d = self._http(trace, "GET", self._repo(repo)+"/contents/"+self._path(path),
                       {"ref": branch} if branch else {})
        if not isinstance(d, dict) or d.get("type") != "file":
            raise ValueError("Pfad ist keine normale Datei.")
        limit = self.valves.MAX_FILE_BYTES if max_bytes is None else max_bytes
        if d.get("size", 0) > limit or d.get("encoding") != "base64":
            raise ValueError("Datei zu groß oder Kodierung nicht unterstützt.")
        raw = base64.b64decode(d["content"])
        if len(raw) > limit:
            raise ValueError("Datei zu groß.")
        return {"path": path, "sha": d["sha"], "content": raw.decode("utf-8")}

    def _start_context_present(self, messages, snapshot):
        """Nur vollständige echte Werkzeugergebnisse zählen, keine Benutzerzitate."""
        for message in messages or []:
            if not isinstance(message, dict) or message.get("role") != "tool":
                continue
            content = message.get("content")
            if not isinstance(content, str):
                continue
            try:
                payload = json.loads(content)
            except ValueError:
                continue
            if not isinstance(payload, dict) or payload.get("ok") is not True:
                continue
            result = payload.get("result")
            if (isinstance(result, dict) and result.get("startup_receipt") == snapshot["startup_receipt"]
                    and result.get("content") == snapshot["content"]):
                return True
        return False

    async def read_start_md(self, __chat_id__: Optional[str] = None, __user__: Optional[dict] = None,
                            __metadata__: Optional[dict] = None, __messages__: Optional[list] = None,
                            __id__: Optional[str] = None) -> str:
        """Lädt den kurzen GhostWriter-Einstieg beim Chatbeginn. Keine normalen Parameter nötig.
        Nach erfolgreichem Laden nicht erneut aufrufen. Bereits vorhandene Anweisungen
        ergeben nur einen kurzen Status. Nur die Benutzernachricht „Start neu laden“
        oder „Reload start“ fordert eine neue GitHub-Fassung an. Inhalt intern befolgen,
        nicht als Antwort abschreiben. Chat- und Benutzerkennung liefert Open WebUI.
        """
        def op(trace):
            metadata = __metadata__ or {}
            chat = __chat_id__ or metadata.get("chat_id")
            user = (__user__ or {}).get("id") or metadata.get("user_id")
            if not isinstance(chat, str) or not chat or not isinstance(user, str) or not user:
                raise ValueError("Start nicht geladen: Open WebUI muss Chat-ID und Benutzer-ID bereitstellen.")
            if __chat_id__ and metadata.get("chat_id") and __chat_id__ != metadata["chat_id"]:
                raise ValueError("Widersprüchliche Chat-Kennung; Start nicht geladen.")
            repo = self._instance_repo()
            root = self._repo(repo)  # Freigabe auch bei einem gespeicherten Einstieg erneut prüfen.
            branch = self.valves.START_BRANCH.strip()
            # Getrennte Zustände je Benutzer, Chat, Werkzeug, Repo, Branch und Zugang.
            # Weder Token noch persönliche IDs werden im Zustandsschlüssel gespeichert.
            credential = hashlib.sha256(self.valves.GITHUB_TOKEN.encode()).hexdigest()
            key = hashlib.sha256(json.dumps([user, chat, __id__ or "ghostwriter-github", repo.lower(),
                                             branch, credential]).encode()).hexdigest()
            latest = metadata.get("user_message") or {}
            if not latest and __messages__:
                latest = next((m for m in reversed(__messages__) if m.get("role") == "user"), {})
            command = latest.get("content")
            reload_requested = isinstance(command, str) and command.strip().casefold() in ("start neu laden", "reload start")
            message_id = metadata.get("user_message_id") or latest.get("id")
            if reload_requested and not message_id:
                raise ValueError("Zum ausdrücklichen Neuladen fehlt die Benutzer-Nachrichten-ID von Open WebUI.")
            try:
                state_dir = Path(self.valves.START_STATE_DIR)
                state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                path = state_dir / "startup.sqlite3"
                db = sqlite3.connect(path, timeout=2*self.valves.TIMEOUT+10, isolation_level=None)
                try:
                    path.chmod(0o600)
                    db.execute("CREATE TABLE IF NOT EXISTS startup (scope TEXT PRIMARY KEY, snapshot TEXT NOT NULL)")
                    # Sperre schützt auch mehrere Threads, Tools-Instanzen und Worker.
                    db.execute("BEGIN IMMEDIATE")
                    row = db.execute("SELECT snapshot FROM startup WHERE scope = ?", (key,)).fetchone()
                    snapshot = json.loads(row[0]) if row else None
                    refresh = reload_requested and (snapshot is None or snapshot.get("reload_message_id") != message_id)
                    fetched = snapshot is None or refresh
                    if fetched:
                        selected = branch or self._http(trace, "GET", root)["default_branch"]
                        try:
                            data = self._read_utf8(trace, repo, "START.md", selected, self.valves.MAX_START_BYTES)
                        except ValueError as error:
                            raise ValueError(str(error) + " Für den Einstieg ist die kurze, im GhostWriter-Update erzeugte START.md erforderlich.") from None
                        if self.valves.GITHUB_TOKEN in data["content"]:
                            raise ValueError("START.md enthält den Zugangstoken und wird nicht gespeichert.")
                        receipt = hashlib.sha256((key + data["sha"] + data["content"]).encode()).hexdigest()
                        snapshot = {**data, "repo": repo, "branch": selected,
                                    "startup_receipt": receipt, "reload_message_id": message_id if reload_requested else None}
                        db.execute("INSERT OR REPLACE INTO startup (scope, snapshot) VALUES (?, ?)",
                                   (key, json.dumps(snapshot, ensure_ascii=False)))
                    if len(snapshot["content"].encode("utf-8")) > self.valves.MAX_START_BYTES:
                        raise ValueError("Gespeicherter Einstieg überschreitet MAX_START_BYTES; kurze START.md erzeugen und ausdrücklich neu laden.")
                    db.execute("COMMIT")
                finally:
                    db.close()  # Unvollständige/fehlgeschlagene Initialisierung wird zurückgerollt.
            except (OSError, sqlite3.Error):
                raise ValueError("Startzustand nicht verfügbar. START_STATE_DIR muss im beschreibbaren, persistenten Datenvolume liegen.") from None
            present = self._start_context_present(__messages__, snapshot)
            result = {k: snapshot[k] for k in ("repo", "branch", "path", "sha", "startup_receipt")}
            result.update({"fetched": fetched, "already_loaded": not fetched,
                           "context_restored": not fetched and not present})
            if fetched or not present:
                result["content"] = snapshot["content"]
                result["message"] = "Einstieg intern lesen, Dateiinhalt nicht ausgeben. Beim normalen Start kurz begrüßen und danach die aktuelle Bibliothek mit Lesewerkzeugen laden und anzeigen. Bei konkreter Benutzeranfrage diese direkt bearbeiten."
            else:
                result["message"] = "Einstieg bereits im Chat vorhanden. Kein GitHub-Abruf. Jetzt Benutzeranfrage bearbeiten; Startwerkzeug nicht wiederholen."
            if fetched:
                try:
                    library = self._library_view(trace, repo, snapshot["branch"] if not branch else None)
                    result["view"] = library["view"]
                    result["books"] = library["books"]
                    result["library_source"] = {key: library[key] for key in ("path", "branch", "sha", "source_kind")}
                    result["message"] = "START.md intern lesen. Beim normalen Start einen kurzen Willkommenssatz und danach die fertige Bibliotheksansicht aus view unverändert anzeigen. Nicht selbst JSON in eine Ansicht umdeuten. Bei konkreter Buchanfrage diese direkt bearbeiten."
                except (ValueError, KeyError, TypeError) as error:
                    result["library_error"] = str(error)
                    result["message"] = "Einstieg geladen, Bibliotheksansicht fehlgeschlagen. library_error verständlich melden; keine leere Bibliothek und keine Platzhalter erfinden. Erneuter Bibliotheksabruf über show_library."
            return result
        return await self._run(op)

    async def get_repo(self, repo: str) -> str:
        """Liest Repository, Standard-Branch und verfügbare Berechtigungsangaben. Kein Schreibtest."""
        def op(t):
            d = self._http(t, "GET", self._repo(repo))
            return {k: d.get(k) for k in ("full_name", "default_branch", "private", "permissions", "html_url")}
        return await self._run(op)

    async def list_dir(self, repo: str, path: str = "", branch: Optional[str] = None) -> str:
        """Listet Dateien und Verzeichnisse. branch explizit setzen, um den richtigen Buchstand zu lesen."""
        def op(t):
            d = self._http(t, "GET", self._repo(repo)+"/contents/"+(self._path(path) if path else ""), {"ref": branch} if branch else {})
            if not isinstance(d, list):
                raise ValueError("Pfad ist eine Datei.")
            return [{k: i.get(k) for k in ("type", "path", "sha", "size")} for i in d]
        return await self._run(op)

    async def read_file(self, repo: str, path: str, branch: Optional[str] = None) -> str:
        """Liest eine UTF-8-Datei samt Datei-SHA. branch kann auch eine Commit-SHA für einen konsistenten Lesestand sein."""
        return await self._run(lambda t: self._read_utf8(t, repo, path, branch))

    async def get_branches(self, repo: str) -> str:
        """Listet alle Branches mit Head-SHA, einschließlich buch/* und ghostwriter/* ."""
        return await self._run(lambda t: [{"name": d["name"], "sha": d["commit"]["sha"]} for d in self._pages(t, self._repo(repo)+"/branches")])

    async def get_head(self, repo: str, branch: str) -> str:
        """Liest die aktuelle Head-SHA. Vor Änderungen als expected_head_sha merken."""
        return await self._run(lambda t: self._http(t, "GET", self._repo(repo)+"/git/ref/heads/"+quote(branch, safe="/")))

    async def create_branch(self, repo: str, new_branch_name: str, source_branch: str) -> str:
        """Legt einen Branch an. Buch-Branches nie mit dem Standard-Branch zusammenführen."""
        def op(t):
            root = self._repo(repo)
            sha = self._http(t, "GET", root+"/git/ref/heads/"+quote(source_branch, safe="/"))["object"]["sha"]
            return self._http(t, "POST", root+"/git/refs", data={"ref": "refs/heads/"+new_branch_name, "sha": sha}, expected=(201,))
        return await self._run(op)

    async def compare_commits(self, repo: str, base_sha: str, head_sha: str) -> str:
        """Vergleicht Stände. Bei 300 Dateien ist die GitHub-Dateiliste möglicherweise unvollständig: neu lesen und nicht blind schreiben."""
        def op(t):
            d = self._http(t, "GET", self._repo(repo)+"/compare/"+quote(base_sha, safe="")+"..."+quote(head_sha, safe=""))
            files = d.get("files", [])
            return {"status": d.get("status"), "files_may_be_truncated": len(files) >= 300,
                    "files": [{k: f.get(k) for k in ("filename", "previous_filename", "status", "patch")} for f in files]}
        return await self._run(op)

    async def commit_files(self, repo: str, branch: str, files_json: str, commit_message: str, expected_head_sha: str) -> str:
        """Speichert alle Dateien einer Aufgabe in GENAU EINEM Commit. Keine Einzelschreibaufrufe. Nur nach erforderlicher Benutzerfreigabe verwenden. Bei neuer Head-SHA abbrechen und neu lesen.
        :param files_json: JSON-Liste: [{"path":"datei.md","content":"vollständiger UTF-8-Text"}]. content:null löscht eine Datei.
        :param branch: Normalerweise ghostwriter/<buch-branch>; neuer Buch-Branch nur beim ausdrücklich beauftragten Anlegen.
        :param expected_head_sha: Zuvor gelesene vollständige Branch-Head-SHA.
        :param commit_message: Deutsche Nachricht nach START.md, mit GhostWriter-Aktion im Nachrichtentext.
        """
        def op(t):
            root = self._repo(repo)
            entries = json.loads(files_json)
            if not isinstance(entries, list) or not entries:
                raise ValueError("files_json muss eine nichtleere Liste sein.")
            seen = set()
            for item in entries:
                self._path(item["path"])
                if item["path"] in seen:
                    raise ValueError("Doppelter Dateipfad.")
                seen.add(item["path"])
                text = item["content"]
                if text is not None and (not isinstance(text, str) or len(text.encode("utf-8")) > self.valves.MAX_FILE_BYTES):
                    raise ValueError("Dateiinhalt ungültig oder zu groß.")
                if isinstance(text, str) and self.valves.GITHUB_TOKEN in text:
                    raise ValueError("Token darf nicht gespeichert werden.")
            if self.valves.GITHUB_TOKEN and self.valves.GITHUB_TOKEN in commit_message:
                raise ValueError("Token darf nicht in der Commit-Nachricht stehen.")
            if not re.fullmatch(r"[0-9a-fA-F]{40}", expected_head_sha) or not commit_message.strip():
                raise ValueError("Vollständige expected_head_sha und Commit-Nachricht erforderlich.")
            ref = root+"/git/ref/heads/"+quote(branch, safe="/")
            head = self._http(t, "GET", ref)["object"]["sha"]
            if head != expected_head_sha:
                raise ValueError("Nicht gespeichert: Branch wurde inzwischen geändert. Neu lesen und abgleichen.")
            commit = self._http(t, "GET", root+"/git/commits/"+head)
            tree = []
            for item in entries:
                if item["content"] is None:
                    tree.append({"path": item["path"], "mode": "100644", "type": "blob", "sha": None})
                else:
                    blob = self._http(t, "POST", root+"/git/blobs", data={"content": item["content"], "encoding": "utf-8"}, expected=(201,))
                    tree.append({"path": item["path"], "mode": "100644", "type": "blob", "sha": blob["sha"]})
            new_tree = self._http(t, "POST", root+"/git/trees", data={"base_tree": commit["tree"]["sha"], "tree": tree}, expected=(201,))
            if new_tree["sha"] == commit["tree"]["sha"]:
                return {"changed": False, "message": "Nichts geändert", "sha": head}
            new_commit = self._http(t, "POST", root+"/git/commits", data={"message": commit_message, "tree": new_tree["sha"], "parents": [head]}, expected=(201,))
            # Konflikte werden mit force:false abgewiesen, nicht überschrieben.
            if self._http(t, "GET", ref)["object"]["sha"] != head:
                raise ValueError("Nicht gespeichert: Branch inzwischen geändert; vorbereiteter Commit nicht veröffentlicht.")
            self._http(t, "PATCH", root+"/git/refs/heads/"+quote(branch, safe="/"), data={"sha": new_commit["sha"], "force": False})
            return {"changed": True, "sha": new_commit["sha"], "branch": branch, "message": "Gespeichert; PR/Übernahme separat prüfen."}
        return await self._run(op)

    async def list_pull_requests(self, repo: str, state: str = "open") -> str:
        """Listet Pull Requests mit Head- und Ziel-Branch; passenden GhostWriter-PR exakt zuordnen."""
        def op(t):
            return [{"number": d["number"], "title": d["title"], "head": d["head"]["ref"], "head_sha": d["head"]["sha"], "base": d["base"]["ref"], "url": d["html_url"]} for d in self._pages(t, self._repo(repo)+"/pulls", {"state": state})]
        return await self._run(op)

    async def get_pull_request(self, repo: str, pull_number: int) -> str:
        """Liest PR-Zustand, Head, Ziel und Merge-Status."""
        return await self._run(lambda t: self._http(t, "GET", self._repo(repo)+f"/pulls/{pull_number}"))

    async def create_pull_request(self, repo: str, title: str, head_branch: str, base_branch: str, body: str = "") -> str:
        """Erstellt PR. Für Buchänderungen Titel GhostWriter: offene Änderungen und Ziel Buch-Branch verwenden."""
        return await self._run(lambda t: self._http(t, "POST", self._repo(repo)+"/pulls", data={"title": title, "head": head_branch, "base": base_branch, "body": body}, expected=(201,)))

    async def merge_pull_request(self, repo: str, pull_number: int, expected_head_sha: str) -> str:
        """Übernimmt PR mit Merge-Commit, nur nach ausdrücklicher Übernahmebestätigung oder geprüftem changes.auto_merge:true. Auflagen benötigen eigene Bestätigung. Kein Freigabeersatz."""
        def op(t):
            d = self._http(t, "PUT", self._repo(repo)+f"/pulls/{pull_number}/merge", data={"sha": expected_head_sha, "merge_method": "merge"})
            if not d.get("merged"):
                raise ValueError("Pull Request wurde nicht übernommen.")
            return d
        return await self._run(op)

    async def delete_merged_work_branch(self, repo: str, pull_number: int, expected_head_sha: str) -> str:
        """Löscht ausschließlich den unveränderten ghostwriter/*-Branch eines bereits gemergten PR. Nie Buch-Branches löschen."""
        def op(t):
            root = self._repo(repo)
            pr = self._http(t, "GET", root+f"/pulls/{pull_number}")
            branch = pr["head"]["ref"]
            if not pr.get("merged") or branch != "ghostwriter/"+pr["base"]["ref"] or pr["head"]["repo"]["full_name"].lower() != repo.lower():
                raise ValueError("Kein übernommener PR mit passendem Arbeits-Branch.")
            sha = self._http(t, "GET", root+"/git/ref/heads/"+quote(branch, safe="/"))["object"]["sha"]
            if sha != expected_head_sha or sha != pr["head"]["sha"]:
                raise ValueError("Arbeits-Branch hat neue Änderungen; nicht gelöscht.")
            self._http(t, "DELETE", root+"/git/refs/heads/"+quote(branch, safe="/"), expected=(204,))
            return {"deleted": branch}
        return await self._run(op)

    async def list_commits(self, repo: str, branch: str, per_page: int = 5) -> str:
        """Liest die letzten 1–100 Commits mit SHA und Nachricht."""
        def op(t):
            d = self._http(t, "GET", self._repo(repo)+"/commits", {"sha": branch, "per_page": max(1, min(per_page, 100))})
            return [{"sha": c["sha"], "message": c["commit"]["message"]} for c in d]
        return await self._run(op)

    async def list_issues(self, repo: str, state: str = "open") -> str:
        """Listet Issues ohne Pull Requests. Programmfehler im upstream.repo suchen."""
        return await self._run(lambda t: [{"number": i["number"], "title": i["title"], "state": i["state"]} for i in self._pages(t, self._repo(repo)+"/issues", {"state": state}) if "pull_request" not in i])

    async def create_pr_review(self, repo: str, pull_number: int, body: str, event: str = "COMMENT") -> str:
        """Erstellt nur auf Benutzerauftrag ein GitHub-Review; keine redaktionelle Buchfreigabe."""
        def op(t):
            if event not in ("COMMENT", "APPROVE", "REQUEST_CHANGES"):
                raise ValueError("Ungültiges Review-Ereignis.")
            return self._http(t, "POST", self._repo(repo)+f"/pulls/{pull_number}/reviews", data={"body": body, "event": event}, expected=(200, 201))
        return await self._run(op)

    async def list_workflow_runs(self, repo: str, branch: str) -> str:
        """Liest die letzten 30 GitHub-Actions-Läufe eines Buch- oder Arbeits-Branchs."""
        def op(t):
            d = self._http(t, "GET", self._repo(repo)+"/actions/runs", {"branch": branch, "per_page": 30})
            return [{k: r.get(k) for k in ("id", "name", "status", "conclusion", "html_url", "head_sha")} for r in d["workflow_runs"]]
        return await self._run(op)

    async def dispatch_workflow(self, repo: str, workflow_file: str, branch: str, inputs_json: str = "{}") -> str:
        """Startet einen Workflow nur auf ausdrücklichen Auftrag und mit aktiviertem Valve. Niemals die Umwandlung Einzelbuch→Bibliothek starten; dafür GitHub verwenden."""
        def op(t):
            if not self.valves.ALLOW_WORKFLOW_DISPATCH:
                raise ValueError("Workflow-Start im Valve deaktiviert.")
            if workflow_file not in ("proof.yml", "index.yml", "library.yml"):
                raise ValueError("Nur proof.yml, index.yml und library.yml sind hier freigegeben. Veröffentlichung/Umwandlung bitte in GitHub starten.")
            inputs = json.loads(inputs_json)
            if not isinstance(inputs, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in inputs.items()):
                raise ValueError("inputs_json muss ein Objekt mit Zeichenketten sein.")
            if workflow_file != "proof.yml" and inputs:
                raise ValueError("Dieser Workflow hat keine Eingabefelder.")
            if workflow_file == "proof.yml" and (set(inputs)-{"formats"} or any(f.strip() not in {"pdf", "pdf_print", "cover", "docx", "epub"} for f in inputs.get("formats", "pdf").split(","))):
                raise ValueError("Ungültige Probedruck-Formate.")
            self._http(t, "POST", self._repo(repo)+"/actions/workflows/"+workflow_file+"/dispatches", data={"ref": branch, "inputs": inputs}, expected=(204,))
            return {"accepted": True, "message": "Start angefordert; Erfolg mit list_workflow_runs prüfen.", "workflow": workflow_file, "branch": branch}
        return await self._run(op)
