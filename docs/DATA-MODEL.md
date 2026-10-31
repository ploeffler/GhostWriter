# Datei- und Statusmodell

## Vorgeschlagene Projektstruktur

```text
repository/
├── README.md
├── START.md
├── ghostwriter.yml
├── research/
│   └── sources.md
├── brainstorming/
├── chapters/
│   ├── 01-einleitung/
│   │   ├── README.md
│   │   ├── sections/
│   │   │   ├── 01-zielsetzung.md
│   │   │   └── 02-aufbau.md
│   │   └── research/
│   │       └── <section-id>/
│   │           ├── run-001.md
│   │           └── run-002.md
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

## Abschnittsdatei – Frontmatter-Beispiel

```yaml
---
id: sec-01-purpose
number: "1.1"
title: "Zielsetzung"
status: planned
fact_check:
  enabled: false
  level: standard
approvals:
  writing: false
  section: false
---
```

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


## Verbindliche Workflow-Definition

Die kanonische maschinenlesbare Definition der Zustände, Übergänge, Freigabeschranken und GitHub-Automatisierung liegt in [`workflow.yml`](../workflow.yml). Ihre Struktur wird durch [`schemas/workflow.schema.json`](../schemas/workflow.schema.json) beschrieben. Die Erläuterung steht in [`docs/WORKFLOW-MODEL.md`](WORKFLOW-MODEL.md).

Bei Abweichungen gilt:
1. Globale KI-Qualitätsregeln aus `ghostwriter.yml` dürfen durch Workflow- oder Abschnittsregeln nicht abgeschwächt werden.
2. `workflow.yml` ist maßgeblich für Statusübergänge, Freigaben und Automatisierungsregeln.
3. Dieses Dokument beschreibt Dateipfade und Datenkonventionen; es ersetzt nicht die Workflow-Definition.


## AI-Kostenprotokoll

Jede AI-Aktivität erhält einen eigenen Kosteneintrag, der über die stabile `section_id` einem Abschnitt zugeordnet wird. Die Einträge sind unveränderlich und enthalten mindestens Aktivitäts-ID, Zeitpunkt, Anbieter, Modell, Aktivitätstyp, Abschnitts-ID, Währung, Betrag und Kostenstatus. Token- und sonstige Nutzungsdaten sowie Preisgrundlage und Preisquelle werden ergänzt, soweit verfügbar.

Die Abschnittssumme wird aus den Einträgen berechnet. Die Kapitelsumme ist die Summe seiner Abschnittssummen; die Projektsumme addiert die Kapitelsummen und separat ausgewiesene projektweite Kosten. Es gibt keine manuell duplizierten Kapitel- oder Projektbuchungen. Tatsächliche, geschätzte und manuell erfasste Kosten sind unterscheidbar. Originalwährung und Umrechnungsdaten bleiben nachvollziehbar.

Für v0.5 genügt die manuelle Erfassung mit Summenbildung. v1.0 ergänzt nach Möglichkeit automatischen Provider-Import, Preisberechnung, Währungsumrechnung und Budgetwarnungen.
