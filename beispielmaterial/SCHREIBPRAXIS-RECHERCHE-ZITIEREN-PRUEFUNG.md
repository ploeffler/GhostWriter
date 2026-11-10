# Prüfvermerk: Recherche und Zitieren

Stand: 10. November 2026. Auftrag: nach dem lokalen deutschen Entwurf Englisch und beide Übersichten ergänzen; bei erfolgreichen Prüfungen gemeinsam übertragen und veröffentlichen.

## Geprüfter Umfang

Beide vollständigen Folgen in Deutsch und Englisch: fünf Recherche- und sechs Zitierstationen je Sprache; 44 Stationsseiten einschließlich Quellvorschauen und Website-Ausgaben, beide Übersichten, Inhaltsdateien, gemeinsamer Erzeuger und Pflegehinweise. Umsetzung auf isoliertem aktuellem Hauptstand; keine privaten Bücher, persönlichen Regeln oder älteren Fremdänderungen im Paket. Programmversion unverändert.

Die zentralen Schreibpraxis-Vorlagen, Serienvorgaben und Regeln der redaktionellen Qualitätssicherung wurden verwendet. Deutsche Buchnamen und Fundstellen bleiben im Englischen erhalten; die englische Übersetzung des fiktiven Eigenzitats wird ausdrücklich gekennzeichnet.

## Redaktion und Fachquelle

Alle Stationen vollständig auf Folgefragen, Autorenentscheidungen, Begriffe, Quellenzuordnung und offene Punkte geprüft. Ausgangsbehauptung, Befund, Änderungsvorschlag und ausgewählte Textprobe bleiben unterscheidbar. Der ganze Beispielabsatz wird erneut betrachtet. Eigenverweis, wörtliche Übernahme und sinngemäße Wiedergabe werden durchgespielt. Eine nicht gelesene Studie und fehlende Seitenzahlen werden nicht erfunden. Die Fachinformation wird nicht als Originalstudie ausgegeben.

Tatsächlich konsultierte Fachquelle: Schweizerischer Erdbebendienst (SED) an der ETH Zürich, [Können Erdbeben vorhergesagt werden?](https://www.seismo.ethz.ch/de/knowledge/faq/can-earthquakes-be-predicted/), auch in [englischer Fassung](https://www.seismo.ethz.ch/en/knowledge/faq/can-earthquakes-be-predicted/), Einleitung und Abschnitt zur Frühwarnung; gelesen am 10. November 2026. Kein ausgewiesenes Veröffentlichungsdatum auf den gelesenen Seiten. Institutionelle Fachinformation, keine Originalstudie; keine vollständige Literaturübersicht oder Untersuchung bestimmter Warnsysteme.

Alle Dialoge und Buchfundstellen sind fiktiv, die Buchsuche wurde nicht ausgeführt. Die Autorenwahl im simulierten Dialog ist keine echte Speicherung oder formale Abschnittsfreigabe. Die Kennzeichnung steht auf jeder Seite unter der Stationsnavigation. Keine Suchfunktion oder Anbieterleistung wird durch die Simulation nachgewiesen.

## Lokale Prüfungen vor Übertragung

Bestanden:

- 44 Stationsseiten: vollständige Gesprächs-, Ergebnis- und Tabellentexte gegenüber den Inhaltsdateien; Deutsch/Englisch mit identischen Stationen und Blockarten.
- Sprachwechsel und Rückwechsel jeweils zur entsprechenden Station, Logo-Ziele zur passenden Übersicht, Folgentitel zum Anfang der eigenen Sprache, alle lokalen Links und Anker, aktive Station, Vor-/Zurück und Fortschritt.
- Simulationshinweise an der vorgegebenen Position, gemeinsame Fußzeilen je Sprache, kein zurückgebliebener Hinweis auf einen rein deutschen Entwurf.
- Nach der Gestaltungskorrektur: beide Übersichten mit fünf vollständig anklickbaren Kacheln, je eigener Illustration, Einordnung und Beschreibung. Die bisherigen drei Folgen behalten ihre Reihenfolge; Recherche und Zitieren folgen als vierte und fünfte Kachel. Kein zusätzlicher Textlink-Abschnitt.
- Bytegleicher Neuaufbau beider Folgen, Assets und Übersichten.
- `python3 scripts/check_docs.py --ui /tmp/ghostwriter-docsite-ui`: bestanden einschließlich der verfügbaren UI-Prüfung.
- `python3 -m unittest tests.test_check_docs tests.test_docs_site tests.test_build_docs_wiki`: 21 Tests, erfolgreich, davon ein umgebungsabhängiger Test übersprungen.
- `python3 scripts/package_docs_site.py --output /tmp/gw-recherche-zitieren-pages`: bestanden, einschließlich zentraler Dokumentation und vorhandener Beispiele. Der Paketprüfer ist im aktuellen Hauptstand vorhanden; die frühere lokale Dateilücke ist damit für das Veröffentlichungspaket erledigt.
- `python3 scripts/build_docs_wiki.py --output /tmp/gw-recherche-zitieren-wiki`: bestanden, 43 Seiten, Programmversion 0.6.0.
- `git diff --check` sowie direkte Prüfung neuer Textdateien auf abschließende Leerzeichen und Dateiende: bestanden.

## Korrektur der Übersicht

Am 10. November 2026 nach Benutzerhinweis beide neuen Folgen in das gemeinsame Kachelraster aufgenommen. Die vorige Einbindung als separater Textabschnitt entsprach nicht der gewünschten Darstellung. Deutsch und Englisch sowie Erzeuger und Pflegehinweise gemeinsam korrigiert. Lokale Prüfung: je fünf Kacheln, korrekte Linkziele, unveränderte Reihenfolge der ersten drei Folgen, eigene SVG-Illustrationen, Fußzeilen und bytegleicher Neuaufbau.

## Ergebnis und Grenzen

**Redaktionelle und verfügbare technische Prüfungen bestanden; bereit für die beauftragte Veröffentlichung.** Der einzelne übersprungene Umgebungstest ist ausgewiesen. Kein laufzeitrelevanter Programmcode oder Manuskript einer realen Bibliothek wurde verändert.

Eine gerenderte Browserabnahme und praktische Tastaturprüfung wurden nicht durchgeführt. Browserzugriff bleibt gemäß persönlicher Vorgabe an eine gesonderte Freigabe gebunden. Responsive Regeln und Fokusmarkierung sind vorhanden, aber nicht visuell abgenommen. Diese Grenze ist kein behaupteter Prüferfolg.

Die Pages-Action ist mit `documentation=true` auszuführen, damit die bestehende zentrale Dokumentation erhalten bleibt. Upload, Merge und Deployment werden erst nach tatsächlicher Bestätigung als erfolgreich gemeldet. Nach dem Deployment sind die öffentlichen Dateien per HTTP mit dem lokal geprüften Paket abzugleichen. Technischer Veröffentlichungsnachweis in der lokalen Übergabe; keine vorweggenommene Live-Bestätigung in diesem Prüfvermerk.

---
Entwickelt mit Unterstützung von Claude (Anthropic)
Entwickelt mit Unterstützung von Codex (OpenAI)
