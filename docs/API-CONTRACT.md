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
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/writing-approval | Schreibfreigabe nach Zustimmung erteilen |
| DELETE | /v1/projects/{owner}/{repo}/sections/{section_id}/writing-approval | Schreibfreigabe zurücknehmen |
| POST | /v1/projects/{owner}/{repo}/matter | Teil von Vor- oder Nachspann anlegen (`kind`, `title`; #57) |
| POST | /v1/projects/{owner}/{repo}/characters | Figur anlegen (`name`, `role`; #53) |
| POST | /v1/projects/{owner}/{repo}/sections/{section_id}/images | Bild ablegen (Datei, Bildunterschrift, Herkunft; #54) |
| POST | /v1/projects/{owner}/{repo}/images/{image_id}/approve | Bild nach Zustimmung freigeben |
| DELETE | /v1/projects/{owner}/{repo}/images/{image_id}/approve | Bildfreigabe zurücknehmen |
| PATCH | /v1/projects/{owner}/{repo}/characters/{character_id} | Figur speichern (alle Felder; die ID bleibt) |
| PATCH | /v1/projects/{owner}/{repo}/matter/{matter_id} | Titel, Ziel und Text eines Teils speichern, bei Vorwort und Nachwort auch Verfasser und Ort/Datum (nie Freigaben) |
| PATCH | /v1/projects/{owner}/{repo}/matter/{matter_id}/glossary | Glossar-Einträge aufnehmen, ändern oder entfernen; doppelte Begriffe werden abgelehnt (#58) |
| POST | /v1/projects/{owner}/{repo}/matter/{matter_id}/writing-approval | Schreibfreigabe eines Teils nach Zustimmung erteilen |
| DELETE | /v1/projects/{owner}/{repo}/matter/{matter_id}/writing-approval | Schreibfreigabe eines Teils zurücknehmen |
| POST | /v1/projects/{owner}/{repo}/matter/{matter_id}/approve | Teil nach Zustimmung freigeben |
| DELETE | /v1/projects/{owner}/{repo}/matter/{matter_id}/approve | Freigabe eines Teils zurücknehmen |
| DELETE | /v1/projects/{owner}/{repo}/sections/{section_id}/approve | Abschnittsfreigabe zurücknehmen |
| DELETE | /v1/projects/{owner}/{repo}/chapters/{chapter_id}/approve | Kapitelfreigabe zurücknehmen |
| PATCH | /v1/projects/{owner}/{repo} | Projektdaten ändern (`project.update`) |
| PATCH | /v1/projects/{owner}/{repo}/settings | Projekteinstellungen ändern (`project.settings.update`) |
| POST | /v1/projects/{owner}/{repo}/chapters/reorder | Kapitelreihenfolge ändern (`chapter.reorder`) |
| POST | /v1/projects/{owner}/{repo}/chapters/{chapter_id}/sections/reorder | Abschnittsreihenfolge eines Kapitels ändern (`section.reorder`) |
| POST | /v1/projects/{owner}/{repo}/chapters/{chapter_id}/research-runs | Kapitelrecherche unveränderlich speichern (`chapter.research.start`) |
| PATCH | /v1/projects/{owner}/{repo}/chapters/{chapter_id} | auch Ziel und Kurzbeschreibung allein (`chapter.texts.update`) |
| POST | /v1/projects/{owner}/{repo}/chapters/{chapter_id}/sections | auch mehrere vorgeschlagene Abschnitte am Ende in einem Commit (`chapter.sections.add`) |
| GET | /v1/projects/{owner}/{repo}/changes | Offene Änderungen: Arbeits-Branch, Pull Request, Commits |
| POST | /v1/projects/{owner}/{repo}/books | Neues Buch in einer Bibliothek anlegen: Branch `buch/<slug>` vom Standard-Branch, ein Commit „Neues Buch angelegt“ (`library.book.create`, #38) |
| POST | /v1/projects/{owner}/{repo}/series | Serie anlegen: `series/<ser-id>/series.yml` auf dem Standard-Branch (`series.create`, #116) |
| PATCH | /v1/projects/{owner}/{repo}/series/{series_id} | Serie ändern; die ID bleibt (`series.update`) |
| POST | /v1/projects/{owner}/{repo}/series/{series_id}/volumes | Buch als nächsten Band hinzufügen (`series.volume.add`); ein Buch gehört zu höchstens einer Serie |
| DELETE | /v1/projects/{owner}/{repo}/series/{series_id}/volumes/{branch} | Band entfernen, das Buch bleibt (`series.volume.remove`) |
| POST | /v1/projects/{owner}/{repo}/series/{series_id}/reorder | Bandreihenfolge ändern (`series.reorder`) |
| PATCH | /v1/projects/{owner}/{repo}/series/{series_id}/characters/{character_id} | Figur der Serie ändern (`character.series.update`) |
| POST | /v1/projects/{owner}/{repo}/characters/{character_id}/detach | Kopie einer Figur der Serie im Buch anlegen (`character.detach`) |
| POST | /v1/projects/{owner}/{repo}/characters/{character_id}/align | Kopie entfernen, wieder die Figur der Serie (`character.align`) |
| POST | /v1/projects/{owner}/{repo}/characters/{character_id}/adopt | Figur des Buchs in die Serie übernehmen; zwei Commits (`character.adopt`) |
| POST | /v1/projects/{owner}/{repo}/matter/{matter_id}/glossary/from-series | Begriff der Serie ins Glossar des Buchs (`matter.glossary.from_series`) |
| POST | /v1/projects/{owner}/{repo}/series/{series_id}/glossary | Begriff in die Serie aufnehmen bzw. ändern (`matter.glossary.to_series`) |
| PUT | /v1/projects/{owner}/{repo}/series/{series_id}/omnibus | Sammelband anlegen bzw. ändern (`series.omnibus.update`) |
| POST | /v1/projects/{owner}/{repo}/series/{series_id}/omnibus/approve | Sammelband freigeben (`series.omnibus.approve`) |
| DELETE | /v1/projects/{owner}/{repo}/series/{series_id}/omnibus/approve | Freigabe zurücknehmen (`series.omnibus.revoke`) |
| POST | /v1/projects/{owner}/{repo}/series/{series_id}/omnibus/editions | Nächste Auflage des Sammelbands (`series.omnibus.publish`) |
| POST | /v1/projects/{owner}/{repo}/analyses | Analyse im Hintergrund starten (`analysis.start`, #123); Ergebnis unter `analysis/` im Buch-Branch |
| POST | /v1/projects/{owner}/{repo}/characters/suggestions | Ausgewählte Figuren aus dem Text übernehmen: anlegen, leere Felder ergänzen, Abschnitten zuordnen (`character.suggest.apply`) |
| POST | /v1/projects/{owner}/{repo}/changes/merge | Offene Änderungen nach Bestätigung übernehmen (`changes.merge`) |

## Projektdaten im Lese-Endpunkt

`GET /v1/projects/{owner}/{repo}` liefert die Projektfelder aus `ghostwriter.yml`, wie sie `docs/DATA-MODEL.md` beschreibt, darunter `title`, `title_short`, `author`, `description_short`, `description` und `current_edition`, den Buchsatz `typesetting` (mit Vorgaben ergänzt), dazu `structure.chapters` mit Kapiteln und Abschnitten. Die Endpunkte für Projektdaten, Projekteinstellungen und Reihenfolgen stehen oben als Entwurf; die Aktionen und ihre Daten stehen in `templates/ui/BEFUELLUNG.md`. Gibt es offene Änderungen, liest der Endpunkt vom Arbeits-Branch und liefert zusätzlich `pending_changes` (Pull-Request-Nummer und -URL, Anzahl und Nachrichten der Commits) und `head_sha` des gelesenen Stands. Für Abschnitte werden die offenen Marker im Manuskript je Art gezählt (`anekdote`, `quelle`, `medizin`, `recht`), damit Kapitelansicht und Abschnittsformular sie anzeigen können. Kapitel und Abschnitte liefert der Endpunkt in derselben Struktur wie `ghostwriter-index.json` (Feld `chapters`, siehe `scripts/build_index.py`); ist die Datei im gelesenen Stand aktuell, kann er sie unverändert ausliefern.

## KI-API-Kosten

Nur das Backend erzeugt Kosteneinträge, und nur für kostenpflichtige KI-Anbieteraufrufe, die es selbst ausführt (#13). Verwaltungsanfragen (lesen, speichern, Übersichten) und Arbeit im Chat über Abos erzeugen keine. Für jeden solchen Aufruf hängt das Backend im selben Commit wie das Ergebnis einen Eintrag an `chapters/<kapitel>/costs/<abschnitt>.yml` (bzw. `costs/project.yml`) an: `source: backend_api`, projektweit eindeutige `activity_id` (Idempotenzschlüssel; ein zweiter Aufruf mit derselben `activity_id` wird abgelehnt statt doppelt gezählt), `run_id` des Laufs, `request_id` des Anbieters, Nutzungsmengen und Preisgrundlage. Fehlen Nutzungsdaten, Status `estimated` bzw. `unavailable`, nie als tatsächliche Kosten.

## Gemeinsame Schreibregeln
Jeder schreibende Request enthält expected_head_sha, idempotency_key und die fachlichen Nutzdaten. Der Dienst validiert Repository-Berechtigung, IDs, Statusübergänge und Freigabevoraussetzungen. Bei einem SHA-Konflikt antwortet er mit 409 Conflict und dem aktuellen Head-SHA. Ein Konflikt liegt nur vor, wenn seit `expected_head_sha` eine der Dateien geändert wurde, die die Operation schreibt; Änderungen an anderen Dateien werden übernommen. Der Assistent liest den neuen Stand und klärt den Konflikt, bevor er erneut schreibt.

Schreibweg wie in `START.md`, „Schreiben ins Repository“: Der Dienst schreibt nie direkt auf den Buch-Branch. Jede Operation ist ein Commit im Arbeits-Branch `ghostwriter/<buch-branch>`; fehlt er, legt der Dienst ihn samt Pull Request an. `POST …/changes/merge` mergt nur mit `confirmed: true` aus einer ausdrücklichen Bestätigung im Chat, mit Merge-Commit, und löscht danach den Arbeits-Branch.

Erfolgsantworten enthalten mindestens success, commit_sha, commit_url, updated_paths, project_head_sha und pull_request_url. Fehlerantworten enthalten einen stabilen Fehlercode, eine kurze Erklärung und eine sichere nächste Aktion. Keine Secrets oder Stacktraces zurückgeben.

## Freigaberegeln
- initialize nur nach Freigabe der vollständigen Kapitel- und Abschnittsstruktur.
- Manuskriptänderungen nur nach Schreibfreigabe für den betreffenden Abschnitt.
- Abschnittsfreigabe nur, nachdem der Benutzer den finalen Abschnittstext gesehen und ausdrücklich freigegeben hat.
- Kapitelzusammenführung nur, wenn alle Abschnitte approved sind.
- Kapitel-Freigabe nur nach Sichtung und ausdrücklicher Gesamtzustimmung.
- Ein technischer API-Aufruf ersetzt niemals die Zustimmung des Benutzers.
- Freigabe-Endpunkte verlangen `confirmed: true` aus der Bestätigung im Chat und hängen einen Eintrag an `approvals.yml` an (`kind`, `id`, `action`, `at`, `by`, `commit` = `expected_head_sha`); Schreib-Endpunkte ändern `approvals` nie.

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

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
