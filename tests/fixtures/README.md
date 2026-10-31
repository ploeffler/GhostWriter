# Testdaten

Beispielprojekte für Tests bis einschließlich GhostWriter v0.5. Jedes Projekt
liegt in der Struktur, die `docs/DATA-MODEL.md` für echte Buchprojekte vorsieht.

| Ordner | Zweck |
|---|---|
| `leeres-projekt/` | Frisch angelegtes Projekt ohne Metadaten und ohne Kapitel. Prüft die leeren Fälle: Projektübersicht ohne Kapitel, erstes Kapitel anlegen, Auflage ohne freigegebene Inhalte. |
| `adhs/` | Das Manuskript „ADHS im Erwachsenenleben“ (11 Kapitel, 113 Abschnitte) in Projektstruktur. Grundlage für das Testbuch. |
| `sources/` | Ausgangsdateien, aus denen Testprojekte erzeugt werden. |

## Leeres Projekt

`leeres-projekt/ghostwriter.yml` ist eine unveränderte Kopie der
`ghostwriter.yml` aus dem Starter: Status `concept`, alle Projektfelder leer,
`structure.chapters` leer. `chapters/` enthält nur einen Platzhalter, damit
der Ordner existiert.

Ändert sich die Starter-`ghostwriter.yml`, wird diese Kopie mitgezogen.

## ADHS-Projekt

`adhs/` wird aus `sources/adhs-im-erwachsenenleben.md` erzeugt und nicht von Hand bearbeitet:

```sh
rm -rf tests/fixtures/adhs
python scripts/import_manuscript.py tests/fixtures/sources/adhs-im-erwachsenenleben.md tests/fixtures/adhs --title "ADHS im Erwachsenenleben"
```

Der Manuskripttext ist unverändert. Jede „##“-Überschrift eines Kapitels wird ein Abschnitt (Status `writing`, Schreibfreigabe erteilt, Faktencheck `optional`). Untertitel und Vorspann, Quellenverzeichnis und Prüfliste stehen in der `README.md` des Kapitels. Ziel und Kurzbeschreibung der Abschnitte sind „Offen.“.

Erfundene Testdaten (Autor, Freigaben, Kosten, Auflage 1) kommen erst im Branch `test/test-book` dazu (Issue #7).

## Prüfung

Alle Projekte unter `tests/fixtures/` werden bei jedem Push von der GitHub Action „Projektdateien prüfen“ (`.github/workflows/validate.yml`) mit `scripts/validate_project.py` geprüft. Lokal:

```sh
pip install pyyaml jsonschema
python scripts/validate_project.py . tests/fixtures/leeres-projekt tests/fixtures/adhs
```
