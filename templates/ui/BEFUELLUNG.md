# Befüllen der Chat-Vorlagen

Diese Regeln sagen dem Assistenten, wie er die Vorlagen in `templates/ui/` aus dem Buch-Repository befüllt, wie er sie ohne Widgets als Text ausgibt und in welchem Format die Vorlagen Nachrichten in den Chat schicken. `scripts/render_view.py` setzt die Regeln für Projektübersicht, Kapitelansicht und Abschnittsformular um und dient als Referenz:

```sh
python scripts/render_view.py <projektordner> project [--text] [--repo owner/name] [--branch name]
python scripts/render_view.py <projektordner> chapter 2 [--text]
python scripts/render_view.py <projektordner> section 2.4 [--text]
```

## Grundregeln

- **Kein ganzes Buch im Chat.** Höchstens der Text eines Abschnitts wird ausgegeben, nie ein ganzes Kapitel oder das ganze Buch. Zusammenführen und Export laufen nur über die GitHub Action. Lesen für Prüfungen ist erlaubt; das Ergebnis im Chat ist ein Bericht. Ganze Dateien gibt es nur als Release-Download auf ausdrückliche Anforderung.
- **Nur echte Daten.** Jeder Wert stammt aus dem Repository. Fehlt ein Wert, bleibt der Platzhalter leer oder zeigt den hier festgelegten Ersatztext; nichts wird erfunden.
- **Maskieren.** Werte werden HTML-maskiert eingesetzt (`&`, `<`, `>`, `"`, `'`).
- **Vorlagen-Kommentar** am Dateianfang wird nicht mit ausgegeben.
- **Wiederholblöcke** `{{#NAME}} … {{/NAME}}` werden je Eintrag einmal ausgegeben; die Marker selbst entfallen.

## Berechnete Werte

| Wert | Regel |
|---|---|
| Abschnittskosten | Summe von `cost_amount` aller Einträge in `chapters/<kapitel>/costs/<abschnitts-id>.yml`; Einträge mit `cost_amount: null` (Status `unavailable`) zählen nicht |
| Kapitelkosten | Summe der Abschnittskosten des Kapitels |
| Projektkosten | Summe der Kapitelkosten plus `costs/project.yml` |
| Geldformat | zwei Nachkommastellen, Komma, Leerzeichen, Währungszeichen: `1,80 €`. Enthält die Summe mindestens einen Eintrag mit `cost_status: estimated`, steht `≈ ` davor. Gibt es keinen Betrag, steht `–` |
| Kosten-Tooltip | Grundtext (z. B. „Summe der Abschnittskosten“), bei Schätzungen ergänzt um „, enthält geschätzte Kosten“; ohne Betrag „Noch keine Kosten erfasst“ |
| Marker | Vorkommen von `[PLATZHALTER-ANEKDOTE`, `[QUELLE PRÜFEN`, `[MEDIZIN PRÜFEN`, `[RECHT PRÜFEN` im Manuskript (Teil unter `## Manuskript`); der Hinweis nach dem Doppelpunkt bis `]` ist `MARKER_TEXT` |
| Marker-Text | `keine offenen Marker`, `1 offener Marker`, `N offene Marker` |
| Anzahl Abschnitte | `1 Abschnitt`, `N Abschnitte` |
| Freigegeben | `<Anzahl Abschnitte mit Status approved> von <Anzahl Abschnitte>` |
| Auflage | `project.current_edition` > 0: „Auflage N“, sonst „noch keine Auflage“ |
| Sichtbare Nummern | Kapitel- und Abschnittsnummer aus der Reihenfolge in `structure.chapters` |
| Kapitel-Link | `https://github.com/<owner>/<repo>/blob/<branch>/<kapitelpfad>/README.md`, Branch wie im Link des Benutzers, sonst `main` |
| Ziel, Kurzbeschreibung | Text unter `## Ziel des Abschnitts` bzw. `## Kurzbeschreibung`; „Offen.“ gilt als leer |

## Platzhalter je Vorlage

### `projektuebersicht.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE` | `project.title`, sonst `project.working_title` |
| `PROJECT_TITLE_SHORT` | `project.title_short`, sonst wie `PROJECT_TITLE` |
| `PROJECT_AUTHOR` | `project.author` |
| `PROJECT_DESCRIPTION_SHORT`, `PROJECT_DESCRIPTION` | `project.description_short`, `project.description` |
| `PROJECT_COST`, `PROJECT_COST_HINT` | Projektkosten, Tooltip „Bisherige Gesamtkosten“ |
| `PROJECT_EDITION_TEXT` | Auflage |
| Block `CHAPTERS`: `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_STATUS`, `CHAPTER_COST`, `CHAPTER_COST_HINT`, `CHAPTER_URL` | je Kapitel aus `structure.chapters`, Kosten und Link wie oben; ohne Kapitel entfällt der Bereich „Kapitel“ |

### `kapitelansicht.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT`, `CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE` | Projekt und Kapitel |
| `CHAPTER_SUBTITLE` | erste kursive Zeile `*…*` in der `README.md` des Kapitels; sonst leer |
| `SECTION_COUNT_TEXT`, `MARKER_COUNT_TEXT`, `APPROVED_COUNT_TEXT` | wie oben, Marker über alle Abschnitte |
| `CHAPTER_COST`, `CHAPTER_COST_HINT` | Kapitelkosten |
| Block `SECTIONS`: `SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE`, `SECTION_STATUS`, `SECTION_COST`, `MARKERS_ANEKDOTE`, `MARKERS_QUELLE`, `MARKERS_MEDIZIN`, `MARKERS_RECHT` | je Abschnitt; Status aus dem Kopf der Abschnittsdatei |

