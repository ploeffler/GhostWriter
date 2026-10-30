# GPT- und GitHub-Integration

## ChatGPT-GitHub-Verbindung (MVP)
1. Benutzer öffnet ChatGPT-Einstellungen und den Bereich Apps/Verbindungen.
2. Benutzer wählt GitHub, meldet sich an und autorisiert die Verbindung.
3. Wenn verfügbar, wird nur das GhostWriter-Repository freigegeben.
4. Ghostwriter liest mindestens README.md und START.md.
5. Der Assistent nennt das geprüfte Repository und bestätigt den tatsächlichen Lesezugriff.
6. Vor ausdrücklicher Strukturfreigabe erfolgen keine Schreiboperationen und kein Dummy-Commit.
7. Nach Freigabe wird das Zielrepository erneut bestätigt. Erfolg wird erst nach GitHub-Bestätigung gemeldet.

Offizielle Einstiege:
- ChatGPT-Einstellungen: https://chatgpt.com/#settings
- Hilfe zur GitHub-Verbindung: https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt

Die Menübezeichnungen und Berechtigungsoptionen können variieren. Der Benutzer autorisiert selbst. Ghostwriter fragt keine Passwörter oder persönlichen Tokens im Chat ab.

## Wichtige Abgrenzung
Die ChatGPT-GitHub-Verbindung ist nicht dasselbe wie eine eigene GhostWriter-GPT-Action oder GitHub-App. Sie lädt START.md nicht automatisch als Systemprompt und stellt keine GhostWriter-spezifischen API-Operationen bereit. Ein Markdown-Link lädt Dateiinhalte nicht automatisch in den Chat.

## Eigene GhostWriter-GPT-Action
Der fachliche API-Vertrag steht in API-CONTRACT.md. Er beschreibt Endpunkte, Authentifizierung, Versionsschutz, Freigabe-Gates und Fehlerbehandlung.

Der Vertrag ist noch kein laufender Dienst. Vor Konfiguration einer GPT-Action müssen ein erreichbarer HTTPS-API-Dienst, sichere Authentifizierung und eine zur Implementierung passende OpenAPI-Spezifikation bereitstehen. Eine OpenAPI-Datei allein führt keine GitHub-Operationen aus.

## GitHub Actions
GitHub Actions eignen sich für Validierung und größere Verarbeitungsschritte, nicht als impliziter Listener für Chatnachrichten. Ein GPT benötigt eine explizite API-Schnittstelle, um Dateien zu lesen/schreiben oder einen Workflow auszulösen.

## Sicherheitsregeln
- Repository-Ziel vor jeder Schreiboperation eindeutig bestätigen.
- Nur notwendige Berechtigungen anfordern.
- Keine Secrets oder Tokens in Prompts oder Repositorydateien speichern.
- Vor destruktiven Änderungen Bestätigung einholen.
- Freigegebene Inhalte nicht stillschweigend überschreiben.
- Bei fehlgeschlagenen Schreiboperationen den tatsächlichen Status mitteilen.