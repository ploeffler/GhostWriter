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
python scripts/render_view.py <projektordner> library --library library.json [--repo owner/name] [--text]
python scripts/render_view.py <projektordner> data --library library.json [--github github.json] [--repo owner/name] [--text]
python scripts/render_view.py <projektordner> approval-writing 2.4 | approval-section 2.4 | approval-chapter 2 [--revoke] [--text]
```

## Darstellungsmodus (verbindlich)

Die Bediensprache wird zuerst nach `START.md` bestimmt. Bei Englisch verwende eine englische Textfassung oder tatsächlich unterstützte native Chat-Elemente; Englisch bleibt standardmäßig nativ; die grafischen Vorlagen können mit ausdrücklich gewähltem `--ui-ref` geprüft werden. Buchinhalte und technische Kennungen unverändert lassen. Bei Deutsch gelten die folgenden Modi:

- **Widget:** nur bei Anbietern, deren Chat-Oberfläche GhostWriter-Widgets darstellt (`chat_widgets: true` in `providers.yml`, derzeit Claude). Der Modus wird vor der **ersten** Ansicht festgelegt, also auch vor dem Bücherregal beim Wiedereinstieg in eine Bibliothek (`START.md`, Abschnitt 0, #135). Dann ist jede Ansicht ein Widget – Projektübersicht, Bücherregal, Daten, Formulare, Bestätigungen, Auswahlkarten (Ausgabe unten). Eine Startseite, fehlende Daten (etwa ohne `library.json` oder `--github`) oder eine kurze Antwort sind kein Grund für Text.
- **Markdown / native Ausgabe:** bei ChatGPT (OpenAI) und Gemini (Google) gemäß der gemeinsamen übersichtlichen Ansicht unten; **Nur Text** bei ausdrücklich gewählter Textdarstellung und weiteren Anbietern (etwa Copilot) und im Zweifel; erscheint ein Widget nicht, ab dann ebenfalls. Dann jede Ansicht als Textfassung (`render_view.py … --text`, siehe „Textfassung ohne Widgets“). **Nie HTML, `GW.render` oder Widget-Code ausgeben**, auch nicht als Codeblock.

Nie beide Fassungen derselben Ansicht und nie den Modus von Ansicht zu Ansicht wechseln. Der Benutzer kann umschalten: `Nur Text` stellt auf Text um; `Widgets` stellt bei Deutsch und einem Anbieter mit `chat_widgets: true` zurück. Bei Englisch standardmäßig bei Text bzw. unterstützten nativen Elementen bleiben. Die übersetzte grafische Vorschau nur ausdrücklich und in einem tatsächlich widgetfähigen Client verwenden.

### Fähigkeiten der Umgebung (#662, UI 0.80.0)

Eine Umgebung, die nicht alle Aktionen ausführt (Claude-Web-App, später die eigene App), meldet das der Laufzeit mit `GW.capabilities({<aktion>: {state: "chat"|"spaeter", reason: {de, en}}}, <sprache>)`. Knöpfe mit `data-a` bzw. `data-gw-send` dieser Aktionen sind dann schon vor dem Klick ausgegraut (Grund als `title`). Der Chat ruft das nicht auf; dort bleibt alles wie bisher. Die Liste der Claude-Web-App steht in `apps/claude/aktionen.json`.

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
- **Daten unverändert übergeben (#360):** Die Ausgabe von `render_view.py` nie von Hand kürzen oder umbauen; sie enthält nur Felder, die die Vorlage liest. Ist sie zu groß für den Chat, das melden (als Fehler im Hauptrepository) statt Felder wegzulassen – sonst fehlen etwa Prüf-Tags oder Kosten.
- **Kompakte Prüf-Listen (#674, ab UI 0.74.0):** `…_CHECKS_JSON`, `CHECKS_JSON` und `CHECKS_HISTORY_JSON` sind kein JSON-Text mehr, sondern echtes JSON im Payload: `{"k": [Schlüssel], "r": [[Werte], …], "p": [Berichtspfade]}` (`checks.as_payload`). Schlüssel: `CK_SHORT`, `CK_LABEL`, `CK_RESULT`, `CK_STATE`, `CK_WHEN`, `CK_PARTIAL`, `CK_REPORT` (Index in `p`, jeder Pfad einmal), in der erweiterten Darstellung `CK_ID`, `CK_NOTE`, in Abschnitt und Kapitel `CK_PILL`. `CK_TAG`, `CK_TEXT` und `CK_MARK` sendet `render_view.py` nicht mehr; `gw.js` setzt sie aus den übrigen Feldern mit den Sprachtexten zusammen (gleiche Texte wie `checks.localize`). Keine Prüfungen: Feld fehlt. Ein nativer Renderer liest die Liste mit `tests/widget_helpers.check_list` als Vorbild.
- **Scheiben von Bücherregal und Kapitelansicht (#674, ab UI 0.78.0):** Wie bei der Projektübersicht: `render_view.py . library --scheibe liste` nennt `kopf`, `buch:1` … `buch:N` (eine Buchkarte mit ihren Auflagen) und, falls es Serien ohne Bände gibt, `ende`; `render_view.py . chapter <N> --scheibe liste` nennt `kopf`, `abschnitt:1` … `abschnitt:N` und `ende` (Hinweis zum Zusammenführen; die Legende der Prüf-Tags steht in der letzten Abschnittsscheibe). Nur im Widget-Modus; jede Scheibe in einem eigenen Widget-Aufruf, sobald sie vorliegt.
- **Scheiben der Projektübersicht (#674, ab UI 0.75.0):** `render_view.py . project --scheibe liste` nennt die Scheiben (`kopf`, `kapitel:1` … `kapitel:N`, `ende`); `--scheibe <name>` gibt genau diese Scheibe als eigenes kleines Widget aus (nur im Widget-Modus). Der Assistent gibt die Scheiben nacheinander aus, jede in einem eigenen Widget-Aufruf, sobald sie vorliegt: zuerst `kopf` (Titel, Symbolleiste, Hinweise, Handlungsbedarf, Vorspann), dann je Kapitel eine, zuletzt `ende` (Nachspann, Nachweis). Die Vorlage (`SLICE`) lässt bei Kapitel- und Endscheiben Kopf und Rahmen weg, damit alles wie eine Spalte wirkt; die Legende der Prüf-Tags steht in der letzten Kapitelscheibe. Ohne `--scheibe` kommt die Ansicht wie bisher in einem Stück. Der Abstand zwischen zwei Widgets ist Sache des Clients und nur durch Sichtprüfung zu beurteilen.
- **Kompakte Daten (#674, ab UI 0.72.0):** `render_view.py` schickt die Daten mit `"_PACK":1`. Leere Felder (`""`, `[]`, `null`) der obersten Ebene fehlen dann; `gw.js` behandelt jeden Platzhalter der Vorlage und ihrer Sprachtexte als leer. Wiederholblöcke kommen als `{"k":[Feldnamen],"r":[[Werte],…]}`, wenn das kürzer ist und alle Zeilen dieselben Felder haben; fehlende Werte am Zeilenende sind leer. Das spart bei Übersichten 40–50 % der Zeichen, die der Assistent ausgeben muss, und die Ansicht erscheint früher. Auch diese Form unverändert übergeben (#360). Wer die Daten selbst liest, klappt sie mit `render_view.unpack_payload` bzw. `GW.unpack` aus; die vollständigen Rohdaten stehen weiter in `RenderedWidget.data`.
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
| Kosten-Tooltip | Grundtext (z. B. „Summe der Abschnittskosten“), bei Schätzungen ergänzt um „, enthält geschätzte Kosten“; ohne Betrag „Keine KI-API-Kosten erfasst (Arbeit im Chat über ein Abo kostet nichts zusätzlich)“. Gibt es Kosten nur in `costs/project.yml` (z. B. Medienaufträge, #754), steht bei Kapitel und Abschnitt ohne eigenen Betrag `– (nur Buch)` (`CHAPTER_COST`/`SECTION_COST`; in der Kapitelliste der Projektübersicht nur der Tooltip) und der Tooltip „Keine Kosten für diesen Teil erfasst: KI-API-Kosten (z. B. Medienaufträge) sind nur fürs ganze Buch erfasst, siehe Projektübersicht“ (Englisch: `– (book only)`) |
| Marker | Vorkommen von `[PLATZHALTER-ANEKDOTE`, `[QUELLE PRÜFEN`, `[MEDIZIN PRÜFEN`, `[RECHT PRÜFEN` im Manuskript (Teil unter `## Manuskript`); der Hinweis nach dem Doppelpunkt bis `]` ist `MARKER_TEXT` |
| Marker-Text | `keine offenen Marker`, `1 offener Marker`, `N offene Marker` |
| Anzahl Abschnitte | `1 Abschnitt`, `N Abschnitte` |
| Abgeschlossen | `<Anzahl Abschnitte mit Status approved> von <Anzahl Abschnitte>` |
| Gelesener Stand (`HEAD_SHA`) | vollständiger Commit-SHA des Stands, aus dem gelesen wurde: Arbeits-Branch, wenn es offene Änderungen gibt, sonst Buch-Branch (`START.md`, „Schreiben ins Repository“). Jede Vorlage bekommt ihn; `gw.js` hängt ihn an jede schreibende Aktion als `expected_head_sha` an: Endung `.update`, `.create` (außer `edition.create`) und `.reorder` sowie die Liste `GW.writes` (u. a. `approval.confirm`, `changes.merge`, `chapter.sections.add`, `chapter.research.start`, `series.volume.*`, `series.omnibus.approve`/`revoke`/`publish`, `import.apply`/`edit`/`outline.apply`, `analysis.apply`, `character.suggest.apply`, `image.place`; UI 0.61.1, #179). Reine Aufträge wie `run.start` und `edition.*` tragen ihn nicht |
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
| `PREVIEW_TEXT`, `PREVIEW_URL` | nicht in der Datei: aus den Tags `<kurztitel>-vorab-N` (wie unten) |
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

`date` darf unverändert aus GitHub kommen (UTC mit `Z`, z. B. `2026-11-10T16:51:47Z`) oder einen Offset tragen. `render_view.py` rechnet die Uhrzeit in die Ortszeit um (#252): Kennt der Assistent die Zeitzone des Benutzers, übergibt er sie mit `--timezone <IANA-Name>` (z. B. `--timezone Europe/Vienna`). Ohne Angabe gilt bei Deutsch `Europe/Vienna` (MEZ/MESZ), sonst UTC; Uhrzeiten in UTC sind dann mit „UTC“ gekennzeichnet. Zeitpunkte ohne Zeitzone erscheinen wie angegeben.

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
| `CHRONOLOGY_COUNT`, `CHRONOLOGY_HINTS`, `CHRONOLOGY_TEXT` | Chronologie (#354, `story/chronology.yml`): Zahl der Einträge, Zahl der Hinweise ohne „ohne Datum“ (`scripts/chronology.py`), „Chronologie: N Einträge, M Hinweise“; ohne Chronologie weglassen. Ab UI 0.56.0 als Zeile unter dem Kopf, dazu der Knopf „Zeitleiste“ (`view.timeline`) |
| `PREVIEW_TEXT`, `PREVIEW_URL` | letzte Vorabfassung (#352): „Vorabfassung N vom TT.MM.JJJJ“ (Datum des Tags bzw. des markierten Stands) und Link `https://github.com/<repo>/releases/tag/<tag>`; aus den Tags `<kurztitel>-vorab-N` des Klons (Funktion `previews` in `scripts/render_view.py`). Ohne Vorabfassung bzw. ohne geholte Tags weglassen; dann entfällt die Anzeige. Ab UI 0.54.0 neben „Buchprojekt · Auflage …“, in der Textfassung in der Zeile mit der Auflage |
| `CREDIT_TEXT`, `CREDIT_URL` | Hinweis und Link aus `templates/branding.yml` (`credit`), klein unter der Karte bzw. am Ende der Textfassung; nie im Buch |
| `PENDING_COUNT`, `PENDING_TEXT`, `PENDING_PR` | nur bei offenen Änderungen (Arbeits-Branch mit offenem Pull Request, siehe „Offene Änderungen“): Anzahl der Commits, „1 Änderung“ bzw. „N Änderungen“, Nummer des Pull Requests. Ohne offene Änderungen weglassen; dann entfällt der Hinweis mit dem Knopf „Buchänderungen übernehmen“ |
| `IMPORT_TEXT` | Import (#124, `import_book.py status`): ab sieben Tage vor Ablauf einer früheren Aufbewahrungsfrist bzw. danach „Das Original des Imports (<datei>) bleibt erhalten, auch nach der früheren Frist (bis TT.MM.JJJJ bzw. „bis zur ersten Auflage“). Entfernt wird es nur auf ausdrücklichen Auftrag.“ (D21: Fristen löschen nichts); sonst weglassen |
| Block `ANALYSES`: `A_KIND`, `A_TEXT`, `A_RUN`, `A_ICON` | je Art mit offenem Hintergrundlauf (#123, #124, `analyze.latest_all`): Art (`characters`, `summaries`, …), „Figurenvorschläge vom TT.MM.JJJJ liegen bereit (N)“ bzw. „Kurzbeschreibungen und Ziele vom …“, „Stilprofil vom …“, „Schauplätze vom …“, „Zeitleiste vom …“, „Mögliche Widersprüche vom …“, „Sprachliche Hinweise vom …“, Pfad der Vorschlagsdatei (`analysis/<art>/run-NNN.json`), Tabler-Symbol der Art; ohne offenen Lauf weglassen. Der Knopf „Ansehen“ schickt `analysis.open` |
| `LIMIT_STATE`, `LIMIT_TEXT` | Limitwarnung (#62): `warn` (weniger als 20 % übrig) bzw. `pause` (weniger als 10 %, bei Actions-Minuten auch unter 100 Restminuten, Vorwarnung unter 300, #277; die Update-Automatik ist ausgesetzt) mit Text wie „Automatik pausiert: KI-Budget 8 % übrig (9,20 von 10,00 € verbraucht)“; Stand aus `scripts/limits.py check --json` (`render_view.py project --limits datei`), ohne Datei nur das KI-Budget aus den Kostendateien. Bei `ok` weglassen; dann entfällt der Hinweis |
| `SERIES_ID`, `SERIES_TEXT` | Serie des Buchs (#116) aus `series/` auf dem Standard-Branch (`scripts/series.py of <branch>`): ID und „Band N der Serie „…““; ohne Serie weglassen. Dann steht oben ein Link zur Serie (`view.series`) |
| `UPDATE_BEHIND`, `UPDATE_TEXT` | nur wenn der Buch-Branch hinter dem Hauptrepository liegt (siehe „Update-Stand“): Anzahl Commits und Text wie „3 Commits hinter ploeffler/GhostWriter:main · Version 0.3.1 verfügbar (installiert 0.3.0)“. Sonst weglassen; dann entfällt der Hinweis mit dem Knopf „GhostWriter aktualisieren“ |
| Block `CHAPTERS`: `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_STATUS`, `CHAPTER_COST`, `CHAPTER_COST_HINT`, `CHAPTER_ID` | je Kapitel aus `structure.chapters`, Kosten wie oben; `CHAPTER_ID` ist die stabile Kapitel-ID, ein Klick auf das Kapitel schickt `view.chapter`; ohne Kapitel entfällt der Bereich „Kapitel“ |
| `CHECKS_RECENT_TEXT`, `CHECKS_LEGEND`, Liste `CHECKS_RECENT` | Prüfprotokoll (#331, `editorial/checks.yml`, `scripts/checks.py`): „Letzte Prüfungen“, je Prüfart der neueste Eintrag (höchstens drei), etwa „Sprache ✓· 2026-11-17 · Korrektur ✓ 2026-11-16“; Legende der Kürzel. `CHECKS_RECENT*` nur in der Darstellung „erweitert“ (#538), sonst fehlen sie. Ohne Prüfprotokoll weglassen |
| im Block `CHAPTERS`: `CHAPTER_WORDS`, `CHAPTER_WORDS_TEXT`, `CHAPTER_WORDS_PCT`, `CHAPTER_APPROVED_TEXT`, `CHAPTER_NOTES`, `CHAPTER_NOTES_TEXT` | Kapitelkarte in drei Zeilen (#362, ab UI 0.57.0): Wörter im Manuskript ohne Fußnoten und Kommentare („1.336 Wörter“), Balkenbreite 0–100 relativ zum längsten Kapitel, abgeschlossene Abschnitte („3 von 9“). Offene Hinweise nur, wenn das Prüfprotokoll sie führt (`checks.py record … --notes N`): Summe aus dem neuesten Eintrag je Prüfart, der das Kapitel berührt; sonst weglassen statt schätzen. Die Textfassung zeigt sie als Spalten „Umfang“, „Fertig“ und „Hinweise“ |
| im Block `CHAPTERS`: `CHAPTER_CHECKS_JSON` (Widget); `CHAPTER_CHECKS_TEXT` und Liste `CHAPTER_CHECKS` nur in der Textfassung (#360) | Prüf-Tags des Kapitels (#331); `CHAPTER_CHECKS_JSON` ist dieselbe Liste kompakt als JSON (`CK_TAG`, `CK_TEXT`, `CK_RESULT`, `CK_STATE`, `CK_REPORT`) für `data-gw-checks` im Widget (die Vorlagen kennen keine verschachtelten Blöcke). Kurzfassung wie „S✓ L✓· K✓*“ und je Prüfart ein Tag mit `CK_KIND`, `CK_LABEL` („Sprache“), `CK_SHORT` („L“), `CK_RESULT` (`passed` …), `CK_RESULT_TEXT`, `CK_MARK` (✓, ✓·, ✗, …), `CK_DATE`, `CK_REPORT` (Pfad des Berichts, für den Link), `CK_STATE` (`current`, `changed` = seit Prüfung geändert, `unknown`), `CK_STATE_TEXT`, `CK_PARTIAL` (`1`, wenn die Prüfung nur einen Teil des Kapitels abdeckt), `CK_TEXT` (für den Tooltip), `CK_TAG`, `CK_PILL` (Klartext für das Widget, „Qualität ✓·“; das Widget zeigt ihn als Tag wie die Marker „Quelle“, „Recht“, #340), `CK_WHEN` (Datum, mit Uhrzeit falls gespeichert). Ohne Prüfprotokoll weglassen. Die Textfassung zeigt sie als Spalte „Prüfungen“ |
| im Block `CHAPTERS`, nur mit `--darstellung erweitert` (#398, #672): `CHAPTER_CHECK_DETAILS` | Höchstens eine **kurze** Zeile Handlungsbedarf je Kapitel („Struktur nicht bestanden · 11 offene Hinweise“): nicht bestandene Prüfungen, seit der Prüfung geänderter Text, offene Hinweise; ohne Bedarf fehlt das Feld. Kein Fließtext aus Notizen und **kein Prüfverlauf** (`CHAPTER_HISTORY_JSON` und `CHAPTER_HISTORY_COUNT` entfallen in der Projektübersicht, #672); „Frühere Prüfungen“ stehen nur in der Kapitelansicht (`CHECKS_HISTORY_JSON`). `CHAPTER_CHECKS_JSON` trägt in dieser Stufe zusätzlich `CK_ID` und `CK_NOTE` (Tooltip). Die Legende nennt „Frühere Prüfungen“ in der Projektübersicht nicht. Textfassung: kein Block „Prüfdetails“; der Handlungsbedarf steht in der Liste „Handlungsbedarf“. Aufruf, wenn im Chat „Darstellung: erweitert“ gilt (oder `display: erweitert` in `assistant.yml`): `render_view.py <buch> project --darstellung erweitert` |
| `CHECKS_HISTORY_COUNT`, `CHECKS_HISTORY_JSON`, Block `CHECKS_HISTORY` | Kapitelansicht und Abschnittsformular (#340): frühere Prüfungen, also alle Einträge, die die Einheit berühren, außer dem neuesten je Prüfart; neueste zuerst. Felder wie bei den Tags plus `CK_ID`, `CK_NOTE`; JSON mit `CK_KIND`, `CK_LABEL`, `CK_WHEN`, `CK_DATE`, `CK_TAG`, `CK_MARK`, `CK_TEXT`, `CK_RESULT`, `CK_STATE`, `CK_REPORT`. Widget und Textfassung gruppieren nach Prüfart; je Eintrag nur Datum und Uhrzeit mit Ergebniszeichen. Ist ein Eintrag durch eine spätere Prüfung derselben Art ersetzt, die alles abdeckt, was er in dieser Einheit prüfte, steht vor `CK_NOTE` „ersetzt durch spätere Prüfung <Zeit> <Zeichen>“ (Tooltip; zusätzlich `CK_SUPERSEDED` mit Zeit und Zeichen der ersetzenden Prüfung, die Textfassung hängt „(ersetzt durch …)“ an). Ohne frühere Prüfungen weglassen. Ergebnis `unknown` (Kürzel `?`) bei nachgetragenen Berichten ohne Ergebniszeile |
| `CHARACTER_COUNT` | Zahl der Figuren (`characters`, #53); ohne Figuren weglassen, dann entfällt der Knopf „Figuren“ |
| im Block `CHAPTERS`: `CHAPTER_STALE_TEXT`, `CHAPTER_STALE_HINT`, `CHAPTER_CHECKOUT_TEXT`; im Block `MATTER_FRONT`/`MATTER_BACK`: `MATTER_STALE_TEXT`, `MATTER_STALE_HINT` | Marken (ab UI 0.69.0): „2 veraltet“ mit Tooltip „1.2: Veraltet seit …: Grund“ (#592, `head.stale` der Abschnitte und Teile), „ausgecheckt (GW-7F3A)“ (#572, `checkouts.yml`); leer = keine Marke. Die Marke steht in eigenen Feldern, nicht mehr im Titel |
| `STALE_TEXT` | „3 veraltet“ (Abschnitte und Teile, `scripts/stale.py list`); ein Klick sendet `stale.list`; leer = keine Zeile (#592, ab UI 0.69.0) |
| Block `CHECKOUTS`: `CO_ID`, `CO_TEXT`, `CO_ARGS` | aktive Checkouts (#572, ab UI 0.69.0): „Kapitel 3–5 ausgecheckt an Anna seit 24.11. (GW-7F3A)“, überfällig mit Tagen; `CO_ARGS` = `{"id":"GW-7F3A"}`; „Checkout beenden“ (mit Rückfrage) sendet `checkout.end`; fehlt = kein Hinweis. In der Kapitelansicht nur die Checkouts, die das Kapitel betreffen |
| Block `TODO`: `TODO_TEXT`, `TODO_ACTION`, `TODO_ARGS`, `TODO_ACTION2`, `TODO_ARGS2` | Handlungsbedarf der Prüfungen (#538, #593, ab UI 0.69.0, `checks.todo_widget()`): je Eintrag „Kapitel 2: Sprache nicht bestanden · 3 offene Hinweise“ bzw. „Buch neu prüfen (Sprache)“; Klick = `view.chapter` mit `chapter_id` (buchweite Einträge: nicht klickbar), zweiter Knopf „Hinweise durchsehen“ = `view.notes_review`, nur bei offenen Hinweisen. Nur offene Hinweise zählen; „Letzte Prüfungen“ (`CHECKS_RECENT_TEXT`) nur in der Darstellung „erweitert“. Fehlt der Block, entfällt die Karte |
| Blöcke `MATTER_FRONT`, `MATTER_BACK`: `MATTER_ID`, `MATTER_TITLE`, `MATTER_STATUS`, `MATTER_MARKERS` | Vor- und Nachspann (#57, #58) aus `structure.front_matter` (über der Kapitelliste) bzw. `back_matter` (darunter) in Buchreihenfolge: ID (`mat-…`), Titel, Status, Zahl offener Marker; ein Klick schickt `view.matter`. Ein leerer Bereich fehlt |

### `kapitelansicht.html`

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT`, `CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE` | Projekt und Kapitel |
| `CHAPTER_SUBTITLE` | erste kursive Zeile `*…*` in der `README.md` des Kapitels; sonst leer |
| `CHAPTER_GOAL`, `CHAPTER_SUMMARY` | `## Ziel des Kapitels` und `## Kurzbeschreibung` der Kapitel-README („Offen.“ gilt als leer); nur Ausgabe, leer = „noch offen“. Der Knopf daneben öffnet die Kapitelrecherche |
| `SECTION_COUNT_TEXT`, `MARKER_COUNT_TEXT`, `APPROVED_COUNT_TEXT` | wie oben, Marker über alle Abschnitte |
| `CHAPTER_APPROVABLE` | `true`, wenn das Kapitel auf `ready_for_approval` steht und alle Abschnitte `approved` sind; sonst leer (dann fehlt der Knopf „Kapitel abschließen“) |
| `CHAPTER_REVISION_READY` | `true`, wenn alle Abschnitte Manuskripttext und mindestens Status `writing` haben; sonst leer. Ermittelt mit `scripts/chapter_revision.py`; bei leerem Wert fehlt „Kapitel überarbeiten“. Vor der Durchführung den aktuellen Stand erneut prüfen. |
| `CHAPTER_COST`, `CHAPTER_COST_HINT` | Kapitelkosten |
| im Block `SECTIONS`: `SECTION_STALE_TEXT`, `SECTION_STALE_HINT`, `SECTION_CHECKOUT_TEXT`, `SECTION_ANECDOTE_TEXT`, `SECTION_ANECDOTE_HINT`; Block `CHECKOUTS` mit `CO_ID`, `CO_TEXT`, `CO_ARGS` | Marken je Abschnitt (ab UI 0.69.0): „veraltet“ mit Tooltip „Veraltet seit …: Grund“ (#592), „ausgecheckt“ (#572), ab UI 0.79.0 „enthält Anekdote“ bzw. „Anekdote eingeplant“ mit den Titeln als Tooltip (#643); Hinweis auf Checkouts, die das Kapitel betreffen, mit „Checkout beenden“ |
| Block `SECTIONS`: `SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE`, `SECTION_STATUS`, `SECTION_COST`, `MARKERS_ANEKDOTE`, `MARKERS_QUELLE`, `MARKERS_MEDIZIN`, `MARKERS_RECHT` | je Abschnitt; Status aus dem Kopf der Abschnittsdatei |
| im Block `SECTIONS`: `SECTION_CHECKS_TEXT`, `SECTION_CHECKS_JSON`, Liste `SECTION_CHECKS`; dazu `CHAPTER_CHECKS_TEXT`, `CHECKS_JSON`, `CHECKS_LEGEND`, Block `CHECKS` | Prüf-Tags (#331) je Abschnitt und für das ganze Kapitel, Felder wie `CHAPTER_CHECKS` in der Projektübersicht; ohne Prüfprotokoll weglassen. Tags sind keine Freigabe und stehen getrennt von Status und Freigaben |

### `abschnitt-bearbeiten.html`

Veraltet-Vermerk (#592, ab UI 0.69.0): `STALE_TEXT` („Veraltet seit 25.11.2026: Grund“, leer = nicht markiert), `STALE_NONE` (`1`, wenn nicht markiert) und `STALE_ARGS` (`{"section_id":"…"}`) aus `render_view.stale_values()`. „Als veraltet markieren“ fragt den Grund ab und sendet `section.mark_stale`, „Markierung entfernen“ sendet `section.clear_stale`; beides ändert weder Status noch Freigabe (`scripts/stale.py`). Gilt gleich für `teil-bearbeiten.html` mit der Teil-ID (`mat-…`) als `section_id`: `STALE_TEXT`, `STALE_NONE`, `STALE_ARGS`.

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT`, `CHAPTER_ID`, `CHAPTER_NUMBER`, `SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE` | Projekt, Kapitel, Abschnitt |
| `SECTION_STATUS`, `FACT_CHECK` | Kopf der Abschnittsdatei: `status`, `fact_check` |
| `APPROVAL_WRITING`, `APPROVAL_SECTION` | `approvals.writing`, `approvals.section` als `true`/`false`; nur Anzeige, geändert werden sie über „Freigabe bestätigen“ |
| `SECTION_COST`, `SECTION_COST_HINT` | Abschnittskosten, Tooltip „Summe der Kosteneinträge“ |
| `SECTION_GOAL`, `SECTION_SUMMARY`, `SECTION_MANUSCRIPT` | Ziel, Kurzbeschreibung, Manuskript |
| `MARKER_COUNT_TEXT` | Marker des Abschnitts |
| Block `MARKERS`: `MARKER_TYPE`, `MARKER_LABEL`, `MARKER_TEXT` | je Marker in Reihenfolge; ohne Marker entfällt der Bereich „Offene Marker“ |
| Block `CHECKS`, `CHECKS_JSON`, `SECTION_CHECKS_TEXT` | Prüf-Tags des Abschnitts (#331), `CHECKS_JSON` für `data-gw-checks`, Felder wie `CHAPTER_CHECKS` in der Projektübersicht; ohne Prüfung weglassen. Nur Anzeige, keine Freigabe |
| Block `HINTS`: `H_KIND_TEXT`, `H_TEXT`, `H_QUOTE` | sprachliche Hinweise zum Abschnitt aus `story/hints.yml` (#124): Art („Langer Satz“, „Wortwiederholung“, „Gleiche Satzanfänge“, „Füllwörter“, „KI-typisches Muster“, #305), Hinweis, Fundstelle; ohne Hinweise weglassen |
| `PREV_SECTION_ID`, `PREV_SECTION_PROMPT`, `NEXT_SECTION_ID`, `NEXT_SECTION_PROMPT` | Nachbarabschnitte im selben Kapitel, Text „Abschnitt N.M „Titel“ bearbeiten“; am Rand leer |
| `CHARACTERS_ENABLED`, Block `ALL_CHARACTERS`: `C_ID`, `C_NAME`, `C_ON` | nur wenn das Buch Figuren hat (#53): `1`; je Figur ID, Name und `1`, wenn sie in `characters` des Abschnittskopfs steht |
| `RESEARCH_QUEUE_AVAILABLE`, `RESEARCH_QUEUE_TEXT` | Option „Warteschlange“ der Recherche (#482, ab UI 0.65.0): `true`, wenn für die Recherche ein Dienst mit API eingestellt ist (Buch, sonst Standard-Branch der Bibliothek; `research_queue_values()`), sonst `false`; Text „mit Internet über <Dienst>“, sonst leer. Der Klick sendet `run.start` mit `task: research`, `mode: scheduled` |
| `WRITING_NOW_AVAILABLE`, `RESEARCH_NOW_AVAILABLE` | Option „Sofort“ des KI-Entwurfs bzw. der Recherche (ab UI 0.81.0, #759): `false` sperrt sie vor dem Klick, wenn die Umgebung weder Chat noch Modell hat (eigene Web-App; setzt `S.sample`); im Chat leer lassen (Option bleibt frei) |

### `abschnittssteuerung.html`

`SECTION_ID`, `SECTION_NUMBER`, `SECTION_TITLE` wie im Abschnittsformular, ebenso `RESEARCH_QUEUE_AVAILABLE` und `RESEARCH_QUEUE_TEXT`. Ab UI 0.77.0 (#65): `CHAPTER_ID` (Kapitel des Abschnitts) für die Start-Option „nach Freigabe des Kapitels“; die Zeile „Start der Warteschlange“ (sofort · später · bei freiem Budget · nach Freigabe) ergänzt `run.start` (`mode: scheduled`) und `chapter.research.start` um `start` (`later` \| `budget_free` \| `after_approval`), `not_before` (ISO-Zeitpunkt bei `later`) bzw. `after_event` (`chapter_approved:<Kapitel>`).

### `projektdaten-bearbeiten.html`

`PROJECT_TITLE`, `PROJECT_TITLE_SHORT`, `PROJECT_AUTHOR`, `PROJECT_DESCRIPTION_SHORT`, `PROJECT_DESCRIPTION` wie in der Projektübersicht, hier als Vorbelegung der Felder. Dazu die Buchangaben (#299, ab UI 0.46.0): `PROJECT_SUBTITLE` (`project.subtitle`), `PROJECT_LANGUAGE` (`project.language`), `PROJECT_BOOK_TYPE` (`project.book_type`), `PROJECT_TARGET_AUDIENCE` (`project.target_audience`), `PROJECT_TRANSLATIONS` (`project.translations_planned` als Komma-Liste, leer = keine).

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
| `APPROVAL_WARNING_TEXT` | „Bisher abgeschlossen: N von M Kapiteln; nur abgeschlossene Kapitel kommen in die Auflage.“; leer, wenn alle abgeschlossen sind (der Hinweis entfällt) |
| Block `FORMATS`: `FORMAT_LABEL` | `book_releases.assets`, in v0.5 PDF, DOCX, EPUB |
| `PREVIEW_TAG` | Tag der nächsten Vorabfassung `<kurztitel>-vorab-N` (höchste vorhandene Nummer + 1, wie `edition_info.py --preview`). Ab UI 0.54.0 zeigt das Formular damit den Knopf „Vorabfassung“ neben „Probedruck“ (#352): Der erste Klick zeigt, dass dieser Tag und ein im Repository sichtbares Pre-Release entstehen, erst der zweite sendet `edition.preview`. Leer = kein Knopf |

### `kapitel-bearbeiten.html`

`CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_SUBTITLE` wie in der Kapitelansicht; `CHAPTER_SUMMARY` und `CHAPTER_GOAL` aus `## Kurzbeschreibung` und `## Ziel des Kapitels` der Kapitel-README („Offen.“ gilt als leer).

### `kapitelrecherche.html`

| Platzhalter | Quelle |
|---|---|
| `CHAPTER_ID`, `CHAPTER_NUMBER`, `CHAPTER_TITLE`, `CHAPTER_GOAL`, `CHAPTER_SUMMARY` | wie in der Kapitelansicht; nach einer Recherche die zuletzt gesendeten, noch nicht gespeicherten Werte (`--draft`) |
| `RESEARCH_QUESTION`, `RESEARCH_SCOPE` | `question` und `scope` des letzten Laufs bzw. die gesendeten Werte; sonst leer |
| `RESEARCH_TASK` | `goal`, `sections`, `summary` oder leer: gesendeter Wert, sonst `task` des letzten Laufs, sonst `goal`, solange das Ziel leer ist |
| `SECTION_COUNT`, `SECTIONS_NOTE` | Zahl der vorhandenen Abschnitte und Hinweis, dass sie unverändert bleiben und neue ans Ende kommen (bei abgeschlossenem Kapitel: wird wieder „in Arbeit“) |
| Block `SUGGESTED_SECTIONS`: `SUG_TITLE`, `SUG_SUMMARY` | Zeilen `- Titel: Kurzbeschreibung` unter `## Vorschlag: Abschnitte` des letzten Laufs, ohne Titel, die es im Kapitel schon gibt; leer = Bereich entfällt |
| `PREV_CHAPTER`, `PREV_CHAPTER_LABEL`, `PREV_CHAPTER_SUMMARY`, `PREV_WEIGHT` | vorheriges Kapitel („Kapitel N · Titel“, Kurzbeschreibung); Gewichtung 0–3 aus gesendetem Wert bzw. letztem Lauf, sonst 2; ohne vorheriges Kapitel leer (Bereich entfällt) |
| `NEXT_CHAPTER`, `NEXT_CHAPTER_LABEL`, `NEXT_CHAPTER_SUMMARY`, `NEXT_WEIGHT` | ebenso für das nächste Kapitel |
| `RESEARCH_PROVIDER_TEXT` | „Recherche über: …“ aus `ai_providers.research.provider` (sonst `default`; `chat` = „aktueller Chat“) |
| `RUN_COUNT_TEXT` | Zahl der Läufe unter `research/kapitel/` und Datum des letzten |
| `LAST_RUN`, `LAST_RUN_ID`, `LAST_RUN_TEXT` | letzter Lauf: `true`, `id`, Abschnitt `## Kurzfassung`; ohne Lauf entfällt der Ergebnisbereich |
| `SUGGESTED_GOAL`, `SUGGESTED_SUMMARY` | `## Vorschlag: Ziel des Kapitels` und `## Vorschlag: Kurzbeschreibung` des letzten Laufs; leer = kein Vorschlag |

### `buecherregal.html`

`BOOK_CHECKOUT_TEXT` (ab UI 0.69.0, #572): ausgecheckte Bereiche des Buchs aus `checkouts.yml` des Buch-Branchs (`library.json`, Feld `checkouts`), z. B. „Kapitel 3–5 ausgecheckt an Anna seit 24.11. (GW-7F3A)“, überfällig mit Tagen; leer = entfällt.

Startseite einer Bibliothek; Widget oder Text nach dem Darstellungsmodus. Erzeugt mit `render_view.py library --library library.json --repo <owner>/<repo>` (Widget; `--text` nur im Modus „Nur Text“) aus der Übersicht `library.json` auf dem Standard-Branch (`scripts/library.py build`, Action „Bücherregal aktualisieren“); fehlt sie, live aus den Branches.

| Platzhalter | Quelle |
|---|---|
| `LIBRARY_NAME` | `owner/repo` (`--repo`; ohne Angabe aus `GITHUB_REPOSITORY` bzw. `git remote origin`, bei der Seite „Daten“ auch aus `repo.full_name` in `--github`; sonst „unbekanntes Repository“, nie das Hauptrepository, #134) |
| `BOOK_COUNT_TEXT`, `EMPTY` | Zahl der Bücher („1 Buch“, „2 Bücher“); `EMPTY` = `1` ohne Buch |
| `UPDATED_TEXT` | derzeit leer (Bereich entfällt) |
| Block `BOOKS`: `BOOK_BRANCH`, `BOOK_TITLE`, `BOOK_TITLE_SHORT`, `BOOK_AUTHOR_TEXT` | je Buch aus `library.json`: `branch`, `title`, `title_short`, „von <author>“ |
| `BOOK_STATE`, `BOOK_STATE_TEXT` | `status`: `ready` „eingerichtet“ (hat Kapitel) bzw. `setup` „im Aufbau“ |
| `BOOK_PROGRESS`, `BOOK_PROGRESS_TEXT` | Anteil `sections_approved`/`sections_total` in Prozent; „N von M Abschnitten abgeschlossen · K von L Kapiteln“, im Aufbau „Gliederung noch offen“ |
| `BOOK_EDITION_TEXT`, `BOOK_COST` | `current_edition` („Auflage N“ bzw. „noch keine Auflage“), `cost.text` |
| `BOOK_PENDING_TEXT` | `pending` > 0: „N Änderungen offen“ (Commits im Arbeits-Branch), sonst leer |
| `BOOK_JOBS_TEXT` | Hintergrund-Warteschlange des Buchs (#484, ab UI 0.66.0) aus `books[].jobs` in `library.json` (`done`, `failed`, `waiting`, `waiting_budget`; `jobs.remote_status()`): „Warteschlange: N fertig · M fehlgeschlagen · K warten“; leer, wenn nichts |
| `BOOK_UPDATED_TEXT` | „zuletzt geändert am TT.MM.JJJJ“ bzw. „angelegt am …“ aus `updated_at` |
| `BOOK_SERIES`, `BOOK_SERIES_TITLE`, `BOOK_SERIES_KEY`, `BOOK_VOLUME_TEXT` | Serie des Buchs (#116) aus `library.json` (`series`) bzw. `series/` auf dem Standard-Branch: ID, Reihentitel, Kürzel `S1`, `S2` … (Reihenfolge der Serien) und „Band N“; ohne Serie leer. Bücher einer Serie stehen zuerst, je Serie in Bandreihenfolge, danach die übrigen |
| Block `EMPTY_SERIES`: `S_ID`, `S_TITLE`, `S_KEY` | Serien, zu denen noch kein Buch gehört; sonst Block weglassen |
| `SESSION_COUNT_NUMBER`, `SESSION_COUNT_TEXT` | Zahl der offenen Sitzungssicherungen und „Offene Sitzungssicherungen (N)“; ohne offene Sicherung leer (Rubrik entfällt) |
| `JOBS_TEXT` | Summe aller Bücher, „Hintergrund-Warteschlange: N fertig · …“ (#484); leer = Rubrik entfällt |
| Block `SESSIONS`: `SS_SESSION`, `SS_TITLE`, `SS_BOOK`, `SS_BOOK_BRANCH`, `SS_BRANCH`, `SS_TIME_TEXT`, `SS_DEVICE_TEXT`, `SS_OS_TEXT`, `SS_CLIENT_TEXT`, `SS_STATUS`, `SS_STATUS_TEXT`, `SS_PR` | je offener Sitzungssicherung aus `sessions` in `library.json` (bzw. `--sessions`, #237), neueste zuerst: Kennung, `context.project` (sonst Kennung), Titel des Zielbuchs, Zielbranch, Sicherungsbranch, `last_saved.at` in Ortszeit (`--timezone`), Gerät, System, Client mit Version (fehlend „unbekannt“), Status `open` „Änderungspaket“ (mit Link `SS_PR`) / `pr_pending` „gesichert, Änderungspaket ausstehend“ / `unknown` „Status nicht verfügbar“. Rubrik direkt unter dem Titel; ohne offene Sicherung Block weglassen |
| `BOOK_KEY`, `BOOK_EDITION_COUNT` | Nummer des Buchs im Regal (Kürzel der Textfassung) und Zahl seiner Auflagen aus `editions` (#235) |
| Block `EDITIONS`: `E_BOOK_BRANCH`, `E_BOOK_KEY`, `E_KEY`, `E_NUMBER`, `E_TEXT`, `E_DATE_TEXT`, `E_TAG`, `E_BRANCH`, `E_DETAIL` | je Auflage eines Buchs aus `library.json` (`editions`), in Regal- und dann numerischer Reihenfolge: Buch-Branch und Nummer des Buchs, Kürzel `<Buch>.<Auflage>`, „Auflage N“, Datum (Tag bzw. letzter Commit des Auflagen-Branchs), Tag, Auflagen-Branch (leer, wenn es keinen gibt), Kurzangabe für die Textfassung. Das Widget ordnet die Einträge über `E_BOOK_BRANCH` unter der Karte des Buchs an; die Textfassung zeigt sie als Zeilen „↳ Auflage N“ unter dem Buch. Ohne Auflagen Block weglassen |

In der Projektübersicht kommt `LIBRARY_COUNT` (Zahl der Bücher, nur ab 2, sonst leer) aus derselben Datei (`--library`).

### `daten.html`

Seite „Daten“ (`render_view.py data`, `START.md`, „Daten“). Quellen: `library.json` (`--library`), Rohdaten der GitHub-API (`--github`: `repo`, `branches`, `pulls`, `runs`), Update-Stand (`--upstream`).

| Platzhalter | Quelle |
|---|---|
| `LIBRARY_NAME` | `owner/repo` (`--repo`; ohne Angabe aus `GITHUB_REPOSITORY` bzw. `git remote origin`, bei der Seite „Daten“ auch aus `repo.full_name` in `--github`; sonst „unbekanntes Repository“, nie das Hauptrepository, #134) |
| `PROGRAM_VERSION_TEXT`, `UI_TEXT` | `program.version`, `program.upstream`, `program.ui_version`, `program.ui_commit` aus `library.json` |
| `PROGRAM_UPDATE_TEXT`, `PROGRAM_BEHIND` | Update-Stand aus `--upstream` („aktuell“ bzw. Commits dahinter); ohne Angabe „nicht abgefragt“; `PROGRAM_BEHIND` nur, wenn dahinter |
| `PROGRAM_LAST_UPDATE_TEXT`, `PROGRAM_SKIPPED_TEXT` | `program.last_update`, `program.skipped_workflows` (aus `.ghostwriter/update.yml` des Standard-Branchs) |
| Block `LIMITS`: `L_LABEL`, `L_STATE`, `L_TEXT` | Nutzungsgrenzen (#62): je geprüfter Grenze Name, Ampel `ok` / `warn` (unter 20 %) / `pause` (unter 10 %) und Stand wie „62 % übrig (3,80 von 10,00 € verbraucht)“; aus `--limits` (`scripts/limits.py check --json`) bzw. aus den Kostendateien des Buchs und `rate_limit` in `github.json`. Keine Grenze eingestellt bzw. prüfbar = Block weglassen |
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
| Block `IMAGES`: `I_ID`, `I_CAPTION`, `I_STATE`, `I_SOURCE`, `I_SIZE`, `I_IN_TEXT`, `I_POSITION`, `I_WIDTH` | je Beschreibung `img-….yml` im Bildordner: ID, Bildunterschrift, `status` (`draft`/`approved`; bewusst nicht `…_STATUS`, das gw.js übersetzen würde), Herkunft deutsch, Größe in px, `1`, wenn `![](bild:…)` im Manuskript steht; `position` (leer = an der Stelle im Text) und `width_pct` (Vorgabe 100) für Lage und Breitenregler (#54, ab UI 0.61.0) |

### `figuren.html`

Liste der Figuren (`render_view.py characters`, #53).

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | wie in der Projektübersicht |
| Block `CHARACTERS`: `C_ID`, `C_NAME`, `C_ROLE`, `C_SHORT`, `C_USED` | je Figur aus `characters` und dem Kopf der Figurendatei: ID, Name, Rolle deutsch, `short`, Abschnitte bzw. Teile mit dieser Figur im Kopf (`character_usage`), sonst „–“ |
| `C_SOURCE`, `C_SOURCE_TEXT` | nur in einem Band einer Serie (#116): `series` „aus der Serie“ (Figur unter `series/<ser-id>/characters/`), `copy` bzw. `copy_diff` (Figur des Buchs mit derselben ID: Kopie, gleich bzw. abweichend), `own` „nur in diesem Buch“; ohne Serie leer |
| `C_PORTRAIT` | Profilbild (#417) als verkleinerte JPEG-Daten-URL (80 px, quadratisch beschnitten), nie das Original; Quelle: `portrait` im Figurenkopf, sonst das erste freigegebene Referenzbild mit Rolle `visual_reference` und Link `person:<char-id>`; ohne Bild leer. Textfassung: Liste „Profilbilder“ mit Dateipfad |
| `SERIES_TITLE` | Reihentitel des Bandes; ohne Serie leer (dann kein Hinweis) |

### `figur-bearbeiten.html`

Formular einer Figur (`render_view.py characters <name|id>`).

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | wie in der Projektübersicht |
| `CHARACTER_ID`, `CHARACTER_NAME`, `CHARACTER_ROLE` | `id`, `name`, `role` (main, supporting, minor) |
| `CHARACTER_SHORT`, `CHARACTER_AGE`, `CHARACTER_APPEARANCE`, `CHARACTER_VOICE`, `CHARACTER_VISUAL` | gleichnamige Felder des Kopfs (`short`, `age`, `appearance`, `voice`, `visual`), sonst leer |
| `CHARACTER_PORTRAIT`, `CHARACTER_PORTRAIT_ID` | Profilbild (#417) als verkleinerte Daten-URL (192 px) und ID des Referenzbilds; ohne Bild leer. Anderes Bild wählen: `portrait: ref-img-…` im Figurenkopf setzen |
| `CHARACTER_TRAITS` | `traits`, kommagetrennt |
| `CHARACTER_DESCRIPTION`, `CHARACTER_NOTES` | `## Beschreibung`, `## Notizen` (Platzhalter der Vorlage = leer) |
| `CHARACTER_USED` | Abschnitte bzw. Teile mit dieser Figur, sonst „noch nirgends“ |
| Block `RELATIONS`: `R_TO`, `R_NAME`, `R_KIND` | `relations`: ID und Name der anderen Figur, Art |
| Block `OTHERS`: `O_ID`, `O_NAME` | alle anderen Figuren (Auswahl für Beziehungen) |
| `CHARACTER_SOURCE`, `CHARACTER_SOURCE_TEXT` | Herkunft wie `C_SOURCE` (#116); bestimmt Speichern (`character.series.update` bei `series`) und die Knöpfe „Kopie nur für dieses Buch“, „An Serie angleichen“, „In die Serie übernehmen“ |
| `SERIES_ID`, `SERIES_TITLE` | Serie des Bandes; ohne Serie leer |

### `figurenbild.html`

Stilkarten und Variantenvergleich für das Figurenbild (#540, Teil 3, UI 0.76.0; `render_view.py . figure-image stil` bzw. `figure-image <Figur>`, `START.md`, „Figurenbild-Assistent“). Textfassung mit `--text` (de/en), auch in Clients ohne Widgets. Gespeichert wird nichts im Widget selbst: Es sendet nur Nachrichten, der Assistent führt danach `figurenbild.py` aus.

| Platzhalter | Quelle |
|---|---|
| `FB_MODE` | `stil` \| `varianten` |
| `FB_INHERITED_TEXT` | Hinweis auf vom Serienstil geerbte Angaben (z. B. „Medium von der Serie geerbt“); derzeit leer, der Serienstil wird erst über `figurenbild.py --serie` gelesen |
| `FB_MEDIUM`, `FB_REALISMUS`, `FB_FARBIGKEIT`, `FB_LICHT`, `FB_AUSSCHNITT`, `FB_HINTERGRUND`, `FB_MERKMALE`, `FB_AUSSCHLUESSE`, `FB_FREITEXT` | aktueller Bildstil (`images/stil.yml`); Listen als Text mit Komma |
| Block `MEDIA`: `M_VALUE`, `M_LABEL`, `M_DESC` | die fünf Medien von `figurenbild.MEDIEN` |
| `FB_FIGURE_ID`, `FB_FIGURE_NAME` | Figur der Variantenansicht |
| Block `VARIANTS`: `V_ID`, `V_THUMB`, `V_ART_TEXT`, `V_STATUS`, `V_STATUS_TEXT`, `V_KLEIDUNG`, `V_TOOL`, `V_INPUT`, `V_PROMPT` | je Bild aus `characters/<id>/bilder.yml`; `V_THUMB` ist eine kleine Ableitung (160 px) als Daten-URL, nie das Original; `V_PROMPT` nur der Anfang |

Aktionen: `figurenbild.stil.save` (`style` mit den gefüllten Feldern; Speichern erst nach zweitem Klick im Widget → `figurenbild.py . stil set '<json>'`, ein Commit), `figurenbild.pick` (`figure`, `image_id`, `status`: `gewaehlt` | `idee` → `figurenbild.py . waehlen`; keine Referenzfreigabe), `figurenbild.change` (`figure`, `image_id`: der Assistent fragt, was sich ändern soll, und legt die Änderung als neue Variante mit Eingabebild an), `form.cancel`.

### `figurengespraech.html`

Steuerkarte neben dem Chat für das Figurengespräch (#431, UI 0.73.0; `render_view.py character-talk [<Figur>] [--draft '<json>']`, `START.md`, „Figuren“, Schritt 8). Das Widget **steuert** das Gespräch, die Antworten der Figur stehen im Chat (ein Widget kann Nachrichten senden, aber den Chat nicht lesen). Drei Stufen mit `--draft '{"phase": "start|active|insights", "until": "2.3", "insights": [{"field": "traits", "text": "…"}]}'`: `start` (ohne Figur: Auswahl von Figur und Stelle), `active` (mit Figur: „Gespräch beenden“, „Stelle ändern“, „Figur wechseln“), `insights` (Karte „Erkenntnisse“ nach dem Gespräch). Textfassung mit `--text` (de/en), auch in Clients ohne Widgets.

| Platzhalter | Quelle |
|---|---|
| `TALK_PHASE` | `start` \| `active` \| `insights` |
| `TALK_FIGURE_ID`, `TALK_FIGURE_NAME`, `TALK_PORTRAIT` | gewählte Figur; Profilbild als kleine Ableitung des freigegebenen Referenzbilds (#417, wie `figuren`), leer = Anfangsbuchstabe |
| `TALK_UNTIL`, `TALK_UNTIL_TEXT`, `TALK_KNOWLEDGE_TEXT` | Stelle (`2.3`, `2` = bis Ende Kapitel 2, leer = ganzes Buch), als Text und woher der Wissensstand kommt („7 Ereignisse (5 belegt, 2 angenähert)“, aus `characters.knowledge`, wie `interview`) |
| Block `FIGURES`: `F_ID`, `F_NAME`, `F_PORTRAIT` | alle Figuren des Buchs (und der Serie) |
| Block `PLACES`: `P_VALUE`, `P_LABEL` | „bis Ende Kapitel N: Titel“ und je Abschnitt „N.M Titel“ |
| Block `INSIGHTS`: `I_IDX`, `I_FIELD`, `I_FIELD_TEXT`, `I_TEXT`, `I_CURRENT` | Vorschläge des Assistenten aus dem Gespräch (Feld: `traits`, `voice`, `short`, `appearance`, `age`, `description`, `notes`, `relation`), mit bisherigem Wert; nichts vorangehakt |

Aktionen: `character.talk.start|end|until|switch|apply` (siehe unten), `form.cancel`.

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
| `RUN_ID`, `RUN_TEXT` | `run` und „Hintergrundlauf NNN vom TT.MM.JJJJ“, bei einem Lauf aus einer Chat-Rückgabe (`source: chat`, #353) „Chat-Analyse NNN vom TT.MM.JJJJ“ |
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

### `glossar-vorschlag.html`

Auswahl „Glossar-Begriffe aus dem Text“ aus einem Hintergrundlauf (#490, #630, ab UI 0.70.0, Art `glossary`; `render_view.py analysis-suggest --draft analysis/glossary/run-NNN.json`). Nichts ist vorangehakt; ein angehakter Begriff braucht eine Erklärung.

| Platzhalter | Quelle |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT`, `SCOPE_TEXT` | wie bei `kurzbeschreibung-vorschlag` (`KIND` = `glossary`) |
| `SUGGEST_COUNT_TEXT` | „N Begriffe“ |
| Block `SUGGESTIONS`: `S_IDX`, `S_TERM`, `S_EXPL`, `S_SECTIONS`, `S_EVIDENCE` | je Begriff aus der Vorschlagsdatei: Nummer, Begriff, Erklärung (leer, wenn der Text keine gibt), Abschnitte, bis zu zwei Fundstellen |
| `S_STATE`, `S_STATE_TEXT` | `new` bzw. `existing` (steht schon im Glossar; nicht wählbar), „neu“ bzw. „steht schon im Glossar“ |

„Übernehmen“ sendet `analysis.apply` mit `kind` = `glossary`, `run` und `choices` `[{index, term, explanation}]`; übernommen wird jeder Begriff einzeln über `scripts/matter.py` (vorhandene Einträge bleiben, ohne Erklärung wird nichts angelegt).

### `rueckgabe.html`

Eingecheckte Rückgabe (#573, #209, #630, ab UI 0.70.0): `render_view.py checkin checkouts/<kennung>/rueckgabe-<datum>` (Textfassung mit `--text`). Die Rückgabe beendet den Checkout nie; Aufbau-Änderungen sind nicht vorangehakt.

| Platzhalter | Quelle |
|---|---|
| `RET_ID`, `RET_KIND_TEXT`, `RET_DATE_TEXT`, `RET_STATS_TEXT` | Kennung, „Word-Datei (DOCX) · Programm“, Datum, „N Befunde · M Kommentare · K Aufbau-Änderungen“ aus `rueckgabe.yml` |
| `RET_LATE_TEXT` | Hinweis bei später Rückgabe (`spaet`), sonst leer |
| `RET_FOLDER`, `RET_FINDINGS_FILE` | Ablageordner; Befunddatei (leer = keine Befunde, Knopf „Befunde durchsehen“ sendet `view.notes_review`) |
| `RET_END_ARGS` | `{"id":"GW-…"}`, solange der Checkout läuft (Knopf „Checkout beenden“ sendet `checkout.end`); sonst leer |
| `RET_CAN_APPLY`, `RET_APPLY_HINT` | `1`, wenn der Checkout beendet ist; sonst der Hinweis „erst beenden“ |
| Blöcke `NOTES` (`N_TEXT`), `PAGES` (`P_TEXT`), `QUESTIONS` (`Q_TEXT`) | „Nicht übernommen: …“, „Vergleich über den Text“, Zuordnung der Abschnitte; Seiten eines Scans mit Zuordnung; offene Fragen |
| Block `AUFBAU`: `A_ID`, `A_TEXT`, `A_STATE` | Aufbau-Änderungen (`offen`, `uebernommen`, `nicht-moeglich`); die Auswahl sendet `checkout.aufbau` |

### `orte-vorschlag.html`

Auswahl „Schauplätze aus dem Text“ aus einem Hintergrundlauf (#124, Art `places`; `render_view.py analysis-suggest --draft analysis/places/run-NNN.json`).

| Platzhalter | Quelle |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT`, `SCOPE_TEXT` | wie bei `kurzbeschreibung-vorschlag` (`KIND` = `places`) |
| `SUGGEST_COUNT_TEXT` | „N Orte“ |
| Block `SUGGESTIONS`: `S_IDX`, `S_NAME`, `S_ALIASES`, `S_KIND`, `S_SHORT`, `S_SECTIONS`, `S_EVIDENCE` | je Ort aus der Vorschlagsdatei: Nummer, Name, andere Bezeichnungen, Art, ein Satz, Abschnitte (`N.M`), bis zu zwei Fundstellen |
| `S_STATE`, `S_STATE_TEXT`, `S_EXISTING` | `new` bzw. `existing` (Name oder andere Bezeichnung steht schon in `story/places.yml`), „neu“ bzw. „schon da: …“, ID des bekannten Orts (vorgewählt bei „Zusammenlegen mit“) |
| Block `MERGE`: `M_ID`, `M_NAME` | Orte aus `story/places.yml` |

### `zeitleiste.html`

Grafische Zeitleiste der Chronologie (#354, ab UI 0.56.0; `render_view.py timeline`, Aktion `view.timeline`). Gefüllt von `chronology.widget_values()`; die Textfassung (`--text`) ist `chronology.text_view()`, bei Englisch nativ als Text (`--language en`, #364). Mit Erzählzeit (`epoch`, #379, ab UI 0.60.0) enthält `TIMELINE_JSON` zusätzlich `epoch` (`base` = interner Tag 0, `label`) und je Zeitpunkt `minutes` (Lage im Tag: die Uhrzeit, ohne Uhrzeit gleichmäßig zwischen den Nachbarn desselben Tags, #394; angezeigt wird die Uhrzeit nur über `label`); die Vorlage beschriftet dann in „Tag N“. Hinweise enthalten auch die Art „Text gegen Chronologie“ (`text`, Abgleich mit `story/timeline.yml`); als Datei ohne Widget: `chronology.py export`.

| Platzhalter | Quelle |
|---|---|
| `PROJECT_TITLE_SHORT` | `project.title_short` |
| `COUNT_TEXT` | „N Einträge · M Hinweise“ (Hinweise ohne „ohne Datum“) |
| `TIMELINE_JSON` | JSON: `entries` (je Eintrag `id`, `kind`, `lo`/`hi` = frühester/spätester Tag des Beginns, `end_lo`/`end_hi` = des Endes bei `span`, `open` = Ende offen, `label` = Datum wie in der Textfassung, `what`, `status`, `estimated`, `lanes` = Figuren-IDs bzw. `@none`, `people`, `place` = Ortsname, `chapter` = „N: Titel“, `source`, `flag` = von einem Hinweis betroffen), `lanes` (`key`, `label`; `@none` = „Ohne Figur“), `chapters` (Kapitelband: `label` „K1“, `lo`, `hi` aus den Einträgen mit `chapter`). Einträge ohne Datum haben leeres `lo` und stehen nur in der Liste |
| `EMPTY_TEXT` | Text ohne Chronologie; sonst leer |
| Block `FINDINGS`: `F_KIND_TEXT`, `F_TEXT`, `F_ENTRIES` | Hinweise aus `chronology.findings()` ohne „ohne Datum“: Art, Satz, IDs |

Zeitraum, Filter nach Belegstand und Auswahl eines Eintrags wirken nur in der Ansicht; gesendet wird nur `view.project`.

### `einstellungen.html`

Alle Einstellungen (#299, ab UI 0.64.0; `render_view.py <ordner> settings-overview [wo]`, Befehl „Alle Einstellungen“). Nur lesend. Gefüllt von `settings_overview.widget_values()`; die Textfassung (`--text`) ist `settings_overview.markdown()`, auch auf Englisch. `wo`: leer bzw. eine Gruppe (`typesetting`) für das Buch, `bibliothek`, `serie <ser-id>`, `sammelband <ser-id>`.

| Platzhalter | Quelle |
|---|---|
| `SETTINGS_KIND` | `book`, `library`, `series` oder `omnibus` (Zurück-Knopf: Projektübersicht bzw. Bücherregal) |
| `SETTINGS_TITLE` | „Alle Einstellungen“, dazu Seite und Titel |
| `SETTINGS_INTRO` | Zahl der Einstellungen und der eigenen Werte |
| Block `GROUPS`: `G_KEY`, `G_TITLE`, `G_ROWS` | je Gruppe; `G_ROWS` ist eine JSON-Liste mit `key`, `label` (Abschnittstitel bei „Abweichend vom Buch“), `value` (Anzeigetext), `origin` (`book`, `library`, `default`, `unset`, `own`, `series`, `omnibus`, `section`), `origin_text`, `differs` (weicht von der Vorgabe ab), `form_text` (Formular bzw. „nur in der Datei“) |

Filter „Nur eigene Werte“ und Suche wirken nur in der Ansicht; gesendet wird nur `view.project` bzw. `view.library`.

### `hinweisdurchsicht.html`

Hinweisdurchsicht (#367, ab UI 0.58.0; `render_view.py notes-review [<datei>]`, Aktion `view.notes_review`). Ohne Datei die neueste `editorial/durchsicht-*.yml`. Gefüllt von `hinweise.widget_values()`; die Textfassung (`--text`) ist `hinweise.show()`. Ablauf und Grenzen: [Lektorat, „Hinweise durchsehen“](../../docs/LEKTORAT.md#hinweise-durchsehen-hinweisdurchsicht-367).

| Platzhalter | Quelle |
|---|---|
| `REVIEW_FILE` | Pfad der Dialogdatei im Buch, wird mit jeder Aktion zurückgeschickt |
| `REVIEW_BOOK`, `REVIEW_DATE_TEXT`, `REVIEW_COUNT_TEXT` | `buch`, „Stand TT.MM.JJJJ“ aus `erstellt`, „N Einträge · M entschieden · K offen“ |
| Blöcke `AUTO` (`ohne_autor`) und `AUTHOR` (`autorenentscheidung`): `E_ID`, `E_WHERE`, `E_CHAPTER_TEXT`, `E_KIND`, `E_REASON`, `E_CONTEXT`, `E_OLD`, `E_NEW`, `E_DECISION`; bei `AUTHOR` dazu `E_QUESTION` (mit „· Antwort: …“, wenn der Autor geantwortet hat, und „· ⚠️ …: wird nicht automatisch umgesetzt“, wenn `neu` kein Ersatztext ist, #675) und `E_PROPOSED` (gesetzt, wenn `E_NEW` ein Vorschlag des Assistenten ist, ab UI 0.68.0; `E_VARIANTS_JSON`, JSON-Liste der Varianten, ab UI 0.70.0) | `id`, `abschnitt`, „Kapitel N · <Status>“, `art`, `grund`, `kontext`, `alt`, `neu`, `entscheidung` (bzw. `umgesetzt`), `frage`; leere Gruppen weglassen |
| Block `SKIPPED`: `SK_REF`, `SK_REASON` | `ausgelassen` (`befund`, `grund`) |

Ab 12 offenen Einträgen zeigt das Widget nur die aktuelle Stufe (#570: Blockierendes, Gruppen, Runden zu fünf, „gering“ zugeklappt; `render_view.py notes-review --alle` zeigt alles). Eine Gruppe erscheint als eine Zeile mit der ID `gruppe:<schlüssel>`; `ja` nimmt alle Einträge mit Vorschlag an, `nein` lässt alle (`hinweise.py decide . --group <id> --decision ja|nein`), „einzeln ansehen“ öffnet sie (`hinweise.py show . --group <id>`). „gering lassen“: `hinweise.py decide . --gering`.

**Einzelne Karte (#473, Kopfzeile #608):** `REVIEW_COUNT_TEXT` beginnt mit Stufe, Thema und Fortschritt im Thema („Stufe 2 · Thema 1 von 22: … · 1 von 2 in diesem Thema · Eintrag 5 von 121 · noch 117 offen“); `hinweise.py decide … --next-card --repo <owner/repo>` speichert und gibt die nächste Karte fertig befüllt aus (#609), ohne `HEAD_SHA` von Hand zu übertragen. `render_view.py notes-review --next` bzw. `--entry <id>` füllt dieselbe Vorlage mit genau einem Eintrag (`REVIEW_COUNT_TEXT` = „Eintrag 8 von 21 · noch 14 offen“); nach der Antwort ruft der Assistent im Einzelmodus ohne Rückfrage `--next` erneut auf. Autorenentscheidungen mit Varianten: `E_QUESTION` enthält weiter „Variante k: …“ in einer Zeile, die Antwort `variante N` speichert `hinweise.py decide . <id> --variant N`; ab UI 0.70.0 hat jede Variante einen Knopf (`E_VARIANTS_JSON`), der `notes_review.decide` mit `decision` = `geändert`, `variant` (ab 1) und `new` sendet. **Themen (#570):** Hat die Durchsicht `themen`, zeigt die Stufe „Thema i von n: <Titel>“ alle offenen Einträge des Themas gemeinsam.

Jede Antwort sendet einzeln `notes_review.decide`; „Frage stellen“ (nur Autorenentscheidungen, ab UI 0.68.0) sendet `notes_review.ask` und entscheidet nichts; „Umsetzen prüfen“ sendet `notes_review.plan`. Das Widget ändert selbst nichts.

**Vorschlag, Rückfragen und Speichern (#609):** Hat eine Autorenentscheidung keinen Vorschlag, formuliert der Assistent ihn **vor** der Karte: `hinweise.py propose . <id> --new "<Text>" [--variant "<Text>" …]` schreibt `neu` (und `varianten`) mit `vorschlag_von: assistent`; die Karte zeigt ihn als „Vorschlag · vom Assistenten“, und „Übernehmen“ speichert genau diesen Text. Kommt `geändert` mit einem Text, der mit einem Fragezeichen endet (Rückfrage über „Anders formulieren“), **speichert nichts**: `decide` (Skript `hinweise.py`) lehnt ihn ab (außer mit `--as-text`); der Assistent beantwortet die Frage und zeigt dieselbe Karte erneut (`hinweise.py ask . <id> [--repo <owner/repo>]`). **Streichung (#615):** `hinweise.py propose . <id> --delete` bzw. `hinweise.py decide . <id> --decision streichen` setzt `streichen: true`; `E_NEW` zeigt dann „(entfällt)“, „Übernehmen“ speichert die Streichung, `plan`/`apply` entfernen den alten Wortlaut. Nach der Entscheidung gibt `hinweise.py decide … --next-card --repo <owner/repo>` die nächste Karte aus, ohne den `HEAD_SHA` von Hand zu übertragen. Gespeichert (committet) wird je abgeschlossenem Thema bzw. Runde und mit dem Befehl „Zwischenstand speichern“ (`hinweise.py checkpoint .`), nicht je Antwort (`START.md`, „Speichern der Durchsicht“).

### `chronologie-vorschlag.html`

Auswahl der Chronologie-Vorschläge (#364, ab UI 0.59.0; Art `chronology`, `render_view.py analysis-suggest --draft analysis/chronology/run-NNN.json`). Einträge aus Unterlagen, nie aus dem Manuskript; „schon da“ ist nicht vorgewählt.

| Platzhalter | Inhalt |
|---|---|
| `KIND`, `RUN_ID`, `RUN_TEXT` | `chronology`, Lauf, „Hintergrundlauf NNN vom …“ bzw. „Chat-Lauf …“ |
| `SUGGEST_COUNT_TEXT` | „N Vorschläge · M schon da“ |
| Block `ENTRIES`: `C_IDX`, `C_N`, `C_DATE`, `C_LABEL`, `C_STATUS`, `C_WHAT`, `C_SOURCE`, `C_QUOTE`, `C_NOTE`, `C_EXISTING`, `C_SAME` | Nummer in der Vorschlagsdatei und laufende Nummer, Datum bzw. Beginn (änderbar), Anzeige des Datums, Belegstand (`documented`, `reported`, `uncertain`; wählbar auch `invented`), was geschah, Fundort, Zitat, Notiz („Figur nicht angelegt: …“), ID eines gleichen vorhandenen Eintrags, Nummer des Vorschlags zum selben Ereignis |

Übernehmen sendet `analysis.apply` mit `kind: chronology`, `run` und `choices` `{index, what, status}` (`date` nur, wenn geändert); Verwerfen `form.cancel`.

### `zeitleiste-vorschlag.html`

Auswahl „Zeitleiste“ aus einem Hintergrundlauf (#124, Art `timeline`; `render_view.py analysis-suggest --draft analysis/timeline/run-NNN.json`). Eine Chat-Rückgabe (`docs/CHAT-ANALYSEN.md`) hat ab #353 einen eigenen Lauf; `--draft` darf auch die Datei aus `analysis/chat-returns/` sein. Ein solcher Lauf hat keine Auffälligkeiten.

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
| `SUGGEST_COUNT_TEXT`, `RULES_TEXT` | „N Hinweise“ und die Regeln (Satzlänge, Wiederholungen, Satzanfänge, Füllwörter, KI-typische Muster) aus `analyze.py` |
| Block `SUGGESTIONS`: `S_IDX`, `S_WHERE`, `S_KIND`, `S_KIND_TEXT`, `S_TEXT`, `S_QUOTE` | je Hinweis: Nummer, Abschnitt, `long_sentence`/`repetition`/`same_start`/`filler`/`ai_pattern` (#305) bzw. mit LanguageTool (#280) `spelling`/`grammar`/`punctuation`/`typography` und deutsch, Hinweis, Fundstelle |

### `import-vorschau.html`

Gliederung eines Manuskript-Imports prüfen (#124, `render_view.py import-preview`; Daten aus `import/proposal.json` und `import/import.yml`).

| Platzhalter | Quelle |
|---|---|
| `IMPORT_TITLE`, `IMPORT_AUTHOR`, `IMPORT_FORMAT` | `title`, `author` (Dokument-Eigenschaften bzw. einzelne oberste Überschrift), `format` |
| `STATS_TEXT`, `LOSSLESS` | „N Kapitel, M Abschnitte, K Teile von Vor- und Nachspann · X von Y Wörtern übernommen“; `LOSSLESS` = `1`, wenn die Wortzahl der Umwandlung entspricht |
| `KEEP_TEXT` | Aufbewahrung des Originals deutsch: für neue Importe „bis zum ausdrücklichen Löschauftrag“ (D21); ältere Importe zeigen ihre frühere Frist („bis zur ersten Auflage“, „30 Tage“, „90 Tage“, „dauerhaft“), die nichts löscht |
| `KINDS_TEXT` | Arten von Vor- und Nachspann als `kind=Name`, kommagetrennt (Auswahl „ist Teil …“) |
| Block `WARNINGS`: `W_TEXT` | Hinweise der Umwandlung (PDF, Tabellen, Fußnoten, Bilder, sehr lange Abschnitte, keine Gliederung) |
| `NO_STRUCTURE` | `1`, wenn das Dokument keine Gliederung hat (`structure: none`, ein Kapitel) und kein offener KI-Vorschlag da ist; dann der Knopf „Gliederung mit KI vorschlagen“ (`import.outline.start`) |
| `OUTLINE_TEXT` | offener KI-Vorschlag in `import/outline.json`: „KI-Vorschlag für die Gliederung liegt bereit: N Kapitel, M Abschnitte“ mit „Ansehen“ (`import.outline.open`); sonst weglassen |
| Block `PARTS`: `P_IDX`, `P_KIND`, `P_AREA`, `P_LABEL`, `P_TITLE`, `P_WORDS` | Teile von Vor- und Nachspann: Nummer im Vorschlag, Art, `front`/`back`, Name der Art, Überschrift, Wörter |
| Block `ROWS`: `R_TYPE`, `R_CHAPTER`, `R_SECTION`, `R_LABEL`, `R_TITLE`, `R_WORDS`, `R_COUNT`, `R_SCENES`, `R_LONG` | je Kapitel (`chapter`, mit „N Abschnitte“) und darunter je Abschnitt (`section`, Szenen wenn mehr als eine, `R_LONG` = `1` über 4000 Wörter) |

### `gliederung-vorschlag.html`

KI-Vorschlag für die Gliederung beim Import (#124, `render_view.py import-outline`; Daten aus `import/outline.json`). Nur für Manuskripte ohne Gliederung.

| Platzhalter | Quelle |
|---|---|
| `RUN_ID`, `RUN_TEXT` | `run` (`outline-NNN`) und „Vorschlag NNN vom TT.MM.JJJJ (Modell)“ |
| `STATS_TEXT` | „N Kapitel, M Abschnitte aus K Absätzen · D Anfänge ohne wörtliche Fundstelle verworfen“ |
| `PARTIAL_TEXT` | nur bei sehr langen Manuskripten (`full_text: false`): „… die KI hat je Absatz nur den Anfang gelesen.“ |
| Block `ROWS`: `O_TYPE`, `O_CHAPTER`, `O_SECTION`, `O_LABEL`, `O_TITLE`, `O_START`, `O_WORDS`, `O_COUNT`, `O_QUOTE`, `O_REASON` | je Kapitel (`chapter`, mit „N Abschnitte“) und darunter je Abschnitt (`section`): Nummern, „Kapitel N“ bzw. „N.M“, Titel, erster Absatz (ab 1), Wörter, Anfang (wörtlich geprüft), Begründung der KI (beim ersten Abschnitt eines Kapitels leer) |

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
| `RESEARCH`, `GHOSTWRITING` | `1`, wenn Recherche bzw. KI-Entwurf für die Art erlaubt ist (`MATTER_RESEARCH`, `MATTER_GHOSTWRITING`) |
| `PERSONAL_NOTE` | Hinweis bei Widmung und Danksagung, dass der Autor den Text selbst schreibt; sonst leer |

### `ki-angabe.html`

Formular „KI-Angabe im Buch“ (`render_view.py ai-disclosure`, #78; `scripts/ai_disclosure.py`).

| Platzhalter | Quelle |
|---|---|
| `AI_MODE`, `AI_PLACEMENT`, `AI_NAME_SERVICES`, `AI_TEXT` | `ai_disclosure.mode` (`none` wird zu `functions`), Ort (`placement`; ohne Wahl bei ausgeschaltetem Impressum `page`), `.name_services` (`true`/`false`), `.text` = bestätigter Zusatz (Vorgaben: functions, imprint, false, leer) |
| `AI_MINIMUM` | Mindestangabe mit Autor (`minimum`, #356); steht immer im Buch |
| `AI_FUNCTIONS` | Aufzählung im Mustersatz, kommagetrennt (`functions`) |
| `AI_USED_TEXT` | laut Lauf-Dateien genutzte Aufgaben und Dienste (`usage`), z. B. „Recherche: Perplexity · Textentwürfe: Anthropic Claude“; leer = keine Läufe |
| `AI_PROPOSAL_SHORT`, `AI_PROPOSAL_SHORT_NAMED`, `AI_PROPOSAL_DETAILED`, `AI_PROPOSAL_DETAILED_NAMED` | `suggest`: Zusatz kurz/ausführlich ohne bzw. mit Dienstnamen; leer = keine Läufe |
| `AI_PLACES_MISSING` | Orte ohne Grundlage, kommagetrennt: `foreword`/`afterword` ohne Vorwort bzw. Nachwort, `imprint` bei ausgeschaltetem Impressum |
| `AI_LEGAL_HINT` | `LEGAL_HINT` aus `scripts/ai_disclosure.py` |

### `ausgabeoptionen.html`

Formular „Ausgabeoptionen“ (`render_view.py output`, #68). Ab UI 0.48.0 mit „Vorderseite im PDF“ (`typesetting.pdf_cover`) und „Eigene Vorderseite“ (`cover.front`, #324); ab UI 0.49.0 mit „Gestaltung der Titelseite“ (`title_style`), „Kennzeichnung im Probedruck“ (`proof_mark`, #310) und dem Format Broschüre (`booklet`). Damit sind alle Felder von `typesetting` im Formular. Ab UI 0.53.0 zeigt unter beiden Auswahlen ein kleines Vorschaubild den gewählten Wert (#310); neue Platzhalter gibt es dafür nicht. Ab UI 0.50.0 zeigen Projektübersicht, Kapitelansicht und Abschnittsformular die Prüf-Tags (#331, `data-gw-checks`).

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
| `LIBRARY_NAME` | `owner/repo` (`--repo`; ohne Angabe aus `GITHUB_REPOSITORY` bzw. `git remote origin`, bei der Seite „Daten“ auch aus `repo.full_name` in `--github`; sonst „unbekanntes Repository“, nie das Hauptrepository, #134) |
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
| `APPROVAL_TITLE`, `APPROVAL_BUTTON`, `APPROVAL_EFFECT` | Überschrift, Knopf und Satz zur Wirkung, je nach Art (Muster: `render_view.py approval-…`). Der Knopf nennt die Aktion: „Abschließen“/„Wieder öffnen“ bei Abschnitt, Kapitel und Vor-/Nachspann, „Schreiben erlauben“/„Schreiben sperren“ beim Schreiben; „Freigeben“/„Zurücknehmen“ nur beim Bild (#292) |
| `TARGET_ID`, `TARGET_LABEL` | Abschnitts- bzw. Kapitel-ID und „Abschnitt N.M „Titel““ bzw. „Kapitel N „Titel““ |
| `HEAD_SHA`, `HEAD_SHORT` | gelesener Stand, voll und mit 7 Zeichen; er landet als `commit` in `approvals.yml` |
| Block `CHECKS`: `CHECK_STATE`, `CHECK_TEXT` | Prüfpunkte nach `START.md`, „Freigaben“, Schritt 2: `ok`, `warn` oder `block`; bei `block` ist Bestätigen gesperrt |

### `aenderungen-uebernehmen.html`

| Platzhalter | Quelle |
|---|---|
| `PENDING_TEXT`, `PENDING_PR` | wie in der Projektübersicht |
| `BOOK_BRANCH`, `WORK_BRANCH` | Buch-Branch und Arbeits-Branch (`ghostwriter/<buch-branch>`) |
| `HEAD_SHA` | letzter Commit des Arbeits-Branchs; `gw.js` schickt ihn mit `changes.merge` zurück |
| Block `CHANGES`: `CHANGE_MESSAGE`, `CHANGE_DATE`, `CHANGE_SHA` | höchstens fünf neueste Benutzer-Commits des Pull Requests, innerhalb dieser Auswahl älteste zuerst: erste Zeile der Commit-Nachricht, Datum `TT.MM.JJJJ, HH:MM` in Ortszeit (siehe „Offene Änderungen“), Commit mit 7 Zeichen |

Bei mehr als fünf Änderungen beginnt `CHANGES` mit einer Zusammenfassungszeile: Zahl der älteren Änderungen und Hinweis „Alle Änderungen anzeigen“ (`changes-merge --alle`); Datum und Commit bleiben dort leer. `--alle` zeigt alle Benutzer-Commits, älteste zuerst. Gesamtzahl, Ziel, Änderungspaket und `HEAD_SHA` bleiben vom Kürzen unberührt; die Bestätigung betrifft das ganze Paket. Auf ausdrücklichen Wunsch die vollständige Ansicht mit frischen Daten öffnen, sonst auch im Begleittext keine volle Commitliste. Text und Widget verwenden dieselbe Auswahl (Deutsch/Englisch).

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

### `warteschlange.html`

Hintergrund-Warteschlange (#478, ab UI 0.67.0; `render_view.py queue`, `--text` als Textfassung, Deutsch und Englisch). Gefüllt von `queue_view.widget_values()`; die Textfassung ist `queue_view.text_view()`. Liest nur; die Reihenfolge folgt festen Regeln (`docs/DATA-MODEL.md`, „Hintergrund-Warteschlange“).

| Platzhalter | Quelle |
|---|---|
| `QUEUE_BOOK`, `QUEUE_COUNT_TEXT`, `QUEUE_EMPTY` | `project.title_short` bzw. `title`, „N Aufträge“ bzw. „keine Aufträge“, `1` bei leerer Warteschlange |
| Block `PENDING` (wartende Aufträge): `J_TITLE`, `J_DETAIL`, `J_STATE_TEXT`, `J_WHEN_TEXT`, `J_PRIORITY_TEXT`, `J_BLOCKED_TEXT`, `J_NOTE`, `J_PRIO_DISABLED`, `J_ARGS` | Art und Abschnitt („Recherche · 2.1 Titel“), Frage bzw. Angaben der Art, Zustand (wartet, wartet auf Bestätigung wegen Budget, wartet auf einen anderen Auftrag), „eingereicht …“, „vorgezogen“ (sonst leer), „Erst nach <Pfad>“ (sonst leer), Hinweis bei Ring in `after`, `disabled` bei schon vorgezogenen, JSON `{"request":"<Pfad im Buch>"}` |
| Block `FAILED`: `J_TITLE`, `J_DETAIL`, `J_WHEN_TEXT`, `J_ARGS` | Auftrag mit `error`, Grund, „fehlgeschlagen …“ |
| Block `DONE`: `J_TITLE`, `J_DETAIL` | Rechercheläufe mit `request:` im Kopf, noch nicht im Buch-Branch (nur auf dem Arbeits-Branch erkennbar) |

„Vorziehen“ sendet `queue.prioritize`, „Abbrechen“ (mit Rückfrage) `queue.cancel`, beide mit `request`; „Erneut versuchen“ bei fehlgeschlagenen Aufträgen (ab UI 0.69.0, #596) sendet `queue.retry` mit `request`.

### `anekdoten.html`

Anekdoten des Buchs und seiner Reihe (#643, UI 0.79.0; `render_view.py anecdotes [<Abschnitt>]`, `START.md`, „Anekdoten“). Nur für Eigentümer und Bearbeiter (#455); Lesern nicht zeigen. Der **Originaltext erscheint nie im Widget**; „Anzeigen“ holt ihn im Chat (`anekdoten.py . show <id>`).

| Platzhalter | Quelle |
|---|---|
| `ANEC_MODE` | `list` (alle) oder `section` (mit Abschnitt: passende freie und für ihn eingeplante, sortiert wie `anekdoten.py suggest`) |
| `ANEC_COUNT_TEXT` | „5 Anekdoten · 3 frei · 1 eingeplant · 1 verwendet“ (immer über alle) |
| `ANEC_SECTION_ID`, `ANEC_SECTION_NUMBER`, `ANEC_SECTION_TITLE` | Abschnitt im Modus `section` (Eingabe `1.2` oder `sec-…`) |
| Block `ANECDOTES`: `A_ID`, `A_TITLE`, `A_STATE`, `A_STATE_TEXT`, `A_PLANNED_TEXT`, `A_TOPICS_TEXT`, `A_SERIES_TEXT`, `A_USES_TEXT`, `A_MATCH_TEXT` | je Eintrag aus `anekdoten.entries`: Zustand `frei` \| `eingeplant` \| `verwendet`, „eingeplant für 1.2“, Themen, „Reihe <ser-id>“, „verwendet in 2.1 (anonymisiert)“, im Modus `section` „Passt: …“ (gemeinsame Wörter) |
| Block `HINTS`: `H_TEXT` | `anekdoten.py . check` (Original ohne Einverständnisvermerk) |

Aktionen: `anecdote.capture`, `anecdote.show`, `anecdote.suggest`, `anecdote.plan`, `anecdote.use` (siehe unten). Der Abschnitt kommt als Nummer (`1.2`); `anekdoten.py` nimmt Nummer oder Kennung.

### `analyse-einstellungen.html`

Formular „Analyse-Einstellungen“ (`render_view.py analysis-settings`, #299, ab UI 0.47.0) für den Block `analysis`.

| Platzhalter | Quelle |
|---|---|
| `ANALYSIS_PROVIDER`, `ANALYSIS_MODEL`, `ANALYSIS_MERGE_MODEL` | `analysis.provider`, `.model`, `.merge_model`; leer = Vorgabe |
| `DEFAULT_MODEL_ANTHROPIC`, `DEFAULT_MERGE_ANTHROPIC`, `DEFAULT_MODEL_OPENAI`, `DEFAULT_MERGE_OPENAI` | Vorgaben der Anbieter aus `scripts/analyze.py` (`PROVIDERS`) |
| `PRICE_INPUT`, `PRICE_OUTPUT`, `PARALLEL` | `analysis.price_input_per_mtok`, `.price_output_per_mtok`, `.parallel`; leer = keine Preise bzw. Vorgabe 4 |
| `CURRENCY` | Projektwährung (`EUR`) |
| `LT_LANGUAGE`, `LT_LANGUAGE_DEFAULT` | `analysis.languagetool.language`; Vorgabe aus `project.language` (`analyze.lt_language`, z. B. `de-DE`) |
| `LT_WORDS`, `LT_RULES` | `analysis.languagetool.words` bzw. `.disabled_rules`, je Zeile ein Eintrag |

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
| `LIMIT_SUMMARY` | Stand der Limits aus `scripts/limits.py` (`limit_summary`), z. B. „KI-Budget 62 % übrig (3,80 von 10,00 € verbraucht).“ oder „Keine Limits eingestellt.“ |
| `AI_DISCLOSURE_TEXT` | KI-Angabe kurz, z. B. „kurz, im Impressum“, „nur Mindestangabe, im Impressum“ (`ai_disc_text`) |
| `GW_VERSION_TEXT` | „Installiert: GhostWriter <version>“ aus `ghostwriter-manifest.yml`, dazu „ · zuletzt aktualisiert am TT.MM.JJJJ“ aus `.ghostwriter/update.yml` (`updated_at`), falls vorhanden |
| `GW_UPDATE_HINT` | nur wenn `.ghostwriter/update.yml` `skipped_workflows` enthält: Hinweis auf das Secret `GHOSTWRITER_UPDATE_TOKEN` (`docs/UPDATES.md`); sonst leer |

## Textfassung ohne Widgets

Im Modus „Nur Text“ (siehe „Darstellungsmodus“) bekommt der Chat dieselben Inhalte als Markdown. **Dort nie HTML, `GW.render` oder Widget-Code ausgeben.** Muster erzeugt `scripts/render_view.py … --text`; jede Ansicht und jedes Formular hat eine Textfassung.

Gestaltung:

- **Überschrift** `###` mit Symbol: 📘 Projekt, 📖 Kapitel, ✏️ Abschnitt, 📜 Vor- und Nachspann, 📝 Bearbeiten, ➕ Anlegen, ↕️ Reihenfolge, ⚙️ Einstellungen, 📚 Auflage bzw. Bücherregal, 📗 Neues Buch, 🗂️ Daten, 🔀 Buchänderungen übernehmen, ✅ Freigeben, ↩️ Freigabe zurücknehmen, 🤖 KI-Dienste.
- **Status** deutsch mit Symbol: ⚪ geplant, 🔎 Recherche, 💡 Ideensammlung, 🟦 bereit zum Schreiben, ✏️ Schreiben bzw. in Arbeit, 🔁 Überarbeitung, 🔍 Faktencheck bzw. Durchsicht, 🟡 bereit zum Abschluss, 🔒 abgeschlossen (#292; technisch `approved`).
- **Marker** als Symbol mit Anzahl: 💬 Anekdote, 📚 Quelle, 🩺 Medizin, ⚖️ Recht; darunter klein die Legende.
- **Tabellen** für Listen und Felder; Zahlen und Kosten rechtsbündig.
- **Aktionen** am Ende nach einer Trennlinie als Kürzel in Inline-Code: Zahlen öffnen Kapitel (`2`) oder Abschnitte (`2.4`), Buchstaben lösen Aktionen aus.
- **Formulare** zeigen die aktuellen Werte als Tabelle; geantwortet wird mit `Feld: neuer Wert`, je Zeile ein Feld. `X` bricht ab.

| Ansicht | Kürzel |
|---|---|
| Bücherregal | `1`–`N` Buch öffnen · `S1`–`SN` Serie öffnen · `N` Neues Buch · `NS` Neue Serie · `D` Daten |
| Serie | `1`–`N` Band öffnen · `H` Band hinzufügen · `R` Reihenfolge ändern · `ENT` Band entfernen · `NB` Neues Buch in dieser Serie · `B` Serie bearbeiten · `Ü` Bücherregal |
| Daten | `Ü` Bücherregal · `U` GhostWriter aktualisieren (nur wenn dahinter) |
| Figuren | Name einer Figur öffnet sie · `+ Name` legt eine Figur an (optional `Rolle: Nebenfigur`) · `Ü` Übersicht |
| Projektübersicht, Kapitel, Abschnitt, Teil, Figuren, Serie | zusätzlich `FV` 👤 Figuren aus dem Text vorschlagen |
| Projektübersicht | `FI` Figuren · `L` Bücherregal (nur ab zwei Büchern) · `S` Serie (nur bei einem Band einer Serie) · `1`–`N` Kapitel öffnen (📖) · `B1`–`BN` Kapitel bearbeiten (✎ in jeder Kapitelzeile, wie der Bearbeiten-Knopf der Kapitelansicht) · `N.M` zuletzt bearbeiteter Abschnitt · Titel eines Teils von Vor- oder Nachspann öffnet ihn (nur vorhandene) · `M` Buchänderungen übernehmen (nur bei offenen Änderungen) · `D` KI-Dienste · `P` Projektdaten · `N` Neues Kapitel · `R` Kapitelreihenfolge · `V` Vor- und Nachspann · `A` Neue Auflage · `E` Einstellungen |
| Vor- und Nachspann | Titel eines Teils öffnet ihn · `+ Widmung` usw. legt einen fehlenden Teil an · `Ü` Übersicht |
| Glossar | `+ Begriff: Erklärung` aufnehmen · `Begriff: neue Erklärung` ändern · `- Begriff` entfernen · `VB` Begriffe vorschlagen · `F` Titel, Ziel, Einleitung · `SE`/`SP` Schreiben erlauben/sperren, `AB`/`WO` abschließen/wieder öffnen · `RS` Recherche je Begriff · `Ü` Übersicht |
| Teil des Vor- oder Nachspanns | `T` Text ändern · `F` Titel und Ziel (Vorwort, Nachwort: dazu Verfasser, Ort und Datum) · `SE`/`SP` Schreiben erlauben bzw. sperren · `AB`/`WO` abschließen bzw. wieder öffnen · `RS`, `GS` Recherche bzw. KI-Entwurf sofort (Vorwort, Prolog, Epilog, Nachwort) · `Ü` Übersicht |
| Kapitelansicht | `N.1`–`N.M` Abschnitt öffnen · `KU` Kapitel überarbeiten (nur bei vollständigem Manuskript) · `B` Kapitel bearbeiten · `Z` Ziel, Kurzbeschreibung, Kapitelrecherche · `N` Neuer Abschnitt · `R` Abschnittsreihenfolge · `AK` Kapitel abschließen (nur wenn möglich) · `Ü` Übersicht |
| Abschnitt | `T` Text ändern (geänderten Text schicken) · `F` Ziel, Kurzbeschreibung, Faktencheck · `SE`/`SP` Schreiben erlauben bzw. sperren · `AB`/`WO` Abschnitt abschließen bzw. wieder öffnen · `RS` Recherche sofort · `GS` KI-Entwurf sofort · `N.M` vorheriger/nächster Abschnitt · `K` Zum Kapitel |
| Projektübersicht, Kapitel, Abschnitt | zusätzlich `AC` Auschecken zum Gegenlesen (Aktion `checkout.start`, Befehl `Auschecken Kapitel 3–5` bzw. `Auschecken Buch`), `EC` Einchecken (`checkout.return`), `CB` Checkout beenden (`checkout.end`, nur mit Bestätigung), `ME` Material einbringen (`material.add`); Skills `ghostwriter-gegenlesen` und `ghostwriter-material` (#572–#574) |
| Formulare | `Feld: Wert` je Zeile · Ausgabeoptionen: `Ränder: klassisch`, `Formate: PDF, EPUB`, `ISBN E-Book: …` · KI-Angabe: `Angabe: kurz`, `Ort: Nachwort`, `Funktionen: Rechtschreibung, Stil`, `Dienste nennen: ja`, `Text: …`, `OK` übernimmt den Vorschlag · Reihenfolge als Nummernliste · Auflage: `OK` übernimmt den Vorschlag · Buchänderungen übernehmen: `OK` übernimmt · Freigabe: `OK` bestätigt · Neues Buch: `Titel: …`, `Kurztitel: …`, `Autor: …` · Auswahl: `1b, 2a` (Frage und Buchstabe; bei Mehrfachauswahl `2a c`), eigene Antwort `1: Text`, `S` überspringt (nur wenn angeboten) · Kapitelrecherche: `Ziel: …`, `Kurzbeschreibung: …`, `Frage: …`, `Schwerpunkte: …`, `Aufgabe: Ziel|Abschnitte|Kurzbeschreibung|keine`, `Vorher: 0–3`, `Nachher: 0–3`, `VZ`/`VK` Vorschlag übernehmen, `AS 1, 3` vorgeschlagene Abschnitte anlegen · KI-Dienste: `+ id`, `- id`, `Aufgabe: id` · `X` bricht ab |

Die früheren Kürzel `FS`, `FA` und `FK` werden weiter verstanden (#292).

Ein Kürzel entspricht dem Klick auf den gleichnamigen Knopf; es gelten dieselbe Aktion, dieselben Statuszeilen und dieselbe Ausgangsansicht danach.

Zusätzlich gelten überall die ausgeschriebenen Befehle aus `START.md`, Abschnitt 0, „Befehle“ (`Start`, `Übersicht`, `Kapitel 3`, `Hilfe` …).

## Nachrichtenformat

Jede Vorlage schickt eine Nachricht aus einer lesbaren Zeile und den festen Daten. Der Chat zeigt die Nachricht vollständig an. Seit ghostwriter-ui 0.71.0 (#642) steht darin **kein Codeblock** mehr: Die Claude-App meldete Nachrichten mit einem Block `gw` als möglicherweise schädlichen Code.

Aufbau, immer in dieser Reihenfolge:

1. **Klartextzeile** für Menschen („Abschnitt 2.4 „Die Scham, die wir mitbringen“ bearbeiten“).
2. **Kennzeile** als Inline-Code: `gw:<aktion>`, dahinter alle kurzen Werte (Zahl, `true`/`false` oder Text ohne Leerzeichen und Backtick, höchstens 80 Zeichen) als `schlüssel=wert`, getrennt durch Leerzeichen.
3. **Feldzeilen** für alle übrigen Werte (Freitext, Leerzeichen, leer, länger als 80 Zeichen), je Feld eine Zeile `feld: wert`. Mehrzeilige Werte setzen jede Folgezeile mit zwei Leerzeichen eingerückt fort. Ein leerer Wert steht als `feld:`. Backtick und Backslash im Wert sind mit einem Backslash maskiert (`\``, `\\`); beim Lesen wieder zurücknehmen. Zahlen, Listen und Objekte, die nicht in die Kennzeile passen, stehen als `feld (JSON): <JSON in einer Zeile>`.

Die Web-App und die gemeinsame App-Laufzeit lesen diese Feldzeilen einschließlich leerer Werte, Einrückung, Maskierung und JSON. Alte `gw`-JSON-Blöcke bleiben lesbar. Ein unlesbares JSON-Feld stoppt die Aktion, statt mit unvollständigen Formulardaten zu speichern.

````text
Eintrag e-033: anders formulieren

`gw:notes_review.decide file=editorial/durchsicht-2026-11-20.yml entry=e-033 decision=geändert`
new: Die Überfahrt von Trogir nach Triest dauerte
  zwei Tage und eine Nacht.
````

`expected_head_sha` steht auf **12 Zeichen** gekürzt in der Kennzeile; für den Abgleich mit dem Head genügt der Anfang (Präfix). Große Datenmengen gehören nicht in die Nachricht, sie bleiben im Repository (die Nachricht nennt nur Pfad bzw. ID). Die Daten werden nicht kodiert oder komprimiert; der Benutzer soll lesen können, was das Widget in seinem Namen schickt.

Welche Werte in die Kennzeile und welche in Feldzeilen kommen, entscheidet `GW.message` in `ghostwriter-ui` selbst. Kurzform `gw:a k=v` entspricht `{"action":"a","k":"v"}`; Zahlen und `true`/`false` werden als solche gelesen. Der Assistent wertet die Daten aus; die Zeile darüber ist für Menschen. Freie Eingaben ohne Daten bleiben erlaubt.

**Übergang:** Das frühere Format mit einem Block `gw` und JSON (` ```gw` … ` ``` `) wird weiter gelesen, etwa von Widgets älterer Versionen (UI bis 0.70.0, Claude-Web-App). Neue Widgets senden es nicht mehr.

| Aktion | Daten | Bedeutung | Antwort des Assistenten | Endpunkt in `docs/API-CONTRACT.md` (Weg B) |
|---|---|---|---|---|
| `view.project` | – | Projektübersicht zeigen | Vorlage `projektuebersicht` (`render_view.py project`) | `GET /v1/projects/{owner}/{repo}` |
| `view.chapter` | `chapter_id` | Kapitelansicht zeigen, dazu die Lesefassung als Datei (`assemble.py … reading N`, START.md „Lesefassung“, #289) | Vorlage `kapitelansicht` (`render_view.py chapter N`) | `GET /v1/projects/{owner}/{repo}` |
| `view.section` | `section_id` | Abschnittsformular zeigen, dazu die Lesefassung als Datei (`assemble.py … reading N.M`, #289) | Vorlage `abschnitt-bearbeiten` (`render_view.py section N.M`; Textfassung mit Lesefassung: `--text --ohne-manuskript`; ungespeicherte Abschnittsvorschläge: bestehendes `assemble.py reading N.M --draft-file`, gleiche Vorschaudatei, Dateipanel nach START.md „Lesefassung“, #316) | `GET /v1/projects/{owner}/{repo}` |
| `view.matter` | `matter_id` (leer = alle Teile) | Teil von Vor- oder Nachspann zeigen bzw. die Liste „Vor- und Nachspann“ (#57) | Vorlage `teil-bearbeiten` (`render_view.py matter <teil>`) bzw. `vor-nachspann` (`render_view.py matter`) | `GET /v1/projects/{owner}/{repo}` |
| `view.images` | `section_id` (auch `mat-…`) | Bilder eines Abschnitts zeigen (#54) | Vorlage `bilder` (`render_view.py images <N.M|id>`) | `GET /v1/projects/{owner}/{repo}` |
| `image.prompt` | `section_id`, `scene`, `characters` (optional) | Bild-Auftrag zusammensetzen | `python scripts/images.py . prompt …` (bei Diagramm, Karte, Schaubild `--kind graphic --labels …`); Prompt zeigen, dann im Chat erzeugen oder als „Auftrag kopieren“ ausgeben (`START.md`, „Illustrationen“); nichts schreiben | – |
| `image.add` | `section_id`, `caption`, `alt`, `source`, `provider`, `prompt`, Datei als Anhang, `expected_head_sha` | Bild ablegen | `python scripts/images.py . add …`, ein Commit; danach die Bilder des Abschnitts | `POST …/sections/{section_id}/images` |
| `image.layout` | `image_id`, `position` (`top-left` … `bottom-right` oder `text`), `width` (10–100) | Lage und Breite eines Bildes speichern (#54) | `python scripts/images.py . layout <image_id> --position … --width …`, ein Commit; danach die Bilder des Abschnitts | – |
| `image.place` | `image_id`, `section_id` | Bild in den Text setzen | nachfragen, wohin (nach welchem Absatz), dann mit Schreibfreigabe die Zeile `![](bild:img-…)` als eigenen Absatz einfügen, Commit wie `section.update`; ohne Schreibfreigabe zuerst die Freigabe anbieten | `PUT …/sections/{section_id}/manuscript` |
| `view.characters` | – | Liste der Figuren zeigen (#53, Befehl `Figuren`) | Vorlage `figuren` (`render_view.py characters`) | `GET /v1/projects/{owner}/{repo}` |
| `view.character` | `character_id` | Formular einer Figur zeigen | Vorlage `figur-bearbeiten` (`render_view.py characters <id>`) | `GET /v1/projects/{owner}/{repo}` |
| `character.create` | `name`, `role`, `expected_head_sha` | Figur anlegen | `python scripts/characters.py . add "<Name>" --role <role>`, Commit nach `START.md`, „Figuren“; danach das Formular der neuen Figur | `POST …/characters` |
| `character.update` | `character_id`, `name`, `role`, `short`, `age`, `appearance`, `traits` (Liste), `voice`, `visual`, `relations` (Liste `{to, kind}`), `description`, `notes`, `expected_head_sha` | Figur speichern | `python scripts/characters.py . update <id> '<json>'`, ein Commit; danach das Formular | `PATCH …/characters/{character_id}` |
| `matter.create` | `kind` (`dedication` \| `foreword` \| `prologue` \| `epilogue` \| `afterword` \| `glossary` \| `acknowledgments`), `title` (optional), `expected_head_sha` | Teil anlegen | `python scripts/matter.py . add <art> [--title …]`, Commit nach `START.md`, „Vor- und Nachspann“; danach der neue Teil | `POST …/matter` |
| `matter.update` | `matter_id`, `title`, `goal`, `manuscript`, bei Vorwort und Nachwort `byline`, `place_date`, `expected_head_sha` (nie `approvals`) | Teil speichern | Datei in `matter/` (und bei neuem Titel `ghostwriter.yml`) schreiben, danach der Teil | `PATCH …/matter/{matter_id}` |
| `character.suggest` | `scope` (`book`, Kapitelnummer, `N.M`, `mat-…` bzw. `ser-…`) | Figuren aus dem Text vorschlagen | `python scripts/characters.py . scan <scope>` (Serie: `scripts/series.py . scan <ser-id>`), Teil für Teil lesen, Vorschläge als JSON (`START.md`, „Figuren“, Schritt 6), dann Vorlage `figuren-vorschlag` (`render_view.py character-suggest --draft …`) | – |
| `import.edit` | `ops` (Liste, siehe `scripts/import_book.py`: `rename_chapter`, `rename_section`, `split_scenes`, `merge_sections`, `merge_chapters`, `split_chapter`, `to_matter`, `to_chapter`, `outline`, `discard_outline`) | Gliederung des Import-Vorschlags ändern | Action „Manuskript importieren“ mit `step: edit` und `ops` (bzw. `import_book.py . edit`), danach die Vorschau neu | `PATCH /v1/projects/{owner}/{repo}/import` |
| `import.outline.start` | – | Gliederung mit KI vorschlagen (nur ohne Gliederung) | vorher den Schlüssel prüfen (#445): Melden `secrets` in `ghostwriter-index.json` bzw. `library.json` `ANTHROPIC_API_KEY` und `OPENAI_API_KEY` als fehlend, den Lauf nicht starten, sondern auf die Seite „Daten“ und `KEYS_GUIDE_URL` hinweisen (ohne Schlüssel bricht der Lauf mit Fehler ab). Dann `python scripts/import_book.py . outline --plan` zeigen (Absätze, Tokens, Kosten) und die Limits; in einem Satz sagen, dass der Text an den KI-Anbieter geht. Nach einem Ja die Action „Manuskript importieren“ mit `step: outline` (unter 10 % Budget nur mit `confirm_low_budget`); danach die Vorschau mit dem Hinweis | `POST /v1/projects/{owner}/{repo}/import/outline` |
| `import.outline.open` | – | KI-Vorschlag für die Gliederung ansehen | Vorlage `gliederung-vorschlag` (`render_view.py import-outline`) | – |
| `import.outline.apply` | `chapters` (Liste `{title, start, sections: [{title, start}]}`, Absatznummern ab 1) | KI-Vorschlag (mit den Änderungen) übernehmen | Action mit `step: edit` und `ops` = `[{"op": "outline", "chapters": …}]` (bzw. `import_book.py . edit`), danach die Vorschau neu. „Verwerfen“ (`form.cancel` mit `form: import.outline.apply`): `ops` = `[{"op": "discard_outline"}]` | `PATCH /v1/projects/{owner}/{repo}/import` |
| `import.apply` | `writing_approval` (nur mit Häkchen) | Buch aus dem Vorschlag anlegen | Action mit `step: apply` (bzw. `import_book.py . apply [--writing-approval]`), danach die Projektübersicht und das Angebot der Analysen | `POST /v1/projects/{owner}/{repo}/import/apply` |
| `analysis.start` | `kind` (`characters`, `summaries`, `style`, `places`, `timeline`, `continuity`, `language`, `chronology`, `portraits`; mehrere mit Komma), `scope` (`book` bzw. Kapitelnummer), optional `confirm_low_budget` | Analyse im Hintergrund starten (#123) | vorher `python scripts/analyze.py . plan --scope …` (Umfang, Tokens, Kosten) und Limits zeigen; nach Bestätigung die Action „Analyse im Hintergrund“ auf dem Buch-Branch starten (`POST /repos/{owner}/{repo}/actions/workflows/analyse.yml/dispatches`, `ref` = Buch-Branch, `inputs`) | `POST /v1/projects/{owner}/{repo}/analyses` |
| `analysis.open` | `kind`, `run` (Pfad der Vorschlagsdatei) | Vorschläge eines Hintergrundlaufs ansehen | `render_view.py analysis-suggest --draft <run>`: Figuren in `figuren-vorschlag` (Übernehmen wie `character.suggest.apply` mit `run`), Kurzbeschreibungen in `kurzbeschreibung-vorschlag`, Stilprofil in `stilprofil-vorschlag`, Schauplätze in `orte-vorschlag`, Zeitleiste in `zeitleiste-vorschlag`, Widersprüche in `widerspruch-vorschlag`, Sprache in `sprache-vorschlag`, Chronologie in `chronologie-vorschlag` (#364) (Übernehmen mit `analysis.apply`) | – |
| `analysis.apply` | `kind` (`summaries`, `style`, `places`, `glossary` (`{index, term, explanation}`, #490), `timeline`, `continuity`, `language`, `chronology`), `run` (`run-NNN`), `choices` (Kurzbeschreibungen: Liste `{index, goal?, short?}`, nur angehakte Felder; Stilprofil: `{index, value}`; Schauplätze: `{index, name, kind, short, merge_into?}`; Zeitleiste: `{index, when, what}` je Ereignis und `{issue, text}` je Hinweis; Widersprüche: `{index, text, mark}` mit den Nummern der Fundstellen für den Marker; Sprache: `{index}`; Chronologie: `{index, what?, date?, status?}`) | Ausgewählte Vorschläge eines Hintergrundlaufs übernehmen | Auswahl als JSON-Datei, dann `python scripts/analyze.py . apply run-NNN --kind <art> <datei>` (schreibt nur die genannten Felder und vermerkt den Lauf als erledigt); ein Commit „Analyse übernommen: …“, danach die Projektübersicht. „Verwerfen“ (`form.cancel` mit `form: analysis.apply`, `kind`, `run`): `python scripts/analyze.py . applied run-NNN --kind <art>` | `POST /v1/projects/{owner}/{repo}/analyses/{kind}/{run}/apply` |
| `figurenbild.stil.save` | `style` (Objekt mit den gefüllten Feldern `medium`, `realismus`, `farbigkeit`, `licht`, `ausschnitt`, `hintergrund`, `merkmale`, `ausschluesse`, `freitext`) | Bildstil des Projekts speichern (eigene Bestätigung im Widget) | `python scripts/figurenbild.py . stil set '<json>'`, ein Commit; leere Felder bleiben unverändert | – |
| `figurenbild.pick` | `figure`, `image_id`, `status` (`gewaehlt` \| `idee`) | Variante auswählen (nur der Status, keine Referenzfreigabe) | `python scripts/figurenbild.py . waehlen <Figur> <Bild> --status <status>`, ein Commit | – |
| `figurenbild.change` | `figure`, `image_id` | Variante gezielt ändern | Rückfrage, was sich ändern soll; dann Änderungsprompt mit dem Bild als Eingabe und `figurenbild.py . variante … --art aenderung --eingabe <Bild>` | – |
| `anecdote.capture` | – | Anekdote erzählen (Widget `anekdoten`) | wie Befehl `Anekdote erfassen`: im Chat strukturiert festhalten, Inhalt nicht ändern (`START.md`, „Anekdoten“, Schritt 1) |
| `anecdote.show` | `id` | Original im Chat zeigen | `anekdoten.py . show <id>`; nur Eigentümer und Bearbeiter |
| `anecdote.suggest` | `section` (`N.M`) | Vorschläge für einen Abschnitt | `render_view.py anecdotes <N.M>` |
| `anecdote.plan` | `id`, `section` (`N.M`) | für den Abschnitt einplanen (erst nach zweitem Klick) | `anekdoten.py . plan <id> --section <N.M>`, ein Commit; schreibend, mit `expected_head_sha` |
| `anecdote.use` | `id`, `section` (`N.M`) | Einbau beginnen | nichts schreiben: Fassung, Wahrheitsgehalt, Ersetzungen und Einverständnis im Chat klären, Text als Vorschlag, erst nach Bestätigung `anekdoten.py . use …` (`START.md`, „Anekdoten“, Schritt 3) |
| `character.talk.start` | `figure` (Name oder ID), optional `until` (`N.M`, `N`) | Figurengespräch beginnen (Steuerkarte `figurengespraech`) | Klartext `Figurengespräch <Name> [bis <Stelle>]` bzw. `Talk to <Name> [until <place>]`: `START.md`, „Figuren“, Schritt 8; danach die Karte `character-talk <Figur> --draft '{"phase":"active","until":…}'` zeigen | – |
| `character.talk.end` | – | Gespräch beenden | wie `Gespräch beenden` (Schritt 8.4, 8.5); danach Karte `phase: insights` mit den Erkenntnissen zeigen, als Vorschläge ohne Haken | – |
| `character.talk.until` | `until` (`N.M`, `N` oder `book`) | Stelle im laufenden Gespräch ändern | `characters.py . interview <Figur> --bis <Stelle>` neu lesen und mit der neuen Grenze weiterführen; Karte erneuern | – |
| `character.talk.switch` | `figure`, optional `until` | Figur wechseln | wie `character.talk.start`; das alte Gespräch endet, Erkenntnisse der alten Figur nicht übernehmen, bevor sie bestätigt wurden | – |
| `character.talk.apply` | `figure`, `choices` (Liste `{index, field, text}` der angekreuzten Erkenntnisse) | Ausgewählte Erkenntnisse ins Profil übernehmen (eigene Bestätigung auf der Karte) | nur die gewählten Felder mit `characters.py . update <id> '<json>'`, ein Commit (Listenfelder `traits` ergänzen, Textfelder nur nach Ersetzen-Hinweis); nichts anderes ändern, kein Manuskript | `PATCH …/characters/{character_id}` |
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
| `matter.glossary.suggest` | `matter_id` | Begriffe aus dem abgeschlossenen Text vorschlagen (#58) | Vorschläge mit Fundstelle und Erklärungsentwurf als Auswahl zeigen (`START.md`, „Vor- und Nachspann“, Punkt 4); nichts schreiben | – |
| `view.library` | – | Bücherregal zeigen | Vorlage `buecherregal` (`render_view.py library --library library.json`) | – |
| `view.data` | – | Seite „Daten“ zeigen | Daten sammeln und Vorlage `daten` (`render_view.py data`, `START.md`, „Daten“) | `GET /v1/projects/{owner}/{repo}` |
| `library.book.open` | `branch` | Buch aus dem Bücherregal öffnen | Branch als Buch-Branch übernehmen, Projektübersicht zeigen; Buch im Aufbau: Einstiegsdialog fortsetzen | `GET /v1/projects/{owner}/{repo}` |
| `library.edition.open` | `branch`, `edition` | Auflage eines Buchs aus dem Bücherregal öffnen (#235) | mit Tag: Name, Datum und Link zur Release-Seite zeigen; nur Auflagen-Branch: dessen Projektübersicht zum Nachlesen; nichts schreiben (`START.md`, „Bücherregal“) | – |
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
| `project.update` | `title`, `subtitle`, `title_short`, `author`, `description_short`, `description`, `language`, `book_type`, `target_audience`, `translations_planned` (Liste von Sprachcodes, leer = Feld entfernen), `expected_head_sha` | Projektdaten speichern | in `ghostwriter.yml` schreiben (leere Texte entfernen das Feld, `language` bleibt Pflicht und wird nie geleert), danach Projektübersicht | `PATCH /v1/projects/{owner}/{repo}` |
| `project.settings.open` | – | Projekteinstellungen zeigen | Vorlage `projekteinstellungen` (`render_view.py project-settings`) | – |
| `project.settings.update` | `fact_checking_default`, `typesetting` (`page_size`, `font`, `font_size`, `title_page`, `imprint`, `toc`, `toc_depth`), `updates` (`auto`), `changes` (`auto_merge`), `limits` (`ai_budget_monthly`, `actions_minutes_monthly`; `null` = entfernen), `expected_head_sha` | Einstellungen speichern | `workflow.fact_checking_default`, `typesetting`, `updates`, `changes` und `limits` in `ghostwriter.yml` schreiben, danach Projektübersicht | `PATCH …/settings` |
| `project.ai_disclosure.open` | – | Formular „KI-Angabe im Buch“ zeigen (Befehl `KI-Angabe`, Knopf in den Projekteinstellungen, #78) | Vorlage `ki-angabe` (`render_view.py ai-disclosure`) | – |
| `project.ai_disclosure.update` | `mode` (`functions`, `short`, `detailed`, `custom`), `placement`, `name_services`, `functions` (Aufzählung, leer = Vorgabe), `text` bzw. `use_suggestion`, `expected_head_sha` | KI-Angabe speichern | `scripts/ai_disclosure.py set`, ein Commit (`START.md`, „KI-Angabe im Buch“), danach das Formular | `PATCH …/settings` |
| `project.rules.open` | – | Auswahl „Grundregeln“ zeigen (Befehl `Grundregeln`, #300) | `scripts/rules.py . choice` als `--spec` für `render_view.py choice` | – |
| `project.rules.update` | `step: rules`, `answers` (`facts`, `creativity`, `approvals`: Stufe), `expected_head_sha` | Stufen der Grundregeln setzen | je geänderter Gruppe `scripts/rules.py . plan`; verschärfen direkt mit `set`; **lockern nur nach eigener Bestätigung** (`START.md`, Abschnitt 3, „Stufen der Grundregeln“), dann `set … --confirmed`; danach Projekteinstellungen | `PATCH …/settings` |
| `project.analysis.open` | – | Formular „Analyse-Einstellungen“ zeigen (Befehl `Analyse-Einstellungen`, Zeile in den Projekteinstellungen, #299) | Vorlage `analyse-einstellungen` (`render_view.py analysis-settings`) | – |
| `project.analysis.update` | `provider` (leer = automatisch), `model`, `merge_model`, `price_input_per_mtok`, `price_output_per_mtok` (Zahl oder `null`), `parallel` (1–16 oder `null`), `languagetool` (`language`, `words`, `disabled_rules`), `expected_head_sha` | Analyse-Einstellungen speichern | `python scripts/analyze.py . settings-set '<json>'` (prüft, leere Werte = Vorgabe), ein Commit `Analyse-Einstellungen geändert`; danach Projekteinstellungen | `PATCH …/settings` |
| `project.output.open` | – | Formular „Ausgabeoptionen“ zeigen (Befehl `Ausgabe`, Knopf in Projektübersicht und Projekteinstellungen, #68) | Vorlage `ausgabeoptionen` (`render_view.py output`) | – |
| `project.output.update` | `typesetting` (Felder wie in `docs/DATA-MODEL.md`, „Buchsatz“), `publication` (`publisher`, `isbn_print`, `isbn_ebook`, `rights`), `print`, `cover`, Texte der Rückseite (`blurb`, `author_bio`), `expected_head_sha` | Ausgabeoptionen speichern | in `ghostwriter.yml` schreiben (nur geänderte Felder), prüfen, danach das Formular | `PATCH …/settings` |
| `project.providers.open` | – | Formular „KI-Dienste“ zeigen | Vorlage `ki-dienste` (`render_view.py providers-edit`) | – |
| `project.providers.update` | `available`, `services` (je eigenem Dienst `access`, `model`, `github_connected`, `plan`, `monthly_cost`, `note`, bei `access: api` zusätzlich `api_key_secret`), `roles` (`default`, `research`, `brainstorming`, `writing`, `revision`, `fact_check`: Dienst-ID, `chat` oder leer), `queue_agent`, `search_tools`, `expected_head_sha` | KI-Dienste speichern | `ai_providers` in `ghostwriter.yml` schreiben: `available`, `services` (nur eigene Dienste; leere Felder weglassen; vorhandene Preisfelder `price_input_per_mtok`, `price_output_per_mtok`, `price_per_1k_searches` bleiben, solange das Formular sie nicht mitschickt, #462), `provider` je Aufgabe, `research.search_tools`, `queue_processing.agent`; Modellnamen nicht ändern. Danach Projektübersicht | `PATCH …/settings` |
| `chapter.create.open` | – | Formular „Neues Kapitel anlegen“ zeigen | Vorlage `kapitel-anlegen` (`render_view.py chapter-create`) | – |
| `chapter.create` | `title`, `summary`, `goal`, `position` (Index, 0 = am Anfang), `position_label`, `expected_head_sha` | Kapitel anlegen | Kapitel anlegen, danach Kapitelansicht des neuen Kapitels | `POST …/chapters` |
| `chapter.edit.open` | `chapter_id` | Kapitel bearbeiten | Vorlage `kapitel-bearbeiten` (`render_view.py chapter-edit N`) | – |
| `chapter.update` | `chapter_id`, `title`, `subtitle`, `summary`, `goal`, `expected_head_sha` | Kapitel speichern | Titel in `structure.chapters` und Kapitel-README im selben Commit ändern, danach Kapitelansicht | `PATCH …/chapters/{chapter_id}` |
| `chapter.research.open` | `chapter_id` | Kapitelrecherche öffnen | Vorlage `kapitelrecherche` (`render_view.py chapter-research N`) | – |
| `chapter.texts.update` | `chapter_id`, `goal`, `summary`, `expected_head_sha` | Ziel und Kurzbeschreibung speichern | nur diese beiden Abschnitte der Kapitel-README ändern, danach Kapitelansicht | `PATCH …/chapters/{chapter_id}` |
| `chapter.sections.add` | `chapter_id`, `sections` (Liste mit `title`, `summary`), `expected_head_sha` | Vorgeschlagene Abschnitte anlegen | am Ende des Kapitels anlegen (`START.md`, „Kapitelrecherche“, Schritt 6), ein Commit, danach Kapitelansicht | `POST …/chapters/{chapter_id}/sections` |
| `chapter.research.start` | `chapter_id`, optional `start`, `not_before`, `after_event` (#65, ab UI 0.77.0), `task` (`goal` \| `sections` \| `summary` \| leer), `question`, `scope`, `weight_prev`, `weight_next` (0–3), `goal`, `summary`, `expected_head_sha` | Kapitelrecherche starten | Lauf ausführen und speichern (`START.md`, „Kapitelrecherche“), danach wieder das Formular mit Vorschlägen und den gesendeten Werten (`--draft`) | `POST …/chapters/{chapter_id}/research-runs` |
| `chapter.revision.start` | `chapter_id` | Kapitel überarbeiten | Auf dem aktuellen Lese-Stand Voraussetzungen mit `scripts/chapter_revision.py` erneut prüfen; bei Erfolg das vollständige Kapitel nach `START.md`, „Kapitelüberarbeitung“, prüfen und Vorschläge zeigen. Keine Freigabe erteilen. | – |
| `chapter.reorder.open` | – | Kapitelreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py chapter-reorder`) | – |
| `chapter.reorder` | `order` (alle Kapitel-IDs in neuer Reihenfolge), `expected_head_sha` | Kapitelreihenfolge speichern | `structure.chapters` umsortieren; IDs und Pfade bleiben; danach Projektübersicht | `POST …/chapters/reorder` |
| `section.create.open` | `chapter_id` | Neuen Abschnitt anlegen | Vorlage `abschnitt-anlegen` (`render_view.py section-create N`) | – |
| `section.create` | `chapter_id`, `title`, `goal`, `summary`, `fact_check`, `position` (Index, 0 = am Anfang), `position_label`, `expected_head_sha` | Abschnitt anlegen | Abschnittsdatei aus `templates/section.md` anlegen und in `structure.chapters` eintragen, danach Abschnittsformular | `POST …/chapters/{chapter_id}/sections` |
| `section.reorder.open` | `chapter_id` | Abschnittsreihenfolge ändern | Vorlage `reihenfolge` (`render_view.py section-reorder N`) | – |
| `section.reorder` | `chapter_id`, `order` (alle Abschnitts-IDs des Kapitels in neuer Reihenfolge), `expected_head_sha` | Abschnittsreihenfolge speichern | `sections` des Kapitels umsortieren; IDs und Dateinamen bleiben; danach Kapitelansicht | `POST …/chapters/{chapter_id}/sections/reorder` |
| `section.update` | `section_id`, `goal`, `summary`, `fact_check`, `manuscript`, bei Büchern mit Figuren `characters` (Liste von IDs, #53), `expected_head_sha` (nie `approvals`) | Abschnitt speichern | Abschnittsdatei schreiben, danach Abschnittsformular | `PATCH …/sections/{section_id}`, `PUT …/sections/{section_id}/manuscript` |
| `run.start` | `section_id`, `task` (`research` \| `writing`), `mode` (`immediate` \| `scheduled`), bei `scheduled` optional `start`, `not_before`, `after_event` (#65, ab UI 0.77.0) | AI-Lauf starten; `scheduled` gibt es für `research` (#482): Auftrag in die Hintergrund-Warteschlange (`scripts/jobs.py enqueue`, `START.md`, „Recherche mit Internet in der Action“), sonst `immediate` | Lauf ausführen und Lauf-Datei, Ergebnis und Statuswechsel speichern (`START.md`, „KI-Lauf „Sofort““); ein Kosteneintrag nur für kostenpflichtige KI-API-Aufrufe über das Backend, nie für Chat-Arbeit | `POST …/sections/{section_id}/research-runs` bzw. Manuskript |
| `view.timeline` | – | Zeitleiste zeigen (#354) | `render_view.py timeline` (Vorlage `zeitleiste`) | – |
| `stale.list` | – | Veraltete Abschnitte und Teile zeigen (#592) | `python3 scripts/stale.py . list`, Ausgabe als Liste im Chat; ändert nichts | – |
| `section.mark_stale` | `section_id` (Abschnitts- oder Teil-ID), `reason`, optional `source` | Abschnitt oder Teil als veraltet markieren (#510, #592) | `python3 scripts/stale.py . mark <section_id> --reason <reason> [--source <source>]`, ein Commit auf den Arbeits-Branch; Status, Freigabe und Fingerabdruck bleiben, der Text ändert sich nicht | – |
| `section.clear_stale` | `section_id` | Veraltet-Markierung entfernen (#592) | `python3 scripts/stale.py . clear <section_id>`, ein Commit; beim erneuten Abschließen entfernt der Assistent sie ebenfalls | – |
| `view.notes_review` | optional `file` | Hinweisdurchsicht zeigen (#367) | `render_view.py notes-review [<file>]` (Vorlage `hinweisdurchsicht`); ohne Dialogdatei zuerst `scripts/hinweise.py collect .` | – |
| `queue.prioritize` | `request` (Pfad des Auftrags im Buch) | Auftrag vorziehen (#478) | `python scripts/jobs.py . prioritize --request <request> --push-to ghostwriter/<buch>` bzw. `priority: true` in die Auftragsdatei schreiben, ein Commit auf den Arbeits-Branch; nur wartende Aufträge. Danach `render_view.py queue` erneut | – |
| `queue.retry` | `request` | Fehlgeschlagenen Auftrag erneut versuchen (#596) | `python scripts/jobs.py . retry --request <request> --push-to ghostwriter/<buch>` bzw. `error` und `failed_at` aus der Auftragsdatei entfernen, ein Commit; nur fehlgeschlagene Aufträge, kein zweiter Auftrag. Bei „Modell nicht mehr verfügbar“ vorher das Modell im Formular „KI-Dienste“ ändern. Danach `render_view.py queue` erneut | – |
| `queue.cancel` | `request` | Auftrag abbrechen (#478) | `python scripts/jobs.py . cancel --request <request> --push-to ghostwriter/<buch>` bzw. Auftragsdatei löschen, ein Commit; nur wartende Aufträge, ein laufender lässt sich nicht stoppen. Danach `render_view.py queue` erneut | – |
| `checkout.aufbau` | `folder` (Ablageordner der Rückgabe), `ids` (kommagetrennt, z. B. `a-001,a-003`), `confirm` (`true`) | Ausgewählte Aufbau-Änderungen einer Rückgabe übernehmen (#209, #630) | Die Auswahl im Widget ist die ausdrückliche Bestätigung: `python3 scripts/checkin.py . aufbau <folder> --apply <ids> --confirm` (über `sections.py`), danach ein Commit auf den Arbeits-Branch. Nur bei beendetem Checkout; geänderte Gliederung seit der Rückgabe sperrt. Danach `render_view.py checkin <folder>` erneut | – |
| `notes_review.decide` | `file`, `entry`, `decision` (`ja`, `nein`, `geändert`), bei `geändert` `new` | Antwort zu einem Eintrag speichern (#367) | `python scripts/hinweise.py decide . <entry> --decision <decision> [--new …] --file <file>`, ohne Rückfrage in die Dialogdatei; ist `new` eine Antwort auf die Frage oder eine Anweisung statt eines neuen Wortlauts („Hafen“ für einen ganzen Satz, „… entsprechend ändern“), lehnt `decide` ab: dann `--answer "<new>"` (Feld `antwort`, #675) und, wenn klar, den daraus folgenden Ersatztext mit `--new`; ins offene Änderungspaket kommt sie je abgeschlossenem Thema bzw. Runde (`docs/SPEICHERN.md`, „Hinweise durchsehen“); Ist `entry` eine Gruppe (`gruppe:<schlüssel>`, #570), `hinweise.py decide . --group <entry> --decision ja|nein --file <file>`; danach die nächste Karte (`--next-card`, #609). Ein Text mit Fragezeichen am Ende ist bei `geändert` eine Rückfrage und wird nicht gespeichert (Aufruf `hinweise.py ask . <id>`). **Speichern (#609):** die Dialogdatei wird je abgeschlossenem Thema bzw. Runde und auf „Zwischenstand speichern“ committet (`hinweise.py checkpoint .`), nicht je Antwort. Ändert kein Manuskript | – |
| `notes_review.ask` | `file`, `entry`, `question` | Rückfrage zu einem Eintrag (#609), entscheidet nichts | den Eintrag nicht ändern, nichts speichern; die Frage beantworten und dieselbe Karte erneut zeigen (`python scripts/hinweise.py ask . <entry> --question <question> --file <file> [--repo <owner/repo>]`, `render_view.py … notes-review --entry <entry>`) | – |
| `notes_review.plan` | `file` | Umsetzen prüfen (#367) | `python scripts/hinweise.py plan . --file <file>` zeigen (✅/⚠️/⛔). Wieder öffnen nur über die gewohnte Freigabe; umsetzen (`hinweise.py apply .`) erst auf ausdrücklichen Auftrag als eigener Änderungsschritt | – |
| `checkout.start` | `chapters` (z. B. `3-5`) oder `book`, `reader`, optional `until` | Bereich zum Gegenlesen auschecken und sperren (#572) | Action „Auschecken zum Gegenlesen“ (`checkout.yml`) bzw. `python3 scripts/checkout.py . start … --out <ordner>`; baut DOCX und PDF mit QR-Kennung. Der Klick ist die ausdrückliche Bestätigung | – |
| `material.add` | `file`, `art`, `name`, optional `minors` | Material einbringen (#574): ablegen, aufbereiten, markieren | `python3 scripts/material.py . add <file> --art <art> --name <name> [--minors]`, danach `prepare` und `mark`; Ablauf START.md, „Material einbringen“; ein Commit auf den Arbeits-Branch, nichts übernehmen ohne Bestätigung | – |
| `checkout.return` | `files` (Pfade der Rückgabe), optional `checkout` | Rückgabe einchecken (#573): DOCX, PDF oder Foto/Scan der Ausdrucke | `python3 scripts/checkin.py . <files> [--checkout <id>]`; Original unverändert, Befunde in `editorial/rueckgabe-….yml`, danach Hinweisdurchsicht anbieten; beendet den Checkout nicht | – |
| `checkout.end` | `id`, `reason`, optional `abort` | Checkout ausdrücklich beenden oder abbrechen (#572) | `python3 scripts/checkout.py . end <id> --reason … [--abort]`, nur als eigene Auswahl mit Bestätigung; nie durch Zeit oder Chatende | – |
| `edition.create.open` | – | Formular „Neue Auflage erzeugen“ zeigen | Vorlage `auflage-erzeugen` (`render_view.py edition-create`) | – |
| `edition.proof` | optional `chapters` (z. B. `1-4`, #413) | Probedruck erstellen | Action „Probedruck“ per `workflow_dispatch` starten oder Link *Run workflow* geben; danach Link zum Lauf (Download unter *Artifacts*) | `POST /repos/{owner}/{repo}/actions/workflows/proof.yml/dispatches` |
| `edition.preview` | – (Formate optional, sonst `typesetting.formats`; optional `chapters`, z. B. `1-4`, #413) | Vorabfassung anlegen (#348); auch Knopf „Vorabfassung“ im Formular „Neue Auflage“ (#352), der vor dem Senden selbst nach Bestätigung fragt; der zweite Klick ist die ausdrückliche Bestätigung | nach ausdrücklicher Bestätigung Action „Vorabfassung“ per `workflow_dispatch` starten (`ref` = Buch-Branch) oder Link *Run workflow* geben; danach Link zum Lauf und zum Pre-Release (`START.md`, „Vorabfassung“) | `POST /repos/{owner}/{repo}/actions/workflows/preview.yml/dispatches` |
| `manuscript.export` | `chapter` (optional, Kapitelnummer; bei `format` `md` Pflicht, Kapitel `5` oder Abschnitt `5.1`), `format` (`pdf` Vorgabe, `md` = Lesefassung für Clients ohne Skriptausführung, #289; Datei auf Branch `lesefassung/<buch>`) | Manuskript ausgeben (#260) | Action „Manuskript ausgeben“ per `workflow_dispatch` starten (`ref` = Buch-Branch), Lauf abwarten, PDF mit `scripts/fetch_artifact.py` abholen und als Datei im Chat übergeben; ohne Dateiübergabe Link zum Lauf (*Artifacts*) | `POST /repos/{owner}/{repo}/actions/workflows/manuscript.yml/dispatches` |
| `backup.create` | – | Gesamtsicherung erstellen (#489) | `python3 scripts/sicherung.py erstellen . -o <datei.zip> --repo <owner>/<repo>`, danach `sicherung.py pruefen`; ohne Shell die Action „Gesamtsicherung“ (`sicherung.yml`) starten, das Ergebnis liegt als **privates** Artefakt am Lauf. Die Datei enthält private Bucharbeit: nur als Download im Chat oder privates Artefakt, nie als Release. Keine Secret-Werte, keine automatische Wiederholung, keine Verschlüsselung in dieser Fassung | `POST /repos/{owner}/{repo}/actions/workflows/sicherung.yml/dispatches` |
| `edition.create` | `name`, `tag`, `date`, `formats`, `notes` | Auflage erzeugen | prüfen, Release Notes zeigen, Auflagen-Pull-Request anlegen (`START.md`, „Neue Auflage“); nach dem Merge baut die Action „Auflage veröffentlichen“ | `POST /repos/{owner}/{repo}/actions/workflows/edition.yml/dispatches` (Bau), Pull Request wie Weg A |
| `changes.merge.open` | – | Bestätigung „Buchänderungen übernehmen“ zeigen (Knopf im Hinweis der Projektübersicht, Textfassung `M`) | offene Änderungen aus GitHub lesen, Vorlage `aenderungen-uebernehmen` (`render_view.py changes-merge`) | `GET …/changes` |
| `changes.merge` | `pull_request`, `expected_head_sha` | Offene Buchänderungen übernehmen; der Klick auf „Übernehmen“ bzw. `OK` ist die ausdrückliche Bestätigung | prüfen, dass der Arbeits-Branch noch auf `expected_head_sha` steht (sonst Bestätigung neu zeigen), Pull Request mit Merge-Commit mergen, Arbeits-Branch löschen, danach Projektübersicht | `POST …/changes/merge` |
| `approval.open` | `kind` (`writing` \| `section` \| `chapter` \| `matter` \| `image`), `section_id` bzw. `chapter_id`, `revoke` (nur beim Zurücknehmen); bei Vor- und Nachspann steht die `mat-…`-ID in `section_id` (#57) | Bestätigung „Freigabe“ zeigen | Vorlage `freigabe-bestaetigen` (`render_view.py approval-<kind> N.M` bzw. `N`, für einen Teil `approval-writing\|approval-matter <teil>`, `--revoke`) | – |
| `approval.confirm` | wie `approval.open`, dazu `expected_head_sha` | Freigabe erteilen bzw. zurücknehmen; der Klick ist die ausdrückliche Bestätigung | Hindernisse erneut prüfen, dann nach `START.md`, „Freigaben“, schreiben; danach die Ausgangsansicht | `POST`/`DELETE …/sections/{section_id}/writing-approval`, `…/sections/{section_id}/approve`, `…/chapters/{chapter_id}/approve`, `…/matter/{matter_id}/writing-approval`, `…/matter/{matter_id}/approve` |
| `update.apply` | – | GhostWriter aktualisieren | Action „GhostWriter aktualisieren“ per `workflow_dispatch` starten oder Link *Run workflow* geben (`START.md`, „Programmdateien und Updates“); nie selbst mergen | `POST /repos/{owner}/{repo}/actions/workflows/update.yml/dispatches` |
| `wizard.answer` | `step`, `answers` (je `key` der Frage: Wert, Liste von Werten bei Mehrfachauswahl, `{"other": "Text"}` für eine eigene Antwort, auch als Listeneintrag) | Antworten auf Auswahlkarten | Antworten übernehmen (`START.md`, Abschnitt 4, „Auswahlkarten“), noch nichts schreiben; mit dem nächsten Wizard-Schritt weitermachen | – |
| `wizard.skip` | `step` | Schritt überspringen | Angabe bleibt vorerst offen, nächster Wizard-Schritt | – |
| `form.cancel` | `form` und betroffene ID | Formular ohne Änderung geschlossen | nichts schreiben, Ausgangsansicht zeigen (siehe „Nach dem Formular“) | – |

Schreibende Aktionen (`….update`, `….create` außer `edition.create`, `….reorder`, `changes.merge`, `approval.confirm`) laufen nach `START.md`, „Schreiben ins Repository“: Prüfung gegen `expected_head_sha`, Commit im Arbeits-Branch, kein automatischer Merge.

Jede `….open`-Aktion beantwortet der Assistent sofort mit dem genannten Formular, ohne Rückfrage. Eine Reihenfolge wird nur gespeichert, wenn `order` genau die bisherigen IDs enthält; sonst fragt der Assistent nach.

## Nach dem Formular

Nach Speichern, Abbrechen oder „nichts geändert“ zeigt der Assistent sofort wieder die Ansicht, aus der das Formular geöffnet wurde, neu unter dem Formular. Die alte Ansicht bleibt im Verlauf stehen; der Chat kann nicht zurückblättern.

| Formular | Danach |
|---|---|
| Projektdaten bearbeiten, Projekteinstellungen, KI-Dienste, Kapitelreihenfolge, Neue Auflage, Buchänderungen übernehmen | Projektübersicht |
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
| `approval.confirm` | → Prüfe die Voraussetzungen erneut · → Prüfe, ob sich die Dateien seit dem Lesen geändert haben · → Speichere die Freigabe und den Eintrag in approvals.yml (Commit im Arbeits-Branch) | – | ✓ Abschnitt N.M abgeschlossen (bzw. wieder geöffnet, Schreiben erlaubt/gesperrt), Commit `abc1234` · noch nicht übernommen (Pull Request #NN) |
| `project.update` | → Prüfe Eingaben · → Prüfe, ob sich die Dateien seit dem Lesen geändert haben · → Speichere Projektdaten (Commit im Arbeits-Branch) · → Prüfe Validierung | – | ✓ Projektdaten gespeichert, Commit `abc1234` · noch nicht übernommen (Pull Request #NN) |
| `chapter.create` | → Lege Kapitel „Titel“ an · → Trage es in ghostwriter.yml ein · → Speichere (Commit) | – | ✓ Kapitel N „Titel“ angelegt, Commit `abc1234` |
| `section.update` | → Prüfe, ob sich die Datei seit dem Lesen geändert hat · → Speichere Abschnitt N.M (Commit im Arbeits-Branch) | – | ✓ Abschnitt N.M gespeichert, Commit `abc1234` |
| `run.start` | → Recherche bzw. KI-Entwurf für N.M · → Speichere Lauf und Ergebnis (Commit im Arbeits-Branch) | – | ✓ Entwurf für N.M gespeichert, Lauf `run-003`, Commit `abc1234` |
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
| `edition.preview` | → Starte Vorabfassung | – | ✓ Vorabfassung N angelegt: Tag `<kurztitel>-vorab-N`, Release: <Link> · bzw. ✓ gestartet, Lauf: <Link> |
| `manuscript.export` | → Starte „Manuskript ausgeben“ · → Hole das PDF ab | – | ✓ Manuskript als PDF übergeben (Datei im Chat) bzw. ✓ gestartet, Lauf: <Link> (PDF dort unter *Artifacts*, 14 Tage) |
| `backup.create` | → Erstelle die Gesamtsicherung · → Hole die Datei ab | – | ✓ Sicherung erstellt und geprüft (Bücher, Branches, Hinweise zu Nicht-Lesbarem) bzw. ✓ gestartet, Lauf: <Link> (Datei dort unter *Artifacts*, privat) |
| `edition.create` | → Lege Pull Request für Auflage N an | – | ✓ Pull Request #NN für Auflage N angelegt; Tag und Release erzeugt die Action nach dem Merge |
| `changes.merge` | → Prüfe, ob seit der Bestätigung etwas dazugekommen ist · → Übernehme N Änderungen (Merge) · → Lösche den Arbeits-Branch | – | ✓ N Änderungen übernommen, Merge-Commit `abc1234` |
| Fehler | – | – | ✗ Nicht gespeichert: Grund, etwa „Datei wurde inzwischen geändert“ |

## Weg B

Mit eigener API bleibt alles gleich, was der Benutzer sieht: dieselben Vorlagen aus `ghostwriter-ui`, dieselben Daten (die Platzhalter oben entsprechen den Feldern der API) und dieselben Nachrichten. Nur die Herkunft der Daten ändert sich; `GW.render` bekommt sie dann aus der Antwort der API statt vom Assistenten.

Freigaben gibt es nur über `approval.confirm` (`START.md`, „Freigaben“); `section.update` ändert `approvals` nie (Issue #10).

## Bediensprache der ersten Ansichten und Formulare (#74)

`render_view.py --language en` unterstützt alle vorhandenen Ansichtsarten und Formulare. Ohne `--ui-ref` wird Englisch nativ als Text ausgegeben; mit `--text` gilt das auch bei gewählter Testfassung. Der geprüfte feste UI-Commit bleibt unverändert. `--ui-ref <geprüfter-ui-commit>` ermöglicht ausdrücklich eine grafische Vorschau.

`LANGUAGE` im Widget-Payload ist Metadatum für die Sprachwahl. Die Rohdaten eines Widgets stehen dem alternativen nativen Renderer unverändert zur Verfügung. Projektanalysen enthalten zusätzlich `A_COUNT` und `A_DATE`, Importhinweise `IMPORT_SOURCE` und `IMPORT_EXPIRES`; diese strukturierten Angaben erlauben das Erzeugen englischer Hinweise ohne Übersetzung oder Ersetzung von Buchtexten. Bücherregal-Zeilen enthalten zusätzlich die Rohzahlen `BOOK_SECTION_COUNT`, `BOOK_APPROVED_SECTION_COUNT`, `BOOK_CHAPTER_COUNT`, `BOOK_APPROVED_CHAPTER_COUNT`, `BOOK_EDITION_NUMBER`, `BOOK_PENDING_COUNT` sowie `BOOK_AUTHOR_NAME`, `BOOK_UPDATED_AT` und `BOOK_TITLE_EMPTY`; bei Serien kommen `BOOK_VOLUME_NUMBER` beziehungsweise `SERIES_VOLUME_NUMBER` hinzu. Die Übersicht liefert `BOOK_COUNT_NUMBER` und `SERIES_COUNT_NUMBER`. Damit wird dieselbe Momentaufnahme verwendet, ohne die Bibliothek für die Übersetzung erneut einzulesen. Statuscodes bleiben intern unverändert. In den Anlageformularen bleiben Positionen nullbasiert, `POSITION_SELECTED` und die Faktencheck-Codes unverändert. Nur `POSITION_LABEL` und damit die optionale erklärende `position_label` der strukturierten Nachricht werden sprachgerecht formuliert; entscheidend bleibt der numerische Wert `position`. Englische Feldnamen werden gemäß den Aliasregeln in `START.md` zugeordnet. Alle 38 grafischen Vorlagen bieten englische feste Texte und Skriptmeldungen; mit `--ui-ref` lässt sich diese Fassung ausdrücklich testen. Englisch unterstützt außerdem die Freigabebestätigungen für Schreiben, Abschnitt, Kapitel, Vor-/Nachspann und Bilder sowie Buchänderungen übernehmen, Kapitel-/Abschnittsreihenfolge und Serienbearbeitung. Diese verwenden dieselbe Prüfung und Erzeugung für Text und Widget; die zusätzlichen Programmtexte liegen unter `templates/i18n/views/`. Auch Einstellungen, Ausgabeoptionen, KI-Dienste und KI-Angabe, Vor-/Nachspann, Figuren, Bilder, Serien/Sammelbände, Kapitelrecherche, alle Analysearten, Import, Daten und Wizard-Karten verwenden diese gemeinsame Lokalisierung. Buchtexte, gespeicherte Vorschläge und frei übergebene Auswahltexte bleiben Originaldaten.


### Gemeinsame übersichtliche Ansicht: Claude, ChatGPT und Gemini

Ohne ausdrücklich gewählten Darstellungsmodus gilt „übersichtlich“. Eine ausdrückliche Auswahl „einfach“, „erweitert“ oder „Nur Text“ bleibt wirksam; Antwortumfang und Darstellungsmodus bleiben unabhängig.

- Buch- und Kapitelkopf: Titel, kompakter Arbeitsstand und Kosten; direkt darunter ein Balken mit zehn Segmenten und der genauen Anzahl abgeschlossener Abschnitte. Ohne Abschnitte „0 von 0“ und keinen gefüllten Balken zeigen. „In Arbeit“ zählt alle Abschnitte, die weder geplant noch freigegeben sind; dies ist keine Freigabe. Der Balken misst ausschließlich Abschnittsfreigaben, nicht Fertigstellung oder Veröffentlichung des Buchs.
- Offene Marker mit Anzahl hervorheben. Warnungen, ausstehende Übernahmen und Freigaben weiterhin vollständig zeigen. Fehlende Daten ausdrücklich benennen; keine Zahlen schätzen.
- Einen passenden nächsten Schritt mit vorhandenem Aktionskürzel zeigen: zuletzt bearbeiteter, noch nicht abgeschlossener Abschnitt, sonst erster offener Abschnitt; bei leerer Struktur die Anlage anbieten. Öffnen und Auswählen erteilt keine Freigabe. Vollständige Aktionen bleiben darunter erreichbar. Keine funktionslosen Schaltflächen oder neuen Befehle erfinden.
- Status immer als Symbol und Wort darstellen. Tabellen knapp halten; lange Manuskripttexte bleiben normaler Lesetext.
- **Claude (Anthropic):** bestehende GhostWriter-Widgets verwenden, wenn der konkrete Client sie unterstützt; dieselbe inhaltliche Gliederung anwenden. Bei fehlender Unterstützung auf Markdown zurückfallen. Die externen Widget-Vorlagen werden gesondert gepflegt; diese Vorgabe behauptet keine Änderung ihres HTML-Aufbaus.
- **ChatGPT (OpenAI):** übersichtliches Markdown als gemeinsame Grundlage; native Auswahl- und Anzeigeelemente nur bei tatsächlich vorhandener Unterstützung ergänzen.
- **Gemini (Google):** dieselbe Markdown-Grundansicht ausdrücklich unterstützen. Zusätzliche native Elemente nur bei bestätigter Unterstützung des konkreten Clients. API-Zugang oder Anbietername allein sagt nichts über die Chat-Darstellung aus.

Die Textansichten von Buch und Kapitel berechnen diese Übersicht aus den Abschnittsdateien. Das Bücherregal ergänzt seine vorhandenen Freigabezahlen um denselben Balken. Deutsch und Englisch verwenden dieselbe Berechnung. Ansichten erzeugen keine Änderungen an Buchdateien.


**Persönliches Freigaberecht:** Vor der Ausführung einer bestätigten Freigabe das Konto mit `scripts/approval_authority.py BUCH actor` prüfen und den verifizierten Login im neuen Protokolleintrag verwenden. Fehlende Berechtigung sperrt die Ausführung, ohne Daten zu ändern. Eine Auswahl oder ein Feld `by` ersetzt diese Prüfung nicht. Für veröffentlichbare Ausgaben gilt zusätzlich der persönliche Inhaltsnachweis nach [Speichern und Abschließen](../../docs/SPEICHERN.md#persönliches-freigaberecht-und-inhaltsnachweis). Keine neue Widgetaktion wird dadurch eingeführt; die Claude-Web-App muss den Prüfablauf in Claude übernehmen.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../../assets/logo-dark.svg"><img src="../../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
