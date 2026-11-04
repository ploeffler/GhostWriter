# Befüllen der Chat-Vorlagen

Diese Regeln sagen dem Assistenten, wie er die Chat-Vorlagen mit Daten aus dem Buch-Repository ausgibt, wie er sie ohne Widgets als Text ausgibt und in welchem Format die Vorlagen Nachrichten in den Chat schicken. Die Vorlagen selbst liegen im öffentlichen Repository [ploeffler/ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui) (siehe `README.md` hier). `scripts/render_view.py` setzt die Regeln für Projektübersicht, Kapitelansicht und Abschnittsformular um und dient als Referenz:

```sh
python scripts/render_view.py <projektordner> project [--text] [--head-sha <commit>]
python scripts/render_view.py <projektordner> chapter 2 [--text]
python scripts/render_view.py <projektordner> section 2.4 [--text]
python scripts/render_view.py <projektordner> project-edit | project-settings | chapter-create | chapter-reorder | edition-create [--text]
python scripts/render_view.py <projektordner> project | changes-merge --changes <offene-aenderungen.json> [--head-sha <commit>] [--text]
python scripts/render_view.py <projektordner> chapter-edit 2 | chapter-research 2 | section-create 2 | section-reorder 2 [--text]
python scripts/render_view.py <projektordner> providers-edit [--repo owner/name] [--branch name] [--text]
python scripts/render_view.py <projektordner> approval-writing 2.4 | approval-section 2.4 | approval-chapter 2 [--revoke] [--text]
```

## Darstellungsmodus (verbindlich)

Es gibt zwei Modi, festgelegt einmal zu Beginn des Chats und dann für jede Ansicht gleich:

- **Widget:** nur bei Anbietern, deren Chat-Oberfläche GhostWriter-Widgets darstellt (`chat_widgets: true` in `providers.yml`, derzeit Claude). Dann ist jede Ansicht ein Widget – Projektübersicht, Bücherregal, Daten, Formulare, Bestätigungen, Auswahlkarten (Ausgabe unten). Eine Startseite, fehlende Daten (etwa ohne `library.json` oder `--github`) oder eine kurze Antwort sind kein Grund für Text.
- **Nur Text:** bei allen anderen Anbietern (etwa ChatGPT, Gemini, Copilot) und im Zweifel; erscheint ein Widget nicht, ab dann ebenfalls. Dann jede Ansicht als Textfassung (`render_view.py … --text`, siehe „Textfassung ohne Widgets“). **Nie HTML, `GW.render` oder Widget-Code ausgeben**, auch nicht als Codeblock.

Nie beide Fassungen derselben Ansicht und nie den Modus von Ansicht zu Ansicht wechseln. Der Benutzer kann umschalten: `Nur Text` stellt auf Text um; `Widgets` stellt zurück, aber nur bei einem Anbieter mit `chat_widgets: true` – sonst antworte in einem Satz, dass dieser Chat keine Widgets darstellt.

## Ausgabe im Chat

Im Modus „Widget“ schreibt der Assistent keine fertige Ansicht, sondern nur eine Ladezeile und die Daten. Den Darstellungscode lädt der Chat von jsDelivr:

```html
<div id="gw"></div>
<script src="https://cdn.jsdelivr.net/gh/ploeffler/ghostwriter-ui@<commit>/dist/gw.min.js"></script>
<script>GW.render("<vorlage>", { "PLATZHALTER": "Wert", "BLOCK": [ { … }, … ] })</script>
```

- `<commit>` ist der feste Commit aus `templates/ui/ghostwriter-ui.yml`, nie `main`. `gw.min.js` ist die von jsDelivr automatisch verkleinerte Fassung von `dist/gw.js` (schnelleres erstes Laden); bei Fehlersuche `gw.js` laden. So ändert sich keine Ansicht unbemerkt.
- `<vorlage>` ist der Dateiname der Vorlage ohne `.html`, etwa `projektuebersicht`.
- Die Daten sind ein JSON-Objekt: Platzhalter als Schlüssel ohne Klammern, Wiederholblöcke als Arrays von Objekten. Welche Platzhalter es gibt, steht unten.
- Statuswerte (Felder auf `_STATUS`) stehen als Rohwert in den Daten, etwa `writing`; `gw.js` zeigt sie deutsch an, mit derselben Zuordnung wie die Textfassung.
- `gw.js` maskiert die Werte, wiederholt die Blöcke und entfernt Bereiche mit `data-gw-if="NAME"`, wenn `NAME` fehlt oder leer ist (Kapitel der Projektübersicht, offene Marker des Abschnitts).
- In den Daten wird `</` als `<\/` geschrieben, damit Manuskripttext das Skript nicht beendet.
- `ghostwriter-ui` enthält nur Darstellungscode. Buchinhalte kommen ausschließlich über die Daten in den Chat, nie in dieses Repository.

## Grundregeln

- **Kein ganzes Buch im Chat.** Höchstens der Text eines Abschnitts wird ausgegeben, nie ein ganzes Kapitel oder das ganze Buch. Zusammenführen und Export laufen nur über die GitHub Action. Lesen für Prüfungen ist erlaubt; das Ergebnis im Chat ist ein Bericht. Ganze Dateien gibt es nur als Release-Download auf ausdrückliche Anforderung.
- **Nur echte Daten.** Jeder Wert stammt aus dem Repository. Fehlt ein Wert, bleibt der Platzhalter leer oder zeigt den hier festgelegten Ersatztext; nichts wird erfunden.
- **Maskieren** übernimmt `gw.js`; die Daten enthalten den Rohtext.

## Berechnete Werte

