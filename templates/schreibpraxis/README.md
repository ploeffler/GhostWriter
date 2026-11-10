# Schreibpraxis – Vorlagen und Bauanleitung

[English](README.en.md)

Diese Vorlagen sind der Ausgangspunkt für neue Schreibpraxis-Folgen. Bestehende Folgen sind bereits mit ihren jeweiligen Quellen und Erzeugern versioniert; sie werden durch dieses Paket nicht automatisch umgebaut. Der Grundstil ist aus der ersten Folge übernommen und um Übersichts- und Navigationselemente ergänzt. Änderungen hier ändern keine bereits erzeugten Seiten.

## Dateien

| Datei | Verwendung |
| --- | --- |
| `folge.html` | Eine Station einer Seitenstrecke |
| `uebersicht.html` | Einstieg mit den Kacheln aller Folgen |
| `kachel.html` | Eine ganze, anklickbare Kachel |
| `grundstil.css` | Farben, Schriften, Logo-Kopf, Dialoge, Menü, Fortschritt, Kacheln und schmale Ansichten |
| `auftrag.de.md` / `brief.en.md` | Wiederverwendbarer Arbeitsauftrag für eine neue Folge |

Die `.html`-Dateien sind Vorlagen mit Platzhaltern, keine fertigen Webseiten. Sie lassen sich mit Pythons `string.Template.substitute` befüllen. Unbekannte oder fehlende Platzhalter sollen den Aufbau abbrechen. Alle Textwerte vor dem Einsetzen mit `html.escape` behandeln; nur selbst erzeugtes HTML in die mit `_HTML` bezeichneten Felder einsetzen. `$ILLUSTRATION_SVG` ist eine geprüfte, im Repository gestaltete Illustration. Fortschritt als Zahl von 0 bis 100 einsetzen.

```python
from pathlib import Path
from string import Template

template = Template(Path('templates/schreibpraxis/folge.html').read_text())
# values enthält alle unten beschriebenen Felder, Texte bereits HTML-escaped.
page = template.substitute(values)
```

## Verbindliche Gestaltung und Navigation

- Original-Federlogo aus `assets/logo.svg`. Orange `#f07f2e`, lesbarer dunkler Akzent `#b9551d`, warmer heller Hintergrund, Serifentitel und Systemschrift für den übrigen Text.
- „Schreibpraxis“ steht sichtbar ausschließlich unter GhostWriter; englisch „Writing practice“. Der individuelle Folgentitel steht über der Stationsnavigation.
- **Logo und Text einer Folge führen zur Schreibpraxis-Übersicht der jeweiligen Sprache.** Der Folgentitel im Menü führt zum Anfang der Folge. Das Logo der Übersicht führt zur GhostWriter-Startseite.
- Vor-/Zurück, aktive Station und stationsgleicher Sprachwechsel. Kein Link zum Anfang der Folge als Ersatz für einen Übersicht-Link.
- Vollständig simulierte Folgen: gut sichtbarer Hinweis auf jeder Seite unmittelbar unter dem Menü. Teilweise erfundene Dialoge direkt als solche kennzeichnen. Reale Abläufe, abstrahierte Inhalte und Simulation unterscheiden; keine Anbieterleistung aus erfundenen Dialogen ableiten.
- Ganze Kachel anklickbar, sinnvolle Reihenfolge, kurze Beschreibung und Einordnung des Beispiels. Buchentwicklung steht aktuell zuerst. README und HTML-Startseite verlinken die Übersicht als Text, ohne zusätzliche Hauptkachel.
- Responsive, ohne externe Schriftarten oder JavaScript nutzbar. Claude- und Codex-Hinweis je einmal in der passenden Sprache in der Fußzeile.

## Platzhalter

Gemeinsam: `LANG`, `PAGE_TITLE`, `STYLE_URL`, `LOGO_URL`, `OTHER_LANG`, `OTHER_URL`, `OTHER_LABEL`, `SERIES_LABEL`, `NAV_LABEL`, `CLAUDE_CREDIT`, `CODEX_CREDIT`.

Folge: `OVERVIEW_URL`, `OVERVIEW_LABEL`, `EPISODE_URL`, `EPISODE_TITLE`, `PAGE_POSITION`, `PAGE_COUNT`, `NAV_ITEMS_HTML`, `SIMULATION_NOTICE_HTML`, `STAGE_LABEL`, `LEAD`, `CONTENT_HTML`, `PROGRESS_PERCENT`, `PREVIOUS_LINK_HTML`, `NEXT_LINK_HTML`.

