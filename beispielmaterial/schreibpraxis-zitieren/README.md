# Das habe ich doch schon recherchiert – Eigenes wiederfinden und richtig zitieren

[English](README.en.md)

Zweisprachige Folge der Serie Schreibpraxis. Deutsch wurde am 10. November 2026 zunächst lokal erstellt; danach wurden Englisch, beide Übersichten und die Veröffentlichung ausdrücklich beauftragt. Alle Dialoge, Manuskriptproben und Buchfundstellen sind simuliert. Nur die verlinkte Fachinformation ist real und wurde gelesen. Keine echten Bücher wurden durchsucht oder geändert.

## Quellen und reproduzierbarer Aufbau

`inhalt.json` enthält das deutsche Drehbuch einschließlich Lernziel und Simulationshinweis; `content.en.json` die stationsgleiche englische Fassung. Deutscher Buchtitel und Fundstellen bleiben im Englischen erhalten. Die Übersetzung des fiktiven Eigenzitats ist gekennzeichnet. Texte als reinen Text pflegen; HTML wird maskiert. Zulässige Blöcke: `message`, `result`, `note`, `table`, `link`. Bei inhaltlichen Änderungen beide Sprachen und deren Zuordnung prüfen.

Gemeinsamer [Erzeuger](../../scripts/build_research_writing_practice.py), zentrale [Folgenvorlage](../../templates/schreibpraxis/folge.html) und gemeinsamer Grundstil; originales Federlogo. Seiten und Assets neben dieser Anleitung sind die Quellvorschau. Die Website-Ausgabe liegt unter `website/zitieren/`. Erzeugte Dateien nicht von Hand bearbeiten.

```sh
python3 scripts/build_research_writing_practice.py --publish
python3 scripts/build_writing_practice_index.py
python3 scripts/check_docs.py
python3 scripts/package_docs_site.py
```

Ohne `--publish` entsteht nur die Quellvorschau. Mit dem Schalter werden zusätzlich Website-Dateien **lokal** erzeugt; kein Upload oder Deploy. Der gemeinsame Erzeuger baut beide Folgen und Sprachen. Beide Übersichten zeigen alle fünf Folgen als vollständig anklickbare Kacheln mit Illustration, Einordnung und Beschreibung. Die bisherigen drei Folgen behalten ihre Reihenfolge; Recherche und Zitieren folgen als vierte und fünfte Kachel. Logo führt zur Übersicht der jeweiligen Sprache, Folgentitel zum Folgenanfang und Sprachwechsel zur entsprechenden Station.

[Deutsch](index.html) · [English](index.en.html) · [Übersicht](../../website/schreibpraxis.html)

## Fachquelle und Grenzen

Schweizerischer Erdbebendienst (SED) an der ETH Zürich: [Können Erdbeben vorhergesagt werden?](https://www.seismo.ethz.ch/de/knowledge/faq/can-earthquakes-be-predicted/), auch in [englischer Fassung](https://www.seismo.ethz.ch/en/knowledge/faq/can-earthquakes-be-predicted/). Einleitung und Abschnitt zur Erdbebenfrühwarnung. Institutionelle Fachinformation, keine Originalstudie. Ohne ausgewiesenes Veröffentlichungsdatum; gelesen am 10. November 2026. Keine systematische Literaturübersicht oder Prüfung einzelner Warnsysteme.

[Gemeinsamer Prüfvermerk](../SCHREIBPRAXIS-RECHERCHE-ZITIEREN-PRUEFUNG.md). Alle Dialoge und Buchfundstellen bleiben auch nach Veröffentlichung fiktiv. Keine Suchfunktion oder Anbieterleistung wird durch die Simulation nachgewiesen. Vor einer echten Buchverwendung Quellen und tatsächliche Ausgabe/Fundstelle prüfen. Pages mit `documentation=true` starten, damit die zentrale Dokumentation erhalten bleibt. Veröffentlichungserfolg erst nach bestätigtem Deployment melden.

---
Entwickelt mit Unterstützung von Claude (Anthropic)
Entwickelt mit Unterstützung von Codex (OpenAI)
