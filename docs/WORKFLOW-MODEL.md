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

- **GhostWriter v0.5** ist eine bereits nutzbare Basisversion: Buchprojekt und Metadaten, Kapitel-/Abschnittsstruktur, Recherche, Brainstorming, Schreiben, Überarbeitung, explizite Freigaben, GitHub-Ablage und einfacher Buch-Export. Erweiterte Automatisierung darf die Basisnutzung nicht blockieren.
- **GhostWriter v1.0** ist der geplante Vollausbau: vollständige Workflow-Automatisierung, GitHub-Issue-/Milestone-Steuerung, robuste Freigabe- und Auditmechanismen, wiederholbare Recherche und Faktenprüfung sowie vollständige Export- und Release-Pipeline.
- Die Roadmap beschreibt den Zielumfang; Funktionen gelten erst nach Implementierung und Prüfung als umgesetzt.

## Buchausgaben als GitHub Releases

Jede veröffentlichte Ausgabe des Buches wird als eigener GitHub Release abgebildet. Ein Release ist ein unveränderlicher Snapshot eines konkreten Repository-Commits mit Release Notes und – soweit erzeugt – PDF-, EPUB- und DOCX-Dateien.

- Tags folgen dem Muster `book-vMAJOR.MINOR[.PATCH]`, z. B. `book-v1.0`.
- Nur ausdrücklich freigegebene Manuskriptinhalte dürfen veröffentlicht werden.
- Release Notes dokumentieren Änderungen gegenüber der vorherigen Ausgabe.
- Korrekturen erzeugen eine neue Ausgabeversion; bestehende Releases werden nicht stillschweigend verändert.
- GhostWriter-Produktversionen (v0.5/v1.0), technische Git-Tags und Buchausgaben sind getrennte Versionsräume.
