# Ghostwriter

Chatgesteuerte, GitHub-basierte Buchentwicklung.

Ghostwriter begleitet Autorinnen und Autoren von der Buchidee über Recherche und Brainstorming bis zur abschnittsweisen Manuskripterstellung und kapitelweisen Freigabe. GitHub ist der persistente Projektspeicher und die Versionsverwaltung; ChatGPT ist die dialogorientierte Arbeitsoberfläche.

## Schnellstart

1. Dieses Starterpaket in ein neues GitHub-Repository übernehmen.
2. Repository nach Wunsch benennen (z. B. `mein-buch`).
3. `START.md` öffnen und den darin beschriebenen Startprompt in einen neuen Chat kopieren.
4. Den Wizard durchlaufen. Bis zur Freigabe der Kapitelstruktur werden keine Buchdateien angelegt oder verändert.
5. Nach Freigabe wird die Projektstruktur in dieses Repository übertragen.

> Hinweis: Ein normaler Markdown-Link überträgt den Inhalt von `START.md` nicht automatisch in einen Chat. Für den MVP wird der Inhalt kopiert oder als Datei bereitgestellt. Eine spätere GPT-/GitHub-Anbindung kann die Datei automatisch laden.

## Projektregeln

Die globalen KI-Einstellungen stehen in `ghostwriter.yml` und gelten für Recherche, Brainstorming, Schreiben, Überarbeiten und Fact-Checking:

- Halluzinationsschutz: `strict`
- Quellen: `required`
- Unsicherheiten: `explicit`
- Kreativität: `balanced`
- Internetrecherche: `research`

## Dokumentation

- [Start-Wizard](START.md)
- [Architektur und Workflow](docs/ARCHITECTURE.md)
- [Datei- und Statusmodell](docs/DATA-MODEL.md)
- [GPT-/GitHub-Action-Schnittstelle](docs/INTEGRATION.md)

## Grundprinzip

**Buch → Kapitel → Abschnitte → Recherche-/Brainstormingläufe → Manuskript → Abschnittsfreigabe → Kapitelzusammenführung → Kapitelfreigabe.**

Jedes Kapitel hat mindestens einen und beliebig viele Abschnitte. Abschnitte können jederzeit hinzugefügt, verschoben oder neu geordnet.
