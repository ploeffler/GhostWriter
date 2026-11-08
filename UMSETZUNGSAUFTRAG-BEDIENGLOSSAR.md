# Umsetzungsauftrag für das GhostWriter Bedienglossar

Stand: 8. November 2026. Auftrag vom Benutzer erteilt. Diese Datei beschreibt die Umsetzung; sie meldet das Glossar noch nicht als fertig. Zunächst lokal bearbeiten und prüfen. Eine Übertragung zu GitHub braucht einen ausdrücklichen Auftrag.

## Ziel

Ein eigenes, gut auffindbares Bedienglossar erklärt die Begriffe von GhostWriter in verständlicher Sprache. Es hilft insbesondere dabei, Arbeitszustände, Speicherung, Übernahme und inhaltliche Freigaben auseinanderzuhalten.

Das Bedienglossar gehört zur Programmdokumentation. Es ist nicht das Glossar eines Buchs und wird niemals in Manuskripte, Probedrucke oder Buchauflagen aufgenommen.

## Ergebnis der Umsetzung

- Eine deutsche Seite `docs/BEDIENGLOSSAR.md` und eine entsprechende englische Seite `docs/USER-GLOSSARY.en.md`.
- Gegenseitige Sprachlinks und stabile Sprungmarken zu den einzelnen Begriffen.
- Alphabetische Orientierung in der jeweiligen Sprache; englische Begriffe werden sinnvoll übersetzt, technische Kennungen bleiben unverändert.
- Pro Begriff eine kurze Erklärung, bei Bedarf ein kleines Beispiel und ein Link zur maßgeblichen Anleitung. Keine technische Begriffssammlung ohne Bezug zur Bedienung.
- Sichtbare Links aus README, Anleitung, Hilfe und Dokumentationsverzeichnis, jeweils in den vorhandenen Sprachfassungen. Hinweise an erklärungsbedürftigen Stellen sollen direkt zum passenden Begriff führen.

Vor der Anlage vorhandene Hilfeseiten und Verzeichnisse prüfen. Inhaltlich gleiche Erklärungen vereinheitlichen und verlinken, ohne die verbindlichen Arbeitsanweisungen durch das Glossar zu ersetzen.

## Startumfang

| Bereich | Zunächst zu erklärende Begriffe |
|---|---|
| Buchaufbau | Bibliothek, Buch, Szene, Kapitel, Abschnitt, Gliederung, Vor- und Nachspann |
| Erstellung | Erstellungskreislauf, Recherche, Brainstorming, Entwurf, Überarbeitung, Faktenprüfung, Prüfergebnis |
| Zustände und Freigaben | geplant, in Bearbeitung, bereit zur Freigabe, Schreibfreigabe, Abschnittsfreigabe, Kapitelfreigabe, Bildfreigabe, Freigaberücknahme |
| Speicherung | Arbeitsstand, Buchstand, Änderungspaket, gespeichert, geprüft, übernommen, blockiert, Konflikt |
| Gesprächsarbeit | Session, Session sichern, Session laden, Session übernehmen, Sicherungslücke |
| Bilder und Grafiken | Medium, Illustration, Grafik, Referenzbild, Referenzfreigabe, Medienabschnitt, Bildunterschrift, Alternativtext, Platzierung, Textumfluss, Satzbreite, Größenregler |
| Ausgabe | Probedruck, Auflage, Veröffentlichung, PDF, Word-Datei beziehungsweise DOCX, E-Book beziehungsweise EPUB |

Technische Begriffe wie Branch, Commit, Pull Request, Merge und Tag nur erklären, soweit sie beim Lesen der bestehenden Dokumentation helfen. In deutschen Bedienerklärungen stehen die verständlichen Begriffe im Vordergrund; technische Entsprechungen können ergänzend genannt werden.

## Inhaltlich besonders wichtige Unterscheidungen

1. Eine Schreibfreigabe erlaubt das Schreiben; sie gibt den fertigen Abschnitt noch nicht frei.
2. Gespeichert ist nicht automatisch übernommen. Übernommen ist nicht automatisch inhaltlich freigegeben. Ein positives Prüfergebnis ersetzt keine Freigabe.
3. Eine Gesprächssicherung schützt verfügbare Gesprächsarbeit und verändert nicht das Manuskript. Laden ist nicht Übernehmen. Nicht gesicherte oder nicht zugängliche Inhalte bleiben als Lücke erkennbar.
4. Ein Referenzbild dient einem Erstellungsauftrag. Seine Ablage oder Referenzfreigabe macht es nicht automatisch zur Buchabbildung.
5. Eine Szene entspricht einem Abschnitt; pro Abschnitt höchstens ein Medium. Ein eigener Abschnitt kann nur ein Bild oder eine Grafik enthalten, etwa vor oder nach einem Textabschnitt. Gespeicherte Varianten und reine Referenzen sind keine Manuskriptplatzierungen.
6. Platzierung bezeichnet die sechs vorgesehenen Positionen oben/unten × links/mittig/rechts im Abschnittstext mit Textumfluss. Der vorgesehene Größenregler stellt die Breite in Prozent der nutzbaren Seitenbreite ein; die Höhe bleibt proportional.
7. Neue Anforderungen und tatsächlich verfügbare Funktionen auseinanderhalten. Die Mengenbegrenzung, die sechs Positionen, Textumfluss und der Größenregler sind zum Zeitpunkt dieses Auftrags noch nicht technisch umgesetzt. Vor dem Schreiben den dann aktuellen Stand prüfen; geplante Funktionen im Glossar entsprechend kennzeichnen.
8. Ein Probedruck ist keine veröffentlichte Auflage. Veröffentlichte Auflagen bleiben unverändert.
9. GhostWriter ist für textorientierte Bücher gedacht, nicht für Bildbände oder Fotobücher. Diese Einordnung prominent bei den Medienbegriffen und mit Verweis auf die entsprechende Anleitung erklären.

