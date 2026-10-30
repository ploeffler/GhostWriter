# GPT- und GitHub-Integration

## Ziel

ChatGPT soll das vom Benutzer gewählte Repository lesen und nach Freigabe aktualisieren können.

## MVP ohne Integration

Der Wizard läuft im Chat. Die Kapitelstruktur wird als Dateiinhalte bzw. Paket ausgegeben und vom Benutzer ins Repository übernommen.

## Spätere Integration

Bevorzugter Ansatz:
- GitHub App oder OAuth-basierte Anbindung mit minimal erforderlichen Repository-Berechtigungen;
- Benutzer bestätigt die konkrete Repository-URL;
- Ghostwriter liest Projektdateien und `ghostwriter.yml`;
- Änderungen werden als nachvollziehbare Commits oder Pull Requests vorgeschlagen;
- Schreibzugriff erfolgt nur auf das ausdrücklich ausgewählte Benutzerrepository.

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

- Repository-Ziel vor Schreiboperationen eindeutig bestätigen.
- Nur die erforderlichen Berechtigungen anfordern.
- Keine Secrets oder Tokens in Prompts oder Repositorydateien speichern.
- Vor destruktiven Änderungen Bestätigung einholen.
- Keine bereits freigegebenen Inhalte stillschweigend überschreiben.
- Bei fehlgeschlagenen Schreiboperationen den tatsächlichen Status mitteilen.
