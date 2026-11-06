# Tägliche GitHub-Übersicht

[English](DAILY-SUMMARY.en.md) · Deutsch

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

Die Ergänzung läuft als letzter Schritt im vorhandenen Workflow. Es gibt keinen zweiten Zeitplan und keinen eigenen E-Mail-Versand. Der geplante tägliche Lauf veröffentlicht zusätzlich höchstens einen Issue-Kommentar pro UTC-Tag mit dem vollständigen Bericht einschließlich der Update-Ergebnisse je Branch. Die Ergebnisse stehen unter **Actions → GhostWriter aktualisieren → Summary**. Ist die PR-Abfrage vorübergehend nicht erreichbar, wird dies in der Übersicht ausgewiesen; der Update-Lauf selbst wird dadurch nicht beeinträchtigt.

## Tagesbericht erhalten

Beim ersten Versand wird im jeweiligen Repository einmalig das Issue **„GhostWriter: täglicher Update-Bericht“** angelegt. Jeder Tageskommentar enthält den vollständigen Bericht und erwähnt den Empfänger mit `@Benutzername`. Standard ist der GitHub-Akteur des geplanten Workflows (`github.actor`), also der für die Zeitplanung verantwortliche Benutzer. Optional kann die Repository-Variable `GHOSTWRITER_REPORT_RECIPIENT` einen festen GitHub-Benutzernamen vorgeben. Für Organisations-Repositories ebenfalls einen Benutzer wählen, nicht die Organisation.

Der Empfänger aktiviert in seinen persönlichen GitHub-Benachrichtigungseinstellungen E-Mail für Erwähnungen beziehungsweise abonnierte Vorgänge und abonniert bei Bedarf das Berichts-Issue mit **Subscribe**. GitHub verschickt dann die Kommentarbenachrichtigung; GhostWriter benötigt weder SMTP noch zusätzliche Secrets und kann eine E-Mail bei deaktivierten Benachrichtigungen nicht erzwingen. Andere abonnierte Benutzer können ebenfalls benachrichtigt werden. Die erstmalige Issue-Erstellung kann zusätzlich eine Benachrichtigung an Beobachter auslösen.

Wiederholte Läufe am selben UTC-Tag erzeugen keinen weiteren Kommentar und ändern den bestehenden nicht. Die bestehende Workflow-Sperre verhindert parallele Zustellungen. Schließen des Berichts-Issues pausiert den Versand; Wiederöffnen aktiviert ihn wieder. Das Issue wird anhand einer festen unsichtbaren Kennung gefunden; sein Titel darf geändert werden, die Kennung im Text muss erhalten bleiben.

Manuelle Update-Läufe versenden standardmäßig nichts. Mit **„Vollständigen Tagesbericht als Issue-Kommentar zustellen“** kann der Bericht ausdrücklich auch manuell angefordert werden; die Tagesbegrenzung gilt weiterhin. Probeläufe (`dry_run`) versenden nie. Ein Versandfehler lässt das Update-Ergebnis unverändert und wird in der Actions-Zusammenfassung gemeldet. Überschreitet ein Bericht die Kommentargrößengrenze, bleibt er vollständig in der Actions-Zusammenfassung; er wird nicht gekürzt oder auf mehrere Kommentare verteilt.

Für wenig E-Mails können die normalen Actions-Benachrichtigungen auf Fehler beschränkt und andere unerwünschte Repository-Abonnements reduziert werden. GhostWriter verändert persönliche GitHub-Einstellungen nicht. Die Verbindung braucht im Workflow weiterhin `issues: write`; zusätzliche Rechte sind nicht nötig.

## Sprache des Berichts

Die Sprachwahl für geplante Berichte lautet: Repository-Variable `GHOSTWRITER_INTERFACE_LANGUAGE` → optionale Buch-Einstellung `interface.language` → `assistant.yml: interface_language` vom Standard-Branch → Deutsch. `en` wählt Englisch; Sprachvarianten wie `en-GB` werden auf die Basissprache abgebildet. Die Manuskriptsprache `project.language` beeinflusst diese Auswahl nicht. Für einen lokalen Aufruf: `python scripts/daily_summary.py --language en`.

Überschriften, Beschriftungen, Entscheidungen und Zustellmeldungen des Tagesberichts sind übersetzt. Titel, Branch-Namen und Nutzdaten bleiben unverändert. Die zuvor erzeugten Detailmeldungen des Update- und Limitskripts können weiterhin deutsch sein; grafische Vorlagen und erzeugte Chat-Ansichten werden gesondert migriert.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
