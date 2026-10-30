# Ghostwriter – Architektur

## Produktidee

Ghostwriter ist ein chatgesteuerter Schreib- und Rechercheworkflow. GitHub ist persistenter Projektspeicher und Versionsverwaltung; ChatGPT übernimmt Dialog, Planung und inhaltliche Arbeit.

## Benutzerablauf

1. Benutzer erstellt ein Repository aus dem Ghostwriter-Starter (Fork oder Template).
2. Repository kann optional nach einem Arbeitstitel benannt werden.
3. Benutzer startet ChatGPT über den Link/Startprompt in `START.md`.
4. Wizard entwickelt Buchkonzept und Kapitel-/Abschnittsstruktur ausschließlich im Chat.
5. Nach ausdrücklicher Freigabe wird die Struktur in das Benutzerrepository übertragen.
6. Danach beginnt der laufende Abschnittsworkflow.

## Architekturprinzipien

- Chat ist die Arbeitsoberfläche, GitHub die persistente Quelle des Projektzustands.
- Projektstruktur und Manuskript sind Dateien, nicht ein monolithisches Dokument.
- Kapitel werden in eigenen Verzeichnissen ausgelagert.
- Jeder Abschnitt ist eine eigenständige Arbeits- und Freigabeeinheit.
- Recherche- und Brainstormingläufe bleiben als Historie erhalten.
- Freigaben sind explizite Meilensteine.
- Bereits freigegebene Inhalte werden nicht stillschweigend verändert.
- Stabile IDs sind unabhängig von sichtbarer Kapitel-/Abschnittsnummerierung.

## Phasen

### A – Konzeption im Chat
Buchidee, Metadaten, Zielgruppe, Stil, Kapitel und Abschnitte entwickeln. Keine Repository-Änderungen vor Strukturfreigabe.

### B – Repository initialisieren
README, Konfiguration, Kapitelordner, Kapitelübersichten und Abschnittsdateien erzeugen.

### C – Abschnittsweise Buchentwicklung
Für jeden Abschnitt: Recherche → Brainstorming → Schreibfreigabe → Schreiben → Überarbeiten → optional Fact-Checking → Abschnittsfreigabe.

Wenn alle Abschnitte eines Kapitels freigegeben sind: Kapitel zusammenführen → Kapitelprüfung und Überarbeitung → Gesamtfreigabe.

## Dynamische Struktur

Jedes Kapitel hat mindestens einen und beliebig viele Abschnitte. Abschnitte können jederzeit hinzugefügt, umbenannt, verschoben, geteilt und neu geordnet werden. Bei Änderungen an einem freigegebenen Kapitel wird dessen Freigabestatus zurückgesetzt. Bestehende freigegebene Texte und Historien bleiben erhalten.

## KI-Qualitätsregeln

Globale Defaults:
- strict: keine erfundenen Fakten/Quellen;
- required: Quellen für externe Tatsachenbehauptungen;
- explicit: Unsicherheiten klar kennzeichnen;
- balanced: ausgewogene Kreativität;
- research: aktive Internetrecherche bei Rechercheaufträgen.

Kapitel- und Abschnittsregeln dürfen ergänzen, aber globale Wahrheits- und Quellenregeln nicht lockern.

## MVP-Grenze

MVP:
- Wizard und Strukturentwicklung;
- explizite Freigabe;
- Repository-Initialisierung;
- stabile Datei- und Statuskonventionen.

Später:
- GPT Actions / GitHub App;
- Recherche- und Brainstormingläufe im Repository speichern;
- Abschnittsmanuskripte und Prüfberichte;
- Kapitelzusammenführung;
- automatisierte Validierung via GitHub Actions.
