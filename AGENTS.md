# GhostWriter – Hinweise für KI-Assistenten

Dieses Repository ist ein GhostWriter-Repository: ein einzelnes Buch, eine **Bibliothek** (Bücher als Branches `buch/*`, auf dem Standard-Branch nur Programm und Starter) oder das Programm selbst (`upstream.repo` in `ghostwriter-manifest.yml`). Diese Datei kommt mit jedem Update aus dem Hauptrepository; Eigenes gehört in `assistant.yml` (siehe unten). Für Claude gilt `CLAUDE.md` mit denselben Regeln.

## Immer

1. **Zuerst `START.md`:** Vor der ersten Antwort `START.md` lesen und Abschnitt 0 (Wiedereinstieg) befolgen.
2. **Darstellungsmodus vor der ersten Ansicht:** nach `providers.yml`. Stellt dieser Chat GhostWriter-Widgets dar (`chat_widgets: true`), `scripts/render_view.py` ohne `--text` aufrufen; sonst und im Zweifel **nur Text** mit `--text` und nie HTML- oder Widget-Code (`templates/ui/BEFUELLUNG.md`, „Darstellungsmodus“).
3. **Repository-Name:** `render_view.py` immer mit `--repo <owner>/<repo>` dieses Repositorys aufrufen.
4. **Profil der Bibliothek:** Gibt es `assistant.yml` auf dem Standard-Branch, gelten seine Angaben: Git-Benutzer für Commits, Autor, Standard-Erzählstimme. Fehlt das Profil, beim Wiedereinstieg einmal anbieten (`START.md`, „Assistenten-Profil“).
5. **Fehler und Wünsche zum Programm** als Issue im Hauptrepository (`upstream.repo` in `ghostwriter-manifest.yml`), nicht im Buch-Repository; vorher nach einem gleichen Issue suchen.
6. **Redaktionelle Qualitätssicherung:** Vor dem Abschluss einer Schreib- oder Überarbeitungsaufgabe die vollständige betroffene Einheit prüfen, bei kapitelweiten Auswirkungen das ganze Kapitel und bei buchweiten Auswirkungen die relevanten Kapitel. Die Prüfschritte, Korrekturschleife und Ergebnisstufen stehen in [`docs/QUALITAETSSICHERUNG.md`](docs/QUALITAETSSICHERUNG.md). Projektindividuelle Fakten und Stilvorgaben ausschließlich aus dem Buchprofil und freigegebenen Projektunterlagen übernehmen.
7. **Grenzen:** Nie Secret-Werte lesen oder ausgeben, kein ganzes Buch im Chat, Freigaben nur mit ausdrücklicher Bestätigung (`START.md`).

## Im Programm-Repository selbst

Ist dieses Repository selbst `upstream.repo`, wird hier GhostWriter entwickelt; es gibt kein Buch. Tests mit `python -m unittest discover -s tests -p "test_*.py"`, Doku-Prüfung mit `python scripts/check_docs.py`; Commit-Nachrichten und Doku auf Deutsch.
