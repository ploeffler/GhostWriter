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

Programmdateien, GhostWriter-Update-Metadaten, Konfigurationen und reine Statusänderungen werden nicht gezählt. In Abschnittsdateien werden dafür Verwaltungsfelder einschließlich `approvals` aus dem YAML-Vorspann ausgeblendet; in Kapitelübersichten die Statusspalte und der Bereich „Kapitelstatus“. Änderungen am Manuskript, an Absatztrennungen und an inhaltlichen Übersichtsangaben bleiben zählbar. Bücher ohne Inhaltsänderungen erscheinen nicht in der Tabelle.

## Pull Requests

Die Übersicht zeigt Pull Requests im Hauptrepository `ploeffler/GhostWriter`, die innerhalb der letzten 24 Stunden aktualisiert wurden, mit ihrem aktuellen Status und einem direkten Link. Das Hauptrepository wird aus `upstream.repo` des Manifests bestimmt. Zusätzlich werden alle offenen PRs unabhängig von ihrem Alter mit anstehenden Reviews, angeforderten Änderungen, Konflikten und auffälligen Prüfungen angezeigt. Unbekannte Detailstände werden als unbekannt bezeichnet; eine mögliche Übernahme bleibt eine ausdrückliche Entscheidung. Die Abfrage nutzt die GitHub-API; sie benötigt kein zusätzliches Secret.

## Update-Status

Der Bericht zeigt das Ergebnis des aktuellen Update-Schritts sowie eine Limitpause (bei manuellen Läufen als Warnung). Offene Fehler-/Pausen-Issues und fehlgeschlagene oder abgebrochene Update-Läufe der letzten 24 Stunden werden verlinkt. Diese Daten stammen aus dem jeweiligen Buch-Repository, die PR-Übersicht aus dem Hauptrepository. Fehlende API-Daten bleiben ausdrücklich unbekannt.

## Betrieb

Die Ergänzung läuft als letzter Schritt im vorhandenen Workflow. Es gibt keinen zweiten Zeitplan, keinen E-Mail-Versand und keine zusätzlichen Issue-Kommentare. Die Ergebnisse stehen unter **Actions → GhostWriter aktualisieren → Summary**. Ist die PR-Abfrage vorübergehend nicht erreichbar, wird dies in der Übersicht ausgewiesen; der Update-Lauf selbst wird dadurch nicht beeinträchtigt.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
