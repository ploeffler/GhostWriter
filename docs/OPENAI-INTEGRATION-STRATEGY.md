# GhostWriter – ChatGPT-Integrationsstrategie

## Warum diese Trennung wichtig ist

OpenAI hat am 30. Oktober 2026 angekündigt, Custom GPTs am 11. Dezember 2026 einzustellen. Benutzerdefinierte GPT-Actions werden bei der Migration nicht automatisch übernommen. Ein Ersatz kann einen eigenen MCP-Server und eine neue Integration erfordern. Maßgeblich sind die Hinweise im jeweiligen ChatGPT-Konto.

Daher soll GhostWriter nicht von einer einzelnen ChatGPT-Integrationsart abhängen.

## Architekturprinzip

- GhostWriter REST API bleibt die fachliche, plattformunabhängige Schnittstelle.
- Auth0 verwaltet GhostWriter-Benutzeridentitäten.
- GitHub App verwaltet den separaten Zugriff auf Repositories.
- ChatGPT ist ein Client, nicht der Speicherort der Buchdaten.
- GPT-Action-OAuth ist höchstens ein Übergangs-/Kompatibilitätspfad.
- Ein späterer MCP-Server kann dieselben GhostWriter-Domain-Services verwenden.

## Geplanter MCP-Pfad

Vor einer öffentlichen MCP-Integration sind die aktuellen Anforderungen des ChatGPT-Plugins/MCP-Clients zu testen. Insbesondere Client Registration, PKCE, OAuth Discovery, Audience/Resource-Bindung, Token-Lebenszyklus und Consent müssen End-to-End validiert werden.

Auth0 unterstützt Dynamic Client Registration, warnt aber ausdrücklich davor, offene Registrierung ungeschützt zu aktivieren: damit könnten beliebige Personen Anwendungen im Tenant registrieren. Für einen MCP-Server muss deshalb geprüft werden, ob Client-ID-Metadaten (CIMD), eine kontrollierte Vorregistrierung oder eine abgesicherte DCR-Strategie möglich ist. Nicht einfach offene DCR aktivieren.

Ein möglicher Aufbau ist ein MCP-kompatibler OAuth-Provider auf Cloudflare Workers, der Auth0 als vorgelagerten Login-/Identity Provider nutzt und eigene, auf die GhostWriter-API beschränkte Tokens ausstellt. Das ist eine Architekturoption, keine bereits implementierte Funktion.

## Konsequenz für den aktuellen Stand

Die Auth0-JWT-Prüfung im Worker ist ein erster geschützter REST-API-Zugriff. Sie ist noch kein vollständiger MCP-Server und kein Nachweis, dass die Integration mit ChatGPT funktioniert.

Vor einer Produktivfreigabe:
1. aktuelle ChatGPT-Migrations-/Plugin-Möglichkeiten des Kontos prüfen;
2. entscheiden, ob zuerst MCP statt GPT Action implementiert wird;
3. OAuth Discovery und Client Registration mit einem echten ChatGPT-MCP-Client testen;
4. Token-Audience und Berechtigungen für genau die GhostWriter-Ressource prüfen;
5. Integration mit einem Testkonto und Testrepository abnehmen.

## Referenzen

- OpenAI: https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq
- OpenAI GPT Actions: https://help.openai.com/en/articles/9442513-configuring-actions-in-gpts
- Auth0 Dynamic Client Registration: https://github.com/auth0/docs/blob/master/articles/api-auth/dynamic-client-registration.md
- MCP Authorization: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
