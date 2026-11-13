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

## Dateien im Chat übergeben (#260)

„Manuskript ausgeben“ baut das PDF in der Action „Manuskript ausgeben“; der Chat holt es mit `scripts/fetch_artifact.py` ab und übergibt es als Datei. Stand 11.11.2026, **noch nicht in allen Apps praktisch geprüft**:

| App | Erwarteter Weg |
|---|---|
| Claude mit Arbeitsumgebung | PDF abholen und als Datei im Chat senden |
| Codex | PDF im Arbeitsordner ablegen bzw. anhängen |
| ChatGPT (GitHub-Connector) | abhängig von Connector und Code-Umgebung; sonst Link zum Lauf |
| Open WebUI | Link zum Lauf (`dispatch_workflow` startet `manuscript.yml`) |

Ohne Dateiübergabe bleibt der Link zum Lauf: Download unter *Artifacts*, 14 Tage, mit GitHub-Anmeldung.

**Erprobt am 11.11.2026 (Claude in der Cloud):** Bau und Start funktionieren; das Abholen scheiterte, weil GitHub Artifacts über `*.blob.core.windows.net` ausliefert und die Sitzung diese Adresse sperrt. Abhilfe: die Adresse unter *Einstellungen → Fähigkeiten* erlauben, sonst gilt der Link zum Lauf.

## Lesefassung neben der Ansicht (#289)

Zur Kapitel- und Abschnittsansicht erzeugt der Assistent mit `scripts/assemble.py … reading N` bzw. `N.M` den Text als Markdown-Datei und übergibt sie neben der Ansicht, nach jeder Änderung neu (`START.md`, „Lesefassung“). Stand 13.11.2026:

| App | Weg |
|---|---|
| Claude mit Arbeitsumgebung | Datei senden mit Darstellung „anzeigen“: öffnet sich in der Seitenansicht, nichts wird heruntergeladen (in YAWA erprobt) |
| Codex | Datei im Arbeitsordner nennen |
| ChatGPT (GitHub-Connector) | noch nicht: der Connector liest nur, `assemble.py` läuft nicht; geplant über die Action „Manuskript ausgeben“ (#289, Teil 2) |
| Open WebUI | noch nicht; Abschnittstext wie bisher in der Ansicht |

## Automatisch geladene Hinweise (#136)

Jedes GhostWriter-Repository bringt drei Einstiegsdateien mit, die mit jedem Update aus dem Hauptrepository kommen:

- `CLAUDE.md` – liest Claude von selbst, sobald das Repository in einer Sitzung mit Repository-Zugriff eingebunden ist (Claude Code, auch in claude.ai).
- `AGENTS.md` – dieselben Regeln für andere Assistenten, die diese Datei lesen.
- `.claude/skills/ghostwriter/SKILL.md` – allgemeiner Skill für den Wiedereinstieg.

Dazu kommt je Repository das **Assistenten-Profil** `assistant.yml` mit dem daraus erzeugten persönlichen Skill `.claude/skills/<autor>-auf-<repo>/SKILL.md` (Git-Benutzer, Autor, Standard-Erzählstimme; `START.md`, „Assistenten-Profil“). Beides gehört dem Buch und wird von Updates nie überschrieben.

**Grenzen:** Automatisch geladen wird das nur von Assistenten mit Zugriff auf das Repository, die diese Dateien auch lesen. In reinen Chat-Apps (ChatGPT, Gemini, Copilot, Claude ohne eingebundenes Repository) bleibt der Hinweis in `README.md` der Einstieg; der Assistent liest `START.md` und `assistant.yml` dann beim Wiedereinstieg selbst. In diese Dateien gehören keine Secrets und keine Manuskripttexte.

## Skills auswählen (#261)

Welcher Skill zu einer Aufgabe passt, entscheidet Claude anhand der Skill-Beschreibungen. Der Benutzer sieht das sonst nicht, und bei ähnlichen Beschreibungen ist die Wahl nicht eindeutig. Deshalb gilt für GhostWriter (`CLAUDE.md`, `AGENTS.md`, Skill `ghostwriter`):

- **Wahl nennen:** Zu Beginn einer Aufgabe nennt Claude in einem Satz, welchen Skill es verwendet, oder dass keiner passt.
- **Spezifischer vor allgemein:** Der persönliche Skill des Repositorys (`assistant.yml` → `skill`) geht vor dem allgemeinen Skill `ghostwriter`. `ghostwriter` ist für Buch- und Bibliotheks-Repositorys gedacht, nicht für Programmarbeit am Hauptrepository. Nur bei echter Mehrdeutigkeit fragt Claude einmal kurz nach.
- **Nicht doppelt laden:** Jeder Ladevorgang setzt die ganze Anleitung erneut in den Verlauf. Das kostet Kontext, und der Verlauf wird früher zusammengefasst. Liegt die Anleitung im Gespräch noch vor, lädt Claude sie nicht erneut. Fehlt sie nach dem Zusammenfassen eines langen Verlaufs, lädt Claude sie neu und sagt das kurz.

**Skills im Konto:** Skills, die im Claude-Konto liegen (nicht im Repository), kann GhostWriter nicht ändern. Haben zwei davon fast dieselbe Beschreibung (etwa ein älterer Skill für dieselbe Bibliothek neben dem erzeugten persönlichen Skill), den überzähligen in den Claude-Einstellungen unter „Skills“ entfernen. Eine Projektanweisung wie „Bestätige die Skillauswahl“ ist damit nicht mehr nötig, schadet aber nicht.

## Darstellung

- **Claude** zeigt die Vorlagen als Inline-Widgets. Der Assistent gibt nur eine Ladezeile für `ghostwriter-ui` (fester Commit, über jsDelivr) und die Daten aus; das ist deutlich kürzer als die ganze Ansicht. Ein Klick schickt die festgelegte Nachricht in den Chat.
- **ChatGPT** zeigt diese Widgets nicht. Dort gibt der Assistent die Textfassung aus `templates/ui/BEFUELLUNG.md` aus: Markdown mit Tabellen und Symbolen, Aktionen als Kürzel (`2`, `2.4`, `P`, `X` …), die der Benutzer per Antwort wählt. Echte Formulare in ChatGPT gingen nur über eine eigene App mit MCP-Server (Apps SDK), siehe Weg B.
- **Open WebUI** zeigt keine Widgets. Die Pipe „GhostWriter Direkt“ erzeugt alle Ansichten selbst als Markdown und schaltet „Darstellung: einfach / übersichtlich / erweitert“, „Nur Text“ und den Antwortmodus ohne Modellaufruf um (ab Pipe 1.8 mit GitHub-Werkzeug 1.5, #282). Das Gesprächsmodell erhält ab Werkzeug 1.6 einen eigenen kurzen Einstieg `docs/start/einstieg-openwebui.md` statt der allgemeinen `START.md` (#204). Einzelheiten: [Open-WebUI-Anleitung](../integrations/openwebui/README.md#darstellung-und-antwortmodus-direkt-pipe-18-werkzeug-15).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
