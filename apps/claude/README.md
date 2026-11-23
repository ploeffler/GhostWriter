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
- Hinweisdurchsicht (#367): Karte „Hinweisdurchsicht“ in der Projektübersicht, Ansicht mit einer Karte je Eintrag
  aus `editorial/durchsicht-*.yml`. „Übernehmen“, „Nicht ändern“ und eigene Fassung speichern jede Antwort sofort
  als kleinen Nachtrag (nur die Zeilen des Eintrags ändern sich, die Datei wird danach gegengeprüft; schnelle
  Klicks laufen nacheinander). „Umsetzen prüfen“ zeigt ✅/⚠️/⛔, ändert aber nichts; bei umsetzbaren Einträgen
  bietet es den Knopf „… ins Manuskript umsetzen“ an. Das Umsetzen (wie `hinweise.py apply`) ersetzt in den Manuskripten
  den alten Wortlaut durch den entschiedenen, markiert die Einträge als `umgesetzt` und schreibt den Befundstatus zurück
  (umgesetzt → `erledigt`, nein → `entschieden`), alles in einem Commit auf den Arbeits-Branch. Umgesetzt werden nur
  ✅-Einträge; abgeschlossene Kapitel und Abschnitte werden nie angefasst. Ändert eine frühere Umsetzung den Text eines
  späteren Eintrags in demselben Abschnitt, wird dieser übersprungen und gemeldet (das Skript bricht dort ab). Danach zeigt
  die App die betroffenen Stellen im Zusammenhang. **Noch nicht in der App:** Nachprüfung (Schlusskorrektur,
  Qualitätsprüfung) und erneutes Abschließen der Kapitel; das geht weiter im Chat.
- Claude-Leiste in Projektübersicht, Kapitel und Abschnitt. Claude kann Knöpfe anbieten, die nur eine Ansicht
  oder ein Formular öffnen (Liste `SAFE_ACTIONS` in `index.html`). Speichern und Abschließen bleiben eigene Schritte.
  Will der Benutzer im Chat etwas ändern, sagt Claude nicht nur „kann ich nicht“, sondern bietet den Knopf zum
  passenden Formular an, in dem er speichert.

Nicht in der App: zeitgesteuerte Läufe, Auflagen, Bilder, Figuren, Löschen, Lektorat. Ebenso Läufe der Actions,
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

## Nachziehen bei Programmänderungen

Ändern sich Abläufe, Datenmodell, Freigaberegeln, Aktionen (`templates/ui/BEFUELLUNG.md`) oder Widgets,
wird die App im selben Änderungspaket mitgezogen:

1. `index.html` anpassen. Neue Ansicht: Vorlage in `build_vendor.py` → `TEMPLATES` eintragen.
2. Neue Widget-Version: `python3 apps/claude/build_vendor.py --gw ../ghostwriter-ui/dist/gw.js --tabler <@tabler/icons>/icons/outline`.
3. Test:
   ```
   npm install --prefix /tmp/gw-claude-test jsdom@24 js-yaml@4
   NODE_PATH=/tmp/gw-claude-test/node_modules GW_REPO=chillyconcane/YAWA node apps/claude/tests/app.test.cjs
   ```
   Der Test liest mit `gh api` und schreibt nichts. Echte Schreibtests (Speichern, Freigabe, Übernehmen)
   macht der Benutzer in der App.
4. Veröffentlichen: neue Connector-Werkzeuge zuerst in den Fähigkeiten des Artefakts eintragen, dann
   `index.html` und `vendor/` veröffentlichen. Die App ist öffentlich geteilt, eine neue Fassung ist also sofort
   für alle sichtbar. Veröffentlichen ist ein eigener Schritt und braucht eine Freigabe.

Benutzte Connector-Werkzeuge: `get_file_contents`, `list_pull_requests`, `pull_request_read`, `create_branch`,
`create_or_update_file`, `create_pull_request`, `update_pull_request_branch`, `merge_pull_request`, `push_files`,
`get_me`, `search_repositories`, `list_branches`.
