"""
title: GhostWriter Direkt
description: Start und Bibliothek direkt ausführen, Gespräch an das Basismodell weitergeben.
version: 1.0.0
required_open_webui_version: 0.13.0
requirements: pydantic
"""
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        BASE_MODEL: str = Field(default="llama3.2:3b", description="Basismodell für normale Gesprächsbeiträge; nicht diese Pipe selbst auswählen.")
        TOOL_ID: str = Field(default="", description="Optional: ID des gebundenen GhostWriter-GitHub-Werkzeugs. Leer: genau eine passende Integration erforderlich.")
        INTERFACE_LANGUAGE: Literal["de", "en"] = Field(default="de", description="Sprache der Begrüßung und Fehlermeldungen; passend zum GitHub-Werkzeug einstellen.")

    def __init__(self):
        self.valves = self.Valves()

    def _text(self, de, en):
        return en if self.valves.INTERFACE_LANGUAGE == "en" else de

    def _user_text(self, body, metadata):
        message = (metadata or {}).get("user_message")
        if not isinstance(message, dict):
            message = next((m for m in reversed(body.get("messages") or [])
                            if isinstance(m, dict) and m.get("role") == "user"), {})
        content = message.get("content", "")
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content
                                if isinstance(part, dict) and part.get("type") == "text")
        return content if isinstance(content, str) else ""

    def _functions(self, tools):
        """Nur von Open WebUI injizierte lokale Callables verwenden, nie Modell-JSON."""
        groups = {}
        for name, entry in (tools or {}).items():
            if not isinstance(entry, dict) or entry.get("type") in ("builtin", "external", "terminal"):
                continue
            tool_id, function = entry.get("tool_id"), entry.get("callable")
            if not tool_id or not callable(function) or (self.valves.TOOL_ID and tool_id != self.valves.TOOL_ID):
                continue
            spec_name = (entry.get("spec") or {}).get("name")
            for method in ("read_start_md", "show_library"):
                if (name == method or spec_name == method or getattr(function, "__name__", None) == method
                        or spec_name == f"{tool_id}_{method}"):
                    if method in groups.setdefault(tool_id, {}):
                        raise ValueError(self._text("Mehrdeutige Werkzeugfunktion; nur eine GhostWriter-Integration zuordnen.",
                                                    "Ambiguous tool function; bind only one GhostWriter integration."))
                    groups[tool_id][method] = function
        complete = [functions for functions in groups.values() if set(functions) == {"read_start_md", "show_library"}]
        if len(complete) != 1:
            raise ValueError(self._text(
                "Dem Modell genau ein GhostWriter-GitHub-Werkzeug ab Version 1.2 zuordnen. Bei mehreren Integrationen TOOL_ID festlegen.",
                "Bind exactly one GhostWriter GitHub tool, version 1.2 or later. Set TOOL_ID if several integrations are attached."))
        return complete[0]

    async def _call(self, function):
        value = await function()
        try:
            payload = json.loads(value) if isinstance(value, str) else value
        except ValueError:
            payload = None
        if not isinstance(payload, dict) or payload.get("ok") is not True or not isinstance(payload.get("result"), dict):
            error = payload.get("error") if isinstance(payload, dict) else None
            raise ValueError(error if isinstance(error, str) else self._text("Ungültige Werkzeugantwort.", "Invalid tool response."))
        return payload["result"]

    async def _forward(self, body, request, user_data, metadata):
        # Open-WebUI-Import erst im Weiterleitungspfad: die direkten Befehle
        # benötigen weder Ollama noch einen Modellaufruf.
        from open_webui.models.users import Users
        from open_webui.utils.chat import generate_chat_completion
        if request is None or not (user_data or {}).get("id"):
            raise ValueError(self._text("Open-WebUI-Anfrage oder Benutzerkennung fehlt.", "Open WebUI request or user identity is missing."))
        if not self.valves.BASE_MODEL.strip() or self.valves.BASE_MODEL == body.get("model"):
            raise ValueError(self._text("BASE_MODEL muss ein anderes, verfügbares Modell sein.", "BASE_MODEL must be a different, available model."))
        app_state = getattr(getattr(request, "app", None), "state", None)
        target = getattr(app_state, "MODELS", {}).get(self.valves.BASE_MODEL)
        if isinstance(target, dict) and target.get("pipe"):
            raise ValueError(self._text("BASE_MODEL muss ein reguläres Modell sein, keine weitere Pipe.",
                                       "BASE_MODEL must be a regular model, not another pipe."))
        try:
            user = await Users.get_user_by_id(user_data["id"])
        except Exception:
            raise RuntimeError("Benutzerabfrage fehlgeschlagen") from None
        if user is None:
            raise ValueError(self._text("Open-WebUI-Benutzer nicht verfügbar.", "Open WebUI user is unavailable."))
        payload = {**body, "model": self.valves.BASE_MODEL, "metadata": dict(metadata or {})}
        try:
            return await generate_chat_completion(request, payload, user)
        except Exception:
            # Auch ValueError aus einem Provider darf keine ungefilterte URL,
            # Header oder Zugangsdaten in die sichtbare Antwort übernehmen.
            raise RuntimeError("Modellanfrage fehlgeschlagen") from None

    async def pipe(self, body: dict, __tools__: Optional[dict] = None, __user__: Optional[dict] = None,
                   __metadata__: Optional[dict] = None, __request__=None, __task__: Optional[str] = None):
        """Start/Bibliothek direkt beantworten; normale Beiträge an BASE_MODEL weitergeben."""
        try:
            metadata = __metadata__ or {}
            # Titel-/Folgefragen-Erzeugung hat eigene Aufgabenprompts. Niemals
            # anhand der dort ebenfalls vorhandenen letzten Chatnachricht starten.
            if __task__ or metadata.get("task"):
                return await self._forward(body, __request__, __user__, metadata)
            command = self._user_text(body, metadata).strip().casefold()
            functions = self._functions(__tools__)
            startup = await self._call(functions["read_start_md"])
            if command in ("start", "bibliothek", "library", "home", "start neu laden", "reload start"):
                if startup.get("library_error"):
                    raise ValueError(startup["library_error"])
                view = startup.get("view")
                if not isinstance(view, str) or not view.strip():
                    library = await self._call(functions["show_library"])
                    view = library.get("view")
                if not isinstance(view, str) or not view.strip():
                    raise ValueError(self._text("Das Werkzeug hat keine fertige Bibliotheksansicht geliefert.",
                                                "The tool did not return a ready library view."))
                if command in ("start", "start neu laden", "reload start"):
                    greeting = self._text("Herzlich willkommen, dein Schreibassistent ist geladen und bereit.",
                                          "Welcome, your writing assistant is loaded and ready.")
                    return greeting + "\n\n" + view
                return view
            if startup.get("library_error"):
                # Ein Bibliotheksfehler darf nicht durch eine erfundene Modellansicht verdeckt werden.
                raise ValueError(startup["library_error"])
            payload = dict(body)
            payload["messages"] = [dict(message) for message in body.get("messages", [])]
            source = startup.get("content")
            if isinstance(source, str) and source.strip():
                instructions = {"role": "system", "content": "GhostWriter-Projektanweisungen (intern):\n" + source}
                if instructions not in payload["messages"]:
                    payload["messages"].insert(0, instructions)
            return await self._forward(payload, __request__, __user__, metadata)
        except ValueError as error:
            return "✗ " + str(error)
        except Exception:
            # Ungefilterte Server-/Provider-Ausnahmen können Zugangsdaten enthalten.
            return self._text("✗ GhostWriter konnte die Anfrage nicht ausführen. Werkzeugzuordnung, Berechtigungen und Basismodell prüfen.",
                              "✗ GhostWriter could not process the request. Check tool bindings, permissions and the base model.")
