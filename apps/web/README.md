# GhostWriter – eigene Web-App (Stufe 1, ohne Chat)

Erster Wurf der eigenen App aus [#662](https://github.com/ploeffler/GhostWriter/issues/662): dieselben Ansichten wie in der Claude-Web-App
([`apps/claude/`](../claude/README.md)), aber ohne Claude und ohne Konnektor. Sie läuft aus einem einzigen Ordner direkt im Browser und spricht
über die GitHub-REST-Schnittstelle mit einem **Fine-grained Token** mit GitHub.

**Stand:** Entwurf, noch nicht veröffentlicht. Installierbar als App (PWA), die App-Hülle läuft ohne Netz, und ein Abschnitt lässt sich ohne Netz schreiben und
später hochladen. Es gibt noch keine Konfliktlösung (ein Konflikt wird gemeldet, nichts wird überschrieben) und keine Einstellungen; das folgt in den
nächsten Schritten von #662. Sie ist **nicht** Teil dessen, was
Updates in Bibliotheken kopieren.

## Was sie kann

- Anmelden mit Token, Repository wählen (`owner/repo`), Bücherregal bzw. Buch öffnen, Projektübersicht, Kapitel, Abschnitt, Figuren, Daten.
- Abschnitt schreiben und speichern: ein Commit je Aufgabe auf den Arbeits-Branch `ghostwriter/<buch-branch>`, das Änderungspaket wird angelegt;
  Freigaben wie in der Claude-Web-App (mit Prüfliste und Eintrag in `approvals.yml`). Ins Buch kommt es erst über „Änderungen übernehmen“ mit Bestätigung.
- Was die App nicht kann, ist vor dem Klick ausgegraut, mit Grund (`apps/claude/aktionen.json`, Knopf-Inventar). Fragen an eine KI gibt es hier noch
  nicht (`S.sample` ist leer, keine Chat-Seitenleiste).

## Installieren und ohne Netz (PWA, #35)

`manifest.webmanifest` und der Service Worker `sw.js` machen die Seite installierbar (Browser-Menü „App installieren“; nur über `https` oder `localhost`).
Der Service Worker legt die **App-Hülle** (Seite, Widget-Laufzeit, Symbole, `js-yaml`) im Browser ab; die App startet dann auch ohne Netz. Alles von anderen
Adressen, vor allem `api.github.com` mit dem Token, geht unberührt ans Netz und wird **nie** zwischengespeichert. Der Name des Speichers enthält einen Hash der
Hülle (`build.py`); ein neuer Stand ersetzt den alten beim nächsten Laden.

Die Leiste oben zeigt **Offline** („gelesen werden kann, was schon geladen ist; Speichern geht erst wieder mit Netz“) oder **Online, aber GitHub nicht erreichbar**.
`navigator.onLine` ist nur ein erster Hinweis; deshalb fragt die App zusätzlich `api.github.com/rate_limit` ab (ohne Token, zählt nicht gegen das Limit, mit
Zeitlimit): beim Start, bei online/offline, beim Zurückkehren in die App und nach einem Netzfehler mit wachsendem Abstand (10 s bis 5 min), kein Dauerabfragen.
## Ohne Netz schreiben: nicht hochgeladene Änderungen (#61)

Wer **einen Abschnitt** speichert, während GitHub nicht erreichbar ist (oder solange ältere Änderungen noch warten), sichert ihn zuerst **auf diesem Gerät**
(IndexedDB, Schlüssel `outbox`; der Browser wird gebeten, den Speicher nicht von selbst zu räumen). Die Ansicht zeigt sofort die lokale Fassung.

- **Dauerhafte Leiste** oben, nicht wegklickbar, solange etwas wartet: „⬆ N Änderungen nur auf diesem Gerät – noch nicht hochgeladen“ mit **Jetzt hochladen**
  (offline: „Hochladen, sobald wieder Netz da ist“), darunter unter „Betroffen“ die Stellen (Abschnitt 2.5 …). Zähler im Tab-Titel „(N) GhostWriter“.
  Liegt etwas länger als 24 Stunden nur lokal, steht eine Erinnerung dabei.
- **Verlassen:** Tab schließen oder neu laden fragt der Browser nach; beim Abmelden fragt die App (die Änderungen bleiben auf dem Gerät).
- **Hochladen von selbst**, sobald GitHub wieder erreichbar ist, der Reihe nach (Branch und Änderungspaket wie beim normalen Speichern). Nur ein Tab lädt hoch
  (Web Locks).
- **Nichts wird überschrieben:** Hat sich dieselbe Datei auf GitHub inzwischen geändert (Blob-Kennung ≠ Stand beim Schreiben, und der Text ist nicht
  identisch), bleibt die lokale Fassung liegen, die Leiste meldet „⚠ 1 Konflikt“ und spätere Änderungen am selben Buch warten. Die **Lösung** (Fassungen
  nebeneinander, Zusammenführen, „Später“ als eigener Branch) folgt im nächsten Schritt.
- Liegt eine Änderung schon identisch auf GitHub (etwa nach einem unklaren Fehler), wird sie nicht doppelt hochgeladen.

**Grenzen:** Offline lässt sich nur das **Schreiben eines Abschnitts** sichern (Ziel, Kurzbeschreibung, Manuskript, Faktencheck). Alle anderen Aktionen (Freigeben,
Kapitel anlegen, Figuren, Warteschlange …) brauchen Netz und melden das. Ein **Neuladen ohne Netz** zeigt die gesicherten Änderungen in der Leiste, öffnet aber
noch kein Buch (die Bücher werden nicht lokal gehalten); weiterschreiben geht wieder mit Netz. Ohne IndexedDB (sehr alte Browser, privates Fenster) liegen die
Änderungen nur im Arbeitsspeicher; die Leiste warnt dann.

**Gelesen** wird aus dem Netz; was offline noch angezeigt wird, ist nur, was die Ansicht schon geladen hat.

**Veröffentlichen:** Diese Fassung ist nirgends gehostet. Eine GitHub Page für die App kommt erst nach ausdrücklicher Freigabe (öffentliche Bereitstellung).
Lokal ausprobieren: `cd apps/web && python3 -m http.server 8765`, dann `http://localhost:8765/` öffnen.

## Token

Auf GitHub unter *Settings → Developer settings → Fine-grained tokens* einen Token anlegen: **Repository access** nur das eine Repository mit den Büchern,
**Permissions** „Contents“ und „Pull requests“ jeweils *Read and write*. Der Token bleibt nur in diesem Browser (`localStorage`, Schlüssel `gw.token`),
wird nur an `api.github.com` gesendet und mit „Abmelden“ gelöscht. Er steht nie im Repository, in Commits oder in Fehlermeldungen.

## Aufbau

- `index.src.html`, `ports-web.js` (GitHub-REST, Formen wie `GW_PORTS` in [`apps/claude/ports-claude.js`](../claude/ports-claude.js)), `net-web.js` (online/offline), `outbox-web.js` (lokal sichern, hochladen), `boot-web.js`, `web.css`, `manifest.webmanifest`, `sw.src.js` (wird zu `sw.js`), `icons/`.
- Ansichten und Abläufe kommen aus [`apps/shared/`](../shared). `python3 apps/web/build.py` baut `index.html` und kopiert die Widget-Laufzeit
  (`vendor/gw-lite.js`, `vendor/icons.css`) aus `apps/claude/vendor/`; `--check` prüft den Stand. `vendor/js-yaml.min.js` (MIT) liegt fest hier.
- Tests: `tests/test_app_web.py`, `apps/web/tests/ports-web.test.cjs` (Anschluss gegen einen nachgestellten `fetch`) und `apps/web/tests/sw.test.cjs` (Service Worker) und `apps/web/tests/outbox.test.cjs` (lokal sichern, hochladen, Konflikt), alle ohne Netz.
  Ausprobieren: `index.html` im Browser öffnen oder einen kleinen Webserver im Ordner starten.

## Grenzen dieser Fassung

- Die Commit-Kennung einer Referenz holt die App mit einer zusätzlichen Anfrage und merkt sie sich wenige Sekunden (Rate-Limit von GitHub).
- Schreiben ist nur mit schnellem Vorrücken des Branchs möglich (`force: false`). Hat sich der Branch inzwischen geändert, meldet die App das und
  überschreibt nichts.
- Der Service Worker und die Installation wurden in Chromium geprüft (Hülle angelegt, Neuladen ohne Netz, Anzeige); Safari/iOS und Firefox sind nicht geprüft.
- Hinweise im Text nennen noch „Claude“ (gemeinsame Ansichten); die Texte werden mit den nächsten Schritten angepasst.
- Nicht gegen ein echtes Repository mit echtem Token geprüft: Die Durchläufe (Anmelden, Buch öffnen, Abschnitt speichern; offline schreiben, hochladen, Konflikt) liefen im Browser gegen eine nachgestellte GitHub-Schnittstelle.
- Pro Datei wird nur die Blob-Kennung verglichen; ein Zusammenführen verschiedener Absätze gibt es noch nicht.
