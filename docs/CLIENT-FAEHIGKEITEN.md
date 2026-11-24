# Clients und Fähigkeiten

Stand: 24. November 2026, Programmversion 0.9.0. Diese Seite sagt je Client, was GhostWriter **darstellt** und **ausführt**, was nicht geht und was noch ungeprüft ist. Sie beantwortet die Frage aus #555. Was dort als Ziel steht (interaktive Ansichten für ChatGPT und Codex), ist unten ausdrücklich als **Planung** gekennzeichnet und **nicht verfügbar**.

Aus dem Namen eines Programms folgt weder Unterstützung noch Unmöglichkeit. Maßgeblich ist, was in der jeweiligen Umgebung tatsächlich ankommt. Die Matrix ändert sich mit Programm- und Clientständen; prüfe sie vor wichtigen Arbeiten in deiner eigenen Sitzung.

## Legende

| Zeichen | Bedeutung |
|---|---|
| ✅ | verfügbar: im Programm umgesetzt und dokumentiert |
| ❌ | nicht verfügbar |
| ⏳ | ungeprüft: keine belastbare Aussage, auch keine Unmöglichkeit |

„Verfügbar“ ist keine Abnahme. Die praktische Abnahme steht im [Testplan v1.0](TESTPLAN-v1.0.md) und ist dort je Client mit Datum eingetragen; offene Zugänge sind dort als ⏳ ausgewiesen.

## Fünf verschiedene Fähigkeiten

Sie werden oft verwechselt:

1. **Text und Markdown:** Jede Ansicht gibt es als Textfassung (`render_view.py … --text`). Das geht überall.
2. **Datei- oder Vorschaupanel:** zeigt eine Datei an. Das ist kein GhostWriter-Widget. Im Dateipanel von Codex bedeutet `queued` nur „zur Anzeige vorgemerkt“; die Datei kann lokal vorhanden sein, ohne dass du sie im Panel öffnen kannst. GhostWriter meldet eine Datei erst als geöffnet, wenn die Anzeige bestätigt ist, sonst nennt es nur den Pfad.
3. **Native Auswahlfragen:** Frageelemente des Clients. GhostWriter nutzt sie, wo sie vorhanden sind, und bietet sonst Text an.
4. **GhostWriter-Widget:** die interaktive Ansicht aus [ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui) (`GW.render`). Sie braucht einen Client, der sie darstellt (`chat_widgets: true` in `providers.yml`, derzeit Claude). GhostWriter gibt nie HTML oder Widget-Code als Text aus.
5. **Installierte Integration (MCP-App, Plugin):** eine eigene Oberfläche in einem Client. Ein vorhandenes Dateiwerkzeug oder ein Plugin-System beweist nicht, dass eine GhostWriter-Oberfläche installiert ist.

## Funktionsmatrix

| Fähigkeit | ChatGPT | Codex (Desktop, CLI, IDE) | Claude (claude.ai) | Claude Code | Claude-Web-App | Open WebUI |
|---|---|---|---|---|---|---|
| Textfassung aller Ansichten | ✅ | ✅ | ✅ | ✅ | — (eigene Darstellung) | ✅ |
| Native Auswahlfragen | ⏳ | ⏳ | ⏳ | ⏳ | — | ⏳ |
| GhostWriter-Widgets | ❌ (keine installierte Integration) | ⏳ | ✅ | ⏳ | ✅ (eigene Fassung) | ⏳ (eigener Weg über Pipe und Werkzeug) |
| Datei oder PDF im Client anzeigen | ⏳ | ⏳ (Panel: `queued` ≠ geöffnet) | ⏳ | ⏳ | — | ⏳ (Link zum Lauf) |
| Ins Repository schreiben (Branch, Commit, Pull Request) | ✅ (22.11., Weg nicht einzeln belegt) | ✅ (22.11., Weg nicht einzeln belegt) | ✅ (22.11.) | ✅ | ✅ (Commit auf den Arbeits-Branch) | ⏳ (persönlicher Zugang nötig) |
| Freigaben nur mit ausdrücklicher Bestätigung | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hintergrund-Warteschlange ansehen, vorziehen, abbrechen | ⏳ | ✅ (Text) | ✅ (Widget) | ✅ (Text) | ✅ | ⏳ |
| Englische Bedienung | ✅ (Text) | ✅ (Text) | ✅ (Text; Widget mit `--ui-ref`) | ✅ (Text) | ⏳ | ✅ (Text) |

