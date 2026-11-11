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

**Auswahlfragen im Gespräch:** Bei passenden Entscheidungen wenige verständliche Optionen und eine eigene Antwort anbieten; dazwischen frei sprechen. Keine Durchklickstrecke. Unterstützte Frageelemente bzw. vorhandene Karten nutzen, sonst Text. Details: `docs/QUALITAETSSICHERUNG.md`, „Gezielte Auswahlfragen im Gespräch“. Freigaben und Speicheraufträge bleiben eigene Schritte; eine anstehende Freigabe wird aber als eigene Auswahl angeboten („Abschnitt 3.2 freigeben“, „Noch ändern“, „Später“) statt als „sag …“-Satz zum Abtippen. Der Klick ist die ausdrückliche Bestätigung (`START.md`, „Freigaben“, „Freigabe im Chat“).

**Skillauswahl (#261):** Zu Beginn einer Aufgabe in einem Satz nennen, welcher Skill verwendet wird (oder dass keiner passt). Passen mehrere, den spezifischeren nehmen: den persönlichen Skill dieses Repositorys (`assistant.yml` → `skill`) vor `ghostwriter`; für Programmarbeit am Hauptrepository nicht `ghostwriter`. Bei echter Mehrdeutigkeit einmal kurz fragen. Einen Skill, dessen Anleitung im Gespräch noch vorliegt, nicht erneut laden; nur neu laden, wenn sie nach dem Zusammenfassen des Verlaufs fehlt, und das dann kurz sagen. Details: `docs/CHAT-APPS.md`, „Skills auswählen“.

## Im Programm-Repository selbst

Ist dieses Repository selbst `upstream.repo`, wird hier GhostWriter entwickelt; es gibt kein Buch. Keine Buchinhalte, Buch-Branches, Auflagen-Tags und kein `assistant.yml` (#48, Prüfung `scripts/library.py check-program`). Vor einem Pull Request:

- Tests: `python -m unittest discover -s tests -p "test_*.py"`
- Doku: `python scripts/check_docs.py`
- Commit-Nachrichten und Doku auf Deutsch.

## Dokumentation wächst mit (verbindlich im Programm-Repository)

Bei Änderungen an Funktionen, Bedienung, Einrichtung oder Abläufen die betroffenen Anleitungen im selben Änderungspaket nachziehen. Gemeinsame Inhaltsquelle ist `docs/`; die Website daraus erzeugen, keine unabhängig gepflegte Wiki-Fassung anlegen. Deutsch und Englisch, Beispiele, Grafiken, Navigation und Verweise gemeinsam pflegen; Planungen ausdrücklich kennzeichnen.

Vor Upload Dokumentationscheck, lokalen Website-Aufbau und passende Tests ausführen. Zusätzlich die fachliche Übereinstimmung mit Implementierung, Freigaben und Grenzen prüfen und im PR betroffene Quellen, geprüfte Abläufe und offene Lücken nennen; automatische Links ersetzen die Fachprüfung nicht. Programmversion auf der Website aus dem Manifest anzeigen. Dokumentationsaktualisierung und bestätigten öffentlichen Stand als feste Release-Schritte behandeln. Einzelheiten und Abnahmekriterien: [Dokumentationspflege](docs/DOKUMENTATION-PFLEGE.md).

Prüfen, Bauen, Hochladen, Mergen und Veröffentlichen bleiben getrennt. Ein Uploadauftrag erlaubt weder Merge noch Aktivierung. Öffentliche Bereitstellung nur nach ausdrücklicher Freigabe; keine private Bucharbeit veröffentlichen.
