# GhostWriter – eigene Web-App (Stufe 1, ohne Chat)

Erster Wurf der eigenen App aus [#662](https://github.com/ploeffler/GhostWriter/issues/662): dieselben Ansichten wie in der Claude-Web-App
([`apps/claude/`](../claude/README.md)), aber ohne Claude und ohne Konnektor. Sie läuft aus einem einzigen Ordner direkt im Browser und spricht
über die GitHub-REST-Schnittstelle mit einem **Fine-grained Token** mit GitHub.

**Stand:** Entwurf, auf der GitHub Page veröffentlicht (siehe unten). Installierbar als App (PWA), die App-Hülle läuft ohne Netz, und ein Abschnitt lässt sich ohne Netz schreiben und
später hochladen. Konflikte lassen sich lösen. Es gibt noch keine Einstellungen; das folgt in den nächsten Schritten von #662. Sie ist **nicht** Teil dessen, was
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
- **Nichts wird überschrieben, Konflikte löst du selbst (#662):** Hat sich dieselbe Datei auf GitHub inzwischen geändert (Blob-Kennung ≠ Stand beim Schreiben),
  vergleicht die App **dreifach, je Absatz** (Ausgangstext ↔ dieses Gerät ↔ GitHub, `merge3.js`): Änderungen an **verschiedenen Absätzen** werden von selbst
  zusammengeführt und hochgeladen (der Commit sagt das); dieselbe Änderung auf beiden Seiten zählt einmal. Nur wo beide Seiten denselben Bereich verschieden
  geändert haben, bleibt die lokale Fassung liegen, die Leiste meldet „⚠ ungelöster Konflikt“ mit **Konflikt lösen**. Die Ansicht zeigt je Stelle beide Fassungen
  nebeneinander: **Meins behalten**, **GitHub übernehmen**, **Beides behalten** (untereinander, mit der Marke `[KONFLIKT PRÜFEN: …]`) oder **Selbst
  zusammenfügen** (Textfeld); ohne Wahl wird nichts gespeichert. **Später – nichts verlieren** legt den lokalen Stand auf einem eigenen Branch
  `ghostwriter/konflikt-<buch>-<datum>-<Nr>` ab; die Leiste zeigt dann „Konflikt später zu lösen“, der Eintrag hält nichts auf und lässt sich jederzeit
  lösen. Ist der Abschnitt auf GitHub inzwischen **abgeschlossen**, warnt die Ansicht: nach dem Zusammenführen weicht der Text von der Freigabe ab und muss neu
  abgeschlossen werden (nie stillschweigend als freigegeben).
- Liegt eine Änderung schon identisch auf GitHub (etwa nach einem unklaren Fehler), wird sie nicht doppelt hochgeladen.

**Grenzen:** Offline lässt sich nur das **Schreiben eines Abschnitts** sichern (Ziel, Kurzbeschreibung, Manuskript, Faktencheck). Alle anderen Aktionen (Freigeben,
Kapitel anlegen, Figuren, Warteschlange …) brauchen Netz und melden das. Ein **Neuladen ohne Netz** zeigt die gesicherten Änderungen in der Leiste, öffnet aber
noch kein Buch (die Bücher werden nicht lokal gehalten); weiterschreiben geht wieder mit Netz. Ohne IndexedDB (sehr alte Browser, privates Fenster) liegen die
Änderungen nur im Arbeitsspeicher; die Leiste warnt dann.

**Gelesen** wird aus dem Netz; was offline noch angezeigt wird, ist nur, was die Ansicht schon geladen hat.

**Veröffentlichen (freigegeben von Peter am 27.11.2026):** Die App liegt auf der GitHub Page unter `https://ploeffler.github.io/GhostWriter/app/` (nur die
Laufzeitdateien, `scripts/package_web_app.py`; Quellen, Tests und README gehören nicht dazu). Veröffentlichen heißt: Action **Beispielseiten veröffentlichen**
(`pages.yml`) mit `web_app: true` und `documentation: true`; mit `docs_ref: v1.5` (Tag des letzten Release) bleibt die veröffentlichte Dokumentation unverändert und nur
die App kommt dazu. Der Release-Ablauf (`release.yml`) nimmt die App bei jeder Veröffentlichung mit, damit sie nicht verschwindet. Die Seite enthält keine Buchinhalte;
jeder Benutzer meldet sich mit seinem eigenen Token an. Eine **neue Fassung** der App erreicht Geräte beim nächsten Laden (der Name des Service-Worker-Speichers
ändert sich mit jedem Bau). Forks können dieselbe App auf ihrer eigenen Page hosten (`https://<besitzer>.github.io/<repo>/app/`), die Herkunft zeigt Einstellungen › Verbindungen.
Lokal ausprobieren: `cd apps/web && python3 -m http.server 8765`, dann `http://localhost:8765/` öffnen.

## Bibliotheksansicht: Serien als Akkordeon (#662)

Im Bücherregal stehen Serien (Reihen) als **Akkordeon**: je Serie ein aufklappbarer Bereich mit Titel, Zahl der Bände, Fortschritt aller Bände („40 von 87 Abschnitten freigegeben“ mit Balken) und
**Serie öffnen ›**; darin liegen die Karten der Bände in Bandreihenfolge. Danach kommt **Einzelne Bücher**. Serien sind zuerst zugeklappt, „Einzelne Bücher“ zuerst offen; der Zustand wird je Serie im Browser
gemerkt. Ohne Serien bleibt das Regal wie bisher. Die Kopfzeile nennt die Zahl der Serien, Serien ohne Band stehen darunter. Die Daten (`library.json` → `series`, je Buch `series` und `volume`) füllt jetzt
auch die Claude-Web-App in die Widget-Felder (vorher blieben sie leer und die Serien erschienen als lose Karten); das Akkordeon selbst gibt es nur in der eigenen Web-App (`regal-web.js`).

## Ausgabe und Läufe: Actions starten, Ergebnisse holen (#662)

Der Drucker oben rechts öffnet **Ausgabe und Läufe**. Die App startet die Actions des Buch-Repositorys per `workflow_dispatch` (Vertrag: `templates/ui/BEFUELLUNG.md`,
Aktionstabelle; `ref` ist der Buch-Branch) und zeigt, was daraus wird. Die Aktionen der Ansichten (`edition.proof`, `edition.preview`, `manuscript.export`, `checkout.start`,
`edition.create.open`) öffnen dieselbe Ansicht und sind in dieser App nicht mehr ausgegraut.

- **Probedruck** (`proof.yml`): Formate (PDF, Druck-PDF, Booklet, Umschlag, DOCX, EPUB) und Kapitel; nichts wird veröffentlicht.
- **Vorabfassung** (`preview.yml`): legt einen Tag `<kurztitel>-vorab-N` und ein im Repository sichtbares Pre-Release an; deshalb erst nach einem **zweiten Klick** („Ja, jetzt starten“).
- **Manuskript ausgeben** (`manuscript.yml`): PDF oder Lesefassung (Lesefassung braucht ein Kapitel oder einen Abschnitt).
- **Auschecken zum Gegenlesen** (`checkout.yml`): Kapitel oder ganzes Buch, Gegenleser (Pflicht), Frist, Probelauf; sperrt den Bereich, deshalb ebenfalls mit zweitem Klick.
- **Letzte Läufe** (Stand läuft / fertig / fehlgeschlagen / abgebrochen, Branch, Zeit, Link). **Im Buch nur die Läufe dieses Buchs** (Buch-Branch und Arbeits-Branch `ghostwriter/<buch-branch>`), ebenso nur dessen Auflagen und Vorabfassungen. Der Knopf „Alle Läufe der Bibliothek“ zeigt die Übersicht über das ganze Repository mit dem Buchnamen je Lauf; ohne geöffnetes Buch (Bücherregal) öffnet der Drucker diese Übersicht, gestartet wird dort nichts (v1.6). Nach dem Start fragt die App alle 6 Sekunden nach, **nur solange ein Lauf läuft, die
  Ansicht offen ist und höchstens 10 Minuten**; sonst gibt es keinen Abruf im Takt. Die Ergebnisse (PDF, DOCX …) stehen auf der Laufseite unter „Artifacts“ (14 Tage).
- **Auflagen und Vorabfassungen:** die letzten Releases mit ihren Dateien als Links (öffnen sich bei GitHub; für private Repositorys musst du dort angemeldet sein).

**Seite „Daten“:** Statt des Links zur Action zeigt sie bei **Erledigte Branches** die Knöpfe **Nur anzeigen** (löscht nichts) und **Aufräumen** (startet die Action „Branches aufräumen“, `cleanup.yml`,
auf dem Standard-Branch). Die Knöpfe erscheinen nur, wenn der Token es darf: Schreibrecht am Repository, Recht „Actions“ und die Action ist im Buch vorhanden; sonst steht der Link mit dem Grund da.
„Aufräumen“ fragt mit einem zweiten Klick nach; gelöscht werden nur erledigte Arbeits-Branches (Änderungspaket übernommen oder vollständig im Buch enthalten), Branches mit offenem Änderungspaket oder eigenen
Commits bleiben (Prüfung in der Action). Nach dem Start steht der Link zum Lauf da, die Seite lädt die Zahl der Branches und **Letzte Läufe** nach (jetzt mit echten Läufen statt „nicht abrufbar“).

Eingaben werden vor dem Start geprüft (Kapitel nur als Zahlen, Frist als `JJJJ-MM-TT`, Pflichtfelder); nie startet etwas ohne Klick. Fehlt die Action im Buch, sagt die App es und verweist auf
„GhostWriter aktualisieren“; fehlt dem Token das Recht „Actions“, sagt sie das ebenfalls. **Nicht in dieser Fassung:** eine neue **Auflage** anlegen (Auflagen-Änderungspaket mit Freigaben,
`edition.create`) und Recherche/Analysen/Warteschlange starten (brauchen KI-Schlüssel des Forks und Kostenabfragen); das geht weiter im Chat mit GhostWriter.

## Sprachnotizen (#644, #662)

Das Mikrofon oben rechts öffnet **Sprachnotizen**. Die App nimmt im Browser auf (MediaRecorder, Opus, höchstens 30 Minuten je Aufnahme) und speichert die Aufnahme **nur auf diesem Gerät**
(IndexedDB `gw-web-voice`, der Browser wird gebeten, den Speicher nicht zu räumen). Beschluss Peter vom 25.11.2026, daran hält sich die App:

- **Audio kommt nie ins Repository und nie in einen Actions-Lauf; Spracherkennung läuft nie als Action.** Es gibt im Code keinen Netzzugriff für Aufnahmen (ein Test prüft das).
- Die App-Aufnahme ist die **einzige Kopie**. Sie bleibt, bis sie im Chat abgeschrieben ist und du sie herunterlädst oder verwirfst; verwerfen fragt immer nach, bei einer noch nicht abgeschriebenen Aufnahme mit deutlichem Hinweis.
- **Ablauf:** aufnehmen → **Herunterladen** → die Datei im Chat mit GhostWriter hochladen („Sprachnotiz“, Abschrift und Zuordnung nach #644) → hier **Im Chat abgeschrieben** wählen.
  Die Leiste oben zeigt solange „🎙 N Sprachnotizen warten auf Abschrift – nur auf diesem Gerät“.
- **Kontext:** Gemerkt wird, wo aufgenommen wurde (ganzes Buch, Kapitel N, Abschnitt N.M); der Name der heruntergeladenen Datei enthält Datum, Uhrzeit und diese Stelle
  (`sprachnotiz-2026-11-27-0940-abschnitt-2-5.webm`) als Vorschlag für die spätere Zuordnung.
- **Diktieren** in Textfelder geht ohne eigenen Code mit dem Mikrofon der Handy-Tastatur (läuft auf dem Gerät).
- Mikrofon wird erst bei „Aufnahme starten“ angefragt und danach freigegeben; fehlt das Recht oder das Mikrofon, sagt die App es. Ist der Speicher knapp, steht eine Warnung da; schlägt das Speichern fehl,
  bietet die App die Aufnahme sofort zum Herunterladen an.

**Nicht in dieser Fassung:** Erkennung auf dem Gerät (der Browser müsste das ohne Netz können; nicht überall verfügbar), das Hochladen eines Stapels vom Diktiergerät (das geschieht im Chat),
die Abschrift selbst (Chat, nach #644) und eine Wiederaufnahme einer unterbrochenen Aufnahme nach einem Absturz der Seite (eine laufende Aufnahme liegt bis zum Beenden im Arbeitsspeicher; beim Schließen der Seite fragt der Browser nach).

## Einstellungen › Verbindungen, Gerät, Fehler melden (#662)

Das Zahnrad oben rechts öffnet **Einstellungen › Verbindungen**. Eine Gruppe erscheint erst, wenn ihre Funktion umgesetzt ist (kein toter Knopf); KI-Anbieter,
Sprachnotizen und E-Mail-Feedback kommen mit ihren Versionen dazu. Schlüssel und Token stehen nur mit Status da, nie mit Wert, und alles lässt sich testen
oder trennen.

- **GitHub:** angemeldet als, Token vorhanden (mit Ablaufdatum, wenn GitHub es mitschickt), Repository, Rechte am Repository (Lesen/Schreiben/Verwalten), übrige Anfragen,
  **Verbindung testen**, **Abmelden**.
- **Herkunft dieser App:** die Adresse (`location.origin`) zum Kopieren, für die CORS-Freigabe lokaler Server (genutzt ab v2.0).
- **Speicher auf diesem Gerät:** belegt von verfügbar, dauerhafter Speicher angefordert (mit Knopf), nicht hochgeladene Änderungen, Dateien der App-Hülle.
- **Gerät und Fähigkeiten:** WebGPU (nur Vorhandensein), Arbeitsspeicher und Kerne (grob, nicht jeder Browser meldet sie), Speicherplatz, System und Browser,
  App installiert, eingebaute Browser-KI, Mikrofon, Aufnahme, Spracherkennung, online/GitHub erreichbar. Die **Fähigkeiten-Matrix** [`faehigkeiten.json`](faehigkeiten.json)
  (wird mit der App ausgeliefert, funktioniert offline) legt je Funktion die Voraussetzungen, einen Ersatzweg und Begründungstexte (DE/EN) fest; die Ansicht zeigt
  „geht“, „unklar“ (Messwert fehlt) oder „geht nicht“ mit Grund. Gleiche Struktur wie die geplante Modellliste (#525); der **Probelauf** für Modelle folgt mit #525. Die
  Messwerte bleiben auf dem Gerät.
- **Fehler melden ohne Chat:** Fehler, die die App zeigt oder die unbehandelt auftreten, merkt sie sich bereinigt (letzte 30, nach Fingerabdruck zusammengefasst, im
  Browser). Unter jeder Fehlermeldung und in einem Hinweis bei unbehandelten Fehlern steht **Fehler melden**; das öffnet ein **vorausgefülltes neues Issue** im
  Hauptrepository (`upstream` der Bibliothek, sonst `ploeffler/GhostWriter`): Fehlerklasse, Programmversion der Web-App, Schritt, Aufruf (ohne Repository und Pfade),
  bereinigte Meldung, grober Browser, Fingerabdruck, Häufigkeit; **keine** Repository-, Buch-, Branch- oder Textnamen, keine Pfade, keine Secrets (Format nach #660).
  Du siehst den Text bei GitHub und schickst ihn selbst ab; die App braucht dafür keinen zusätzlichen Schlüssel. Grobe Gerätewerte („WebGPU ja, 8 GB“) gehen nur mit
  ausdrücklichem Häkchen mit. Die Arbeit geht bei einem Fehler nie verloren (sie liegt als „nur lokal“ in der Outbox).

## Token

Auf GitHub unter *Settings → Developer settings → Fine-grained tokens* einen Token anlegen: **Repository access** nur das eine Repository mit den Büchern,
**Permissions** „Contents“ und „Pull requests“ jeweils *Read and write*; zum Starten von Läufen zusätzlich „Actions“ *Read and write* (ohne dieses Recht gehen alle anderen Funktionen; Läufe lassen sich dann nur ansehen). Der Token bleibt nur in diesem Browser (`localStorage`, Schlüssel `gw.token`),
wird nur an `api.github.com` gesendet und mit „Abmelden“ gelöscht. Er steht nie im Repository, in Commits oder in Fehlermeldungen.

## Aufbau

- `index.src.html`, `ports-web.js` (GitHub-REST, Formen wie `GW_PORTS` in [`apps/claude/ports-claude.js`](../claude/ports-claude.js)), `net-web.js` (online/offline), `merge3.js` (Dreiwege-Vergleich), `outbox-web.js` (lokal sichern, hochladen), `konflikt-web.js` (Konflikt lösen), `fehler-web.js` (Fehler melden), `einstellungen-web.js` (Einstellungen, Gerät), `runs-web.js` (Actions starten), `voice-web.js` (Sprachnotizen), `regal-web.js` (Serien als Akkordeon), `faehigkeiten.json`, `boot-web.js`, `web.css`, `manifest.webmanifest`, `sw.src.js` (wird zu `sw.js`), `icons/`.
- Ansichten und Abläufe kommen aus [`apps/shared/`](../shared). `python3 apps/web/build.py` baut `index.html` und kopiert die Widget-Laufzeit
  (`vendor/gw-lite.js`, `vendor/icons.css`) aus `apps/claude/vendor/`; `--check` prüft den Stand. `vendor/js-yaml.min.js` (MIT) liegt fest hier.
- Tests: `tests/test_app_web.py`, `apps/web/tests/ports-web.test.cjs` (Anschluss gegen einen nachgestellten `fetch`) und `apps/web/tests/sw.test.cjs` (Service Worker) `apps/web/tests/outbox.test.cjs` (lokal sichern, hochladen, Konflikt) `apps/web/tests/merge3.test.cjs` (Zusammenführen) und `apps/web/tests/fehler.test.cjs` (Bereinigen, Meldungstext, Matrix) und `apps/web/tests/runs.test.cjs` (Starten, Eingaben, Stand) und `apps/web/tests/voice.test.cjs` (Aufnehmen, Verwalten, kein Netz), alle ohne Netz.
  Ausprobieren: `index.html` im Browser öffnen oder einen kleinen Webserver im Ordner starten.

## Grenzen dieser Fassung

- Die Commit-Kennung einer Referenz holt die App mit einer zusätzlichen Anfrage und merkt sie sich wenige Sekunden (Rate-Limit von GitHub).
- Schreiben ist nur mit schnellem Vorrücken des Branchs möglich (`force: false`). Hat sich der Branch inzwischen geändert, meldet die App das und
  überschreibt nichts.
- Der Service Worker und die Installation wurden in Chromium geprüft (Hülle angelegt, Neuladen ohne Netz, Anzeige); Safari/iOS und Firefox sind nicht geprüft.
- Hinweise im Text nennen noch „Claude“ (gemeinsame Ansichten); die Texte werden mit den nächsten Schritten angepasst.
- Nicht gegen ein echtes Repository mit echtem Token geprüft: Die Durchläufe (Anmelden, Buch öffnen, Abschnitt speichern; offline schreiben, hochladen, Konflikt) liefen im Browser gegen eine nachgestellte GitHub-Schnittstelle.
- Läufe starten und ansehen wurde nur gegen die nachgestellte Schnittstelle geprüft (kein echter Lauf, kein echter Token mit Recht „Actions“). Die Namen der Eingaben stammen aus den Workflow-Dateien; ändern sie sich, muss `runs-web.js` nachgezogen werden.
- Das bereinigte Fehlerprotokoll wird noch **nicht** zusätzlich im Arbeits-Branch abgelegt (`.ghostwriter/app-fehler.yml`) und nicht vom täglichen Update-Lauf ausgewertet (#660, v2.0); gemeldet wird nur über das vorausgefüllte Issue. Die Bereinigung ist eine Vorsichtsmaßnahme (Namen, Pfade, Titel in Anführungszeichen, Token, Adressen, E-Mail), keine Garantie: bitte den Text vor dem Absenden ansehen.
- Zusammengeführt wird Text je Absatz (durch eine Leerzeile getrennt). **Änderungen in benachbarten Absätzen zählen als eine Stelle** und werden als Konflikt gezeigt (wie benachbarte Zeilen in git). Für Dateien ohne gespeicherten Ausgangstext (ältere Einträge) und ohne Absätze gilt die Wahl für die ganze Datei. Strukturdateien (`ghostwriter.yml`) werden nicht feldweise zusammengeführt.
- Die Konfliktlösung wurde nur im Browser gegen die nachgestellte Schnittstelle geprüft, nicht mit mehreren echten Geräten.

## Modell im Browser (Gerüst, #525)

Der Knopf mit dem Roboter oben öffnet **Modell im Browser**. Ein Sprachmodell läuft dann auf dem Gerät (WebGPU, Transformers.js 4.3.2); der Text verlässt das Gerät nie.

- **Modellliste:** [`modelle.json`](modelle.json) (Format wie `faehigkeiten.json`): Gemma 4 E2B (Standard, 2,9 GB), Gemma 4 E4B (stark, 4,6 GB), Qwen3.5 2B (Notbehelf, 1,5 GB, schwaches Deutsch). Alle Apache 2.0, nicht gesperrt. Die App schlägt je nach Gerät eines vor; was nicht passt, bleibt ausgegraut mit Grund (gleiche Auswertung wie die Matrix in den Einstellungen).
- **Nichts ohne Klick:** Die Laufzeit (von `cdn.jsdelivr.net`) und die Gewichte (von `huggingface.co`) werden erst nach „Herunterladen“ geladen, bei mehr als 1,5 GB nach einer Rückfrage. Sie liegen danach im Cache dieses Browsers und lassen sich dort löschen. Fortschritt, Abbrechen, Probelauf mit Zeitmessung sind eingebaut.
- **Chat:** Lektorat, Zusammenfassen, Übersetzen, freie Frage. Das Modell schlägt nur vor; ein Vorschlag wird erst nach „Vorschlag kopieren“ übernommen. Es wird nichts automatisch gespeichert und kein Text an Actions oder Dritte geschickt.
- **Werkzeugaufrufe** (Recherche) sind nur ergänzend vorbereitet: kleiner Leser für das Gemma- und das Qwen-Format (`mdlParseTools`), noch ohne Suchanbindung.
- **Noch offen:** Abnahme auf einem Gerät mit WebGPU und shader-f16 (die Testumgebung hat keines; getestet sind Liste, Passung, Auswahl, Leser und die Ansicht), Übernahme eines Vorschlags direkt in den Abschnitt, Abschrift der Sprachnotizen (Gemma 4 mit Audio), Cache über den Service Worker für Offline-Start der Laufzeit.

## Versionen im Kopf (#735)

Im Kopf steht „App x.y.z“ und, sobald ein Repository offen ist, „Repository x.y.z“ (GhostWriter-Version aus `ghostwriter-manifest.yml`, nur gelesen). Weichen die beiden Stände ab (Haupt- oder Nebenversion), wird die Anzeige gelb und der Tooltip nennt den Grund; ist das Manifest nicht lesbar (offline), steht nur die App-Version da.

