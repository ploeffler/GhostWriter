# Externer KI-Dialog – lokale Erprobung

Datum: 10. November 2026. Ausgangsstand des Hauptrepositorys: `19a2e33e01b8f5c2c8a418cf38bcf6c002b90bb8`.

## Umfang

Auftrag des Autors: allgemeinen Ablauf mit Initiierung, Auftrag, Rückgabe, Analyse und Empfehlung als lokal getestet dokumentieren und direkt als PR ins Hauptrepository geben. Der Ablauf ist Chat-Anweisung mit Vorlagen, keine Anbieter-API oder neue technische Parserfunktion. Er ergänzt den vorhandenen Weg „Auftrag kopieren“ und die Entscheidung D07. Der spätere Prompt-Compiler aus #204 ist nicht umgesetzt und nicht Voraussetzung.

## Tatsächliche manuelle Erprobung

- Ein konkretes Aufgabenpaket als Textdateien und ZIP vorbereitet. Die Trennung zwischen ausgefülltem Auftrag und ZIP mit weiteren Anleitungen wurde im Gespräch erklärt.
- Ein vom Autor als Gemini-Rückgabe bezeichneter sichtbarer Gesprächsverlauf mit Fragen, Antworten und Entwurf wurde als Textdatei zurückgebracht und ausgewertet.
- Ein fehlendes letztes Wort wurde vom Autor nachgereicht. Original und Nachtrag blieben getrennt; die zunächst begrenzte Bewertung wurde korrigiert.
- Die Analyse unterschied neue Autorenangaben und Anbieterinterpretationen, Gesprächsführung, Ergebnisqualität und Grenzen. Anschließend wurde eine konkrete Empfehlung ergänzt.
- Start- und Rückgabeformulierungen im Gespräch abgestimmt und im allgemeinen Ablauf festgehalten. Keine neue Parseraktion aus der Formulierung abgeleitet.

Ergebnis: **manueller Grundweg lokal getestet**. Keine privaten Buchtexte, Originalantworten oder konkreten persönlichen Angaben werden als Testdaten ins Hauptrepository übernommen.

## Grenzen

Die tatsächliche Rückgabe enthielt den Ausgangsprompt und die Modellbezeichnung nicht. Eine identische Informationslage mehrerer Anbieter ist nicht belegt. Es handelt sich nicht um einen kontrollierten Anbieter-Vergleich, eine erneute externe Erprobung jeder Vorlagenfassung oder eine Abnahme in ChatGPT, Codex, Claude und Open WebUI zugleich. Automatische ZIP-Erzeugung, Dateiimport, Parseraktionen und Anbieteraufrufe sind nicht implementiert. Der Assistent erstellt verfügbare Datei-/Textartefakte mit seinen vorhandenen Werkzeugen und legt Grenzen offen.

## Technische Prüfung dieses PR

Auf dem endgültigen Stand ausgeführt:

- `python3 -m unittest discover -s tests -p 'test_*.py'`: **405 Tests, OK, 69 übersprungen**, Laufzeit ca. 174 Sekunden. Übersprungene Fälle sind keine bestandenen Funktionsabnahmen.
- `python3 scripts/check_docs.py`: bestanden; ohne externe UI-Kopie, daher keine entsprechende UI-Platzhalterprüfung.
- `python3 scripts/build_docs_site.py` und `--check`: bestanden.
- `python3 scripts/package_docs_site.py`: lokales Offline-Paket gebaut, nicht veröffentlicht.
- `git diff --check`: bestanden.
- Erzeugte deutsche und englische Einstiege mit neutraler Beispielkonfiguration geprüft: 6.485 bzw. 6.330 Zeichen, Ablauf verlinkt und innerhalb der geprüften Längengrenze.
- Sprachseiten und Empfehlung im Website-Aufbau vorhanden; keine Testberichte oder privaten Dialoge darin verlinkt. Vorgesehene Quelldateien auf private Inhalte geprüft.

 Die Website enthält nur die allgemeinen Anleitungen; dieser Testbericht und private Dialoge gehören nicht zum Website-Paket. Produktversion und Veröffentlichung bleiben unverändert, der PR wird nicht automatisch übernommen.
