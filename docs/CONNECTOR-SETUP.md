# GhostWriter mit GitHub verbinden: Schritt für Schritt

Diese Anleitung ist für alle, die mit GitHub wenig zu tun haben. Du brauchst kein Programmierwissen. Plane etwa 20 Minuten ein.

> **Stand:** 31.10.2026. Die Menüs von GitHub, claude.ai und ChatGPT ändern sich immer wieder. Heißt ein Knopf bei dir etwas anders, such nach einem ähnlichen Wort. Punkte, die noch niemand mit GhostWriter ausprobiert hat, sind mit **(noch ungetestet)** markiert. Ergebnisse bitte in Issue #22 eintragen.

## Worum geht es?

GhostWriter speichert dein Buch auf GitHub. Damit ein Chat (claude.ai oder ChatGPT) dort **speichern** kann, braucht er eine eigene Erlaubnis. Die eingebauten GitHub-Verbindungen der Chat-Apps können nur **lesen**.

Du richtest deshalb einmalig drei Dinge ein:

1. **Eine eigene „App“ bei GitHub.** Das ist kein Programm, das du installierst, sondern eine Art Ausweis. Er sagt: „Dieser Chat darf in **diesem einen** Buch-Repository Dateien ändern und Pull Requests anlegen, sonst nichts.“
2. **Einen Connector in claude.ai.** Er verbindet claude.ai mit GitHub und benutzt dafür den Ausweis aus Schritt 1.
3. **Optional: denselben Connector in ChatGPT.**

Danach meldest du dich einmal an und bestätigst, und jeder neue Chat kann dein Buch lesen und Änderungen als Pull Request speichern.

### Kleine Wörterliste

| Wort | Bedeutung |
|---|---|
| **Repository** („Repo“) | Der Ordner deines Buchs auf GitHub, z. B. `deinname/mein-buch`. |
| **Branch** | Eine Arbeitskopie im Repository. GhostWriter schreibt Änderungen erst in die Arbeitskopie `ghostwriter/…`. |
| **Pull Request** | Ein Vorschlag „Bitte diese Änderungen ins Buch übernehmen“. Erst wenn du in GhostWriter „Änderungen übernehmen“ bestätigst, wird er übernommen. |
| **GitHub App** | Der Ausweis aus Schritt 1, mit genau festgelegten Rechten. |
| **Client-ID** | Die „Ausweisnummer“ der App. Nicht geheim. |
| **Client-Secret** | Das „Passwort“ der App. **Geheim!** Nie in einen Chat, eine E-Mail oder eine Datei im Repository schreiben. |
| **Connector** | Die Verbindung zwischen Chat-App und GitHub. |
| **MCP-Server** | Der Dienst von GitHub, über den der Chat mit GitHub spricht. Adresse: `https://api.githubcopilot.com/mcp/` |

## Bevor du anfängst

- [ ] Du hast ein **GitHub-Konto** und kannst dich anmelden.
- [ ] Dein **Buch-Repository** gibt es schon, z. B. `deinname/mein-buch`. Du weißt, wie es heißt.
- [ ] Du hast ein **Konto bei claude.ai** (jeder Tarif; im kostenlosen Tarif ist ein eigener Connector erlaubt). Auf Team- oder Enterprise-Tarifen darf nur ein **Owner** der Organisation eigene Connectors hinzufügen.
- [ ] Optional: ein **ChatGPT-Konto** mit Plus, Pro, Business, Enterprise oder Edu. Ob ChatGPT damit auch **speichern** darf, hängt vom Tarif ab; siehe Teil 4.
- [ ] Ein Notizzettel oder Textprogramm für die Client-ID (das Secret nicht dauerhaft notieren, nur kurz kopieren).

Ein Copilot-Abo brauchst du nach aktuellem Stand **nicht**: GitHub gibt den MCP-Server für alle GitHub-Nutzer frei. Ältere Anleitungen nennen noch ein Copilot-Abo als Voraussetzung. Erscheint beim Verbinden ein Hinweis auf Copilot, trag das bitte in Issue #22 ein.

## Teil 1: Die GitHub App anlegen (ca. 10 Minuten)

