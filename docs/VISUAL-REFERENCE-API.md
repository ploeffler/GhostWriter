# API-Vertrag: projektweite visuelle Referenzbilder

**Status:** Architekturvorschlag für Issue #143, noch keine implementierte API.
**Hosting:** anbieterneutral. **Maßgebliche Datenquelle:** GhostWriter-GitHub-Repository.

## 1. Grundsätze

- Referenzen liegen getrennt von Illustrationen unter `reference-images/`.
- GitHub speichert Metadaten und Bilddateien; die erste Ausbaustufe benötigt keinen separaten Cloud-Objektspeicher.
- Upload setzt den Status `stored`; Freigabe ist eine separate, bewusste Aktion.
- Nur freigegebene Referenzen mit Rolle `visual_reference` dürfen ausgewählt werden.
- Auswahl und tatsächliche Übergabe der Bildbytes an den Provider sind getrennte Schritte.
- Rücknahme blockiert neue Aufträge, löscht aber weder Datei noch historische Auftragsprotokolle.
- Referenzen gelangen nie automatisch in Manuskript, Illustrationsbestand oder Buchausgabe.

## 2. Identität und Berechtigungen

Jeder Request benötigt ein Auth0-Access-Token. Die API prüft Signatur, Issuer, Audience, Ablaufzeit und Scope. Auth0-Identität allein gewährt keinen Repositoryzugriff. Zusätzlich sind GhostWriter-Konto, aktive GitHub-App-Installation, Freigabe genau dieses Repositorys und Projekt-/Branch-Zuordnung zu prüfen.

GitHub-Installationstokens bleiben serverseitig. Sie dürfen weder an Client oder Bilddienst weitergegeben noch protokolliert werden.

Vorgesehene Scopes:
- `read:projects` – Referenzen und Metadaten lesen;
- `write:projects` – Upload, Metadatenänderung, Freigabe und Rücknahme;
- `create:image_jobs` – Bildauftrag mit expliziten Referenz-IDs starten.

## 3. Speicherung und Schreibweg

Erste Ausbaustufe: GitHub ist Speicher und Versionshistorie.
- Bild: `reference-images/<ref-id>.<png|jpg>`
- Metadaten: `reference-images/<ref-id>.yml`
- Änderungen erfolgen auf dem GhostWriter-Arbeitsbranch, nicht direkt auf dem Buch-Standardbranch.
- Die API erstellt/aktualisiert einen PR; „Änderungen übernehmen“ bleibt der maßgebliche Merge-Schritt.
- Datei und Metadaten bilden einen logischen Änderungssatz. Es darf kein Metadatensatz auf eine nicht gespeicherte Datei zeigen.
- Vor dem Commit: tatsächliche PNG/JPEG-Signatur, Größenlimit, Bilddekodierung, Abmessungen und SHA-256 prüfen. SVG, HTML, ausführbare und unbekannte Formate ablehnen.
- Konfigurierbares Uploadlimit; Startwert 10 MiB je Bild. GitHub-Grenzen gelten zusätzlich.

GitHub-Contents-/Git-Data-Aufrufe werden hinter einem Repository-Storage-Interface gekapselt. So kann später ein anderer Speicher ergänzt werden, ohne API-Vertrag oder Clientfluss zu ändern.

## 4. HTTP-Endpunkte

Alle Pfade relativ zu `/v1`; IDs sind opaque und keine frei definierbaren Dateipfade.

| Methode und Pfad | Zweck | Scope |
|---|---|---|
| `GET /projects/{project_id}/reference-images` | Liste, Status, Rollen, Links, Hash, Version | `read:projects` |
| `POST /projects/{project_id}/reference-images` | Upload; Status zunächst `stored` | `write:projects` |
| `GET /projects/{project_id}/reference-images/{id}` | Metadaten | `read:projects` |
| `GET /projects/{project_id}/reference-images/{id}/content` | Bildbytes nach Berechtigungsprüfung | `read:projects` |
| `PATCH /projects/{project_id}/reference-images/{id}` | Beschreibung, Herkunft, Rechte, Links | `write:projects` |
| `POST /projects/{project_id}/reference-images/{id}/approve` | explizite Freigabe | `write:projects` |
| `POST /projects/{project_id}/reference-images/{id}/withdraw` | Rücknahme | `write:projects` |
| `POST /projects/{project_id}/image-jobs` | Bildauftrag mit Provider, Modell und Referenz-IDs | `create:image_jobs` |
| `GET /projects/{project_id}/image-jobs/{job_id}` | Status und Übergabeprotokoll | `read:projects` |

### Upload-Vertrag

`POST .../reference-images` nutzt `multipart/form-data`:
- `file`: PNG/JPEG-Bildbytes;
- `metadata`: JSON mit `caption`, `description`, `purpose`, `origin`, `license`, `consent`, `roles`, `links`.

Erfolg: `201` mit ID, SHA-256, Größe, Abmessungen, Status `stored` und PR-/Branch-Information. Keine automatische Freigabe.

### Bildauftrag und Übergabe

