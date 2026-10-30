# GhostWriter – OAuth- und GitHub-Autorisierungsfluss

## Ziel und Trennung

GhostWriter hat zwei unabhängige Vertrauensbeziehungen:

1. **ChatGPT Action → GhostWriter API:** ChatGPT erhält ein GhostWriter-Access-Token für den angemeldeten GhostWriter-Benutzer.
2. **GhostWriter API → GitHub:** Der Benutzer verbindet ein GitHub-Konto und autorisiert eine GhostWriter GitHub App. GhostWriter verwaltet GitHub-Tokens serverseitig.

Das GitHub-Token wird niemals als Action-Parameter, Prompt-Inhalt oder API-Antwort an ChatGPT zurückgegeben. Die Action sieht ausschließlich GhostWriter-Projekt- und Operationsergebnisse.

## A. ChatGPT-Authentifizierung

### Soll-Ablauf

1. Die GPT-Action ist im GPT-Editor auf OAuth konfiguriert.
2. ChatGPT leitet den Benutzer zur GhostWriter-Autorisierungsseite weiter.
3. GhostWriter authentifiziert den Benutzer über einen noch festzulegenden Identity-Provider und zeigt die angeforderten GhostWriter-Berechtigungen.
4. Der Benutzer stimmt zu; GhostWriter bindet die Freigabe an den authentifizierten Benutzer und den registrierten GPT-Action-Client.
5. ChatGPT tauscht den Authorization Code am Token-Endpunkt gegen ein kurzlebiges Access-Token und optional ein Refresh-Token.
6. ChatGPT sendet bei jedem Action-Aufruf `Authorization: Bearer <GhostWriter access token>`.
7. GhostWriter validiert Token, Ablaufzeit, Zielgruppe und Scopes bei jedem Aufruf.

### Erforderliche OAuth-Funktionen

- Authorization Code Flow über HTTPS;
- exakte Redirect-URI-Prüfung gegen die im GPT-Editor angezeigte Callback-URL;
- `state`-Prüfung und Schutz gegen CSRF;
- sichere Client-Authentifizierung am Token-Endpunkt;
- kurzlebige Access-Tokens, kontrollierte Refresh-Tokens und Widerruf;
- Token-Audience für genau die GhostWriter API;
- Scopes mindestens `project:read` und `project:write`;
- Rate Limits und Audit-Ereignisse ohne Tokens oder Secrets.

Die GPT-Action-Konfiguration benötigt Client-ID, Client-Secret, Authorization-URL, Token-URL, Scope und Token-Austauschmethode. Die konkrete ChatGPT-Callback-URL wird erst aus dem GPT-Editor übernommen und im OAuth-Client exakt registriert.

### Kompatibilitäts-Gate

Cloudflares `workers-oauth-provider` ist ein Kandidat, aber seine OAuth-2.1-/PKCE- und Client-Registrierungsfunktionen beweisen noch nicht, dass der konkrete GPT-Action-OAuth-Handshake samt Client-Authentifizierung und Token-Austausch ohne Anpassung funktioniert. Vor Festlegung muss ein minimaler End-to-End-Prototyp gegen die von ChatGPT tatsächlich gesendeten Requests getestet werden. Keine Produktionskonfiguration, bis dieser Test bestanden ist.

## B. GitHub-Verbindung

### Empfohlener Ansatz

Eine **GitHub App** statt eines persönlichen Access Tokens oder einer breit berechtigten OAuth App.

1. Benutzer startet „GitHub verbinden“ in GhostWriter.
2. GhostWriter führt den Benutzer durch die GitHub-App-Autorisierung und Installation.
3. Der Benutzer installiert die App nur für ausgewählte Repositories oder die ausdrücklich gewählte Organisation.
4. GhostWriter validiert den OAuth-Callback serverseitig und ordnet GitHub-Benutzer, App-Installation und erlaubte Repository-IDs dem GhostWriter-Benutzer zu.
5. Bei jedem API-Aufruf prüft GhostWriter die Zuordnung, die App-Installation und die erforderlichen Repository-Berechtigungen.
6. GhostWriter erzeugt kurzlebige Installation Access Tokens serverseitig und verwendet sie ausschließlich für GitHub API-Aufrufe.
7. Benutzer können eine Verbindung trennen; GhostWriter widerruft bzw. verwirft gespeicherte Autorisierungsdaten und blockiert weitere Zugriffe.

