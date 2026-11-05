# GhostWriter – Hinweise für Claude

Dieses Repository ist ein GhostWriter-Repository: ein einzelnes Buch, eine **Bibliothek** (Bücher als Branches `buch/*`, auf dem Standard-Branch nur Programm und Starter) oder das Programm selbst (`upstream.repo` in `ghostwriter-manifest.yml`). Diese Datei kommt mit jedem Update aus dem Hauptrepository; Eigenes gehört in `assistant.yml` (siehe unten).

## Immer

1. **Zuerst `START.md`:** Vor der ersten Antwort `START.md` lesen und Abschnitt 0 (Wiedereinstieg) befolgen. Den Ablauf fasst der Skill `ghostwriter` zusammen (`.claude/skills/ghostwriter/SKILL.md`).
2. **Darstellungsmodus vor der ersten Ansicht:** Zuerst die Bediensprache nach `START.md` bestimmen. Bei Englisch Text oder unterstützte native Chat-Elemente verwenden; die Widgets sind noch nicht vollständig übersetzt. Bei Deutsch zeigt Claude Widgets; `--text` verwenden, wenn ein Widget nicht erscheint oder der Benutzer Text verlangt (`templates/ui/BEFUELLUNG.md`, „Darstellungsmodus“).
3. **Repository-Name:** `render_view.py` immer mit `--repo <owner>/<repo>` dieses Repositorys aufrufen.
4. **Profil der Bibliothek:** Gibt es `assistant.yml` auf dem Standard-Branch, gelten seine Angaben: Git-Benutzer für Commits, Autor, Standard-Erzählstimme. Der persönliche Skill dazu liegt unter `.claude/skills/<skill>/SKILL.md` (Name in `assistant.yml` → `skill`). Fehlt das Profil, beim Wiedereinstieg einmal anbieten (`START.md`, „Assistenten-Profil“).
5. **Fehler und Wünsche zum Programm** als Issue im Hauptrepository (`upstream.repo` in `ghostwriter-manifest.yml`), nicht im Buch-Repository; vorher nach einem gleichen Issue suchen.
6. **Redaktionelle Qualitätssicherung:** Vor dem Abschluss einer Schreib- oder Überarbeitungsaufgabe die vollständige betroffene Einheit prüfen, bei kapitelweiten Auswirkungen das ganze Kapitel und bei buchweiten Auswirkungen die relevanten Kapitel. Die Prüfschritte, Korrekturschleife und Ergebnisstufen stehen in [`docs/QUALITAETSSICHERUNG.md`](docs/QUALITAETSSICHERUNG.md). Projektindividuelle Fakten und Stilvorgaben ausschließlich aus dem Buchprofil und freigegebenen Projektunterlagen übernehmen.
7. **Darstellungsmodus:** Die Darstellung ist unabhängig vom Antwortmodus. „Darstellung: einfach“, „Darstellung: übersichtlich“, „Darstellung: erweitert“ und „Nur Text“ gelten im laufenden Chat bis zur nächsten Änderung. Bei Englisch die Sprachregel aus Punkt 2 beachten. Bei Deutsch verwendet Claude sein GhostWriter-Widget; ChatGPT native strukturierte Chat-Elemente, soweit unterstützt; andere Clients erhalten eine Textdarstellung. Keine nicht unterstützten Widgets vortäuschen. Details siehe `docs/QUALITAETSSICHERUNG.md`.
8. **Verständliche Chat-Ausgaben:** Standardmäßig im einfachen Modus antworten: Alltagssprache statt unnötiger Git-Fachbegriffe, kurze Ergebnis- und Handlungserklärungen. Der Benutzer kann mit „Erweiterte Antworten an“ bzw. „Debugger-Modus an“ technische Details einschalten und mit „Erweiterte Antworten aus“ bzw. „Einfacher Modus“ wieder ausschalten. Fehler, Risiken und ausstehende Freigaben niemals verschweigen. Details siehe `docs/QUALITAETSSICHERUNG.md`.
9. **Grenzen:** Nie Secret-Werte lesen oder ausgeben, kein ganzes Buch im Chat, Freigaben nur mit ausdrücklicher Bestätigung (`START.md`).

## Im Programm-Repository selbst

Ist dieses Repository selbst `upstream.repo`, wird hier GhostWriter entwickelt; es gibt kein Buch. Keine Buchinhalte, Buch-Branches, Auflagen-Tags und kein `assistant.yml` (#48, Prüfung `scripts/library.py check-program`). Vor einem Pull Request:

- Tests: `python -m unittest discover -s tests -p "test_*.py"`
- Doku: `python scripts/check_docs.py`
- Commit-Nachrichten und Doku auf Deutsch.
