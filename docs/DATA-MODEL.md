# Datei- und Statusmodell

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
│   │   └── costs/
│   │       └── <section-id>.yml   # KI-API-Kosten über das Backend (nur dann)
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

| `typesetting` | Buchsatz der Auflagen, in den Projekteinstellungen bearbeitbar (siehe unten) |
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

Seitenformat, Schrift und Titelei wirken nur in PDF und DOCX; EPUB übernimmt Inhaltsverzeichnis und Titelei.

### Kapitel-README

Titel, Untertitel (erste kursive Zeile `*…*`), `## Kurzbeschreibung` und `## Ziel des Kapitels` stehen in `chapters/<kapitel>/README.md`; „Offen.“ steht für noch leer. Der Titel steht zusätzlich in `structure.chapters`. „Kapitel bearbeiten“ ändert beides im selben Commit.

Die Struktur von `ghostwriter.yml` beschreibt [`schemas/ghostwriter.schema.json`](../schemas/ghostwriter.schema.json).

## Abschnittsdatei – Frontmatter-Beispiel

```yaml
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

## Übersichtsdatei

`ghostwriter-index.json` wird von `scripts/build_index.py` erzeugt, im Repository von der Action „Übersichtsdatei aktualisieren“ (`.github/workflows/index.yml`) nach jedem Push, der Buchdateien ändert. Sie enthält je Kapitel und Abschnitt Status, Freigaben, Kosten-Summen (Betrag, Schätzkennzeichen, Text) und Markerzahlen je Art, dazu Projektsumme, Auflage und `workflow.current_*`, aber keinen Manuskripttext und keine Zeitstempel. Die Prüf-Action meldet eine veraltete Datei als Hinweis. Ohne Kapitel gibt es keine Übersichtsdatei.

## Freigabe-Protokoll

`approvals.yml` hält jede erteilte oder zurückgenommene Freigabe als eigenen Eintrag fest (`workflow.yml`: `record_approval_actor_and_timestamp`, `user_approval_record`). Einträge werden nur angehängt. Die Felder `approvals.writing` und `approvals.section` im Kopf der Abschnittsdatei und der Kapitelstatus zeigen den aktuellen Stand; das Protokoll zeigt, wer wann welchen Stand bestätigt hat. Schema: [`schemas/approvals.schema.json`](../schemas/approvals.schema.json); Ablauf: `START.md`, „Freigaben“.

```yaml
entries:
- kind: section          # writing | section | chapter
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

**Bücherregal** (`library.json` auf dem Standard-Branch, #37): `python scripts/library.py build` schreibt je Buch `branch`, `title`, `title_short`, `slug`, `author`, `status` (`ready` | `setup`), `current_edition`, `chapters_total`/`chapters_approved`, `sections_total`/`sections_approved`, `cost` (wie in der Übersichtsdatei), `pending` (Commits im Arbeits-Branch) und `updated_at` (letzter Commit). Kein Manuskripttext. Die Action „Bücherregal aktualisieren“ hält sie aktuell; im Hauptrepository läuft sie nicht.

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

Eine Auflage ist ein Pull Request, der `project.current_edition` auf N erhöht und die Release Notes in `editions/auflage-N.md` ablegt (`START.md`, „Neue Auflage“). Nach dem Merge baut die Action „Auflage veröffentlichen“ (`.github/workflows/edition.yml`) aus den freigegebenen Kapiteln PDF, DOCX und EPUB (`scripts/assemble.py`, `scripts/build_edition.py`, Vorlagen in `templates/book/`), legt den Tag `<kurztitel-slug>-auflage-N` an und hängt die Dateien an das Release. Der Buchsatz folgt `typesetting`. Was ins Buch kommt: Kapiteltitel, Untertitel, der Text unter `## Manuskript` jedes freigegebenen Abschnitts und die Quellen der Kapitel-README; nicht Vorspann, Ziele, Prüflisten oder Arbeitsdateien. Zitatblöcke, die mit **Merkkasten** beginnen, werden als Kasten gesetzt.

Offene Marker im freigegebenen Text verhindern eine Auflage (entschieden am 01.11.2026). Für Zwischenstände gibt es den **Probedruck** (`scripts/build_edition.py --proof`, Action „Probedruck“): alle Kapitel und Abschnitte mit Statusvermerk, Marker hervorgehoben, „Probedruck – nicht zur Veröffentlichung“ in der Fußzeile, ohne Tag und Release; die Dateien stehen 14 Tage am Lauf der Action zum Download.

## AI-Kostenprotokoll

Erfasst werden nur zusätzliche KI-API-Kosten für Anbieteraufrufe über das GhostWriter-Backend (#13, Erfassungsbereich in [WORKFLOW-MODEL.md](WORKFLOW-MODEL.md#ai-kosten-und-nutzungsverbrauch)); Arbeit im Chat über Abos erzeugt keinen Eintrag. Jeder solche Aufruf erhält einen eigenen Kosteneintrag, der über die stabile `section_id` einem Abschnitt zugeordnet wird. Die Einträge sind unveränderlich und enthalten mindestens Aktivitäts-ID (projektweit eindeutig, Schutz vor Doppelzählung), Zeitpunkt, Herkunft (`source`), Anbieter, Modell, Aktivitätstyp, Abschnitts-ID, Währung, Betrag und Kostenstatus. `run_id` verweist auf den Lauf, `request_id` auf den Aufruf beim Anbieter; `synthetic: true` kennzeichnet erfundene Testdaten. Token- und sonstige Nutzungsdaten sowie Preisgrundlage und Preisquelle werden ergänzt, soweit verfügbar.

Die Abschnittssumme wird aus den Einträgen berechnet. Die Kapitelsumme ist die Summe seiner Abschnittssummen; die Projektsumme addiert die Kapitelsummen und separat ausgewiesene projektweite Kosten. Es gibt keine manuell duplizierten Kapitel- oder Projektbuchungen. Tatsächliche, geschätzte und manuell erfasste Kosten sind unterscheidbar. Originalwährung und Umrechnungsdaten bleiben nachvollziehbar.

### Ablage

Die Einträge liegen als YAML, eine Datei pro Abschnitt unter `chapters/<kapitel-id>/costs/<abschnitts-id>.yml`; projektweite Kosten, die keinem Abschnitt gehören, in `costs/project.yml`. Neue Einträge werden nur angehängt, bestehende nie verändert. Kapitel- und Projektsummen werden nicht gespeichert, sondern beim Anzeigen berechnet.

```yaml
# chapters/ch-01-endlich-eine-erklaerung/costs/sec-01-04-die-uhr.yml
section_id: sec-01-04-die-uhr
entries:
  - activity_id: act-2026-10-31-001
    occurred_at: "2026-10-31T16:45:00+01:00"
    source: backend_api         # backend_api | legacy_chat_estimate (vor v0.4, zählt nicht)
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



## Dauerhafter Buchkontext

`context/book.md` enthält die Buchzusammenfassung; `context/<chapter-id>.md` die jeweilige Kapitelzusammenfassung. Frontmatter: `source_commit` (vollständiger Commit-SHA des gelesenen Quellstands) und `source_digest` (SHA-256 aus dem Kontextplan). Inhalt, Aktualitätsprüfung und Startregel stehen in [CONTEXT.md](CONTEXT.md). Diese abgeleiteten Dateien ersetzen weder Manuskript noch Freigaben. Die feste Grenze von 15.000 Wörtern ist bis einschließlich v1.0 keine Projekteinstellung; Konfiguration folgt erst ab v1.1.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
