# Befüllen der Chat-Vorlagen

Diese Regeln sagen dem Assistenten, wie er die Chat-Vorlagen mit Daten aus dem Buch-Repository ausgibt, wie er sie ohne Widgets als Text ausgibt und in welchem Format die Vorlagen Nachrichten in den Chat schicken. Die Vorlagen selbst liegen im öffentlichen Repository [ploeffler/ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui) (siehe `README.md` hier). `scripts/render_view.py` setzt die Regeln für Projektübersicht, Kapitelansicht und Abschnittsformular um und dient als Referenz:

```sh
python scripts/render_view.py <projektordner> project [--text] [--repo owner/name] [--branch name]
python scripts/render_view.py <projektordner> chapter 2 [--text]
python scripts/render_view.py <projektordner> section 2.4 [--text]
python scripts/render_view.py <projektordner> project-edit | project-settings | chapter-create | chapter-reorder | edition-create [--text]
python scripts/render_view.py <projektordner> chapter-edit 2 | section-create 2 | section-reorder 2 [--text]
```

## Ausgabe im Chat

Der Assistent schreibt keine fertige Ansicht, sondern nur eine Ladezeile und die Daten. Den Darstellungscode lädt der Chat von jsDelivr:

```html
<div id="gw"></div>
<script src="https://cdn.jsdelivr.net/gh/ploeffler/ghostwriter-ui@<commit>/dist/gw.js"></script>
<script>GW.render("<vorlage>", { "PLATZHALTER": "Wert", "BLOCK": [ { … }, … ] })</script>
```

- `<commit>` ist der feste Commit aus `templates/ui/ghostwriter-ui.yml`, nie `main`. So ändert sich keine Ansicht unbemerkt.
- `<vorlage>` ist der Dateiname der Vorlage ohne `.html`, etwa `projektuebersicht`.
- Die Daten sind ein JSON-Objekt: Platzhalter als Schlüssel ohne Klammern, Wiederholblöcke als Arrays von Objekten. Welche Platzhalter es gibt, steht unten.
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

## Textfassung ohne Widgets

Chats ohne Widgets (etwa ChatGPT) bekommen dieselben Inhalte als Markdown. **Dort nie HTML, `GW.render` oder Widget-Code ausgeben.** Muster erzeugt `scripts/render_view.py … --text`; jede Ansicht und jedes Formular hat eine Textfassung.

Gestaltung:

- **Überschrift** `###` mit Symbol: 📘 Projekt, 📖 Kapitel, ✏️ Abschnitt, 📝 Bearbeiten, ➕ Anlegen, ↕️ Reihenfolge, ⚙️ Einstellungen, 📚 Auflage.
- **Status** deutsch mit Symbol: ⚪ geplant, 🔎 Recherche, 💡 Ideensammlung, 🟦 bereit zum Schreiben, ✏️ Schreiben bzw. in Arbeit, 🔁 Überarbeitung, 🔍 Faktencheck bzw. Durchsicht, 🟡 bereit zur Freigabe, ✅ freigegeben.
- **Marker** als Symbol mit Anzahl: 💬 Anekdote, 📚 Quelle, 🩺 Medizin, ⚖️ Recht; darunter klein die Legende.
- **Tabellen** für Listen und Felder; Zahlen und Kosten rechtsbündig.
- **Aktionen** am Ende nach einer Trennlinie als Kürzel in Inline-Code: Zahlen öffnen Kapitel (`2`) oder Abschnitte (`2.4`), Buchstaben lösen Aktionen aus.
- **Formulare** zeigen die aktuellen Werte als Tabelle; geantwortet wird mit `Feld: neuer Wert`, je Zeile ein Feld. `X` bricht ab.

| Ansicht | Kürzel |
|---|---|
| Projektübersicht | `1`–`N` Kapitel öffnen · `N.M` zuletzt bearbeiteter Abschnitt · `P` Projektdaten · `N` Neues Kapitel · `R` Kapitelreihenfolge · `A` Neue Auflage · `E` Einstellungen |
| Kapitelansicht | `N.1`–`N.M` Abschnitt öffnen · `B` Kapitel bearbeiten · `N` Neuer Abschnitt · `R` Abschnittsreihenfolge · `Ü` Übersicht |
| Abschnitt | `T` Text ändern (geänderten Text schicken) · `F` Ziel, Kurzbeschreibung, Faktencheck, Freigaben · `RS` Recherche sofort · `GS` Ghostwriting sofort · `N.M` vorheriger/nächster Abschnitt · `K` Zum Kapitel |
| Formulare | `Feld: Wert` je Zeile · Reihenfolge als Nummernliste · Auflage: `OK` übernimmt den Vorschlag · `X` bricht ab |

