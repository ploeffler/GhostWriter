# Chat-Apps für GhostWriter v0.5

Stand: 31.10.2026. Vorrangig unterstützt werden Claude und ChatGPT. Funktionen der Chat-Apps ändern sich laufend; vor dem Einsatz prüfen.

## Ergebnis

Die **eingebauten GitHub-Verbindungen** beider Apps können nur lesen. Für Weg A braucht GhostWriter aber Schreibzugriff: Commits auf einen Arbeits-Branch, Pull Request anlegen und mergen, Tag und Release anlegen.

| Fähigkeit | Claude: eingebaute GitHub-Integration | Claude mit Arbeitsumgebung (agentische Sitzung, Claude Code) | ChatGPT: GitHub-Connector | ChatGPT: Codex | Eigener Connector mit GitHubs MCP-Server (beide Apps) |
|---|---|---|---|---|---|
| Repository lesen | ja (Dateien eines Branches) | ja | ja | ja | ja |
| Commit, Branch | nein | ja | nein | ja | laut Werkzeugliste vorgesehen, im Chat zu testen |
| Pull Request anlegen | nein | ja | nein | ja | zu testen |
| Pull Request mergen | nein | ja | nein | nicht belegt | zu testen |
| Tag und Release anlegen | nein | nein: in der Sitzung vom 31.10.2026 von GitHub abgelehnt („not permitted for this session type“), ebenso Branches löschen | nein | nicht belegt | nicht belegt |
| Chat-Vorlagen als Widget mit Rückmeldung in den Chat | ja (Inline-Widgets) | ja, wenn die Sitzung Widgets anbietet | nein, Textfassung nötig | nein | wie die jeweilige App |

Belege:
- Claude: Die GitHub-Integration synchronisiert nur Dateinamen und Inhalte eines Branches, ohne Commit-Historie und Pull Requests ([Anthropic-Hilfe: Use the GitHub integration](https://support.claude.com/en/articles/10167454-use-the-github-integration)).
- ChatGPT: Der GitHub-Connector in Chat und Deep Research ist zum Lesen gedacht; Codex kann Branches pushen und Pull Requests öffnen ([Übersicht vom 9.7.2026](https://www.usecarly.com/blog/chatgpt-github-integration/)). Die Hilfeseite von OpenAI ([Connecting GitHub to ChatGPT](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)) war beim Abruf nicht erreichbar.
- GitHubs offizieller MCP-Server ist unter `https://api.githubcopilot.com/mcp/` erreichbar und hat Werkzeuggruppen für Repositories und Pull Requests; für Claude Desktop und Claude Code gibt es Anleitungen, für claude.ai und ChatGPT als eigener Connector ist eine eigene OAuth-App nötig ([github-mcp-server](https://github.com/github/github-mcp-server), [Diskussion zu claude.ai](https://github.com/anthropics/claude-ai-mcp/issues/98)).

## Schreibwege für Weg A

1. **Claude mit Arbeitsumgebung.** Commits, Branches, Pull Requests und Merge funktionieren heute, ebenso die Widgets; Tags und Releases nicht. Abhängig von der Claude-App mit agentischen Sitzungen.
2. **Eigener Connector mit GitHubs MCP-Server** in Claude und ChatGPT. Einmalige OAuth-Einrichtung je App; welche Schreibwerkzeuge im Chat verfügbar sind, muss praktisch getestet werden. Anleitung: [CONNECTOR-SETUP.md](CONNECTOR-SETUP.md).
3. **Rückfall** aus `docs/INTEGRATION.md`, Betriebsart B: Der Assistent gibt geänderte Dateien vollständig aus, der Benutzer committet selbst. Funktioniert überall, aber ohne Pull-Request-Ablauf aus dem Chat.

Keiner der Wege legt verlässlich Tags und Releases an. Vorschlag: Eine Auflage wird ein Pull Request, der `project.current_edition` hochzählt und die Release Notes enthält; nach dem Merge legt eine GitHub Action Tag und Release an und hängt PDF, DOCX und EPUB an (Issues #16 und #17).

Welcher Weg für v0.5 gilt, wird am Ende von v0.2 entschieden.

## Darstellung

- **Claude** zeigt die Vorlagen als Inline-Widgets. Der Assistent gibt nur eine Ladezeile für `ghostwriter-ui` (fester Commit, über jsDelivr) und die Daten aus; das ist deutlich kürzer als die ganze Ansicht. Ein Klick schickt die festgelegte Nachricht in den Chat.
- **ChatGPT** zeigt diese Widgets nicht. Dort gibt der Assistent die Textfassung aus `templates/ui/BEFUELLUNG.md` aus: Markdown mit Tabellen und Symbolen, Aktionen als Kürzel (`2`, `2.4`, `P`, `X` …), die der Benutzer per Antwort wählt. Echte Formulare in ChatGPT gingen nur über eine eigene App mit MCP-Server (Apps SDK), siehe Weg B.
