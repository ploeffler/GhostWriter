# Chat- und GitHub-Integration

## In-Chat-Version (MVP, anbieterunabhängig)

Die In-Chat-Version funktioniert mit jedem KI-Chat-Assistenten, der die Anweisungen in `START.md` befolgen kann. Je nach Fähigkeiten der Chat-Anwendung gibt es zwei Betriebsarten:

**A – mit GitHub-Anbindung der Chat-Anwendung**
1. Benutzer öffnet die Einstellungen seiner Chat-Anwendung (meist Verbindungen, Integrationen, Apps oder Konnektoren).
2. Benutzer wählt GitHub, meldet sich an und autorisiert die Verbindung.
3. Wenn verfügbar, wird nur das GhostWriter-Repository freigegeben.
4. Ghostwriter liest mindestens README.md und START.md.
5. Der Assistent nennt das geprüfte Repository und bestätigt den tatsächlichen Lesezugriff.
6. Vor ausdrücklicher Strukturfreigabe erfolgen keine Schreiboperationen und kein Dummy-Commit.
7. Nach Freigabe wird das Zielrepository erneut bestätigt. Erfolg wird erst nach GitHub-Bestätigung gemeldet.

**B – ohne GitHub-Anbindung**
1. Benutzer stellt `START.md` (und bei Bedarf weitere Projektdateien) als Anhang oder eingefügten Text bereit.
2. Der Assistent gibt neue oder geänderte Dateien vollständig und mit Dateipfad im Chat aus.
3. Der Benutzer committet selbst und stellt bei späteren Arbeitsschritten den aktuellen Dateistand wieder bereit.
4. Der Assistent behauptet nie, einen Commit ausgeführt zu haben.

Menübezeichnungen, Berechtigungsoptionen und verfügbare Werkzeuge unterscheiden sich je nach Anbieter. Maßgeblich ist die Hilfe des jeweiligen Anbieters. Der Benutzer autorisiert selbst. Ghostwriter fragt keine Passwörter oder persönlichen Tokens im Chat ab.

## Entscheidung für v0.5

GhostWriter v0.5 nutzt ausschließlich die In-Chat-Version, Betriebsart A (mit GitHub-Anbindung der Chat-Anwendung). Die eigene Schnittstelle folgt nach v0.5; wie sie schon jetzt berücksichtigt wird, steht in `docs/ARCHITECTURE.md` unter „Betriebsweg bis v0.5: Weg A“.

## Wichtige Abgrenzung
Die GitHub-Verbindung einer Chat-Anwendung ist nicht dasselbe wie eine eigene GhostWriter-Schnittstelle (API, MCP-Server oder GitHub-App). Sie lädt START.md nicht automatisch als Systemprompt und stellt keine GhostWriter-spezifischen Operationen bereit. Ein Markdown-Link lädt Dateiinhalte nicht automatisch in den Chat.

## Eigene GhostWriter-Schnittstelle
Der fachliche API-Vertrag steht in API-CONTRACT.md. Er beschreibt Endpunkte, Authentifizierung, Versionsschutz, Freigabe-Gates und Fehlerbehandlung. Er ist als anbieterneutraler Dienst gedacht; eine ChatGPT-GPT-Action ist nur einer von mehreren möglichen Clients (siehe OPENAI-INTEGRATION-STRATEGY.md, AUTH0-SETUP.md und OAUTH-FLOW.md für diesen Pfad).

Der Vertrag ist noch kein laufender Dienst. Vor der Anbindung eines Chat-Clients müssen ein erreichbarer HTTPS-API-Dienst, sichere Authentifizierung und eine zur Implementierung passende Schnittstellenbeschreibung (z. B. OpenAPI oder MCP) bereitstehen. Eine Spezifikationsdatei allein führt keine GitHub-Operationen aus.

## GitHub Actions
GitHub Actions eignen sich für Validierung und größere Verarbeitungsschritte, nicht als impliziter Listener für Chatnachrichten. Ein Chat-Assistent benötigt eine explizite Schnittstelle, um Dateien zu lesen/schreiben oder einen Workflow auszulösen.

## Sicherheitsregeln
- Repository-Ziel vor jeder Schreiboperation eindeutig bestätigen.
- Nur notwendige Berechtigungen anfordern.
- Keine Secrets oder Tokens in Prompts oder Repositorydateien speichern.
- Vor destruktiven Änderungen Bestätigung einholen.
- Freigegebene Inhalte nicht stillschweigend überschreiben.
- Bei fehlgeschlagenen Schreiboperationen den tatsächlichen Status mitteilen.