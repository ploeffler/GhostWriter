# Ghostwriter – Architektur

## Versionsentscheidung vom 08.11.2026

Bis einschließlich v1.0 sind keine Verbindungen zu KI-Anbieter-APIs vorgesehen. KI-Arbeit erfolgt im Chat oder per „Auftrag kopieren“ mit geprüfter Rückgabe; Anbieterzugänge sind keine Voraussetzung der Abnahme. Die eigene GhostWriter-Schnittstelle und die GitHub-Anbindung sind davon getrennt. Frühere v1.0-Pläne für direkte KI-Aufrufe, zeitgesteuerte Anbieterläufe und automatische Anbieter-Verbrauchsabfragen sind auf die Zeit nach v1.0 verschoben. Maßgeblich sind die [Roadmap und Aufgabenabgrenzung](WORKFLOW-MODEL.md#verbindliche-entscheidung-v10-ohne-ki-anbieter-apis) und `workflow.yml`. Bestehender optionaler Code wird dadurch nicht entfernt.

## Ergänzende Beschlüsse D01–D32

Die [bestätigten Entscheidungen](ENTSCHEIDUNGEN-v1.0.md) verschieben zusätzlich eigene Web-App, Verwaltungsdienst und Offline-Web-App auf nach v1.0. Bis dahin bestehende Client-/GitHub-Anbindungen verwenden; kein eigener Serverbetrieb. Die Branch-Trennung ist intern, ohne Branch-Verwaltung durch Benutzer. Relevante Zustände bleiben sichtbar. [Arbeitsaufträge und Abnahmegrenzen](AUFTRAEGE-v1.0.md) unterscheiden Planung und bereits implementiertes Verhalten.

## Produktidee

Ghostwriter ist ein chatgesteuerter Schreib- und Rechercheworkflow. GitHub ist persistenter Projektspeicher und Versionsverwaltung; ein KI-Chat-Assistent übernimmt Dialog, Planung und inhaltliche Arbeit. Der Workflow ist anbieterunabhängig: Er setzt nur einen Assistenten voraus, der die Anweisungen in `START.md` befolgt.

## Benutzerablauf

1. Benutzer erstellt ein Repository aus dem Ghostwriter-Starter (Fork oder Template).
2. Repository kann optional nach einem Arbeitstitel benannt werden.
3. Benutzer verbindet GitHub in seiner Chat-Anwendung, autorisiert den Zugriff und wählt – soweit angeboten – nur das GhostWriter-Repository aus. Ohne GitHub-Anbindung gibt der Assistent Dateien im Chat aus und der Benutzer committet selbst.
4. Ghostwriter prüft den Zugriff, indem es Repository und Projektdateien wie `README.md` und `START.md` liest. Vor der Strukturfreigabe erfolgen keine Schreibtests und keine Projektänderungen.
5. Benutzer startet den Wizard über den Startprompt in `START.md`.
6. Wizard entwickelt Buchkonzept und Kapitel-/Abschnittsstruktur ausschließlich im Chat.
7. Nach ausdrücklicher Freigabe und Bestätigung des Zielrepositorys wird die Struktur übertragen.
8. Danach beginnt der laufende Abschnittsworkflow.

## GitHub-Verbindung und Berechtigungen

- Die GitHub-Verbindung ist die vom jeweiligen Chat-Anbieter bereitgestellte Verbindung (Connector, Integration, App oder Werkzeug).
- Die Verbindung muss vom Benutzer in seiner Chat-Anwendung autorisiert werden; Ghostwriter darf keine Passwörter oder Tokens im Chat oder Repository erfragen oder speichern.
- Repository-Zugriff wird vor dem Wizard durch einen Lesezugriff auf das ausgewählte Repository verifiziert.
- Schreibberechtigungen werden nur für die spätere, ausdrücklich freigegebene Übertragung benötigt. Kein künstlicher Schreibtest vor der Freigabe.
- Eine maßgeschneiderte GhostWriter-Schnittstelle (API, MCP-Server oder eigene GitHub-App) ist eine separate, spätere Integration und entsteht nicht automatisch durch das Verbinden von GitHub.
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

## Betriebsweg bis v0.5: Weg A

Entschieden am 31.10.2026: GhostWriter v0.5 läuft über **Weg A**. Der KI-Assistent liest und schreibt das Buch-Repository über die GitHub-Verbindung der Chat-Anwendung, gesteuert durch `START.md` und die Chat-Vorlagen aus `ghostwriter-ui` (Regeln in `templates/ui/`). Die eigene GhostWriter-Schnittstelle (**Weg B**: Backend, GitHub App, Auth0, MCP-Server) wird bis v0.5 nicht weiterentwickelt, aber bei jedem Schritt berücksichtigt:

- **Formular entspricht Endpunkt:** Jede Schreibregel in `START.md` nennt den passenden Endpunkt aus `docs/API-CONTRACT.md`.
- **Feste Nachrichtenform:** Formulare senden ihre Daten in einem festen, maschinenlesbaren Format, das später unverändert an die API gehen kann.
- **Versionsschutz im Chat:** Der Assistent prüft vor dem Schreiben, ob sich die Datei seit dem Lesen geändert hat (entspricht `expected_head_sha`).
- **Prüfregeln einmal schreiben:** Schemas und Prüfungen der GitHub Action sind so abgelegt, dass das Backend sie wiederverwenden kann.
- **Eine Oberfläche:** Die Vorlagen in `ghostwriter-ui` bekommen ihre Daten als JSON über `GW.render`; mit Weg B kommen dieselben Daten von der API.
- **Contract mitpflegen:** Änderungen am Datenmodell werden im selben Schritt in `docs/API-CONTRACT.md` nachgetragen.

## KI-Anbindung der eigenen App (Planungsstand 07.11.2026)

Die installierbare GhostWriter-Web-App (#35) und die eigene Schnittstelle
(#19) stellen nicht automatisch einen KI-Zugang bereit. Ein Chatfenster in der
App ist zunächst eine Oberfläche; die GitHub-Anmeldung vermittelt Buchzugriff,
keinen Zugang zu einem KI-Modell. Die konkrete KI-Anbindung der eigenen App ist
noch als Architekturentscheidung auszuarbeiten, nicht als umgesetzt anzusehen.

Drei Betriebswege unterscheiden:

| Betriebsweg | KI-Anbindung |
|---|---|
| GhostWriter im vorhandenen KI-Chat | Der dortige Assistent bearbeitet die Projektdateien mit den verfügbaren Werkzeugen. GhostWriter ruft selbst kein Modell auf. |
| Eigene App mit externem KI-Chat | GhostWriter bereitet einen vollständigen Abschnittsauftrag vor. Der Benutzer übergibt ihn an den gewählten Chat und bringt das Ergebnis zur Prüfung zurück. |
| Eigene App mit integriertem KI-Chat | Erfordert eine ausdrücklich unterstützte Anbieteranbindung, üblicherweise eine Modell-API, oder ein lokal angebundenes Modell. Verfügbarkeit, Anmeldung und Abrechnung müssen für den gewählten Weg geklärt werden. |

Ein vorhandenes Chat-Abo nicht als automatisch nutzbaren Zugang für die eigene
App voraussetzen. Die Aufteilung in Abschnitte löst die Modellanbindung nicht.
Für die weitere Planung festlegen, welche Betriebswege die App unterstützt,
wie Auftragsübergabe und Rückgabe funktionieren und wie Buchstand, Kontext,
Fehler und Freigaben über diese Wege erhalten bleiben. Einen anderen Anbieter
nicht stillschweigend anstelle des gewählten Dienstes verwenden.

Die abschnittsweise Übersetzung soll zunächst im vorhandenen KI-Chat möglich
sein, ohne zusätzliche Übersetzungs-API oder Hintergrundlauf. Die dafür
bestätigten Regeln stehen im
[Workflow-Modell](WORKFLOW-MODEL.md#buchübersetzung-geplant).

## MVP-Grenze

MVP:
- GitHub-Verbindungs-Onboarding und Lesezugriffsprüfung;
- Wizard und Strukturentwicklung;
- explizite Freigabe;
- Repository-Initialisierung;
- stabile Datei- und Statuskonventionen.

Bereits im Repository vorgesehene bzw. implementierte v0.5-Bausteine:
- Recherche-, Brainstorming-, Schreib- und Analyse-Läufe als getrennte, unveränderliche Dateien;
- Abschnittsmanuskripte und Freigabehistorie;
- Kapitelzusammenführung und Prüfung freigegebener Inhalte;
- Projekt- und Schemaprüfung sowie CI-Validierung über GitHub Actions.

Spätere Ausbaustufen:
- vollständige End-to-End-Orchestrierung von Issues und Milestones;
- eigene GhostWriter-Schnittstelle (API/MCP-Server, ggf. GitHub-App) für beliebige Chat-Clients;
- zeitgesteuerte KI-Läufe, Warteschlange und automatisierte Budgetsteuerung;
- weitere Produktfunktionen gemäß `workflow.yml` und `docs/WORKFLOW-MODEL.md`.

Die Nennung eines Bausteins beschreibt den Repository-Stand bzw. das Zielmodell, nicht automatisch eine vollständig produktive Automatisierung. Maßgeblich sind die Roadmap-Abnahme und die zugehörigen Tests.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