Ein Kürzel entspricht dem Klick auf den gleichnamigen Knopf; es gelten dieselbe Aktion, dieselben Statuszeilen und dieselbe Ausgangsansicht danach.

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
| `project.edit` | – | Formular „Projektdaten bearbeiten“ zeigen | Vorlage `projektdaten-bearbeiten` (`render_view.py project-edit`) | – |
| `project.update` | `title`, `title_short`, `author`, `description_short`, `description` | Projektdaten speichern | in `ghostwriter.yml` schreiben, danach Projektübersicht | noch offen |
| `project.settings.open` | – | Projekteinstellungen zeigen | Vorlage `projekteinstellungen` (`render_view.py project-settings`) | – |
| `project.settings.update` | `fact_checking_default`, `typesetting` (`page_size`, `font`, `font_size`, `title_page`, `imprint`, `toc`, `toc_depth`) | Einstellungen speichern | `workflow.fact_checking_default` und `typesetting` in `ghostwriter.yml` schreiben, danach Projektübersicht | noch offen |
| `chapter.create.open` | – | Formular „Neues Kapitel anlegen“ zeigen | Vorlage `kapitel-anlegen` (`render_view.py chapter-create`) | – |
| `chapter.create` | `title`, `summary`, `goal`, `position` (Index, 0 = am Anfang), `position_label` | Kapitel anlegen | Kapitel anlegen, danach Kapitelansicht des neuen Kapitels | `POST …/chapters` |
| `chapter.edit.open` | `chapter_id` | Kapitel bearbeiten | Vorlage `kapitel-bearbeiten` (`render_view.py chapter-edit N`) | – |
| `chapter.update` | `chapter_id`, `title`, `subtitle`, `summary`, `goal` | Kapitel speichern | Titel in `structure.chapters` und Kapitel-README im selben Commit ändern, danach Kapitelansicht | `PATCH …/chapters/{chapter_id}` |
| `chapter.reorder.open` | – | Kapitelreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py chapter-reorder`) | – |
| `chapter.reorder` | `order` (alle Kapitel-IDs in neuer Reihenfolge) | Kapitelreihenfolge speichern | `structure.chapters` umsortieren; IDs und Pfade bleiben; danach Projektübersicht | noch offen |
| `section.create.open` | `chapter_id` | Neuen Abschnitt anlegen | Vorlage `abschnitt-anlegen` (`render_view.py section-create N`) | – |
| `section.create` | `chapter_id`, `title`, `goal`, `summary`, `fact_check`, `position` (Index, 0 = am Anfang), `position_label` | Abschnitt anlegen | Abschnittsdatei aus `templates/section.md` anlegen und in `structure.chapters` eintragen, danach Abschnittsformular | `POST …/chapters/{chapter_id}/sections` |
| `section.reorder.open` | `chapter_id` | Abschnittsreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py section-reorder N`) | – |
| `section.reorder` | `chapter_id`, `order` (alle Abschnitts-IDs des Kapitels in neuer Reihenfolge) | Abschnittsreihenfolge speichern | `sections` des Kapitels umsortieren; IDs und Dateinamen bleiben; danach Kapitelansicht | `POST …/sections/{section_id}/move` je verschobenem Abschnitt |
| `section.update` | `section_id`, `goal`, `summary`, `fact_check`, `approvals`, `manuscript` | Abschnitt speichern | Abschnittsdatei schreiben, danach Abschnittsformular | `PATCH …/sections/{section_id}`, `PUT …/sections/{section_id}/manuscript` |
| `run.start` | `section_id`, `task` (`research` \| `writing`), `mode` (`immediate` \| `scheduled`) | AI-Lauf starten; in v0.5 nur `immediate` | Lauf ausführen, Ergebnis und Kosten speichern | `POST …/sections/{section_id}/research-runs` bzw. Manuskript |
| `edition.create.open` | – | Formular „Neue Auflage erzeugen“ zeigen | Vorlage `auflage-erzeugen` (`render_view.py edition-create`) | – |
| `edition.create` | `name`, `tag`, `date`, `formats`, `notes` | Auflage erzeugen | Pull Request für die Auflage anlegen | noch offen |
| `form.cancel` | `form` und betroffene ID | Formular ohne Änderung geschlossen | nichts schreiben, Ausgangsansicht zeigen (siehe „Nach dem Formular“) | – |

