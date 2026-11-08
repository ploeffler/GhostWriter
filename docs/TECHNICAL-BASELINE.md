# GhostWriter – technische Basisentscheidung

Die [Entscheidung #169 vom 08.11.2026](ENTSCHEIDUNG-169.md) bestätigt den Arbeits-Branch bei Bedarf und präzisiert Lebenszyklus, Parallelität und Fehlerfälle. Sie ändert keine Branch-Namen und ist keine Behauptung eines bereits implementierten zentralen Schreibdienstes.


## Status

**Hosting und Backend-Laufzeit sind offen.** Cloudflare Workers wurde als technische Basis zurückgenommen. Die externe Cloudflare-GitHub-Verbindung für dieses Repository wurde am 04.11.2026 deaktiviert. Das frühere Worker-Gerüst wurde aus dem Repository entfernt. Es gibt derzeit keinen produktiven oder lokalen GhostWriter-API-Dienst.

Auth0 bleibt als externer Identity Provider vorgesehen. GitHub bleibt die maßgebliche Datenquelle für Buchprojekte.

## Architekturziele (anbieterneutral)

- **API:** versionierte HTTPS-REST-API unter `/v1`, später gegebenenfalls ergänzt durch MCP.
- **Identity Provider:** Auth0 (ausgewählt, aber derzeit nicht mit einer GhostWriter-API verbunden).
- **GitHub-Verbindung:** separate GitHub App.
- **Projekt- und Manuskriptpersistenz:** GitHub bleibt maßgebliche Datenquelle.
- **Schreibweg:** Änderungen gehen nicht direkt auf den Buch-Branch, sondern als Commits in den Arbeits-Branch `ghostwriter/<buch-branch>` mit einem offenen Pull Request; gemergt wird nur nach Bestätigung über „Änderungen übernehmen“ in der Projektübersicht (entschieden am 31.10.2026, Issue #9; Ablauf in `START.md`, „Schreiben ins Repository“).
- **Zusätzlicher Speicher:** zunächst keiner. Spätere Datenbank- oder Objektspeicherentscheidungen erfolgen unabhängig vom Hostinganbieter und nur bei konkretem Bedarf.

## Authentifizierungsarchitektur (Zielbild)

Der Chat-Client authentifiziert den Benutzer über Auth0 und erhält ein Access Token für die GhostWriter-API. Die API muss dessen Signatur über Auth0 JWKS sowie Issuer, Audience, Ablaufzeit und Scopes prüfen.

GitHub wird separat über eine GhostWriter GitHub App verbunden. GitHub-Tokens bleiben serverseitig.

Siehe [AUTH0-SETUP.md](AUTH0-SETUP.md) und [OAUTH-FLOW.md](OAUTH-FLOW.md).

## Offene Entscheidungen

- Hosting und Laufzeit der API;
- endgültige API-Audience und Produktionsdomain;
- Auth0-Tenant-Konfiguration und Chat-Client-Registrierung;
- GitHub-App-Installation und Speicherung der Zuordnungen;
- Audit- und Aufbewahrungsfristen, Rate Limits und Monitoring.

## Implementierungsstand

Vorhanden:
- Architektur- und Sicherheitsanforderungen;
- Auth0 als vorgesehener Identity Provider;
- GitHub als maßgebliche Projekt- und Manuskriptablage.

Noch nicht vorhanden:
- ausführbare GhostWriter-API;
- Auth0-Integration in einen GhostWriter-Dienst;
- GitHub-App-Integration;
- Projekt- und Manuskriptendpunkte;
- produktive OpenAPI-Spezifikation und Deployment.

## Nächste Schritte

1. Hostingoptionen anhand Betrieb, Kosten, Datenschutz, Wartbarkeit und Anbieterbindung vergleichen.
2. API-Verträge und Sicherheitsgrenzen festlegen.
3. Hostinganbieter und Laufzeit bewusst auswählen.
4. Auth0-Handshake und GitHub-App-Verbindung implementieren und mit Testkonto/Testrepository abnehmen.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
