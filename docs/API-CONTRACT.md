# GhostWriter API-Vertrag (Entwurf für die GPT-Action)

## Status
Dieser Vertrag beschreibt die geplante Schnittstelle. Er ist noch keine laufende API und enthält keinen Produktiv-Host. Vor Aktivierung müssen ein HTTPS-Dienst, Authentifizierung und eine passende OpenAPI-Spezifikation implementiert werden.

Die GPT-Action kommuniziert ausschließlich mit dem GhostWriter-Dienst. Dieser führt GitHub-Operationen serverseitig aus. Tokens und Passwörter gehören niemals in Prompts, Action-Parameter oder Repositorydateien.

## Grundprinzipien
- Repository-Bindung: Jede Anfrage bezieht sich auf ein vom Benutzer ausgewähltes Repository; der Dienst prüft die Berechtigung serverseitig.
- Minimalrechte: Nur notwendige GitHub-Rechte anfordern.
- Keine freie Dateischreib-API: Die Action nutzt fachliche Operationen und IDs statt beliebiger Pfade.
- Freigabe-Gates: Initialisierung, Manuskriptänderungen und Freigaben nur nach ausdrücklicher Zustimmung im Chat.
- Versionsschutz: Schreibanfragen enthalten expected_head_sha. Bei zwischenzeitlichen Änderungen wird mit HTTP 409 abgebrochen.
- Idempotenz: Schreibanfragen unterstützen Idempotency-Key gegen doppelte Commits oder Läufe.
- Nachvollziehbarkeit: Erfolgreiche Schreiboperationen liefern Commit-SHA und Commit-URL.

## Authentifizierung und Autorisierung
- GPT Action zum GhostWriter-Dienst: OAuth 2.0 oder ein gleichwertiger sicherer Mechanismus über HTTPS.
- GhostWriter-Dienst zu GitHub: serverseitig verwaltetes GitHub-App-Installationstoken oder gleichwertiger Mechanismus mit minimalen Repository-Rechten.
- Bei jeder Anfrage werden Benutzeridentität und Repository-Zugriff serverseitig geprüft.
- Benutzer können Repository-Zugriff explizit verbinden und entziehen.
- Tokens werden serverseitig sicher gespeichert, nie protokolliert und nie an das Modell zurückgegeben.

## Vorgeschlagene Endpunkte

Der detaillierte getrennte OAuth- und GitHub-Verbindungsfluss steht in [OAUTH-FLOW.md](OAUTH-FLOW.md). Die folgenden zusätzlichen Endpunkte sind vorgesehen, aber noch nicht implementiert:

| Methode | Pfad | Zweck |
|---|---|---|
| GET | /v1/account | GhostWriter-Konto und Verbindungsstatus ohne Secrets |
| POST | /v1/github/connections/start | GitHub-Verknüpfung starten |
| GET | /v1/github/connections/callback | Serverseitiger OAuth-Callback |
| GET | /v1/github/repositories | Autorisierte Repositories auflisten |
| DELETE | /v1/github/connections/{connection_id} | Verbindung trennen |

Die Pfade sind Entwurf und müssen mit dem implementierten Dienst übereinstimmen.

