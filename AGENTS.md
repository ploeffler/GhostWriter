# GhostWriter – Hinweise für KI-Assistenten

Dieses Repository ist ein GhostWriter-Repository: ein einzelnes Buch, eine **Bibliothek** (Bücher als Branches `buch/*`, auf dem Standard-Branch nur Programm und Starter) oder das Programm selbst (`upstream.repo` in `ghostwriter-manifest.yml`). Diese Datei kommt mit jedem Update aus dem Hauptrepository; Eigenes gehört in `assistant.yml` (siehe unten). Für Claude gilt `CLAUDE.md` mit denselben Regeln.

## Immer

1. **Zuerst `START.md`:** Vor der ersten Antwort `START.md` lesen und Abschnitt 0 (Wiedereinstieg) befolgen.
2. **Darstellungsmodus vor der ersten Ansicht:** Bediensprache nach `START.md` bestimmen. Bei Englisch Text oder tatsächlich unterstützte native Chat-Elemente verwenden; die grafischen Vorlagen sind noch nicht vollständig übersetzt. Bei Deutsch: Claude zeigt das GhostWriter-Widget gemäß `templates/ui/BEFUELLUNG.md`; ChatGPT verwendet unterstützte native Chat-Ausgaben. Keine Claude-Widgets oder HTML als ChatGPT-Widget voraussetzen. Bei anderen oder unklaren Clients auf Text zurückfallen. Die Umschaltung „Darstellung: einfach/übersichtlich/erweitert“ und „Nur Text“ beachten.
3. **Repository-Name:** `render_view.py` immer mit `--repo <owner>/<repo>` dieses Repositorys aufrufen.
4. **Profil der Bibliothek:** Gibt es `assistant.yml` auf dem Standard-Branch, gelten seine Angaben: Git-Benutzer für Commits, Autor, Standard-Erzählstimme. Fehlt das Profil, beim Wiedereinstieg einmal anbieten (`START.md`, „Assistenten-Profil“).
5. **Fehler und Wünsche zum Programm** als Issue im Hauptrepository (`upstream.repo` in `ghostwriter-manifest.yml`), nicht im Buch-Repository; vorher nach einem gleichen Issue suchen.
6. **Redaktionelle Qualitätssicherung:** Vor dem Abschluss einer Schreib- oder Überarbeitungsaufgabe die vollständige betroffene Einheit prüfen, bei kapitelweiten Auswirkungen das ganze Kapitel und bei buchweiten Auswirkungen die relevanten Kapitel. Die Prüfschritte, Korrekturschleife und Ergebnisstufen stehen in [`docs/QUALITAETSSICHERUNG.md`](docs/QUALITAETSSICHERUNG.md). Projektindividuelle Fakten und Stilvorgaben ausschließlich aus dem Buchprofil und freigegebenen Projektunterlagen übernehmen.
7. **Darstellungsmodus:** Die Darstellung ist unabhängig vom Antwortmodus. „Darstellung: einfach“, „Darstellung: übersichtlich“, „Darstellung: erweitert“ und „Nur Text“ gelten im laufenden Chat bis zur nächsten Änderung. ChatGPT-Ausgaben mit nativen Chat-Elementen gestalten, soweit unterstützt; keine nicht unterstützten Widgets vortäuschen. Details siehe `docs/QUALITAETSSICHERUNG.md`.
8. **Verständliche Chat-Ausgaben:** Standardmäßig im einfachen Modus antworten: Alltagssprache statt unnötiger Git-Fachbegriffe, kurze Ergebnis- und Handlungserklärungen. Der Benutzer kann mit „Erweiterte Antworten an“ bzw. „Debugger-Modus an“ technische Details einschalten und mit „Erweiterte Antworten aus“ bzw. „Einfacher Modus“ wieder ausschalten. Fehler, Risiken und ausstehende Freigaben niemals verschweigen. Details siehe `docs/QUALITAETSSICHERUNG.md`.
9. **Grenzen:** Nie Secret-Werte lesen oder ausgeben, kein ganzes Buch im Chat, Freigaben nur mit ausdrücklicher Bestätigung (`START.md`).

**Auswahlfragen im Gespräch:** Bei passenden Entscheidungen wenige verständliche Optionen und eine eigene Antwort anbieten; dazwischen frei sprechen. Keine Durchklickstrecke. Unterstützte Frageelemente bzw. vorhandene Karten nutzen, sonst Text. Details: `docs/QUALITAETSSICHERUNG.md`, „Gezielte Auswahlfragen im Gespräch“. Freigaben und Speicheraufträge bleiben eigene Schritte.

## Im Programm-Repository selbst

Ist dieses Repository selbst `upstream.repo`, wird hier GhostWriter entwickelt; es gibt kein Buch. Tests mit `python -m unittest discover -s tests -p "test_*.py"`, Doku-Prüfung mit `python scripts/check_docs.py`; Commit-Nachrichten und Doku auf Deutsch.
