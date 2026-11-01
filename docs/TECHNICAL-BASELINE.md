# GhostWriter – technische Basisentscheidung

## Status

Cloudflare Workers und TypeScript sind die Backend-Basis. Auth0 ist als externer Identity Provider ausgewählt. Noch keine Produktionsfreigabe und kein Live-Dienst.

## Entscheidung

- **Runtime/Hosting:** Cloudflare Workers
- **Sprache:** TypeScript
- **API:** versionierte HTTPS-REST-API unter \`/v1\`
- **Identity Provider:** Auth0
- **GitHub-Verbindung:** separate GitHub App
- **Projekt- und Manuskriptpersistenz:** GitHub bleibt maßgebliche Datenquelle
- **Schreibweg:** Änderungen gehen nicht direkt auf den Buch-Branch, sondern als Commits in den Arbeits-Branch `ghostwriter/<buch-branch>` mit einem offenen Pull Request; gemergt wird nur nach Bestätigung über „Änderungen übernehmen“ in der Projektübersicht (entschieden am 31.10.2026, Issue #9; Ablauf in `START.md`, „Schreiben ins Repository“).
- **Zusätzlicher Speicher:** zunächst keiner; später D1 für dauerhafte Benutzer-/GitHub-Installationszuordnungen und KV für kurzlebigen OAuth-State, falls erforderlich.

## Authentifizierungsarchitektur

ChatGPT authentifiziert den Benutzer über Auth0 und erhält ein Access Token für die GhostWriter-API. Der Worker prüft dessen RS256-Signatur über Auth0 JWKS sowie Issuer, Audience, Ablaufzeit und Scopes. Das Auth0 Client-Secret verbleibt in der GPT-Action-Konfiguration.

GitHub wird separat über eine GhostWriter GitHub App verbunden. GitHub-Tokens bleiben serverseitig.

Siehe [AUTH0-SETUP.md](AUTH0-SETUP.md) und [OAUTH-FLOW.md](OAUTH-FLOW.md).

## Offene Entscheidungen

- endgültige Auth0-Tenant-Region und eigene Auth0-Domain;
- finale API-Audience und Produktionsdomain;
- GitHub-App-Installation und Speicherung der Zuordnungen;
- Audit- und Aufbewahrungsfristen, Rate Limits und Monitoring.

## Implementierungsstand

Vorhanden:
- öffentlicher Health-Endpunkt;
- geschützter \`GET /v1/account\`;
- Auth0 JWT-Validierung und Scope-Prüfung;
- lokale Testgrundlage und Auth0-Konfigurationsanleitung.

Noch nicht vorhanden:
- Auth0-Tenant und GPT-Action-OAuth-Konfiguration;
- GitHub-App-Integration;
- Projekt- und Manuskriptendpunkte;
- produktive OpenAPI-Spezifikation und Deployment.

## Nächste Schritte

1. Auth0-Tenant und API gemäß AUTH0-SETUP.md einrichten.
2. GPT-Action-Client registrieren und echte ChatGPT Callback URL hinterlegen.
3. Worker lokal mit Auth0 Issuer und Audience konfigurieren.
4. Auth0-Handshake und geschützten Account-Endpunkt testen.
5. GitHub App und geschützte Repository-Leseoperationen implementieren.

---

<sub>Entwickelt mit Unterstützung von Claude (Anthropic) · [claude.ai](https://claude.ai)</sub>
