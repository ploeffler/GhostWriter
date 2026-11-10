# Serie Schreibpraxis – Gestaltung und Aufbau

Am 10. November 2026 vom Autor als gemeinsame Serie für diese Art HTML-Strecken festgelegt. Die Serienbezeichnung „Schreibpraxis“ steht unter GhostWriter links oben. Jede Folge trägt einen eigenen Titel. „Schreibpraxis“ erscheint auf den Seiten ausschließlich unter GhostWriter, nicht erneut im Menü oder in der Fußzeile. Der Folgentitel steht deutlich oberhalb der Stationsnavigation; kein zusätzlicher Serienhinweis oder Querverweis auf eine andere Folge in diesem Bereich.

## Folgen

- **Vom Gespräch zum eigenen Text:** `schreiben-mit-ghostwriter/index.html`; deutsch/englisch veröffentlicht.
- **Augmentiert arbeiten – Ein Brief, drei Schreibdialoge:** `schreibpraxis-augmentiert/index.html`; deutsch/englisch aus dem simulierten Drehbuch in PR #243 erstellt; Veröffentlichung am 10. November 2026 ausdrücklich beauftragt. Beide Sprachen unter website/augmentiert/ mit stationsgleichem Sprachwechsel.

- **Aus einer Idee wird ein Krimi:** `schreibpraxis-buchentwicklung/index.html`; zweisprachige Simulation zur inhaltsgestützten Konzeptentwicklung; Veröffentlichung ausdrücklich beauftragt, erste Kachel auf der Übersicht. Öffentliche Ausgabe unter `website/buchentwicklung/`.

## Recherche und Zitieren · zweisprachige Folgen

- **Stimmt das so? – Eine Behauptung auf dem Prüfstand / Is that right? – Putting a claim to the test:** `schreibpraxis-recherche/index.html` und `index.en.html`; fünf Stationen je Sprache zur quellenbasierten Prüfung und Überarbeitung einer Erdbebenbehauptung. Website-Ausgabe unter `website/recherche/`.
- **Das habe ich doch schon recherchiert – Eigenes wiederfinden und richtig zitieren / Haven’t we researched this before? – Finding your earlier work and citing it clearly:** `schreibpraxis-zitieren/index.html` und `index.en.html`; sechs Stationen je Sprache zu früheren Buchtexten, Eigenverweisen, Fachbelegen und Quellenlücken. Website-Ausgabe unter `website/zitieren/`.

Am 10. November 2026 zunächst Deutsch lokal beauftragt, anschließend Englisch, beide Übersichten und Veröffentlichung nach erfolgreichen Prüfungen. Gemeinsamer Aufbau: `python3 scripts/build_research_writing_practice.py --publish` (nur lokale Dateien). Inhalte in `inhalt.json` und `content.en.json` der jeweiligen Folge. Beide Übersichten zeigen alle fünf Folgen als vollständig anklickbare Kacheln; die drei bisherigen Folgen behalten ihre Reihenfolge. Recherche und Zitieren stehen als vierte und fünfte Kachel mit eigener Illustration und Einordnung. Stationsgleicher Sprachwechsel, Logo-Link zur passenden Übersicht und Hinweis unter dem Menü auf jeder Seite. Gespräche und Buchfunde sind erfunden, die benannte Fachinformation ist tatsächlich geprüft. [Gemeinsamer Prüfvermerk](SCHREIBPRAXIS-RECHERCHE-ZITIEREN-PRUEFUNG.md). Veröffentlichung erst nach bestätigtem Deployment als abgeschlossen melden.

## Wiederverwendbare Vorlagen

Zentraler Einstieg für neue Folgen: [Vorlagen und Bauanleitung](../templates/schreibpraxis/README.md), [English](../templates/schreibpraxis/README.en.md). Dort liegen Seiten-/Übersichts-/Kachelgerüste, Grundstil und wiederverwendbare Arbeitsaufträge. Die vorhandenen Folgen behalten ihre versionierten Erzeuger; Änderungen an den neuen Vorlagen bauen sie nicht automatisch um. Logo und Kopftext einer Folge führen zur sprachlich passenden Übersicht, der Folgentitel zum Folgenanfang.

## Gemeinsame Gestaltung

Originales Federlogo aus `assets/logo.svg`, GhostWriter-Wortmarke als Text, Serienname darunter. Orange `#f07f2e` für Linie, Fortschritt und Hervorhebungen; dunkleres Orange `#b9551d` für lesbare Akzentschrift und Links. Warmer heller Hintergrund, dunkle Schrift, Serifenschrift für den großen Titel, Systemschrift für Navigation und Erläuterung.

Seitenstrecke mit wenigen Hauptstationen, seitlicher Navigation, aktiver Station, Fortschritt und Vor-/Zurück. Auf schmalen Ansichten Navigation horizontal und Inhalte einspaltig. Inhalte ohne JavaScript nutzbar. Logo und Gestaltung nicht mit jeder Folge neu erfinden. Grundlage für diese Folge ist das vorhandene `schreiben-mit-ghostwriter/stil.css`; folgenspezifische Ergänzungen separat halten.

## Redaktion

Dialoge sparsam und gut lesbar als Gespräch darstellen; Rollen sichtbar benennen. Erfundene Dialoge und Textproben unmittelbar kennzeichnen. Vollständig simulierte Folgen erhalten auf jeder Seite einen deutlichen Hinweis direkt unter der Stationsnavigation. Anbieterbezeichnungen begründen keinen echten Anbieteraufruf, typisches Verhalten oder Qualitätsrangfolge.

Menschliche Beiträge wie Erfahrung, Antwort, Korrektur und Auswahl sichtbar machen. Nicht nur KI-Ausgaben präsentieren. Faktische Abläufe und Simulationen unterscheiden. Privates abstrahieren, Originalquellen nicht versehentlich veröffentlichen. Erklärtext, Gespräch und Ergebnis typografisch trennen.

Bei Veröffentlichung beide Sprachen, stationsgleichen Sprachwechsel, Rückweg zur Website und Textlink auf der Startseite vorsehen. Keine zusätzliche Kachel ohne ausdrücklichen Gestaltungswunsch. Lokale Erstellung, Upload und Veröffentlichung bleiben getrennte Schritte.



## Übersicht

Zweisprachiger Einstieg: `website/schreibpraxis.html` und `website/schreibpraxis.en.html`, erzeugt mit `python3 scripts/build_writing_practice_index.py`. Fünf Text-/Illustrationskacheln führen in beiden Sprachen zu den Folgen; Recherche und Zitieren sind als vierte und fünfte Kachel gleichwertig eingebunden. README und HTML-Startseite verlinken die Übersicht als Text; dort keine zusätzliche Hauptkachel. Original-Logo in `website/assets/logo.svg`.

---
Entwickelt mit Unterstützung von Claude (Anthropic)
Entwickelt mit Unterstützung von Codex (OpenAI)
