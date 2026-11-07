"""
title: GhostWriter GitHub
description: GitHub lesen und Aufgaben als gemeinsamen Commit speichern.
version: 1.4.1
requirements: requests,pydantic,pyyaml
"""
import asyncio
import base64
import hashlib
import hmac
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote

import requests
import yaml
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

    def _navigation_scope(self, repo, chat, user, metadata, tool_id):
        metadata = metadata or {}
        chat = chat or metadata.get("chat_id")
        user = (user or {}).get("id") or metadata.get("user_id")
        if not isinstance(chat, str) or not chat or not isinstance(user, str) or not user:
            return None
        return json.dumps([repo.lower(), chat, user, tool_id or "ghostwriter-github"])

    def _navigation_view(self, result, payload, scope):
        if scope is None:
            return result
        encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        signature = hmac.new(self.valves.GITHUB_TOKEN.encode(), (scope + "\n" + encoded).encode(), hashlib.sha256).hexdigest()
        receipt = encoded + "." + signature
        return {**result, "navigation_receipt": receipt,
                "view": result["view"] + "\n\n<!-- ghostwriter-nav:" + receipt + " -->"}

    def _navigation_data(self, receipt, scope):
        if not scope or not isinstance(receipt, str) or len(receipt) > 100000:
            raise ValueError("Auswahl fehlt oder ist veraltet. Bitte Bibliothek erneut öffnen.")
        try:
            encoded, signature = receipt.rsplit(".", 1)
            expected = hmac.new(self.valves.GITHUB_TOKEN.encode(), (scope + "\n" + encoded).encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError()
            data = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True))
            if not isinstance(data, dict) or data.get("kind") not in ("library", "book"):
                raise ValueError()
            return data
        except (ValueError, UnicodeError, TypeError):
            raise ValueError("Auswahl gehört nicht zu dieser Sitzung oder wurde verändert. Bitte Bibliothek erneut öffnen.") from None

    def _signed_library(self, result, scope):
        return self._navigation_view(result, {"kind": "library", "branches": [b["branch"] for b in result["books"]],
                                               "sha": result["sha"]}, scope)

    async def show_library(self, __chat_id__: Optional[str] = None, __user__: Optional[dict] = None,
                           __metadata__: Optional[dict] = None, __id__: Optional[str] = None) -> str:
        """Zeigt die echte Bibliothek für START_REPO. Bei „Bibliothek“, „Library“ oder „Home“ aufrufen.
        Liest library.json jedes Mal frisch vom tatsächlichen Standard-Branch, unabhängig von START_BRANCH.
        Die fertige Markdown-Ansicht aus view unverändert anzeigen; books ordnet Nummern zu Branches zu.
        Bei einem Fehler keine leere Liste, Nullwerte oder Beispieldaten erfinden.
        """
        def op(trace):
            repo = self._instance_repo()
            scope = self._navigation_scope(repo, __chat_id__, __user__, __metadata__, __id__)
            return self._signed_library(self._library_view(trace, repo), scope)
        return await self._run(op)

    def _book_view(self, trace, repo, book_branch, chapter=0, section=0, expected_head=None):
        root = self._repo(repo)
        library = self._library_view(trace, repo)
        if not any(book["branch"] == book_branch for book in library["books"]):
            raise ValueError("Das ausgewählte Buch ist nicht mehr in der Bibliothek. Bitte Bibliothek neu öffnen.")
        branches = {b["name"]: b["commit"]["sha"] for b in self._pages(trace, root + "/branches")}
        if book_branch not in branches:
            raise ValueError("Buchbranch nicht gefunden. Bitte Bibliothek neu öffnen.")
        work = "ghostwriter/" + book_branch
        pulls = [p for p in self._pages(trace, root + "/pulls", {"state": "open"})
                 if p["base"]["ref"] == book_branch and p["head"]["ref"] == work
                 and (p["head"].get("repo") or {}).get("full_name", "").lower() == repo.lower()]
        if len(pulls) > 1:
            raise ValueError("Mehrere passende Arbeits-PRs. Buchzuordnung muss zuerst geklärt werden.")
        reading = work if pulls else book_branch
        if reading not in branches:
            raise ValueError("Arbeitsbranch des offenen PR fehlt. Buch nicht geöffnet.")
        head = branches[reading]
        if not re.fullmatch(r"[0-9a-fA-F]{40}", head) or (pulls and pulls[0]["head"]["sha"] != head):
            raise ValueError("Buchstand hat sich während des Lesens geändert. Bitte erneut öffnen.")
        cfg = yaml.safe_load(self._read_utf8(trace, repo, "ghostwriter.yml", head)["content"])
        if not isinstance(cfg, dict) or not isinstance(cfg.get("project"), dict) or not isinstance(cfg.get("structure"), dict):
            raise ValueError("Ungültige Projektdatei; keine Buchübersicht erzeugt.")
        chapters = cfg["structure"].get("chapters")
        if not isinstance(chapters, list) or any(not isinstance(c, dict) or not isinstance(c.get("sections"), list) for c in chapters):
            raise ValueError("Ungültige Kapitelstruktur; keine Buchübersicht erzeugt.")
        changed = bool(expected_head and expected_head != head)
        if changed:
            chapter, section = 0, 0  # Keine Auswahl aus einer inzwischen umgeordneten Struktur erraten.
        english = self.valves.INTERFACE_LANGUAGE == "en"
        def text(value):
            if not isinstance(value, str):
                raise ValueError("Ungültiger Titel in der Projektdatei.")
            return re.sub(r"([|\[\]*_`<>])", r"\\\1", value.replace("\\", "\\\\").replace("\n", " ").replace("\r", " "))
        def status(value):
            labels = {"planned": ("geplant", "planned"), "in_progress": ("in Arbeit", "in progress"),
                      "ready_for_assembly": ("bereit zum Zusammenführen", "ready for assembly"),
                      "assembly": ("Zusammenführung", "assembly"), "review": ("Prüfung", "review"),
                      "ready_for_approval": ("bereit zur Freigabe", "ready for approval"),
                      "approved": ("freigegeben", "approved"), "writing": ("Entwurf", "draft"),
                      "research": ("Recherche", "research"), "revision": ("Überarbeitung", "revision"),
                      "brainstorming": ("Ideensammlung", "brainstorming"), "ready_to_write": ("bereit zum Schreiben", "ready to write"),
                      "fact_check": ("Faktenprüfung", "fact check")}
            if not isinstance(value, str):
                return "unbekannt" if not english else "unknown"
            return text(labels.get(value, (value, value))[int(english)])
        title = text(cfg["project"].get("title") or cfg["project"].get("working_title") or book_branch)
        context = {"repo": repo, "book_branch": book_branch, "reading_branch": reading, "sha": head,
                   "book_title": cfg["project"].get("title") or cfg["project"].get("working_title"),
                   "book_language": cfg["project"].get("language"), "level": "book",
                   "chapters": [{"number": i, "id": c.get("id"), "title": c.get("title"), "status": c.get("status")}
                                for i, c in enumerate(chapters, 1)]}
        lines = ["### 📖 " + title, "", text(repo), "",
                 ("Reading branch: " if english else "Lesestand: ") + "`" + reading + "` · `" + head[:7] + "`"]
        if pulls:
            lines += [("Pending changes · PR #" if english else "Noch nicht übernommene Änderungen · PR #") + str(pulls[0]["number"])]
        if changed:
            lines += ["", "The book changed. Choose again from the updated overview." if english else
                      "Der Buchstand wurde inzwischen geändert. Bitte aus der aktualisierten Übersicht erneut wählen."]
        if chapter == 0:
            lines += ["", ("Author: " if english else "Autor: ") + text(cfg["project"].get("author") or "–"), "",
                      "| No. | Chapter | Sections | Status |" if english else "| Nr. | Kapitel | Abschnitte | Stand |", "|---|---|---|---|"]
            for number, ch in enumerate(chapters, 1):
                lines.append(f"| {number} | {text(ch.get('title') or '–')} | {len(ch['sections'])} | {status(ch.get('status'))} |")
            if not chapters:
                lines.append("No chapters yet." if english else "Noch keine Kapitel angelegt.")
            if chapters:
                lines += ["", "`Chapter N` or a number · `Library`" if english else "`Kapitel N` oder Nummer · `Bibliothek`"]
            else:
                lines += ["", "`Library`" if english else "`Bibliothek`"]
        else:
            if chapter < 1 or chapter > len(chapters):
                raise ValueError("Diese Kapitelnummer gibt es im aktuellen Buch nicht.")
            ch = chapters[chapter - 1]
            context.update(level="chapter", chapter=context["chapters"][chapter - 1], sections=[])
            lines += ["", f"#### {chapter}. {text(ch.get('title') or '–')}", ""]
            def section_data(s):
                path = s.get("path")
                folder = ch.get("path")
                if not isinstance(path, str) or not isinstance(folder, str) or not path.startswith(folder.rstrip("/") + "/sections/"):
                    raise ValueError("Ungültiger Abschnittspfad; Abschnitt nicht gelesen.")
                raw = self._read_utf8(trace, repo, path, head)["content"]
                match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", raw, re.S)
                if not match:
                    raise ValueError("Abschnitt ohne gültige Metadaten.")
                metadata = yaml.safe_load(match[1])
                if not isinstance(metadata, dict):
                    raise ValueError("Abschnitt mit ungültigen Metadaten.")
                return metadata, raw[match.end():].strip()
            if section == 0:
                lines += ["| No. | Section | Status |" if english else "| Nr. | Abschnitt | Stand |", "|---|---|---|"]
                for number, s in enumerate(ch["sections"], 1):
                    meta, _ = section_data(s)
                    context["sections"].append({"number": f"{chapter}.{number}", "id": s.get("id"),
                                                "title": s.get("title"), "status": meta.get("status")})
                    lines.append(f"| {chapter}.{number} | {text(s.get('title') or '–')} | {status(meta.get('status'))} |")
                if ch["sections"]:
                    lines += ["", f"`Section {chapter}.N` or a number · `Overview` · `Library`" if english else
                              f"`Abschnitt {chapter}.N` oder Nummer · `Übersicht` · `Bibliothek`"]
                else:
                    lines += ["", "No sections yet. `Overview` · `Library`" if english else
                              "Noch keine Abschnitte. `Übersicht` · `Bibliothek`"]
            else:
                if section < 1 or section > len(ch["sections"]):
                    raise ValueError("Diese Abschnittsnummer gibt es im aktuellen Kapitel nicht.")
                s = ch["sections"][section - 1]
                meta, body = section_data(s)
                context.update(level="section", section={"number": f"{chapter}.{section}", "id": s.get("id"),
                               "title": s.get("title"), "status": meta.get("status")})
                lines += [f"##### {chapter}.{section} {text(s.get('title') or '–')}", "", status(meta.get("status")), "", body,
                          "", f"`Chapter {chapter}` · `Overview` · `Library`" if english else f"`Kapitel {chapter}` · `Übersicht` · `Bibliothek`"]
        return {"repo": repo, "book_branch": book_branch, "branch": reading, "sha": head, "chapter": chapter, "section": section,
                "changed": changed, "view": "\n".join(lines), "conversation_context": context}

    async def open_book(self, selection: str, receipt: str, __chat_id__: Optional[str] = None,
                        __user__: Optional[dict] = None, __metadata__: Optional[dict] = None,
                        __id__: Optional[str] = None) -> str:
        """Öffnet eine Nummer aus der angezeigten Bibliothek oder eine Buch-/Kapitel-/Abschnittsansicht.
        selection ist der unveränderte Navigationsbefehl, receipt die zugehörige Navigationsquittung.
        Nur lesend. Kein Schreiben, keine Freigabe. Veränderte Strukturen werden nicht still umgedeutet.
        """
        def op(trace):
            repo = self._instance_repo()
            scope = self._navigation_scope(repo, __chat_id__, __user__, __metadata__, __id__)
            context = self._navigation_data(receipt, scope)
            command = selection.strip().casefold()
            number = re.fullmatch(r"(?:(?:buch|book)\s*)?([1-9][0-9]*)", command)
            ch = re.fullmatch(r"(?:kapitel|chapter)\s*([1-9][0-9]*)", command)
            sec = re.fullmatch(r"(?:(?:abschnitt|section)\s*)?([1-9][0-9]*)\.([1-9][0-9]*)", command)
            chapter = section = 0
            if context["kind"] == "library":
                if not number or int(number[1]) > len(context.get("branches", [])):
                    raise ValueError("Bitte eine Buchnummer aus der angezeigten Bibliothek wählen.")
                book = context["branches"][int(number[1]) - 1]
            else:
                book = context["book_branch"]
                if ch:
                    chapter = int(ch[1])
                elif sec:
                    chapter, section = int(sec[1]), int(sec[2])
                elif number and not command.startswith(("buch", "book")):
                    if context.get("chapter"):
                        chapter, section = context["chapter"], int(number[1])
                    else:
                        chapter = int(number[1])
                elif command not in ("übersicht", "overview"):
                    raise ValueError("Unbekannte Navigation; bitte Bibliothek, Übersicht, Kapitel oder Abschnitt wählen.")
            result = self._book_view(trace, repo, book, chapter, section,
                                     context.get("sha") if context["kind"] == "book" and command not in ("übersicht", "overview") else None)
            return self._navigation_view(result, {"kind": "book", "book_branch": book, "sha": result["sha"],
                                                  "chapter": result["chapter"], "section": result["section"]}, scope)
        return await self._run(op)

    async def get_current_context(self, receipt: str, __chat_id__: Optional[str] = None,
                                  __user__: Optional[dict] = None, __metadata__: Optional[dict] = None,
                                  __id__: Optional[str] = None) -> str:
        """Liest den ausgewählten Gesprächskontext frisch. Keine Statusänderung oder Freigabe.
        receipt stammt aus der zuletzt angezeigten Ansicht. Bei geändertem Lesestand erneut wählen.
        """
        def op(trace):
            repo = self._instance_repo()
            scope = self._navigation_scope(repo, __chat_id__, __user__, __metadata__, __id__)
            selected = self._navigation_data(receipt, scope)
            if selected["kind"] == "library":
                result = self._library_view(trace, repo)
                result["changed"] = (selected.get("sha") != result["sha"] or
                                     selected.get("branches") != [b["branch"] for b in result["books"]])
                result["conversation_context"] = {"level": "library", "repo": repo, "books": result["books"]}
                return self._signed_library(result, scope)
            result = self._book_view(trace, repo, selected["book_branch"], selected.get("chapter", 0),
                                     selected.get("section", 0), expected_head=selected.get("sha"))
            workflow = yaml.safe_load(self._read_utf8(trace, repo, "workflow.yml", result["sha"])["content"])
            rules = {}
            if not isinstance(workflow, dict):
                raise ValueError("Ungültige Ablaufregeln; Gesprächskontext nicht geladen.")
            for entity in ("chapter", "section"):
                definition = (workflow.get("entities") or {}).get(entity, {})
                flow = workflow.get(entity + "_workflow", {})
                statuses = definition.get("statuses")
                transitions = flow.get("transitions")
                if (not isinstance(statuses, list) or not statuses or not all(isinstance(v, str) for v in statuses)
                        or not isinstance(transitions, list) or not all(isinstance(t, dict) for t in transitions)):
                    raise ValueError("Unvollständige Statusregeln; Gesprächskontext nicht geladen.")
                rules[entity] = {"statuses": statuses, "transitions": transitions, "invariants": flow.get("invariants", [])}
            result["conversation_context"]["status_rules"] = rules
            return self._navigation_view(result, {"kind": "book", "book_branch": result["book_branch"],
                          "sha": result["sha"], "chapter": result["chapter"], "section": result["section"]}, scope)
        return await self._run(op)

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
        except (ValueError, KeyError, TypeError, AttributeError, UnicodeError, yaml.YAMLError) as exc:
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
                    scope = self._navigation_scope(repo, __chat_id__, __user__, __metadata__, __id__)
                    library = self._signed_library(self._library_view(trace, repo, snapshot["branch"] if not branch else None), scope)
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
