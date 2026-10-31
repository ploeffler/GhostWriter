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
│   │   └── costs/
│   │       └── <section-id>.yml   # Kosteneinträge des Abschnitts
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

Jede AI-Aktivität erhält einen eigenen Kosteneintrag, der über die stabile `section_id` einem Abschnitt zugeordnet wird. Die Einträge sind unveränderlich und enthalten mindestens Aktivitäts-ID, Zeitpunkt, Anbieter, Modell, Aktivitätstyp, Abschnitts-ID, Währung, Betrag und Kostenstatus. Token- und sonstige Nutzungsdaten sowie Preisgrundlage und Preisquelle werden ergänzt, soweit verfügbar.

Die Abschnittssumme wird aus den Einträgen berechnet. Die Kapitelsumme ist die Summe seiner Abschnittssummen; die Projektsumme addiert die Kapitelsummen und separat ausgewiesene projektweite Kosten. Es gibt keine manuell duplizierten Kapitel- oder Projektbuchungen. Tatsächliche, geschätzte und manuell erfasste Kosten sind unterscheidbar. Originalwährung und Umrechnungsdaten bleiben nachvollziehbar.

### Ablage

Die Einträge liegen als YAML, eine Datei pro Abschnitt unter `chapters/<kapitel-id>/costs/<abschnitts-id>.yml`; projektweite Kosten, die keinem Abschnitt gehören, in `costs/project.yml`. Neue Einträge werden nur angehängt, bestehende nie verändert. Kapitel- und Projektsummen werden nicht gespeichert, sondern beim Anzeigen berechnet.

```yaml
# chapters/ch-01-endlich-eine-erklaerung/costs/sec-01-04-die-uhr.yml
section_id: sec-01-04-die-uhr
entries:
  - activity_id: act-2026-10-31-001
    occurred_at: "2026-10-31T16:45:00+01:00"
    provider: chat
    model: ""
    activity_type: research
    section_id: sec-01-04-die-uhr
    currency: EUR
    cost_amount: 0.12
    cost_status: estimated      # actual | estimated | manually_entered | unavailable
```

Für v0.5 genügt die manuelle Erfassung mit Summenbildung. v1.0 ergänzt nach Möglichkeit automatischen Provider-Import, Preisberechnung, Währungsumrechnung und Budgetwarnungen.



## Dauerhafter Buchkontext

`context/book.md` enthält die Buchzusammenfassung; `context/<chapter-id>.md` die jeweilige Kapitelzusammenfassung. Frontmatter: `source_commit` (vollständiger Commit-SHA des gelesenen Quellstands) und `source_digest` (SHA-256 aus dem Kontextplan). Inhalt, Aktualitätsprüfung und Startregel stehen in [CONTEXT.md](CONTEXT.md). Diese abgeleiteten Dateien ersetzen weder Manuskript noch Freigaben. Die feste Grenze von 15.000 Wörtern ist bis einschließlich v1.0 keine Projekteinstellung; Konfiguration folgt erst ab v1.1.
