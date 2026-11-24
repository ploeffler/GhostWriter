# Planungsstand und Nachträge bis v1.0

Standabgleich: 23. November 2026, Programmversion 0.9.0 (Quellcommit `3c528ff`). Die ursprünglichen Beschlüsse stammen vom 8. November; spätere Ergänzungen sind im Entscheidungsprotokoll datiert. Beschlüsse, Vorschläge und Prüfergebnisse sind getrennt ausgewiesen. Eine Anforderung ist erst nach Umsetzung und Abnahme fertig.

| Dokument | Geltung |
|---|---|
| [Bestätigte Beschlüsse](ENTSCHEIDUNGEN-v1.0.md) | Verbindlicher fachlicher Umfang einschließlich der ergänzten Medien-/Umschlag-/Websitevorgaben und DOCX-Metadaten für v1.1 |
| [Arbeitsaufträge](AUFTRAEGE-v1.0.md) | Lieferblöcke und noch offene Abnahmen |
| [Entscheidungsauftrag mit Gesprächsprotokoll](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/ENTSCHEIDUNGSAUFTRAG-v1.0.md) | Historischer Fragen-/Antwortenkatalog; das bestätigte Protokoll hat bei Widersprüchen Vorrang |
| [Zwischenversionen bis v1.0](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLAN-v1.0-ZWISCHENVERSIONEN.md) | Vorschlag; Website für v0.9.0 bestätigt |
| [Medienplatzierung Deutsch](MEDIENPLATZIERUNG.md) / [Englisch](MEDIA-LAYOUT.en.md) | Mengenbegrenzung, sechs Positionen, Textumfluss und Breitensteuerung implementiert; praktische Format- und Clientabnahme noch offen |
| [Lokaler Bildtest](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/tests/evidence/2026-11-08-bilder/TESTBERICHT.md) | Historischer Prüfstand vom 8. November; spätere Korrekturen sind in der Medienanleitung beschrieben. Keine vollständige aktuelle Produktabnahme |
| [Bedienglossar](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/UMSETZUNGSAUFTRAG-BEDIENGLOSSAR.md) | Deutsches/englisches Bedienglossar vorhanden: [Deutsch](BEDIENGLOSSAR.md), [Englisch](USER-GLOSSARY.en.md); kein Buchglossar |
| [Zentrale Dokumentationswebsite](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLANUNGSNOTIZ-DOKUMENTATIONSWEBSITE.md) | Website-Erzeuger und zweisprachige Quellen vorhanden; lokaler Aufbau am 23. November erfolgreich. Aktuelle öffentliche Fassung und Browserabnahme hier nicht geprüft; keine neue Veröffentlichung beauftragt |
| [Buch-Overlays](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLANUNGSNOTIZ-BUCH-OVERLAYS.md) | Vorgemerkte Idee ohne Versionszusage |
| [BookyAI-Vergleich](BOOKYAI-VERGLEICH.md) | Datierte Recherche vom 07.11.2026, kein aktueller Praxistest; Web-App-Angabe am 20.11.2026 an D06/D19 angeglichen |
| [Marktvergleich](MARKTVERGLEICH-v1.0.md) / [Englisch](MARKET-COMPARISON-v1.0.en.md) | Datierte Recherche vom 20.11.2026 zu Sudowrite, Novelcrafter, Atticus, Scrivener und BookyAI, kein Praxistest |
| [Prompt-Caching prüfen](PROMPT-CACHING.md) | Gespeicherter technischer Prüfablauf, kein Nachweis aktiver Cache-Nutzung |

Skill-Unterstützung: Für v1.0 ist der Abgleich der vorhandenen Unterstützung für Claude und Codex bestätigt (A10). Die Repository-Skills für Einstieg, Lektorat und Buchgedächtnis sind bereits vorhanden; AGENTS.md und CLAUDE.md beschreiben die Auswahl für alle Assistenten. Die vollständige praktische Abnahme für Claude und Codex bleibt offen. Der beschlossene schrittweise Ausbau ab v1.1 ist keine Zusage, dass alle Fachskills dann fertig sind. Details im [Beschluss](ENTSCHEIDUNGEN-v1.0.md#beschluss-vom-8-november-2026-skill-unterstützung).

Die sechs Ablaufgrafiken und ihre deutschen/englischen Seiten sind bereits durch Änderung #224 in main. Die gemeinsame Claude-/Codex-Fußzeile, die Medienanforderungen und die verlinkten Nachträge sind im ausgewerteten Quellstand enthalten; sie sind kein noch ausstehendes ursprüngliches Übertragungspaket. Persönliche lokale Arbeitsregeln werden nicht an Nutzer-Forks verteilt.

## Abnahmegrenzen des aktuellen Bestands

Implementierung und automatische Tests ersetzen keine praktische Gesamtabnahme. Die [Arbeitsaufträge](AUFTRAEGE-v1.0.md) bleiben der Kriterienkatalog; historische offene Checkboxen beweisen für sich weder fehlenden Code noch eine bestandene Prüfung.

- **Freigaberechte:** Name und Manuskript-Fingerabdruck werden protokolliert beziehungsweise geprüft; persönliche Kontoprüfung und Inhaltsnachweise an den offiziellen Schreib-/Ausgabewegen sind ergänzt; die praktische Client- und Organisationsabnahme bleibt offen. Siehe [Zusammenarbeit und Freigaberecht](GRUNDSAETZE.md#zusammenarbeit-und-freigaberecht).
- **Standabgleich und Sicherung:** Werkzeuge für Standvergleich, Übergabe, Antwort- und Abschnittsabschlusssicherung sind vorhanden. Aktuelle Mehrclient- und Wiederherstellungsnachweise bleiben erforderlich.
- **Import:** Originale bleiben bis zum ausdrücklichen Löschauftrag erhalten; alte Fristen lösen keine automatische Entfernung aus. Die entsprechende frühere Abweichung in A06 ist behoben.
- **Warteschlange:** Der Nachtrag vom 22. November in D08 nimmt sie ausdrücklich in v1.0 auf. Reihenfolge, Vorziehen, Abbrechen und Budget-/Wiederanlaufverhalten gehören in die Abnahme; kostenpflichtige Anbieter-Live-Tests sind weiterhin keine Voraussetzung.
- **Abschluss:** Vier-Client-Prüfungen, relevante Exportformate, der vollständige Weg von einer Gestaltungsvorlage zum bestätigten Umschlag sowie der abschließende Gesamtlauf bleiben gesondert nachzuweisen. Dieser Standabgleich erklärt v1.0 nicht für fertig.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
