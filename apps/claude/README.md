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
  „Nachsehen“ zeigt Stand, Fehler oder Ergebnis (Quellen, Suchanfragen, Kosten). Ohne solchen Dienst bleibt
  „Sofort“ die Recherche ohne Internet über Claude.
  Der Push startet die Action in der Fassung des Arbeits-Branchs. Weicht `research.yml` dort vom Buch-Branch ab
  (Änderungspaket älter als das letzte Update), bringt die App das Änderungspaket vorher auf den Buchstand
  (`update_pull_request_branch`).
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
