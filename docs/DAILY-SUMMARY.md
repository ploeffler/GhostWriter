# Tägliche GitHub-Übersicht

Die Action **GhostWriter aktualisieren** ergänzt ihre bestehende Actions-Zusammenfassung um eine Übersicht der letzten 24 Stunden.

## Buchinhalte

Pro erkanntem Buch-Branch werden Inhalts-Commits und unterschiedliche geänderte Inhaltsdateien gezählt. Berücksichtigt werden ausschließlich die im Manifest als Buchbestand geführten Manuskriptbereiche:

- `chapters/`
- `matter/`
- `cover/`
- `characters/`
- `story/`
- `research/`

Programmdateien, GhostWriter-Update-Metadaten, Konfigurationen und reine Statusänderungen werden nicht gezählt. Bücher ohne Inhaltsänderungen erscheinen nicht in der Tabelle.

## Pull Requests

Die Übersicht zeigt Pull Requests im Hauptrepository `ploeffler/GhostWriter`, die innerhalb der letzten 24 Stunden aktualisiert wurden, mit ihrem aktuellen Status und einem direkten Link. Die Abfrage nutzt die öffentliche GitHub-API; sie benötigt keinen zusätzlichen Secret.

## Betrieb

Die Ergänzung läuft als letzter Schritt im vorhandenen Workflow. Es gibt keinen zweiten Zeitplan, keinen E-Mail-Versand und keine zusätzlichen Issue-Kommentare. Die Ergebnisse stehen unter **Actions → GhostWriter aktualisieren → Summary**. Ist die PR-Abfrage vorübergehend nicht erreichbar, wird dies in der Übersicht ausgewiesen; der Update-Lauf selbst wird dadurch nicht beeinträchtigt.
