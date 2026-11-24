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

**Testauswahl im Pull Request (#439):** Die Prüfung `validate` führt bei einem Pull Request nur die Tests aus, die zu den geänderten Dateien passen (`scripts/select_tests.py`). Reine Doku-Änderungen lösen die Tests aus, die `docs/` lesen. Ein geändertes Skript löst die Tests aus, die es oder ein Skript, das es importiert, verwenden. Ein geänderter Test läuft selbst. `START.md`, `CLAUDE.md`, `AGENTS.md`, Vorlagen unter `templates/` und einzelne Workflows unter `.github/workflows/` lösen die Tests aus, die den Pfad als Zeichenkette im Code nennen oder den Ordner als Ganzes durchlaufen, dazu die Tests der Skripte, die das tun (#485); eine Erwähnung in Hilfetexten oder Kommentaren zählt nicht. Nennt niemand die Datei, läuft alles. Ein Abgleich der allgemeinen Skills (`.claude/skills/<name>/SKILL.md`, `ghostwriter-skills.yml`) löst die Tests aus, die Skills oder die Quellenangabe lesen, dazu die Doku-Prüfung (#567); übrige Dateien unter `.claude/` lösen die volle Suite aus. Die Satzpakete (TeX, pandoc) werden nur installiert, wenn ein ausgewählter Test sie braucht. Die volle Suite läuft im Zweifel: bei `workflow.yml`, Manifest, übrigen Dateien unter `.github/`, Schemas, Starter, Testdaten, gelöschten oder umbenannten Dateien, Skripten ohne zugeordneten Test und wenn mehr als 60 % der Tests betroffen wären. Auf dem Standard-Branch läuft sie nach jedem Merge, außer der Stand wurde schon im Pull Request vollständig und grün geprüft (#485): Der PR-Lauf hinterlegt dann den geprüften Baum als Artefakt `validate-full-<tree>`, und hat der Merge-Commit genau diesen Baum, prüft der Lauf auf dem Standard-Branch nur Schema, Doku und Website. Hat sich der Standard-Branch zwischen PR-Lauf und Merge bewegt, läuft die volle Suite. Auch auf dem Standard-Branch bricht ein neuer Push den älteren Lauf ab. Änderungspakete deshalb klein und thematisch schneiden: Doku getrennt von Programmänderungen, breite Dateien wie `START.md` nur dort ändern, wo es nötig ist. `validate` startet die Tests über `scripts/run_tests.py`: jedes Testmodul in einem eigenen Prozess, so viele gleichzeitig wie der Runner Kerne hat, Module mit Satz zuerst; am Ende stehen die langsamsten Module (#485). Lokal gilt weiter die volle Suite bzw. `verify.py` (`python3 scripts/run_tests.py` ist dieselbe Suite, parallel); `python3 scripts/select_tests.py --files <liste>` zeigt die Auswahl.

Vor der **öffentlichen Freigabe** beide Sprachen gerendert ansehen: Desktop und schmale Ansicht, Tastatur und Fokus, lange Tabellen, Ablaufgrafiken, Suchtreffer/Leersuche/kein Treffer, Sprachwechsel und Beispiele. Browserprüfung nur mit der im Arbeitskontext erforderlichen ausdrücklichen Freigabe. Fehlt sie, diese Abnahme offen lassen; Strukturprüfungen sind kein Ersatz für die Sichtprüfung.

## Prüfbericht vor dem Pull Request

`scripts/verify.py` (#390) führt die festen Schritte nacheinander aus und bricht beim ersten harten Fehler ab: Tests, `check_docs.py` (mit `--ui <ordner>`, wenn angegeben), Website aufbauen und prüfen, `library.py check-program`, Secret-Suche in den hinzugefügten Zeilen gegenüber `origin/main` und `git diff --check`. Die Secret-Suche nennt nur Muster und Fundstelle, nie den Wert. Geprüft wird der committete Stand; vor dem Aufruf also committen.

```sh
python3 scripts/verify.py --ui ../ghostwriter-ui --out /tmp/pruefbericht.md
python3 scripts/verify.py --skip tests --abnahme geprüft --abnahme-beleg "chillyconcane/YAWA, 0.7.0, Umschlag gebaut"
```

Der Bericht zeigt je Schritt „bestanden“, „nicht bestanden“, „übersprungen“ oder „nicht ausgeführt“, das Gesamturteil „bereit für PR“ oder „nicht bereit“ und kommt so in die PR-Beschreibung. Eigene Zeile **Abnahme im Buch** (`geprüft`, `fehlgeschlagen`, `nicht durchgeführt`, `entfällt`) mit Bibliothek, Programmversion und Beleg: Grüne Tests, Merge oder Release beweisen nicht, dass eine Änderung in einer Bibliothek funktioniert. Fremde Bibliotheken nur mit Freigabe prüfen. Darunter steht der nächste erlaubte Schritt; Prüfen, Mergen und Veröffentlichen bleiben getrennt.

Von Hand bleibt die Durchsicht des Diffs (ungewollte Änderungen, Fehlerbehandlung, Randfälle) und diese Doku-Checkliste:

- Betroffene Anleitungen in `docs/` auf Deutsch und Englisch nachgezogen
- Alle genannten Pfade existieren, Beispielbefehle laufen
- Links funktionieren, keine veralteten Verweise
- Planungen sind gekennzeichnet

Doku, die nicht zur Wirklichkeit passt, ist schlimmer als keine.

## Fester Bestandteil jeder Programmveröffentlichung

1. Funktionsumfang und Programmversion in `ghostwriter-manifest.yml` bestätigen. Die Website liest diese Version beim Aufbau direkt daraus; keine zweite Versionsnummer pflegen. Eine vorgezogene Dokumentationsänderung erhöht nicht allein die Produktversion.
2. Betroffene deutsche und englische Anleitungen im selben Änderungspaket aktualisieren und fachlich abnehmen. Im PR bzw. in den Release Notes festhalten, welche Anleitungen zu welchem Funktionsstand gehören. Bei unveränderten Inhalten begründen, warum kein Nachziehen nötig ist.
3. Obige lokale Prüfungen, gerenderte Abnahme und abschließende Dateiauswahl durchführen. Dokumentationsstand, Quellencommit und Prüfnachweise in der Release-Checkliste festhalten.
3a. **Release vorbereiten** (`.github/workflows/release-prepare.yml`, #488, ohne Freigabe, beliebig oft): von Hand mit `version` starten. Der Ablauf legt den Branch `release/<version>` an, setzt die Version im Manifest und fügt in `docs/UPDATES.md` und `docs/UPDATES.en.md` einen Entwurf der Release Notes aus den seit dem letzten Tag gemergten PRs ein (`scripts/release.py prepare`; ein vorhandener Entwurf wird nicht überschrieben). Danach prüft er Doku (`check_docs.py`), den Prüfbericht ohne Tests (`verify.py --skip tests`), alle Programmsprachen gegenüber Deutsch (`release.py languages`: fehlende und überzählige Schlüssel, abweichende Platzhalter, Doku-Seiten ohne Fassung; Sprachen werden aus `templates/ui/i18n/`, `templates/i18n/views/` und `docs/site.json` ermittelt) und die offenen Issues im Meilenstein (`v1.0` für 1.0.0); gibt es `docs/TESTPLAN-v<X.Y>.md`, nennt der Bericht die Zahl der offenen Handprüfungen (⏳), ohne dass sie das Urteil ändern. Ergebnis ist ein Bericht (Artefakt `release-report-<version>`, bei offenem Release-PR auch als Kommentar) mit dem Gesamturteil **bereit zum Scharfschalten** oder **nicht bereit**: nicht bereit bei Lücken in de oder en (#74), roter Prüfung oder offenem `bug` im Meilenstein; weitere Sprachen mit Lücken gelten als „teilweise“. Der Entwurf trägt eine Markierung; solange sie in den Notes steht, verweigert „Release veröffentlichen“ den Start. Die Sitzung überarbeitet die Notes im Release-PR, entfernt die Markierung und lässt den PR übernehmen. Den Release-PR legt die Sitzung an (mit dem Bericht in der Beschreibung), weil ein vom Ablauf angelegter PR `validate` nicht auslöst; dort läuft die volle Testsuite, und sie muss vor dem Veröffentlichen grün sein. Der Bericht steht außerdem in der Zusammenfassung des Laufs.
4. Übernahme des PR und öffentliche Bereitstellung **getrennt** ausdrücklich freigeben lassen. Ein Upload oder Merge veröffentlicht keine Dokumentation.
5. Erst nach Freigabe auf dem freigegebenen `main`-Commit den ausschließlich manuellen Ablauf **Release veröffentlichen** (`.github/workflows/release.yml`, #488) starten: Eingaben `version` (wie im Manifest) und `confirm` (dieselbe Version noch einmal). Auslöser im Chat ist der ausdrückliche Satz „Release <version> freigeben und veröffentlichen“; ein bloßes „ok“ reicht nicht. Der Ablauf prüft mit `scripts/release.py check` Version, Bestätigung und die Release Notes (ohne Entwurfsmarkierung) in `docs/UPDATES.md` und `docs/UPDATES.en.md`, legt Tag (`v1.0` für 1.0.0, `v1.0.1` für Patch-Stände) und GitHub-Release an, veröffentlicht die Dokumentationswebsite und prüft danach die öffentliche Versionsanzeige je Sprache. Mit `dry_run: true` wird alles geprüft und gebaut, aber nichts angelegt oder veröffentlicht. Ein erneuter Start setzt fort: ein vorhandener Tag am selben Commit und ein vorhandenes Release bleiben unverändert; zeigt der Tag auf einen anderen Commit, bricht der Ablauf ab (im Trockenlauf nur Warnung). Keine Push-, PR- oder Release-Auslösung; nur Hauptrepository und `main`, für Forks und Bücher keine Website. **Vorabversion (Pre-release):** Denselben Ablauf vom Branch `release/<version>` aus starten, mit `prerelease: N`, nach dem ausdrücklichen Satz „Pre-release <version>-rc.N freigeben“. Er prüft wie oben, legt den Tag `v<X.Y>-rc.N` (z. B. `v1.0-rc.1`) und ein GitHub-Release mit Vermerk „Pre-release“ an und veröffentlicht **keine** Website. `main` bleibt unverändert, der tägliche Update-Lauf bringt den Büchern also nichts Neues. Zum Ausprobieren in einem Testbuch bzw. einer Testbibliothek dort einmal in `ghostwriter-manifest.yml` (Standard-Branch) `upstream.ref: release/<version>` setzen und „GhostWriter aktualisieren“ von Hand starten; das Update bringt den Stand des Release-Branchs und setzt `ref` dabei mit der neuen Programmdatei wieder auf `main` zurück. Fremde Bibliotheken nur mit Freigabe ihres Eigentümers. Das endgültige Release vom Release-PR aus wie in diesem Schritt; Pre-release von `main` und endgültiges Release von einem Release-Branch lehnt `release.py check` ab.

Der bisherige Ablauf **Beispielseiten veröffentlichen** (`pages.yml`, `documentation: true`) bleibt für eine Website-Veröffentlichung ohne Release; Standardwert `false` lässt den Beispielseitenweg bestehen.
6. Nach bestätigtem Lauf die öffentliche Versionsanzeige, beide Sprachen, Suche, Grafiken, Sprachwechsel und bisherigen Beispieladressen prüfen. Tatsächlichen Quellencommit, Lauf und öffentlichen Dokumentationsstand in den Release Notes bestätigen. Ist die Veröffentlichung zurückgestellt oder fehlgeschlagen, das ausdrücklich nennen; Release-Abschluss nicht als vollständig dokumentiert melden.

Der vorbereitete Zielpfad ist `/GhostWriter/documentation/de/` bzw. `/en/` im bereits verwendeten Pages-Auftritt. Die Freigabe dieses PR allein aktiviert ihn nicht. Bis zur gesonderten Freigabe keine Pages-Action starten und keine Hosting-Einstellung ändern. Eine Rückkehr zum bisherigen Beispielauftritt wäre ein erneut ausdrücklich freizugebender manueller Lauf mit `documentation: false`.

## Wiki-Aufbau

Das veröffentlichte Wiki wird aus denselben Quellen erzeugt. Titel, globale Fußzeile, Sprachwechsel und Prüfungen sind in [Wiki-Gestaltung](WIKI-GESTALTUNG.md) und [Wiki appearance](WIKI-APPEARANCE.en.md) beschrieben. Der Aufbau veröffentlicht nichts automatisch.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
