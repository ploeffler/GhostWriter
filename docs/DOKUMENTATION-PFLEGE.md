# Dokumentation pflegen und veröffentlichen

## Gemeinsame Quelle und Verantwortung

`docs/` ist die gemeinsame Inhaltsquelle der Programmdokumentation. Die zentrale Website wird daraus erzeugt. Es gibt keine zweite, unabhängig gepflegte Wiki-Fassung und keinen automatischen Upload in ein Wiki. Falls ein Wiki als Einstieg verwendet wird, verweist es auf dieselbe Dokumentation; eine Einrichtung oder Änderung des GitHub-Wikis ist nicht Teil dieses Auftrags.

Bei jeder Änderung an Funktionen, Bedienung, Einrichtung oder Arbeitsabläufen gehören die betroffenen Anleitungen **im selben Änderungspaket** dazu. Deutsche und englische Fassungen, Beispiele, Grafiken, Navigation und Verweise gemeinsam nachziehen. Neue oder geänderte Seitenpaare in `docs/site.json` eintragen. Geplante Funktionen ausdrücklich kennzeichnen; keine Freigabe oder Unterstützung aus einem grünen Test ableiten.

Der Änderungsautor prüft die fachliche Übereinstimmung mit dem tatsächlichen Programm: Voraussetzungen, Befehle, Zustände, Freigaben, Schreibwirkungen, Grenzen und Fehlermeldungen anhand von Implementierung und passenden Tests abgleichen. Im PR betroffene Quellen, geprüfte Abläufe, Ergebnis und verbleibende Lücken nennen. Der Review prüft diese Angaben; ungeprüfte Inhalte oder fehlende Übersetzungen verhindern die Dokumentationsabnahme. Automatische Links ersetzen diese fachliche Prüfung nicht.

## Lokal aufbauen und ansehen

Abhängigkeiten einmal in einer lokalen Python-Umgebung installieren:

```sh
python3 -m venv .venv-docs
.venv-docs/bin/pip install -r scripts/docsite/requirements.txt
.venv-docs/bin/python scripts/build_docs_site.py
.venv-docs/bin/python scripts/package_docs_site.py
.venv-docs/bin/python -m http.server 8000 --bind 127.0.0.1 --directory build/pages
```

Die lokale Vorschau liegt unter `http://127.0.0.1:8000/documentation/de/index.html` bzw. `/documentation/en/index.html`. Mit Strg+C beenden. Die Suche lädt ihren Index lokal über HTTP, nicht über `file://`. Die Website benötigt keinen Suchdienst, keine Analysewerkzeuge und keine externen Schriftarten. Ohne JavaScript bleiben alle Anleitungen und die Navigation nutzbar.

`build/documentation/` enthält nur die erzeugte Programmdokumentation. `build/pages/` enthält zusätzlich die bereits freigegebenen öffentlichen Beispielseiten aus `website/`; es kopiert keine privaten Beispielquellen. Die neue Dokumentation verlinkt diese vorhandenen Seiten. Nur im erzeugten Paket erhalten die zwei Übersichtsseiten zusätzlich einen Dokumentationslink. `website/` wird nicht verändert. Die Ausgabe ist kein eigenständig zu pflegender Inhalt und bleibt von Git ausgeschlossen.

## Öffentliche Inhaltsgrenze

`docs/site.json` wählt jede Handbuchquelle und ihr Sprachpaar ausdrücklich aus. Es gibt kein rekursives Kopieren aller `docs/`-Inhalte. Nur tatsächlich referenzierte Abbildungen unter `docs/bilder/` werden übernommen. Technische Repository-Verweise sind gesondert aufgelistet und sichtbar als solche mit Sprache markiert. Interne Planungs-/Prüfverweise werden nicht öffentlich verlinkt; unbekannte relative Ziele brechen den Aufbau ab, bis sie fachlich klassifiziert wurden.

Planungsnotizen, Arbeitsaufträge, Testberichte, Buchtexte und Gesprächssicherungen gehören nicht in den öffentlichen Website-Aufbau oder Suchindex. Die vorhandenen bewusst veröffentlichten „So einfach“-Beispiele werden unverändert wiederverwendet; ihre privaten Quellen werden nicht erneut eingelesen. Beim Ändern der Auswahl öffentliche Eignung jeder Quelle und Abbildung prüfen. Ein erneuter Aufbau entfernt veraltete erzeugte Seiten und Assets.

