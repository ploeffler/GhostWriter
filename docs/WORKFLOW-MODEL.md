# Maschinenlesbares Workflow-Modell

## Zweck und Verbindlichkeit

`workflow.yml` ist die kanonische, maschinenlesbare Definition der GhostWriter-Arbeitsabläufe. Sie legt Zustände, erlaubte Übergänge, Voraussetzungen, unveränderliche Regeln, Historien und GitHub-Automatisierung fest. `ghostwriter.yml` bleibt für konkrete Buchmetadaten und die projektspezifische Konfiguration zuständig.

Die JSON-Schema-Datei unter `schemas/workflow.schema.json` beschreibt die Struktur und validiert zentrale Pflichtfelder und unveränderliche Sicherheitsregeln.

## Zustandsmodell

### Abschnitt

`planned → research → brainstorming → ready_to_write → writing → revision → [fact_check] → ready_for_approval → approved`

Recherche, Brainstorming, Revision und Faktenprüfung können mehrere Läufe bzw. Runden umfassen. Jeder Lauf wird als eigene Datei gespeichert. Faktenprüfung ist optional und verändert den Manuskripttext niemals automatisch.

Der Übergang zu `writing` verlangt eine ausdrückliche Schreibfreigabe. Der Übergang zu `approved` verlangt eine ausdrückliche Abschnittsfreigabe des Benutzers.

### Kapitel

`planned → in_progress → ready_for_assembly → assembly → review → ready_for_approval → approved`

Ein Kapitel kann erst zusammengeführt werden, wenn alle zugehörigen Abschnitte freigegeben sind. Die Kapitelgesamtfreigabe ist eine eigenständige Benutzerentscheidung und wird nicht aus Abschnittsfreigaben abgeleitet.

## GitHub-Aufgaben und Milestones

Für jede konkrete Arbeitseinheit kann ein Issue erzeugt werden. Jedes Issue muss mindestens die Entitäts-ID, den aktuellen und angestrebten Status, Aufgabentyp, einschlägige Anweisungen, Eingaben, Akzeptanzkriterien, betroffene Dateien und gegebenenfalls die Freigabeschranke enthalten.

Milestones gruppieren Arbeit auf Kapitel- oder Projektebene. Das Schließen eines Issues oder das Abschließen eines Milestones ist niemals gleichbedeutend mit einer Benutzerfreigabe.

## Änderungsregeln

Stabile IDs werden unabhängig von sichtbaren Nummern geführt. Nummern werden aus der aktuellen Reihenfolge berechnet. Strukturänderungen bewahren Inhalte und Historie. Löschen und Aufteilen erfordern Bestätigung. Jede strukturelle Änderung an einem freigegebenen Kapitel setzt dessen Freigabestatus zurück.

## Schreib- und Auditregeln

- Keine Schreiboperation ohne die jeweils erforderliche ausdrückliche Freigabe.
- Vor jeder GitHub-Schreiboperation den erwarteten Head-SHA berücksichtigen.
- Mutationen mit Idempotency-Key absichern.
- Erfolg erst nach bestätigter GitHub-Antwort melden.
- Statuswechsel, Freigabeakteur, Zeitstempel und Commit-SHA dokumentieren.
- Globale KI-Qualitätsregeln dürfen lokal nur verschärft, niemals abgeschwächt werden.

## Verhältnis zu bestehenden Dateien

- `START.md`: Gesprächsführung und Onboarding.
- `ghostwriter.yml`: Metadaten und konkrete Buchkonfiguration.
- `workflow.yml`: kanonische Workflow- und Automatisierungsregeln.
- `schemas/workflow.schema.json`: strukturelle Validierung von `workflow.yml`.
- `docs/DATA-MODEL.md`: Dateistruktur und Datenkonventionen.

Die Workflow-Datei definiert das Soll-Verhalten. Sie bedeutet nicht, dass alle beschriebenen Automatisierungen bereits implementiert sind.


## Produkt-Roadmap: v0.5 und v1.0

Die GhostWriter-Produktversion und die Ausgabeversion eines Buches sind getrennte Dinge.

- **GhostWriter v0.5** ist eine bereits nutzbare Basisversion mit diesem Funktionsumfang:
  - ein Projekt erstellen und einrichten,
  - Kapitel erstellen und einrichten,
  - Kapitel und Abschnitte bearbeiten,
  - eine Auflage erstellen und ihren Inhalt als PDF, DOCX und EPUB bereitstellen,
  - AI-Läufe (Recherche, Brainstorming, Schreiben) nur im Modus „Sofort“ direkt im Chat; der Modus „Zeitgesteuert“ über die Cloud-Warteschlange folgt nach v0.5.

  Erweiterte Automatisierung darf die Basisnutzung nicht blockieren.
- **GhostWriter v1.0** ist der geplante Vollausbau: vollständige Workflow-Automatisierung, GitHub-Issue-/Milestone-Steuerung, robuste Freigabe- und Auditmechanismen, wiederholbare Recherche und Faktenprüfung sowie vollständige Export- und Release-Pipeline.
- Die Roadmap beschreibt den Zielumfang; Funktionen gelten erst nach Implementierung und Prüfung als umgesetzt.