| Wert | Regel |
|---|---|
| Abschnittskosten | Summe von `cost_amount` aller Einträge mit `source: backend_api` in `chapters/<kapitel>/costs/<abschnitts-id>.yml`; Einträge mit `cost_amount: null` (Status `unavailable`) und alte Chat-Schätzungen (`source: legacy_chat_estimate`) zählen nicht. Erfasst werden nur zusätzliche KI-API-Kosten über das Backend (#13), nie Chat-Arbeit über Abos |
| Kapitelkosten | Summe der Abschnittskosten des Kapitels |
| Projektkosten | Summe der Kapitelkosten plus `costs/project.yml` |
| Geldformat | zwei Nachkommastellen, Komma, Leerzeichen, Währungszeichen: `1,80 €`. Enthält die Summe mindestens einen Eintrag mit `cost_status: estimated`, steht `≈ ` davor. Gibt es keinen Betrag, steht `–` |
| Kosten-Tooltip | Grundtext (z. B. „Summe der Abschnittskosten“), bei Schätzungen ergänzt um „, enthält geschätzte Kosten“; ohne Betrag „Keine KI-API-Kosten erfasst (Arbeit im Chat über ein Abo kostet nichts zusätzlich)“ |
| Marker | Vorkommen von `[PLATZHALTER-ANEKDOTE`, `[QUELLE PRÜFEN`, `[MEDIZIN PRÜFEN`, `[RECHT PRÜFEN` im Manuskript (Teil unter `## Manuskript`); der Hinweis nach dem Doppelpunkt bis `]` ist `MARKER_TEXT` |
| Marker-Text | `keine offenen Marker`, `1 offener Marker`, `N offene Marker` |
| Anzahl Abschnitte | `1 Abschnitt`, `N Abschnitte` |
| Freigegeben | `<Anzahl Abschnitte mit Status approved> von <Anzahl Abschnitte>` |
| Gelesener Stand (`HEAD_SHA`) | vollständiger Commit-SHA des Stands, aus dem gelesen wurde: Arbeits-Branch, wenn es offene Änderungen gibt, sonst Buch-Branch (`START.md`, „Schreiben ins Repository“). Jede Vorlage bekommt ihn; `gw.js` hängt ihn an jede schreibende Aktion (auch `approval.confirm`) als `expected_head_sha` an |
| Auflage | `project.current_edition` > 0: „Auflage N“, sonst „noch keine Auflage“ |
| Sichtbare Nummern | Kapitel- und Abschnittsnummer aus der Reihenfolge in `structure.chapters` |
| Ziel, Kurzbeschreibung | Text unter `## Ziel des Abschnitts` bzw. `## Kurzbeschreibung`; „Offen.“ gilt als leer |

## Übersichtsdatei

`ghostwriter-index.json` fasst das ganze Buch ohne Manuskripttext zusammen; erzeugt wird sie von `scripts/build_index.py`, im Repository von der Action „Übersichtsdatei aktualisieren“ nach jedem Push. Gibt es sie, befüllt der Assistent Projektübersicht und Kapitelansicht nur daraus und liest dafür keine Abschnitts- und Kostendateien. Das Abschnittsformular und jede Prüfung vor dem Schreiben lesen weiter die Einzeldateien. Fehlt die Datei oder hat der Assistent im selben Chat gerade selbst geschrieben, gelten die Einzeldateien (`START.md`, „Schreiben ins Repository“, Schritt 5).

| Platzhalter | Feld in `ghostwriter-index.json` |
|---|---|
| `PROJECT_TITLE`, `PROJECT_TITLE_SHORT`, `PROJECT_AUTHOR` | `project.title`, `project.title_short`, `project.author` |
| `PROJECT_DESCRIPTION_SHORT`, `PROJECT_DESCRIPTION` | nicht in der Datei: aus `ghostwriter.yml` |
| `PROJECT_COST` | `project.cost.text`; Tooltip aus `project.cost.estimated` |
| `PROJECT_EDITION_TEXT` | aus `project.current_edition` |
| Block `CHAPTERS` | `chapters[]`: `number`, `id`, `title`, `status`, `cost.text` |
| `CHAPTER_SUBTITLE`, `CHAPTER_COST` | `chapters[].subtitle`, `chapters[].cost.text` |
| `SECTION_COUNT_TEXT`, `APPROVED_COUNT_TEXT` | `chapters[].sections_total`, `chapters[].sections_approved` |
| `MARKER_COUNT_TEXT` | Summe von `chapters[].markers` |
| `CHAPTER_APPROVABLE` | `chapters[].status` = `ready_for_approval` und `sections_approved` = `sections_total` |
| Block `SECTIONS` | `chapters[].sections[]`: `number`, `id`, `title`, `status`, `cost.text`, `markers.anekdote` … `markers.recht` |

`cost.amount` ist `null`, wenn es keinen Betrag gibt; `cost.text` ist dann `–`.

## Offene Änderungen

Offene Änderungen sind die Commits im Arbeits-Branch `ghostwriter/<buch-branch>`, solange dazu ein offener Pull Request in den Buch-Branch besteht (`START.md`, „Schreiben ins Repository“). Der Assistent liest sie vor jeder Projektübersicht und vor `changes.merge.open` aus GitHub: offenen Pull Request mit diesem Head und dieser Basis suchen, seine Commits auflisten (älteste zuerst). Commits mit `GhostWriter-Aktion: index.build` (die Action „Übersichtsdatei aktualisieren“) oder `GhostWriter-Aktion: update` (die Action „GhostWriter aktualisieren“) sind keine Änderungen des Benutzers: Sie erscheinen nicht in der Liste und zählen nicht mit. Bleiben nur solche Commits übrig, gibt es keine offenen Änderungen. Für `render_view.py` gehören sie in eine JSON-Datei für `--changes`:

```json
{"pull_request": 12, "book_branch": "main", "work_branch": "ghostwriter/main",
 "commits": [{"sha": "…40 Zeichen…", "message": "Abschnitt 2.4 gespeichert\n\nGhostWriter-Aktion: section.update", "date": "2026-10-31T23:12:00+01:00"}]}
```

Gibt es keinen offenen Pull Request, gibt es keine offenen Änderungen; die Ansichten lesen dann vom Buch-Branch.

## Update-Stand

Wie weit der Buch-Branch hinter dem Hauptrepository liegt (`START.md`, „Programmdateien und Updates“), ermittelt der Assistent vor jeder Projektübersicht:

1. `upstream.repo` und `upstream.ref` aus `ghostwriter-manifest.yml` des Buchs lesen (fehlt die Datei: kein Hinweis). Im Hauptrepository selbst auf `main`: kein Hinweis.
2. **Fork** (gleiches Netzwerk): `GET /repos/<owner>/<repo>/compare/<buch-branch>...<upstream-owner>:<upstream-repo>:<upstream-ref>`; `ahead_by` ist die Zahl der Commits, die dem Buch fehlen.
3. **Kein Fork** (eigenes Repository aus dem Starter) oder Vergleich nicht möglich: `version` und Head-Commit von `upstream` lesen und mit `version` im Manifest und `commit` in `.ghostwriter/update.yml` des Buchs vergleichen; weicht der Commit ab, „neue Version“ ohne Anzahl (`behind: 1`).
4. Für `render_view.py` als JSON für `--upstream`: `{"behind": 3, "upstream": "ploeffler/GhostWriter:main", "version": "0.3.1", "installed": "0.3.0"}`. Bei `behind: 0` entfällt der Hinweis.

Kann der Assistent den Stand nicht ermitteln (keine Leserechte auf das Hauptrepository), entfällt der Hinweis ohne Meldung.

## Platzhalter je Vorlage

### `projektuebersicht.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE` | `project.title`, sonst `project.working_title` |
| `PROJECT_TITLE_SHORT` | `project.title_short`, sonst wie `PROJECT_TITLE` |
| `PROJECT_AUTHOR` | `project.author` |
| `PROJECT_DESCRIPTION_SHORT`, `PROJECT_DESCRIPTION` | `project.description_short`, `project.description` |
| `PROJECT_COST`, `PROJECT_COST_HINT` | Projektkosten, Tooltip „Zusätzliche KI-API-Kosten über das GhostWriter-Backend“ |
| `PROJECT_EDITION_TEXT` | Auflage |
| `CREDIT_TEXT`, `CREDIT_URL` | Hinweis und Link aus `templates/branding.yml` (`credit`), klein unter der Karte bzw. am Ende der Textfassung; nie im Buch |
| `PENDING_COUNT`, `PENDING_TEXT`, `PENDING_PR` | nur bei offenen Änderungen (Arbeits-Branch mit offenem Pull Request, siehe „Offene Änderungen“): Anzahl der Commits, „1 Änderung“ bzw. „N Änderungen“, Nummer des Pull Requests. Ohne offene Änderungen weglassen; dann entfällt der Hinweis mit dem Knopf „Änderungen übernehmen“ |
| `IMPORT_TEXT` | Import (#124, `import_book.py status`): sieben Tage vor Ablauf der Aufbewahrung „Das Original des Imports (<datei>) wird am TT.MM.JJJJ entfernt (Aufbewahrung …).“; sonst weglassen |
| Block `ANALYSES`: `A_KIND`, `A_TEXT`, `A_RUN`, `A_ICON` | je Art mit offenem Hintergrundlauf (#123, #124, `analyze.latest_all`): Art (`characters`, `summaries`, …), „Figurenvorschläge vom TT.MM.JJJJ liegen bereit (N)“ bzw. „Kurzbeschreibungen und Ziele vom …“, „Stilprofil vom …“, „Schauplätze vom …“, „Zeitleiste vom …“, „Mögliche Widersprüche vom …“, „Sprachliche Hinweise vom …“, Pfad der Vorschlagsdatei (`analysis/<art>/run-NNN.json`), Tabler-Symbol der Art; ohne offenen Lauf weglassen. Der Knopf „Ansehen“ schickt `analysis.open` |
| `LIMIT_STATE`, `LIMIT_TEXT` | Limitwarnung (#62): `warn` (weniger als 20 % übrig) bzw. `pause` (weniger als 10 %, die Update-Automatik ist ausgesetzt) mit Text wie „Automatik pausiert: KI-Budget 8 % übrig (9,20 von 10,00 €)“; Stand aus `scripts/limits.py check --json` (`render_view.py project --limits datei`), ohne Datei nur das KI-Budget aus den Kostendateien. Bei `ok` weglassen; dann entfällt der Hinweis |
| `SERIES_ID`, `SERIES_TEXT` | Serie des Buchs (#116) aus `series/` auf dem Standard-Branch (`scripts/series.py of <branch>`): ID und „Band N der Serie „…““; ohne Serie weglassen. Dann steht oben ein Link zur Serie (`view.series`) |
| `UPDATE_BEHIND`, `UPDATE_TEXT` | nur wenn der Buch-Branch hinter dem Hauptrepository liegt (siehe „Update-Stand“): Anzahl Commits und Text wie „3 Commits hinter ploeffler/GhostWriter:main · Version 0.3.1 verfügbar (installiert 0.3.0)“. Sonst weglassen; dann entfällt der Hinweis mit dem Knopf „Update einspielen“ |
| Block `CHAPTERS`: `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_STATUS`, `CHAPTER_COST`, `CHAPTER_COST_HINT`, `CHAPTER_ID` | je Kapitel aus `structure.chapters`, Kosten wie oben; `CHAPTER_ID` ist die stabile Kapitel-ID, ein Klick auf das Kapitel schickt `view.chapter`; ohne Kapitel entfällt der Bereich „Kapitel“ |
| `CHARACTER_COUNT` | Zahl der Figuren (`characters`, #53); ohne Figuren weglassen, dann entfällt der Knopf „Figuren“ |
| Blöcke `MATTER_FRONT`, `MATTER_BACK`: `MATTER_ID`, `MATTER_TITLE`, `MATTER_STATUS`, `MATTER_MARKERS` | Vor- und Nachspann (#57, #58) aus `structure.front_matter` (über der Kapitelliste) bzw. `back_matter` (darunter) in Buchreihenfolge: ID (`mat-…`), Titel, Status, Zahl offener Marker; ein Klick schickt `view.matter`. Ein leerer Bereich fehlt |

### `kapitelansicht.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT`, `CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE` | Projekt und Kapitel |
| `CHAPTER_SUBTITLE` | erste kursive Zeile `*…*` in der `README.md` des Kapitels; sonst leer |
| `CHAPTER_GOAL`, `CHAPTER_SUMMARY` | `## Ziel des Kapitels` und `## Kurzbeschreibung` der Kapitel-README („Offen.“ gilt als leer); nur Ausgabe, leer = „noch offen“. Der Knopf daneben öffnet die Kapitelrecherche |
| `SECTION_COUNT_TEXT`, `MARKER_COUNT_TEXT`, `APPROVED_COUNT_TEXT` | wie oben, Marker über alle Abschnitte |
| `CHAPTER_APPROVABLE` | `true`, wenn das Kapitel auf `ready_for_approval` steht und alle Abschnitte `approved` sind; sonst leer (dann fehlt der Knopf „Kapitel freigeben“) |
| `CHAPTER_COST`, `CHAPTER_COST_HINT` | Kapitelkosten |
| Block `SECTIONS`: `SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE`, `SECTION_STATUS`, `SECTION_COST`, `MARKERS_ANEKDOTE`, `MARKERS_QUELLE`, `MARKERS_MEDIZIN`, `MARKERS_RECHT` | je Abschnitt; Status aus dem Kopf der Abschnittsdatei |

### `abschnitt-bearbeiten.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT`, `CHAPTER_ID`, `CHAPTER_NUMBER`, `SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE` | Projekt, Kapitel, Abschnitt |
| `SECTION_STATUS`, `FACT_CHECK` | Kopf der Abschnittsdatei: `status`, `fact_check` |
| `APPROVAL_WRITING`, `APPROVAL_SECTION` | `approvals.writing`, `approvals.section` als `true`/`false`; nur Anzeige, geändert werden sie über „Freigabe bestätigen“ |
| `SECTION_COST`, `SECTION_COST_HINT` | Abschnittskosten, Tooltip „Summe der Kosteneinträge“ |
| `SECTION_GOAL`, `SECTION_SUMMARY`, `SECTION_MANUSCRIPT` | Ziel, Kurzbeschreibung, Manuskript |
| `MARKER_COUNT_TEXT` | Marker des Abschnitts |
| Block `MARKERS`: `MARKER_TYPE`, `MARKER_LABEL`, `MARKER_TEXT` | je Marker in Reihenfolge; ohne Marker entfällt der Bereich „Offene Marker“ |
| Block `HINTS`: `H_KIND_TEXT`, `H_TEXT`, `H_QUOTE` | sprachliche Hinweise zum Abschnitt aus `story/hints.yml` (#124): Art („Langer Satz“, „Wortwiederholung“, „Gleiche Satzanfänge“, „Füllwörter“), Hinweis, Fundstelle; ohne Hinweise weglassen |
| `PREV_SECTION_ID`, `PREV_SECTION_PROMPT`, `NEXT_SECTION_ID`, `NEXT_SECTION_PROMPT` | Nachbarabschnitte im selben Kapitel, Text „Abschnitt N.M „Titel“ bearbeiten“; am Rand leer |
| `CHARACTERS_ENABLED`, Block `ALL_CHARACTERS`: `C_ID`, `C_NAME`, `C_ON` | nur wenn das Buch Figuren hat (#53): `1`; je Figur ID, Name und `1`, wenn sie in `characters` des Abschnittskopfs steht |

### `abschnittssteuerung.html`

`SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE` wie im Abschnittsformular.

### `projektdaten-bearbeiten.html`

`PROJECT_TITLE`, `PROJECT_TITLE_SHORT`, `PROJECT_AUTHOR`, `PROJECT_DESCRIPTION_SHORT`, `PROJECT_DESCRIPTION` wie in der Projektübersicht, hier als Vorbelegung der Felder.

### `kapitel-anlegen.html`

| Platzhalter | Quelle |
|---|---|
| Block `POSITIONS`: `POSITION_LABEL`, `POSITION_SELECTED` | „Am Anfang (vor Kapitel 1)“, dann „Nach Kapitel N „Titel““ je Kapitel; die letzte lautet „Am Ende (nach Kapitel N „Titel“)“. Ohne Kapitel nur „Als erstes Kapitel“. `POSITION_SELECTED` ist `selected` für die Vorauswahl (am Ende), sonst leer |

### `auflage-erzeugen.html`

| Platzhalter | Quelle |
|---|---|
| `EDITION_NUMBER` | `project.current_edition` + 1 |
| `EDITION_NAME`, `EDITION_TAG` | `book_releases.name_pattern` bzw. `tag_pattern` aus `workflow.yml` |
| `EDITION_DATE_DEFAULT` | heutiges Datum, `YYYY-MM-DD` |
| `APPROVAL_WARNING_TEXT` | „Bisher sind N von M Kapiteln freigegeben; nur diese kommen in die Auflage.“; leer, wenn alle freigegeben sind (der Hinweis entfällt) |
| Block `FORMATS`: `FORMAT_LABEL` | `book_releases.assets`, in v0.5 PDF, DOCX, EPUB |

### `kapitel-bearbeiten.html`

`CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_SUBTITLE` wie in der Kapitelansicht; `CHAPTER_SUMMARY` und `CHAPTER_GOAL` aus `## Kurzbeschreibung` und `## Ziel des Kapitels` der Kapitel-README („Offen.“ gilt als leer).

### `kapitelrecherche.html`

| Platzhalter | Quelle |
|---|---|
| `CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_GOAL`, `CHAPTER_SUMMARY` | wie in der Kapitelansicht; nach einer Recherche die zuletzt gesendeten, noch nicht gespeicherten Werte (`--draft`) |
| `RESEARCH_QUESTION`, `RESEARCH_SCOPE` | `question` und `scope` des letzten Laufs bzw. die gesendeten Werte; sonst leer |
| `RESEARCH_TASK` | `goal`, `sections`, `summary` oder leer: gesendeter Wert, sonst `task` des letzten Laufs, sonst `goal`, solange das Ziel leer ist |
| `SECTION_COUNT`, `SECTIONS_NOTE` | Zahl der vorhandenen Abschnitte und Hinweis, dass sie unverändert bleiben und neue ans Ende kommen (bei freigegebenem Kapitel: wird wieder „in Arbeit“) |
| Block `SUGGESTED_SECTIONS`: `SUG_TITLE`, `SUG_SUMMARY` | Zeilen `- Titel: Kurzbeschreibung` unter `## Vorschlag: Abschnitte` des letzten Laufs, ohne Titel, die es im Kapitel schon gibt; leer = Bereich entfällt |
| `PREV_CHAPTER`, `PREV_CHAPTER_LABEL`, `PREV_CHAPTER_SUMMARY`, `PREV_WEIGHT` | vorheriges Kapitel („Kapitel N · Titel“, Kurzbeschreibung); Gewichtung 0–3 aus gesendetem Wert bzw. letztem Lauf, sonst 2; ohne vorheriges Kapitel leer (Bereich entfällt) |
| `NEXT_CHAPTER`, `NEXT_CHAPTER_LABEL`, `NEXT_CHAPTER_SUMMARY`, `NEXT_WEIGHT` | ebenso für das nächste Kapitel |
| `RESEARCH_PROVIDER_TEXT` | „Recherche über: …“ aus `ai_providers.research.provider` (sonst `default`; `chat` = „aktueller Chat“) |
| `RUN_COUNT_TEXT` | Zahl der Läufe unter `research/kapitel/` und Datum des letzten |
| `LAST_RUN`, `LAST_RUN_ID`, `LAST_RUN_TEXT` | letzter Lauf: `true`, `id`, Abschnitt `## Kurzfassung`; ohne Lauf entfällt der Ergebnisbereich |
| `SUGGESTED_GOAL`, `SUGGESTED_SUMMARY` | `## Vorschlag: Ziel des Kapitels` und `## Vorschlag: Kurzbeschreibung` des letzten Laufs; leer = kein Vorschlag |

### `buecherregal.html`

Startseite einer Bibliothek; Widget oder Text nach dem Darstellungsmodus. Erzeugt mit `render_view.py library --library library.json` aus der Übersicht `library.json` auf dem Standard-Branch (`scripts/library.py build`, Action „Bücherregal aktualisieren“); fehlt sie, live aus den Branches.

| Platzhalter | Quelle |
|---|---|
| `LIBRARY_NAME` | `owner/repo` (`--repo`) |
| `BOOK_COUNT_TEXT`, `EMPTY` | Zahl der Bücher („1 Buch“, „2 Bücher“); `EMPTY` = `1` ohne Buch |
| `UPDATED_TEXT` | derzeit leer (Bereich entfällt) |
| Block `BOOKS`: `BOOK_BRANCH`, `BOOK_TITLE`, `BOOK_TITLE_SHORT`, `BOOK_AUTHOR_TEXT` | je Buch aus `library.json`: `branch`, `title`, `title_short`, „von <author>“ |
| `BOOK_STATE`, `BOOK_STATE_TEXT` | `status`: `ready` „eingerichtet“ (hat Kapitel) bzw. `setup` „im Aufbau“ |
| `BOOK_PROGRESS`, `BOOK_PROGRESS_TEXT` | Anteil `sections_approved`/`sections_total` in Prozent; „N von M Abschnitten freigegeben · K von L Kapiteln“, im Aufbau „Gliederung noch offen“ |
| `BOOK_EDITION_TEXT`, `BOOK_COST` | `current_edition` („Auflage N“ bzw. „noch keine Auflage“), `cost.text` |
| `BOOK_PENDING_TEXT` | `pending` > 0: „N Änderungen offen“ (Commits im Arbeits-Branch), sonst leer |
| `BOOK_UPDATED_TEXT` | „zuletzt geändert am TT.MM.JJJJ“ bzw. „angelegt am …“ aus `updated_at` |
| `BOOK_SERIES`, `BOOK_SERIES_TITLE`, `BOOK_SERIES_KEY`, `BOOK_VOLUME_TEXT` | Serie des Buchs (#116) aus `library.json` (`series`) bzw. `series/` auf dem Standard-Branch: ID, Reihentitel, Kürzel `S1`, `S2` … (Reihenfolge der Serien) und „Band N“; ohne Serie leer. Bücher einer Serie stehen zuerst, je Serie in Bandreihenfolge, danach die übrigen |
| Block `EMPTY_SERIES`: `S_ID`, `S_TITLE`, `S_KEY` | Serien, zu denen noch kein Buch gehört; sonst Block weglassen |

In der Projektübersicht kommt `LIBRARY_COUNT` (Zahl der Bücher, nur ab 2, sonst leer) aus derselben Datei (`--library`).

### `daten.html`

Seite „Daten“ (`render_view.py data`, `START.md`, „Daten“). Quellen: `library.json` (`--library`), Rohdaten der GitHub-API (`--github`: `repo`, `branches`, `pulls`, `runs`), Update-Stand (`--upstream`).

| Platzhalter | Quelle |
|---|---|
| `LIBRARY_NAME` | `owner/repo` (`--repo`) |
| `PROGRAM_VERSION_TEXT`, `UI_TEXT` | `program.version`, `program.upstream`, `program.ui_version`, `program.ui_commit` aus `library.json` |
| `PROGRAM_UPDATE_TEXT`, `PROGRAM_BEHIND` | Update-Stand aus `--upstream` („aktuell“ bzw. Commits dahinter); ohne Angabe „nicht abgefragt“; `PROGRAM_BEHIND` nur, wenn dahinter |
| `PROGRAM_LAST_UPDATE_TEXT`, `PROGRAM_SKIPPED_TEXT` | `program.last_update`, `program.skipped_workflows` (aus `.ghostwriter/update.yml` des Standard-Branchs) |
| Block `LIMITS`: `L_LABEL`, `L_STATE`, `L_TEXT` | Nutzungsgrenzen (#62): je geprüfter Grenze Name, Ampel `ok` / `warn` (unter 20 %) / `pause` (unter 10 %) und Stand wie „62 % übrig (3,80 von 10,00 €)“; aus `--limits` (`scripts/limits.py check --json`) bzw. aus den Kostendateien des Buchs und `rate_limit` in `github.json`. Keine Grenze eingestellt bzw. prüfbar = Block weglassen |
| `LIMITS_TEXT` | nur bei `pause`: „Update-Automatik pausiert: …“ mit dem Grund; sonst leer |
| `GITHUB_KNOWN` | `1`, wenn `--github` übergeben wurde; sonst leer (Hinweis erscheint) |
| `REPO_TEXT` | `repo.private`, `repo.size` (KB), Zahl der `branches`; ohne `--github` „unbekannt“ |
| `CLEANUP_URL`, `TASKS_URL` | Action „Branches aufräumen“, Suche nach dem Issue „Löschaufgaben“ |
| Block `BOOKS`: `B_TITLE`, `B_BRANCH`, `B_COMMIT_TEXT` | je Buch aus `library.json`: Titel, Branch, `updated_at` und `last_commit` |
| `B_PENDING_TEXT`, `B_PENDING`, `B_AUTOMERGE_TEXT` | `pending` (Commits im Arbeits-Branch) und Pull Request mit `head.ref` = Arbeits-Branch; `auto_merge` |
| `B_EDITION_TEXT` | `last_edition` (neuester Tag `<slug>-auflage-N` mit Datum) |
| `B_PROOF_TEXT` | neuester Lauf „Probedruck“ auf dem Buch-Branch, Download 14 Tage ab Start |
| `B_DATA_TEXT`, `B_MIGRATION` | `data_version`, `migration_pending` |
| `B_CHECK`, `B_CHECK_TEXT` | neuester Lauf „Projektdateien prüfen“ auf dem Buch-Branch: `ok`, `fail` oder leer |
| Block `SECRETS`: `S_NAME`, `S_STATE`, `S_TEXT` | `secret_names` und `secrets` aus `library.json`: `yes` hinterlegt, `no` fehlt, `unknown` noch nicht geprüft |
| Block `RUNS`: `R_NAME`, `R_STATE`, `R_TEXT`, `R_URL` | je Action der neueste Lauf aus `runs`: Name, `ok`/`fail`/`other`, Ergebnis, Datum, Branch, Link |

### `bilder.html`

Bilder eines Abschnitts bzw. Teils (`render_view.py images <N.M|id>`, #54).

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | wie in der Projektübersicht |
| `TARGET_ID`, `TARGET_TITLE` | Abschnitt (`sec-…`) bzw. Teil (`mat-…`) und Titel |
| `IMAGE_STYLE` | `images.style`, sonst leer |
| `TARGET_CHARACTERS` | Figuren aus `characters` im Kopf, kommagetrennt |
| Block `IMAGES`: `I_ID`, `I_CAPTION`, `I_STATE`, `I_SOURCE`, `I_SIZE`, `I_IN_TEXT` | je Beschreibung `img-….yml` im Bildordner: ID, Bildunterschrift, `status` (`draft`/`approved`; bewusst nicht `…_STATUS`, das gw.js übersetzen würde), Herkunft deutsch, Größe in px, `1`, wenn `![](bild:…)` im Manuskript steht |

### `figuren.html`

Liste der Figuren (`render_view.py characters`, #53).

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | wie in der Projektübersicht |
| Block `CHARACTERS`: `C_ID`, `C_NAME`, `C_ROLE`, `C_SHORT`, `C_USED` | je Figur aus `characters` und dem Kopf der Figurendatei: ID, Name, Rolle deutsch, `short`, Abschnitte bzw. Teile mit dieser Figur im Kopf (`character_usage`), sonst „–“ |
| `C_SOURCE`, `C_SOURCE_TEXT` | nur in einem Band einer Serie (#116): `series` „aus der Serie“ (Figur unter `series/<ser-id>/characters/`), `copy` bzw. `copy_diff` (Figur des Buchs mit derselben ID: Kopie, gleich bzw. abweichend), `own` „nur in diesem Buch“; ohne Serie leer |
| `SERIES_TITLE` | Reihentitel des Bandes; ohne Serie leer (dann kein Hinweis) |

### `figur-bearbeiten.html`

Formular einer Figur (`render_view.py characters <name|id>`).

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | wie in der Projektübersicht |
| `CHARACTER_ID`, `CHARACTER_NAME`, `CHARACTER_ROLE` | `id`, `name`, `role` (main, supporting, minor) |
| `CHARACTER_SHORT`, `CHARACTER_AGE`, `CHARACTER_APPEARANCE`, `CHARACTER_VOICE`, `CHARACTER_VISUAL` | gleichnamige Felder des Kopfs (`short`, `age`, `appearance`, `voice`, `visual`), sonst leer |
| `CHARACTER_TRAITS` | `traits`, kommagetrennt |
| `CHARACTER_DESCRIPTION`, `CHARACTER_NOTES` | `## Beschreibung`, `## Notizen` (Platzhalter der Vorlage = leer) |
| `CHARACTER_USED` | Abschnitte bzw. Teile mit dieser Figur, sonst „noch nirgends“ |
| Block `RELATIONS`: `R_TO`, `R_NAME`, `R_KIND` | `relations`: ID und Name der anderen Figur, Art |
| Block `OTHERS`: `O_ID`, `O_NAME` | alle anderen Figuren (Auswahl für Beziehungen) |
| `CHARACTER_SOURCE`, `CHARACTER_SOURCE_TEXT` | Herkunft wie `C_SOURCE` (#116); bestimmt Speichern (`character.series.update` bei `series`) und die Knöpfe „Kopie nur für dieses Buch“, „An Serie angleichen“, „In die Serie übernehmen“ |
| `SERIES_ID`, `SERIES_TITLE` | Serie des Bandes; ohne Serie leer |

### `figuren-vorschlag.html`

Auswahl „Figuren aus dem Text“ (`render_view.py character-suggest --draft vorschlaege.json`, `START.md`, „Figuren“, Schritt 6). Ausgelöst mit dem Personen-Symbol (`ti-user-search`) in Serie, Projektübersicht, Figurenliste, Kapitel, Abschnitt und Teil – nicht im Bücherregal.

| Platzhalter | Quelle |
|---|---|
| `SCOPE`, `SCOPE_TEXT` | Bereich aus `character.suggest` (`book`, Kapitelnummer, `N.M`, `mat-…`, `ser-…`) und deutsch („ganzes Buch“, „Kapitel 2“, „alle Bände der Serie“) |
| `SUGGEST_COUNT_TEXT` | „N Vorschläge“ |
| `RUN_ID`, `RUN_TEXT`, `CONFLICTS_TEXT` | nur bei Vorschlägen aus einem Hintergrundlauf (#123): `run`, „Hintergrundlauf NNN vom TT.MM.JJJJ“ und die Widersprüche (`conflicts`), z. B. „Opi, Alter: 78 / 80“; sonst leer |
| `SERIES_ID`, `SERIES_TITLE`, `SERIES_LEVEL` | Serie des Buchs bzw. die Serie; `SERIES_LEVEL` = `1` beim Vorschlag auf Serienebene |
| Block `SUGGESTIONS`: `S_IDX`, `S_NAME`, `S_ALIASES`, `S_ROLE`, `S_SHORT`, `S_DETAILS`, `S_SECTIONS`, `S_EVIDENCE` | je Vorschlag aus der JSON-Datei des Assistenten: Nummer, Name, weitere Namen, Rolle, ein Satz, Alter/Aussehen/Eigenschaften/Sprechweise, Abschnitte, bis zu drei Fundstellen |
| `S_STATE`, `S_STATE_TEXT`, `S_EXISTING` | `new` (neu), `existing` (Figur des Buchs mit diesem Namen oder Alias), `series` (Figur der Serie); Text und Name der bekannten Figur |
| Block `MERGE`: `M_ID`, `M_NAME` | bekannte Figuren (Buch und Serie) für „Zusammenlegen mit“ |

### `kurzbeschreibung-vorschlag.html`

Auswahl „Kurzbeschreibung und Ziel“ aus einem Hintergrundlauf (#124, Art `summaries`; `render_view.py analysis-suggest --draft analysis/summaries/run-NNN.json`, `START.md`, „Analysen im Hintergrund“). Geöffnet mit „Ansehen“ in der Projektübersicht (`analysis.open`).

| Platzhalter | Quelle |
|---|---|
| `KIND` | Art des Laufs (`summaries`) |
| `RUN_ID`, `RUN_TEXT` | `run` und „Hintergrundlauf NNN vom TT.MM.JJJJ“ |
| `SCOPE_TEXT`, `SUGGEST_COUNT_TEXT` | Bereich des Laufs („ganzes Buch“, „Kapitel 2“) und „N Vorschläge“ |
| Block `SUGGESTIONS`: `S_IDX`, `S_LEVEL`, `S_LABEL`, `S_TITLE` | je Vorschlag in Buchreihenfolge (Kapitel, dann seine Abschnitte): Nummer in der Vorschlagsdatei, `chapter` bzw. `section`, „Kapitel N“ bzw. „N.M“, Titel |
| `S_GOAL`, `S_SHORT`, `S_EVIDENCE` | vorgeschlagenes Ziel und Kurzbeschreibung, bis zu zwei Fundstellen „N.M: „…““ |
| `S_GOAL_NOW`, `S_SHORT_NOW`, `S_GOAL_ON`, `S_SHORT_ON` | bisheriger Text aus der Abschnittsdatei („## Ziel des Abschnitts“, „## Kurzbeschreibung“) bzw. der README.md des Kapitels („## Kurzbeschreibung“, „## Ziel des Kapitels“), „Offen.“ und Platzhalter der Vorlage zählen als leer; `1` = vorangehakt (Vorschlag da und bisher leer) |

### `stilprofil-vorschlag.html`

Auswahl „Stilprofil“ aus einem Hintergrundlauf (#124, Art `style`; `render_view.py analysis-suggest --draft analysis/style/run-NNN.json`, `START.md`, „Analysen im Hintergrund“).

| Platzhalter | Quelle |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT`, `SCOPE_TEXT` | wie bei `kurzbeschreibung-vorschlag` (`KIND` = `style`) |
| `SUGGEST_COUNT_TEXT` | „N Angaben“ |
| `STATS_TEXT` | Zahlen ohne KI aus `stats`: „14,2 Wörter je Satz · 18 % wörtliche Rede · N Wörter“ |
| Block `SUGGESTIONS`: `S_IDX`, `S_FIELD`, `S_LABEL`, `S_VALUE` | je Angabe: Nummer, `perspective`/`tense`/`address`/`register`/`tone`/`features`, deutsche Bezeichnung, Vorschlag (Listen mit Komma) |
| `S_NOW`, `S_ON` | bisheriger Wert in `style` (`ghostwriter.yml`); `1` = vorangehakt (bisher kein Wert) |
| `S_VARIANTS`, `S_EVIDENCE` | abweichende Kapitel („Präsens in Kapitel 3“), bis zu zwei Fundstellen |

### `orte-vorschlag.html`

Auswahl „Schauplätze aus dem Text“ aus einem Hintergrundlauf (#124, Art `places`; `render_view.py analysis-suggest --draft analysis/places/run-NNN.json`).

| Platzhalter | Quelle |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT`, `SCOPE_TEXT` | wie bei `kurzbeschreibung-vorschlag` (`KIND` = `places`) |
| `SUGGEST_COUNT_TEXT` | „N Orte“ |
| Block `SUGGESTIONS`: `S_IDX`, `S_NAME`, `S_ALIASES`, `S_KIND`, `S_SHORT`, `S_SECTIONS`, `S_EVIDENCE` | je Ort aus der Vorschlagsdatei: Nummer, Name, andere Bezeichnungen, Art, ein Satz, Abschnitte (`N.M`), bis zu zwei Fundstellen |
| `S_STATE`, `S_STATE_TEXT`, `S_EXISTING` | `new` bzw. `existing` (Name oder andere Bezeichnung steht schon in `story/places.yml`), „neu“ bzw. „schon da: …“, ID des bekannten Orts (vorgewählt bei „Zusammenlegen mit“) |
| Block `MERGE`: `M_ID`, `M_NAME` | Orte aus `story/places.yml` |

### `zeitleiste-vorschlag.html`

Auswahl „Zeitleiste“ aus einem Hintergrundlauf (#124, Art `timeline`; `render_view.py analysis-suggest --draft analysis/timeline/run-NNN.json`).

| Platzhalter | Quelle |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT`, `SCOPE_TEXT` | wie bei `kurzbeschreibung-vorschlag` (`KIND` = `timeline`) |
| `SUGGEST_COUNT_TEXT` | „N Ereignisse · M Auffälligkeiten“ |
| Block `ISSUES`: `I_IDX`, `I_KIND`, `I_KIND_TEXT`, `I_EVENTS`, `I_TEXT` | je Auffälligkeit (`issues`): Nummer, `jump`/`contradiction`/`unclear` und deutsch (Zeitsprung, Widerspruch, unklar), Nummern der Ereignisse, Hinweis; ohne Auffälligkeiten weglassen |
| Block `EVENTS`: `E_IDX`, `E_N`, `E_WHERE`, `E_WHEN`, `E_WHAT`, `E_EVIDENCE`, `E_FLAG` | je Ereignis in Buchreihenfolge: Nummer in der Datei, laufende Nummer `n`, Abschnitt, Zeitangabe, was geschieht, Fundstelle; `E_FLAG` = `1`, wenn es zu einer Auffälligkeit gehört |

### `widerspruch-vorschlag.html`

Auswahl „Mögliche Widersprüche“ aus einem Hintergrundlauf (#124, Art `continuity`; `render_view.py analysis-suggest --draft analysis/continuity/run-NNN.json`).

| Platzhalter | Quelle |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT`, `SCOPE_TEXT` | wie bei `kurzbeschreibung-vorschlag` (`KIND` = `continuity`) |
| `SUGGEST_COUNT_TEXT`, `FACTS_TEXT` | „N mögliche Widersprüche“, „M Tatsachen mit Fundstelle verglichen“ (`facts`) |
| Block `SUGGESTIONS`: `S_IDX`, `S_TEXT`, `S_COUNT` | je Widerspruch: Nummer, Satz (Text des Markers), Zahl der Fundstellen |
| Block `FACTS`: `F_IDX`, `F_K`, `F_WHERE`, `F_ABOUT`, `F_FACT`, `F_QUOTE`, `F_ON` | alle Fundstellen flach: Nummer des Widerspruchs, Nummer darin (ab 0), Abschnitt, Gegenstand, Tatsache, Zitat; `F_ON` = `1` bei der letzten (dort kommt der Marker hin, wenn nichts anderes gewählt ist) |

### `sprache-vorschlag.html`

Auswahl „Sprachliche Hinweise“ aus einem Hintergrundlauf (#124, Art `language`, ohne KI; `render_view.py analysis-suggest --draft analysis/language/run-NNN.json`).

| Platzhalter | Quelle |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT`, `SCOPE_TEXT` | wie bei `kurzbeschreibung-vorschlag` (`KIND` = `language`) |
| `SUGGEST_COUNT_TEXT`, `RULES_TEXT` | „N Hinweise“ und die Regeln (Satzlänge, Wiederholungen, Satzanfänge, Füllwörter) aus `analyze.py` |
| Block `SUGGESTIONS`: `S_IDX`, `S_WHERE`, `S_KIND`, `S_KIND_TEXT`, `S_TEXT`, `S_QUOTE` | je Hinweis: Nummer, Abschnitt, `long_sentence`/`repetition`/`same_start`/`filler` und deutsch, Hinweis, Fundstelle |

### `import-vorschau.html`

Gliederung eines Manuskript-Imports prüfen (#124, `render_view.py import-preview`; Daten aus `import/proposal.json` und `import/import.yml`).

| Platzhalter | Quelle |
|---|---|
| `IMPORT_TITLE`, `IMPORT_AUTHOR`, `IMPORT_FORMAT` | `title`, `author` (Dokument-Eigenschaften bzw. einzelne oberste Überschrift), `format` |
| `STATS_TEXT`, `LOSSLESS` | „N Kapitel, M Abschnitte, K Teile von Vor- und Nachspann · X von Y Wörtern übernommen“; `LOSSLESS` = `1`, wenn die Wortzahl der Umwandlung entspricht |
| `KEEP_TEXT` | Aufbewahrung des Originals deutsch („bis zur ersten Auflage“, „30 Tage“, „90 Tage“, „dauerhaft“) |
| `KINDS_TEXT` | Arten von Vor- und Nachspann als `kind=Name`, kommagetrennt (Auswahl „ist Teil …“) |
| Block `WARNINGS`: `W_TEXT` | Hinweise der Umwandlung (PDF, Tabellen, Fußnoten, Bilder, sehr lange Abschnitte, keine Gliederung) |
| Block `PARTS`: `P_IDX`, `P_KIND`, `P_AREA`, `P_LABEL`, `P_TITLE`, `P_WORDS` | Teile von Vor- und Nachspann: Nummer im Vorschlag, Art, `front`/`back`, Name der Art, Überschrift, Wörter |
| Block `ROWS`: `R_TYPE`, `R_CHAPTER`, `R_SECTION`, `R_LABEL`, `R_TITLE`, `R_WORDS`, `R_COUNT`, `R_SCENES`, `R_LONG` | je Kapitel (`chapter`, mit „N Abschnitte“) und darunter je Abschnitt (`section`, Szenen wenn mehr als eine, `R_LONG` = `1` über 4000 Wörter) |

### `vor-nachspann.html`

Liste „Vor- und Nachspann“ (`render_view.py matter`, #57, #58).

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | wie in der Projektübersicht |
| Block `PARTS`: `PART_KIND`, `PART_TITLE`, `PART_AREA`, `PART_ID`, `PART_STATUS`, `PART_HINT` | je mögliche Art in Buchreihenfolge (`MATTER` in `scripts/render_view.py`): Art, Titel des vorhandenen Teils bzw. Vorgabetitel, `front`/`back`, ID (leer = nicht angelegt), Status (leer = nicht angelegt), kurze Beschreibung |

### `teil-bearbeiten.html`

Formular eines Teils von Vor- oder Nachspann (`render_view.py matter <teil>`).

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | wie in der Projektübersicht |
| `MATTER_ID`, `MATTER_KIND`, `MATTER_TITLE`, `MATTER_AREA_TEXT`, `MATTER_STATUS` | Eintrag in `structure.front_matter`/`back_matter` und Kopf der Datei; „Vorspann“ bzw. „Nachspann“ |
| `MATTER_GOAL`, `MATTER_MANUSCRIPT` | `## Ziel` (Platzhalter der Vorlage = leer) und `## Manuskript` („Noch nicht begonnen.“ und beim Glossar leer) |
| `MARKER_COUNT_TEXT`, Block `MARKERS` (`MARKER_TYPE`, `MARKER_LABEL`, `MARKER_TEXT`) | offene Marker im Text wie im Abschnittsformular |
| `APPROVAL_WRITING`, `APPROVAL_SECTION` | `approvals.writing`, `approvals.section` als `true`/`false` |
| `SIGNED`, `BYLINE`, `PLACE_DATE` | `1` bei Vorwort und Nachwort; `byline`, `place_date` aus dem Kopf |
| `GLOSSARY`, `GLOSSARY_INTRO`, Block `GLOSSARY_ENTRIES` (`G_TERM`, `G_TEXT`) | `1` beim Glossar; Einleitung und Einträge (`glossary_entries`), alphabetisch nach DIN 5007-1 |
| Block `SERIES_TERMS`: `T_TERM`, `T_TEXT`, `T_BOOK_TEXT`, `T_STATE`, `T_STATE_TEXT`; `SERIES_ID`, `SERIES_TITLE` | nur beim Glossar eines Bandes einer Serie mit Begriffen (#116): Vergleich `series/<ser-id>/glossary.yml` mit dem Glossar des Buchs (`series.compare_terms`): `missing` (nur in der Serie), `same`/`differs` (im Buch gleich bzw. abweichend), `own` (nur im Buch); sonst Block weglassen |
| `RESEARCH`, `GHOSTWRITING` | `1`, wenn Recherche bzw. Ghostwriting für die Art erlaubt ist (`MATTER_RESEARCH`, `MATTER_GHOSTWRITING`) |
| `PERSONAL_NOTE` | Hinweis bei Widmung und Danksagung, dass der Autor den Text selbst schreibt; sonst leer |

### `ki-angabe.html`

Formular „KI-Angabe im Buch“ (`render_view.py ai-disclosure`, #78; `scripts/ai_disclosure.py`).

| Platzhalter | Quelle |
|---|---|
| `AI_MODE`, `AI_PLACEMENT`, `AI_NAME_SERVICES`, `AI_TEXT` | `ai_disclosure.mode`, `.placement`, `.name_services` (`true`/`false`), `.text` (Vorgaben: none, imprint, false, leer) |
| `AI_USED_TEXT` | laut Lauf-Dateien genutzte Aufgaben und Dienste (`usage`), z. B. „Recherche: Perplexity · Textentwürfe: Anthropic Claude“; leer = keine Läufe |
| `AI_PROPOSAL_SHORT`, `AI_PROPOSAL_SHORT_NAMED`, `AI_PROPOSAL_DETAILED`, `AI_PROPOSAL_DETAILED_NAMED` | `suggest` für kurz/ausführlich ohne bzw. mit Dienstnamen; leer = keine Läufe |
| `AI_PLACES_MISSING` | Orte ohne Grundlage, kommagetrennt: `foreword`/`afterword` ohne Vorwort bzw. Nachwort, `imprint` bei ausgeschaltetem Impressum |
| `AI_LEGAL_HINT` | `LEGAL_HINT` aus `scripts/ai_disclosure.py` |

### `ausgabeoptionen.html`

Formular „Ausgabeoptionen“ (`render_view.py output`, #68).

| Platzhalter | Quelle |
|---|---|
| `OUTPUT_JSON` | JSON-Text: `typesetting` (alle Felder, Vorgaben ergänzt), `publication`, `print`, `cover` (wie in `ghostwriter.yml`, fehlend = `{}`), `blurb` und `author_bio` (aus `cover/rueckseite.md`, `## Klappentext` bzw. `## Über …`) |

### `buch-anlegen.html`

Formular „Neues Buch“ (`render_view.py book-create`, `START.md`, „Neues Buch“).

| Platzhalter | Quelle |
|---|---|
| `BRANCH_PREFIX` | `library.book_prefix` aus `ghostwriter-manifest.yml` (`buch/`) |
| `WORKING_TITLE`, `TITLE_SHORT` | gesendete Werte (`--draft`), sonst leer |
| `AUTHOR` | gesendeter Wert, sonst Autor des zuletzt geänderten Buchs aus `library.json` |
| `ERROR_TEXT` | `error` aus `--draft` (z. B. Name inzwischen vergeben); sonst leer |
| Block `TAKEN`: `TAKEN_SLUG`, `TAKEN_BRANCH` | alle Bücher der Bibliothek: `slug` und `branch` |
| `SERIES_ID`, `SERIES_TEXT` | nur bei „Neues Buch in dieser Serie“ (`--draft '{"series_id":"ser-…"}'`, #116): ID und „Band N der Serie „…““ (nächste Bandnummer); der Autor ist dann der des letzten Bandes. Sonst leer |

### `serie.html`

Seite einer Serie (#116, `render_view.py series <ser-id|S1|Titel>`, `START.md`, „Serien“).

| Platzhalter | Quelle |
|---|---|
| `LIBRARY_NAME` | `owner/repo` (`--repo`) |
| `SERIES_ID`, `SERIES_TITLE`, `SERIES_SUBTITLE`, `SERIES_DESCRIPTION` | `series/<ser-id>/series.yml`: `id`, `title`, `subtitle`, `description` |
| `SERIES_KIND_TEXT` | `kind`: `continuous` „durchgehende Handlung“, `standalone` „eigenständige Bände“ |
| `VOLUME_COUNT_TEXT` | „1 Band“, „N Bände“ |
| Block `VOLUMES`: `V_NUMBER`, `V_BRANCH`, `V_TITLE`, `V_TITLE_SHORT`, `V_STATE`, `V_STATE_TEXT`, `V_PROGRESS`, `V_PROGRESS_TEXT`, `V_EDITION_TEXT` | je Band in Reihenfolge (`volumes`) die Werte wie im Bücherregal (`BOOK_…`); ein Branch, den es nicht mehr gibt, mit „nicht gefunden“ |
| Block `CANDIDATES`: `C_BRANCH`, `C_TITLE` | Bücher der Bibliothek, die zu keiner Serie gehören; keine = Block weglassen |
| Block `SERIES_CHARACTERS`: `SC_ID`, `SC_NAME`, `SC_ROLE`, `SC_SHORT` | Figuren der Serie (`series/<ser-id>/characters/`); keine = Block weglassen |
| Block `SERIES_TERMS`: `ST_TERM`, `ST_TEXT` | Begriffe der Serie (`series/<ser-id>/glossary.yml`); keine = Block weglassen |
| `OMNIBUS_STATE`, `OMNIBUS_TITLE`, `OMNIBUS_TEXT` | Sammelband (`series/<ser-id>/omnibus.yml`): `status` (`draft`, `approved`), `title`, „N Bände · freigegeben bzw. Entwurf · Auflage N“; ohne Sammelband weglassen |

### `sammelband.html`

Formular „Sammelband“ (#116, Stufe 4, `render_view.py omnibus-edit <ser-id>`).

| Platzhalter | Quelle |
|---|---|
| `SERIES_ID`, `SERIES_TITLE` | Serie |
| `OMNIBUS_TITLE`, `OMNIBUS_SUBTITLE`, `OMNIBUS_FOREWORD`, `OMNIBUS_AFTERWORD` | `omnibus.yml`: `title` (neu: „<Reihe> – Sammelband“), `subtitle`, `foreword`, `afterword` |
| `OMNIBUS_ISBN_PRINT`, `OMNIBUS_ISBN_EBOOK` | `publication.isbn_print`, `publication.isbn_ebook` |
| `OMNIBUS_STATE` | `status`; leer, wenn es noch keinen Sammelband gibt |
| `OMNIBUS_EDITION`, `OMNIBUS_TAG` | `current_edition` (0 = noch keine) und der Tag der nächsten Auflage (`<reihen-slug>-sammelband-auflage-N`) |
| Block `OVOLUMES`: `OV_NUMBER`, `OV_BRANCH`, `OV_TITLE`, `OV_ON`, `OV_EDITION`, `OV_LAST`, `OV_TEXT` | je Band der Serie: Nummer, Branch, Titel, ob gewählt, gewählte Auflage (leer = neueste), neueste Auflage aus `library.json` (`last_edition`; 0 = keine, dann nicht wählbar) |
| Block `KEEP`: `K_KIND`, `K_LABEL`, `K_ON` | Teile von Vor- und Nachspann der Bände; `keep_matter` (Vorgabe Prolog und Epilog) |

### `serie-bearbeiten.html`

Formular „Neue Serie“ bzw. „Serie bearbeiten“ (#116, `render_view.py series-edit [<ser-id>]`).

| Platzhalter | Quelle |
|---|---|
| `SERIES_ID` | leer bei einer neuen Serie, sonst `id` |
| `SERIES_TITLE`, `SERIES_SUBTITLE`, `SERIES_KIND`, `SERIES_DESCRIPTION` | gesendete Werte (`--draft`), sonst die der Serie; neue Serie: leer bzw. `continuous` |
| `ERROR_TEXT` | `error` aus `--draft`; sonst leer |
| `SERIES_ISSN`, `SERIES_ALSO` | `issn` (sonst leer) und `also_in_series` als `true`/`false` (fehlt = `true`) |
| Block `TAKEN`: `TAKEN_TITLE` | Titel der anderen Serien (das Formular sperrt doppelte Titel) |

### `auswahl.html`

Auswahlkarten für feste Antwortmöglichkeiten im Einstiegsdialog (`START.md`, Abschnitt 4, „Auswahlkarten“) und in anderen geführten Dialogen. Erzeugt mit `render_view.py choice wizard.N` aus `templates/wizard-choices.yml` oder mit `--spec` für eine eigene Auswahl.

| Platzhalter | Quelle |
|---|---|
| `STEP` | Kennung des Schritts (`wizard.N` bzw. `step` aus `--spec`); geht in `wizard.answer` unverändert zurück |
| `TITLE`, `SUBTITLE`, `NOTE` | `title`, `subtitle`, `note` des Schritts; `{step}` und `{steps}` werden durch Schrittnummer und `steps_total` ersetzt |
| `SKIPPABLE` | `1`, wenn der Schritt `skippable: true` hat, sonst leer (Knopf „Überspringen“ entfällt) |
| Block `QUESTIONS`: `Q_INDEX`, `Q_KEY`, `Q_HEADER`, `Q_TEXT`, `Q_MULTI` | je Frage: laufende Nummer ab 1, `key`, `header` (höchstens 12 Zeichen), `text`, `1` bei `multi: true` |
| Block `OPTIONS`: `OPT_Q`, `OPT_VALUE`, `OPT_LABEL`, `OPT_DESC`, `OPT_RECOMMENDED`, `OPT_SELECTED` | alle Antworten aller Fragen in einem flachen Block (gw.js kennt keine verschachtelten Blöcke): `Q_INDEX` der Frage, `value`, `label`, `desc`, `1` bei `recommended`, `1`, wenn `field` in `ghostwriter.yml` diesen Wert schon hat |

### `ki-dienste.html`

| Platzhalter | Quelle |
|---|---|
| Block `SERVICES`: `SERVICE_ID`, `SERVICE_NAME`, `SERVICE_GROUP`, `SERVICE_ROLES`, `SERVICE_NOTE` | alle Dienste aus `providers.yml` (`providers` → `llm`, `search_tools` → `search`, `queue_agents` außer `manual` → `agent`); `SERVICE_ROLES` sind die `roles` des Dienstes, bei `search` „search“, bei `agent` „queue_processing“; `SERVICE_NOTE` aus Sitzland, Websuche und `note` |
| `SERVICE_AVAILABLE` | `true`, wenn die ID in `ai_providers.available` steht, sonst leer |
| `SERVICE_GUIDE_URL` | Link „Anleitung“ ins Repository des Buchs (`https://github.com/<owner>/<repo>/blob/<branch>/<pfad>`): `setup` des Dienstes, sonst der passende Abschnitt in `docs/DIENSTE-NUTZEN.md` (Chat-Dienst mit App: Weg 2, lokal: Weg 3, nur API oder Plattform: Weg 4, Recherchequellen, Agenten) |
| `SERVICE_WEBSITE_URL` | `url` des Dienstes für den Link „Website“; leer, wenn es keine gibt |
| `SERVICE_ACCESS_OPTIONS`, `SERVICE_ACCESS` | mögliche Zugänge und gewählter Zugang (`ai_providers.services.<id>.access`, sonst der erste): Chat-Dienste `app`/`api`/`cli` laut `access` in `providers.yml`, lokale `local`, Kataloge `web`/`api`, Such-APIs `api`, Agenten `github` |
| `SERVICE_MODEL`, `SERVICE_GITHUB`, `SERVICE_PLAN`, `SERVICE_COST`, `SERVICE_MEMO` | aus `ai_providers.services.<id>`: `model`, `github_connected` (`true` oder leer), `plan`, `monthly_cost` (Zahl ohne Währung, leer = unbekannt), `note` |
| `SERVICE_SECRET` | `ai_providers.services.<id>.api_key_secret`, sonst `SERVICE_SECRET_DEFAULT` |
| `SERVICE_SECRET_DEFAULT`, `SERVICE_SECRET_ALT`, `SERVICE_KEY_URL` | aus `providers.yml`: `api_key_secret` (ohne Eintrag `<ID>_API_KEY`), `api_key_alt`, `api_key_url` (ohne Eintrag `url`) |
| `SERVICE_SECRET_STATE` | aus `ghostwriter-index.json`, Feld `secrets`: `ok` (Secret vorhanden), `alt` (nur das alternative Secret vorhanden), `missing` (fehlt), leer (unbekannt, z. B. Name geändert oder noch nicht geprüft) |
| `CONNECTOR_GUIDE_URL` | Link auf `docs/CONNECTOR-SETUP.md` im Repository des Buchs |
| `SECRETS_URL` | `https://github.com/<owner>/<repo>/settings/secrets/actions/new` |
| `KEYS_GUIDE_URL` | Link auf `docs/DIENSTE-NUTZEN.md#api-schlüssel-als-github-secret` |
| Block `ROLES`: `ROLE_ID`, `ROLE_LABEL`, `ROLE_HINT`, `ROLE_VALUE` | die Aufgaben `default`, `research`, `brainstorming`, `writing`, `revision`, `fact_check`, `queue_processing`; `ROLE_VALUE` ist `provider` bzw. bei der Warteschlange `agent` (leer = wie Standard) |

### `freigabe-bestaetigen.html`

| Platzhalter | Quelle |
|---|---|
| `APPROVAL_KIND` | `writing`, `section` oder `chapter` aus `approval.open` |
| `APPROVAL_REVOKE` | `true` beim Zurücknehmen (`revoke` in `approval.open`), sonst leer |
| `APPROVAL_TITLE`, `APPROVAL_BUTTON`, `APPROVAL_EFFECT` | Überschrift, Knopf und Satz zur Wirkung, je nach Art (Muster: `render_view.py approval-…`) |
| `TARGET_ID`, `TARGET_LABEL` | Abschnitts- bzw. Kapitel-ID und „Abschnitt N.M „Titel““ bzw. „Kapitel N „Titel““ |
| `HEAD_SHA`, `HEAD_SHORT` | gelesener Stand, voll und mit 7 Zeichen; er landet als `commit` in `approvals.yml` |
| Block `CHECKS`: `CHECK_STATE`, `CHECK_TEXT` | Prüfpunkte nach `START.md`, „Freigaben“, Schritt 2: `ok`, `warn` oder `block`; bei `block` ist Bestätigen gesperrt |

### `aenderungen-uebernehmen.html`

| Platzhalter | Quelle |
|---|---|
| `PENDING_TEXT`, `PENDING_PR` | wie in der Projektübersicht |
| `BOOK_BRANCH`, `WORK_BRANCH` | Buch-Branch und Arbeits-Branch (`ghostwriter/<buch-branch>`) |
| `HEAD_SHA` | letzter Commit des Arbeits-Branchs; `gw.js` schickt ihn mit `changes.merge` zurück |
| Block `CHANGES`: `CHANGE_MESSAGE`, `CHANGE_DATE`, `CHANGE_SHA` | je Commit des Pull Requests, älteste zuerst: erste Zeile der Commit-Nachricht, Datum `TT.MM.JJJJ, HH:MM`, Commit mit 7 Zeichen |

### `abschnitt-anlegen.html`

| Platzhalter | Quelle |
|---|---|
| `CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE` | das Kapitel |
| `FACT_CHECK_DEFAULT` | `workflow.fact_checking_default`, sonst `optional` |
| Block `POSITIONS`: `POSITION_LABEL`, `POSITION_SELECTED` | „Am Anfang (vor N.1)“, dann „Nach N.M „Titel““ je Abschnitt; die letzte lautet „Am Ende (nach N.M „Titel“)“. Ohne Abschnitte nur „Als erster Abschnitt“. Vorauswahl am Ende |

### `reihenfolge.html`

Für Kapitel und Abschnitte.

| Platzhalter | Quelle |
|---|---|
| `REORDER_KIND` | `chapter` bzw. `section` |
| `REORDER_HEADING` | „Kapitelreihenfolge ändern“ bzw. „Abschnittsreihenfolge in Kapitel N ändern“ |
| `CHAPTER_ID`, `CHAPTER_NUMBER` | bei Abschnitten das Kapitel, sonst leer |
| Block `ITEMS`: `ITEM_ID`, `ITEM_NUMBER`, `ITEM_TITLE` | Kapitel bzw. Abschnitte in der bisherigen Reihenfolge |

### `projekteinstellungen.html`

| Platzhalter | Quelle |
|---|---|
| `FACT_CHECK_DEFAULT` | `workflow.fact_checking_default`, sonst `optional` |
| `PAGE_SIZE`, `FONT`, `FONT_SIZE`, `TOC_DEPTH` | `typesetting`, fehlende Felder mit den Vorgaben aus `docs/DATA-MODEL.md` |
| `TITLE_PAGE`, `IMPRINT`, `TOC` | `typesetting` als `true`/`false` |
| Block `FIXED`: `FIXED_LABEL`, `FIXED_VALUE` | KI-Grundeinstellungen (`ai_settings`) und Freigabepflichten (`workflow.require_…`), nur zur Anzeige |
| `UPDATES_AUTO` | `updates.auto` als `true`/`false`; fehlt der Block, `true` |
| `CHANGES_AUTO_MERGE` | `changes.auto_merge` als `true`/`false`; fehlt der Block, `false` |
| `LIMIT_BUDGET`, `LIMIT_MINUTES` | `limits.ai_budget_monthly` bzw. `limits.actions_minutes_monthly` als Zahl; fehlt = leer (keine Prüfung) |
| `LIMIT_SUMMARY` | Stand der Limits aus `scripts/limits.py` (`limit_summary`), z. B. „KI-Budget 62 % übrig (3,80 von 10,00 €).“ oder „Keine Limits eingestellt.“ |
| `AI_DISCLOSURE_TEXT` | KI-Angabe kurz, z. B. „kurz, im Impressum“, „keine“ (`ai_disc_text`) |
| `GW_VERSION_TEXT` | „Installiert: GhostWriter <version>“ aus `ghostwriter-manifest.yml`, dazu „ · zuletzt aktualisiert am TT.MM.JJJJ“ aus `.ghostwriter/update.yml` (`updated_at`), falls vorhanden |
| `GW_UPDATE_HINT` | nur wenn `.ghostwriter/update.yml` `skipped_workflows` enthält: Hinweis auf das Secret `GHOSTWRITER_UPDATE_TOKEN` (`docs/UPDATES.md`); sonst leer |

## Textfassung ohne Widgets

Im Modus „Nur Text“ (siehe „Darstellungsmodus“) bekommt der Chat dieselben Inhalte als Markdown. **Dort nie HTML, `GW.render` oder Widget-Code ausgeben.** Muster erzeugt `scripts/render_view.py … --text`; jede Ansicht und jedes Formular hat eine Textfassung.

Gestaltung:

- **Überschrift** `###` mit Symbol: 📘 Projekt, 📖 Kapitel, ✏️ Abschnitt, 📜 Vor- und Nachspann, 📝 Bearbeiten, ➕ Anlegen, ↕️ Reihenfolge, ⚙️ Einstellungen, 📚 Auflage bzw. Bücherregal, 📗 Neues Buch, 🗂️ Daten, 🔀 Änderungen übernehmen, ✅ Freigeben, ↩️ Freigabe zurücknehmen, 🤖 KI-Dienste.
- **Status** deutsch mit Symbol: ⚪ geplant, 🔎 Recherche, 💡 Ideensammlung, 🟦 bereit zum Schreiben, ✏️ Schreiben bzw. in Arbeit, 🔁 Überarbeitung, 🔍 Faktencheck bzw. Durchsicht, 🟡 bereit zur Freigabe, ✅ freigegeben.
- **Marker** als Symbol mit Anzahl: 💬 Anekdote, 📚 Quelle, 🩺 Medizin, ⚖️ Recht; darunter klein die Legende.
- **Tabellen** für Listen und Felder; Zahlen und Kosten rechtsbündig.
- **Aktionen** am Ende nach einer Trennlinie als Kürzel in Inline-Code: Zahlen öffnen Kapitel (`2`) oder Abschnitte (`2.4`), Buchstaben lösen Aktionen aus.
- **Formulare** zeigen die aktuellen Werte als Tabelle; geantwortet wird mit `Feld: neuer Wert`, je Zeile ein Feld. `X` bricht ab.

| Ansicht | Kürzel |
|---|---|
| Bücherregal | `1`–`N` Buch öffnen · `S1`–`SN` Serie öffnen · `N` Neues Buch · `NS` Neue Serie · `D` Daten |
| Serie | `1`–`N` Band öffnen · `H` Band hinzufügen · `R` Reihenfolge ändern · `ENT` Band entfernen · `NB` Neues Buch in dieser Serie · `B` Serie bearbeiten · `Ü` Bücherregal |
| Daten | `Ü` Bücherregal · `U` Update einspielen (nur wenn dahinter) |
| Figuren | Name einer Figur öffnet sie · `+ Name` legt eine Figur an (optional `Rolle: Nebenfigur`) · `Ü` Übersicht |
| Projektübersicht, Kapitel, Abschnitt, Teil, Figuren, Serie | zusätzlich `FV` 👤 Figuren aus dem Text vorschlagen |
| Projektübersicht | `FI` Figuren · `L` Bücherregal (nur ab zwei Büchern) · `S` Serie (nur bei einem Band einer Serie) · `1`–`N` Kapitel öffnen (📖) · `B1`–`BN` Kapitel bearbeiten (✎ in jeder Kapitelzeile, wie der Bearbeiten-Knopf der Kapitelansicht) · `N.M` zuletzt bearbeiteter Abschnitt · Titel eines Teils von Vor- oder Nachspann öffnet ihn (nur vorhandene) · `M` Änderungen übernehmen (nur bei offenen Änderungen) · `D` KI-Dienste · `P` Projektdaten · `N` Neues Kapitel · `R` Kapitelreihenfolge · `V` Vor- und Nachspann · `A` Neue Auflage · `E` Einstellungen |
| Vor- und Nachspann | Titel eines Teils öffnet ihn · `+ Widmung` usw. legt einen fehlenden Teil an · `Ü` Übersicht |
| Glossar | `+ Begriff: Erklärung` aufnehmen · `Begriff: neue Erklärung` ändern · `- Begriff` entfernen · `VB` Begriffe vorschlagen · `F` Titel, Ziel, Einleitung · `FS`, `FA` Freigaben · `RS` Recherche je Begriff · `Ü` Übersicht |
| Teil des Vor- oder Nachspanns | `T` Text ändern · `F` Titel und Ziel (Vorwort, Nachwort: dazu Verfasser, Ort und Datum) · `FS` Schreiben freigeben bzw. zurücknehmen · `FA` freigeben bzw. zurücknehmen · `RS`, `GS` Recherche bzw. Ghostwriting sofort (Vorwort, Prolog, Epilog, Nachwort) · `Ü` Übersicht |
| Kapitelansicht | `N.1`–`N.M` Abschnitt öffnen · `B` Kapitel bearbeiten · `Z` Ziel, Kurzbeschreibung, Kapitelrecherche · `N` Neuer Abschnitt · `R` Abschnittsreihenfolge · `FK` Kapitel freigeben (nur wenn möglich) · `Ü` Übersicht |
| Abschnitt | `T` Text ändern (geänderten Text schicken) · `F` Ziel, Kurzbeschreibung, Faktencheck · `FS` Schreiben freigeben bzw. zurücknehmen · `FA` Abschnitt freigeben bzw. zurücknehmen · `RS` Recherche sofort · `GS` Ghostwriting sofort · `N.M` vorheriger/nächster Abschnitt · `K` Zum Kapitel |
| Formulare | `Feld: Wert` je Zeile · Ausgabeoptionen: `Ränder: klassisch`, `Formate: PDF, EPUB`, `ISBN E-Book: …` · KI-Angabe: `Angabe: kurz`, `Ort: Nachwort`, `Dienste nennen: ja`, `Text: …`, `OK` übernimmt den Vorschlag · Reihenfolge als Nummernliste · Auflage: `OK` übernimmt den Vorschlag · Änderungen übernehmen: `OK` übernimmt · Freigabe: `OK` bestätigt · Neues Buch: `Titel: …`, `Kurztitel: …`, `Autor: …` · Auswahl: `1b, 2a` (Frage und Buchstabe; bei Mehrfachauswahl `2a c`), eigene Antwort `1: Text`, `S` überspringt (nur wenn angeboten) · Kapitelrecherche: `Ziel: …`, `Kurzbeschreibung: …`, `Frage: …`, `Schwerpunkte: …`, `Aufgabe: Ziel|Abschnitte|Kurzbeschreibung|keine`, `Vorher: 0–3`, `Nachher: 0–3`, `VZ`/`VK` Vorschlag übernehmen, `AS 1, 3` vorgeschlagene Abschnitte anlegen · KI-Dienste: `+ id`, `- id`, `Aufgabe: id` · `X` bricht ab |

Ein Kürzel entspricht dem Klick auf den gleichnamigen Knopf; es gelten dieselbe Aktion, dieselben Statuszeilen und dieselbe Ausgangsansicht danach.

Zusätzlich gelten überall die ausgeschriebenen Befehle aus `START.md`, Abschnitt 0, „Befehle“ (`Start`, `Übersicht`, `Kapitel 3`, `Hilfe` …).

## Nachrichtenformat

Jede Vorlage schickt eine Nachricht aus einer lesbaren Zeile und den festen Daten. Der Chat zeigt die Nachricht vollständig an; damit sie unauffällig bleibt, gibt es zwei Formen.

**Kurzform** für Klicks ohne Eingaben (Ansichten öffnen, Formulare öffnen, Navigation): eine Zeile Inline-Code `gw:<aktion>`, dahinter die Daten als `schlüssel=wert`, getrennt durch Leerzeichen:

````text
Abschnitt 2.4 „Die Scham, die wir mitbringen“ bearbeiten

`gw:view.section section_id=sec-02-04-die-scham-die-wir-mitbringen`
````

**Block** für alles mit Eingaben (Formulare speichern) oder wenn ein Wert Leerzeichen enthält, leer oder länger als 80 Zeichen ist: JSON im Block `gw`:

````text
Projektdaten speichern: ADHS im Erwachsenenleben

```gw
{"action":"project.update","title":"ADHS im Erwachsenenleben", …}
```
````

Welche Form gilt, entscheidet `gwSend` in `ghostwriter-ui` selbst. Beide Formen bedeuten dasselbe: Kurzform `gw:a k=v` entspricht `{"action":"a","k":"v"}`; Zahlen und `true`/`false` werden als solche gelesen. Der Assistent wertet die Daten aus; die Zeile darüber ist für Menschen. Freie Eingaben ohne Daten bleiben erlaubt.

| Aktion | Daten | Bedeutung | Antwort des Assistenten | Endpunkt in `docs/API-CONTRACT.md` (Weg B) |
|---|---|---|---|---|
| `view.project` | – | Projektübersicht zeigen | Vorlage `projektuebersicht` (`render_view.py project`) | `GET /v1/projects/{owner}/{repo}` |
| `view.chapter` | `chapter_id` | Kapitelansicht zeigen | Vorlage `kapitelansicht` (`render_view.py chapter N`) | `GET /v1/projects/{owner}/{repo}` |
| `view.section` | `section_id` | Abschnittsformular zeigen | Vorlage `abschnitt-bearbeiten` (`render_view.py section N.M`) | `GET /v1/projects/{owner}/{repo}` |
| `view.matter` | `matter_id` (leer = alle Teile) | Teil von Vor- oder Nachspann zeigen bzw. die Liste „Vor- und Nachspann“ (#57) | Vorlage `teil-bearbeiten` (`render_view.py matter <teil>`) bzw. `vor-nachspann` (`render_view.py matter`) | `GET /v1/projects/{owner}/{repo}` |
| `view.images` | `section_id` (auch `mat-…`) | Bilder eines Abschnitts zeigen (#54) | Vorlage `bilder` (`render_view.py images <N.M|id>`) | `GET /v1/projects/{owner}/{repo}` |
| `image.prompt` | `section_id`, `scene`, `characters` (optional) | Bild-Auftrag zusammensetzen | `python scripts/images.py . prompt …`; Prompt zeigen, dann im Chat erzeugen oder als „Auftrag kopieren“ ausgeben (`START.md`, „Illustrationen“); nichts schreiben | – |
| `image.add` | `section_id`, `caption`, `alt`, `source`, `provider`, `prompt`, Datei als Anhang, `expected_head_sha` | Bild ablegen | `python scripts/images.py . add …`, ein Commit; danach die Bilder des Abschnitts | `POST …/sections/{section_id}/images` |
| `image.place` | `image_id`, `section_id` | Bild in den Text setzen | nachfragen, wohin (nach welchem Absatz), dann mit Schreibfreigabe die Zeile `![](bild:img-…)` als eigenen Absatz einfügen, Commit wie `section.update`; ohne Schreibfreigabe zuerst die Freigabe anbieten | `PUT …/sections/{section_id}/manuscript` |
| `view.characters` | – | Liste der Figuren zeigen (#53, Befehl `Figuren`) | Vorlage `figuren` (`render_view.py characters`) | `GET /v1/projects/{owner}/{repo}` |
| `view.character` | `character_id` | Formular einer Figur zeigen | Vorlage `figur-bearbeiten` (`render_view.py characters <id>`) | `GET /v1/projects/{owner}/{repo}` |
| `character.create` | `name`, `role`, `expected_head_sha` | Figur anlegen | `python scripts/characters.py . add "<Name>" --role <role>`, Commit nach `START.md`, „Figuren“; danach das Formular der neuen Figur | `POST …/characters` |
| `character.update` | `character_id`, `name`, `role`, `short`, `age`, `appearance`, `traits` (Liste), `voice`, `visual`, `relations` (Liste `{to, kind}`), `description`, `notes`, `expected_head_sha` | Figur speichern | `python scripts/characters.py . update <id> '<json>'`, ein Commit; danach das Formular | `PATCH …/characters/{character_id}` |
| `matter.create` | `kind` (`dedication` \| `foreword` \| `prologue` \| `epilogue` \| `afterword` \| `glossary` \| `acknowledgments`), `title` (optional), `expected_head_sha` | Teil anlegen | `python scripts/matter.py . add <art> [--title …]`, Commit nach `START.md`, „Vor- und Nachspann“; danach der neue Teil | `POST …/matter` |
| `matter.update` | `matter_id`, `title`, `goal`, `manuscript`, bei Vorwort und Nachwort `byline`, `place_date`, `expected_head_sha` (nie `approvals`) | Teil speichern | Datei in `matter/` (und bei neuem Titel `ghostwriter.yml`) schreiben, danach der Teil | `PATCH …/matter/{matter_id}` |
| `character.suggest` | `scope` (`book`, Kapitelnummer, `N.M`, `mat-…` bzw. `ser-…`) | Figuren aus dem Text vorschlagen | `python scripts/characters.py . scan <scope>` (Serie: `scripts/series.py . scan <ser-id>`), Teil für Teil lesen, Vorschläge als JSON (`START.md`, „Figuren“, Schritt 6), dann Vorlage `figuren-vorschlag` (`render_view.py character-suggest --draft …`) | – |
| `import.edit` | `ops` (Liste, siehe `scripts/import_book.py`: `rename_chapter`, `rename_section`, `split_scenes`, `merge_sections`, `merge_chapters`, `split_chapter`, `to_matter`, `to_chapter`) | Gliederung des Import-Vorschlags ändern | Action „Manuskript importieren“ mit `step: edit` und `ops` (bzw. `import_book.py . edit`), danach die Vorschau neu | `PATCH /v1/projects/{owner}/{repo}/import` |
| `import.apply` | `writing_approval` (nur mit Häkchen) | Buch aus dem Vorschlag anlegen | Action mit `step: apply` (bzw. `import_book.py . apply [--writing-approval]`), danach die Projektübersicht und das Angebot der Analysen | `POST /v1/projects/{owner}/{repo}/import/apply` |
| `analysis.start` | `kind` (`characters`, `summaries`, `style`, `places`, `timeline`, `continuity`, `language`; mehrere mit Komma), `scope` (`book` bzw. Kapitelnummer), optional `confirm_low_budget` | Analyse im Hintergrund starten (#123) | vorher `python scripts/analyze.py . plan --scope …` (Umfang, Tokens, Kosten) und Limits zeigen; nach Bestätigung die Action „Analyse im Hintergrund“ auf dem Buch-Branch starten (`POST /repos/{owner}/{repo}/actions/workflows/analyse.yml/dispatches`, `ref` = Buch-Branch, `inputs`) | `POST /v1/projects/{owner}/{repo}/analyses` |
| `analysis.open` | `kind`, `run` (Pfad der Vorschlagsdatei) | Vorschläge eines Hintergrundlaufs ansehen | `render_view.py analysis-suggest --draft <run>`: Figuren in `figuren-vorschlag` (Übernehmen wie `character.suggest.apply` mit `run`), Kurzbeschreibungen in `kurzbeschreibung-vorschlag`, Stilprofil in `stilprofil-vorschlag`, Schauplätze in `orte-vorschlag`, Zeitleiste in `zeitleiste-vorschlag`, Widersprüche in `widerspruch-vorschlag`, Sprache in `sprache-vorschlag` (Übernehmen mit `analysis.apply`) | – |
| `analysis.apply` | `kind` (`summaries`, `style`, `places`, `timeline`, `continuity`, `language`), `run` (`run-NNN`), `choices` (Kurzbeschreibungen: Liste `{index, goal?, short?}`, nur angehakte Felder; Stilprofil: `{index, value}`; Schauplätze: `{index, name, kind, short, merge_into?}`; Zeitleiste: `{index, when, what}` je Ereignis und `{issue, text}` je Hinweis; Widersprüche: `{index, text, mark}` mit den Nummern der Fundstellen für den Marker; Sprache: `{index}`) | Ausgewählte Vorschläge eines Hintergrundlaufs übernehmen | Auswahl als JSON-Datei, dann `python scripts/analyze.py . apply run-NNN --kind <art> <datei>` (schreibt nur die genannten Felder und vermerkt den Lauf als erledigt); ein Commit „Analyse übernommen: …“, danach die Projektübersicht. „Verwerfen“ (`form.cancel` mit `form: analysis.apply`, `kind`, `run`): `python scripts/analyze.py . applied run-NNN --kind <art>` | `POST /v1/projects/{owner}/{repo}/analyses/{kind}/{run}/apply` |
| `character.suggest.apply` | `scope`, `choices` (Liste `{index, name, role, short, merge_into?, target?}`), optional `run` (Hintergrundlauf; nach dem Übernehmen `characters.py apply … --run run-NNN`, auch beim Verwerfen als erledigt vermerken: `analyze.py applied run-NNN`) | Ausgewählte Vorschläge übernehmen | Auswahl mit der eigenen JSON-Datei zusammenführen (`selected`, geänderte Namen, `merge_into`, `target: series`), dann `python scripts/characters.py . apply <datei>` (bei `target: series` mit `--series-repo`; Serienebene: `scripts/series.py . apply-characters <ser-id> <datei>`); ein Commit im Buch, ggf. einer auf dem Standard-Branch; danach die Figurenliste | `POST /v1/projects/{owner}/{repo}/characters/suggestions` |
| `character.series.update` | `series_id`, `character_id` und die Felder wie bei `character.update`, `expected_head_sha` | Figur der Serie speichern (gilt für alle Bände ohne eigene Kopie, #116) | `python scripts/characters.py <standard> series-update <ser-id> <id> '<json>'`, ein Commit auf dem Standard-Branch; danach das Formular | `PATCH /v1/projects/{owner}/{repo}/series/{series_id}/characters/{character_id}` |
| `character.detach` | `character_id` | Kopie einer Figur der Serie nur für dieses Buch | `python scripts/characters.py . detach <id>`, ein Commit im Buch; danach das Formular | `POST /v1/projects/{owner}/{repo}/characters/{character_id}/detach` |
| `character.align` | `character_id` | Kopie entfernen, wieder die Figur der Serie | `python scripts/characters.py . align <id>`, ein Commit im Buch | `POST /v1/projects/{owner}/{repo}/characters/{character_id}/align` |
| `character.adopt` | `character_id` | Figur des Buchs (Kopie oder eigene) in die Serie übernehmen | `python scripts/characters.py . adopt <id> --series-repo <standard>`: Commit auf dem Standard-Branch (Figur der Serie), dann Commit im Buch (Kopie entfernt) | `POST /v1/projects/{owner}/{repo}/characters/{character_id}/adopt` |
| `matter.glossary.from_series` | `matter_id`, `term` | Begriff der Serie ins Glossar des Buchs übernehmen bzw. die Kopie angleichen (#116) | `python scripts/matter.py . glossary-from-series "<Begriff>"`, ein Commit im Buch; danach das Glossar | `POST /v1/projects/{owner}/{repo}/matter/{matter_id}/glossary/from-series` |
| `matter.glossary.to_series` | `matter_id`, `term` | Begriff des Buchs mit seiner Erklärung in die Serie übernehmen | `python scripts/matter.py . glossary-to-series "<Begriff>" --series-repo <standard>`, ein Commit auf dem Standard-Branch | `POST /v1/projects/{owner}/{repo}/series/{series_id}/glossary` |
| `series.omnibus.edit.open` | `series_id` | Formular „Sammelband“ zeigen | Vorlage `sammelband` (`render_view.py omnibus-edit <ser-id>`) | – |
| `series.omnibus.update` | `series_id`, `title`, `subtitle`, `volumes` (Liste `{branch, edition?}`), `keep_matter`, `foreword`, `afterword`, `publication` (`isbn_print`, `isbn_ebook`), `expected_head_sha` | Sammelband anlegen bzw. speichern | `scripts/series.py omnibus-update <ser-id> '<json>'` (jede Änderung: wieder Entwurf), ein Commit auf dem Standard-Branch; danach das Formular | `PUT /v1/projects/{owner}/{repo}/series/{series_id}/omnibus` |
| `series.omnibus.approve` | `series_id` | Sammelband freigeben (ausdrücklich bestätigt im Formular) | `scripts/series.py omnibus-approve <ser-id>`; vorher `scripts/build_omnibus.py <repo> <ser-id> --check`; ein Commit | `POST /v1/projects/{owner}/{repo}/series/{series_id}/omnibus/approve` |
| `series.omnibus.revoke` | `series_id` | Freigabe des Sammelbands zurücknehmen | `scripts/series.py omnibus-revoke <ser-id>`, ein Commit | `DELETE /v1/projects/{owner}/{repo}/series/{series_id}/omnibus/approve` |
| `series.omnibus.publish` | `series_id` | Nächste Auflage des Sammelbands veröffentlichen | `scripts/series.py omnibus-publish <ser-id>` (Auflage + 1), ein Commit auf dem Standard-Branch; die Action „Sammelband veröffentlichen“ baut und veröffentlicht sie | `POST /v1/projects/{owner}/{repo}/series/{series_id}/omnibus/editions` |
| `matter.glossary.update` | `matter_id`, `title`, `goal`, `intro`, `set` (Liste `{term, explanation}`), `remove` (Liste von Begriffen), `expected_head_sha` | Glossar-Einträge aufnehmen, ändern, entfernen (#58) | `scripts/matter.py glossary-set` (neue Begriffe mit `--new`) bzw. `glossary-remove`, ein Commit, danach das Glossar | `PATCH …/matter/{matter_id}/glossary` |
| `matter.glossary.suggest` | `matter_id` | Begriffe aus dem freigegebenen Text vorschlagen (#58) | Vorschläge mit Fundstelle und Erklärungsentwurf als Auswahl zeigen (`START.md`, „Vor- und Nachspann“, Punkt 4); nichts schreiben | – |
| `view.library` | – | Bücherregal zeigen | Vorlage `buecherregal` (`render_view.py library --library library.json`) | – |
| `view.data` | – | Seite „Daten“ zeigen | Daten sammeln und Vorlage `daten` (`render_view.py data`, `START.md`, „Daten“) | `GET /v1/projects/{owner}/{repo}` |
| `library.book.open` | `branch` | Buch aus dem Bücherregal öffnen | Branch als Buch-Branch übernehmen, Projektübersicht zeigen; Buch im Aufbau: Einstiegsdialog fortsetzen | `GET /v1/projects/{owner}/{repo}` |
| `library.book.create.open` | – | Formular „Neues Buch“ zeigen | Vorlage `buch-anlegen` (`render_view.py book-create`) | – |
| `library.book.create` | `working_title`, `title_short`, `author`, `branch`, optional `series_id` | Neues Buch anlegen | Namen erneut prüfen, Branch und einen Commit anlegen (`START.md`, „Neues Buch“); mit `series_id` zusätzlich ein Commit auf dem Standard-Branch: als nächster Band der Serie (`START.md`, „Serien“); dann Einstiegsdialog auf dem neuen Branch | `POST /v1/projects/{owner}/{repo}/books` |
| `view.series` | `series_id` | Seite einer Serie zeigen | Vorlage `serie` (`render_view.py series <ser-id>`) | – |
| `series.create.open` | – | Formular „Neue Serie“ zeigen | Vorlage `serie-bearbeiten` (`render_view.py series-edit`); im Einzelbuch-Repository stattdessen der Hinweis auf die Umwandlung (#40) | – |
| `series.edit.open` | `series_id` | Formular „Serie bearbeiten“ zeigen | Vorlage `serie-bearbeiten` (`render_view.py series-edit <ser-id>`) | – |
| `series.create` | `title`, `subtitle`, `kind`, `description`, optional `issn`, `also_in_series`, `expected_head_sha` | Serie anlegen | `series/<ser-id>/series.yml` auf dem Standard-Branch (`scripts/series.py create`), danach Seite der Serie | `POST /v1/projects/{owner}/{repo}/series` |
| `series.update` | `series_id`, `title`, `subtitle`, `kind`, `description`, `expected_head_sha` | Serie speichern | `series.yml` ändern (ID bleibt; `scripts/series.py update`), danach Seite der Serie | `PATCH /v1/projects/{owner}/{repo}/series/{series_id}` |
| `series.volume.add` | `series_id`, `branch` | Buch als nächsten Band hinzufügen | prüfen (Buch der Bibliothek, noch in keiner Serie), in `volumes` anhängen (`scripts/series.py add`), danach Seite der Serie | `POST /v1/projects/{owner}/{repo}/series/{series_id}/volumes` |
| `series.volume.remove` | `series_id`, `branch` | Band aus der Serie entfernen | aus `volumes` streichen; das Buch bleibt unverändert (`scripts/series.py remove`), danach Seite der Serie | `DELETE /v1/projects/{owner}/{repo}/series/{series_id}/volumes/{branch}` |
| `series.reorder` | `series_id`, `order` (alle Buch-Branches), `expected_head_sha` | Bandreihenfolge speichern | `volumes` in neuer Reihenfolge (`scripts/series.py reorder`), danach Seite der Serie | `POST /v1/projects/{owner}/{repo}/series/{series_id}/reorder` |
| `project.edit` | – | Formular „Projektdaten bearbeiten“ zeigen | Vorlage `projektdaten-bearbeiten` (`render_view.py project-edit`) | – |
| `project.update` | `title`, `title_short`, `author`, `description_short`, `description`, `expected_head_sha` | Projektdaten speichern | in `ghostwriter.yml` schreiben, danach Projektübersicht | `PATCH /v1/projects/{owner}/{repo}` |
| `project.settings.open` | – | Projekteinstellungen zeigen | Vorlage `projekteinstellungen` (`render_view.py project-settings`) | – |
| `project.settings.update` | `fact_checking_default`, `typesetting` (`page_size`, `font`, `font_size`, `title_page`, `imprint`, `toc`, `toc_depth`), `updates` (`auto`), `changes` (`auto_merge`), `limits` (`ai_budget_monthly`, `actions_minutes_monthly`; `null` = entfernen), `expected_head_sha` | Einstellungen speichern | `workflow.fact_checking_default`, `typesetting`, `updates`, `changes` und `limits` in `ghostwriter.yml` schreiben, danach Projektübersicht | `PATCH …/settings` |
| `project.ai_disclosure.open` | – | Formular „KI-Angabe im Buch“ zeigen (Befehl `KI-Angabe`, Knopf in den Projekteinstellungen, #78) | Vorlage `ki-angabe` (`render_view.py ai-disclosure`) | – |
| `project.ai_disclosure.update` | `mode`, `placement`, `name_services`, `text` bzw. `use_suggestion`, `expected_head_sha` | KI-Angabe speichern | `scripts/ai_disclosure.py set`, ein Commit (`START.md`, „KI-Angabe im Buch“), danach das Formular | `PATCH …/settings` |
| `project.output.open` | – | Formular „Ausgabeoptionen“ zeigen (Befehl `Ausgabe`, Knopf in Projektübersicht und Projekteinstellungen, #68) | Vorlage `ausgabeoptionen` (`render_view.py output`) | – |
| `project.output.update` | `typesetting` (Felder wie in `docs/DATA-MODEL.md`, „Buchsatz“), `publication` (`publisher`, `isbn_print`, `isbn_ebook`, `rights`), `print`, `cover`, Texte der Rückseite (`blurb`, `author_bio`), `expected_head_sha` | Ausgabeoptionen speichern | in `ghostwriter.yml` schreiben (nur geänderte Felder), prüfen, danach das Formular | `PATCH …/settings` |
| `project.providers.open` | – | Formular „KI-Dienste“ zeigen | Vorlage `ki-dienste` (`render_view.py providers-edit`) | – |
| `project.providers.update` | `available`, `services` (je eigenem Dienst `access`, `model`, `github_connected`, `plan`, `monthly_cost`, `note`, bei `access: api` zusätzlich `api_key_secret`), `roles` (`default`, `research`, `brainstorming`, `writing`, `revision`, `fact_check`: Dienst-ID, `chat` oder leer), `queue_agent`, `search_tools`, `expected_head_sha` | KI-Dienste speichern | `ai_providers` in `ghostwriter.yml` schreiben: `available`, `services` (nur eigene Dienste; leere Felder weglassen), `provider` je Aufgabe, `research.search_tools`, `queue_processing.agent`; Modellnamen nicht ändern. Danach Projektübersicht | `PATCH …/settings` |
| `chapter.create.open` | – | Formular „Neues Kapitel anlegen“ zeigen | Vorlage `kapitel-anlegen` (`render_view.py chapter-create`) | – |
| `chapter.create` | `title`, `summary`, `goal`, `position` (Index, 0 = am Anfang), `position_label`, `expected_head_sha` | Kapitel anlegen | Kapitel anlegen, danach Kapitelansicht des neuen Kapitels | `POST …/chapters` |
| `chapter.edit.open` | `chapter_id` | Kapitel bearbeiten | Vorlage `kapitel-bearbeiten` (`render_view.py chapter-edit N`) | – |
| `chapter.update` | `chapter_id`, `title`, `subtitle`, `summary`, `goal`, `expected_head_sha` | Kapitel speichern | Titel in `structure.chapters` und Kapitel-README im selben Commit ändern, danach Kapitelansicht | `PATCH …/chapters/{chapter_id}` |
| `chapter.research.open` | `chapter_id` | Kapitelrecherche öffnen | Vorlage `kapitelrecherche` (`render_view.py chapter-research N`) | – |
| `chapter.texts.update` | `chapter_id`, `goal`, `summary`, `expected_head_sha` | Ziel und Kurzbeschreibung speichern | nur diese beiden Abschnitte der Kapitel-README ändern, danach Kapitelansicht | `PATCH …/chapters/{chapter_id}` |
| `chapter.sections.add` | `chapter_id`, `sections` (Liste mit `title`, `summary`), `expected_head_sha` | Vorgeschlagene Abschnitte anlegen | am Ende des Kapitels anlegen (`START.md`, „Kapitelrecherche“, Schritt 6), ein Commit, danach Kapitelansicht | `POST …/chapters/{chapter_id}/sections` |
| `chapter.research.start` | `chapter_id`, `task` (`goal` \| `sections` \| `summary` \| leer), `question`, `scope`, `weight_prev`, `weight_next` (0–3), `goal`, `summary`, `expected_head_sha` | Kapitelrecherche starten | Lauf ausführen und speichern (`START.md`, „Kapitelrecherche“), danach wieder das Formular mit Vorschlägen und den gesendeten Werten (`--draft`) | `POST …/chapters/{chapter_id}/research-runs` |
| `chapter.reorder.open` | – | Kapitelreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py chapter-reorder`) | – |
| `chapter.reorder` | `order` (alle Kapitel-IDs in neuer Reihenfolge), `expected_head_sha` | Kapitelreihenfolge speichern | `structure.chapters` umsortieren; IDs und Pfade bleiben; danach Projektübersicht | `POST …/chapters/reorder` |
| `section.create.open` | `chapter_id` | Neuen Abschnitt anlegen | Vorlage `abschnitt-anlegen` (`render_view.py section-create N`) | – |
| `section.create` | `chapter_id`, `title`, `goal`, `summary`, `fact_check`, `position` (Index, 0 = am Anfang), `position_label`, `expected_head_sha` | Abschnitt anlegen | Abschnittsdatei aus `templates/section.md` anlegen und in `structure.chapters` eintragen, danach Abschnittsformular | `POST …/chapters/{chapter_id}/sections` |
| `section.reorder.open` | `chapter_id` | Abschnittsreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py section-reorder N`) | – |
| `section.reorder` | `chapter_id`, `order` (alle Abschnitts-IDs des Kapitels in neuer Reihenfolge), `expected_head_sha` | Abschnittsreihenfolge speichern | `sections` des Kapitels umsortieren; IDs und Dateinamen bleiben; danach Kapitelansicht | `POST …/chapters/{chapter_id}/sections/reorder` |
| `section.update` | `section_id`, `goal`, `summary`, `fact_check`, `manuscript`, bei Büchern mit Figuren `characters` (Liste von IDs, #53), `expected_head_sha` (nie `approvals`) | Abschnitt speichern | Abschnittsdatei schreiben, danach Abschnittsformular | `PATCH …/sections/{section_id}`, `PUT …/sections/{section_id}/manuscript` |
| `run.start` | `section_id`, `task` (`research` \| `writing`), `mode` (`immediate` \| `scheduled`) | AI-Lauf starten; in v0.5 nur `immediate` | Lauf ausführen und Lauf-Datei, Ergebnis und Statuswechsel speichern (`START.md`, „KI-Lauf „Sofort““); ein Kosteneintrag nur für kostenpflichtige KI-API-Aufrufe über das Backend, nie für Chat-Arbeit | `POST …/sections/{section_id}/research-runs` bzw. Manuskript |
| `edition.create.open` | – | Formular „Neue Auflage erzeugen“ zeigen | Vorlage `auflage-erzeugen` (`render_view.py edition-create`) | – |
| `edition.proof` | – | Probedruck erstellen | Action „Probedruck“ per `workflow_dispatch` starten oder Link *Run workflow* geben; danach Link zum Lauf (Download unter *Artifacts*) | `POST /repos/{owner}/{repo}/actions/workflows/proof.yml/dispatches` |
| `edition.create` | `name`, `tag`, `date`, `formats`, `notes` | Auflage erzeugen | prüfen, Release Notes zeigen, Auflagen-Pull-Request anlegen (`START.md`, „Neue Auflage“); nach dem Merge baut die Action „Auflage veröffentlichen“ | `POST /repos/{owner}/{repo}/actions/workflows/edition.yml/dispatches` (Bau), Pull Request wie Weg A |
| `changes.merge.open` | – | Bestätigung „Änderungen übernehmen“ zeigen (Knopf im Hinweis der Projektübersicht, Textfassung `M`) | offene Änderungen aus GitHub lesen, Vorlage `aenderungen-uebernehmen` (`render_view.py changes-merge`) | `GET …/changes` |
| `changes.merge` | `pull_request`, `expected_head_sha` | Offene Änderungen übernehmen; der Klick auf „Übernehmen“ bzw. `OK` ist die ausdrückliche Bestätigung | prüfen, dass der Arbeits-Branch noch auf `expected_head_sha` steht (sonst Bestätigung neu zeigen), Pull Request mit Merge-Commit mergen, Arbeits-Branch löschen, danach Projektübersicht | `POST …/changes/merge` |
| `approval.open` | `kind` (`writing` \| `section` \| `chapter` \| `matter` \| `image`), `section_id` bzw. `chapter_id`, `revoke` (nur beim Zurücknehmen); bei Vor- und Nachspann steht die `mat-…`-ID in `section_id` (#57) | Bestätigung „Freigabe“ zeigen | Vorlage `freigabe-bestaetigen` (`render_view.py approval-<kind> N.M` bzw. `N`, für einen Teil `approval-writing\|approval-matter <teil>`, `--revoke`) | – |
| `approval.confirm` | wie `approval.open`, dazu `expected_head_sha` | Freigabe erteilen bzw. zurücknehmen; der Klick ist die ausdrückliche Bestätigung | Hindernisse erneut prüfen, dann nach `START.md`, „Freigaben“, schreiben; danach die Ausgangsansicht | `POST`/`DELETE …/sections/{section_id}/writing-approval`, `…/sections/{section_id}/approve`, `…/chapters/{chapter_id}/approve`, `…/matter/{matter_id}/writing-approval`, `…/matter/{matter_id}/approve` |
| `update.apply` | – | GhostWriter-Update einspielen | Action „GhostWriter aktualisieren“ per `workflow_dispatch` starten oder Link *Run workflow* geben (`START.md`, „Programmdateien und Updates“); nie selbst mergen | `POST /repos/{owner}/{repo}/actions/workflows/update.yml/dispatches` |
| `wizard.answer` | `step`, `answers` (je `key` der Frage: Wert, Liste von Werten bei Mehrfachauswahl, `{"other": "Text"}` für eine eigene Antwort, auch als Listeneintrag) | Antworten auf Auswahlkarten | Antworten übernehmen (`START.md`, Abschnitt 4, „Auswahlkarten“), noch nichts schreiben; mit dem nächsten Wizard-Schritt weitermachen | – |
| `wizard.skip` | `step` | Schritt überspringen | Angabe bleibt vorerst offen, nächster Wizard-Schritt | – |
| `form.cancel` | `form` und betroffene ID | Formular ohne Änderung geschlossen | nichts schreiben, Ausgangsansicht zeigen (siehe „Nach dem Formular“) | – |

Schreibende Aktionen (`….update`, `….create` außer `edition.create`, `….reorder`, `changes.merge`, `approval.confirm`) laufen nach `START.md`, „Schreiben ins Repository“: Prüfung gegen `expected_head_sha`, Commit im Arbeits-Branch, kein automatischer Merge.

Jede `….open`-Aktion beantwortet der Assistent sofort mit dem genannten Formular, ohne Rückfrage. Eine Reihenfolge wird nur gespeichert, wenn `order` genau die bisherigen IDs enthält; sonst fragt der Assistent nach.

## Nach dem Formular

Nach Speichern, Abbrechen oder „nichts geändert“ zeigt der Assistent sofort wieder die Ansicht, aus der das Formular geöffnet wurde, neu unter dem Formular. Die alte Ansicht bleibt im Verlauf stehen; der Chat kann nicht zurückblättern.

| Formular | Danach |
|---|---|
| Projektdaten bearbeiten, Projekteinstellungen, KI-Dienste, Kapitelreihenfolge, Neue Auflage, Änderungen übernehmen | Projektübersicht |
| Neues Kapitel anlegen | gespeichert: Kapitelansicht des neuen Kapitels; abgebrochen: Projektübersicht |
| Kapitel bearbeiten | aus der Kapitelansicht geöffnet: Kapitelansicht; aus der Projektübersicht (Stift je Kapitel bzw. `BN` in der Textfassung): Projektübersicht |
| Abschnittsreihenfolge | Kapitelansicht |
| Neuer Abschnitt | gespeichert: Abschnittsformular des neuen Abschnitts; abgebrochen: Kapitelansicht |
| Abschnitt bearbeiten | Abschnittsformular mit dem neuen Stand; „Zum Kapitel“ führt zurück |
| Freigabe bestätigen | Abschnittsfreigaben: Abschnittsformular; Kapitelfreigabe: Kapitelansicht; Vor- und Nachspann: der Teil |
| Teil von Vor- oder Nachspann anlegen bzw. bearbeiten | der Teil (abgebrochen: Liste „Vor- und Nachspann“) |

Ausnahme: Schlägt das Speichern fehl (✗), bleibt es beim Formular; der Assistent zeigt es mit den gesendeten Werten erneut, damit keine Eingabe verloren geht.

## Statustexte

Statuszeilen, Ladetexte und Ergebniszeilen nach `START.md`, „Statusanzeige“. Die Texte sind Muster; Nummern und Titel werden eingesetzt. Bei jeder schreibenden Aktion außer `changes.merge` steht vor dem Speichern die Zeile „→ Prüfe, ob sich die Dateien seit dem Lesen geändert haben“, und die Ergebniszeile endet mit „· noch nicht übernommen (Pull Request #NN)“.

| Aktion | Statuszeilen | Ladetext | Ergebniszeile |
|---|---|---|---|
| `view.project` | → Lese ghostwriter.yml · → Berechne Kosten | Projektübersicht wird geladen | – |
| `view.chapter` | → Lese Kapitel N · → Zähle Marker und Kosten | Kapitel N wird geladen | – |
| `view.section` | → Lese Abschnitt N.M | Abschnitt N.M wird geladen | – |
| `project.edit`, `project.settings.open`, alle `….open` | – | Formular wird vorbereitet | – |
| `changes.merge.open` | → Lese offene Änderungen (Pull Request #NN) | Änderungen werden geladen | – |
| `approval.open` | → Prüfe die Voraussetzungen für die Freigabe | Freigabe wird vorbereitet | – |
| `approval.confirm` | → Prüfe die Voraussetzungen erneut · → Prüfe, ob sich die Dateien seit dem Lesen geändert haben · → Speichere die Freigabe und den Eintrag in approvals.yml (Commit im Arbeits-Branch) | – | ✓ Abschnitt N.M freigegeben, Commit `abc1234` · noch nicht übernommen (Pull Request #NN) |
| `project.update` | → Prüfe Eingaben · → Prüfe, ob sich die Dateien seit dem Lesen geändert haben · → Speichere Projektdaten (Commit im Arbeits-Branch) · → Prüfe Validierung | – | ✓ Projektdaten gespeichert, Commit `abc1234` · noch nicht übernommen (Pull Request #NN) |
| `chapter.create` | → Lege Kapitel „Titel“ an · → Trage es in ghostwriter.yml ein · → Speichere (Commit) | – | ✓ Kapitel N „Titel“ angelegt, Commit `abc1234` |
| `section.update` | → Prüfe, ob sich die Datei seit dem Lesen geändert hat · → Speichere Abschnitt N.M (Commit im Arbeits-Branch) | – | ✓ Abschnitt N.M gespeichert, Commit `abc1234` |
| `run.start` | → Recherche bzw. Ghostwriting für N.M · → Speichere Lauf und Ergebnis (Commit im Arbeits-Branch) | – | ✓ Entwurf für N.M gespeichert, Lauf `run-003`, Commit `abc1234` |
| `chapter.update` | → Speichere Kapitel N (ghostwriter.yml und README, Commit) | – | ✓ Kapitel N gespeichert, Commit `abc1234` |
| `chapter.texts.update` | → Speichere Ziel und Kurzbeschreibung von Kapitel N (Commit) | – | ✓ Ziel und Kurzbeschreibung gespeichert, Commit `abc1234` |
| `chapter.research.start` | → Kapitelrecherche für Kapitel N · → Speichere Lauf (Commit) | – | ✓ Kapitelrecherche gespeichert, Lauf `run-001`, Commit `abc1234` |
| `chapter.sections.add` | → Lege N Abschnitte in Kapitel K an · → Speichere (Commit) | – | ✓ N Abschnitte angelegt (K.x–K.y), Commit `abc1234` |
| `chapter.reorder`, `section.reorder` | → Prüfe die neue Reihenfolge · → Speichere ghostwriter.yml (Commit) | – | ✓ Reihenfolge gespeichert, Commit `abc1234` |
| `section.create` | → Lege Abschnitt „Titel“ in Kapitel N an · → Speichere (Commit) | – | ✓ Abschnitt N.M „Titel“ angelegt, Commit `abc1234` |
| `project.providers.update` | → Prüfe, ob sich die Dateien seit dem Lesen geändert haben · → Speichere KI-Dienste (Commit im Arbeits-Branch) | – | ✓ KI-Dienste gespeichert, Commit `abc1234` · noch nicht übernommen (Pull Request #NN) |
| `project.settings.update` | → Speichere Projekteinstellungen (Commit) | – | ✓ Projekteinstellungen gespeichert, Commit `abc1234` |
| `update.apply` | → Starte GhostWriter-Update | – | ✓ Update gestartet, Lauf: <Link> · oder Link *Run workflow*, wenn der Chat Workflows nicht starten kann |
| `edition.proof` | → Starte Probedruck | – | ✓ Probedruck gestartet, Lauf: <Link> (PDF dort unter *Artifacts*, 14 Tage) |
| `edition.create` | → Lege Pull Request für Auflage N an | – | ✓ Pull Request #NN für Auflage N angelegt; Tag und Release erzeugt die Action nach dem Merge |
| `changes.merge` | → Prüfe, ob seit der Bestätigung etwas dazugekommen ist · → Übernehme N Änderungen (Merge) · → Lösche den Arbeits-Branch | – | ✓ N Änderungen übernommen, Merge-Commit `abc1234` |
| Fehler | – | – | ✗ Nicht gespeichert: Grund, etwa „Datei wurde inzwischen geändert“ |

## Weg B

Mit eigener API bleibt alles gleich, was der Benutzer sieht: dieselben Vorlagen aus `ghostwriter-ui`, dieselben Daten (die Platzhalter oben entsprechen den Feldern der API) und dieselben Nachrichten. Nur die Herkunft der Daten ändert sich; `GW.render` bekommt sie dann aus der Antwort der API statt vom Assistenten.

Freigaben gibt es nur über `approval.confirm` (`START.md`, „Freigaben“); `section.update` ändert `approvals` nie (Issue #10).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../../assets/logo-dark.svg"><img src="../../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