## Erforderliche Prüfungen vor Upload und Release

```sh
python3 scripts/check_docs.py
python3 scripts/build_docs_site.py
python3 scripts/build_docs_site.py --check
python3 scripts/package_docs_site.py
python3 -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Mit verfügbarer passender UI-Kopie zusätzlich `python3 scripts/check_docs.py --ui <ordner>` ausführen. Die normale Projektprüfung baut die Website ohne Veröffentlichungsrechte. Die Tests prüfen Inhaltsgrenzen, Sprachpaare, lokale Links und Anker, Fußzeile, Versionsanzeige, Suchindex, echte Suchlogik (mit Node) und die manuelle Veröffentlichungsschranke.

Vor der **öffentlichen Freigabe** beide Sprachen gerendert ansehen: Desktop und schmale Ansicht, Tastatur und Fokus, lange Tabellen, Ablaufgrafiken, Suchtreffer/Leersuche/kein Treffer, Sprachwechsel und Beispiele. Browserprüfung nur mit der im Arbeitskontext erforderlichen ausdrücklichen Freigabe. Fehlt sie, diese Abnahme offen lassen; Strukturprüfungen sind kein Ersatz für die Sichtprüfung.

## Fester Bestandteil jeder Programmveröffentlichung

1. Funktionsumfang und Programmversion in `ghostwriter-manifest.yml` bestätigen. Die Website liest diese Version beim Aufbau direkt daraus; keine zweite Versionsnummer pflegen. Eine vorgezogene Dokumentationsänderung erhöht nicht allein die Produktversion.
2. Betroffene deutsche und englische Anleitungen im selben Änderungspaket aktualisieren und fachlich abnehmen. Im PR bzw. in den Release Notes festhalten, welche Anleitungen zu welchem Funktionsstand gehören. Bei unveränderten Inhalten begründen, warum kein Nachziehen nötig ist.
3. Obige lokale Prüfungen, gerenderte Abnahme und abschließende Dateiauswahl durchführen. Dokumentationsstand, Quellencommit und Prüfnachweise in der Release-Checkliste festhalten.
4. Übernahme des PR und öffentliche Bereitstellung **getrennt** ausdrücklich freigeben lassen. Ein Upload oder Merge veröffentlicht keine Dokumentation.
5. Erst nach Freigabe auf dem freigegebenen `main`-Commit den ausschließlich manuellen Ablauf **Beispielseiten veröffentlichen** mit `documentation: true` starten. Standardwert ist `false`: der bisherige Beispielseitenweg bleibt bestehen. Keine Push-, PR- oder Release-Auslösung. Der Ablauf ist auf Hauptrepository und main beschränkt; für Forks/Bücher keine automatische Website.
6. Nach bestätigtem Lauf die öffentliche Versionsanzeige, beide Sprachen, Suche, Grafiken, Sprachwechsel und bisherigen Beispieladressen prüfen. Tatsächlichen Quellencommit, Lauf und öffentlichen Dokumentationsstand in den Release Notes bestätigen. Ist die Veröffentlichung zurückgestellt oder fehlgeschlagen, das ausdrücklich nennen; Release-Abschluss nicht als vollständig dokumentiert melden.

Der vorbereitete Zielpfad ist `/GhostWriter/documentation/de/` bzw. `/en/` im bereits verwendeten Pages-Auftritt. Die Freigabe dieses PR allein aktiviert ihn nicht. Bis zur gesonderten Freigabe keine Pages-Action starten und keine Hosting-Einstellung ändern. Eine Rückkehr zum bisherigen Beispielauftritt wäre ein erneut ausdrücklich freizugebender manueller Lauf mit `documentation: false`.

## Wiki-Aufbau

Das veröffentlichte Wiki wird aus denselben Quellen erzeugt. Titel, globale Fußzeile, Sprachwechsel und Prüfungen sind in [Wiki-Gestaltung](WIKI-GESTALTUNG.md) und [Wiki appearance](WIKI-APPEARANCE.en.md) beschrieben. Der Aufbau veröffentlicht nichts automatisch.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
