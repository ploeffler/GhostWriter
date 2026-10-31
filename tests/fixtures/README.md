# Testdaten

Beispielprojekte für Tests bis einschließlich GhostWriter v0.5. Jedes Projekt
liegt in der Struktur, die `docs/DATA-MODEL.md` für echte Buchprojekte vorsieht.

| Ordner | Zweck |
|---|---|
| `leeres-projekt/` | Frisch angelegtes Projekt ohne Metadaten und ohne Kapitel. Prüft die leeren Fälle: Projektübersicht ohne Kapitel, erstes Kapitel anlegen, Auflage ohne freigegebene Inhalte. |

## Leeres Projekt

`leeres-projekt/ghostwriter.yml` ist eine unveränderte Kopie der
`ghostwriter.yml` aus dem Starter: Status `concept`, alle Projektfelder leer,
`structure.chapters` leer. `chapters/` enthält nur einen Platzhalter, damit
der Ordner existiert.

Ändert sich die Starter-`ghostwriter.yml`, wird diese Kopie mitgezogen.
