# Interaktive Buchansichten für weitere Clients

**Planung, noch nicht umgesetzt:** [Feature-Request #555](https://github.com/ploeffler/GhostWriter/issues/555), Stand 24. November 2026. Diese Seite beschreibt den gewünschten Funktionsumfang und keine installierbare fertige Erweiterung. Heute nutzbare Wege stehen unter [Client-Fähigkeiten](CLIENT-FAEHIGKEITEN.md).

## Gewünschte Bedienung

Bibliothek, Buch, Kapitel und Abschnitt sollen in ChatGPT, Codex, Claude, Open WebUI und weiteren geeigneten Clients dieselben Daten und Aktionen anbieten. Die Oberfläche zeigt Kapitelstruktur, Bearbeitungsstand, Schreib- und Abschlussstatus, Quellenstand, offene Punkte und nächste Aktionen. Navigation soll ohne Abtippen von Kürzeln möglich sein. Der Textweg bleibt vollständig erhalten.

Ein eigener UI-Adapter braucht einen tatsächlichen Rückkanal zum Assistenten oder zu den freigegebenen Werkzeugen. Reines HTML im Chat und ein als Knopf formatierter Text reichen nicht. Welche Oberfläche nutzbar ist, wird anhand der verfügbaren Fähigkeiten entschieden, nicht anhand des Produktnamens.

## Geplanter technischer Weg

- Gemeinsame Ansichts- und Aktionsdaten statt getrennt gepflegter Geschäftsregeln je Client.
- Für ChatGPT den dokumentierten MCP-Apps-UI-Weg evaluieren: MCP-Werkzeuge plus UI-Ressource und eingerichtete Integration. Die OpenAI-Dokumentation ist in den [Client-Fähigkeiten](CLIENT-FAEHIGKEITEN.md#quellen-und-nachprüfung) verlinkt.
- Für Codex Desktop, CLI und IDE getrennt ermitteln, welche UI-Hosts, Datei- und Vorschauwerkzeuge sowie Rückkanäle tatsächlich vorhanden sind. ChatGPT-Unterstützung ist kein Codex-Nachweis.
- Bestehenden Claude-Widget-Weg einbeziehen; Open WebUI und unbekannte Clients mit sicheren Textalternativen behandeln.
- Eine Fähigkeitenansicht zeigt verfügbar / nicht verfügbar / ungeprüft, nötige Einrichtung, Integrationsstand und letzte praktische Abnahme.

Die Architekturplanung [#525](https://github.com/ploeffler/GhostWriter/issues/525) bevorzugt einen Weg ohne selbst betriebenen Server. Ein UI-Adapter kann zusätzliche Infrastruktur erfordern; Hosting, Authentifizierung und Betrieb sind vor der Umsetzung zu entscheiden. Dieser Dokumentationsstand genehmigt kein neues Backend und verschiebt keine bestehenden Versionsgrenzen. Bezug: [Figurengespräch-Widget #431](https://github.com/ploeffler/GhostWriter/issues/431).

## Verbindliche Grenzen für die Umsetzung

Ansicht öffnen ist lesend. Persönliche Rollen und Abschnittssperren bleiben wirksam. Speichern, Schreiben erlauben, Abschließen, Übernehmen und Veröffentlichen bleiben getrennte Aktionen mit den bestehenden Bestätigungen. Vor einer Änderung den aktuellen Stand erneut prüfen; veraltete Ansichten dürfen keine fremden Änderungen überschreiben. Lokaler Vorschlag, gespeicherter Arbeitsstand und übernommener Buchstand müssen sichtbar unterscheidbar sein.

Eine vorgemerkte Anzeige oder ein gestarteter Auftrag ist kein Erfolg. Bei fehlendem UI-Host, gescheiterter Anzeige oder fehlenden Werkzeugen den konkreten Fehler zeigen und auf den vollständigen Textweg zurückfallen. Private Manuskripte bleiben im autorisierten Datenweg; öffentliche Doku verwendet nur neutrale Beispiele.

## Abnahme vor einer Unterstützungszusage

- Bibliothek → Buch → Kapitel → Abschnitt sowie Rücknavigation und Aktualisierung nach Aktionen praktisch prüfen.
- Jede Clientvariante mit Einrichtung, Version, Datum und Ergebnis einzeln erfassen; nicht geprüfte Kombinationen als ungeprüft kennzeichnen.
- Deutsch und Englisch, schmale Darstellung, Tastatur und Fokus sowie Fehler-/Offlinefälle prüfen.
- Fehlende Schreibrechte, gesperrte Abschnitte, veraltete Daten, Abbruch und doppelte Klicks ohne unerlaubte Änderungen behandeln.
- Ohne Widget dieselben zulässigen Aktionen als Text anbieten; keine Scheinknöpfe oder stillen Bestätigungen.
- Dokumentation und sichtbare Anzeige gemeinsam prüfen. Grüne Strukturtests ersetzen keine Sichtabnahme und kein persönliches Freigaberecht.

Installation, fertige Befehle und konkrete Client-Abnahmen folgen erst mit dem implementierten Adapter. Bis dahin gelten die [bestehenden Ansichten](DIALOGE.md) und die [Chat-App-Anleitungen](CHAT-APPS.md).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
