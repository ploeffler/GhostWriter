# Auth0-Einrichtung für GhostWriter

Auth0 ist als verwalteter Identity Provider ausgewählt. GitHub bleibt eine getrennte Autorisierung über eine GitHub App.

## Auth0 konfigurieren

1. Erstelle einen Tenant bei https://auth0.com/signup und wähle eine passende Region.
2. Lege eine API namens `GhostWriter API` an.
3. Verwende als Identifier zunächst einen Platzhalter wie `https://api.ghostwriter.example`; ersetze ihn später durch die feste API-Audience.
4. Wähle RS256 als Signing Algorithm und aktiviere RBAC.
5. Lege zunächst die Permissions `read:account`, `read:projects` und `write:projects` an.
6. Erstelle eine Anwendung vom Typ **Regular Web Application** für die GPT-Action.
7. Aktiviere Authorization Code und verwende für den Token-Austausch POST mit Client-ID und Client-Secret.
8. Kopiere die Client-ID und das Client-Secret sicher. Das Secret gehört ausschließlich in die OAuth-Einstellungen der GPT-Action.

## GPT-Action OAuth-Einstellungen

- Client ID: Auth0 Application Client ID
- Client Secret: Auth0 Application Client Secret
- Authorization URL: `https://YOUR_TENANT_DOMAIN/authorize?audience=https%3A%2F%2Fapi.ghostwriter.example`
- Token URL: `https://YOUR_TENANT_DOMAIN/oauth/token`
- Scope: `read:account`
- Token exchange: POST

Ersetze `YOUR_TENANT_DOMAIN` und die API-Audience durch die tatsächlichen Werte. Registriere danach exakt die Callback-URL, die ChatGPT im GPT-Editor anzeigt. Keine Callback-URL erraten.

## Worker-Konfiguration

Kopiere `backend/.dev.vars.example` nach `.dev.vars` und setze:

- `AUTH0_ISSUER=https://YOUR_TENANT_DOMAIN/` (mit abschließendem Slash)
- `AUTH0_AUDIENCE=https://api.ghostwriter.example`

Diese beiden Werte sind keine Secrets. Das Client-Secret der GPT-Action wird nicht im Worker benötigt.

## Test

1. `GET /v1/health` muss ohne Anmeldung 200 liefern.
2. `GET /v1/account` ohne Token muss 401 liefern.
3. Nach erfolgreichem GPT-Action-Login muss `GET /v1/account` mit gültigem Token und `read:account` 200 liefern.
4. Abgelaufene Tokens, falscher Issuer, falsche Audience und fehlender Scope müssen abgewiesen werden.

## Noch manuell erforderlich

Der Betreiber muss den Auth0-Tenant, die API und die Anwendung im eigenen Auth0-Konto anlegen und die GPT-Action konfigurieren. GhostWriter hat keinen Zugriff auf dein Auth0-Konto; es wurden keine Zugangsdaten erstellt und kein Dienst veröffentlicht.

Preise und Tariflimits vor Produktivstart prüfen: https://auth0.com/de/pricing