GitHub App user access tokens sind auf Ressourcen begrenzt, auf die der Benutzer Zugriff hat und die App installiert ist; außerdem gelten die von der App angeforderten Berechtigungen. Das passt zum Repository-spezifischen Zugriffskonzept.

### Minimale GitHub-Rechte (vorläufig)

- **Contents: Read and write** – Projektdateien lesen und freigegebene Buchdateien schreiben.
- **Metadata: Read-only** – Repository-Metadaten und Identifikation.

Weitere Rechte (z. B. Pull Requests) erst anfordern, falls GhostWriter tatsächlich PR-basierte Schreibabläufe implementiert. Keine Organisations- oder Administrationsrechte.

## C. Speicherung und Geheimnisse

- GitHub App Private Key, Client Secret und Signaturschlüssel nur als Cloudflare Worker Secrets.
- Benutzerbezogene GitHub-Verbindungsdaten verschlüsselt speichern; Zugriff nur über serverseitige Worker-Logik.
- KV ist für kurzlebige OAuth-State-/Nonce-/Token-Daten möglich; für dauerhafte Benutzer-, Installations- und Repository-Zuordnungen ist D1 mit klaren Zugriffsschlüsseln und Verschlüsselung vorzuziehen.
- Keine Tokens in Logs, Traces, Fehlermeldungen, Commits oder API-Antworten.
- Löschung/Widerruf, Token-Rotation und Ablauf regelmäßig testen.

## D. API-Erweiterungen

Geplante Endpunkte (erst nach Authentifizierungsdesign implementieren):

- `GET /v1/account` – GhostWriter-Konto und Verbindungsstatus, ohne Secrets.
- `POST /v1/github/connections/start` – GitHub-Verknüpfung starten; liefert nur eine kurzlebige Autorisierungs-URL und State-Referenz.
- `GET /v1/github/connections/callback` – serverseitiger OAuth-Callback.
- `GET /v1/github/repositories` – nur tatsächlich autorisierte und für den Benutzer freigegebene Repositories.
- `DELETE /v1/github/connections/{connection_id}` – Verbindung trennen und lokale Tokens widerrufen/löschen.

Diese Endpunkte dürfen niemals GitHub-Tokens an den Action-Client zurückgeben.

## E. Offene Entscheidung vor Implementierung

**Wo soll das GhostWriter-Benutzerkonto liegen?**

- Managed Identity Provider (empfohlen für geringeren Betriebsaufwand), oder
- eigener Login-/Kontodienst innerhalb von GhostWriter.

Die Wahl beeinflusst Login, Passwort-/E-Mail-Verifikation, Recovery, Sitzungen, Datenschutz und Betriebsaufwand. Erst nach dieser Entscheidung wird der konkrete OAuth-Provider ausgewählt.

## F. Abnahmetests

- falsche oder abweichende Redirect-URI wird abgelehnt;
- fehlender/falscher `state`-Wert wird abgelehnt;
- abgelaufenes, widerrufenes, falsches Audience- oder falsches Scope-Token wird abgelehnt;
- Benutzer A kann weder Projekte noch GitHub-Verbindungen von Benutzer B sehen;
- nicht installierte oder nicht freigegebene Repositories sind nicht sichtbar;
- Tokens erscheinen weder in Action-Antworten noch in Logs;
- Entziehen der GitHub-Verbindung blockiert weitere GitHub-Zugriffe;
- ChatGPT OAuth-Handshake wird mit einem echten GPT-Action-Test vollständig durchgespielt.
