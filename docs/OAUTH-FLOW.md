# GhostWriter – OAuth- und GitHub-Autorisierungsfluss

## Vertrauensbeziehungen

1. **Chat-Client → GhostWriter API:** Auth0 ist als externer Identity Provider vorgesehen. Eine ausführbare GhostWriter-API und deren Hosting sind noch nicht festgelegt.
2. **GhostWriter API → GitHub:** Der Benutzer verbindet sein GitHub-Konto separat und autorisiert später eine GhostWriter GitHub App.

GitHub-Tokens werden niemals als Action-Parameter, Prompt-Inhalt oder API-Antwort an ChatGPT zurückgegeben.

## A. Chat-Authentifizierung über Auth0 (geplant)

1. Der Chat-Client startet den OAuth-Flow.
2. Auth0 authentifiziert den Benutzer und leitet den Authorization Code an die registrierte Callback-URL zurück.
3. Der Client tauscht den Code am Auth0 Token Endpoint gegen ein Access Token.
4. Der Client sendet das Access Token an die GhostWriter-API.
5. Die GhostWriter-API muss JWT-Signatur, Issuer, Audience, Ablaufzeit und erforderlichen Scope prüfen.
6. GhostWriter ordnet die pseudonyme Auth0-Subject-ID dem GhostWriter-Benutzerkonto zu.

**Status:** Auth0 ist als Identity Provider ausgewählt. Die frühere Cloudflare-Worker-Implementierung wurde zurückgenommen; es gibt derzeit keinen API-Endpunkt, der diese Prüfung ausführt. OAuth-Callback, Audience und Clientkonfiguration werden erst nach Festlegung der API-Architektur verbindlich.

## B. GitHub-Verbindung (noch nicht implementiert)

Eine GitHub App ist gegenüber persönlichen Tokens oder breit berechtigten OAuth Apps bevorzugt.

- Benutzer startet „GitHub verbinden“.
- Benutzer autorisiert die GitHub App und installiert sie nur für ausgewählte Repositories.
- GhostWriter ordnet GitHub-Benutzer, App-Installation und erlaubte Repository-IDs dem GhostWriter-Benutzer zu.
- Jede Repositoryoperation prüft Benutzerzuordnung, Installation und Berechtigungen.
- Kurzlebige Installation Access Tokens werden serverseitig verwendet.
- Trennen der Verbindung blockiert weitere Zugriffe.

Vorläufige Minimalrechte: **Contents: Read and write**, **Metadata: Read-only**.

## C. Geplante API-Endpunkte

- `GET /v1/account` – Konto- und Verbindungsstatus ohne Secrets.
- `POST /v1/github/connections/start` – GitHub-Verknüpfung starten.
- `GET /v1/github/connections/callback` – serverseitiger Callback.
- `GET /v1/github/repositories` – autorisierte und freigegebene Repositories auflisten.
- `DELETE /v1/github/connections/{connection_id}` – Verbindung trennen.

Die Endpunkte sind Anforderungen, keine bereits vorhandene API.

## E. Referenzbilder (geplant)

Der hostingneutrale API-Vertrag für Upload, Freigabe, Rücknahme, Versionshistorie und tatsächliche Bilddienstübergabe steht in [VISUAL-REFERENCE-API.md](VISUAL-REFERENCE-API.md) (Issue #143). Die dort beschriebenen Endpunkte sind Architekturvorgaben, noch keine ausführbare API.

## D. Abnahmetests

- falsche Redirect URI oder fehlender/falscher State wird abgelehnt;
- abgelaufenes, widerrufenes, falsches Audience- oder falsches Scope-Token wird abgelehnt;
- Benutzer A kann keine Projekte oder GitHub-Verbindungen von Benutzer B sehen;
- nicht installierte oder nicht freigegebene Repositories sind nicht sichtbar;
- Tokens erscheinen weder in Client-Antworten noch in Logs;
- GitHub-Verbindung widerrufen blockiert weitere GitHub-Zugriffe;
- OAuth-Handshake wird mit einem echten Client vollständig getestet.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