| Methode | Pfad | Zweck |
|---|---|---|
| GET | /v1/health | Dienststatus |
| GET | /v1/repositories | Freigegebene Repositories des Benutzers |
| GET | /v1/projects/{owner}/{repo} | Projektmetadaten, Konfiguration, Struktur und Commit lesen |
| POST | /v1/projects/{owner}/{repo}/initialize | Freigegebene Buchstruktur initialisieren |
| POST | /v1/projects/{owner}/{repo}/chapters | Kapitel anlegen |
| PATCH | /v1/projects/{owner}/{repo}/chapters/{chapter_id} | Kapitelmetadaten aktualisieren |
| POST | /v1/projects/{owner}/{repo}/chapters/{chapter_id}/sections | Abschnitt anlegen |
| PATCH | /v1/projects/{owner}/{repo}/sections/{section_id} | Abschnittsdaten oder Status aktualisieren |
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/move | Abschnitt verschieben |
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/archive | Abschnitt nach Bestätigung archivieren |
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/research-runs | Recherchelauf unveränderlich speichern |
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/brainstorming-runs | Brainstorminglauf unveränderlich speichern |
| PUT | /v1/projects/{owner}/{repo}/sections/{section_id}/manuscript | Manuskriptentwurf speichern |
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/fact-check-reports | Fact-Checking-Bericht speichern |
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/approve | Abschnitt nach Zustimmung freigeben |
| POST | /v1/projects/{owner}/{repo}/chapters/{chapter_id}/assemble | Kapitel aus freigegebenen Abschnitten zusammenführen |
| POST | /v1/projects/{owner}/{repo}/chapters/{chapter_id}/approve | Kapitel nach Gesamtzustimmung freigeben |

## Gemeinsame Schreibregeln
Jeder schreibende Request enthält expected_head_sha, idempotency_key und die fachlichen Nutzdaten. Der Dienst validiert Repository-Berechtigung, IDs, Statusübergänge und Freigabevoraussetzungen. Bei einem SHA-Konflikt antwortet er mit 409 Conflict und dem aktuellen Head-SHA. Der Assistent liest den neuen Stand und klärt den Konflikt, bevor er erneut schreibt.

Erfolgsantworten enthalten mindestens success, commit_sha, commit_url, updated_paths und project_head_sha. Fehlerantworten enthalten einen stabilen Fehlercode, eine kurze Erklärung und eine sichere nächste Aktion. Keine Secrets oder Stacktraces zurückgeben.

## Freigaberegeln
- initialize nur nach Freigabe der vollständigen Kapitel- und Abschnittsstruktur.
- Manuskriptänderungen nur nach Schreibfreigabe für den betreffenden Abschnitt.
- Abschnittsfreigabe nur, nachdem der Benutzer den finalen Abschnittstext gesehen und ausdrücklich freigegeben hat.
- Kapitelzusammenführung nur, wenn alle Abschnitte approved sind.
- Kapitel-Freigabe nur nach Sichtung und ausdrücklicher Gesamtzustimmung.
- Ein technischer API-Aufruf ersetzt niemals die Zustimmung des Benutzers.

## Statuscodes
| HTTP | Bedeutung |
|---|---|
| 200 | Lesen oder Aktualisieren erfolgreich |
| 201 | Ressource angelegt bzw. Commit erstellt |
| 400 | Ungültige Eingabe oder Statusübergang |
| 401 | Authentifizierung fehlt/ungültig |
| 403 | Fehlende Berechtigung |
| 404 | Repository oder Ressource nicht gefunden/freigegeben |
| 409 | Projekt-Head geändert oder Idempotenzkonflikt |
| 422 | Fachliche Validierung fehlgeschlagen |
| 429 | Rate Limit |
| 5xx | Dienst- oder GitHub-Fehler |

## Vor der Implementierung zu entscheiden
- Hosting und Domain des API-Dienstes;
- OAuth-Fluss und Benutzerkontenmodell;
- GitHub App und minimale Rechte;
- exakte JSON-Schemas und OpenAPI-3.x-Spezifikation;
- Commit direkt auf Branch oder Pull Request;
- Audit-, Datenschutz- und Aufbewahrungsregeln;
- automatisierte Tests und Deployment.

## Umsetzungsschritte
1. API-Dienst und Authentifizierung entwerfen.
2. GitHub-App mit minimalen Rechten einrichten.
3. Leseoperationen implementieren und testen.
4. SHA-geschützte Schreiboperationen implementieren.
5. OpenAPI aus dem tatsächlich implementierten Dienst erzeugen.
6. GPT-Action konfigurieren und mit Testrepository prüfen.
7. Erst danach die Action als einsatzbereit dokumentieren.