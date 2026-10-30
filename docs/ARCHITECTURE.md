# Ghostwriter – Architektur

## Produktidee

Ghostwriter ist ein chatgesteuerter Schreib- und Rechercheworkflow. GitHub ist persistenter Projektspeicher und Versionsverwaltung; ChatGPT übernimmt Dialog, Planung und inhaltliche Arbeit.

## Benutzerablauf

1. Benutzer erstellt ein Repository aus dem Ghostwriter-Starter (Fork oder Template).
2. Repository kann optional nach einem Arbeitstitel benannt werden.
3. Benutzer verbindet GitHub in ChatGPT, autorisiert den Zugriff und wählt – soweit angeboten – nur das GhostWriter-Repository aus.
4. Ghostwriter prüft den Zugriff, indem es Repository und Projektdateien wie `README.md` und `START.md` liest. Vor der Strukturfreigabe erfolgen keine Schreibtests und keine Projektänderungen.
5. Benutzer startet den Wizard über den Startprompt in `START.md`.
6. Wizard entwickelt Buchkonzept und Kapitel-/Abschnittsstruktur ausschließlich im Chat.
7. Nach ausdrücklicher Freigabe und Bestätigung des Zielrepositorys wird die Struktur übertragen.
8. Danach beginnt der laufende Abschnittsworkflow.

## GitHub-Verbindung und Berechtigungen

- Die ChatGPT-GitHub-Verbindung ist das vorhandene Konto-/App-Connector-Onboarding.
- Die Verbindung muss vom Benutzer in ChatGPT autorisiert werden; Ghostwriter darf keine Passwörter oder Tokens im Chat oder Repository erfragen oder speichern.
- Repository-Zugriff wird vor dem Wizard durch einen Lesezugriff auf das ausgewählte Repository verifiziert.
- Schreibberechtigungen werden nur für die spätere, ausdrücklich freigegebene Übertragung benötigt. Kein künstlicher Schreibtest vor der Freigabe.
- Die maßgeschneiderte GhostWriter-GPT-Action bzw. eigene GitHub-App ist eine separate, spätere Integration und entsteht nicht automatisch durch das Verbinden des GitHub-Connectors.
- Bei fehlendem Zugriff muss der Assistent dies melden und darf keine erfolgreichen Lese- oder Schreibvorgänge behaupten.

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

### 0 – Verbindung und Zugriff prüfen

GitHub verbinden, Repository auswählen und Lesezugriff bestätigen. Keine Repository-Schreiboperation vor der Strukturfreigabe.

### A – Konzeption im Chat

Buchidee, Metadaten, Zielgruppe, Stil, Kapitel und Abschnitte entwickeln. Keine Repository-Änderungen vor Strukturfreigabe.

### B – Repository initialisieren

Nach Freigabe und erneuter Bestätigung des Zielrepositorys README, Konfiguration, Kapitelordner, Kapitelübersichten und Abschnittsdateien erzeugen.

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
- GitHub-Verbindungs-Onboarding und Lesezugriffsprüfung;
- Wizard und Strukturentwicklung;
- explizite Freigabe;
- Repository-Initialisierung;
- stabile Datei- und Statuskonventionen.

Später:
- eigene GPT Actions / GhostWriter-GitHub-App;
- Recherche- und Brainstormingläufe im Repository speichern;
- Abschnittsmanuskripte und Prüfberichte;
- Kapitelzusammenführung;
- automatisierte Validierung via GitHub Actions.