Übersicht: `HOME_URL`, `HOME_LABEL`, `LEAD`, `TILES_HTML`. Kachel: `EPISODE_URL`, `ILLUSTRATION_SVG`, `EVIDENCE_LABEL`, `EPISODE_TITLE`, `DESCRIPTION`, `OPEN_LABEL`.

`NAV_ITEMS_HTML`: geordnete Listeneinträge; genau ein Link mit `aria-current="page"`. `SIMULATION_NOTICE_HTML`: beispielsweise `<aside class="simulation"><strong>Vollständig simulierter Dialog</strong>…</aside>`; nur bei einer nicht simulierten Folge leer lassen und tatsächliche Herkunft passend erläutern. `CONTENT_HTML` kann `.message` mit sichtbarer Rollenbezeichnung, `.message.author` für Autorenantworten und `.result` für eine Zusammenfassung verwenden. Ein fehlender Vorgänger wird durch ein leeres Element ersetzt, der letzte nächste Link führt zum Folgenanfang. Übersetzungen bilden dieselben Stationen ab.

## Bestehende Quellen und reproduzierbarer Aufbau

| Gegenstand | Quelle / Befehl ab Repository-Wurzel |
| --- | --- |
| Übersicht | `python3 scripts/build_writing_practice_index.py` |
| Vom Gespräch zum eigenen Text | `python3 beispielmaterial/schreiben-mit-ghostwriter/erzeugen.py --publish` |
| Augmentiert arbeiten | `python3 beispielmaterial/schreibpraxis-augmentiert/erzeugen.py --publish` |
| Aus einer Idee wird ein Krimi | `python3 beispielmaterial/schreibpraxis-buchentwicklung/erzeugen.py --publish` |
| Serienvorgaben | [SCHREIBPRAXIS-SERIE.md](../../beispielmaterial/SCHREIBPRAXIS-SERIE.md) |

Die Erzeuger liefern beide Sprachen. Drehbücher, Inhalte, Übersetzungen und besondere CSS-Regeln liegen im jeweiligen Quellverzeichnis. `--publish` erzeugt nur lokale Dateien unter `website/`; kein Upload oder Deploy. Abhängigkeiten für Markdown und HTML-Prüfungen stehen in `scripts/docsite/requirements.txt`.

## Neue Folge liefern und prüfen

1. Lernziel, Titel, Herkunft und wenige Hauptstationen festlegen. Zuerst den inhaltlichen Ablauf entwickeln; Fragen aus den Antworten ableiten, menschliche Entscheidungen sichtbar machen.
2. Quellen und Erzeuger unter `beispielmaterial/` ablegen. Deutsch und Englisch gemeinsam pflegen, keine privaten Originaldialoge veröffentlichen.
3. Ausgabe nach `website/<folge>/` erzeugen. In der Übersicht Quelle und Kachel in beiden Sprachen ergänzen. Relative Pfade unterscheiden sich zwischen Quellvorschau und öffentlicher Ausgabe; beide prüfen.
4. Alle Gesprächsbeiträge und Ergebnisse gegen die Quelle prüfen. Linkziele, Sprachwechsel, aktives Menü, Logo-Ziel, Simulationshinweis, Reihenfolge und Fußzeilen prüfen. Erneuter Aufbau muss dieselben Dateien ergeben.
5. `python3 scripts/check_docs.py`, `python3 scripts/package_docs_site.py` und `git diff --check` ausführen. Vor Übertragung Ergebnis mitteilen. Visuelle Abnahme, soweit autorisiert, mit schmaler Ansicht und Tastatur; fehlende Abnahme offen ausweisen.
6. Nur ausdrücklich beauftragte Dateien übertragen. Upload, Merge und Live-Veröffentlichung gesondert autorisieren, sofern der bestehende Auftrag sie nicht schon umfasst. Für die manuelle Pages-Action `documentation=true` setzen, damit die zentrale Dokumentationswebsite erhalten bleibt. Nach dem Deploy Erreichbarkeit und die tatsächlichen Linkziele prüfen.

---
Entwickelt mit Unterstützung von Claude (Anthropic)
Entwickelt mit Unterstützung von Codex (OpenAI)