Die Textfassungen erzeugt `render_view.py`; das setzt eine Umgebung voraus, die Skripte ausführen kann (Codex, Claude Code, Arbeitsumgebung). Ohne Skripte arbeitet der Assistent nach `START.md` und liest die Dateien selbst. Die Zeilen zum Schreiben und zur Praxisabnahme stützen sich auf [Testplan v1.0](TESTPLAN-v1.0.md), Abschnitt 1. Zeilen mit „⏳“ sind nicht widerlegt, sondern nicht geprüft.

## Pro Client

- **ChatGPT:** Der eingebaute GitHub-Connector liest nur. Schreiben geht über eine Umgebung mit Schreibrecht (Codex, ChatGPT Work oder ein eigener Connector). Die Ansichten erscheinen als Markdown bzw. native Elemente, soweit der Client sie unterstützt. Einrichtung: [Chat-Apps](CHAT-APPS.md), [Connector einrichten](CONNECTOR-SETUP.md).
- **Codex (Desktop, CLI, IDE):** liest `AGENTS.md` und die Skills im Repository selbst. Desktop, CLI und IDE sind getrennt zu betrachten; eine Aussage für die eine Variante gilt nicht für die anderen. Einrichtung: [Chat-Apps](CHAT-APPS.md).
- **Claude (claude.ai):** zeigt die GhostWriter-Widgets. Schreiben über Arbeitsumgebung oder GitHub-Connector.
- **Claude Code:** lädt die Skills des Repositorys; Schreiben über die Arbeitsumgebung.
- **Claude-Web-App:** ein Artefakt in Claude, das dieselben Vorlagen zeigt und Klicks direkt ausführt, über die GitHub-Verbindung des Benutzers. Außerhalb des Lieferumfangs von v1.0 ([D06](ENTSCHEIDUNGEN-v1.0.md#d06--eigene-web-app-ohne-integrierten-modellaufruf)). Funktionen und Grenzen: [apps/claude/README.md](https://github.com/ploeffler/GhostWriter/blob/main/apps/claude/README.md).
- **Open WebUI:** eigener Weg über das GitHub-Werkzeug und die Pipe „GhostWriter Direkt“, ohne lokale GhostWriter-Skripte. Schreiben braucht den persönlichen Zugang des Benutzers. Einrichtung: [Open WebUI](https://github.com/ploeffler/GhostWriter/blob/main/integrations/openwebui/README.md).

## Immer gleich

- Eine Ansicht zu öffnen speichert nichts und erteilt keine Freigabe. Ein Klick erteilt nur die konkret angezeigte Bestätigung.
- Die Ansicht liest den Stand neu. Schreibende Schritte prüfen den aktuellen Stand und lehnen ein veraltetes Formular ab.
- Persönliche Rollen, Abschnittssperren und ausdrückliche Bestätigungen gelten in jedem Client unverändert. Es gibt keinen automatischen Merge.
- Ohne Widget, Panel oder Installation bleibt die vollständige Bedienung über Text.

## Fehlerdiagnose

| Beobachtung | Was es bedeutet | Was zu tun ist |
|---|---|---|
| Das Widget erscheint nicht | Der Client stellt es nicht dar | `Nur Text` sagen; GhostWriter zeigt die Textfassung |
| Eine Datei steht im Panel als `queued` | Die Anzeige ist nur vorgemerkt | Den Pfad nehmen; GhostWriter meldet die Datei nicht als geöffnet |
| Ein Werkzeug ist nicht verbunden | Der Schritt geht in dieser Umgebung nicht | GhostWriter nennt den Schritt und gibt die Dateiinhalte mit Zielpfad aus, damit du selbst committen kannst |
| Open WebUI erkennt die Buchnavigation nicht | Werkzeuge kommen nicht als Callables bei der Pipe an | `Navigation prüfen` (ab Pipe 1.9) zeigt es ohne GitHub- oder Modellaufruf |
| Eine Ansicht wirkt veraltet | Der gelesene Stand hat sich geändert | Ansicht neu öffnen; schreibende Aktionen prüfen den Stand ohnehin |

## Planung (nicht verfügbar)

Dieser Abschnitt ist **keine Zusage und keine Beschreibung vorhandener Funktionen.** Er fasst #555 zusammen:

- Interaktive Bibliotheks-, Buch-, Kapitel- und Abschnittsansichten für ChatGPT, Codex und weitere Clients, gespeist aus denselben Ansichts- und Aktionsdaten wie heute, mit Adaptern je nach tatsächlich verfügbarer Fähigkeit.
- Für ChatGPT ist ein MCP-Apps-UI-Weg zu evaluieren und als installierbare Integration anzubieten. Eine solche Integration braucht voraussichtlich einen gehosteten Server. Eigener Hosting- und Verwaltungsdienst ist nach [D06](ENTSCHEIDUNGEN-v1.0.md#d06--eigene-web-app-ohne-integrierten-modellaufruf) und D09 auf nach v1.0 verschoben; die Hostingfrage ist offen (#525). Keine stillschweigende Freigabe eines neuen Backends.
- Codex Desktop, CLI und IDE sind einzeln zu prüfen; Unterstützung in ChatGPT wird nicht pauschal übertragen.

### Was die OpenAI-Dokumentation belegt (abgerufen am 24.11.2026)

- Ein Plugin besteht aus einem **MCP-Server** mit Werkzeugen für ChatGPT und Codex und einer optionalen Web-Komponente, die in ChatGPT als iframe erscheint. ChatGPT setzt dafür den offenen Standard MCP Apps UI um.
- Die Werkzeuge sollen ohne Komponente nutzbar bleiben, „so ChatGPT and Codex can complete the workflow without UI“. **Für Codex ist in diesen Seiten nur das belegt; eine Darstellung der UI in Codex steht dort nicht.**
- Der Server stellt `/mcp` über Streamable HTTP bereit und muss für ChatGPT **öffentlich per HTTPS** erreichbar sein (Tunnel in der Entwicklung, sonst Deployment). Das ist die Hostingfrage (#525, D06, D09).
- Der Rückkanal der UI läuft über `postMessage` mit `ui/*`, darunter `tools/call` und `ui/message` (Folgenachricht senden). Er entspricht dem heutigen `sendPrompt`-Weg der GhostWriter-Ansichten; Theming, Icons und CSP-Angaben (`connectDomains`, `resourceDomains`, `frameDomains`) wären zusätzlich nötig.
- Die Doku verlangt, **Fähigkeiten zu prüfen statt Produktnamen** abzufragen. Das gilt auch für die Fähigkeitenansicht oben.
- Offen bleibt: Die Ansichtsdaten entstehen heute in einer Umgebung mit Shell (`render_view.py`). Ein MCP-Server müsste sie selbst aus dem Repository erzeugen, mit GitHub-Anmeldung je Benutzer.
- Eine Fähigkeitenansicht im Programm mit Status verfügbar / nicht verfügbar / ungeprüft, Voraussetzung und letzter Abnahme.

## Quellen

- Offizielle OpenAI-Grundlagen laut #555 (am 24.11.2026 direkt abgerufen und gelesen): [App-Quickstart](https://developers.openai.com/plugins/build/app-quickstart) und [ChatGPT-UI](https://developers.openai.com/plugins/build/chatgpt-ui). Der Quickstart trennt MCP-Werkzeuge für ChatGPT und Codex von der optionalen UI in ChatGPT.
- Im Repository: [Chat-Apps](CHAT-APPS.md), [Testplan v1.0](TESTPLAN-v1.0.md), `providers.yml` (`chat_widgets`), `templates/ui/BEFUELLUNG.md` (Darstellungsmodus), `AGENTS.md`.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
