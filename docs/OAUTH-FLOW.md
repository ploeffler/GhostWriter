# GhostWriter – OAuth- und GitHub-Autorisierungsfluss

## Vertrauensbeziehungen

1. **ChatGPT Action → GhostWriter API:** Auth0 authentifiziert den Benutzer und stellt ein Access Token für die GhostWriter-API aus.
2. **GhostWriter API → GitHub:** Der Benutzer verbindet sein GitHub-Konto separat und autorisiert später eine GhostWriter GitHub App.

GitHub-Tokens werden niemals als Action-Parameter, Prompt-Inhalt oder API-Antwort an ChatGPT zurückgegeben.

## A. ChatGPT-Authentifizierung über Auth0

Die Einrichtung steht in [AUTH0-SETUP.md](AUTH0-SETUP.md).

1. GPT-Action verwendet OAuth im GPT-Editor.
2. ChatGPT leitet den Benutzer zum Auth0 Authorization Endpoint weiter.
3. Auth0 authentifiziert den Benutzer und leitet den Authorization Code an die registrierte ChatGPT Callback URL zurück.
4. ChatGPT tauscht den Code am Auth0 Token Endpoint gegen ein Access Token.
5. ChatGPT sendet bei jedem Action-Aufruf \`Authorization: Bearer <Auth0 access token>\`.
6. GhostWriter validiert JWT-Signatur, Issuer, Audience, Ablaufzeit und erforderlichen Scope.
7. GhostWriter ordnet die pseudonyme Auth0-Subject-ID dem GhostWriter-Benutzerkonto zu.

GPT Actions benötigen Client-ID, Client-Secret, Authorization URL, Token URL, Scope und Token-Austauschmethode. Auth0 dokumentiert den Authorization Code Flow mit Client-ID, Client-Secret, Code und Redirect URI beim POST zum Token Endpoint.

Das Auth0 Client-Secret verbleibt in der GPT-Action-Konfiguration und wird nicht in den Worker kopiert.

## B. GitHub-Verbindung (noch nicht implementiert)

Eine GitHub App ist gegenüber persönlichen Tokens oder breit berechtigten OAuth Apps bevorzugt.

- Benutzer startet „GitHub verbinden“.
- Benutzer autorisiert die GitHub App und installiert sie nur für ausgewählte Repositories.
- GhostWriter ordnet GitHub-Benutzer, App-Installation und erlaubte Repository-IDs dem GhostWriter-Benutzer zu.
- Jede Repositoryoperation prüft Benutzerzuordnung, Installation und Berechtigungen.
- Kurzlebige Installation Access Tokens werden serverseitig verwendet.
- Trennen der Verbindung blockiert weitere Zugriffe.

Vorläufige Minimalrechte: **Contents: Read and write**, **Metadata: Read-only**.

## C. Geplante GitHub-Endpunkte

- \`GET /v1/account\` – Konto- und Verbindungsstatus ohne Secrets.
- \`POST /v1/github/connections/start\` – GitHub-Verknüpfung starten.
- \`GET /v1/github/connections/callback\` – serverseitiger Callback.
- \`GET /v1/github/repositories\` – autorisierte und freigegebene Repositories auflisten.
- \`DELETE /v1/github/connections/{connection_id}\` – Verbindung trennen.

## D. Abnahmetests

- falsche Redirect URI oder fehlender/falscher State wird abgelehnt;
- abgelaufenes, widerrufenes, falsches Audience- oder falsches Scope-Token wird abgelehnt;
- Benutzer A kann keine Projekte oder GitHub-Verbindungen von Benutzer B sehen;
- nicht installierte oder nicht freigegebene Repositories sind nicht sichtbar;
- Tokens erscheinen weder in Action-Antworten noch in Logs;
- GitHub-Verbindung widerrufen blockiert weitere GitHub-Zugriffe;
- ChatGPT OAuth-Handshake wird mit einer echten GPT-Action vollständig getestet.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