### Stufen bis v0.5

Der Weg zu v0.5 ist in fünf Stufen geteilt. Jede endet mit einer Abnahme im Chat mit den Testdaten. Die Stufen sind als GitHub-Milestones `v0.1` bis `v0.5` angelegt, die Arbeitsaufträge als Issues; der ausführliche Plan steht in [GhostWriter v0.5 – Voraussetzungen und Arbeitsaufträge](https://claude.ai/artifact/Dx54iTWGE9nx9KgHUBdfPj).

| Stufe | Ziel | Abnahme |
|---|---|---|
| v0.1 | Datenmodell steht und wird geprüft | Prüf-Action läuft ohne Fehler über das leere Projekt und ein ADHS-Kapitel |
| v0.2 | Testprojekt lesen und anzeigen | Link zum Test-Repo zeigt Übersicht, Kapitel und Abschnitt mit richtigen Summen und Markern |
| v0.3 | Projekt und Kapitel einrichten und bearbeiten | Im leeren Projekt anlegen, umordnen, speichern und mit Bestätigung freigeben; jede Änderung ein Commit |
| v0.4 | AI-Läufe „Sofort“ mit Kosten | Recherche und Ghostwriting für einen ADHS-Abschnitt mit Lauf-Datei, Statuswechsel und Kosteneintrag |
| v0.5 | Auflage und Export | Auflage 2 mit PDF, DOCX und EPUB; Auflage 1 unverändert; Testplan bestanden |

## Buchausgaben als GitHub Releases

Jede veröffentlichte Ausgabe des Buches wird als eigener GitHub Release abgebildet. Ein Release ist ein unveränderlicher Snapshot eines konkreten Repository-Commits mit Release Notes und – soweit erzeugt – PDF-, EPUB- und DOCX-Dateien.

- Ausgaben heißen **Auflagen** und werden mit ganzen Zahlen ab 1 gezählt. Der Release-Name verbindet Kurztitel und Auflage, z. B. „ADHS im Erwachsenenleben – Auflage 1“.
- Der Tag ist daraus abgeleitet: Kurztitel in Kleinbuchstaben, Umlaute umgeschrieben, Leer- und Sonderzeichen als Bindestrich, z. B. `adhs-im-erwachsenenleben-auflage-1`.
- Eine neue Auflage entsteht nur auf ausdrücklichen Wunsch des Benutzers.
- Nur ausdrücklich freigegebene Manuskriptinhalte dürfen veröffentlicht werden.
- Release Notes dokumentieren Änderungen gegenüber der vorherigen Ausgabe.
- Korrekturen werden im Repository gesammelt und erscheinen mit der nächsten Auflage. Veröffentlichte Auflagen werden nicht verändert.
- GhostWriter-Produktversionen (v0.5/v1.0), technische Git-Tags und Buchausgaben sind getrennte Versionsräume.


## AI-Kosten und Nutzungsverbrauch

Jede AI-Aktivität wird als eigener, unveränderlicher Kosteneintrag erfasst und primär einem Abschnitt über dessen stabile ID zugeordnet. Erfasst werden – soweit verfügbar – Anbieter, Modell, Aktivitätstyp, Zeitpunkt, Token-/Nutzungsmenge, Preisgrundlage, Preisquelle und Betrag. Nicht verfügbare Werte werden ausdrücklich als unbekannt markiert; manuelle Eingaben und Schätzungen bleiben als solche gekennzeichnet.

- **Abschnitt:** Summe aller zugeordneten AI-Aktivitäten.
- **Kapitel:** automatisch berechnete Summe der Abschnittssummen.
- **Projekt:** automatisch berechnete Summe aller Kapitelsummen zuzüglich separat ausgewiesener projektweiter Kosten.
- Tatsächliche und geschätzte Kosten werden getrennt ausgewiesen. Originalwährung und Originalbetrag bleiben erhalten; Umrechnungen speichern Wechselkurs und Datum.
- Summen werden aus Einzelbuchungen abgeleitet. Dieselbe Aktivität darf nicht zusätzlich auf Kapitel- oder Projektebene verbucht werden.
- Korrekturen erzeugen nachvollziehbare Gegen- oder Folgeeinträge; historische Buchungen werden nicht stillschweigend überschrieben.

### Ausbaustufen

**v0.5:** einfache manuelle Kostenerfassung, optionale Token-/Nutzungsdaten, Abschnittszuordnung, Kapitelzwischensummen und Projektgesamtbetrag; Kennzeichnung tatsächlicher, geschätzter und manuell eingetragener Kosten.

**v1.0:** automatischer Import von Provider-Nutzungsdaten, modellbezogene Preisberechnung, soweit technisch verfügbar automatische Zuordnung, Währungsumrechnung, detaillierte Berichte sowie Budgetgrenzen und Warnungen.

Die Kostenfunktion muss auch dann nutzbar bleiben, wenn ein Anbieter keine Nutzungsdaten oder Rechnungswerte bereitstellt.
