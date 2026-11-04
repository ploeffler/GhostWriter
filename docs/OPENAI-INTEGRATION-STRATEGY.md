# GhostWriter – ChatGPT-Integrationsstrategie

## Warum diese Trennung wichtig ist

GhostWriter soll nicht von einer einzelnen ChatGPT-Integrationsart abhängen. ChatGPT ist ein Client, nicht der Speicherort der Buchdaten.

## Architekturprinzip

- GhostWriter benötigt langfristig eine fachliche, plattformunabhängige API.
- Auth0 bleibt als externer Identity Provider vorgesehen.
- Eine GitHub App verwaltet den separaten Zugriff auf Repositories.
- ChatGPT ist ein möglicher Client; GPT-Action-OAuth ist höchstens ein Übergangs-/Kompatibilitätspfad.
- Ein späterer MCP-Server kann dieselben GhostWriter-Domain-Services verwenden.
- Hosting und Laufzeit der API bleiben offen. Cloudflare Workers ist nicht mehr die festgelegte Basis.

## Geplanter MCP-Pfad

Vor einer öffentlichen MCP-Integration sind die aktuellen Anforderungen des ChatGPT-MCP-Clients zu testen. Insbesondere Client Registration, PKCE, OAuth Discovery, Audience/Resource-Bindung, Token-Lebenszyklus und Consent müssen End-to-End validiert werden.

Auth0 unterstützt Dynamic Client Registration, warnt aber ausdrücklich davor, offene Registrierung ungeschützt zu aktivieren: damit könnten beliebige Personen Anwendungen im Tenant registrieren. Für einen MCP-Server muss deshalb geprüft werden, ob Client-ID-Metadaten (CIMD), eine kontrollierte Vorregistrierung oder eine abgesicherte DCR-Strategie möglich ist. Nicht einfach offene DCR aktivieren.

## Konsequenz für den aktuellen Stand

Die frühere Auth0-JWT-Prüfung auf Cloudflare Workers wurde zurückgenommen. Derzeit gibt es keinen ausführbaren GhostWriter-API-Server und keinen vollständigen MCP-Server. Die Auth0-Auswahl ist eine Architekturentscheidung, keine funktionierende ChatGPT-Anmeldung.

Vor einer Produktivfreigabe:
1. Hosting- und Laufzeitoptionen unabhängig vom Anbieter vergleichen;
2. API-Verträge und Domain-Services definieren;
3. entscheiden, ob zuerst MCP statt GPT Action implementiert wird;
4. OAuth Discovery und Client Registration mit einem echten Client testen;
5. Token-Audience und Berechtigungen für genau die GhostWriter-Ressource prüfen;
6. Integration mit einem Testkonto und Testrepository abnehmen.

## Referenzen

- OpenAI GPT Actions: https://help.openai.com/en/articles/9442513-configuring-actions-in-gpts
- Auth0 Dynamic Client Registration: https://github.com/auth0/docs/blob/master/articles/api-auth/dynamic-client-registration.md
- MCP Authorization: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
