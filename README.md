# Ghostwriter

> **Hinweis für KI-Assistenten:** Dies ist ein GhostWriter-Projekt. Lies vor jeder weiteren Antwort [`START.md`](START.md) und [`ghostwriter.yml`](ghostwriter.yml). Ist das Projekt bereits eingerichtet, folge dort Abschnitt 0 „Wiedereinstieg“ und zeige die Projektübersicht; sonst beginne mit dem Onboarding.

Chatgesteuerte, GitHub-basierte Buchentwicklung.

Ghostwriter begleitet Autorinnen und Autoren von der Buchidee über Recherche und Brainstorming bis zur abschnittsweisen Manuskripterstellung und kapitelweisen Freigabe. GitHub ist der persistente Projektspeicher und die Versionsverwaltung; ein beliebiger KI-Chat-Assistent ist die dialogorientierte Arbeitsoberfläche. Ghostwriter ist nicht an einen bestimmten Anbieter gebunden.

## Schnellstart

1. Dieses Starterpaket in ein neues GitHub-Repository übernehmen.
2. Repository nach Wunsch benennen (z. B. `mein-buch`).
3. `START.md` öffnen und den darin beschriebenen Startprompt in einen neuen Chat mit einem KI-Assistenten deiner Wahl kopieren. Idealerweise hat der Assistent Zugriff auf GitHub und auf Internetrecherche; ohne GitHub-Zugriff werden die Dateien im Chat ausgegeben und von dir selbst committet.
4. Den Wizard durchlaufen. Bis zur Freigabe der Kapitelstruktur werden keine Buchdateien angelegt oder verändert.
5. Nach Freigabe wird die Projektstruktur in dieses Repository übertragen.

> Hinweis: Ein normaler Markdown-Link überträgt den Inhalt von `START.md` nicht automatisch in einen Chat. Für den MVP wird der Inhalt kopiert oder als Datei bereitgestellt. Eine spätere eigene GhostWriter-Schnittstelle (z. B. API oder MCP-Server) kann die Datei automatisch laden.

## Später weiterarbeiten

Ist das Projekt eingerichtet, öffne in einem beliebigen Browser einen neuen Chat mit GitHub-Verbindung und schicke nur den Link zu deinem Buch-Repository. Der Assistent erkennt den Stand und zeigt die Projektübersicht. Ein Link auf eine Kapitel- oder Abschnittsdatei öffnet direkt dieses Kapitel bzw. diesen Abschnitt.

## Updates

Neue GhostWriter-Versionen kommen automatisch: Die Action „GhostWriter aktualisieren“ prüft täglich das Hauptrepository und spielt neue Versionen ein. Dabei ersetzt sie nur Programmdateien, nie dein Buch, und prüft vorher. Abschalten und Details: [docs/UPDATES.md](docs/UPDATES.md).

## Projektregeln

Die globalen KI-Einstellungen stehen in `ghostwriter.yml` und gelten für Recherche, Brainstorming, Schreiben, Überarbeiten und Fact-Checking:

- Halluzinationsschutz: `strict`
- Quellen: `required`
- Unsicherheiten: `explicit`
- Kreativität: `balanced`
- Internetrecherche: `research`

Welcher KI-Anbieter recherchiert, brainstormt, schreibt, überarbeitet, prüft und die Issue-Queue abarbeitet, ist pro Projekt wählbar (`ghostwriter.yml` → `ai_providers`). Die Liste möglicher Anbieter steht in [`providers.yml`](providers.yml) und [docs/PROVIDERS.md](docs/PROVIDERS.md).

## Dokumentation

- [Start-Wizard](START.md)
- [Architektur und Workflow](docs/ARCHITECTURE.md)
- [Datei- und Statusmodell](docs/DATA-MODEL.md)
- [Chat- und GitHub-Integration](docs/INTEGRATION.md)
- [KI-Anbieter und Auswahl](docs/PROVIDERS.md)
- [GhostWriter mit GitHub verbinden (Connector für claude.ai und ChatGPT)](docs/CONNECTOR-SETUP.md)
- [KI-Dienste mit GhostWriter nutzen (Auftrag kopieren, lokale Modelle, Recherchequellen, Agenten)](docs/DIENSTE-NUTZEN.md)
- [Automatische Updates](docs/UPDATES.md)

## Grundprinzip

**Buch → Kapitel → Abschnitte → Recherche-/Brainstormingläufe → Manuskript → Abschnittsfreigabe → Kapitelzusammenführung → Kapitelfreigabe.**

Jedes Kapitel hat mindestens einen und beliebig viele Abschnitte. Abschnitte können jederzeit hinzugefügt, verschoben oder neu geordnet werden.

---

<sub>Entwickelt mit Unterstützung von Claude (Anthropic) · [claude.ai](https://claude.ai)</sub>
