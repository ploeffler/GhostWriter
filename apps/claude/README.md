# GhostWriter für Claude (Web-App, Versuch)

Eine Web-App, die als Artefakt in Claude läuft: https://claude.ai/artifact/PQ3zcq4ofwwRcP7dMHMG9B
Sie zeigt dieselben Ansichten wie GhostWriter im Chat, also die Widgets aus
[ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui). Klicks führt sie direkt aus, ohne Chat.

**Stand:** Versuch außerhalb des Lieferumfangs von v1.0. Eine eigene Web-App ist nach
[D06](../../docs/ENTSCHEIDUNGEN-v1.0.md#d06--eigene-web-app-ohne-integrierten-modellaufruf) auf nach v1.0 verschoben.
Diese App braucht weder eine eigene API noch einen Server. Sie arbeitet mit der GitHub-Verbindung des
jeweiligen Benutzers in Claude und ruft Claude über dessen eigenes Konto auf.

Die Dateien liegen außerhalb der Ordner, die das Update in die Bibliotheken kopiert. Ein Buch-Repository
bzw. ein Fork bekommt davon nichts. Wer den Link öffnet, nutzt immer die zuletzt veröffentlichte Fassung.

## Was die App kann

- Bücherregal, Seite „Daten“, Projektübersicht mit Prüfergebnissen, Kapitelansicht, Abschnittsformular.
- Speichern eines Abschnitts. Alle Dateien einer Aktion kommen in einem Commit auf den Arbeits-Branch
  `ghostwriter/<buch-branch>`, und das Änderungspaket (Pull Request) wird angelegt bzw. weiterverwendet.
  Ins Buch kommt es erst über „Änderungen übernehmen“ mit Bestätigung.
- Freigaben: Schreiben erlauben/sperren, Abschnitt abschließen/wieder öffnen, Kapitel abschließen/wieder öffnen.
  Vorher zeigt die App die Prüfliste, und jede Freigabe wird in `approvals.yml` festgehalten
  (bei Abschnitten mit `content_sha256`). Die Regeln stehen in `START.md`, „Freigaben“.
- Kapitel und Abschnitte anlegen, Kapitel bearbeiten, Reihenfolge ändern (mit Neunummerierung wie
  `scripts/sections.py renumber`), Projektdaten bearbeiten.
- Recherche und Ghostwriting „Sofort“ über Claude. Das Ergebnis wird zuerst gezeigt und erst auf Knopfdruck
  gespeichert, als Laufdatei und gegebenenfalls als Manuskript. Die Recherche läuft ohne Internet; die Laufdatei
  sagt das ausdrücklich. Pro Lauf genau ein Abschnitt.
- Recherche mit Internet (#462): Ist für die Recherche ein Dienst mit API-Schlüssel eingestellt (Anthropic, OpenAI,
  Google; sonst die Einstellungen des Standard-Branchs), zeigt die Abschnittssteuerung bei „Recherche“ statt
  „Zeitgesteuert“ den aktiven Knopf „Mit Internet · GitHub-Action (Dienst)“; „Sofort · hier in der App“ ist dann
  ausgegraut (Claude hat in der App keine Websuche). Nach einer Rückfrage legt die App nur einen Auftrag
  `<kapitel>/research/<abschnitt>/request-NNN.yml` auf den Arbeits-Branch. Der Commit startet die Action
  „Recherche“, die mit dem Secret des Dienstes sucht und Laufdatei und Kosteneintrag ins Änderungspaket legt.
  Der Auftrag hat das Format der Hintergrund-Warteschlange (`type: research`, `requested_by: web-app`, #483).
  „Nachsehen“ zeigt alle Aufträge des Abschnitts mit Zustand (wartet bzw. läuft, wartet auf Bestätigung,
  fehlgeschlagen) und fertige Ergebnisse (Quellen, Suchanfragen, Kosten). „Trotzdem starten“ bestätigt einen
  Auftrag, der wegen knappem KI-Budget wartet (`confirm_low_budget: true`), statt einen zweiten anzulegen. Ohne solchen Dienst bleibt
  „Sofort“ die Recherche ohne Internet über Claude.
  Der Push startet die Action in der Fassung des Arbeits-Branchs. Weicht `research.yml` dort vom Buch-Branch ab
  (Änderungspaket älter als das letzte Update), bringt die App das Änderungspaket vorher auf den Buchstand
  (`update_pull_request_branch`).
- Figuren (#53): Liste (Knopf „Figuren (n)“ in der Projektübersicht), Formular mit Beschreibung, Notizen und
  Beziehungen, Figur anlegen und speichern. Die Dateien (`characters/<id>.md`, Block `characters` in
  `ghostwriter.yml`) entstehen wie bei `scripts/characters.py`; ein Commit je Aktion auf den Arbeits-Branch.
  „Figuren aus dem Text vorschlagen“ (Buch, Kapitel oder Abschnitt): Claude liest die Texte in Teilen zu je
  etwa 40 000 Zeichen und schlägt nur aus dem Text vor; die Fundstellen prüft die App ohne KI gegen den Text und
  verwirft nicht belegte. Übernommen wird nach Auswahl: neue Figuren, bei bekannten nur leere Felder,
  Beziehungen und die Zuordnung zu Abschnitten in einem Commit.
  Profilbilder (#417): Liste und Formular zeigen das Bild aus `portrait` im Figurenkopf, sonst das erste
  freigegebene Referenzbild mit Rolle `visual_reference` und Link `person:<id>`. Die App lädt das Bild über den
  Konnektor, schneidet es quadratisch zu und verkleinert es (80 bzw. 192 Pixel); das Original bleibt unberührt
  und wird nie ins Buch geschrieben. Ohne freigegebenes Bild, bei zu großer Datei (über 12 MB) oder wenn der
  Konnektor das Bild nicht liefert, bleibt das Feld leer. Ein anderes Bild wählt man wie im Chat mit
  `portrait: ref-img-…` im Figurenkopf.
  Figuren der Serie (#116): Gehört das Buch zu einer Serie (`series/<ser-id>/series.yml` auf dem Standard-Branch), zeigt
  die Liste auch deren Figuren mit Herkunft („aus der Serie“, „Kopie der Serie“, „nur in diesem Buch“). Eine Figur der
  Serie speichern (`character.series.update`, gilt für alle Bände ohne Kopie, **direkt auf dem Standard-Branch**, kein
  Änderungspaket), „Kopie nur für dieses Buch“, „An Serie angleichen“ und „In die Serie übernehmen“ gehen wie im Chat; beim
  Vorschlag aus dem Text bietet die App „als Figur der Serie anlegen“. Den Namen des Standard-Branchs holt die App über die
  Repository-Suche, sonst über den Branch mit dem Stand von `library.json`, zuletzt `main`. **Grenze:** Beim Angleichen und beim
  Übernehmen in die Serie bleibt die Datei `characters/<id>.md` im Buch liegen, weil die App keine Dateien löschen kann (sie wird
  nicht mehr benutzt). **Noch nicht in der App:** Teile von Vor- und Nachspann als Bereich, Vorschläge auf Ebene der Serie.
- Vor- und Nachspann (#510): Die Projektübersicht zeigt die Teile von Vor- und Nachspann mit Status, offenen Markern und der Marke „veraltet“ (Tooltip mit Datum und Grund). Öffnen und Bearbeiten der Teile geht weiter im Chat.
- Rückgaben vom Gegenlesen (#573, #209): Karte „Rückgaben vom Gegenlesen“ in der Projektübersicht, Ansicht (Vorlage `rueckgabe`) mit Kennung, Art, Programm, Zahlen, Hinweisen („Vergleich über den Text“, nicht übernommen), Seiten, offenen Fragen und den Aufbau-Änderungen. **Nur lesend:** Das Einchecken (Upload von DOCX, PDF oder Fotos, QR-Zuordnung, Vergleich) und das Übernehmen der Aufbau-Änderungen laufen im Chat mit GhostWriter (`scripts/checkin.py`), weil die App keine Dateien binär hochladen und keine Programmskripte ausführen kann; „Checkout beenden“ und „Übernehmen“ zeigen den Text für den Chat.
- Abschnitt neu abschließen (#563): Weicht der Text eines abgeschlossenen Abschnitts vom Fingerabdruck der letzten Freigabe
  ab, zeigt die Bestätigung „Geänderten Text neu abschließen“ (Wortzahl damals und jetzt) statt des Hindernisses
  „bereits abgeschlossen“. Die Freigabe schreibt `revoked` und `granted` mit neuem `content_sha256` in einem Commit;
  eine Veraltet-Marke des Abschnitts entfällt dabei.
- Veraltet-Marke (#510, #592; Widgets ab UI 0.69.0): Die Marke „veraltet“ mit Grund steht in Projektübersicht, Kapitelansicht
  und Abschnittsformular (`stale:` im Kopf der Abschnittsdatei wie `scripts/stale.py`). „Als veraltet markieren“ (mit Grund)
  und „Markierung entfernen“ ändern nur den Kopf, ein Commit; Status, Freigabe und Text bleiben. `stale.list` zeigt die Liste.
  **Noch nicht in der App:** Marken bei Teilen von Vor- und Nachspann.
- Erneut versuchen (#554, #596): Fehlgeschlagene Aufträge der Warteschlange zeigen die Meldung des Skripts (bei „Modell
  nicht mehr verfügbar“ mit dem Hinweis auf das Formular „KI-Dienste“). „Erneut versuchen“ entfernt `error` und `failed_at`;
  derselbe Auftrag ist wieder offen, kein zweiter Auftrag, ein Commit.
- Hinweisdurchsicht (#367): Karte „Hinweisdurchsicht“ in der Projektübersicht, Ansicht mit einer Karte je Eintrag
  aus `editorial/durchsicht-*.yml`. „Übernehmen“, „Nicht ändern“ und eigene Fassung speichern jede Antwort sofort
  als kleinen Nachtrag (nur die Zeilen des Eintrags ändern sich, die Datei wird danach gegengeprüft; schnelle
  Klicks laufen nacheinander). „Umsetzen prüfen“ zeigt ✅/⚠️/⛔, ändert aber nichts; bei umsetzbaren Einträgen
  bietet es den Knopf „… ins Manuskript umsetzen“ an. Das Umsetzen (wie `hinweise.py apply`) ersetzt in den Manuskripten
  den alten Wortlaut durch den entschiedenen, markiert die Einträge als `umgesetzt` und schreibt den Befundstatus zurück
  (umgesetzt → `erledigt`, nein → `entschieden`), alles in einem Commit auf den Arbeits-Branch. Umgesetzt werden nur
  ✅-Einträge; abgeschlossene Kapitel und Abschnitte werden nie angefasst. Auslassungspunkte am Rand des alten Wortlauts werden wie in `hinweise.py` weggelassen, ein Wortlaut in einem anderen Abschnitt wird als ⚠️ mit der Stelle gemeldet (#522). Ändert eine frühere Umsetzung den Text eines
  späteren Eintrags in demselben Abschnitt, wird dieser übersprungen und gemeldet (das Skript bricht dort ab). Danach zeigt
  die App die betroffenen Stellen im Zusammenhang. Ab 12 offenen Einträgen zeigt die App wie `hinweise.py` nur die
  aktuelle Stufe (#570): Blockierendes einzeln, ein Thema je Runde (`themen`), Gruppen gleicher Muster (eine Zeile
  `gruppe:<schlüssel>`, „ja“ nimmt alle Einträge mit eindeutigem Vorschlag an, „nein“ lässt alle; ein Commit), Runden zu
  fünf, Geringes zugeklappt („Geringe lassen“ bzw. „Geringes einzeln ansehen“). Nach jeder Antwort erscheint die nächste
  Stufe; „Alle Einträge zeigen“ schaltet die Stufen ab. Vorschläge des Assistenten und Streichungen (#609, #615) werden
  angezeigt. Seit UI 0.70.0 hat jede Variante einer Autorenentscheidung einen eigenen Knopf (wie `hinweise.py decide --variant`: „geändert“ mit dem Wortlaut der Variante, `variante` im Eintrag); „Frage stellen“ geht an Claude mit dem Eintrag als Zusammenhang und entscheidet und speichert nichts. **Noch nicht in der App:** Nachprüfung (Schlusskorrektur, Qualitätsprüfung) und erneutes Abschließen der Kapitel;
  das geht weiter im Chat.
- Hintergrund-Warteschlange (#478): Karte „Hintergrund-Warteschlange“ in der Projektübersicht, Ansicht (Vorlage `warteschlange`)
  mit wartenden, auf Bestätigung wartenden (Budget), von einem anderen Auftrag abhängigen, fehlgeschlagenen und fertigen,
  noch nicht übernommenen Aufträgen. Die Reihenfolge ist dieselbe wie in `scripts/jobs.py` (Vorrang, `after`, Buchreihenfolge,
  Auftragszeit; Ringe werden ignoriert). „Vorziehen“ setzt `priority: true`; „Abbrechen“ (mit Rückfrage) markiert den Auftrag
  als abgebrochen (`error`, `failed_at`), denn die App kann keine Dateien löschen: er steht dann als fehlgeschlagen da und läuft
  nicht mehr. Beides geht nur bei wartenden Aufträgen, jeweils ein Commit auf den Arbeits-Branch; ein schon laufender Auftrag
  lässt sich so nicht stoppen. Gelesen werden die Aufträge des Lesestands (Arbeits-Branch, solange ein Änderungspaket offen ist).
- Skills des Buchs (#524, #535): Beim Öffnen eines Buchs liest die App die `SKILL.md` unter `.claude/skills` (Lesestand, sonst
  Standard-Branch) und den persönlichen Skill aus `assistant.yml`. Die Claude-Leiste nennt die Skills und warnt, wenn die
  allgemeinen Skills von `ghostwriter-skills.yml` (Prüfsummen) abweichen oder der persönliche Skill fehlt. Claude bekommt sie
  als verbindliche Anleitung mit: der persönliche Skill ganz, von den Regeln aus `START.md` nur die, die in der App gelten (der Skill `ghostwriter` ist seit #569 nicht mehr im Buch; die App hat diese Regeln fest eingebaut, wird er in einem älteren Buch noch gefunden, gilt dessen Fassung)
  (Skillauswahl, Auswahlfragen, verständliche Ausgaben, Qualitätssicherung), `ghostwriter-lektorat` bei Prüfaufträgen und
  `ghostwriter-buchgedaechtnis` bei Kontinuitätsfragen (Auswahl nach der Anfrage). Ausgelassen sind die Teile für Chats mit
  Shell (Repository einbinden, Git-Benutzer, Darstellungsmodus, Kurzbefehle, erste Ansicht, Fehlermeldungen ans Hauptrepository);
  das macht die App selbst. Claude nennt zu Beginn einer Aufgabe, welchen Skill er verwendet. Die Anleitung bleibt unter etwa
  20 000 Zeichen.
- Claude-Leiste in Projektübersicht, Kapitel und Abschnitt. Claude kann Knöpfe anbieten, die nur eine Ansicht
  oder ein Formular öffnen (Liste `SAFE_ACTIONS` in `index.html`). Speichern und Abschließen bleiben eigene Schritte.
  Will der Benutzer im Chat etwas ändern, sagt Claude nicht nur „kann ich nicht“, sondern bietet den Knopf zum
  passenden Formular an, in dem er speichert.

Nicht in der App: Einchecken von Rückgaben (Upload), zeitgesteuerte Läufe, Auflagen, Bilder, Figuren, Löschen, Lektorat. Ebenso Läufe der Actions,
Probedrucke und Nutzungsgrenzen, weil der GitHub-Konnektor sie nicht liefert. Klicks auf Fehlendes zeigen
einen Hinweis und den Text, mit dem man es im Chat auslöst.

## Einrichtung pro Benutzer

1. In claude.ai unter Einstellungen → Konnektoren den Konnektor **github** verbinden.
2. Für private Repositorys auf GitHub die App
   [Claude Github MCP Connector](https://github.com/apps/claude-github-mcp-connector) auf dem Konto installieren,
   dem das Repository gehört. Nur „autorisiert“ reicht nicht, dann meldet GitHub „nicht gefunden“.
3. Beim ersten Öffnen und nach neuen Werkzeugen fragt Claude, ob die App GitHub benutzen darf.

## Dateien

| Datei | Inhalt |
|---|---|
| `index.html` | die App (Daten wie `scripts/render_view.py`, Schreiblogik, Claude-Leiste) |
| `vendor/gw-lite.js` | Auszug aus `ghostwriter-ui/dist/gw.js`: nur die benutzten Vorlagen, nur Deutsch |
| `vendor/icons.css` | benutzte Symbole aus `@tabler/icons` als CSS-Masken |
| `build_vendor.py` | baut die beiden Dateien in `vendor/`; nie von Hand ändern |
| `tests/app.test.cjs` | Durchlauf in jsdom mit echten Daten, Schreibaufrufe abgefangen |
| `tests/app-v12.test.cjs` | Neu abschließen, Erneut versuchen, Veraltet-Marken und Stufen der Durchsicht mit nachgebildetem Repository (`tests/fixtures/adhs`), ohne Netz |

## Nachziehen bei Programmänderungen

Ändern sich Abläufe, Datenmodell, Freigaberegeln, Aktionen (`templates/ui/BEFUELLUNG.md`) oder Widgets,
wird die App im selben Änderungspaket mitgezogen:

1. `index.html` anpassen. Neue Ansicht: Vorlage in `build_vendor.py` → `TEMPLATES` eintragen.
2. Neue Widget-Version: `python3 apps/claude/build_vendor.py --gw ../ghostwriter-ui/dist/gw.js --tabler <@tabler/icons>/icons/outline`.
   Neue Felder in `templates/*.html` und `render_view.py` (`book_row()` usw.) in den Datenfunktionen von `index.html` ergänzen; fehlt eines, entfernt `blankRaw()` den rohen Platzhalter (#685), die Anzeige bleibt aber leer. Das Upgrade der Widget-Laufzeit auf UI 0.72 (`_PACK`) ist für 1.6 vorgemerkt: Der Stand 0.72 lässt im Test „Figur speichern“ und „Übernehmen“ fehlschlagen.
3. Test:
   ```
   npm install --prefix /tmp/gw-claude-test jsdom@24 js-yaml@4
   NODE_PATH=/tmp/gw-claude-test/node_modules GW_REPO=chillyconcane/YAWA node apps/claude/tests/app.test.cjs
   ```
   Der Test liest mit `gh api` und schreibt nichts. Ohne Zugriff auf eine Bibliothek läuft
   `NODE_PATH=/tmp/gw-claude-test/node_modules node apps/claude/tests/app-v12.test.cjs` mit nachgebildeten Daten. Echte Schreibtests (Speichern, Freigabe, Übernehmen)
   macht der Benutzer in der App.
4. Veröffentlichen: neue Connector-Werkzeuge zuerst in den Fähigkeiten des Artefakts eintragen, dann
   `index.html` und `vendor/` veröffentlichen. Die App ist öffentlich geteilt, eine neue Fassung ist also sofort
   für alle sichtbar. Veröffentlichen ist ein eigener Schritt und braucht eine Freigabe.

Benutzte Connector-Werkzeuge: `get_file_contents`, `list_pull_requests`, `pull_request_read`, `create_branch`,
`create_or_update_file`, `create_pull_request`, `update_pull_request_branch`, `merge_pull_request`, `push_files`,
`get_me`, `search_repositories`, `list_branches`.