1. Öffne **github.com** und melde dich an.
2. Klick oben rechts auf dein **Profilbild** und dann auf **Settings** (Einstellungen).
3. Scroll in der linken Spalte ganz nach unten und klick auf **Developer settings**.
4. Klick links auf **GitHub Apps** und dann auf **New GitHub App**.
   GitHub fragt eventuell noch einmal nach deinem Passwort. Das ist normal.
5. Fülle das Formular aus. Alles, was hier nicht steht, lässt du, wie es ist.

   | Feld | Was du einträgst |
   |---|---|
   | **GitHub App name** | Ein Name, den es bei GitHub noch nicht gibt, z. B. `GhostWriter-deinname`. Ist er vergeben, häng eine Zahl an. |
   | **Homepage URL** | Die Adresse deines Buch-Repositorys, z. B. `https://github.com/deinname/mein-buch` |
   | **Callback URL** | `https://claude.ai/api/mcp/auth_callback` (genau so, ohne Leerzeichen) |
   | **Expire user authorization tokens** | Haken **an** lassen |
   | **Request user authorization (OAuth) during installation** | Haken **aus** lassen |
   | **Enable Device Flow** | Haken **aus** lassen |
   | **Webhook → Active** | Haken **entfernen**. Wir brauchen keinen Webhook. |

6. Scroll zu **Permissions** und klapp **Repository permissions** auf. Stell genau diese drei ein, alles andere bleibt auf **No access**:

   | Recht | Einstellung | Wofür |
   |---|---|---|
   | **Contents** | **Read and write** | Buchdateien lesen und Änderungen speichern |
   | **Pull requests** | **Read and write** | Pull Request anlegen und nach deiner Bestätigung übernehmen |
   | **Metadata** | **Read-only** | wird automatisch gesetzt, ist Pflicht |

   Bei **Organization permissions** und **Account permissions** änderst du nichts.

7. Bei **Where can this GitHub App be installed?** wählst du **Only on this account**.
8. Klick unten auf **Create GitHub App**.
9. Du landest auf der Seite deiner neuen App. Dort steht **Client ID** (eine Zeichenfolge, die mit `Iv` beginnt). Kopier sie auf deinen Notizzettel.
10. Etwas weiter unten klickst du bei **Client secrets** auf **Generate a new client secret**. GitHub zeigt das Secret **nur dieses eine Mal**. Lass die Seite offen, bis du es in Teil 2 eingetragen hast.

### Die App auf dein Buch beschränken

11. Klick in der linken Spalte deiner App auf **Install App**.
12. Klick neben deinem Konto auf **Install**.
13. Wähl **Only select repositories** und dann **nur dein Buch-Repository** aus.
14. Klick auf **Install**.

Jetzt kann die App ausschließlich dein Buch-Repository sehen und ändern, keine anderen Repositories.

## Teil 2: Connector in claude.ai einrichten (ca. 5 Minuten)

1. Öffne **claude.ai** und melde dich an.
2. Geh zu **Customize → Connectors** (direkt: `https://claude.ai/customize/connectors`).
   Auf Team- oder Enterprise-Tarifen macht das ein Owner unter **Organization settings → Connectors → Add → Custom**.
3. Klick auf **Add custom connector**.
4. Trag ein:

   | Feld | Was du einträgst |
   |---|---|
   | **Name** | `GhostWriter GitHub` |
   | **URL** bzw. **MCP server URL** | `https://api.githubcopilot.com/mcp/` |

5. Öffne **Advanced settings**. Je nach Ansicht heißt die Auswahl dort **OAuth client** → **Use your own OAuth client**.
   - **OAuth Client ID**: die Client-ID aus Teil 1, Schritt 9
   - **OAuth Client Secret**: das Secret aus Teil 1, Schritt 10
6. Klick auf **Add**.
7. Klick beim neuen Connector auf **Connect**. Es öffnet sich eine Seite von GitHub: „Authorize GhostWriter-deinname“. Prüf, dass dort dein Buch-Repository steht, und klick auf **Authorize**.
8. Du bist zurück in claude.ai. Der Connector steht jetzt auf **Connected**.

Jetzt kannst du die GitHub-Seite mit dem Secret schließen. Das Secret brauchst du nicht mehr; wenn du es einmal brauchst, erzeugst du in der App einfach ein neues.

**Warum eine eigene App?** GitHubs MCP-Server lässt Chat-Apps sich nicht automatisch anmelden. Ohne eigene Client-ID scheitert die Verbindung mit einer Meldung wie „does not support dynamic client registration“.

