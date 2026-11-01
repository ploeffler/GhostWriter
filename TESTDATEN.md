# Testdaten in diesem Branch

Dieser Branch `test/test-book` ist das Testbuch für GhostWriter bis v0.5. Der Manuskripttext stammt unverändert aus `tests/fixtures/sources/adhs-im-erwachsenenleben.md`. Alles Folgende ist **erfunden** und dient nur Tests; es wird mit dem Branch nach v0.5 gelöscht.

## Erfundene Angaben

- Autorin: Erika Muster
- Kurz- und Langbeschreibung des Buches
- Projektstatus `writing`, zuletzt bearbeitet: Kapitel 2, Abschnitt 2.4
- Kapitel 1: Status `approved`, Abschnitte alle `approved`
- Kapitel 2: Status `in_progress`, Abschnitte 2.1 `approved`, 2.2 `approved`, 2.3 `approved`, 2.4 `revision`
- Kapitel 3: Status `in_progress`, Abschnitte 3.1 `ready_for_approval`
- Alle übrigen Abschnitte: Status `writing`, Schreibfreigabe erteilt

## Kosteneinträge

| Stelle | Aktivität | Betrag | Status |
|---|---|---|---|
| Abschnitt 1.1 | research | 0,18 EUR | `actual` |
| Abschnitt 1.1 | writing | 0,42 EUR | `estimated` |
| Abschnitt 1.4 | fact_check | 1,20 EUR | `manually_entered` |
| Abschnitt 1.4 | brainstorming | – | `unavailable` |
| Abschnitt 2.4 | writing | 0,35 EUR | `estimated` |
| Abschnitt 2.4 | revision | 0,12 EUR | `estimated` |
| Projekt | other | 2,50 EUR | `manually_entered` |

## Auflagen

- **ADHS im Erwachsenenleben – Auflage 1** (Tag `adhs-im-erwachsenenleben-auflage-1`, 2026-10-30): Testauflage mit dem freigegebenen Kapitel 1.

Tag und Release legt `scripts/build_test_book.py` nicht an. Der Release trägt im Namen den Zusatz „(Testdaten)“.

## Zurücksetzen

Den Branch aus einem frischen Checkout von `main` neu bauen:

```sh
git checkout -B test/test-book origin/main
python scripts/build_test_book.py
git add -A && git commit -m "Testbuch neu aufbauen"
git push --force origin test/test-book
```

## Kapitel 1 ohne Marker (01.11.2026)

Für die Abnahme von v0.5 (Auflage, #18) sind in Kapitel 1 alle Marker entfernt: Platzhalter-Anekdoten gestrichen, Prüfvermerke durch „(Testangabe)“ bzw. „(Testangabe, nicht geprüft)“ ersetzt. Die Inhalte sind dadurch **nicht** geprüft; es bleiben Testdaten.
