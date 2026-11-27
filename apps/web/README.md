# GhostWriter – eigene Web-App (Stufe 1, ohne Chat)

Erster Wurf der eigenen App aus [#662](https://github.com/ploeffler/GhostWriter/issues/662): dieselben Ansichten wie in der Claude-Web-App
([`apps/claude/`](../claude/README.md)), aber ohne Claude und ohne Konnektor. Sie läuft aus einem einzigen Ordner direkt im Browser und spricht
über die GitHub-REST-Schnittstelle mit einem **Fine-grained Token** mit GitHub.

**Stand:** Entwurf, noch nicht veröffentlicht. Es gibt noch keine Installation als App (PWA), keinen Offline-Betrieb, keine Konfliktlösung und keine
Einstellungen; das folgt in den nächsten Schritten von #662. Sie ist **nicht** Teil dessen, was Updates in Bibliotheken kopieren.

## Was sie kann

- Anmelden mit Token, Repository wählen (`owner/repo`), Bücherregal bzw. Buch öffnen, Projektübersicht, Kapitel, Abschnitt, Figuren, Daten.
- Abschnitt schreiben und speichern: ein Commit je Aufgabe auf den Arbeits-Branch `ghostwriter/<buch-branch>`, das Änderungspaket wird angelegt;
  Freigaben wie in der Claude-Web-App (mit Prüfliste und Eintrag in `approvals.yml`). Ins Buch kommt es erst über „Änderungen übernehmen“ mit Bestätigung.
- Was die App nicht kann, ist vor dem Klick ausgegraut, mit Grund (`apps/claude/aktionen.json`, Knopf-Inventar). Fragen an eine KI gibt es hier noch
  nicht (`S.sample` ist leer, keine Chat-Seitenleiste).

## Token

Auf GitHub unter *Settings → Developer settings → Fine-grained tokens* einen Token anlegen: **Repository access** nur das eine Repository mit den Büchern,
**Permissions** „Contents“ und „Pull requests“ jeweils *Read and write*. Der Token bleibt nur in diesem Browser (`localStorage`, Schlüssel `gw.token`),
wird nur an `api.github.com` gesendet und mit „Abmelden“ gelöscht. Er steht nie im Repository, in Commits oder in Fehlermeldungen.

## Aufbau

- `index.src.html`, `ports-web.js` (GitHub-REST, Formen wie `GW_PORTS` in [`apps/claude/ports-claude.js`](../claude/ports-claude.js)), `boot-web.js`.
- Ansichten und Abläufe kommen aus [`apps/shared/`](../shared). `python3 apps/web/build.py` baut `index.html` und kopiert die Widget-Laufzeit
  (`vendor/gw-lite.js`, `vendor/icons.css`) aus `apps/claude/vendor/`; `--check` prüft den Stand. `vendor/js-yaml.min.js` (MIT) liegt fest hier.
- Tests: `tests/test_app_web.py` und `apps/web/tests/ports-web.test.cjs` (Anschluss gegen einen nachgestellten `fetch`, ohne Netz).
  Ausprobieren: `index.html` im Browser öffnen oder einen kleinen Webserver im Ordner starten.

## Grenzen dieser Fassung

- Die Commit-Kennung einer Referenz holt die App mit einer zusätzlichen Anfrage und merkt sie sich wenige Sekunden (Rate-Limit von GitHub).
- Schreiben ist nur mit schnellem Vorrücken des Branchs möglich (`force: false`). Hat sich der Branch inzwischen geändert, meldet die App das und
  überschreibt nichts.
- Hinweise im Text nennen noch „Claude“ (gemeinsame Ansichten); die Texte werden mit den nächsten Schritten angepasst.
- Nicht gegen ein echtes Repository mit echtem Token geprüft: Der Durchlauf Anmelden, Buch öffnen, Abschnitt speichern lief im Browser gegen eine nachgestellte GitHub-Schnittstelle.