**(noch ungetestet):** ob GitHubs MCP-Server die Anmeldung mit einer **GitHub App** genauso annimmt wie mit einer einfacheren **OAuth App**. Klappt Teil 2 nicht, siehe „Wenn etwas nicht klappt“, Punkt 4.

## Teil 3: In einem Chat benutzen

1. Öffne einen neuen Chat in claude.ai.
2. Klick auf **+** und dann auf **Connectors**. Schalte **GhostWriter GitHub** ein.
3. Schick den Link zu deinem Buch-Repository, z. B. `https://github.com/deinname/mein-buch`.
4. Claude zeigt die Projektübersicht. Wenn du etwas speicherst, fragt claude.ai vor jeder Schreibaktion nach, ob es das darf. Lies die Frage und erlaube sie. Klick **Always allow** nur, wenn du dir sicher bist.

Was du erwarten solltest:
- Nach dem Speichern meldet GhostWriter „✓ … gespeichert, Commit abc1234 · noch nicht übernommen (Pull Request #NN)“.
- In der Projektübersicht erscheint der Hinweis „1 Änderung noch nicht übernommen“ mit dem Knopf **Änderungen übernehmen**.
- Erst wenn du dort bestätigst, steht die Änderung im Buch.

## Teil 4: Optional in ChatGPT einrichten

> **Wichtig vorab:** OpenAI macht widersprüchliche Angaben dazu, welche Tarife über eigene Connectors **speichern** dürfen. Sicher ist es laut OpenAI-Hilfe in **Business, Enterprise und Edu** (dort als Beta). Bei **Plus** ist es unklar, bei **Pro** angeblich nur Lesen. Im kostenlosen Tarif geht es nicht. **(noch ungetestet)**

1. Öffne **chatgpt.com** im Browser (nicht in der Handy-App).
2. Geh zu **Settings → Apps → Advanced settings** und schalte **Developer mode** ein.
   In Business-, Enterprise- oder Edu-Arbeitsbereichen muss das eventuell zuerst ein Admin erlauben.
3. Klick auf **Create app** (erscheint neben **Advanced settings**, sobald Developer mode an ist).
4. Trag ein:
   - **Name**: `GhostWriter GitHub`
   - **MCP Server URL**: `https://api.githubcopilot.com/mcp/`
   - **Authentication**: **OAuth**
5. Bietet ChatGPT Felder für **Client ID** und **Client Secret** an, trag dieselben Werte wie in Teil 2 ein. (Für ein neues Secret: in deiner GitHub App **Generate a new client secret**.)
6. ChatGPT zeigt eine **Redirect URL** oder **Callback URL** an. Kopier sie, geh zurück zu deiner GitHub App (**Settings → Developer settings → GitHub Apps → deine App → Edit**), klick bei **Callback URL** auf **Add Callback URL**, füg sie ein und klick unten auf **Save changes**.
7. Zurück in ChatGPT: fertig anlegen und mit GitHub verbinden (**Authorize**).
8. In einem neuen Chat: **+** → **Developer mode** → **GhostWriter GitHub** auswählen, dann den Link zum Buch schicken.

ChatGPT zeigt GhostWriter nicht als Formulare, sondern als Text mit Kürzeln (z. B. `2.4`, `M`, `OK`). Das ist so gewollt.

## Wenn etwas nicht klappt

| Was du siehst | Was du tun kannst |
|---|---|
| 1. „does not support dynamic client registration“ oder „Authorization failed“ gleich beim Verbinden | Die Client-ID fehlt oder ist falsch. Connector entfernen und neu anlegen (Teil 2), dabei unter **Advanced settings** Client-ID und Secret eintragen. Einstellungen lassen sich nachträglich nicht ändern, nur neu anlegen. |
| 2. GitHub meldet „The redirect_uri is not associated with this application“ | Die **Callback URL** in der GitHub App stimmt nicht. Für claude.ai muss dort genau `https://claude.ai/api/mcp/auth_callback` stehen, für ChatGPT zusätzlich die Adresse, die ChatGPT anzeigt. |
| 3. Lesen klappt, Speichern nicht: „Resource not accessible by integration“ oder „404 Not Found“ | Die App ist nicht in deinem Buch-Repository installiert (Teil 1, Schritte 11–14), oder **Contents** bzw. **Pull requests** stehen nicht auf **Read and write**. Nach einer Änderung der Rechte musst du sie unter **Settings → Applications → Installed GitHub Apps → deine App** noch einmal **akzeptieren**. |
| 4. Mit der GitHub App klappt die Anmeldung gar nicht | Ersatzweg: statt einer GitHub App eine **OAuth App** anlegen (**Developer settings → OAuth Apps → New OAuth App**, gleiche Callback URL), Client-ID und Secret wie in Teil 2 eintragen. **Achtung:** Eine OAuth App darf auf **alle** deine Repositories zugreifen, nicht nur auf das Buch. Bitte in Issue #22 melden. |
| 5. Nach einigen Stunden fragt der Chat wieder nach der Anmeldung | Normal: Die Anmeldung einer GitHub App läuft nach rund acht Stunden ab und wird meist automatisch erneuert. Sonst einfach erneut **Connect**. |
| 6. Der Chat zeigt nur Lesen-Werkzeuge an (ChatGPT) | Vermutlich erlaubt dein Tarif keine Schreibaktionen. Siehe Teil 4, „Wichtig vorab“. |
| 7. Hinweis auf ein Copilot-Abo | Bitte in Issue #22 melden (mit Bildschirmfoto ohne Secret). |

## Sicherheit in einfachen Worten

- Das **Secret** ist ein Passwort. Schreib es nie in einen Chat, eine Datei im Repository, ein Issue oder eine E-Mail. Hast du es versehentlich geteilt: in der GitHub App unter **Client secrets** löschen und ein neues erzeugen, dann den Connector neu anlegen.
- Die App darf nur in deinem Buch-Repository Dateien ändern, in keinem anderen. Technisch könnte sie dort jede Datei ändern; GhostWriter schreibt nach seinen Regeln aber nur in die Arbeitskopie `ghostwriter/…`, und ins Buch kommt eine Änderung erst, wenn du „Änderungen übernehmen“ bestätigst. Ältere Stände bleiben in der Versionsgeschichte von GitHub erhalten.
- Die Chat-App fragt vor jeder Schreibaktion nach. Erlaube nur, was zu dem passt, was du gerade in GhostWriter gemacht hast.
- **Verbindung trennen:** in claude.ai unter **Customize → Connectors** den Connector entfernen. Zusätzlich bei GitHub unter **Settings → Applications → Authorized GitHub Apps** die App widerrufen (**Revoke**).
- **Ganz aufhören:** bei GitHub unter **Settings → Applications → Installed GitHub Apps** die App deinstallieren und unter **Developer settings → GitHub Apps** löschen.

## Quellen

- Anthropic: [Add a connector that isn't in the directory](https://claude.com/docs/connectors/custom/add-unlisted.md) (Menüs in claude.ai, eigene OAuth-Client-ID)
- Anthropic: [Authentication for connectors](https://claude.com/docs/connectors/building/authentication) (Callback URL `https://claude.ai/api/mcp/auth_callback`)
- OpenAI: [ChatGPT Developer mode](https://developers.openai.com/api/docs/guides/developer-mode.md) (Menüs, Tarife, Bestätigung von Schreibaktionen)
- [ChatGPT MCP: Setup, Plans, and Limits](https://coworker.ai/blog/chatgpt-mcp) (Stand 15.10.2026; widersprüchliche OpenAI-Angaben zu Schreibrechten je Tarif)
- [Issue „Incompatible auth server: does not support dynamic client registration“](https://github.com/anthropics/claude-plugins-official/issues/283) (GitHubs MCP-Server verlangt eine vorab angelegte App)
- [GitHub MCP Server: Official, Self-Hosted and Per-User OAuth](https://www.scalekit.com/blog/github-mcp-server-per-user-oauth) (Stand 14.10.2026; kein Copilot-Abo nötig, eigene App für OAuth)
- [A practical guide on how to use the GitHub MCP server](https://github.blog/ai-and-ml/generative-ai/a-practical-guide-on-how-to-use-the-github-mcp-server/) (GitHub-Blog, 2025; nennt noch ein Copilot-Abo als Voraussetzung)
- Anthropic: [Connect to GitHub](https://claude.com/docs/third-party/claude-desktop/connectors-github) (GitHub App statt OAuth App möglich; Anmeldung läuft nach etwa acht Stunden ab)
