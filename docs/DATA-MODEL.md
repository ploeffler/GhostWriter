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
| `project.title` | Titel des Buches |
| `project.title_short` | Kurztitel für Badge, Listen und den Namen der Auflagen („Kurztitel – Auflage N“) |
| `project.working_title` | Arbeitstitel, solange kein Titel feststeht |
| `project.subtitle` | Untertitel |
| `project.author` | Autorin oder Autor |
| `project.description_short` | Kurzbeschreibung in einem Satz |
| `project.description` | ausführliche Beschreibung |
| `project.status` | Projektstatus, z. B. `concept` |
| `project.current_edition` | Nummer der letzten erschienenen Auflage, `0` = noch keine |
| `workflow.current_phase` | `wizard` bis zur Strukturfreigabe, danach eine andere Phase |
| `workflow.current_chapter_id`, `workflow.current_section_id` | zuletzt bearbeitete Stelle für den Wiedereinstieg |
| `structure.chapters` | Kapitel in Reihenfolge, je mit `id`, `title`, `path`, `status` und `sections` (je `id`, `title`, `path`) |

| `typesetting` | Buchsatz der Auflagen, in den Projekteinstellungen bearbeitbar (siehe unten) |
| `updates.auto` | neue GhostWriter-Versionen automatisch einspielen; fehlt = `true` ([UPDATES.md](UPDATES.md)) |
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


## Automatische Prüfung

`scripts/validate_project.py` prüft ein Buchprojekt gegen die Schemas in `schemas/` (`ghostwriter.schema.json`, `section.schema.json`, `costs.schema.json`): Projektdatei, Kopf jeder Abschnittsdatei, Übereinstimmung von IDs, Titeln und Nummern mit `structure.chapters`, Verweise in `workflow` und alle Kostendateien. Die GitHub Action „Projektdateien prüfen“ führt die Prüfung bei jedem Push aus. Ein späteres Backend kann dieselben Schemas verwenden.

## Verbindliche Workflow-Definition

Die kanonische maschinenlesbare Definition der Zustände, Übergänge, Freigabeschranken und GitHub-Automatisierung liegt in [`workflow.yml`](../workflow.yml). Ihre Struktur wird durch [`schemas/workflow.schema.json`](../schemas/workflow.schema.json) beschrieben. Die Erläuterung steht in [`docs/WORKFLOW-MODEL.md`](WORKFLOW-MODEL.md).

Bei Abweichungen gilt:
1. Globale KI-Qualitätsregeln aus `ghostwriter.yml` dürfen durch Workflow- oder Abschnittsregeln nicht abgeschwächt werden.
2. `workflow.yml` ist maßgeblich für Statusübergänge, Freigaben und Automatisierungsregeln.
3. Dieses Dokument beschreibt Dateipfade und Datenkonventionen; es ersetzt nicht die Workflow-Definition.


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