## Verbindliche Grundlagen

Die tatsächlichen Definitionen und Zustände aus `START.md`, `workflow.yml`, den Datenmodellen und dem aktuellen Programm übernehmen. Bei widersprüchlichen oder veralteten Erklärungen die Abweichung sichtbar klären; keine neuen Zustände oder Freigaben erfinden.

Geeignete Ausgangsseiten:

- [Buchablauf](docs/BUCHABLAUF.md) und englische Fassung.
- [Erstellungskreislauf](docs/ERSTELLUNGSKREISLAUF.md) und englische Fassung.
- [Speichern und Übernehmen](docs/SPEICHERN.md), [Session-Sicherung](docs/SESSION-SICHERUNG.md) und englische Fassungen.
- [Medien im Abschnitt](docs/MEDIENPLATZIERUNG.md) und englische Fassung.
- [Hilfe](docs/HILFE.md), [Qualitätssicherung](docs/QUALITAETSSICHERUNG.md) und [Workflow-Modell](docs/WORKFLOW-MODEL.md).

## Vorgehen

1. Aktuellen Projektstand und vorhandene Begriffsdefinitionen lesen; Überschneidungen und Widersprüche erfassen.
2. Begriffe und kurze Erklärungen auf Deutsch formulieren; Zustandsbezeichnungen ihrem tatsächlichen Abschnitts-, Kapitel- oder Speicherbezug zuordnen.
3. Inhaltlich gleichwertige englische Fassung erstellen. Keine maschinellen Kennungen übersetzen oder andere Regeln für die englische Bedienung erfinden.
4. Seiten und direkte Begriffslinks in die Dokumentationsnavigation einbauen. Die gemeinsame Doku-Fußzeile mit Claude-Hinweis und Codex-Hinweis in der Zeile darunter verwenden, auf Englisch entsprechend übersetzt.
5. Beide Seiten vollständig gegen die Grundlagen prüfen, anschließend Links und Dokumentationsprüfung ausführen. Bei nötigen Änderungen an Prüfskripten passende Tests ausführen.
6. Lokale Ergebnisse, Prüfergebnis und offene Punkte melden. Nichts als implementiert bezeichnen, das lediglich erklärt oder geplant ist.

## Abnahme

- [ ] Beide Sprachfassungen enthalten den vereinbarten Startumfang und sind über die Dokumentationsnavigation erreichbar.
- [ ] Begriffe haben stabile Sprungmarken; interne Links führen direkt zur passenden Erklärung.
- [ ] Die Erklärungen sind kurz und ohne Git-Vorkenntnisse verständlich.
- [ ] Sämtliche Freigabe- und Speicherbegriffe sind korrekt getrennt; Zustände stimmen mit den verbindlichen Grundlagen überein.
- [ ] Referenzbild, Buchabbildung und Medienabschnitt sind verständlich unterschieden.
- [ ] Mengenbegrenzung, Platzierung, Textumfluss und Breitenregler sind ihrem tatsächlichen Umsetzungsstand entsprechend gekennzeichnet.
- [ ] Das Bedienglossar wird nicht mit dem Buchglossar verwechselt und gelangt nicht in Buchausgaben.
- [ ] Deutsch und Englisch stimmen inhaltlich überein; Sprachwechsel, Querverweise und Fußzeilen funktionieren.
- [ ] `python3 scripts/check_docs.py` besteht; gegebenenfalls nötige Tests bestehen ebenfalls.
- [ ] Ein kurzes Prüfergebnis benennt verbleibende offene Begriffe oder widersprüchliche Quellen.

## Nicht Bestandteil dieses Auftrags

Kein neues Buchglossar, keine Bearbeitung von Manuskripten, keine automatische Freigabe und keine Implementierung der geplanten Medien- und Layoutfunktionen. Für neue Bedienelemente, Hintergrunddienste oder eine Suche über die vorhandenen Dokumentationsmöglichkeiten hinaus ist ein eigener Auftrag erforderlich.