### `abschnitt-bearbeiten.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT`, `CHAPTER_ID`, `CHAPTER_NUMBER`, `SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE` | Projekt, Kapitel, Abschnitt |
| `SECTION_STATUS`, `FACT_CHECK` | Kopf der Abschnittsdatei: `status`, `fact_check` |
| `APPROVAL_WRITING`, `APPROVAL_SECTION` | `approvals.writing`, `approvals.section` als `true`/`false` |
| `SECTION_COST`, `SECTION_COST_HINT` | Abschnittskosten, Tooltip „Summe der Kosteneinträge“ |
| `SECTION_GOAL`, `SECTION_SUMMARY`, `SECTION_MANUSCRIPT` | Ziel, Kurzbeschreibung, Manuskript |
| `MARKER_COUNT_TEXT` | Marker des Abschnitts |
| Block `MARKERS`: `MARKER_TYPE`, `MARKER_LABEL`, `MARKER_TEXT` | je Marker in Reihenfolge; ohne Marker entfällt der Bereich „Offene Marker“ |
| `PREV_SECTION_ID`, `PREV_SECTION_PROMPT`, `NEXT_SECTION_ID`, `NEXT_SECTION_PROMPT` | Nachbarabschnitte im selben Kapitel, Text „Abschnitt N.M „Titel“ bearbeiten“; am Rand leer |

### `abschnittssteuerung.html`

`SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE` wie im Abschnittsformular.

## Textfassung ohne Widgets

Chats ohne Widgets (etwa ChatGPT) bekommen dieselben Inhalte als Markdown; Beispiele erzeugt `scripts/render_view.py … --text`.

- **Projektübersicht:** Titel, Auflage, Autor, Kosten; Kurzbeschreibung als Zitat; Beschreibung; Tabelle der Kapitel mit Link, Kosten und Status; darunter die Aktionen als nummerierte Auswahl.
- **Kapitelansicht:** Kapitel mit Untertitel; Anzahl Abschnitte, Marker, Kosten, Freigaben; Tabelle der Abschnitte mit Markern (Anekdote/Quelle/Medizin/Recht), Kosten und Status; Aktionen.
- **Abschnitt:** Kopfzeile mit Status und Kosten; Faktencheck und Freigaben; Ziel und Kurzbeschreibung; Liste der offenen Marker; der Manuskripttext dieses einen Abschnitts zwischen Trennlinien; Aktionen. Änderungen schickt der Benutzer als geänderten Text zurück.

## Nachrichtenformat

Jede Vorlage schickt eine Nachricht aus einer lesbaren Zeile und einem Block mit festen Daten:

````text
Abschnitt 2.4 „Die Scham, die wir mitbringen“ bearbeiten

```gw
{"action":"view.section","section_id":"sec-02-04-die-scham-die-wir-mitbringen"}
```
````

Der Assistent wertet den Block `gw` aus; die Zeile darüber ist für Menschen. Freie Eingaben ohne Block bleiben erlaubt.

| Aktion | Daten | Bedeutung | Endpunkt in `docs/API-CONTRACT.md` (Weg B) |
|---|---|---|---|
| `view.project` | – | Projektübersicht zeigen | `GET /v1/projects/{owner}/{repo}` |
| `view.chapter` | `chapter_id` | Kapitelansicht zeigen | `GET /v1/projects/{owner}/{repo}` |
| `view.section` | `section_id` | Abschnittsformular zeigen | `GET /v1/projects/{owner}/{repo}` |
| `project.edit` | – | Formular „Projektdaten bearbeiten“ zeigen | – |
| `project.update` | `title`, `title_short`, `author`, `description_short`, `description` | Projektdaten speichern | noch offen |
| `project.settings.open` | – | Projekteinstellungen zeigen | – |
| `chapter.create.open` | – | Formular „Neues Kapitel anlegen“ zeigen | – |
| `chapter.create` | `title`, `summary`, `goal`, `position` (Index, 0 = am Anfang), `position_label` | Kapitel anlegen | `POST …/chapters` |
| `chapter.edit.open` | `chapter_id` | Kapitel bearbeiten | – |
| `chapter.reorder.open` | – | Kapitelreihenfolge ändern | – |
| `section.create.open` | `chapter_id` | Neuen Abschnitt anlegen | – |
| `section.reorder.open` | `chapter_id` | Abschnittsreihenfolge ändern | – |
| `section.update` | `section_id`, `goal`, `summary`, `fact_check`, `approvals`, `manuscript` | Abschnitt speichern | `PATCH …/sections/{section_id}`, `PUT …/sections/{section_id}/manuscript` |
| `run.start` | `section_id`, `task` (`research` \| `writing`), `mode` (`immediate` \| `scheduled`) | AI-Lauf starten; in v0.5 nur `immediate` | `POST …/sections/{section_id}/research-runs` bzw. Manuskript |
| `edition.create.open` | – | Formular „Neue Auflage erzeugen“ zeigen | – |
| `edition.create` | `name`, `tag`, `date`, `formats`, `notes` | Auflage erzeugen | noch offen |
| `form.cancel` | `form` und betroffene ID | Formular ohne Änderung geschlossen | – |

Eine Freigabe über `section.update` mit `approvals.section: true` ersetzt nicht die ausdrückliche Bestätigung des Benutzers (Issue #10).
