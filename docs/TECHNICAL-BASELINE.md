# GhostWriter – technische Basisentscheidung (Vorschlag)

## Status

Vorgeschlagene technische Basis für das Backend-Grundgerüst. Noch keine Produktionsfreigabe und kein Live-Dienst.

## Entscheidungsvorschlag

- **Runtime/Hosting:** Cloudflare Workers
- **Sprache:** TypeScript
- **API:** versionierte HTTPS-REST-API unter `/v1`
- **Projekt- und Manuskriptpersistenz:** GitHub bleibt die maßgebliche Datenquelle
- **Zusätzlicher Speicher:** zunächst keiner; später KV für OAuth-/Sitzungszustand und Idempotenzdaten, falls erforderlich
- **Relationale Datenbank:** vorerst keine. D1 wäre erst sinnvoll, wenn GhostWriter eigene durchsuchbare Projektmetadaten, Abrechnungsdaten oder umfangreiche Audit-Daten dauerhaft verwalten muss.

## Warum diese Basis?

Workers bietet einen verwalteten HTTPS-Runtime- und Deployment-Pfad ohne eigenen Serverbetrieb. TypeScript passt zum API-Vertrag und erlaubt gemeinsame Typen für Requests, Responses und Tests. Das Projekt braucht anfangs keine zweite Datenbank, weil Buchstruktur, Rechercheläufe und Manuskript bereits versioniert im GitHub-Repository liegen.

Cloudflare dokumentiert separate Secret-Bindings für vertrauliche Werte. Zugangsdaten dürfen nicht in Wrangler-Konfigurationsdateien oder im Repository abgelegt werden.

## Geplanter Sicherheits- und Anfragefluss

1. Die GPT-Action authentifiziert sich gegenüber GhostWriter über einen unterstützten OAuth-2.0-Fluss.
2. GhostWriter identifiziert den Benutzer und prüft dessen GhostWriter-Berechtigung.
3. Der Benutzer verbindet GitHub separat und stimmt den angeforderten Rechten zu.
4. GhostWriter prüft bei jeder Repositoryoperation, ob genau dieser Benutzer auf genau dieses Repository zugreifen darf.
5. Der Worker führt GitHub-Aufrufe serverseitig aus; Tokens verlassen den Dienst nicht.
6. Schreiboperationen verlangen weiterhin explizite fachliche Freigabe, `expected_head_sha` und `Idempotency-Key`.
7. Ein erfolgreicher Schreibaufruf meldet Commit-SHA und Commit-URL zurück.

## Authentifizierungsarchitektur

Die beiden OAuth-Vertrauensbeziehungen sind getrennt: ChatGPT authentifiziert sich gegenüber GhostWriter; GhostWriter verbindet GitHub serverseitig über eine GitHub App. Details und Sicherheitsprüfungen stehen in [OAUTH-FLOW.md](OAUTH-FLOW.md). Der konkrete Identity Provider für GhostWriter-Konten ist noch nicht festgelegt. Der Kandidat `workers-oauth-provider` muss zuerst den realen GPT-Action-OAuth-Handshake bestehen; eine MCP-OAuth-Kompatibilität allein reicht nicht als Nachweis.

## Noch offene Architekturentscheidungen

- OAuth-Server für die GPT-Action und dessen Benutzer-/Kontenmodell;
- GitHub-App-Modell: bevorzugt GitHub App mit minimalen Repository-Berechtigungen; Installations- und Benutzerautorisierungsfluss konkretisieren;
- sichere Speicherung und Rotation von GitHub-Zugangsdaten;
- ob Schreiboperationen direkt auf `main` oder zunächst in einen Pull Request gehen;
- Audit- und Aufbewahrungsfristen;
- Produktionsdomain, Rate Limits und Monitoring.

Die OAuth-Bibliothek `@cloudflare/workers-oauth-provider` ist eine mögliche technische Option, muss aber gegen die konkrete GPT-Action-Authentifizierung getestet werden. Ihre Verfügbarkeit allein belegt keine Kompatibilität.

## Implementierungsgrenze des aktuellen Scaffolds

Das Verzeichnis `backend/` enthält nur den Worker-Einstiegspunkt, den Health-Endpunkt und lokale Tests. Alle fachlichen API-Endpunkte und jede Authentifizierung fehlen absichtlich. Unbekannte Routen antworten mit 404; es gibt keine simulierten Erfolgsantworten.

## Nächste Schritte

1. Authentifizierungsmodell für GPT-Action und GitHub festlegen.
2. OAuth- und GitHub-App-Konfiguration vorbereiten.
3. geschützte Leseendpunkte implementieren und mit einem Testrepository prüfen.
4. SHA-geschützte Schreiboperationen und Idempotenz implementieren.
5. OpenAPI aus dem tatsächlichen Implementierungsstand erzeugen.
6. erst nach Tests deployen und GPT-Action anbinden.