Der Auftrag enthält Zielabschnitt, Provider-ID, Modell-ID, Szene/Prompt und geordnete Referenz-IDs. Der Server löst jede ID erneut auf und prüft Projektzugehörigkeit, Freigabe, Rolle, Datei und Hash. Die Bildbytes werden serverseitig geladen und nur übertragen, wenn die konkrete Modell-/Endpoint-Kombination Bildinput unterstützt.

Das unveränderliche Laufprotokoll nennt ID, Git-Commit/Dateiversion, SHA-256 und tatsächlichen Übergabestatus. Nicht unterstützte Provider liefern `PROVIDER_IMAGE_INPUT_UNSUPPORTED`; Referenzen dürfen nicht stillschweigend weggelassen oder als verwendet protokolliert werden.

## 5. Providerfähigkeit

Bildinput ist eine Fähigkeit des konkreten Modells und Endpoints, nicht pauschal eines Unternehmens. Capability:
- `supported`: für dieses Modell/Endpoint getestet;
- `unsupported`: nimmt keine Bildreferenzen an;
- `unknown`: nicht verifiziert; Übergabe wird blockiert.

Providerlimits werden vor dem Senden geprüft. API-Schlüssel kommen ausschließlich aus serverseitiger Secret-Verwaltung. Bildbytes und personenbezogene Referenzmetadaten gehören nicht in normale Logs.

## 6. Versionierung und Rücknahme

Eine Referenz-ID bezeichnet die logische Referenz. Jede geänderte Bilddatei erhält eine neue konkrete Version mit SHA-256 und Git-Commit; historische Versionen werden nicht überschrieben. Bildaufträge bleiben auf ihre ursprünglichen Hashes/Commits bezogen. Rücknahme setzt `withdrawn` und blockiert neue Aufträge, verändert aber keine alten Protokolle. Rücknahme ist keine Löschung.

## 7. Fehlercodes

| HTTP | Code | Bedeutung |
|---|---|---|
| 401 | `UNAUTHENTICATED` | Token ungültig/abgelaufen |
| 403 | `PROJECT_ACCESS_DENIED` | kein Zugriff auf dieses Projekt |
| 404 | `REFERENCE_NOT_FOUND` | Referenz fehlt oder gehört anderem Projekt |
| 409 | `REFERENCE_NOT_APPROVED` | nicht freigegeben/zurückgezogen |
| 413 | `IMAGE_TOO_LARGE` | Größenlimit überschritten |
| 415 | `UNSUPPORTED_IMAGE_FORMAT` | kein PNG/JPEG |
| 422 | `INVALID_IMAGE` | beschädigt/unkodierbar |
| 422 | `PROVIDER_IMAGE_INPUT_UNSUPPORTED` | Modell unterstützt Referenzinput nicht |
| 429 | `RATE_LIMITED` | Limit erreicht |
| 502 | `GITHUB_STORAGE_ERROR` | GitHub-Speicherung fehlgeschlagen |
| 502 | `PROVIDER_HANDOFF_FAILED` | Providerübergabe fehlgeschlagen |

Fehlerantworten enthalten Code, verständliche Meldung und Korrelations-ID, niemals Tokens, Secrets oder Bildbytes.

## 8. UI-Ablauf

1. Bild hochladen, Herkunft/Rechte/Beschreibung/Zuordnungen ergänzen.
2. Als `stored` ablegen; noch nicht auswählbar.
3. Bild und Metadaten prüfen und ausdrücklich freigeben.
4. Beim Bildauftrag konkrete Referenzen auswählen.
5. Vor dem Senden Modellfähigkeit und ausgewählte Bilder anzeigen.
6. Nach dem Auftrag zeigen, welche konkreten Versionen tatsächlich übertragen wurden oder warum nicht.

## 9. Abnahmetests

- Auth0: fehlendes, falsches Audience-, abgelaufenes und unzureichend berechtigtes Token;
- Repository: fremdes/nicht installiertes/nicht freigegebenes Repository;
- Upload: gültiges PNG/JPEG, MIME-Spoofing, beschädigt, zu groß, leer;
- Lifecycle: Upload bleibt nicht freigegeben, Freigabe explizit, Rücknahme blockiert neue Auswahl;
- Isolation: Referenz-ID eines anderen Projekts wird abgewiesen;
- Versionierung: neue Version ändert Hash/Commit, historische Runs behalten alten Hash;
- Provider: supported überträgt Bytes, unsupported/unknown blockiert;
- Logs: keine Tokens, Secrets oder Bildbytes;
- Regression: Illustrations- und Freigabeworkflow #54 unverändert.

## 10. Umsetzung

1. Domain-Vertrag und Repository-Storage-Interface;
2. Auth0 und GitHub-App-Autorisierung;
3. Upload, Validierung, Arbeitsbranch und PR;
4. Abruf und Lifecycle-Endpunkte;
5. UI-Upload, Metadateneditor, Freigabe;
6. Provider-Capabilities und serverseitige Bildübergabe;
7. End-to-End- und Sicherheitstests.

**Nicht festgelegt:** Hoster, Laufzeit oder Cloud-Objektspeicher. Keine Cloudflare-Abhängigkeit.