Jede `….open`-Aktion beantwortet der Assistent sofort mit dem genannten Formular, ohne Rückfrage. Eine Reihenfolge wird nur gespeichert, wenn `order` genau die bisherigen IDs enthält; sonst fragt der Assistent nach.

## Nach dem Formular

Nach Speichern, Abbrechen oder „nichts geändert“ zeigt der Assistent sofort wieder die Ansicht, aus der das Formular geöffnet wurde, neu unter dem Formular. Die alte Ansicht bleibt im Verlauf stehen; der Chat kann nicht zurückblättern.

| Formular | Danach |
|---|---|
| Projektdaten bearbeiten, Projekteinstellungen, Kapitelreihenfolge, Neue Auflage | Projektübersicht |
| Neues Kapitel anlegen | gespeichert: Kapitelansicht des neuen Kapitels; abgebrochen: Projektübersicht |
| Kapitel bearbeiten, Abschnittsreihenfolge | Kapitelansicht |
| Neuer Abschnitt | gespeichert: Abschnittsformular des neuen Abschnitts; abgebrochen: Kapitelansicht |
| Abschnitt bearbeiten | Abschnittsformular mit dem neuen Stand; „Zum Kapitel“ führt zurück |

Ausnahme: Schlägt das Speichern fehl (✗), bleibt es beim Formular; der Assistent zeigt es mit den gesendeten Werten erneut, damit keine Eingabe verloren geht.

## Statustexte

Statuszeilen, Ladetexte und Ergebniszeilen nach `START.md`, „Statusanzeige“. Die Texte sind Muster; Nummern und Titel werden eingesetzt.

| Aktion | Statuszeilen | Ladetext | Ergebniszeile |
|---|---|---|---|
| `view.project` | → Lese ghostwriter.yml · → Berechne Kosten | Projektübersicht wird geladen | – |
| `view.chapter` | → Lese Kapitel N · → Zähle Marker und Kosten | Kapitel N wird geladen | – |
| `view.section` | → Lese Abschnitt N.M | Abschnitt N.M wird geladen | – |
| `project.edit`, `project.settings.open`, alle `….open` | – | Formular wird vorbereitet | – |
| `project.update` | → Prüfe Eingaben · → Speichere Projektdaten (Commit) · → Prüfe Validierung | – | ✓ Projektdaten gespeichert, Commit `abc1234` |
| `chapter.create` | → Lege Kapitel „Titel“ an · → Trage es in ghostwriter.yml ein · → Speichere (Commit) | – | ✓ Kapitel N „Titel“ angelegt, Commit `abc1234` |
| `section.update` | → Prüfe, ob sich die Datei geändert hat · → Speichere Abschnitt N.M (Commit) | – | ✓ Abschnitt N.M gespeichert, Commit `abc1234` |
| `run.start` | → Recherche bzw. Ghostwriting für N.M · → Erfasse Kosten · → Speichere Ergebnis (Commit) | – | ✓ Entwurf für N.M gespeichert, Kosten ≈ 0,12 €, Commit `abc1234` |
| `chapter.update` | → Speichere Kapitel N (ghostwriter.yml und README, Commit) | – | ✓ Kapitel N gespeichert, Commit `abc1234` |
| `chapter.reorder`, `section.reorder` | → Prüfe die neue Reihenfolge · → Speichere ghostwriter.yml (Commit) | – | ✓ Reihenfolge gespeichert, Commit `abc1234` |
| `section.create` | → Lege Abschnitt „Titel“ in Kapitel N an · → Speichere (Commit) | – | ✓ Abschnitt N.M „Titel“ angelegt, Commit `abc1234` |
| `project.settings.update` | → Speichere Projekteinstellungen (Commit) | – | ✓ Projekteinstellungen gespeichert, Commit `abc1234` |
| `edition.create` | → Lege Pull Request für Auflage N an | – | ✓ Pull Request #NN für Auflage N angelegt; Tag und Release erzeugt die Action nach dem Merge |
| Fehler | – | – | ✗ Nicht gespeichert: Grund, etwa „Datei wurde inzwischen geändert“ |

## Weg B

Mit eigener API bleibt alles gleich, was der Benutzer sieht: dieselben Vorlagen aus `ghostwriter-ui`, dieselben Daten (die Platzhalter oben entsprechen den Feldern der API) und dieselben Nachrichten. Nur die Herkunft der Daten ändert sich; `GW.render` bekommt sie dann aus der Antwort der API statt vom Assistenten.

Eine Freigabe über `section.update` mit `approvals.section: true` ersetzt nicht die ausdrückliche Bestätigung des Benutzers (Issue #10).
