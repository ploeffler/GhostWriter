# Datei- und Statusmodell

## Einpflegen und Nachziehen

Der Lauf `catch_up` dokumentiert neue Materialien, den Abgleich aller Abschnitte,
Änderungen und die anschließende Redaktion unter
`analysis/catch-up/run-{sequence}.md`. Ablauf und Pflichtangaben stehen in
[Einpflegen und Nachziehen](NACHZIEHEN.md); es gibt keine automatische Freigabe.

## Vorgeschlagene Projektstruktur

```text
repository/
├── README.md
├── START.md
├── ghostwriter.yml        # inkl. ai_providers (Anbieter je Aufgabe)
├── providers.yml          # Katalog möglicher KI-Anbieter
├── research/
│   └── sources.md
├── brainstorming/
├── costs/
│   └── project.yml        # projektweite Kosteneinträge
├── approvals.yml          # Freigabe-Protokoll, nur anhängen
├── matter/                # Vor- und Nachspann (#57), nur vorhandene Teile
│   ├── widmung.md
│   ├── vorwort.md
│   ├── prolog.md
│   ├── epilog.md
│   ├── nachwort.md
│   ├── glossar.md
│   └── danksagung.md
├── cover/                 # Umschlag (#68): Bilder, rueckseite.md (Klappentext, Autorentext)
├── characters/            # Figuren (#53), je Figur char-<name>.md; nie im Buch
├── story/                 # Schauplätze (places.yml), Zeitleiste (timeline.yml), Hinweise (hints.yml), #124; nie im Buch
├── ghostwriter-index.json # Übersichtsdatei, erzeugt von scripts/build_index.py (nicht von Hand ändern)
├── chapters/
│   ├── 01-einleitung/
│   │   ├── README.md
│   │   ├── sections/
│   │   │   ├── 01-zielsetzung.md
│   │   │   └── 02-aufbau.md
│   │   ├── research/
│   │   │   └── <section-id>/
│   │   │       ├── run-001.md
│   │   │       └── run-002.md
│   │   ├── research/kapitel/
│   │   │   └── run-001.md         # Kapitelrecherche (ganzes Kapitel, Formular „Kapitelrecherche“)
│   │   ├── writing/
│   │   │   └── <section-id>/
│   │   │       └── run-001.md     # Protokoll eines Ghostwriting-Laufs (ab v0.4)
│   │   ├── images/
│   │   │   └── <section-id>/      # Illustrationen (#54)
│   │   │       ├── img-<slug>.png # Bild (PNG oder JPEG)
│   │   │       ├── img-<slug>.yml # Beschreibung: Bildunterschrift, Herkunft, Status
│   │   │       └── run-001.md     # Bildauftrag (Prompt, Dienst, Varianten, Auswahl)
│   │   └── costs/
│   │       └── <section-id>.yml   # KI-API-Kosten aus Backend oder GitHub Actions (nur dann)
│   └── 02-grundlagen/
│       ├── README.md
│       └── sections/
└── prompts/
    ├── research.md
    ├── brainstorming.md
    ├── writing.md
    ├── review.md
    └── fact-check.md
```

## IDs und Nummerierung

IDs sind stabil und maschinenlesbar, z. B. `ch-01-intro` und `sec-01-purpose`. Sichtbare Nummern (1, 1.1, 1.2) werden aus der Reihenfolge berechnet und dürfen sich ändern.

## Abschnittsstatus

- `planned`
- `research`
- `brainstorming`
- `ready_to_write`
- `writing`
- `revision`
- `fact_check`
- `ready_for_approval`
- `approved`

## Kapitelstatus

- `planned`
- `in_progress`
- `ready_for_assembly`
- `assembly`
- `review`
- `ready_for_approval`
- `approved`

## Projektdaten in `ghostwriter.yml`

