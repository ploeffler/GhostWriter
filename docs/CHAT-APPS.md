# Chat-Apps für GhostWriter v0.5

Stand: 31.10.2026. Vorrangig unterstützt werden Claude und ChatGPT. Funktionen der Chat-Apps ändern sich laufend; vor dem Einsatz prüfen.

Welche Fähigkeiten (Text, Dateianzeige, Auswahlfragen, GhostWriter-Widgets, installierte Integrationen) je Client verfügbar, nicht verfügbar oder ungeprüft sind, steht auf der Seite [Clients und Fähigkeiten](CLIENT-FAEHIGKEITEN.md).

## Ergebnis

Die **eingebauten GitHub-Verbindungen** beider Apps können nur lesen (Stand der Bewertung; der Connector im ChatGPT-Chat schreibt laut Nachtrag vom 24.11.2026 inzwischen). Für Weg A braucht GhostWriter aber Schreibzugriff: Commits auf einen Arbeits-Branch, Pull Request anlegen und mergen, Tag und Release anlegen.

| Fähigkeit | Claude: eingebaute GitHub-Integration | Claude mit Arbeitsumgebung (agentische Sitzung, Claude Code) | ChatGPT: GitHub-Connector | ChatGPT: Codex | Eigener Connector mit GitHubs MCP-Server (beide Apps) |
|---|---|---|---|---|---|
| Repository lesen | ja (Dateien eines Branches) | ja | ja | ja | ja |
| Commit, Branch | nein | ja | ja, über den Connector (belegt 24.11.2026, #579) | ja | laut Werkzeugliste vorgesehen, im Chat zu testen |
| Pull Request anlegen | nein | ja | ja, über den Connector (belegt 24.11.2026, #579) | ja | zu testen |
| Pull Request mergen | nein | ja | nicht belegt | nicht belegt | zu testen |
| Tag und Release anlegen | nein | nein: in der Sitzung vom 31.10.2026 von GitHub abgelehnt („not permitted for this session type“), ebenso Branches löschen | nein | nicht belegt | nicht belegt |
| Chat-Vorlagen als Widget mit Rückmeldung in den Chat | ja (Inline-Widgets) | ja, wenn die Sitzung Widgets anbietet | nein, Textfassung nötig | nein | wie die jeweilige App |

**Praxisbericht vom 22.11.2026 (#22, Angabe des Eigentümers):** In Claude und in ChatGPT wurde mit Repositories gearbeitet; Datei ändern mit Commit, Branch anlegen, Pull Request anlegen und Pull Request mergen funktionierten in beiden Apps, und ein GhostWriter-Formular speicherte in ChatGPT als Pull Request. Genutzt wurde ein gemischter Weg; welche Verbindung je App im Einzelnen im Einsatz war (eigener Connector, Codex oder Claude Code), ist nicht je Spalte festgehalten. Die Spalte „Eigener Connector“ bleibt deshalb ohne ausdrückliche Einzelbelege, bis das je App und je Tarif nachgetragen ist.

**Nachtrag vom 24.11.2026 (#579):** Der Praxisbericht stimmt auch für den ChatGPT-Chat: Der GitHub-Connector bietet dort Branches, Commits und Pull Requests, auch ohne Git-Zugang, `gh`-Anmeldung und `add_repo`. Ein Beleg: Commit und Pull Request „GhostWriter: offene Änderungen“ in `chillyconcane/YAWA` über den Connector, `validate` lief mit. Die Schreibprüfung muss deshalb je Zugang erfolgen (`START.md`, „Zugang und Schreibzugriff“):

| Zugang | Prüfung | Nachweis des Schreibens |
|---|---|---|
| Klon und Git-Anmeldung (Claude Code, Claude mit `add_repo`, Codex) | `permissions.push` und Probe-Push mit `--dry-run` | Probe-Push, dann der erste Commit |
| Nur GitHub-Connector (ChatGPT-Chat, Claude ohne Klon) | `permissions.push` über den Connector; **kein Probe-Push** | der erste echte Commit auf `ghostwriter/<buch-branch>` |
| Kein Schreibwerkzeug | nichts zu prüfen | Dateien mit Zielpfad im Chat ausgeben (`START.md`, „Freigabe und Repository-Übertragung“) |

Der Assistent nennt in einem Satz, welcher Fall vorliegt, statt abzubrechen. Kann ein Client keinen Pull Request anlegen, bittet der Assistent den Benutzer, ihn auf GitHub anzulegen.

Belege:
- Claude: Die GitHub-Integration synchronisiert nur Dateinamen und Inhalte eines Branches, ohne Commit-Historie und Pull Requests ([Anthropic-Hilfe: Use the GitHub integration](https://support.claude.com/en/articles/10167454-use-the-github-integration)).
- ChatGPT: Der GitHub-Connector in Chat und Deep Research ist zum Lesen gedacht; Codex kann Branches pushen und Pull Requests öffnen ([Übersicht vom 9.7.2026](https://www.usecarly.com/blog/chatgpt-github-integration/)). Die Hilfeseite von OpenAI ([Connecting GitHub to ChatGPT](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)) war beim Abruf nicht erreichbar.
- GitHubs offizieller MCP-Server ist unter `https://api.githubcopilot.com/mcp/` erreichbar und hat Werkzeuggruppen für Repositories und Pull Requests; für Claude Desktop und Claude Code gibt es Anleitungen, für claude.ai und ChatGPT als eigener Connector ist eine eigene OAuth-App nötig ([github-mcp-server](https://github.com/github/github-mcp-server), [Diskussion zu claude.ai](https://github.com/anthropics/claude-ai-mcp/issues/98)).

## Schreibwege für Weg A

1. **Claude mit Arbeitsumgebung.** Commits, Branches, Pull Requests und Merge funktionieren heute, ebenso die Widgets; Tags und Releases nicht. Abhängig von der Claude-App mit agentischen Sitzungen.
2. **Eigener Connector mit GitHubs MCP-Server** in Claude und ChatGPT. Einmalige OAuth-Einrichtung je App; welche Schreibwerkzeuge im Chat verfügbar sind, muss praktisch getestet werden. Anleitung: [CONNECTOR-SETUP.md](CONNECTOR-SETUP.md).
3. **Rückfall** aus `docs/INTEGRATION.md`, Betriebsart B: Der Assistent gibt geänderte Dateien vollständig aus, der Benutzer committet selbst. Funktioniert überall, aber ohne Pull-Request-Ablauf aus dem Chat.

Keiner der Wege legt verlässlich Tags und Releases an. Vorschlag: Eine Auflage wird ein Pull Request, der `project.current_edition` hochzählt und die Release Notes enthält; nach dem Merge legt eine GitHub Action Tag und Release an und hängt PDF, DOCX und EPUB an (Issues #16 und #17).

Welcher Weg für v0.5 gilt, wird am Ende von v0.2 entschieden.

## Web-App „GhostWriter für Claude“ (Versuch)

**Wird nicht mehr gepflegt (Beschluss vom 27.11.2026; Nachfolger ist die eigene Web-App, #662).** Neben dem Chat gab es einen Versuch mit einer Web-App, die als Artefakt in Claude läuft; der Link bleibt in der zuletzt veröffentlichten Fassung: [GhostWriter für Claude](https://claude.ai/artifact/PQ3zcq4ofwwRcP7dMHMG9B). Sie zeigt dieselben Widgets wie der Chat und führt Klicks direkt aus: Abschnitt speichern, Freigaben, Kapitel und Abschnitte anlegen, Reihenfolge, Projektdaten, Recherche und Ghostwriting „Sofort“, Änderungen übernehmen, die Seite „Daten“ und eine Claude-Leiste mit Vorschlägen. Gelesen und geschrieben wird über die GitHub-Verbindung des jeweiligen Benutzers. Claude läuft über dessen eigenes Konto. Es gibt keine eigene API, keinen Server und keine Schlüssel.

Es gelten dieselben Regeln wie im Chat. Alles kommt auf den Arbeits-Branch, als ein Commit je Aktion. Ins Buch kommt es nur über „Änderungen übernehmen“ mit Bestätigung, und jede Freigabe braucht eine eigene Bestätigung. Für private Repositorys muss die GitHub-App „Claude Github MCP Connector“ auf dem Besitzerkonto installiert sein. Die App gehört nicht zum Lieferumfang von v1.0 ([D06](ENTSCHEIDUNGEN-v1.0.md#d06--eigene-web-app-ohne-integrierten-modellaufruf)). Ihre Dateien kommen mit dem Update nicht in die Bibliotheken. Einrichtung, Grenzen und Nachziehen: [apps/claude/README.md](https://github.com/ploeffler/GhostWriter/blob/main/apps/claude/README.md).

## Dateien im Chat übergeben (#260)

„Manuskript ausgeben“ baut das PDF in der Action „Manuskript ausgeben“; der Chat holt es mit `scripts/fetch_artifact.py` ab und übergibt es als Datei. Stand 11.11.2026, **noch nicht in allen Apps praktisch geprüft**:

| App | Erwarteter Weg |
|---|---|
| Claude mit Arbeitsumgebung | PDF abholen und als Datei im Chat senden |
| Codex | PDF im Arbeitsordner ablegen bzw. anhängen |
| ChatGPT (GitHub-Connector) | abhängig von Connector und Code-Umgebung; sonst Link zum Lauf |
| Open WebUI | Link zum Lauf (`dispatch_workflow` startet `manuscript.yml`) |

Ohne Dateiübergabe bleibt der Link zum Lauf: Download unter *Artifacts*, 14 Tage, mit GitHub-Anmeldung.

**Erprobt am 11.11.2026 (Claude in der Cloud):** Bau und Start funktionieren; das Abholen scheiterte, weil GitHub Artifacts über `*.blob.core.windows.net` ausliefert und die Sitzung diese Adresse sperrt. Abhilfe: die Adresse unter *Einstellungen → Fähigkeiten* erlauben, sonst gilt der Link zum Lauf.

## Lesefassung neben der Ansicht (#289)

Zur Kapitel- und Abschnittsansicht erzeugt der Assistent mit `scripts/assemble.py … reading N` bzw. `N.M` den Text als Markdown-Datei und übergibt sie neben der Ansicht, nach jeder Änderung neu (`START.md`, „Lesefassung“). Stand 15.11.2026:

| App | Weg |
|---|---|
| Claude mit Arbeitsumgebung | Datei senden mit Darstellung „anzeigen“: öffnet sich in der Seitenansicht, nichts wird heruntergeladen (in YAWA erprobt) |
| Codex / ChatGPT Work mit Dateiwerkzeugen | Bestehende Lesefassung im Dateipanel bzw. verfügbaren Vorschauwerkzeug öffnen. In Codex `open_in_codex` mit Dateiziel, absolutem Pfad und `placement: right`; kein Browser. `queued` heißt nur „zur Anzeige vorgemerkt“. |
| ChatGPT ohne Skriptausführung | Action „Manuskript ausgeben“ mit `format md`, danach die Datei vom Branch `lesefassung/<buch>` bereitstellen. Bei nur lesender Verbindung startet der Autor die Action über den Link. Nur vorhandene Datei-/Vorschauwerkzeuge nutzen; keine Canvas- oder Schreibblock-Anzeige voraussetzen. Ohne Vorschau Datei/Link und Einschränkung nennen. **Dieser Ersatzweg ist noch nicht praktisch geprüft.** |
| Open WebUI | `dispatch_workflow` (`format md`, Werkzeug ab 1.7), danach `read_file` vom Branch `lesefassung/<buch>`. **Noch nicht praktisch geprüft** |

Die vorhandene Regel gilt auch für OpenAI (#316), unabhängig vom Darstellungsmodus. Bei vorhandener Skriptausführung direkt erzeugen; kein Action-Lauf nur zum Anzeigen. Auch noch ungespeicherte Abschnittsvorschläge können mit `assemble.py <projekt> reading N.M --draft-file <vorschlag.md> -o <leseordner>` (Leseordner außerhalb des Buchordners) in derselben Datei geprüft und nach Änderungen aktualisiert werden. Die Vorschau verändert kein Manuskript und keine Freigabe; sie zeigt den Vorschlagszustand getrennt vom gespeicherten Status. Lokale Vorschau, Arbeitsbranch und übernommener Buchstand sind verschiedene Speicherstände.

Bei „Darstellung: erweitert“ bleibt die erweiterte Abschnittsansicht im Chat: Kapitel/Abschnitt, Ziel, Kurzbeschreibung, Bearbeitung, tatsächlicher Speicherstand, Schreib- und Abschlussstatus, Quellenstand, offene Punkte und Aktionen. Fehlende Angaben als unbekannt ausweisen; Kosten/Marker nur aus Daten. Den vollständigen Text nicht doppelt im Chat zeigen. `Lesefassung aus/an` wirkt nur im laufenden Chat und schaltet nicht den Darstellungsmodus um. Ohne sichtbare Bestätigung höchstens „Anzeige angefordert“ melden; fehlende Werkzeuge offen nennen. Eine Vorschau ist keine Freigabe.

Die [offizielle OpenAI-Dateidokumentation](https://learn.chatgpt.com/docs/artifacts-viewer) beschreibt Unterschiede zwischen Desktop, Work im Web, CLI und IDE. Sie belegt keine identische Seitenanzeige in jedem Client. Der konkrete Codex-Aufruf richtet sich nach dem tatsächlich angebotenen Werkzeug. Prüfung am 15.11.2026: Erzeugung und Aktualisierung derselben Datei lokal bestätigt. Das Codex-Werkzeug meldete nur `queued`; der Benutzer bestätigte anschließend lesbare Anzeige und automatische Aktualisierung derselben Datei ohne erneutes Öffnen. Diese Sichtabnahme gilt für die geprüfte Codex-Sitzung. ChatGPT Work bleibt praktisch ungeprüft.

Der Branch `lesefassung/<buch>` enthält nur die zuletzt erzeugten Lesefassungen je Kapitel bzw. Abschnitt und wird nie gemergt. Die Datei zeigt den Stand beim Start der Action; nach einer Änderung kommt sie nur neu, wenn die Action erneut läuft. Jeder Lauf kostet etwa eine Actions-Minute (ohne TeX).

## Gespräch und Manuskriptarbeit (#315)

Bucharbeit wechselt zwischen **Gespräch** (Ideen, Figuren, Szenen, Recherche besprechen; keine Buchdateien ändern) und **Manuskriptarbeit** (Abschnitte schreiben und überarbeiten, Buchstand speichern). Mit `work_modes: auto` im Assistenten-Profil oder dem Befehl `Moduswechsel automatisch an` wählt der Assistent den Modus selbst aus dem Auftrag und nennt den Wechsel nur kurz; ohne diese Einstellung fragt er vor der Manuskriptarbeit einmal nach. Vor dem ersten Schreiben prüft er Buch, Branch, Pull Request und den aktuellen Stand der Datei neu. Speichern, Übernehmen und Freigaben bleiben eigene, bestätigte Schritte ([START.md](../START.md), „Gespräch und Manuskriptarbeit“).

| Umgebung | Gespräch | Manuskriptarbeit | Wechsel |
|---|---|---|---|
| Claude mit eingebundenem Repository bzw. Arbeitsumgebung | ja | ja | im selben Chat, ohne Übergabe |
| Claude ohne Repository, ChatGPT mit GitHub-Connector (nur lesend) | ja | nein | vorbereitete Übergabe in eine Umgebung mit Schreibzugriff |
| ChatGPT Work, Codex | ja | ja | im selben Chat; Übergabe zurück in einen reinen Chat bei Bedarf |
| Open WebUI | ja | je nach eingerichteten Werkzeugen | sonst vorbereitete Übergabe |

Ein Wechsel der Oberfläche selbst (z. B. vom ChatGPT-Chat nach Work) liegt beim Anbieter; GhostWriter schaltet sie nicht um. Der Assistent sagt diese Grenze in einem Satz und bietet den Befehl `Übergabe` an: `python scripts/handover.py . --section 3.2 --mode manuskript` erzeugt einen kopierfertigen Text mit Starttext, geprüftem Stand (Repository, Buch-Branch und Commit, Arbeitsbranch, Pull Request, Abschnitt mit Prüfsumme, offene Abschnitte, Gesprächssicherungen) und einem JSON-Block. Aus den Sicherungen – übernommenen im Buch und noch offenen `ghostwriter/chat/*` – übernimmt sie die gespeicherten **Entscheidungen** und **offenen Aufgaben** (Thema Planung), je Sicherung auf 600 Zeichen gekürzt und mit Herkunft; das ist gespeicherter Stand, keine Freigabe (#315, Teil 2). Der Assistent ergänzt, was nur im Chat steht, ausdrücklich als nicht gespeichert. In der anderen Umgebung prüft `python scripts/handover.py . check <übergabe>` vor dem ersten Schreiben: `✓` unverändert, `ⓘ` neuere Fassung (erst neu lesen), `✗` Konflikt (nicht schreiben). Das Skript liest nur.

## Standabgleich zwischen Chats und Apps (#179)

Ein offener Chat kann veraltet sein, wenn in einer anderen App gespeichert, ein Programmupdate eingespielt oder `assistant.yml` geändert wurde. Der Assistent hält nach dem Laden den gelesenen Stand fest (`python scripts/standabgleich.py . stand --book <buch> [--work <arbeitsbranch>] --fetch`) und prüft ihn bei jeder neuen Aufgabe, nach einer Pause und vor dem Schreiben (`… check <stand> --fetch`): `✓` unverändert, `ⓘ` neuer Stand (Dateien neu lesen, bei geänderten Anweisungen oder Profil diese neu laden), `✗` Konflikt (nicht schreiben). Geprüft werden Buch, Arbeitsbranch, Programm, Anweisungen, Profil und Datenversion, dazu als Hinweis `⚠`, ob Übersichtsdatei und Zusammenfassungen zum Stand passen (sonst aus den Originaldateien lesen); Chatinhalte, nicht gesendete Eingaben und der Zwischenspeicher einer Verbindung nicht. Das Skript liest nur.

## Token sparen im laufenden Chat (#392)

Was ein Chat verbraucht, wächst mit jeder Nachricht: Die App schickt den ganzen
bisherigen Verlauf und die Beschreibungen aller verbundenen Werkzeuge jedes Mal
mit. GhostWriter hält den Stand im Repository, darum geht beim Wechsel nichts verloren.

- **Neuer Chat je Aufgabe:** neues Buch, neue Aufgabe oder abgeschlossener
  Abschnitt → neuer Chat. Der Assistent schlägt das an passenden Stellen vor
  (nach einer Freigabe, nach Planung oder Recherche), nie mitten in einer
  Überarbeitung oder Fehlersuche und ohne Zwang.
- **Übergabesatz:** Am Ende einer Aufgabe gibt der Assistent einen kurzen Satz
  zum Weitermachen mit (Buch, Abschnitt, offener Schritt). Im neuen Chat lädt er
  Buchwissen und gesicherte Gespräche selbst ([Wissensstand](BUCHGEDAECHTNIS.md#wissensstand-beim-wechsel-ins-buch-369)).
  Ungesichertes vorher sichern ([Abschluss-Check](SESSION-SICHERUNG.md#abschluss-check-verabschieden-und-ende-einer-befragung-298-372)).
- **Weniger Verbindungen:** Für Bucharbeit nicht benötigte Verbindungen
  (Konnektoren, MCP-Server, Werkzeuge in Open WebUI) im Chat bzw. in den
  Einstellungen der App abschalten. Ein Großteil des Grundverbrauchs stammt aus
  deren Werkzeugbeschreibungen, nicht aus GhostWriter (Messung in #296).
- **Hilfsagent für viele Kapitel:** Wo die App Hilfsagenten kennt (z. B. Claude
  Code), liest er bei Buchgedächtnis und Lektorat die Kapitel und gibt nur
  Befunde mit Fundstellen zurück. Das hält zugleich die Regel „kein ganzes Buch im Chat“ ein.
- **Kleineres Modell für mechanische Prüfungen (#418):** Korrektur und
  Nachprüfung laufen mit einem kleinen Modell, Strukturlektorat und neuer Text
  mit einem großen; siehe [Modellwahl für Hilfsagenten](LEKTORAT.md#modellwahl-für-hilfsagenten-418).
- **Recherche mit Hilfsagenten (#449):** je Recherchethema ein Agent, parallel;
  in den Chat kommt nur das Gerüst der Laufdatei zurück, siehe `START.md`,
  „Recherche mit Hilfsagenten (#449)“.

Nicht übertragen: Einstellungen, die nur für Claude Code im Terminal gelten
(Modellwahl in `settings.json`, Umgebungsvariablen, `/cost`). Offen bleibt eine
Messung mit `Prompt-Profil JSON`, ab welcher Verlaufslänge ein neuer Chat lohnt.

## Automatisch geladene Hinweise (#136)

Jedes GhostWriter-Repository bringt drei Einstiegsdateien mit, die mit jedem Update aus dem Hauptrepository kommen:

- `CLAUDE.md` – liest Claude von selbst, sobald das Repository in einer Sitzung mit Repository-Zugriff eingebunden ist (Claude Code, auch in claude.ai).
- `AGENTS.md` – dieselben Regeln für andere Assistenten, die diese Datei lesen.
- Den Wiedereinstieg beschreibt `START.md`, Abschnitt 0; einen eigenen Skill `ghostwriter` mit Ablauf gibt es im Repository nicht mehr (#569). Im Claude-Konto genügt der schlanke Skill `ghostwriter` aus ghostwriter-skills, der nur auf `START.md` verweist.

Dazu kommt je Repository das **Assistenten-Profil** `assistant.yml` mit dem daraus erzeugten persönlichen Skill `.claude/skills/<autor>-auf-<repo>/SKILL.md` (Git-Benutzer, Autor, Standard-Erzählstimme; `START.md`, „Assistenten-Profil“). Beides gehört dem Buch und wird von Updates nie überschrieben.

**ChatGPT und Codex:** Es gibt keinen eigenen ChatGPT-Einstieg; `AGENTS.md` gilt für ChatGPT und Codex genauso wie `CLAUDE.md` für Claude. Codex liest `AGENTS.md` von selbst. Im ChatGPT-Chat mit GitHub-Connector in den Projektanweisungen auf `AGENTS.md` und `START.md` verweisen. Eine von Hand angelegte `CHATGPT.md` im Buch-Repository gehört dem Buch, kommt mit keinem Update und veraltet deshalb; besser ist ein kurzer Verweis:

```markdown
# GhostWriter – Hinweise für ChatGPT

Es gelten `AGENTS.md` und `START.md` dieses Repositorys (kommen mit jedem Update aus dem Hauptrepository) sowie `assistant.yml`. In ChatGPT gibt es keine Widgets: Ansichten als Textfassung (`render_view.py … --text --repo <owner>/<repo>`). Hier nur ergänzen, was ausschließlich für ChatGPT in diesem Repository gilt.
```

**Grenzen:** Automatisch geladen wird das nur von Assistenten mit Zugriff auf das Repository, die diese Dateien auch lesen. In reinen Chat-Apps (ChatGPT, Gemini, Copilot, Claude ohne eingebundenes Repository) bleibt der Hinweis in `README.md` der Einstieg; der Assistent liest `START.md` und `assistant.yml` dann beim Wiedereinstieg selbst. In diese Dateien gehören keine Secrets und keine Manuskripttexte.

## Skills auswählen (#261)

Die allgemeinen Skills werden in [ghostwriter-skills](https://github.com/ploeffler/ghostwriter-skills) gepflegt. GhostWriter liefert Kopien mit, deren Quellcommit und SHA-256-Prüfsummen in `ghostwriter-skills.yml` festgelegt sind. Sie bleiben offline verfügbar und werden mit normalen Programmupdates verteilt. Änderungen an diesen Skills gehören ins Quellrepository, nicht unabhängig in die Kopien. Persönliche Skills bleiben im Buchrepository. Der optionale Buchteaser wird ausdrücklich aus dem Skill-Repository geladen; er wird nicht automatisch installiert.

Für die Pflege das Quellrepository klonen, eine geprüfte vollständige Commit-ID auswählen und `python scripts/sync_skills.py --source /pfad/zu/ghostwriter-skills --commit VOLLSTAENDIGE_COMMIT_ID` ausführen. Ohne Argumente prüft der Helfer die mitgelieferten Kopien offline. `check_docs.py` enthält diese Prüfung. Der Helfer committet und überträgt nichts; Änderungen im Quellrepository aktualisieren vorhandene Bücher nicht von selbst.



**Unabhängig vom Assistenten:** Die Skills liegen im Repository unter `.claude/skills/<name>/SKILL.md`. Claude Code lädt sie selbst; ChatGPT, Codex und andere Assistenten werden über `AGENTS.md` (Claude über `CLAUDE.md`) angewiesen, die Kopfzeilen aller `SKILL.md` zu lesen und den passenden Skill vollständig zu laden, bevor sie beginnen. Beide Dateien kommen mit dem Update aus dem Hauptrepository; im Buch ist nichts einzurichten.

**Skill-Auflösung ohne native Skillunterstützung (#766):** `START.md` (Abschnitt 0, „Skills finden und laden“) verweist auf `ghostwriter-skills.yml` und legt die Reihenfolge fest: nativer Skill des Chat-Programms, nur wenn er dem vorgesehenen Stand entspricht; sonst die ausgelieferte `SKILL.md` im Buch-Repository; fehlt sie, `skills/<name>/SKILL.md` aus dem Quellrepository am festgelegten Commit (nie von `main`), mit Prüfsumme soweit technisch möglich. Ein Assistent mit GitHub-Lesewerkzeug findet den Skill so ohne Hinweis des Benutzers; fehlende Dateien oder Werkzeuge werden konkret gemeldet, geladen gilt nur, was wirklich gelesen wurde. Persönliche Skills im Buch-Repository gehen vor. Die Regel kommt mit dem normalen Update; in bestehenden Büchern ist nichts von Hand zu ändern.

Der lokale Standabgleich berücksichtigt den gesamten Ordner `.claude/skills/` im geprüften Programmstand einschließlich persönlicher Skills und ihrer Begleitdateien sowie die Quellenangabe `ghostwriter-skills.yml`. Wird eine dieser Dateien hinzugefügt, geändert oder entfernt, meldet er veraltete Anweisungen. Die Regeln müssen vor der nächsten Aufgabe neu geladen werden; ein bereits offener Chat wird dadurch nicht automatisch aktualisiert.

Welcher Skill zu einer Aufgabe passt, entscheidet Claude anhand der Skill-Beschreibungen. Der Benutzer sieht das sonst nicht, und bei ähnlichen Beschreibungen ist die Wahl nicht eindeutig. Deshalb gilt für GhostWriter (`CLAUDE.md`, `AGENTS.md`):

- **Wahl nennen:** Zu Beginn einer Aufgabe nennt Claude in einem Satz, welchen Skill es verwendet, oder dass keiner passt.
- **Allgemeine Skills und ihre Aufgabe:** `ghostwriter-lektorat` (Prüfaufträge), `ghostwriter-buchgedaechtnis` (Fakten und Kontinuität), `ghostwriter-gegenlesen` (Auschecken zum Gegenlesen, Einchecken der Rückgabe, Checkout beenden; Kürzel `AC`, `EC`, `CB`, #572/#573) `ghostwriter-material` (Material einbringen, Kürzel `ME`, auch bei einem Upload ohne Befehl, #574) und `ghostwriter-anekdoten` (eigene Erlebnisse erfassen und anonymisiert einbauen, Kürzel `AN`, auch bei einem `[PLATZHALTER-ANEKDOTE]`, #643). Bei einer Rückgabe als Foto oder Scan gilt `ghostwriter-gegenlesen`, das für Ablage und Aufbereiten auf `ghostwriter-material` verweist.
- **Spezifischer vor allgemein:** Der persönliche Skill des Repositorys (`assistant.yml` → `skill`) geht vor den allgemeinen Skills. Die Buch-Skills sind für Buch- und Bibliotheks-Repositorys gedacht, nicht für Programmarbeit am Hauptrepository. Nur bei echter Mehrdeutigkeit fragt Claude einmal kurz nach.
- **Nicht doppelt laden:** Jeder Ladevorgang setzt die ganze Anleitung erneut in den Verlauf. Das kostet Kontext, und der Verlauf wird früher zusammengefasst. Liegt die Anleitung im Gespräch noch vor, lädt Claude sie nicht erneut. Fehlt sie nach dem Zusammenfassen eines langen Verlaufs, lädt Claude sie neu und sagt das kurz.

**Skills im Konto:** Skills, die im Claude-Konto liegen (nicht im Repository), kann GhostWriter nicht ändern. Haben zwei davon fast dieselbe Beschreibung (etwa ein älterer Skill für dieselbe Bibliothek neben dem erzeugten persönlichen Skill), den überzähligen in den Claude-Einstellungen unter „Skills“ entfernen. Eine Projektanweisung wie „Bestätige die Skillauswahl“ ist damit nicht mehr nötig, schadet aber nicht. Der persönliche Skill gehört nicht ins Konto: Er hängt von Benutzer und Repository ab und lebt nur im Repository (`.claude/skills/<skill>/SKILL.md`, aus `assistant.yml` erzeugt). Eine Kopie im Konto veraltet beim nächsten Neuerzeugen; Claude weist einmal darauf hin, und es gilt die Fassung im Repository. Allgemeine Abläufe wie Einrichten, Schreibzugriff prüfen und Issues melden stehen im Skill `ghostwriter`, nicht im persönlichen Skill.

## Darstellung

- **Claude** zeigt die Vorlagen als Inline-Widgets. Der Assistent gibt nur eine Ladezeile für `ghostwriter-ui` (fester Commit, über jsDelivr) und die Daten aus; das ist deutlich kürzer als die ganze Ansicht. Ein Klick schickt die festgelegte Nachricht in den Chat.
- **ChatGPT** zeigt diese Widgets nicht. Dort gibt der Assistent die Textfassung aus `templates/ui/BEFUELLUNG.md` aus: Markdown mit Tabellen und Symbolen, Aktionen als Kürzel (`2`, `2.4`, `P`, `X` …), die der Benutzer per Antwort wählt. Echte Formulare in ChatGPT gingen nur über eine eigene App mit MCP-Server (Apps SDK), siehe Weg B.
- **Open WebUI** zeigt keine Widgets. Die Pipe „GhostWriter Direkt“ erzeugt alle Ansichten selbst als Markdown und schaltet „Darstellung: einfach / übersichtlich / erweitert“, „Nur Text“ und den Antwortmodus ohne Modellaufruf um (ab Pipe 1.8 mit GitHub-Werkzeug 1.5, #282). Das Gesprächsmodell erhält ab Werkzeug 1.6 einen eigenen kurzen Einstieg `docs/start/einstieg-openwebui.md` statt der allgemeinen `START.md` (#204). Ab Pipe 1.10 gehen die Statusregeln nur bei Statusfragen an das Modell, ältere Ansichten der Pipe nur noch als je eine Zeile (#285). Einzelheiten: [Open-WebUI-Anleitung](../integrations/openwebui/README.md#darstellung-und-antwortmodus-direkt-pipe-18-werkzeug-15).

## Persönliche Freigaben in den Clients

Vor einer Freigabe muss das tatsächlich angemeldete persönliche GitHub-Konto samt Eigentümer- oder ausdrücklichem Freigaberecht nachgewiesen werden. Ein Anzeigename, `by`, Commit-Autor oder erfolgreicher Speichervorgang genügt dafür nicht. Lokale Arbeitsumgebungen verwenden `scripts/approval_authority.py BUCH actor`; ein automatisierter Actions-Job darf diese persönliche Entscheidung nicht stellvertretend erteilen.

Ohne lokale Laufzeit die tatsächlich verfügbaren authentifizierten GitHub-Werkzeuge verwenden und deren Konto-/Berechtigungsgrenzen offen nennen. Ist diese Prüfung nicht möglich, die Freigabe zurückstellen. Der [persönliche Inhaltsnachweis](SPEICHERN.md#persönliches-freigaberecht-und-inhaltsnachweis) kann mit der lesenden manuellen GitHub-Action vorbereitet und geprüft werden. Entwürfe und Probedrucke bleiben möglich.

Open WebUI benötigt GitHub-Werkzeug 1.8.0 mit persönlichen Benutzer-Valves für Schreibaktionen. Die Claude-Web-App muss den neuen Prüf- und Nachweisablauf in Claude übernehmen; eine ältere App darf einen gespeicherten technischen Status nicht als persönlich verifizierte Freigabe ausgeben. Die praktische Abnahme bleibt für jeden Client separat erforderlich.


---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
