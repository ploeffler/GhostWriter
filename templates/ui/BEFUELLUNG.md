# Befüllen der Chat-Vorlagen

Diese Regeln sagen dem Assistenten, wie er die Chat-Vorlagen mit Daten aus dem Buch-Repository ausgibt, wie er sie ohne Widgets als Text ausgibt und in welchem Format die Vorlagen Nachrichten in den Chat schicken. Die Vorlagen selbst liegen im öffentlichen Repository [ploeffler/ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui) (siehe `README.md` hier). `scripts/render_view.py` setzt die Regeln für Projektübersicht, Kapitelansicht und Abschnittsformular um und dient als Referenz:

```sh
python scripts/render_view.py <projektordner> project [--text] [--head-sha <commit>]
python scripts/render_view.py <projektordner> chapter 2 [--text]
python scripts/render_view.py <projektordner> section 2.4 [--text]
python scripts/render_view.py <projektordner> project-edit | project-settings | chapter-create | chapter-reorder | edition-create [--text]
python scripts/render_view.py <projektordner> project | changes-merge --changes <offene-aenderungen.json> [--head-sha <commit>] [--text]
python scripts/render_view.py <projektordner> chapter-edit 2 | section-create 2 | section-reorder 2 [--text]
python scripts/render_view.py <projektordner> providers-edit [--repo owner/name] [--branch name] [--text]
python scripts/render_view.py <projektordner> approval-writing 2.4 | approval-section 2.4 | approval-chapter 2 [--revoke] [--text]
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
| `PENDING_COUNT`, `PENDING_TEXT`, `PENDING_PR` | nur bei offenen Änderungen (Arbeits-Branch mit offenem Pull Request, siehe „Offene Änderungen“): Anzahl der Commits, „1 Änderung“ bzw. „N Änderungen“, Nummer des Pull Requests. Ohne offene Änderungen weglassen; dann entfällt der Hinweis mit dem Knopf „Änderungen übernehmen“ |
| `UPDATE_BEHIND`, `UPDATE_TEXT` | nur wenn der Buch-Branch hinter dem Hauptrepository liegt (siehe „Update-Stand“): Anzahl Commits und Text wie „3 Commits hinter ploeffler/GhostWriter:main · Version 0.3.1 verfügbar (installiert 0.3.0)“. Sonst weglassen; dann entfällt der Hinweis mit dem Knopf „Update einspielen“ |
| Block `CHAPTERS`: `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_STATUS`, `CHAPTER_COST`, `CHAPTER_COST_HINT`, `CHAPTER_ID` | je Kapitel aus `structure.chapters`, Kosten wie oben; `CHAPTER_ID` ist die stabile Kapitel-ID, ein Klick auf das Kapitel schickt `view.chapter`; ohne Kapitel entfällt der Bereich „Kapitel“ |

### `kapitelansicht.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT`, `CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE` | Projekt und Kapitel |
| `CHAPTER_SUBTITLE` | erste kursive Zeile `*…*` in der `README.md` des Kapitels; sonst leer |
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
| `GW_VERSION_TEXT` | „Installiert: GhostWriter <version>“ aus `ghostwriter-manifest.yml`, dazu „ · zuletzt aktualisiert am TT.MM.JJJJ“ aus `.ghostwriter/update.yml` (`updated_at`), falls vorhanden |
| `GW_UPDATE_HINT` | nur wenn `.ghostwriter/update.yml` `skipped_workflows` enthält: Hinweis auf das Secret `GHOSTWRITER_UPDATE_TOKEN` (`docs/UPDATES.md`); sonst leer |

## Textfassung ohne Widgets

Chats ohne Widgets (etwa ChatGPT) bekommen dieselben Inhalte als Markdown. **Dort nie HTML, `GW.render` oder Widget-Code ausgeben.** Muster erzeugt `scripts/render_view.py … --text`; jede Ansicht und jedes Formular hat eine Textfassung.

Gestaltung:

- **Überschrift** `###` mit Symbol: 📘 Projekt, 📖 Kapitel, ✏️ Abschnitt, 📝 Bearbeiten, ➕ Anlegen, ↕️ Reihenfolge, ⚙️ Einstellungen, 📚 Auflage, 🔀 Änderungen übernehmen, ✅ Freigeben, ↩️ Freigabe zurücknehmen, 🤖 KI-Dienste.
- **Status** deutsch mit Symbol: ⚪ geplant, 🔎 Recherche, 💡 Ideensammlung, 🟦 bereit zum Schreiben, ✏️ Schreiben bzw. in Arbeit, 🔁 Überarbeitung, 🔍 Faktencheck bzw. Durchsicht, 🟡 bereit zur Freigabe, ✅ freigegeben.
- **Marker** als Symbol mit Anzahl: 💬 Anekdote, 📚 Quelle, 🩺 Medizin, ⚖️ Recht; darunter klein die Legende.
- **Tabellen** für Listen und Felder; Zahlen und Kosten rechtsbündig.
- **Aktionen** am Ende nach einer Trennlinie als Kürzel in Inline-Code: Zahlen öffnen Kapitel (`2`) oder Abschnitte (`2.4`), Buchstaben lösen Aktionen aus.
- **Formulare** zeigen die aktuellen Werte als Tabelle; geantwortet wird mit `Feld: neuer Wert`, je Zeile ein Feld. `X` bricht ab.