| Feld | Bedeutung |
|---|---|
| `data_version` | Datenstruktur-Version des Buchs; setzt `scripts/migrate_project.py` beim Update, nicht von Hand ändern; fehlt = 0 ([UPDATES.md](UPDATES.md), #59) |
| `project.title` | Titel des Buches |
| `project.title_short` | Kurztitel für Badge, Listen und den Namen der Auflagen („Kurztitel – Auflage N“) |
| `project.working_title` | Arbeitstitel, solange kein Titel feststeht |
| `project.subtitle` | Untertitel |
| `project.author` | Autorin oder Autor |
| `project.description_short` | Kurzbeschreibung in einem Satz |
| `project.description` | ausführliche Beschreibung |
| `project.language` | Sprache des Buchs als Sprachcode, z. B. `de` (Silbentrennung und Anführungszeichen im Buchsatz) |
| `project.translations_planned` | geplante Übersetzungen als Sprachcodes, z. B. `[en]`; nur Angabe aus dem Wizard, fehlt = keine (Umsetzung der Übersetzung: #75) |
| `project.target_audience` | Zielgruppe |
| `project.book_type` | Buchtyp, z. B. Sachbuch, Ratgeber, Roman, Kinderbuch |
| `project.status` | Projektstatus, z. B. `concept` |
| `project.current_edition` | Nummer der letzten erschienenen Auflage, `0` = noch keine |
| `workflow.current_phase` | `wizard` bis zur Strukturfreigabe, danach eine andere Phase |
| `workflow.current_chapter_id`, `workflow.current_section_id` | zuletzt bearbeitete Stelle für den Wiedereinstieg |
| `workflow.require_section_writing_approval`, `workflow.require_section_approval`, `workflow.require_chapter_approval` | Schreib-, Abschnitts- und Kapitelfreigabe sind Pflicht; feste Regeln, nur im Chat mit ausdrücklicher Bestätigung änderbar |
| `workflow.fact_checking_default` | Vorgabe für den Faktencheck neuer Abschnitte: `disabled`, `optional`, `requested` (Projekteinstellungen) |
| `ai_settings` | globale KI-Regeln: `hallucination_policy` (`strict`), `source_policy` (`required`), `uncertainty_policy` (`explicit`), `creativity` (`balanced`), `web_research` (`research`); dürfen nur strenger werden (`START.md`, Abschnitt 3) |
| `ai_providers` | vorhandene KI-Dienste (`available`), Dienst und Modell je Aufgabe, Einstellungen je Dienst (`services`); siehe [PROVIDERS.md](PROVIDERS.md) |
| `structure.chapters` | Kapitel in Reihenfolge, je mit `id`, `title`, `path`, `status` und `sections` (je `id`, `title`, `path`) |
| `images` | Illustrationen (#54): `style` (Bildstil für alle Aufträge), `credit_in_imprint` (KI-erzeugte Bilder im Impressum nennen, Vorgabe `true`), `max_px` (längste Kante beim Ablegen, Vorgabe 3000); siehe „Illustrationen“ |
| `analysis` | Analyse im Hintergrund (#123): `provider` (`anthropic` | `openai`; sonst der erste mit hinterlegtem Schlüssel), `model` (je Kapitel), `merge_model` (Zusammenführen), `price_input_per_mtok`, `price_output_per_mtok` (Preise je 1 Mio. Tokens in Projektwährung; ohne Preise Kosten „unavailable“), `parallel` (gleichzeitige Aufrufe, Vorgabe 4); fehlt = Vorgaben (siehe „Analyse im Hintergrund“) |
| `style` | Stilprofil (#124), Vorgabe fürs Ghostwriting: `perspective` (Erzählperspektive), `tense` (Zeitform), `address` (Anrede des Lesers), `register` (Sprachebene), `tone` und `features` (Listen: Ton, Stilmittel), `sentence_length_avg` (Wörter je Satz) und `dialogue_share` (Anteil wörtlicher Rede, 0–1), beide ohne KI gezählt, `source` (Lauf, aus dem es übernommen wurde); fehlt = kein Stilprofil |
| `limits` | Limitwarnung (#62): `ai_budget_monthly` (KI-API-Kosten über das Backend je Monat in Projektwährung), `actions_minutes_monthly` (GitHub-Actions-Minuten je Monat), `warn_below_percent` (Vorgabe 20), `pause_below_percent` (Vorgabe 10); fehlt ein Betrag = keine Prüfung (siehe docs/UPDATES.md, „Limits“) |
| `characters` | Figuren (#53) in Reihenfolge, je `id` (`char-…`), `name`, `path`; fehlt = keine (siehe „Figuren“) |
| `structure.front_matter`, `structure.back_matter` | Vor- und Nachspann (#57, #58): Teile vor Kapitel 1 (Widmung, Vorwort, Prolog) bzw. nach dem letzten Kapitel (Epilog, Nachwort, Glossar, Danksagung), je mit `id`, `kind`, `title`, `path`; fehlen = keine (siehe „Vor- und Nachspann“) |

| `ai_disclosure` | KI-Angabe im Buch (#78): `mode` (`none`, `short`, `detailed`, `custom`), `placement` (`imprint`, `foreword`, `afterword`, `page`), `name_services`, `text` (bestätigter Wortlaut; nur dieser kommt ins Buch); fehlt = keine Angabe (siehe „KI-Angabe im Buch“) |
| `typesetting` | Buchsatz der Auflagen, Formular „Ausgabeoptionen“ bzw. Projekteinstellungen (siehe unten) |
| `publication` | Angaben im Impressum: Verlag, ISBN je Ausgabe, Rechtehinweis (#68; siehe „Buchsatz“) |
| `print` | Druck (#68): Profil des Anbieters (`kdp`, `bod`, `custom`), Papier, Rückenbreite, Beschnitt, Schnittmarken (siehe „Umschlag und Druck“) |
| `cover` | Umschlag (#68): Vorlage, Farben, Bilder, Preis, Richtung des Rückentexts (siehe „Umschlag und Druck“) |
| `updates.auto` | neue GhostWriter-Versionen automatisch einspielen; fehlt = `true` ([UPDATES.md](UPDATES.md)) |
| `changes.auto_merge` | gespeicherte Änderungen sofort übernehmen statt über „Änderungen übernehmen“; fehlt = `false`. Freigaben und Auflagen brauchen trotzdem ihre eigene Bestätigung (`START.md`, „Schreiben ins Repository“) |
| `.ghostwriter/update.yml` | von der Update-Action geschrieben: installierte Version, Upstream-Commit, Zeitpunkt, ausgelassene Workflow-Dateien; nicht von Hand ändern |
| `ghostwriter-manifest.yml` | Programmversion und welche Dateien zum Programm (`managed`) bzw. zum Buch (`book`) gehören; Teil des Programms |

### Buchsatz

`typesetting` steuert PDF, DOCX und EPUB der nächsten Auflage. Fehlt der Block oder ein Feld, gilt die Vorgabe:

| Feld | Werte | Vorgabe |
|---|---|---|
| `page_size` | `a5`, `12x19`, `13.5x21.5`, `a4` | `a5` |
| `font` | `serif`, `sans` | `serif` |
| `font_size` | `10`, `10.5`, `11`, `11.5`, `12` (pt) | `11` |
| `title_page` | Titelseite in der Titelei | `true` |
| `imprint` | Impressum in der Titelei | `true` |
| `toc` | Inhaltsverzeichnis | `true` |
| `toc_depth` | `1` = nur Kapitel, `2` = Kapitel und Abschnitte | `1` |
| `heading_font` | `same` (wie Grundschrift), `serif`, `sans` | `same` |
| `margins` | `standard`, `classic` (breite Ränder), `modern` (schmale) | `standard` |
| `line_spacing` | `1.0`, `1.1`, `1.2`, `1.3`, `1.5` | `1.1` |
| `paragraph` | `indent` (Einzug), `spacing` (Abstand zwischen Absätzen) | `indent` |
| `hyphenation` | Silbentrennung | `true` |
| `chapter_start` | `any` (nächste Seite), `right` (immer rechte Seite) | `any` |
| `running_heads` | Kolumnentitel: `sections` (Kapitel und Abschnitt), `chapter`, `book` (Buchtitel links, Kapitel rechts), `none` | `sections` |
| `page_numbers` | `header` (oben außen), `footer_center`, `footer_outer` | `header` |
| `initials` | Initiale am Anfang jedes nummerierten Kapitels | `false` |
| `glossary_marks` | Kennzeichnung der Glossar-Verweise im Text: `arrow` (→ Begriff), `italic`, `none` | `arrow` |
| `formats` | Formate einer Auflage: `pdf` (Bildschirm), `pdf_print` (Druck-PDF des Innenteils, `…-druck.pdf`), `cover` (Umschlag, `…-umschlag.pdf`), `docx`, `epub` | `pdf`, `docx`, `epub` |

`font` erlaubt neben `serif` (TeX Gyre Pagella) und `sans` (TeX Gyre Heros) die freien Schriften `pagella`, `termes`, `bonum`, `schola`, `heros`, `adventor` (DOCX nimmt die verbreitete Entsprechung, z. B. Times New Roman für Termes; EPUB nur Serif bzw. serifenlos). Bücher ohne die neuen Felder (#68) sehen aus wie bisher; im DOCX wirken Zeilenabstand und Absätze nur, wenn sie ausdrücklich gesetzt sind. Bearbeitet werden alle Felder im Formular „Ausgabeoptionen“ (Befehl `Ausgabe`).

Seitenformat, Ränder, Kapitelbeginn, Kolumnentitel und Seitenzahlen wirken nur im PDF (DOCX: Seitenformat), Schrift und Absätze in allen Formaten, soweit das Format sie kennt; EPUB übernimmt Inhaltsverzeichnis und Titelei.

**Angaben im Impressum** (`publication`, #68), alle optional: `publisher` (Verlag; „Selbstverlag“ steht so im Impressum), `isbn_print`, `isbn_ebook` (ISBN-10 oder -13, die Prüfung kontrolliert die Prüfziffer; die E-Book-ISBN wird auch Kennung des EPUB), `rights` (Rechtehinweis). Sie stehen in dieser Reihenfolge nach dem ©-Vermerk.

### Kapitel-README

Titel, Untertitel (erste kursive Zeile `*…*`), `## Kurzbeschreibung` und `## Ziel des Kapitels` stehen in `chapters/<kapitel>/README.md`; „Offen.“ steht für noch leer. Der Titel steht zusätzlich in `structure.chapters`. „Kapitel bearbeiten“ ändert beides im selben Commit.

Die Struktur von `ghostwriter.yml` beschreibt [`schemas/ghostwriter.schema.json`](../schemas/ghostwriter.schema.json).

### Umschlag und Druck

Mit `print` und `cover` (#68) entsteht beim Format `cover` ein Umschlag-PDF über Rückseite, Rücken und Vorderseite mit Beschnitt ringsum (`scripts/build_cover.py`): Breite = Beschnitt + Seite + Rücken + Seite + Beschnitt, Höhe = Beschnitt + Seite + Beschnitt; Rücken = Seitenzahl des Innenteils × Papierstärke. Gibt es `cover`, bekommt das EPUB dessen Vorderseite als Cover.

```yaml
print:
  profile: kdp           # kdp | bod | custom
  paper: cream           # nur kdp: white | cream | premium_color
  # spine_mm: 9.4        # feste Rückenbreite (BoD: aus dem BoD-Rechner; Pflicht bei bod und custom ohne paper_mm_per_page)
  # paper_mm_per_page: 0.06
  # bleed_mm: 3          # sonst Vorgabe des Profils
  crop_marks: false      # Schnittmarken an Druck-PDF und Umschlag (8 mm Rand)
cover:
  template: classic      # classic | modern | plain
  background: '#1F2A44'
  text_color: '#FFFFFF'
  image: cover/vorderseite.jpg     # füllt die Vorderseite samt Beschnitt
  author_image: cover/autor.jpg
  price: 18,00 € (D)
  spine_direction: down  # down (von oben nach unten) | up
```

| Profil | Beschnitt | Rücken je Seite | Rückentext |
|---|---|---|---|
| `kdp` (Amazon KDP, Taschenbuch) | 3,2 mm | weiß 0,0572 mm, creme 0,0635 mm, Premiumfarbe 0,0596 mm | ab 79 Seiten, 1,6 mm Abstand zur Kante |
| `bod` (Books on Demand) | 5 mm | nur über den BoD-Rechner: `spine_mm` | ab 6 mm Rückenbreite |
| `custom` | `bleed_mm`, Vorgabe 3 mm | `spine_mm` oder `paper_mm_per_page` | ab 6 mm Rückenbreite |

Stand der Werte: November 2026 (KDP-Hilfe „Cover“, BoD-Hinweise zur Umschlaggestaltung); die Anbieter ändern sie gelegentlich, daher vor dem Hochladen mit deren Rechner abgleichen. Die Rückseite trägt Klappentext und Autorentext aus `cover/rueckseite.md` (Vorlage `templates/cover-rueckseite.md`), das Autorenbild, den Preis und die ISBN der Druckausgabe als EAN-13-Strichcode (unten rechts, weiß hinterlegt). Im Probedruck zeigt der Umschlag Schnitt-, Falz- und Sicherheitslinien.

## Abschnittsdatei – Frontmatter-Beispiel

```yaml
## Bediensprache (#74)

`interface.language` ist eine optionale Buch-Einstellung (`de`, `en`, mit Sprachvariante). Vorrang: ausdrückliche Auswahl → `interface.language` → `assistant.yml: interface_language` auf dem Standard-Branch → Deutsch. Die Bediensprache ist unabhängig von `project.language`. Zunächst wird sie von den Tagesberichten verwendet; grafische Vorlagen und erzeugte Textansichten werden in weiteren Schritten migriert.

---
id: sec-01-purpose
number: "1.1"
title: "Zielsetzung"
status: planned
fact_check: optional   # disabled | optional | requested
approvals:
  writing: false
  section: false
---
```

Der Kopf jeder Abschnittsdatei folgt [`schemas/section.schema.json`](../schemas/section.schema.json). `fact_check` übernimmt die Werte aus `workflow.yml` (`entities.section.fact_check`).

## Vor- und Nachspann

Teile außerhalb der Kapitel (#57, #58), jeweils optional, in dieser Reihenfolge im Buch. Sie gehören dem Buch (`matter/` steht unter `book` im Manifest) und haben je eine Datei mit Kopf wie ein Abschnitt, Schema [`schemas/matter.schema.json`](../schemas/matter.schema.json), Vorlage `templates/matter.md`:

| Art (`kind`) | Bereich | Vorgabetitel | ID | Datei | Im Buch |
|---|---|---|---|---|---|
| `dedication` | `front_matter` | Widmung | `mat-widmung` | `matter/widmung.md` | eigene rechte Seite nach der Titelei, zentriert, ohne Überschrift, nicht im Inhaltsverzeichnis |
| `foreword` | `front_matter` | Vorwort | `mat-vorwort` | `matter/vorwort.md` | nach der Widmung, unnummeriert, im Inhaltsverzeichnis; am Ende optional Verfasser und Ort/Datum |
| `prologue` | `front_matter` | Prolog | `mat-prolog` | `matter/prolog.md` | vor Kapitel 1, unnummeriert, im Inhaltsverzeichnis |
| `epilogue` | `back_matter` | Epilog | `mat-epilog` | `matter/epilog.md` | nach dem letzten Kapitel, unnummeriert, im Inhaltsverzeichnis |
| `afterword` | `back_matter` | Nachwort | `mat-nachwort` | `matter/nachwort.md` | nach dem Epilog, unnummeriert, im Inhaltsverzeichnis; optional Verfasser und Ort/Datum |
| `glossary` | `back_matter` | Glossar | `mat-glossar` | `matter/glossar.md` | vor der Danksagung, unnummeriert, im Inhaltsverzeichnis; Begriffe alphabetisch als Beschreibungsliste |
| `acknowledgments` | `back_matter` | Danksagung | `mat-danksagung` | `matter/danksagung.md` | am Ende, unnummeriert, im Inhaltsverzeichnis |

```yaml
structure:
  front_matter:
  - id: mat-widmung
    kind: dedication
    title: Widmung          # frei wählbar; die ID bleibt
    path: matter/widmung.md
  back_matter:
  - id: mat-danksagung
    kind: acknowledgments
    title: Danksagung
    path: matter/danksagung.md
  chapters: [...]
```

```yaml
---
id: mat-widmung
kind: dedication
title: Widmung
status: planned          # wie bei Abschnitten
approvals:
  writing: false
  section: false         # Freigabe des Teils
# nur Vorwort und Nachwort (#58), beide optional, am Ende rechtsbündig gesetzt:
# byline: Dr. Maria Muster          # Verfasser, wenn nicht der Autor des Buchs
# place_date: Graz, im Oktober 2026
---
```

**Glossar:** Unter `## Manuskript` optional ein einleitender Absatz, dann je Begriff ein Listeneintrag `- Begriff: Erklärung` (Folgezeilen eingerückt). Beim Satz werden die Einträge alphabetisch nach DIN 5007-1 sortiert (Umlaute wie die Grundbuchstaben, ß wie ss, Groß/klein egal) und als Beschreibungsliste gesetzt (PDF `description`, DOCX-Formate „Definition Term“/„Definition“, EPUB `dl` im Abschnitt mit Rolle `glossary`). Ein Begriff darf nur einmal vorkommen (Groß/klein egal); Prüfung, Freigabe und Auflage melden Doppelungen. `scripts/matter.py glossary-set|glossary-remove` ändert einzelne Einträge und schreibt sie sortiert zurück.

**Verweise aufs Glossar** (#107): Im Manuskript eines Abschnitts oder Teils markiert `[Begriff]{.glossar}` einen Begriff, `[Beugungsform]{.glossar term="Begriff"}` eine gebeugte Form (Groß/klein egal). In EPUB, Bildschirm-PDF und DOCX wird daraus ein Link zum Eintrag (Anker `gl-<slug>`), im Druck-PDF nur die Kennzeichnung nach `typesetting.glossary_marks`. Steht kein freigegebenes Glossar in der Ausgabe, bleibt nur der Text; fehlt ein verwiesener Begriff im Glossar, verhindert das die Auflage.

Darunter `## Ziel` und `## Manuskript` (der Text fürs Buch). Jede Art gibt es höchstens einmal; `scripts/matter.py add` legt Datei und Eintrag an, in der Reihenfolge der Tabelle. Nur freigegebene Teile kommen in eine Auflage; ein nicht freigegebener Teil fehlt darin und wird bei der Prüfung genannt, offene Marker in einem freigegebenen Teil verhindern die Auflage. Der Probedruck zeigt alle Teile mit Statusvermerk. Ghostwriting und Recherche gibt es für Vorwort, Prolog, Epilog und Nachwort wie bei Abschnitten, fürs Glossar Vorschläge und Recherche je Begriff (Lauf-Dateien unter `matter/research/<mat-id>/run-NNN.md` bzw. `matter/writing/<mat-id>/run-NNN.md`); Widmung und Danksagung schreibt der Autor selbst (Ghostwriting nur auf ausdrücklichen Wunsch). EPUB: eigene Abschnitte mit den Rollen `dedication`, `foreword`, `prologue`, `epilogue`, `afterword`, `glossary`, `acknowledgments`.

## KI-Angabe im Buch

Ob und wie das Buch angibt, wie bei ihm KI genutzt wurde, ist eine Einstellung des Autors je Buch (#78). Getrennt davon und nie im Buch: der Hinweis auf die Entwicklung von GhostWriter (`templates/branding.yml`).

```yaml
ai_disclosure:
  mode: short            # none | short (ein Satz) | detailed (je Aufgabe) | custom (eigener Text)
  placement: imprint     # imprint | foreword (Ende des Vorworts) | afterword (Ende des Nachworts) | page (eigene Seite am Ende)
  name_services: true    # Dienste namentlich nennen
  text: "Bei der Entstehung dieses Buchs wurden KI-Werkzeuge für Recherche und Textentwürfe eingesetzt (Perplexity). …"
```

`scripts/ai_disclosure.py suggest` schlägt den Wortlaut aus den Köpfen der Lauf-Dateien vor (`type` → Aufgabe, `provider` → Dienst aus `providers.yml`; `chat` erscheint als „ein Chat-Assistent“). Ins Buch kommt nur `text`, also ein bestätigter Wortlaut; ändern sich `mode` oder `name_services`, leert `set` ihn wieder. Satz: im Impressum als weitere Zeilen, am Ende von Vorwort bzw. Nachwort vor Verfasser und Ort/Datum (Block `::: ki-angabe`), als eigene Seite „Hinweis zur KI-Nutzung“ unnummeriert am Ende; in allen drei Formaten und im Probedruck. Ist eine Angabe gewählt, verhindern ein fehlender Wortlaut oder ein fehlender Ort (Impressum ausgeschaltet, kein freigegebenes Vorwort bzw. Nachwort) die Auflage.

## Illustrationen

Bilder zu Abschnitten und Teilen von Vor- und Nachspann (#54). Je Bild die Datei `img-<slug>.png|jpg` und die Beschreibung `img-<slug>.yml` im Ordner `chapters/<kapitel>/images/<section-id>/` bzw. `matter/images/<mat-id>/`, Schema [`schemas/image.schema.json`](../schemas/image.schema.json):

```yaml
id: img-opi-und-strolchi-auf-der-bank
section_id: sec-01-01-…
file: img-opi-und-strolchi-auf-der-bank.png
caption: Opi und Strolchi auf der Bank   # Bildunterschrift
alt: Opi und Strolchi auf der Bank       # Alternativtext (EPUB)
status: draft                            # draft | approved
ai_generated: true
source: copy                             # chat (im Chat erzeugt) | copy (Auftrag bei einem anderen Dienst) | own (eigenes Bild)
provider: openai
prompt: "Stil: …"
characters: [char-opi, char-strolchi]
run: run-001
width_px: 3000
height_px: 2100
```

Jeder Bildauftrag ist ein unveränderlicher Lauf `run-NNN.md` daneben (`runs.illustration` in `workflow.yml`, Pfad `chapters/{chapter_id}/images/{section_id}/run-{sequence}.md`): Prompt, Dienst, Herkunft, Figuren, Zahl der Varianten, Auswahl. Im Manuskript steht das Bild als `![](bild:img-…)` an seiner Stelle (eigener Absatz); die Bildunterschrift kommt aus der Beschreibung, ein Text in den eckigen Klammern ersetzt sie. Im Buch: volle Satzbreite mit Bildunterschrift in PDF, DOCX und EPUB. Nur freigegebene Bilder (Freigabe-Art `image` in `approvals.yml`) kommen in eine Auflage; ein fehlendes oder nicht freigegebenes Bild in freigegebenem Text verhindert sie, der Probedruck zeigt alle mit Vermerk. Unter etwa 300 dpi bei voller Satzbreite gibt der Bau einen Hinweis. KI-erzeugte Bilder nennt das Impressum („Die Abbildung ist mit KI erzeugt (Dienst).“), außer `images.credit_in_imprint: false`. Neue Uploads nach D13: PNG/JPEG, maximal 20.000.000 Bytes pro Datei; ab 500.000.000 Bytes Bildbestand Bestätigung je weiterem Upload. Originale werden unverändert aufbewahrt, bei bestätigter Verkleinerung separat unter `originals/` im Bildordner. Optionale Metadaten `original_file` und `original_sha256` sichern Zuordnung und Fingerabdruck; alte Bilder ohne diese Felder bleiben gültig. `--confirm-resize` bestätigt die Verkleinerung, `--confirm-large-collection` den Upload ab der Warnschwelle. Ohne nötige Bestätigung werden keine Bilddateien angelegt. Pillow ist für Bildprüfung und Verkleinerung erforderlich; die Prüf-Action installiert es. Referenzbilder nutzen dieselben Upload-/Bestandsgrenzen und bleiben unverändert. Keine automatische Entfernung aus der Git-Historie.

`scripts/images.py` setzt den Bild-Auftrag zusammen (`prompt`: Bildstil, Szene und die festen Bildmerkmale `visual` der Figuren aus #53), legt Bilder ab (`add`, verkleinert auf `max_px`) und listet sie.

## Rückgaben von Chat-Analysen

Der [Anbieter-API-freie Analyseweg](CHAT-ANALYSEN.md) verwendet `analysis/chat-returns/<request_id>/request.json` als unveränderte Auftragsbasis und nach Inhaltsfingerabdruck benannte Ergebnis-JSONs. Ein Ergebnis hat `status: proposal`, `verified`, `dropped_without_evidence`, `source_commit`, `chapter_id` und `external_claims_checked: false`. Es ist weder ein Manuskript noch ein Freigabeeintrag. Bestehende API-Analyseformate bleiben unverändert; neue Rückgaben werden nicht ungeprüft als deren offene Läufe ausgegeben.

## Projektweite visuelle Referenzen

Referenzbilder sind keine Illustrationen und werden nicht automatisch in Manuskript oder Ausgabe übernommen. Sie liegen getrennt unter `reference-images/ref-img-<slug>.png|jpg` mit einer gleichnamigen YAML-Beschreibung nach [`schemas/reference-image.schema.json`](../schemas/reference-image.schema.json). Ein Bild kann mehrere Rollen (`visual_reference`, `book_image`) und mehrere Zuordnungen (Projekt, Person/Figur, Ort, Gegenstand, Szene, Kapitel, Abschnitt) haben.

Der Status beginnt immer mit `stored`. Nur eine ausdrückliche Freigabe setzt `approved`; ein Rückzug setzt `withdrawn`, löscht aber weder Bild noch Historie. Nur `approved`-Bilder mit Rolle `visual_reference` dürfen für einen neuen Erstellungsauftrag ausgewählt werden. Die Auswahl erfolgt je Auftrag explizit über `scripts/reference_images.py select` bzw. `scripts/images.py prompt --references …`. Vergangene Aufträge behalten ihre Auswahl unabhängig von späteren Statusänderungen.

Die aktuelle CLI verwaltet die Dateien und erzwingt Freigabe und Auswahl. Die Übergabe der Bildbytes an den Bilddienst und ein authentifizierter API-Upload sind noch nicht implementiert; ein Dateipfad oder eine Textbeschreibung ist keine tatsächliche Bildreferenzübergabe.

## Figuren

Optional auf Buch-Ebene (#53), etwa für Romane, Kinderbücher oder Fallbeispiele. Je Figur eine Datei `characters/char-<slug>.md` (Vorlage `templates/character.md`, Schema [`schemas/character.schema.json`](../schemas/character.schema.json)); `characters/` gehört dem Buch.

```yaml
---
id: char-opi
name: Opi
role: supporting        # main (Hauptfigur) | supporting (Nebenfigur) | minor (Randfigur)
short: Strolchis Besitzer, lebt am Waldrand
age: '78'
appearance: groß, weißer Bart
traits: [geduldig, brummig]
voice: bedächtig, sagt oft „na, schau an“
visual: weißer Bart, grüner Filzhut, karierte Weste   # gleich bleibende Bildmerkmale (#54)
relations:
- to: char-strolchi
  kind: Besitzer          # „Opi ist Besitzer von Strolchi“
---
```

Darunter `## Beschreibung` und `## Notizen`. Abschnitte und Teile von Vor- und Nachspann nennen ihre Figuren im Kopf: `characters: [char-strolchi, char-opi]`. Die Prüfung kontrolliert Dateien, IDs, Namen, Beziehungen und diese Verweise. `scripts/characters.py` legt Figuren an (`add`), ordnet sie zu (`assign`), speichert das Formular (`update`) und gibt den Kontext für KI-Läufe aus (`context <abschnitt>`). Figuren kommen nicht ins Buch.

## Übersichtsdatei

`ghostwriter-index.json` wird von `scripts/build_index.py` erzeugt, im Repository von der Action „Übersichtsdatei aktualisieren“ (`.github/workflows/index.yml`) nach jedem Push, der Buchdateien ändert. Sie enthält je Kapitel und Abschnitt Status, Freigaben, Kosten-Summen (Betrag, Schätzkennzeichen, Text) und Markerzahlen je Art, dazu Projektsumme, Auflage und `workflow.current_*`, bei Vor- und Nachspann unter `matter` je Teil Art, Bereich, Titel, Status, Freigaben und Marker, bei Figuren unter `characters` je Figur ID, Name, Rolle und wo sie vorkommt, aber keinen Manuskripttext und keine Zeitstempel. Die Prüf-Action meldet eine veraltete Datei als Hinweis. Ohne Kapitel gibt es keine Übersichtsdatei.

## Freigabe-Protokoll

`approvals.yml` hält jede erteilte oder zurückgenommene Freigabe als eigenen Eintrag fest (`workflow.yml`: `record_approval_actor_and_timestamp`, `user_approval_record`). Einträge werden nur angehängt. Die Felder `approvals.writing` und `approvals.section` im Kopf der Abschnittsdatei und der Kapitelstatus zeigen den aktuellen Stand; das Protokoll zeigt, wer wann welchen Stand bestätigt hat. Abschnitts- und Vor-/Nachspann-Freigaben speichern im `note`-Feld zusätzlich `content_sha256=<sha256>` der von `section_file` gelesenen, außen getrimmten UTF-8-Fassung des Textes unter `## Manuskript`. Fehlt er oder stimmt er nicht mehr, ist der Abschnitt nicht freigegeben und darf nicht in eine Auflage gelangen. Vor einer Textänderung ist die Freigabe ausdrücklich zurückzunehmen. Schema: [`schemas/approvals.schema.json`](../schemas/approvals.schema.json); Ablauf: `START.md`, „Freigaben“.

Verweist ein historischer Eintrag auf ein nicht mehr vorhandenes Ziel, kann er unter `historical_references` mit seiner **einbasierten** `entry`-Nummer, unverändertem `kind` und `id` sowie einer `reason` dokumentiert werden. Der Eintrag selbst bleibt unverändert. Die Markierung gilt nur für diesen konkreten Protokolleintrag und erteilt keine Freigabe; unbekannte, nicht dokumentierte Verweise bleiben Validierungsfehler. Vor dem Eintrag den Sachverhalt anhand der Historie prüfen; keine Zuordnung zu einem neuen Abschnitt erfinden.

```yaml
entries:
- kind: section          # writing | section | chapter | matter (Vor-/Nachspann) | image (Illustration)
  id: sec-02-04-die-scham-die-wir-mitbringen
  action: granted        # granted | revoked
  at: '2026-10-31T23:30:00+01:00'
  by: ploeffler          # GitHub-Login, sonst chat
  commit: 06e780b…       # bestätigter Stand (expected_head_sha)
```

## Marker im Manuskript

Offene Prüfpunkte stehen als Marker in eckigen Klammern direkt im Manuskript, mit optionalem Hinweis nach dem Doppelpunkt, z. B. `[QUELLE PRÜFEN: Band, Seiten, DOI]`. Es gibt vier Arten:

| Marker | Art | Bedeutung |
|---|---|---|
| `[PLATZHALTER-ANEKDOTE …]` | `anekdote` | durch ein eigenes Erlebnis der Autorin oder des Autors ersetzen |
| `[QUELLE PRÜFEN …]` | `quelle` | Quelle oder Beleg vor Veröffentlichung prüfen |
| `[MEDIZIN PRÜFEN …]` | `medizin` | medizinische Aussage fachlich prüfen |
| `[RECHT PRÜFEN …]` | `recht` | rechtliche Aussage, Leistung oder Zuständigkeit prüfen |

Die Kapitelansicht zählt die Marker je Abschnitt und Art, das Abschnittsformular listet sie einzeln. Ein Abschnitt mit offenen Markern sollte nicht freigegeben werden.

## Recherchelauf

Jeder Lauf ist eine eigene Datei und wird nicht überschrieben. Empfehlenswerte Inhalte:
- Fragestellung und Suchumfang;
- Datum;
- Quellen mit Titel, Herausgeber, URL und Abrufdatum;
- Ergebnisse und Belegstellen;
- Unsicherheiten und Widersprüche;
- offene Fragen;
- Vorschläge für den Abschnitt.

## Kapitelrecherche

Eine Recherche für ein ganzes Kapitel (Formular „Kapitelrecherche“, `START.md`) ist eine eigene Datei `chapters/<kapitel>/research/kapitel/run-NNN.md` aus `templates/chapter-research-run.md` und wird nie überschrieben. Im Kopf: `task` (`goal` Ziel recherchieren, `sections` Abschnitte erstellen, `summary` Kurzbeschreibung erstellen, leer = nur Fragestellung), `question`, `scope`, `weight_prev` und `weight_next` (Gewichtung des vorherigen und nächsten Kapitels: 0 nicht berücksichtigen, 1 abgrenzen, 2 anschließen, 3 stark einbeziehen) und `context` (einbezogene Nachbarkapitel). Pflichtabschnitte: `## Kurzfassung`, `## Vorschlag: Ziel des Kapitels`, `## Vorschlag: Kurzbeschreibung`, bei `sections` `## Vorschlag: Abschnitte` (je Zeile `- Titel: Kurzbeschreibung`). Der Lauf ändert nie Ziel, Kurzbeschreibung, Abschnitte oder Status; erst „Speichern“ bzw. „Ausgewählte Abschnitte anlegen“ im Formular. Neue Abschnitte kommen ans Ende, vorhandene bleiben unverändert.

## Ghostwriting-Lauf

Ab v0.4 protokolliert jeder Ghostwriting-Lauf („Sofort“, `START.md`) eine eigene Datei `chapters/<kapitel>/writing/<abschnitt>/run-NNN.md` aus `templates/writing-run.md`: Anbieter, Modell, Grundlage (verwendete Recherche- und Brainstorming-Läufe, Schreibfreigabe), Ergebnis (Wörter, neue Marker, Statuswechsel) und Hinweise. Der Text selbst steht nur im Manuskript der Abschnittsdatei. Ein Lauf setzt die Schreibfreigabe voraus und erteilt nie eine Freigabe. Kosten entstehen nur bei Aufrufen über das Backend (siehe „AI-Kostenprotokoll“).

## Brainstorminglauf

Jeder Lauf ist eine eigene Datei. Empfehlenswerte Inhalte:
- Ziel des Brainstormings;
- Ideen und Perspektiven;
- Argumentationslinien;
- Beispiele;
- offene Fragen;
- verworfene Ideen mit kurzer Begründung;
- ausgewählte Ergebnisse.

## Fact-Checking

Optional pro Abschnitt. Modi können sein:
- `none`
- `standard`
- `deep`
- `scientific`

Fact-Checking erzeugt einen Bericht mit bestätigten, unzureichend belegten, widersprüchlichen und möglicherweise falschen Aussagen. Der Bericht ändert den Manuskripttext nicht automatisch.

## Freigaberegeln

- Schreiben erst nach abgeschlossener Recherche und Brainstorming sowie Schreibfreigabe.
- Abschnittsfreigabe nur durch ausdrückliche Benutzerbestätigung.
- Kapitelzusammenführung erst, wenn alle Abschnitte `approved` sind.
- Kapitelabschluss nur nach ausdrücklicher Gesamtfreigabe.
- Neue Abschnitte in einem freigegebenen Kapitel setzen den Kapitelstatus auf `in_progress`.


## Bibliothek: mehrere Bücher, je Buch ein Branch

Seit v0.6 (#36) kann ein Repository mehrere Bücher enthalten. Jedes Buch liegt auf einem eigenen Branch und hat dort dieselben Dateien wie ein Einzelbuch (`ghostwriter.yml`, `chapters/` …). Namen und Regeln stehen in `ghostwriter-manifest.yml` → `library` und `scripts/library.py`.

| Begriff | Name | Beispiel |
|---|---|---|
| Buch-Branch | `buch/<slug>`, Slug aus dem Kurztitel wie der Tag-Slug der Auflagen | `buch/adhs-im-erwachsenenleben` |
| Arbeits-Branch | `ghostwriter/<buch-branch>` | `ghostwriter/buch/adhs-im-erwachsenenleben` |
| Standard-Branch | im Bibliotheksmodus nur Programm und Starter (keine Kapitel) | `main` |

**Erkennungsregel** (gilt gleich für Bücherregal, Update-Action und Wiedereinstieg):

0. Der Standard-Branch ist ein Buch, wenn er Kapitel hat (Einzelbuch); sonst enthält er nur das Programm (Bibliothek, Hauptrepository).
1. Branches aus `update.skip_branches` sind nie Bücher.
2. Jeder `buch/*`-Branch mit `ghostwriter.yml` ist ein Buch, auch ohne Kapitel (Status „im Aufbau“).
3. Jeder andere Branch mit Kapiteln ist ein Buch (Altbestand wie `test/test-book`, Einzelbuch auf dem Standard-Branch).

**Eindeutigkeit:** Ein Kurztitel bzw. sein Slug darf in einer Bibliothek nur einmal vorkommen, weil die Auflagen-Tags (`<slug>-auflage-N`) sonst kollidieren. `python scripts/library.py name "<Kurztitel>"` prüft das vor dem Anlegen, `python scripts/library.py check` prüft die ganze Bibliothek (in `validate.yml`). Freigaben, Kosten, Auflagen und alle Schreibregeln gelten je Buch-Branch unverändert.

**Bücherregal** (`library.json` auf dem Standard-Branch, #37): `python scripts/library.py build` schreibt je Buch `branch`, `title`, `title_short`, `slug`, `author`, `status` (`ready` | `setup`), `current_edition`, `chapters_total`/`chapters_approved`, `sections_total`/`sections_approved`, `cost` (wie in der Übersichtsdatei), `pending` (nicht-automatische Benutzer-Commits im Arbeits-Branch; `index.build` und `update` zählen nicht), `updated_at` und `last_commit` (letzter Commit), `data_version` und `migration_pending`, `auto_merge`, `last_edition` (`tag`, `number`, `date`); dazu `program` (`version`, `upstream`, `ui_version`, `ui_commit`, `last_update`, `skipped_workflows`), `secret_names` und – nur in der Action, aus den Namen der Secrets – `secrets` (`{name: true|false|null}`, nie Werte; `null` = eigener, nicht in `providers.yml` bekannter Name; Seite „Daten“, #71). Die Actions prüfen dafür jeden bekannten Namen einzeln (`scripts/secret_check.py`), nie mit `toJSON(secrets)`. Kein Manuskripttext. Die Action „Bücherregal aktualisieren“ hält sie aktuell; im Hauptrepository läuft sie nicht.

**Serien** (`series/<ser-id>/series.yml` auf dem Standard-Branch einer Bibliothek, #116; Schema `schemas/series.schema.json`): `id` (`ser-…`, bleibt beim Umbenennen), `title`, `subtitle`, `kind` (`continuous` | `standalone`), `description`, `volumes` (Buch-Branches in Bandreihenfolge). Ein Buch gehört zu höchstens einer Serie; Serien gibt es nur in Bibliotheken (nicht im Einzelbuch). Das Buch speichert keine Zugehörigkeit. In `library.json` stehen die Serien unter `series` (`id`, `title`, `subtitle`, `kind`, `description`, `volumes`) und je Buch `series` und `volume`. `validate_project.py` prüft `series/` auf dem Standard-Branch, `library.py check` zusätzlich, ob die Bände Bücher der Bibliothek sind. Gemeinsame Inhalte: `series/<ser-id>/characters/char-*.md` (Figuren, Aufbau wie `characters/`, Schema `schemas/character.schema.json`) und `series/<ser-id>/glossary.yml` (`terms`: Liste `{term, text}`, sortiert nach DIN 5007-1). Eine Figur eines Bandes mit derselben ID wie eine Figur der Serie ist deren Kopie und gilt nur dort; ein Begriff im Glossar eines Bandes mit demselben Wort ist entsprechend dessen Fassung. **Sammelband** (`series/<ser-id>/omnibus.yml`, Schema `schemas/omnibus.schema.json`): `title`, `subtitle`, `status` (`draft` | `approved`), `volumes` (Liste `{branch, edition}`; ohne `edition` die neueste Auflage), `keep_matter` (Teile von Vor- und Nachspann der Bände, die bleiben; Vorgabe `prologue`, `epilogue`), `foreword`, `afterword`, `publication`, `typesetting` (sonst wie Band 1), `formats`, `current_edition`. Gebaut von `scripts/build_omnibus.py` (Action „Sammelband veröffentlichen“), Tag `<reihen-slug>-sammelband-auflage-N`; `edition.yml` nennt die enthaltenen Bandauflagen (`volumes`). Weitere Felder der Serie: `issn` (ISSN der Reihe, im Impressum jedes Bandes) und `also_in_series` (Seite „Ebenfalls in dieser Reihe“, Vorgabe `true`). Neuer Marker `[KONTINUITÄT PRÜFEN: …]` (Widerspruch zu einem Vorband) zählt wie die anderen offenen Marker; in der Übersichtsdatei als `markers.kontinuitaet`.

**Assistenten-Profil** (`assistant.yml` auf dem Standard-Branch, #136; Schema `schemas/assistant.schema.json`): `format` (1), `repo` (owner/name, Wert für `render_view.py --repo`), `skill` (Name des persönlichen Skills, `<autor>-auf-<repo>`, bleibt beim Ändern des Autors gleich), `git` (`name`, `email` für Commits des Assistenten), `author` (Vorbelegung bei „Neues Buch“, außer in einer Serie), `voice` (Standard-Erzählstimme: `text` bis 2000 Zeichen, dazu wahlweise `perspective`, `tense`, `address`, `register`, `tone`, `features` wie beim Stilprofil `style`), `upstream` (wohin Fehler gemeldet werden; fehlt = `upstream.repo` des Manifests). Das optionale `startup` konfiguriert den Instanz-Einstieg: `client` (`openwebui`, `chatgpt`, `claude`, `text`) und `tools` mit `read_start` und `read_file` (tatsächliche Werkzeugnamen). Fehlende Zuordnungen bleiben unbekannt. Der Update-Lauf erzeugt damit die kurze `START.md` und die Anweisungsmodule unter `docs/start/`; Details in [GhostWriter-Updates](UPDATES.md#erzeugter-instanz-einstieg). Keine Secrets, keine Manuskripttexte. Daraus erzeugt `scripts/assistant.py` den persönlichen Skill `.claude/skills/<skill>/SKILL.md` (Vorlage `templates/assistant-skill.md`); `validate_project.py` prüft, dass er zum Profil passt. Vorrang beim Schreiben: Vorgaben im Abschnitt, dann `style` des Buchs, dann `voice`. Profil und persönlicher Skill gehören dem Buch; Updates bringen nur `CLAUDE.md`, `AGENTS.md` und den allgemeinen Skill `.claude/skills/ghostwriter/`.

**Einzelbuch** (bisheriger Weg): Der Standard-Branch ist selbst das Buch. Das bleibt gültig; die Umwandlung in eine Bibliothek ist #40.

## Automatische Prüfung

`scripts/validate_project.py` prüft ein Buchprojekt gegen die Schemas in `schemas/` (`ghostwriter.schema.json`, `section.schema.json`, `costs.schema.json`): Projektdatei, Kopf jeder Abschnittsdatei, Übereinstimmung von IDs, Titeln und Nummern mit `structure.chapters`, Verweise in `workflow` und alle Kostendateien. Die GitHub Action „Projektdateien prüfen“ führt die Prüfung bei jedem Push aus. Ein späteres Backend kann dieselben Schemas verwenden.

## Verbindliche Workflow-Definition

Die kanonische maschinenlesbare Definition der Zustände, Übergänge, Freigabeschranken und GitHub-Automatisierung liegt in [`workflow.yml`](../workflow.yml). Ihre Struktur wird durch [`schemas/workflow.schema.json`](../schemas/workflow.schema.json) beschrieben. Die Erläuterung steht in [`docs/WORKFLOW-MODEL.md`](WORKFLOW-MODEL.md).

Bei Abweichungen gilt:
1. Globale KI-Qualitätsregeln aus `ghostwriter.yml` dürfen durch Workflow- oder Abschnittsregeln nicht abgeschwächt werden.
2. `workflow.yml` ist maßgeblich für Statusübergänge, Freigaben und Automatisierungsregeln.
3. Dieses Dokument beschreibt Dateipfade und Datenkonventionen; es ersetzt nicht die Workflow-Definition.


## Auflagen

Eine Auflage ist ein Pull Request, der `project.current_edition` auf N erhöht und die Release Notes in `editions/auflage-N.md` ablegt (`START.md`, „Neue Auflage“). Nach dem Merge baut die Action „Auflage veröffentlichen“ (`.github/workflows/edition.yml`) aus den freigegebenen Kapiteln PDF, DOCX und EPUB (`scripts/assemble.py`, `scripts/build_edition.py`, Vorlagen in `templates/book/`), legt den Tag `<kurztitel-slug>-auflage-N` an und hängt die Dateien an das Release. Der Buchsatz folgt `typesetting`. Was ins Buch kommt: Kapiteltitel, Untertitel, der Text unter `## Manuskript` jedes freigegebenen Abschnitts und die Quellen der Kapitel-README, dazu die freigegebenen Teile von Vor- und Nachspann aus `matter/` (siehe „Vor- und Nachspann“); nicht der Abschnitt „Vorspann“ einer Kapitel-README, Ziele, Prüflisten oder Arbeitsdateien. `edition.yml` im Ausgabeordner nennt neben den Kapiteln die gesetzten Teile (`matter`). Zitatblöcke, die mit **Merkkasten** beginnen, werden als Kasten gesetzt.

Offene Marker im freigegebenen Text verhindern eine Auflage (entschieden am 01.11.2026). Für Zwischenstände gibt es den **Probedruck** (`scripts/build_edition.py --proof`, Action „Probedruck“): alle Kapitel und Abschnitte mit Statusvermerk, Marker hervorgehoben, „Probedruck – nicht zur Veröffentlichung“ in der Fußzeile, ohne Tag und Release; die Dateien stehen 14 Tage am Lauf der Action zum Download.

## AI-Kostenprotokoll

Erfasst werden nur zusätzliche KI-API-Kosten für Anbieteraufrufe über das GhostWriter-Backend (#13, Erfassungsbereich in [WORKFLOW-MODEL.md](WORKFLOW-MODEL.md#ai-kosten-und-nutzungsverbrauch)); Arbeit im Chat über Abos erzeugt keinen Eintrag. Jeder solche Aufruf erhält einen eigenen Kosteneintrag, der über die stabile `section_id` einem Abschnitt zugeordnet wird. Die Einträge sind unveränderlich und enthalten mindestens Aktivitäts-ID (projektweit eindeutig, Schutz vor Doppelzählung), Zeitpunkt, Herkunft (`source`), Anbieter, Modell, Aktivitätstyp, Abschnitts-ID, Währung, Betrag und Kostenstatus. `run_id` verweist auf den Lauf, `request_id` auf den Aufruf beim Anbieter; `synthetic: true` kennzeichnet erfundene Testdaten. Token- und sonstige Nutzungsdaten sowie Preisgrundlage und Preisquelle werden ergänzt, soweit verfügbar.

Die Abschnittssumme wird aus den Einträgen berechnet. Die Kapitelsumme ist die Summe seiner Abschnittssummen; die Projektsumme addiert die Kapitelsummen und separat ausgewiesene projektweite Kosten. Es gibt keine manuell duplizierten Kapitel- oder Projektbuchungen. Tatsächliche, geschätzte und manuell erfasste Kosten sind unterscheidbar. Originalwährung und Umrechnungsdaten bleiben nachvollziehbar.

### Manuskript-Import (#124)

**Aufbewahrung nach D21:** Originale bleiben bis zu einem ausdrücklichen Löschauftrag erhalten. Historische Werte `keep`/`keep_until` beschreiben frühere Fristen, autorisieren aber keine automatische Entfernung. Der geplante tägliche Entfernungslauf ist entfernt. `expire` verändert ohne `confirmed=True` bzw. CLI `--confirmed` keine Datei. Eine bestätigte Entfernung betrifft nur den Arbeitsstand; frühere Git-Versionen bleiben bestehen.

`scripts/import_book.py` (Action „Manuskript importieren“) legt im Buch-Branch ab: das Original unverändert unter `import/original/`, die Umwandlung `import/manuscript.md` (Bilder in `import/media/`), den Vorschlag `import/proposal.json` (`title`, `author`, `format`, `parts` – Teile von Vor- und Nachspann mit `kind`, `title`, `text`, `words`, `area` –, `chapters` mit `sections` – `title`, `text`, `words`, `scenes` –, `warnings`, `images`, `structure` – `headings` (erkannt), `none` (keine Gliederung), `ai` (KI-Vorschlag übernommen) –, `stats` mit `words_original`, `words_proposal`, `lossless`), bei einem KI-Vorschlag für die Gliederung `import/outline.json` (`run`, `created_at`, `provider`, `model`, `paragraphs`, `fingerprint` der Absätze, `chapters` mit `title`, `start` (Absatz ab 1), `quote`, `reason`, `words`, `sections` – je `title`, `start`, `quote`, `reason`, `words` –, `dropped`, `input_tokens`, `output_tokens`, `cost`, `full_text`, `status` – `open`, `empty`, `applied`, `discarded`; Kosten in `costs/project.yml` mit `run_id` `outline-NNN`) und `import/import.yml` (`source`, `format`, `imported_at`, `keep` – `first_edition`, `30`, `90`, `forever` –, `keep_until`, `words`; nach dem Anlegen `applied_at`, `chapters`, `sections`, `matter`, `writing_approval`, `images`; nach ausdrücklich bestätigter Entfernung `removed_at`). Nichts davon kommt ins Buch.

### Schauplätze, Zeitleiste und Hinweise (#124)

Übernommen aus der Analyse im Hintergrund (Arten `places`, `timeline`, `language`), nie im Buch:

- `story/places.yml` (Schema `schemas/places.schema.json`): `places` = Liste mit `id` (`pl-<slug>`), `name`, `aliases`, `kind` (Art des Orts), `short` (ein Satz aus dem Text), `sections` (IDs der Abschnitte bzw. Teile).
- `story/timeline.yml` (Schema `schemas/timeline.schema.json`): `events` in Buchreihenfolge mit `id` (`ev-NNN`), `section` (ID), `when` (Zeitangabe wie im Text), `what`, `quote` (Fundstelle); `notes` = Hinweise zur zeitlichen Abfolge mit `kind` (`jump`, `contradiction`, `unclear`), `text`, `events` (IDs), `sections`.
- `story/hints.yml` (Schema `schemas/hints.schema.json`): `hints` = Hinweise zu Abschnitten mit `id` (`hi-NNN`), `section` (ID), `source` (`language`), `kind` (`long_sentence`, `repetition`, `same_start`, `filler`), `text`, `quote`; ein neuer Lauf ersetzt die Hinweise der Abschnitte, die er gelesen hat. Das Abschnittsformular zeigt sie; am Text ändert sich nichts.

Die Analyse „Widersprüche“ (`continuity`) schreibt keine eigene Datei, sondern setzt gewählte Marker `[KONTINUITÄT PRÜFEN: …]` ins Manuskript.

`scripts/validate_project.py` prüft alle drei gegen ihr Schema, eindeutige IDs und bekannte Abschnitte.

### Analyse im Hintergrund (#123)

`scripts/analyze.py` (Action „Analyse im Hintergrund“) legt je Art (`kind`: `characters` Figuren, `summaries` Kurzbeschreibung und Ziel je Abschnitt und Kapitel, `style` Stilprofil, `places` Schauplätze, `timeline` Zeitleiste, `continuity` Widersprüche, `language` Sprache ohne KI, #124) im Buch-Branch ab: den Lauf `analysis/{kind}/run-{sequence}.md` (Kopf: `id`, `type: analysis`, `kind`, `scope`, `created_at`, `provider`, `model`, `merge_model` (leer bei Arten ohne Zusammenführen), `blocks_analysed`, `blocks_cached`, `suggestions`, `dropped_without_evidence`, `input_tokens`, `output_tokens`, `cost`, `result`), daneben `run-NNN.json` mit den Vorschlägen (`kind`, `scope`, `run`, `created_at`, `items`; bei Figuren im Format von `render_view.py character-suggest` mit `conflicts`, `groups`; bei Kurzbeschreibungen je Eintrag `level` (`chapter` | `section`), `target` (ID), `number`, `title`, `goal`, `short`, `evidence`; beim Stilprofil je Angabe `field`, `value`, `variants` (`{value, where}`), `evidence`, dazu `stats` mit `words`, `sentence_length_avg`, `dialogue_share`; bei Schauplätzen je Ort `name`, `aliases`, `kind`, `short`, `sections`, `evidence` und `groups`; bei der Zeitleiste je Ereignis `n`, `where`, `when`, `what`, `evidence`, dazu `issues` (`kind` `jump` | `contradiction` | `unclear`, `events` = Nummern, `text`); bei Widersprüchen je Eintrag `text` und `facts` (`about`, `fact`, `where`, `quote`, `n`), dazu `facts` = Zahl der verglichenen Tatsachen; bei Sprache je Hinweis `where`, `kind`, `text`, `quote`; Läufe ohne KI haben `provider` und `model` leer und keine Kosten), den Zwischenspeicher `analysis/cache/{kind}/<block>.json` (je Kapitel bzw. „matter“ ein Fingerabdruck des Textes und die geprüften Angaben) und `analysis/{kind}/applied.yml` (`runs`: übernommene bzw. verworfene Läufe). Kosten je Aufruf in `costs/project.yml` mit `source: action_api`, `run_id` (Figuren `run-NNN`, andere Arten `<art>/run-NNN`), Tokens; sie zählen wie Backend-Kosten zum KI-Budget (#62). Nichts davon kommt ins Buch; übernommen wird nur, was im Chat ausgewählt ist (`analyze.py apply`).

### Ablage

Die Einträge liegen als YAML, eine Datei pro Abschnitt unter `chapters/<kapitel-id>/costs/<abschnitts-id>.yml`; projektweite Kosten, die keinem Abschnitt gehören, in `costs/project.yml`. Neue Einträge werden nur angehängt, bestehende nie verändert. Kapitel- und Projektsummen werden nicht gespeichert, sondern beim Anzeigen berechnet.

```yaml
# chapters/ch-01-endlich-eine-erklaerung/costs/sec-01-04-die-uhr.yml
section_id: sec-01-04-die-uhr
entries:
  - activity_id: act-2026-10-31-001
    occurred_at: "2026-10-31T16:45:00+01:00"
    source: backend_api         # backend_api | action_api (Aufruf aus einer Action, #123) | legacy_chat_estimate (vor v0.4, zählt nicht)
    run_id: run-003             # optional: zugehöriger Lauf
    request_id: req_abc123      # optional: Kennung beim Anbieter
    provider: anthropic
    model: claude-sonnet
    activity_type: research
    section_id: sec-01-04-die-uhr
    currency: EUR
    input_tokens: 5200
    output_tokens: 1400
    cost_amount: 0.12
    cost_status: actual         # actual | estimated | manually_entered | unavailable
```

Kosteneinträge schreibt in v0.5 nur das Backend bzw. der Assistent nach einem kostenpflichtigen Backend-Aufruf; für Chat-Läufe entsteht kein Eintrag. v1.0 ergänzt nach Möglichkeit automatischen Provider-Import, Preisberechnung, Währungsumrechnung und Budgetwarnungen.



## Sitzungssicherungen

`conversations/<session-id>/session.json` ordnet eine Session ihrem Projekt, ursprünglichen Zielbranch und Ausgangscommit zu. Je Thema (`conversation`, `decisions`, `research`, `brainstorming`, `drafts`, `planning`, `section_dialogue`) liegen `latest.json` und unveränderliche `<sha256>.json`-Snapshots vor. Sichtbare Gesprächsbeiträge, Quellen, Entscheidungen, Entwürfe und Lücken bleiben erhalten; keine internen Anweisungen oder Secret-Werte. Diese Daten sind eigene Projektdateien, kein Manuskript und keine Freigabe. Ein Sicherungsbranch `ghostwriter/chat/<session-id>` und ein gemeinsamer PR bündeln die Themen-Commits; keine automatische Übernahme. Befehle und Reparaturablauf stehen in [Session-Sicherung](SESSION-SICHERUNG.md).

## Dauerhafter Buchkontext

`context/book.md` enthält die Buchzusammenfassung; `context/<chapter-id>.md` die jeweilige Kapitelzusammenfassung. Frontmatter: `source_commit` (vollständiger Commit-SHA des gelesenen Quellstands) und `source_digest` (SHA-256 aus dem Kontextplan). Inhalt, Aktualitätsprüfung und Startregel stehen in [CONTEXT.md](CONTEXT.md). Diese abgeleiteten Dateien ersetzen weder Manuskript noch Freigaben. Die feste Grenze von 15.000 Wörtern ist bis einschließlich v1.0 keine Projekteinstellung; Konfiguration folgt erst ab v1.1.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
