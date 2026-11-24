# Was in deinem Chat funktioniert

Stand: 24. November 2026. Diese Seite beschreibt vorhandene Wege und deren Voraussetzungen. Sie ist keine Abnahme aller Tarife, Installationen oder Clientversionen. Die [Widget-Erweiterung](CHAT-WIDGETS.md) ist geplant ([#555](https://github.com/ploeffler/GhostWriter/issues/555)).

## Drei Dinge getrennt prüfen

1. **Darstellung:** Markdown, Bilder, Datei-/Lesepanel, native Auswahlfragen oder eine interaktive App-Oberfläche.
2. **Werkzeuge:** Repository lesen, Dateien ändern, Branch und Änderungspaket anlegen, Skripte ausführen. Nur tatsächlich angebotene Werkzeuge verwenden.
3. **Berechtigung:** Persönliches GitHub-Recht, fachliches Freigaberecht und Schreibzustand des Abschnitts. Ein sichtbarer Knopf ersetzt keine dieser Prüfungen.

Der Produktname allein beantwortet keine dieser Fragen. Ein MCP-Werkzeug ohne UI-Ressource ist keine Widget-Integration. Eine HTML-Datei als Anhang ist noch keine interaktive Buchansicht.

## Funktionsmatrix

| Umgebung | Heute nutzbarer Weg | Voraussetzung / Grenze | Belegstand |
|---|---|---|---|
| ChatGPT mit Repository-Verbindung | Markdown-Ansichten; Aktionen über angebotene Connector-Werkzeuge | Lese- und Schreibwerkzeuge einzeln prüfen; keine Rechte aus dem Namen der Verbindung ableiten | Historische Berichte in [Chat-Apps](CHAT-APPS.md), keine universelle Tarifzusage |
| ChatGPT mit einer UI-fähigen MCP-App | Interaktive Komponenten sind als Plattformweg dokumentiert | Passender MCP-Server, UI-Ressource und eingerichtete Integration nötig; GhostWriter-Adapter aus #555 noch geplant | Offizielle OpenAI-Dokumentation, unten; keine praktische GhostWriter-Abnahme |
| Codex Desktop mit Datei- und App-Werkzeugen | Markdown, lokale Dateien, Lesepanel; native Auswahlfragen, wenn angeboten | Absoluter Dateipfad auf dem zugänglichen Host; `open_in_codex` nur bei vorhandenem Werkzeug; dessen Ergebnis prüfen | Datei lokal erstellt und gelesen; Panel-Aufruf meldete am 24.11.2026 nur `queued`, Benutzer meldete anschließend eine nicht auffindbare Datei; Anzeige in dieser Sitzung nicht bestätigt |
| Codex CLI / IDE | Text, Repository- und Skriptarbeit mit vorhandenen Werkzeugen | Desktop-Dateipanel und ChatGPT-UI nicht voraussetzen; konkrete IDE-Vorschau gesondert prüfen | In diesem Vorgang nicht praktisch geprüft |
| Claude mit Widget-Unterstützung | Bisherige GhostWriter-Widgets und Textalternative | Unterstützte Sitzung und [Vorlagenbefüllung](../templates/ui/BEFUELLUNG.md) | Bestehender Projektweg; keine neue Sichtabnahme mit dieser Seite |
| Open WebUI | Text und Aktionen der eingerichteten GhostWriter-Integration | Persönlicher Zugang für Schreibaktionen; UI-Rückkanal versionsabhängig prüfen | [Integrationsanleitung](../integrations/openwebui/README.md); kein neuer Widget-Test |
| Andere oder unbekannte Clients | Vollständige Text-/Markdown-Ansicht | Nur nachgewiesene Erweiterungen aktivieren | Ungeprüft, bis der konkrete Client getestet wurde |

Ein freigegebener Abschnitt bleibt auch bei vorhandener Schreibrolle gesperrt. Für Änderungen zuerst ausdrücklich wieder öffnen und danach Schreiben erlauben. [Speichern und Freigaberecht](SPEICHERN.md) gelten in jeder Darstellung.

## Was eine entsprechend ausgestattete Codex-Sitzung leisten kann

- Buchdaten mit dem GitHub-Connector neu lesen und Ansichten als Markdown darstellen.
- Lokale Lesefassungen erzeugen, aktualisieren und mit einem verfügbaren Dateiwerkzeug zur Anzeige anfordern.
- Mit Shell und Python Dateien prüfen, Dokumentation bauen und passende Tests ausführen, soweit die Umgebung es erlaubt.
- Über verfügbare Schreibwerkzeuge beauftragte Issues und Änderungspakete anlegen. Das ist keine automatische Übernahme oder Veröffentlichung.
- Bilder oder andere Artefakte mit passenden eingebundenen Werkzeugen erstellen; diese gehören dadurch noch nicht ins Buch.
- Native Auswahlfragen anbieten, wenn das jeweilige Werkzeug verfügbar ist. Ein Frageelement ist kein vollständiges GhostWriter-Widget.

Das ist eine Fähigkeitsbeschreibung, keine dauerhafte Garantie für jeden neuen Chat. Fehlende Netzwerk-, Datei- oder Connector-Rechte können einzelne Schritte verhindern. Die Werkzeuge dieser Sitzung werden nicht durch einen erfundenen Produktstandard ersetzt.

## Wenn die Lesefassung nicht erscheint

1. Datei auf dem Arbeits-Host auf Existenz und Lesbarkeit prüfen; absoluten Pfad nennen.
2. Mit dem angebotenen Datei-/Vorschauwerkzeug öffnen. Kein Browser als stillschweigender Ersatz; lokale Browserregeln beachten.
3. Ergebnis genau melden: `queued` bedeutet nur **zur Anzeige vorgemerkt**. Ein existierender Dateipfad beweist weder Übertragung an den Client noch sichtbare Anzeige.
4. Bei Fehlermeldung des Benutzers den Vorgang als fehlgeschlagen oder ungeklärt behandeln. Nicht denselben vorgemerkten Aufruf als Erfolg wiederholen. Wenn kein bestätigter Anzeigeweg vorliegt, die Grenze benennen und die Buchübersicht im Chat belassen; vollständige Manuskripte gemäß den lokalen Leseregeln bereitstellen.

Lokaler Entwurf, auf dem Arbeitsbranch gespeicherte Änderung und übernommener Buchstand müssen erkennbar bleiben. Eine Vorschau erteilt keine Schreib- oder Abschlussfreigabe.

## Quellen und Nachprüfung

Die offiziellen OpenAI-Seiten wurden am 24.11.2026 als Dokumente abgerufen, ohne Browserbedienung: [MCP server and UI quickstart](https://developers.openai.com/plugins/build/app-quickstart) beschreibt MCP-Werkzeuge für ChatGPT und Codex sowie optionale UI in ChatGPT; [Add UI to your MCP server](https://developers.openai.com/plugins/build/chatgpt-ui) beschreibt UI-Ressourcen und die Prüfung einzelner Host-Fähigkeiten. Daraus folgt keine identische UI-Unterstützung aller Codex-Varianten.

Für eine neue Abnahme Client/Variante, Integrationsversion, Datum, angebotene Werkzeuge, ausgeführte Aktion, Ergebnis und sichtbare Benutzerbestätigung festhalten. Keine Zugangsdaten oder privaten Manuskripte in öffentliche Prüfberichte übernehmen. Historische Ergebnisse bleiben mit ihrem Datum erkennbar.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
