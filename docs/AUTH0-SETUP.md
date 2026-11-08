# Auth0-Einrichtung für GhostWriter

Auth0 bleibt als externer, verwalteter Identity Provider vorgesehen. Die Hosting- und Backend-Plattform von GhostWriter ist derzeit **nicht festgelegt**. Es gibt in diesem Repository keine ausführbare GhostWriter-API.

## Auth0 vorbereiten

1. Erstelle bzw. verwende einen Tenant bei https://auth0.com.
2. Lege eine API namens `GhostWriter API` an.
3. Verwende zunächst eine vorläufige Audience wie `https://api.ghostwriter.example`; sie muss vor einer Integration auf die spätere API-Adresse abgestimmt werden.
4. Wähle RS256 als Signing Algorithm und aktiviere RBAC.
5. Lege bei Bedarf die Permissions `read:account`, `read:projects` und `write:projects` an.
6. Erstelle eine Anwendung vom Typ **Regular Web Application**, falls die gewählte Chat-Integration diesen OAuth-Clienttyp benötigt.
7. Bewahre Client-ID und Client-Secret sicher auf. Das Secret gehört ausschließlich in die vorgesehene OAuth-Client-Konfiguration und niemals in ein Repository.

## Wichtiger Implementierungsstatus

Die Auth0-Konfiguration allein stellt noch keine funktionierende GhostWriter-Anmeldung her. Das bisherige Cloudflare-Workers-Backend wurde aus dem Repository zurückgenommen. Es gibt daher aktuell keinen GhostWriter-Endpunkt, der Auth0-Tokens validiert, und keine produktive API-Audience oder Callback-Konfiguration.

Erst nach Auswahl und Implementierung einer Hosting-unabhängigen GhostWriter-API werden Audience, Callback-URLs, Scopes und End-to-End-Tests verbindlich festgelegt. Keine Beispieladresse als produktive URL verwenden.

## Sicherheitsregeln

- Auth0 Client-Secrets niemals committen.
- GitHub-Zugriff bleibt eine separate Autorisierung über eine GhostWriter GitHub App.
- Ein gültiges Auth0-Token ersetzt keine Repository-Berechtigungsprüfung.
- Vor Produktivstart Token-Signatur, Issuer, Audience, Ablaufzeit, Scopes, Widerruf und Benutzertrennung testen.

Preise und Tariflimits vor Produktivstart prüfen: https://auth0.com/de/pricing

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