| Ansicht | Kürzel |
|---|---|
| Projektübersicht | `1`–`N` Kapitel öffnen (📖) · `B1`–`BN` Kapitel bearbeiten (✎ in jeder Kapitelzeile, wie der Bearbeiten-Knopf der Kapitelansicht) · `N.M` zuletzt bearbeiteter Abschnitt · `M` Änderungen übernehmen (nur bei offenen Änderungen) · `D` KI-Dienste · `P` Projektdaten · `N` Neues Kapitel · `R` Kapitelreihenfolge · `A` Neue Auflage · `E` Einstellungen |
| Kapitelansicht | `N.1`–`N.M` Abschnitt öffnen · `B` Kapitel bearbeiten · `N` Neuer Abschnitt · `R` Abschnittsreihenfolge · `FK` Kapitel freigeben (nur wenn möglich) · `Ü` Übersicht |
| Abschnitt | `T` Text ändern (geänderten Text schicken) · `F` Ziel, Kurzbeschreibung, Faktencheck · `FS` Schreiben freigeben bzw. zurücknehmen · `FA` Abschnitt freigeben bzw. zurücknehmen · `RS` Recherche sofort · `GS` Ghostwriting sofort · `N.M` vorheriger/nächster Abschnitt · `K` Zum Kapitel |
| Formulare | `Feld: Wert` je Zeile · Reihenfolge als Nummernliste · Auflage: `OK` übernimmt den Vorschlag · Änderungen übernehmen: `OK` übernimmt · Freigabe: `OK` bestätigt · KI-Dienste: `+ id`, `- id`, `Aufgabe: id` · `X` bricht ab |

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
| `project.update` | `title`, `title_short`, `author`, `description_short`, `description`, `expected_head_sha` | Projektdaten speichern | in `ghostwriter.yml` schreiben, danach Projektübersicht | `PATCH /v1/projects/{owner}/{repo}` |
| `project.settings.open` | – | Projekteinstellungen zeigen | Vorlage `projekteinstellungen` (`render_view.py project-settings`) | – |
| `project.settings.update` | `fact_checking_default`, `typesetting` (`page_size`, `font`, `font_size`, `title_page`, `imprint`, `toc`, `toc_depth`), `updates` (`auto`), `expected_head_sha` | Einstellungen speichern | `workflow.fact_checking_default`, `typesetting` und `updates` in `ghostwriter.yml` schreiben, danach Projektübersicht | `PATCH …/settings` |
| `project.providers.open` | – | Formular „KI-Dienste“ zeigen | Vorlage `ki-dienste` (`render_view.py providers-edit`) | – |
| `project.providers.update` | `available`, `services` (je eigenem Dienst `access`, `model`, `github_connected`, `plan`, `monthly_cost`, `note`, bei `access: api` zusätzlich `api_key_secret`), `roles` (`default`, `research`, `brainstorming`, `writing`, `revision`, `fact_check`: Dienst-ID, `chat` oder leer), `queue_agent`, `search_tools`, `expected_head_sha` | KI-Dienste speichern | `ai_providers` in `ghostwriter.yml` schreiben: `available`, `services` (nur eigene Dienste; leere Felder weglassen), `provider` je Aufgabe, `research.search_tools`, `queue_processing.agent`; Modellnamen nicht ändern. Danach Projektübersicht | `PATCH …/settings` |
| `chapter.create.open` | – | Formular „Neues Kapitel anlegen“ zeigen | Vorlage `kapitel-anlegen` (`render_view.py chapter-create`) | – |
| `chapter.create` | `title`, `summary`, `goal`, `position` (Index, 0 = am Anfang), `position_label`, `expected_head_sha` | Kapitel anlegen | Kapitel anlegen, danach Kapitelansicht des neuen Kapitels | `POST …/chapters` |
| `chapter.edit.open` | `chapter_id` | Kapitel bearbeiten | Vorlage `kapitel-bearbeiten` (`render_view.py chapter-edit N`) | – |
| `chapter.update` | `chapter_id`, `title`, `subtitle`, `summary`, `goal`, `expected_head_sha` | Kapitel speichern | Titel in `structure.chapters` und Kapitel-README im selben Commit ändern, danach Kapitelansicht | `PATCH …/chapters/{chapter_id}` |
| `chapter.reorder.open` | – | Kapitelreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py chapter-reorder`) | – |
| `chapter.reorder` | `order` (alle Kapitel-IDs in neuer Reihenfolge), `expected_head_sha` | Kapitelreihenfolge speichern | `structure.chapters` umsortieren; IDs und Pfade bleiben; danach Projektübersicht | `POST …/chapters/reorder` |
| `section.create.open` | `chapter_id` | Neuen Abschnitt anlegen | Vorlage `abschnitt-anlegen` (`render_view.py section-create N`) | – |
| `section.create` | `chapter_id`, `title`, `goal`, `summary`, `fact_check`, `position` (Index, 0 = am Anfang), `position_label`, `expected_head_sha` | Abschnitt anlegen | Abschnittsdatei aus `templates/section.md` anlegen und in `structure.chapters` eintragen, danach Abschnittsformular | `POST …/chapters/{chapter_id}/sections` |
| `section.reorder.open` | `chapter_id` | Abschnittsreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py section-reorder N`) | – |
| `section.reorder` | `chapter_id`, `order` (alle Abschnitts-IDs des Kapitels in neuer Reihenfolge), `expected_head_sha` | Abschnittsreihenfolge speichern | `sections` des Kapitels umsortieren; IDs und Dateinamen bleiben; danach Kapitelansicht | `POST …/chapters/{chapter_id}/sections/reorder` |
| `section.update` | `section_id`, `goal`, `summary`, `fact_check`, `manuscript`, `expected_head_sha` (nie `approvals`) | Abschnitt speichern | Abschnittsdatei schreiben, danach Abschnittsformular | `PATCH …/sections/{section_id}`, `PUT …/sections/{section_id}/manuscript` |
| `run.start` | `section_id`, `task` (`research` \| `writing`), `mode` (`immediate` \| `scheduled`) | AI-Lauf starten; in v0.5 nur `immediate` | Lauf ausführen und Lauf-Datei, Ergebnis und Statuswechsel speichern (`START.md`, „KI-Lauf „Sofort““); ein Kosteneintrag nur für kostenpflichtige KI-API-Aufrufe über das Backend, nie für Chat-Arbeit | `POST …/sections/{section_id}/research-runs` bzw. Manuskript |
| `edition.create.open` | – | Formular „Neue Auflage erzeugen“ zeigen | Vorlage `auflage-erzeugen` (`render_view.py edition-create`) | – |
| `edition.create` | `name`, `tag`, `date`, `formats`, `notes` | Auflage erzeugen | Pull Request für die Auflage anlegen | noch offen |
| `changes.merge.open` | – | Bestätigung „Änderungen übernehmen“ zeigen (Knopf im Hinweis der Projektübersicht, Textfassung `M`) | offene Änderungen aus GitHub lesen, Vorlage `aenderungen-uebernehmen` (`render_view.py changes-merge`) | `GET …/changes` |
| `changes.merge` | `pull_request`, `expected_head_sha` | Offene Änderungen übernehmen; der Klick auf „Übernehmen“ bzw. `OK` ist die ausdrückliche Bestätigung | prüfen, dass der Arbeits-Branch noch auf `expected_head_sha` steht (sonst Bestätigung neu zeigen), Pull Request mit Merge-Commit mergen, Arbeits-Branch löschen, danach Projektübersicht | `POST …/changes/merge` |
| `approval.open` | `kind` (`writing` \| `section` \| `chapter`), `section_id` bzw. `chapter_id`, `revoke` (nur beim Zurücknehmen) | Bestätigung „Freigabe“ zeigen | Vorlage `freigabe-bestaetigen` (`render_view.py approval-<kind> N.M` bzw. `N`, `--revoke`) | – |
| `approval.confirm` | wie `approval.open`, dazu `expected_head_sha` | Freigabe erteilen bzw. zurücknehmen; der Klick ist die ausdrückliche Bestätigung | Hindernisse erneut prüfen, dann nach `START.md`, „Freigaben“, schreiben; danach die Ausgangsansicht | `POST`/`DELETE …/sections/{section_id}/writing-approval`, `…/sections/{section_id}/approve`, `…/chapters/{chapter_id}/approve` |
| `update.apply` | – | GhostWriter-Update einspielen | Action „GhostWriter aktualisieren“ per `workflow_dispatch` starten oder Link *Run workflow* geben (`START.md`, „Programmdateien und Updates“); nie selbst mergen | `POST /repos/{owner}/{repo}/actions/workflows/update.yml/dispatches` |
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
| Freigabe bestätigen | Abschnittsfreigaben: Abschnittsformular; Kapitelfreigabe: Kapitelansicht |

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
| `chapter.reorder`, `section.reorder` | → Prüfe die neue Reihenfolge · → Speichere ghostwriter.yml (Commit) | – | ✓ Reihenfolge gespeichert, Commit `abc1234` |
| `section.create` | → Lege Abschnitt „Titel“ in Kapitel N an · → Speichere (Commit) | – | ✓ Abschnitt N.M „Titel“ angelegt, Commit `abc1234` |
| `project.providers.update` | → Prüfe, ob sich die Dateien seit dem Lesen geändert haben · → Speichere KI-Dienste (Commit im Arbeits-Branch) | – | ✓ KI-Dienste gespeichert, Commit `abc1234` · noch nicht übernommen (Pull Request #NN) |
| `project.settings.update` | → Speichere Projekteinstellungen (Commit) | – | ✓ Projekteinstellungen gespeichert, Commit `abc1234` |
| `update.apply` | → Starte GhostWriter-Update | – | ✓ Update gestartet, Lauf: <Link> · oder Link *Run workflow*, wenn der Chat Workflows nicht starten kann |
| `edition.create` | → Lege Pull Request für Auflage N an | – | ✓ Pull Request #NN für Auflage N angelegt; Tag und Release erzeugt die Action nach dem Merge |
| `changes.merge` | → Prüfe, ob seit der Bestätigung etwas dazugekommen ist · → Übernehme N Änderungen (Merge) · → Lösche den Arbeits-Branch | – | ✓ N Änderungen übernommen, Merge-Commit `abc1234` |
| Fehler | – | – | ✗ Nicht gespeichert: Grund, etwa „Datei wurde inzwischen geändert“ |

## Weg B

Mit eigener API bleibt alles gleich, was der Benutzer sieht: dieselben Vorlagen aus `ghostwriter-ui`, dieselben Daten (die Platzhalter oben entsprechen den Feldern der API) und dieselben Nachrichten. Nur die Herkunft der Daten ändert sich; `GW.render` bekommt sie dann aus der Antwort der API statt vom Assistenten.

Freigaben gibt es nur über `approval.confirm` (`START.md`, „Freigaben“); `section.update` ändert `approvals` nie (Issue #10).
