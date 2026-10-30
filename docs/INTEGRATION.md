# GPT- und GitHub-Integration

## Ziel

ChatGPT soll das vom Benutzer gewählte Repository lesen und nach ausdrücklicher Freigabe aktualisieren können.

## Bereits vorgesehener MVP-Ablauf: ChatGPT-GitHub-Verbindung

1. Benutzer öffnet die ChatGPT-Einstellungen und den Bereich Apps/Verbindungen.
2. Benutzer wählt GitHub, meldet sich bei GitHub an und autorisiert die Verbindung.
3. Wenn die Oberfläche eine Repository-Auswahl anbietet, wird nur das GhostWriter-Projekt freigegeben.
4. Ghostwriter liest das ausgewählte Repository und prüft mindestens `README.md` und `START.md`.
5. Der Assistent meldet, welches Repository geprüft wurde und ob der Lesezugriff funktioniert.
6. Vor ausdrücklicher Strukturfreigabe werden keine Dateien angelegt oder geändert. Insbesondere wird kein Schreibtest durch einen Dummy-Commit durchgeführt.
7. Nach Freigabe der vollständigen Struktur wird das Zielrepository erneut bestätigt und die erste tatsächliche Schreiboperation ausgeführt. Erfolg wird erst nach Bestätigung durch GitHub gemeldet.

Offizielle Einstiegspunkte:
- [ChatGPT-Einstellungen](https://chatgpt.com/#settings)
- [Hilfe: GitHub mit ChatGPT verbinden](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)

Die Menübezeichnungen und verfügbaren Berechtigungsoptionen können sich je nach ChatGPT-Oberfläche und Verbindungstyp unterscheiden. Der Benutzer autorisiert den Zugriff selbst. Ghostwriter fordert keine Passwörter oder persönlichen Zugriffstokens im Chat an und speichert keine Secrets in Projektdateien.

## Wichtige Abgrenzung

Die ChatGPT-GitHub-Verbindung ist nicht dasselbe wie eine eigens entwickelte GhostWriter-GPT-Action oder eine eigene GitHub-App. Eine verbundene GitHub-App macht den Inhalt von `START.md` auch nicht automatisch zum Systemprompt eines Chats und stellt keine hier beschriebenen GhostWriter-spezifischen API-Operationen bereit. Ein normaler Markdown-Link lädt Dateiinhalte nicht automatisch in den Chat.

## MVP ohne maßgeschneiderte Action

Der Wizard läuft im Chat. Die Kapitelstruktur wird zunächst im Dialog entwickelt. Je nach verfügbaren Connector-Funktionen kann der Benutzer Dateien manuell übernehmen oder ein verbundenes GitHub-Werkzeug verwenden. Ohne bestätigten Schreibzugriff liefert der Assistent vollständige Dateiinhalte bzw. ein Paket aus und behauptet keinen Commit.

## Spätere Integration

Für einen vollständig automatisierten GhostWriter-Workflow ist eine explizite Schnittstelle erforderlich, beispielsweise:
- eine eigene GitHub App oder ein OAuth-basierter Dienst mit minimal erforderlichen Repository-Berechtigungen;
- eine GPT Action mit dokumentiertem API-Schema;
- eine eindeutige Zuordnung zum vom Benutzer ausgewählten Repository;
- nachvollziehbare Commits oder Pull Requests;
- sichere Verwaltung von Tokens/Secrets außerhalb von Prompts und Repositorydateien.

## GitHub Actions

Actions sind für Validierung und größere Verarbeitungsschritte gedacht, nicht als impliziter Listener für Chatnachrichten. Ein GPT benötigt eine explizite API-Schnittstelle, um Dateien zu lesen/schreiben oder einen Workflow via `workflow_dispatch` auszulösen.

## Geplante Operationen

- `get-project`
- `initialize-project`
- `update-project-metadata`
- `create-chapter`
- `update-chapter`
- `create-section`
- `update-section`
- `move-section`
- `reorder-sections`
- `split-section`
- `archive-section`
- `save-research-run`
- `save-brainstorming-run`
- `save-manuscript`
- `save-fact-check-report`
- `approve-section`
- `assemble-chapter`
- `submit-chapter-for-approval`
- `approve-chapter`

## Sicherheits- und Datenregeln

- Repository-Ziel vor jeder Schreiboperation eindeutig bestätigen.
- Nur die erforderlichen Berechtigungen anfordern.
- Keine Secrets oder Tokens in Prompts oder Repositorydateien speichern.
- Vor destruktiven Änderungen Bestätigung einholen.
- Keine bereits freigegebenen Inhalte stillschweigend überschreiben.
- Bei fehlgeschlagenen Schreiboperationen den tatsächlichen Status mitteilen.
