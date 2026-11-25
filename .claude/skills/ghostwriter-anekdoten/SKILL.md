---
name: ghostwriter-anekdoten
description: Eigene Erlebnisse und Anekdoten für ein GhostWriter-Buch festhalten, passende Anekdoten vorschlagen und anonymisiert oder abgewandelt in einen Abschnitt einbauen (mit Wahrheitsgehalt und Einverständnis). Startet bei Befehl Anekdote erfassen, Anekdoten, Capture anecdote, Kürzel AN und bei einem Platzhalter [PLATZHALTER-ANEKDOTE] im Abschnitt. Nicht für Fakten-Recherche, Material-Uploads oder frei erfundene Szenen.
---

# GhostWriter-Anekdoten

Arbeite im ausgewählten Buch nach dessen Repository-Regeln. Der Ablauf steht im
Buchrepo und wird hier nicht wiederholt: `START.md`, Abschnitt „Anekdoten (#643)“,
das Skript `scripts/anekdoten.py` (`add`, `list`, `show`, `suggest`, `plan`, `use`,
`check`) und das Schema `schemas/anecdote.schema.json`. Fehlt die Datei im Buchrepo,
gilt die Fassung im Hauptrepo [GhostWriter](https://github.com/ploeffler/GhostWriter).

## Auslöser

- Befehl `Anekdote erfassen`, `Anekdoten` bzw. `Capture anecdote`, Kürzel **AN**.
- Der Autor erzählt ein eigenes Erlebnis, das ins Buch könnte, oder lädt Text bzw.
  die Abschrift einer Sprachnotiz dafür hoch.
- Ein `[PLATZHALTER-ANEKDOTE: …]` im Abschnitt, bei Abschnittsplanung, Ghostwriting
  oder Ideensammlung: freie Anekdoten anbieten (`anekdoten.py . suggest`).

## Regeln

- **Nur Eigentümer und Bearbeiter.** Leser bekommen weder Liste noch Schreibaktionen
  (Rollen aus `team`, `scripts/team.py`).
- **Erfassen im Original.** Der Text bleibt, wie der Autor ihn erzählt hat; nur
  strukturieren und nach Fehlendem fragen (Titel, Personen mit Rolle, Ort, Zeit,
  Themen). Nichts beschönigen, nichts hinzuerfinden.
- **Anonymisieren erst beim Einbauen.** Eine Auswahlkarte fragt je Verwendung:
  Fassung (anonymisiert, abgewandelt, original), Wahrheitsgehalt (wörtlich,
  frei erzählt, nur als Anlass), Ersetzungen (Original → im Buch, Vorschlag aus den
  Figuren und Orten des Buchs) und Einverständnis (anonymisiert, liegt vor,
  nicht nötig mit Begründung). Originalnamen gehen nie in den Buchtext.
- **Der Text im Abschnitt ist ein Vorschlag.** Übernommen wird nur nach
  ausdrücklicher Bestätigung; erst dann `anekdoten.py . use …` und ein Commit
  zusammen mit dem Abschnitt.
- **Doppelt verwendet** (in einer Reihe auch in einem anderen Band): den Benutzer
  fragen, nichts stillschweigend doppelt einbauen.
- Vor Auflage und Probedruck `anekdoten.py . check` zeigen: Verwendungen der Fassung
  „original“ ohne Einverständnisvermerk.
- Kein Erinnern erfinden: Bekanntes beim vorhandenen Namen nennen („gibt es schon
  als …“), Verworfenes nur mit Hinweis wieder aufgreifen.
- Erwachsene Figuren in sexuellen Szenen, kein Pathos, nichts aus anderen Büchern:
  die Grundregeln für Buchtext aus `START.md` gelten.

## Abschluss

Kurz sagen, was festgehalten, vorgeschlagen oder eingebaut wurde (Kennung, Fassung,
Wahrheitsgehalt, Einverständnis), und was noch offen ist (Bestätigung, Ersetzungen).
