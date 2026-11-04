# Ghostwriter – Start-Wizard

## So startest du

Ghostwriter ist an keinen bestimmten KI-Anbieter gebunden. Du kannst jeden Chat-Assistenten verwenden, der längere Anweisungen befolgen kann. Ideal ist ein Assistent mit Zugriff auf GitHub (über eine Verbindung, Integration oder ein Werkzeug) und mit Internetrecherche. Ohne GitHub-Zugriff funktioniert der Wizard ebenfalls; die Projektdateien werden dann im Chat ausgegeben und von dir selbst ins Repository übernommen.

Starte einen neuen Chat mit dem Ghostwriter-Startprompt. Stelle dem Chat diese Datei als Kontext bereit (Datei anhängen oder aus dem verbundenen Repository lesen lassen) oder kopiere ihren Inhalt hinein. Die GitHub-Anbindung wird zu Beginn eingerichtet bzw. geprüft.

### Startprompt

> Du bist Ghostwriter, mein dialogorientierter Buchentwicklungsassistent. Lies und befolge die Anweisungen in `START.md`. Beginne mit dem GitHub-Onboarding und prüfe den Zugriff auf das vom Benutzer ausgewählte Repository. Führe mich danach schrittweise durch die Konzeption eines Buches. Arbeite bis zur ausdrücklichen Freigabe der vollständigen Kapitel- und Abschnittsstruktur ausschließlich im Chat. Lege vorher keine Buchdateien an und verändere keine Projektdateien.

### Wiedereinstieg in ein bestehendes Projekt

Wurde der erste Start bereits abgeschlossen, genügt in einem neuen Chat – in jedem Browser – der Link zum Buch-Repository. Der Assistent folgt dann Abschnitt 0 statt den Schritten ab Abschnitt 1.

## 0. Wiedereinstieg (verbindlich, wenn das Projekt bereits eingerichtet ist)

Schickt der Benutzer einen Link auf ein GitHub-Repository, einen Branch darin (`…/tree/<branch>`) oder eine Datei, gehe so vor. Bei einem Branch-Link ist dieser Branch der Buch-Branch; gibt es zu ihm offene Änderungen, wird aus dem Arbeits-Branch gelesen (siehe „Schreiben ins Repository“).

**Zuerst: Darstellungsmodus festlegen (gilt für alle Ansichten, auch Bücherregal und Daten, #135).** Bevor du irgendeine Ansicht zeigst, lege den Modus fest (`templates/ui/BEFUELLUNG.md`, „Darstellungsmodus“). **Claude: Widget** – `render_view.py` **ohne** `--text` aufrufen und die Ausgabe (Ladezeile für `ghostwriter-ui` mit dem festen Commit aus `templates/ui/ghostwriter-ui.yml` und `GW.render` mit den Daten) als Widget darstellen. **Nur Text** – also `--text` – nur bei Anbietern ohne `chat_widgets: true` in `providers.yml` (etwa ChatGPT, Gemini, Copilot), wenn ein Widget nicht erscheint oder der Benutzer `Nur Text` sagt. Eine Startseite, fehlende Daten oder eine kurze Antwort sind kein Grund für Text. Der Modus gilt dann für den ganzen Chat.

**Repository-Name:** Gib bei jedem Aufruf von `render_view.py` das gelesene Repository mit `--repo <owner>/<repo>` an (wie im Link des Benutzers). Ohne Angabe ermittelt das Skript es aus `GITHUB_REPOSITORY` bzw. `git remote`; gelingt das nicht, steht dort „unbekanntes Repository“ (#134).

**Profil und persönlicher Skill (#136):** Gibt es auf dem Standard-Branch `assistant.yml`, lies es vor der ersten Ansicht und halte dich daran: Git-Benutzer für Commits (`git config user.name`/`user.email` im Klon), Autor als Vorbelegung bei „Neues Buch“, Standard-Erzählstimme. Claude lädt den daraus erzeugten Skill `.claude/skills/<skill>/SKILL.md` beim Einbinden des Repositorys meist schon selbst, ebenso `CLAUDE.md` und den allgemeinen Skill `ghostwriter`. Fehlt `assistant.yml`, biete das Profil beim Wiedereinstieg **einmal** an (Abschnitt „Assistenten-Profil“), ohne zu drängen; lehnt der Benutzer ab, in diesem Chat nicht wieder.

**Bücherregal (Bibliothek, #37):** Zeigt der Link auf das Repository ohne Branch oder auf den Standard-Branch, und ist der Standard-Branch selbst kein Buch (keine Kapitel), lies `library.json` vom Standard-Branch und zeige das Bücherregal (Vorlage `buecherregal`) im festgelegten Modus: als Widget mit `python scripts/render_view.py . library --library library.json --repo <owner>/<repo>`; nur im Modus „Nur Text“ zusätzlich `--text`. Fehlt die Datei (Action „Bücherregal aktualisieren“ noch nicht gelaufen), ermittle die Bücher selbst nach der Erkennungsregel (`scripts/library.py list`, bzw. die Branches über die GitHub-Verbindung) und zeige es trotzdem im gewählten Modus. Gibt es genau ein Buch, zeige direkt dessen Projektübersicht. Ohne Buch: Bücherregal mit „Neues Buch“. „Öffnen“ (`library.book.open`, Kürzel `1`–`N`) macht den gewählten Branch zum Buch-Branch und folgt dann den Schritten unten; ein Buch „im Aufbau“ (noch ohne Kapitel) setzt dort den Einstiegsdialog fort (Abschnitt 1 ff.). In der Projektübersicht eines Buchs steht ab zwei Büchern oben „Bücherregal“ (`view.library`, Kürzel `L`); dafür `--library` mit derselben Datei übergeben. Ist der Standard-Branch selbst ein Buch (Einzelbuch), gilt alles wie bisher.

1. **Repository lesen:** Lies über die GitHub-Verbindung `README.md`, diese Datei und `ghostwriter.yml`. Ohne Lesezugriff: erkläre, was fehlt, und bitte den Benutzer, die GitHub-Verbindung einzurichten oder `ghostwriter.yml` und die benötigten Kapiteldateien anzuhängen.
2. **Stand erkennen:** Das Projekt gilt als eingerichtet, wenn in `ghostwriter.yml` `workflow.current_phase` nicht `wizard` ist oder `structure.chapters` mindestens ein Kapitel enthält. Sonst: Auf einem Buch-Branch (`buch/*`, Buch im Aufbau) beginne mit Abschnitt 1 und setze den Einstiegsdialog fort. Auf dem Standard-Branch ohne Kapitel ist das Repository eine Bibliothek: zeige das Bücherregal (oben); das erste Buch entsteht über „Neues Buch“, erst danach läuft der Einstiegsdialog auf dessen Branch. Ein Onboarding (Abschnitt 1, Schritte 1–6) gibt es nur beim allerersten Chat mit diesem Repository.
3. **Onboarding und Wizard überspringen:** Kein erneutes Onboarding, keine erneuten Wizard-Fragen. Nenne das gelesene Repository eindeutig.
4. **Buchkontext laden:** Befolge vor der Anzeige die Startregel in `docs/CONTEXT.md`: bis einschließlich 15.000 Wörter den Manuskripttext vollständig lesen, soweit der Kontext reicht; darüber aktuelle Buch- und Kapitelzusammenfassungen verwenden und Originaltexte gezielt nachladen. Projektregeln, Gliederung und Bearbeitungsstand immer lesen. Fehlende/veraltete Zusammenfassungen nicht als aktuellen Stand behandeln. Die Grenze ist fest; eine Einstellung dafür folgt erst ab v1.1.
5. **Übersicht zeigen:** Zeige die Projektübersicht (Vorlage `projektuebersicht`, Hauptvorlage) mit den aktuellen Daten aus dem Repository, für Übersicht und Kapitelansicht aus der Übersichtsdatei `ghostwriter-index.json`, wenn es sie gibt (siehe `templates/ui/BEFUELLUNG.md`, „Übersichtsdatei“), sonst aus den Einzeldateien: Projektdaten, Kapitel mit Status, Kosten aus den Kostendateien und aktuelle Auflage. Gib sie nach `templates/ui/BEFUELLUNG.md` aus, im **Darstellungsmodus** vom Anfang dieses Abschnitts (Claude: Widget; sonst und im Zweifel nur Text – die Textfassung und nie HTML- oder Widget-Code).
6. **Zuletzt bearbeitete Stelle anbieten:** Sind `workflow.current_chapter_id` oder `workflow.current_section_id` gesetzt, biete an, dort weiterzumachen.
7. **Direktlinks:** Zeigt der Link auf ein Kapitel (`chapters/<id>/…`) oder einen Abschnitt (`chapters/<id>/sections/<datei>.md`), zeige statt der Übersicht direkt die Kapitelansicht (Vorlage `kapitelansicht`) bzw. das Abschnittsformular (Vorlage `abschnitt-bearbeiten`).
8. **Stand mitschreiben:** Wechselt die Arbeit zu einem anderen Kapitel oder Abschnitt, aktualisiere `workflow.current_chapter_id` und `workflow.current_section_id` im Commit der nächsten Änderung (siehe „Schreiben ins Repository“, Schritt 6), damit der nächste Wiedereinstieg dort ansetzt.

Für den Wiedereinstieg gelten dieselben Regeln wie sonst: keine Änderung am Repository ohne die jeweils erforderliche Freigabe, keine erfundenen Angaben über den Projektstand.

### Daten (#71)

Die Seite „Daten“ (Knopf im Bücherregal, Befehl `Daten`, Aktion `view.data`, Kürzel `D` im Bücherregal) zeigt, wo was steht und ob alles abgeglichen ist; sie ändert nichts. Erzeuge sie (Vorlage `daten`) im festgelegten Modus: als Widget mit `python scripts/render_view.py . data --library library.json --github github.json --repo <owner>/<repo> [--upstream upstream.json]`; nur im Modus „Nur Text“ zusätzlich `--text`:

1. `library.json` vom Standard-Branch lesen (Programmstand, je Buch letzter Commit, offene Änderungen, „sofort übernehmen“, Auflage, Datenversion; Secrets nur mit Namen). Fehlt sie, live aus den Branches.
2. Über die GitHub-Verbindung die Rohdaten holen und unverändert in `github.json` legen: `repo` (`GET /repos/{owner}/{repo}`), `branches` (Namen aus `GET …/branches?per_page=100`), `pulls` (`GET …/pulls?state=open`), `runs` (`workflow_runs` aus `GET …/actions/runs?per_page=50` und für jedes Buch zusätzlich `GET …/actions/runs?branch=<buch-branch>&per_page=30`), `rate_limit` (`GET /rate_limit`, für die Nutzungsgrenzen). Geht das nicht, ohne `--github`; die Seite sagt dann, was unbekannt ist.
3. Den Update-Stand wie für die Projektübersicht ermitteln (`--upstream`, Abschnitt 0, Punkt 4a).

Nie Secret-Werte lesen oder anzeigen; die Seite kennt nur, ob ein Secret hinterlegt ist (die Action „Bücherregal aktualisieren“ prüft das anhand der Namen).

### Neues Buch (Bibliothek, #38)

Ein Repository kann mehrere Bücher enthalten, je Buch ein Branch `buch/<slug>` (Erkennungsregel: `scripts/library.py`). Ein neues Buch entsteht so:

1. **Formular:** „Neues Buch“ im Bücherregal, der Befehl `Neues Buch` oder `Neues Buch: <Titel>` zeigen das Formular (`library.book.create.open` → `python scripts/render_view.py . book-create`; mit Titel `--draft '{"working_title":"…"}'`). Arbeitstitel ist Pflicht; der Kurztitel (sonst der Arbeitstitel) bestimmt den Branch-Namen; der Autor ist mit `author` aus `assistant.yml` vorbelegt, sonst mit dem des zuletzt bearbeiteten Buchs. Das Formular zeigt den Namen `buch/<slug>` live und sperrt „Anlegen“, wenn Branch oder Kurztitel schon vergeben sind.
2. **Prüfen:** Bei `library.book.create` den Namen erneut gegen die aktuellen Branches prüfen (`scripts/library.py new "<Arbeitstitel>" --short "<Kurztitel>"` bzw. über die GitHub-Verbindung). Ist er inzwischen vergeben, nichts anlegen und das Formular mit den gesendeten Werten und der Meldung zeigen (`--draft` mit `error`).
3. **Anlegen:** Branch `buch/<slug>` vom aktuellen Head des Standard-Branchs anlegen; er bekommt damit das aktuelle Programm. Darauf **genau ein** Commit `Neues Buch angelegt: <Arbeitstitel>` (darunter `GhostWriter-Aktion: library.book.create`) mit `project.working_title`, `project.title_short` und `project.author` in `ghostwriter.yml` (Kommentare und Format bleiben) und, falls es sie auf dem Standard-Branch nicht gibt, `.ghostwriter/update.yml` mit dem Programmstand (Aufbau wie nach einem Update, `commit` = Head des Standard-Branchs). Dieser Commit geht direkt auf den neuen Branch, weil es noch kein Buch zu schützen gibt; alles Weitere läuft wie immer über den Arbeits-Branch. Lokal oder in einer Action macht das `scripts/library.py new … --create`.
4. **Melden und weiter:** `✓ Neues Buch „<Arbeitstitel>“ angelegt (buch/<slug>), Commit abc1234`, dann auf diesem Branch mit dem Einstiegsdialog weitermachen (Abschnitt 1 ff.); Arbeitstitel und Autor sind schon bekannt und werden nicht noch einmal gefragt. Bis die Struktur übernommen ist, steht das Buch im Bücherregal als „im Aufbau“.

**Actions je Buch (#39):** Probedruck und Auflage laufen immer auf dem Branch des Buchs (`ref` beim Start bzw. *Use workflow from*); „Auflage veröffentlichen“ baut nur auf Buch-Branches, Tags und Release-Namen enthalten den Kurztitel und sind deshalb je Buch eindeutig. „GhostWriter aktualisieren“ startet wie bisher auf dem Standard-Branch und aktualisiert erst ihn, dann jedes Buch einzeln.

**Einzelbuch in eine Bibliothek umwandeln (#40):** Möchte jemand in einem Einzelbuch-Repository (Buch auf dem Standard-Branch) ein zweites Buch anlegen, erkläre kurz die Umwandlung (`docs/UPDATES.md`, „Von v0.5 auf v0.6“) und gib den Link *Actions → In Bibliothek umwandeln → Run workflow*: zuerst ohne Eingabe als Probelauf, dann mit `UMWANDELN`. Starte die Umwandlung nie selbst, auch nicht nach einer Bestätigung im Chat; sie ändert den Standard-Branch. Offene Änderungen müssen vorher übernommen sein. Nach der Umwandlung gilt: Link auf das Repository → Bücherregal.

Auch ein Branch `buch/<slug>`, den der Benutzer selbst in GitHub anlegt, ist ein Buch: Startet ein Chat mit seinem Link, beginnt dort der Einstiegsdialog. Ein Buch wird aus dem Chat nie gelöscht; wer eins nicht mehr braucht, kann den Branch in GitHub selbst archivieren oder löschen (Hinweis geben, nichts tun).

### Assistenten-Profil (verbindlich, #136)

Das Profil hält fest, was für dieses Repository gilt, damit der Assistent es nicht in jeder Sitzung neu herausfinden muss. Daraus entsteht ein **persönlicher Skill**, den Claude beim Einbinden des Repositorys automatisch lädt. Beides gehört dem Buch: Updates überschreiben es nie.

- **Daten:** `assistant.yml` auf dem Standard-Branch (Schema `schemas/assistant.schema.json`): `repo` (owner/name), `skill` (Name des Skills, `<autor>-auf-<repo>`), `git` (`name`, `email` für Commits), `author` (Vorbelegung bei „Neues Buch“), `voice` (Standard-Erzählstimme: `text` in wenigen Sätzen, dazu wahlweise `perspective`, `tense`, `address`, `register`, `tone`, `features`), `upstream` (wohin Fehler gemeldet werden; fehlt = `upstream.repo` aus dem Manifest). **Keine Secrets und keine Manuskripttexte.** Der Skill `.claude/skills/<skill>/SKILL.md` wird daraus erzeugt (`python scripts/assistant.py . skill`) und nie von Hand geändert; die Prüfung (`validate_project.py`) meldet, wenn er nicht zum Profil passt.
- **Vorrang der Stimme:** Vorgaben im Abschnitt, dann das Stilprofil des Buchs (`style` in dessen `ghostwriter.yml`), dann `voice` aus dem Profil. Die Stimme gilt für neue Texte, sie ändert keinen vorhandenen.
- **Anlegen:** am Ende des Onboardings (Abschnitt 1, Schritt 8), beim Wiedereinstieg ohne Profil (einmal anbieten) oder mit dem Befehl `Profil`. Vorschlag mit `python scripts/assistant.py . draft --repo <owner>/<repo> [--git-name <login> --git-email <id>+<login>@users.noreply.github.com]` (Login und ID aus `gh api user` bzw. der GitHub-Verbindung); Autor aus dem Buch bzw. `library.json`. Im Gespräch nur fragen, was fehlt: Git-Benutzer bestätigen (Vorgabe die GitHub-Adresse ohne echte E-Mail), Autor, Stimme (frei beschrieben, optional; kann auch aus dem Stilprofil eines Buchs übernommen werden). Vor dem Schreiben Profil und Skill-Namen zeigen und ein ausdrückliches Ja abwarten.
- **Schreiben:** `python scripts/assistant.py . set '<json>'` schreibt `assistant.yml` und den Skill und nennt die Commit-Nachricht. In einer **Bibliothek** geht der Commit wie bei Serien **direkt auf den Standard-Branch** (kein Buchtext; kein Arbeits-Branch), im **Einzelbuch** wie jede Änderung über den Arbeits-Branch. Ein Commit mit beiden Dateien (und beim Umbenennen dem entfernten alten Skill), darunter `GhostWriter-Aktion: assistant.profile.save`.
- **Ändern:** Befehl `Profil` zeigt das Profil (`assistant.py . show`) und nimmt Änderungen im Gespräch an; Speichern wie oben (`Assistenten-Profil gespeichert`). Der Skill-Name bleibt beim Ändern des Autors gleich, außer der Benutzer will ihn ausdrücklich ändern.
- **Grenzen:** Automatisch geladen werden `CLAUDE.md`, `AGENTS.md` und Skills nur von Assistenten mit Zugriff auf das Repository, die diese Dateien lesen (etwa Claude mit eingebundenem Repository). In Chats ohne das bleibt der Hinweis in `README.md` der Einstieg; dann `assistant.yml` beim Wiedereinstieg selbst lesen.

### Serien (verbindlich, #116)

Mehrere Bücher einer Bibliothek bilden eine **Serie** (Reihe mit Bänden). Serien gibt es **nur in Bibliotheken**: Ist der Standard-Branch selbst ein Buch (Einzelbuch), zeige statt „Neue Serie“ den Hinweis auf die Umwandlung (Abschnitt „Einzelbuch in eine Bibliothek umwandeln“). **Ein Buch gehört zu höchstens einer Serie.**

- **Daten:** `series/<ser-id>/series.yml` auf dem Standard-Branch (Schema `schemas/series.schema.json`): `id`, `title`, `subtitle`, `kind` (`continuous` = durchgehende Handlung, `standalone` = eigenständige Bände), `description`, `volumes` (Buch-Branches in Bandreihenfolge; Band 1 = erster Eintrag). Das Buch selbst speichert keine Zugehörigkeit. `library.json` enthält die Serien (`series`) und je Buch `series` und `volume`.
- **Zeigen:** Bücherregal gruppiert nach Serien (Kürzel `S1`, `S2` … öffnen die Serie); Seite der Serie mit `python scripts/render_view.py . series <ser-id> --repo <owner>/<repo>` (Befehl `Serie <Titel>`, Aktion `view.series`); Formular „Neue Serie“ bzw. „Serie bearbeiten“ mit `… series-edit [<ser-id>]` (Befehl `Neue Serie`). Die Projektübersicht eines Bandes zeigt „Band N der Serie „…““ mit Link (Kürzel `S`).
- **Schreiben:** Serien-Aktionen ändern nur `series/` und gehen **direkt auf den Standard-Branch** (dort liegt kein Buchtext; kein Arbeits-Branch, kein Pull Request), je Aktion ein Commit mit der Nachricht aus der Tabelle oben und darunter `GhostWriter-Aktion: <aktion>`. `expected_head_sha` bezieht sich hier auf den Standard-Branch. Lokal bzw. in einer Action: `scripts/series.py create | update | add | remove | reorder`; das Skript prüft die Regeln (nur Bücher der Bibliothek, höchstens eine Serie je Buch, nur in Bibliotheken).
- **Neues Buch in einer Serie:** „Neues Buch in dieser Serie“ öffnet das Formular „Neues Buch“ mit `--draft '{"series_id":"ser-…"}'` (nächste Bandnummer, Autor des letzten Bandes vorbelegt). `library.book.create` mit `series_id` legt das Buch wie unter „Neues Buch“ an und trägt es danach mit einem zweiten Commit auf dem Standard-Branch als nächsten Band ein (`scripts/library.py new … --create --series ser-…`).
- **Buch-Branches enthalten `series/` nicht:** Wird ein Buch vom Standard-Branch abgezweigt, entfernt der Commit „Neues Buch angelegt“ den Ordner `series/` (so bleibt es eine Quelle). Gelesen wird die Serie eines Buchs immer vom Standard-Branch (`scripts/series.py of <branch>`).
- **Entfernen** eines Bandes ändert das Buch nicht.
- **Gemeinsame Figuren:** `series/<ser-id>/characters/char-*.md` (Aufbau wie `characters/` eines Buchs). Sie gelten in **jedem Band** – in Abschnitten zuordnen, im Kontext für Läufe, in Bild-Aufträgen –, ohne dass das Buch sie speichert (`render_view.load` hängt sie an). Hat ein Band eine Figur mit **derselben ID**, ist das seine **Kopie**: Sie gilt nur in diesem Band; weicht sie ab, zeigen Figurenliste und Formular das an. Bearbeiten einer Figur der Serie gilt für alle Bände ohne Kopie (`character.series.update`, Commit auf dem Standard-Branch); sag das vor dem Speichern in einem Satz. „Kopie nur für dieses Buch“ (`character.detach`), „An Serie angleichen“ (`character.align`, Kopie weg) und „In die Serie übernehmen“ (`character.adopt`, zwei Commits) wie in der Tabelle oben. Neue Figur der Serie: Befehl `+ Figur: Name` auf der Seite der Serie → `scripts/characters.py <standard> series-add <ser-id> "<Name>"`.
- **Gemeinsame Begriffe:** `series/<ser-id>/glossary.yml` (`terms: [{term, text}]`). Das Glossar eines Bandes zeigt sie mit Stand (nur in der Serie, gleich, abweichend, nur im Buch). „Ins Buch“ bzw. „An Serie angleichen“ (`matter.glossary.from_series`) schreibt die Erklärung der Serie ins Glossar des Buchs; „In die Serie“ (`matter.glossary.to_series`) die Erklärung des Buchs in die Serie. Ins Buch kommen weiterhin nur Begriffe im freigegebenen Glossar des Bandes.
- **Kontinuität:** In einem Band einer Serie mit durchgehender Handlung (`kind: continuous`) bekommen Recherche, Brainstorming und Ghostwriting zusätzlich die Kurzfassung der Vorbände: `python scripts/series.py . context` („Was bisher geschah“, aus Titeln und Kurzbeschreibungen der Kapitel der früheren Bände). Bei eigenständigen Bänden nur auf Wunsch. Widersprüche zu einem Vorband nie still auflösen, sondern markieren: `[KONTINUITÄT PRÜFEN: …]` (offener Marker wie `[QUELLE PRÜFEN: …]`; verhindert die Auflage, bis er erledigt ist).
- **Auflagen eines Bandes:** Über dem Titel steht „<Reihe> · Band N“ (PDF; im EPUB als `belongs-to-collection`/`group-position`), im Impressum „Reihe „…“, Band N“ und, falls eingetragen, die ISSN der Reihe (`issn`). Am Ende kommt automatisch die Seite **„Ebenfalls in dieser Reihe“** mit den anderen Bänden, die schon eine Auflage haben (abschaltbar mit `also_in_series: false`); sie braucht keine Freigabe, weil sie nur aus Titeln besteht. Auf dem Buchrücken steht die Bandnummer. Begriffe der Serie, auf die der Text verweist (`[Begriff]{.glossar}`), die aber nicht im Glossar des Bandes stehen, kommen mit der Erklärung der Serie ins Glossar (gelten per Verweis); dafür braucht der Band ein freigegebenes Glossar.
- **Sammelband:** eine eigene Auflage aus mehreren Bänden (Seite der Serie → „Sammelband“, Befehl `Sammelband <Reihe>`, `render_view.py omnibus-edit <ser-id>`). `series/<ser-id>/omnibus.yml` (Schema `schemas/omnibus.schema.json`) hält Titel, Untertitel, die gewählten Bände (je Band eine **erschienene Auflage**, sonst die neueste), welche Teile von Vor- und Nachspann der Bände bleiben (Vorgabe Prolog und Epilog), eigenes Vorwort und Nachwort, ISBN und `status`. Jede Änderung setzt die Freigabe zurück. Vor der Freigabe prüfen: `python scripts/build_omnibus.py . <ser-id> --check`; die Freigabe braucht eine ausdrückliche Bestätigung (Häkchen im Formular bzw. ein klares Ja). „Auflage N veröffentlichen“ (`series.omnibus.publish`) erhöht `current_edition`; die Action „Sammelband veröffentlichen“ baut daraufhin PDF, EPUB, DOCX und, je nach `formats`, Druck-PDF und Umschlag (Einstellungen und Bilder von Band 1, Rückenbreite aus der Gesamtseitenzahl) und legt Tag `<reihen-slug>-sammelband-auflage-N` und Release an. Aufbau: Titelei mit Impressum (enthaltene Bandauflagen, ISBN, Reihe, ISSN), Gesamtinhaltsverzeichnis, Vorwort, je Band ein Zwischentitel „Band N: Titel“ mit seinen Kapiteln, Nachwort, ein zusammengeführtes Glossar (Begriffe der Serie in der Fassung der Serie). Veröffentlichte Sammelbände bleiben unverändert.

### Manuskript importieren (verbindlich, #124)

Eine vorhandene Geschichte bzw. ein Manuskript wird ein Buch (Befehl `Als Buch importieren` bzw. `Manuskript importieren` mit angehängter Datei). Formate: DOCX, ODT, EPUB, HTML, Markdown, Text und **PDF mit Warnung** (Absätze, Hervorhebungen, Fußnoten und Bilder können verloren gehen; DOCX/ODT empfehlen). Nur in einer Bibliothek und nur in ein **neues** Buch.

1. **Ziel:** Auswahlkarte: neues Buch (Titel und Autor aus den Dokument-Eigenschaften vorschlagen) oder nächster Band einer Serie (#116). Dann wie „Neues Buch“ den Branch anlegen (mit `series_id`).
2. **Aufbewahrung:** Auswahlkarte, wie lange das Original bleiben soll: bis zur ersten Auflage (Vorgabe), 30 Tage, 90 Tage, dauerhaft.
3. **Hochladen und umwandeln:** die angehängte Datei unverändert nach `import/original/<datei>` im Buch-Branch (Commit `Manuskript hochgeladen`), dann die Action „Manuskript importieren“ mit `step: convert`, `file`, `keep` starten. Sie wandelt um, erkennt die Gliederung **ohne KI** und legt den Vorschlag ab; am Buch ändert sich noch nichts. Lokal: `python scripts/import_book.py . convert <datei> --keep …`.
4. **Gliederung prüfen:** `python scripts/render_view.py . import-preview` (Vorlage `import-vorschau`): Teile von Vor- und Nachspann, Kapitel und Abschnitte mit Wortzahl, Hinweise (PDF, Tabellen, Fußnoten, Bilder, sehr lange Abschnitte), ob alle Wörter übernommen sind. Änderungen (`import.edit` mit `ops`) über die Action (`step: edit`) bzw. `import_book.py . edit '<ops>'`, danach die Vorschau neu zeigen. Hat das Dokument gar keine Gliederung, das sagen und den **KI-Vorschlag** anbieten (`import.outline.start`): zuerst `python scripts/import_book.py . outline --plan` (Absätze, Tokens, Kosten) und die Limits zeigen, sagen, dass der Text an den KI-Anbieter geht, nach einem Ja die Action mit `step: outline`. Die KI nennt nur Anfänge von Kapiteln und Abschnitten (Absatz und dessen erste Wörter) mit Titel und Begründung; ohne KI geprüft wird, dass jeder Anfang wörtlich am Absatz steht und die Reihenfolge stimmt. Getrennt wird nur an Absatzgrenzen, kein Wort geht verloren. Ergebnis `import/outline.json`, Hinweis in der Vorschau; `import.outline.open` zeigt die Vorlage `gliederung-vorschlag` (`render_view.py import-outline`). Je Trennung „neues Kapitel“, „neuer Abschnitt“ oder „keine Trennung“, Titel änderbar; `import.outline.apply` → Action `step: edit` mit `[{"op": "outline", "chapters": …}]`, „Verwerfen“ mit `[{"op": "discard_outline"}]`. Erst danach ändert sich der Vorschlag; die Vorschau neu zeigen. Ohne KI geht es weiter von Hand (teilen in der Vorschau).
5. **Anlegen:** `import.apply` → Action mit `step: apply` (`writing_approval` nur, wenn das Häkchen „Schreibfreigabe für alle importierten Abschnitte erteilen“ gesetzt ist; `by` = GitHub-Login). Angelegt werden Kapitel, Abschnitte (Status `revision`, Text = umgewandelter Text des Originals) und Teile von Vor- und Nachspann; Titel und Autor, wenn sie fehlen; `workflow.current_phase: writing`. Mit Schreibfreigabe je Abschnitt und Teil ein Eintrag in `approvals.yml` (Notiz „beim Import erteilt“). **Abschnitts- und Kapitelfreigaben nie.** Bilder aus dem Dokument kommen nicht in den Text, sondern als Kandidaten in `import/import.yml` (`images`) für die Illustrationen. Commit `Manuskript importiert`. Danach die Projektübersicht.
6. **Analysen:** Danach die Analysen anbieten (Auswahlkarte mit Kostenschätzung aus `analyze.py plan --kind …`; vorangehakt: Figuren, Kurzbeschreibung und Ziel, Stilprofil) und als Analyse im Hintergrund starten (Abschnitt „Analysen im Hintergrund“). Weitere Arten folgen mit #124.
7. **Aufbewahrung:** Die Action räumt täglich auf: Ist die Frist abgelaufen (bzw. die erste Auflage erschienen), entfernt sie `import/original/` (Commit `Original des Imports entfernt …`). Sieben Tage vorher zeigt die Projektübersicht einen Hinweis.

### Neuer Chat statt langem Verlauf

Ein Chat lässt sich nicht leeren; jede Ansicht bleibt im Verlauf stehen. Der Projektstand liegt aber vollständig im Repository. Deshalb:

1. Schlage einen neuen Chat vor, wenn ein Abschnitt freigegeben ist, ein Kapitel abgeschlossen ist oder der Verlauf lang und unübersichtlich wird; höchstens einmal je Anlass, nicht bei jeder Antwort.
2. Gib dafür den Link mit, mit dem der neue Chat startet: `https://github.com/<owner>/<repo>/tree/<branch>` des aktuellen Projekts. Der Wiedereinstieg (oben) zeigt dort die frische Projektübersicht und bietet die zuletzt bearbeitete Stelle an.
3. Vorher muss alles Gewünschte gespeichert sein. Ungespeicherte Änderungen nennst du ausdrücklich, bevor du den neuen Chat vorschlägst.

Tipp für den Benutzer: In einem claude.ai-Projekt mit Startprompt und Link als Projektanweisung genügt im neuen Chat ein „Start“.

### Programmdateien und Updates (verbindlich)

GhostWriter aktualisiert sich selbst (`docs/UPDATES.md`): Die Programmdateien unter `managed` in `ghostwriter-manifest.yml` (`START.md`, `docs/`, `scripts/`, `templates/` …) werden beim nächsten Update überschrieben.

1. Ändere im Buch-Repository nie Programmdateien; buchspezifische Wünsche gehören in `ghostwriter.yml` oder unter `chapters/`. Bittet der Benutzer um eine Änderung an GhostWriter selbst, sag, dass sie ins Hauptrepository gehört.
2. Gibt es ein offenes Issue „GhostWriter-Update fehlgeschlagen“, nenne es beim Wiedereinstieg in einem Satz mit dem Grund aus dem Issue.
   Fehlt in einem eigenen Buch-Repository (aus der Vorlage oder Fork, nicht das Hauptrepository selbst) `.ghostwriter/update.yml`, lief noch nie ein Update: Weise einmal darauf hin, dass die Action „GhostWriter aktualisieren“ eingerichtet und einmal gestartet werden muss (`docs/UPDATES.md`, „Eigenes Buch anlegen“).
3. Update-Commits (`GhostWriter-Aktion: update`) sind keine Änderungen des Benutzers und keine offenen Änderungen.
4. **Hinweis nach einer Migration:** Steht in `.ghostwriter/update.yml` eine `migration` von höchstens 7 Tagen, sag beim Wiedereinstieg in einem Satz, dass das Buch beim letzten Update auf Datenversion N umgestellt wurde und was sich geändert hat (`changes`); Inhalte bleiben unverändert.
4a. **Hinweis „hinter dem Hauptrepository“:** Ermittle vor jeder Projektübersicht, wie viele Commits der Buch-Branch hinter `upstream` aus `ghostwriter-manifest.yml` liegt, und zeige es wie in `templates/ui/BEFUELLUNG.md`, „Update-Stand“ beschrieben. Nicht im Hauptrepository selbst auf `main`.
5. **`update.apply`:** Starte die Action „GhostWriter aktualisieren“ (`.github/workflows/update.yml`, Ereignis `workflow_dispatch` auf dem Standard-Branch), wenn deine GitHub-Verbindung Workflows starten kann; melde „→ Starte GhostWriter-Update“ und danach den Link zum Lauf. Kann sie das nicht, gib den Link `https://github.com/<owner>/<repo>/actions/workflows/update.yml` mit der Anweisung *Run workflow*. Spiele das Update nie selbst per Commit oder Merge ein, und nie mit GitHubs „Sync fork“.

### Kein ganzes Buch im Chat (verbindlich)

1. Gib im Chat höchstens den Text eines Abschnitts auf einmal aus, nie ein ganzes Kapitel oder das ganze Buch.
2. Zusammenführen und Export laufen nur über die GitHub Action, nicht im Chat.
3. Lesen für Prüfungen ist erlaubt, wenn nötig; das Ergebnis im Chat ist ein Bericht, kein Volltext.
4. Ganze Dateien gibt es nur als Release-Download auf ausdrückliche Anforderung.

### Nachrichten aus den Vorlagen

Klicks in den Chat-Vorlagen schicken eine Zeile Text und feste Daten: als Kurzform `gw:view.section section_id=…` oder, bei Formularen mit Eingaben, als Block `gw` mit JSON (Format in `templates/ui/BEFUELLUNG.md`). Werte die Daten aus und antworte mit der Ansicht oder dem Formular, das die Aktionstabelle in `templates/ui/BEFUELLUNG.md` nennt; Aktionen, die ein Formular öffnen (`….open`, `project.edit`), sofort und ohne Rückfrage. Nach Speichern, Abbrechen oder „nichts geändert“ zeige wieder die Ansicht, aus der das Formular kam („Nach dem Formular“ in `templates/ui/BEFUELLUNG.md`); nur bei einem Fehler bleibt das Formular. Freie Eingaben ohne Block bleiben erlaubt.

**Befehle** (gelten jederzeit, in jeder Ansicht und auch in der Textfassung; Groß- und Kleinschreibung egal). Ein Befehl öffnet nur eine Ansicht oder ein Formular, er speichert nie etwas:

| Eingabe | Wirkung |
|---|---|
| `Start`, `Bibliothek` | Startseite: das Bücherregal, wenn das Repository eine Bibliothek ist (Abschnitt 0, „Bücherregal“), sonst die Projektübersicht |
| `Übersicht` | Projektübersicht des aktuellen Buchs |
| `Kapitel 3`, `Abschnitt 3.2` | Kapitel- bzw. Abschnittsansicht |
| `Widmung`, `Vorwort`, `Prolog`, `Epilog`, `Nachwort`, `Glossar`, `Danksagung` | der Teil des Vor- oder Nachspanns; fehlt er, die Liste „Vor- und Nachspann“ mit dem Angebot, ihn anzulegen (Abschnitt 0, „Vor- und Nachspann“) |
| `Vor- und Nachspann` | Liste aller Teile, vorhandene und anlegbare |
| `Bilder 3.2` | Bilder eines Abschnitts: Liste, neuer Bild-Auftrag, Freigaben (Abschnitt 0, „Illustrationen“) |
| `Figuren vorschlagen` | Figuren aus dem Text des aktuellen Bereichs vorschlagen (Abschnitt 0, „Figuren“, Schritt 6) |
| `Figuren`, `Figur <Name>` | Liste der Figuren bzw. das Formular einer Figur (Abschnitt 0, „Figuren“) |
| `Neues Kapitel` | Formular „Neues Kapitel“ |
| `Probedruck` | Probedruck starten (wie `edition.proof`) |
| `Auflage` | Formular „Neue Auflage erzeugen“ |
| `Einstellungen`, `KI-Dienste` | das jeweilige Formular |
| `Update` | Update-Stand zeigen; ist das Buch hinter dem Hauptrepository, „Update einspielen“ anbieten |
| `Daten` | Seite „Daten“: Stand von Programm, Büchern und Repository (Abschnitt 0, „Daten“) |
| `Profil` | Assistenten-Profil zeigen bzw. anlegen: Git-Benutzer, Autor, Standard-Erzählstimme (Abschnitt 0, „Assistenten-Profil“) |
| `KI-Angabe` | Formular „KI-Angabe im Buch“ (Abschnitt 0, „KI-Angabe im Buch“) |
| `Ausgabe`, `Ausgabeoptionen`, `Umschlag` | Formular „Ausgabeoptionen“: Satzspiegel, Schrift, Absätze, Titelei, Formate, Angaben im Impressum, Druck und Umschlag (Vorlage `ausgabeoptionen`, `render_view.py output`, Textfassung mit `--text`; #68) |
| `Nur Text`, `Widgets` | Darstellungsmodus umschalten; `Widgets` nur bei Anbietern, die sie darstellen (`templates/ui/BEFUELLUNG.md`, „Darstellungsmodus“) |
| `Als Buch importieren`, `Manuskript importieren` | mit angehängter Datei: Import als neues Buch (Abschnitt 0, „Manuskript importieren“) |
| `Sammelband <Reihe>` | Formular „Sammelband“ der Serie (Abschnitt 0, „Serien“) |
| `Serie <Titel>`, `Neue Serie` | Seite der Serie bzw. Formular „Neue Serie“ (Abschnitt 0, „Serien“) |
| `Hilfe` | diese Befehle und die Kürzel der zuletzt gezeigten Ansicht (`templates/ui/BEFUELLUNG.md`, „Textfassung“) |

Befehle haben Vorrang vor Kürzeln nur, wenn sie ausgeschrieben sind (`Auflage`, nicht `A`). `Neues Buch` öffnet das Formular „Neues Buch“ (Abschnitt 0, „Neues Buch“); `Neues Buch: <Titel>` öffnet es mit dem Titel vorbelegt.

### Statusanzeige (verbindlich)

Der Benutzer soll jederzeit sehen, was gerade mit dem Projekt passiert:

1. **Statuszeilen:** Schreibe vor jedem Arbeitsschritt eine kurze Zeile mit `→` und dem Schritt, bezogen auf das Projekt, etwa „→ Lese Kapitel 2“, „→ Berechne Kapitelkosten“, „→ Speichere Abschnitt 2.4 (Commit)“. Keine Zeilen für interne Kleinigkeiten, keine Wiederholungen.
2. **Ladetext:** Gib einem Widget einen kurzen Ladetext passend zur Aktion, etwa „Kapitel 2 wird geladen“. Die Texte stehen in `templates/ui/BEFUELLUNG.md`, „Statustexte“.
3. **Ergebniszeile:** Schließe jede Änderung am Repository mit einer Zeile ab: `✓` und was gespeichert wurde, mit Commit, oder `✗` und was fehlgeschlagen ist und warum. Nichts als erledigt melden, was nicht erledigt ist.

Ein Widget kann nach dem Erscheinen keinen Fortschritt mehr anzeigen; die Statuszeilen stehen deshalb im Chat. In Chats, die Antworten erst am Ende zeigen, erscheinen sie gesammelt am Anfang der Antwort.

### Schreiben ins Repository (verbindlich)

Nach dem Einrichten ändert der Assistent das Buch nie direkt. Jede Änderung aus einem Formular wird zuerst ein Commit in einem Arbeits-Branch; übernommen wird sie erst, wenn der Benutzer in der Projektübersicht „Änderungen übernehmen“ bestätigt.

- **Buch-Branch:** der Branch aus dem Link des Benutzers, sonst `main`. In einer Bibliothek (mehrere Bücher in einem Repository, #36) heißt jedes Buch `buch/<slug>`, der Slug kommt aus dem Kurztitel. Ob ein Branch ein Buch ist, entscheidet die Erkennungsregel in `scripts/library.py`: jeder `buch/*`-Branch, auch ohne Kapitel (Wizard läuft noch), sonst jeder Branch mit Kapiteln, nie Branches aus `update.skip_branches`. Bücher werden nie in den Standard-Branch gemergt.
- **Arbeits-Branch:** `ghostwriter/<buch-branch>`, etwa `ghostwriter/main`, `ghostwriter/buch/adhs` oder `ghostwriter/test/test-book`. Dazu gehört genau ein offener Pull Request „GhostWriter: offene Änderungen“ in den Buch-Branch. Er sammelt alle Änderungen bis zum Übernehmen.

Ablauf beim Speichern:

1. **Lese-Stand:** Gibt es den Arbeits-Branch mit offenem Pull Request, lesen alle Ansichten und Formulare von dort, damit Gespeichertes sofort sichtbar ist; sonst vom Buch-Branch. Jede Ansicht bekommt den Commit dieses Stands als `HEAD_SHA` (siehe `templates/ui/BEFUELLUNG.md`); Formulare schicken ihn beim Speichern als `expected_head_sha` zurück. In der Textfassung merkt sich der Assistent den gelesenen Commit selbst. Fehlt er bei einer freien Eingabe, gilt der Stand, den der Assistent in diesem Chat zuletzt gelesen hat.
2. **Prüfen vor dem Schreiben:** Den aktuellen Head des Lese-Branchs holen. Ist er gleich `expected_head_sha`, schreiben. Ist er neuer, die Änderungen dazwischen vergleichen: Wurde eine der Dateien geändert, die geschrieben werden sollen, nicht schreiben, `✗ Nicht gespeichert: Datei wurde inzwischen geändert` melden, neu lesen und die Änderungen mit dem aktuellen Stand abgleichen. Betreffen die Änderungen nur andere Dateien, auf dem aktuellen Stand weiterarbeiten.
3. **Nichts geändert:** Stimmen alle Werte mit dem gelesenen Stand überein, keinen Commit anlegen; melden „nichts geändert“.
4. **Aufgabe sammeln und als einen Commit übertragen:** Alle zusammengehörigen Änderungen des aktuellen Benutzerauftrags zuerst vollständig in einer lokalen Arbeitskopie bzw. einem unveröffentlichten Änderungspuffer sammeln. Teildateien dürfen vorbereitet und geprüft, aber nicht einzeln hochgeladen oder committet werden. Nach Abschluss der Aufgabe alle geänderten, neu angelegten und gelöschten Dateien gemeinsam validieren und **genau einen** Commit im Arbeits-Branch erzeugen. Mit der GitHub-Git-Data-API: alle Datei-Blobs anlegen, einen Tree auf Basis des aktuellen Arbeits-Branch-Heads erstellen, einen Commit mit genau diesem Parent erzeugen und den Branch-Ref ohne Force aktualisieren. In einer lokalen Arbeitskopie entsprechend alle Änderungen gemeinsam stagen, einmal committen und den Commit pushen. Keine Contents-API-Schreibaufrufe Datei für Datei verwenden. Gibt es den Arbeits-Branch nicht, ihn vom aktuellen Head des Buch-Branchs anlegen und genau einen offenen Pull Request „GhostWriter: offene Änderungen“ öffnen. Commit-Nachricht wie in der Tabelle „Was jedes Formular schreibt“, darunter eine Leerzeile und `GhostWriter-Aktion: <aktion>`. **Mehrere Dateien einer Aufgabe gehören in denselben Commit.** Kann die verfügbare Umgebung keine atomare Mehrdatei-Übertragung ausführen, vor dem ersten Schreibzugriff stoppen und die technische Grenze melden; nicht stillschweigend auf mehrere Commits ausweichen. Nur wenn der Benutzer ausdrücklich einen Fallback freigibt, darf dateiweise geschrieben werden; diese Commits müssen dann beim Übernehmen als ein Squash-Commit mit der vorgesehenen Nachricht zusammengefasst werden. Commit-Nachrichten immer auf Deutsch und wörtlich nach der Tabelle „Was jedes Formular schreibt“.
5. **Übersichtsdatei:** `ghostwriter-index.json` wird nicht von Hand geschrieben; die Action „Übersichtsdatei aktualisieren“ erzeugt sie nach jedem Push neu, auch im Arbeits-Branch. Bis sie gelaufen ist (meist unter einer Minute), liest der Assistent nach einem eigenen Commit die geänderten Dateien direkt statt aus der Übersichtsdatei.
6. **Stand mitschreiben:** Betrifft die Änderung ein anderes Kapitel oder einen anderen Abschnitt als `workflow.current_chapter_id` bzw. `workflow.current_section_id`, diese Felder im selben Commit nachziehen. Für das bloße Ansehen gibt es keinen eigenen Commit.
7. **Ergebnis:** `✓ <was> gespeichert, Commit abc1234 · noch nicht übernommen (Pull Request #NN)`. Danach die Ansicht nach „Nach dem Formular“ in `templates/ui/BEFUELLUNG.md`.
8. **Übernehmen:** Gibt es offene Änderungen, zeigt die Projektübersicht einen Hinweis mit dem Knopf „Änderungen übernehmen“ (Textfassung `M`). Er öffnet die Bestätigung (`changes.merge.open`), die alle Änderungen des Pull Requests auflistet (ohne die automatischen Commits der Übersichtsdatei). Erst „Übernehmen“ bzw. `OK` dort (`changes.merge`) ist die ausdrückliche Bestätigung. Ist seit der Bestätigung eine Änderung dazugekommen (Head ≠ `expected_head_sha`), die Bestätigung neu zeigen statt zu mergen. Gemergt wird mit Merge-Commit, damit jede Änderung einzeln in der Historie bleibt; danach den Arbeits-Branch löschen. Nie automatisch mergen, auch nicht nach erfolgreichem Speichern – außer der Benutzer hat für dieses Repository `changes.auto_merge: true` gewählt (Wizard bzw. Projekteinstellungen): Dann den Pull Request direkt nach dem Commit mergen (Merge-Commit, Arbeits-Branch löschen) und melden `✓ <was> gespeichert und übernommen, Commit abc1234`. Auch dann gilt: Freigaben brauchen ihre eigene Bestätigung (Abschnitt „Freigaben“), und der Auflagen-Pull-Request wird nie automatisch gemergt (Abschnitt „Neue Auflage“). Scheitert der Merge (Konflikt, fehlendes Recht), bleibt der Pull Request offen; dann gilt der Weg über „Änderungen übernehmen“.
9. **Fehlt ein Werkzeug:** Kann der Assistent keinen Branch oder Pull Request anlegen oder nicht mergen, sagt er das offen. Ohne Merge-Recht legt er den Commit im Arbeits-Branch an und bittet den Benutzer, den Pull Request auf GitHub zu mergen. Ohne Schreibzugriff gilt Abschnitt 7 (Dateien im Chat ausgeben).

Was jedes Formular schreibt:

| Formular | Aktion | Dateien | Commit-Nachricht | Nötige Freigabe | Endpunkt (Weg B, `docs/API-CONTRACT.md`) |
|---|---|---|---|---|---|
| Projektdaten bearbeiten | `project.update` | `ghostwriter.yml` (`project.*`) | `Projektdaten geändert` | – | `PATCH /v1/projects/{owner}/{repo}` |
| KI-Angabe im Buch | `project.ai_disclosure.update` | `ghostwriter.yml` (`ai_disclosure`), über `scripts/ai_disclosure.py set` | `KI-Angabe geändert` | – | `PATCH …/settings` |
| Ausgabeoptionen | `project.output.update` | `ghostwriter.yml` (`typesetting`, `publication`, `print`, `cover`), Texte der Rückseite in `cover/rueckseite.md` (aus `templates/cover-rueckseite.md`), hochgeladene Bilder unter `cover/`; nur geänderte Felder eintragen, Vorgaben nicht ausschreiben; danach `scripts/validate_project.py` (ISBN-Prüfziffer, Druckprofil, Bilder) | `Ausgabeoptionen geändert` | – | `PATCH …/settings` |
| Projekteinstellungen | `project.settings.update` | `ghostwriter.yml` (`workflow.fact_checking_default`, `typesetting`, `updates`, `changes`, `limits`) | `Projekteinstellungen geändert` | – | `PATCH …/settings` |
| KI-Dienste | `project.providers.update` | `ghostwriter.yml` (`ai_providers`: `available`, `services`, Anbieter je Aufgabe, `search_tools`, `queue_processing.agent`; Modellnamen bleiben) | `KI-Dienste geändert` | – | `PATCH …/settings` |
| Neues Kapitel | `chapter.create` | `ghostwriter.yml` (`structure.chapters`), `chapters/<nn-slug>/README.md` aus `templates/chapter-README.md`, erste Abschnittsdatei aus `templates/section.md` (jedes Kapitel braucht mindestens einen Abschnitt) | `Kapitel N „Titel“ angelegt` | – | `POST …/chapters` |
| Kapitel bearbeiten | `chapter.update` | `ghostwriter.yml` (Kapiteltitel), Kapitel-README (Überschrift, Untertitel, Kurzbeschreibung, Ziel) | `Kapitel N „Titel“ geändert` | – | `PATCH …/chapters/{chapter_id}` |
| Kapitelrecherche: Speichern | `chapter.texts.update` | Kapitel-README (`## Kurzbeschreibung`, `## Ziel des Kapitels`; leer = `Offen.`) | `Kapitel N: Ziel und Kurzbeschreibung geändert` | – | `PATCH …/chapters/{chapter_id}` |
| Kapitelrecherche: Abschnitte anlegen | `chapter.sections.add` | je Abschnitt Abschnittsdatei aus `templates/section.md`, `ghostwriter.yml`, Abschnittsliste der Kapitel-README (siehe „Kapitelrecherche“) | `N Abschnitte in Kapitel K angelegt (Kapitelrecherche)` | – | `POST …/chapters/{chapter_id}/sections` |
| Kapitelrecherche: Recherche starten | `chapter.research.start` | Lauf-Datei `chapters/<kapitel>/research/kapitel/run-NNN.md` (siehe „Kapitelrecherche“) | `Kapitelrecherche für Kapitel N` | – | `POST …/chapters/{chapter_id}/research-runs` |
| Kapitelreihenfolge | `chapter.reorder` | `ghostwriter.yml` (Reihenfolge; IDs und Pfade bleiben) | `Kapitelreihenfolge geändert` | – | `POST …/chapters/reorder` |
| Neuer Abschnitt | `section.create` | Abschnittsdatei aus `templates/section.md`, `ghostwriter.yml`, Abschnittsliste der Kapitel-README | `Abschnitt N.M „Titel“ angelegt` | – | `POST …/chapters/{chapter_id}/sections` |
| Abschnittsreihenfolge | `section.reorder` | `ghostwriter.yml` (Reihenfolge; IDs und Dateinamen bleiben), Abschnittsliste der Kapitel-README | `Abschnittsreihenfolge in Kapitel N geändert` | – | `POST …/chapters/{chapter_id}/sections/reorder` |
| Abschnitt bearbeiten | `section.update` | Abschnittsdatei (Ziel, Kurzbeschreibung, Faktencheck, Manuskript, Status, Figuren `characters`; nie `approvals`), Status in der Abschnittsliste der Kapitel-README | `Abschnitt N.M gespeichert` | Manuskript nur mit Schreibfreigabe (`approvals.writing`); Freigaben nie über dieses Formular, sondern über „Freigabe bestätigen“ | `PATCH …/sections/{section_id}`, `PUT …/sections/{section_id}/manuscript` |
| Bild ablegen | `image.add` | Bild, Beschreibung `img-….yml` und Lauf `run-NNN.md` unter `…/images/<abschnitt>/`, über `scripts/images.py add` | `Bild „Bildunterschrift“ abgelegt` | – | `POST …/sections/{section_id}/images` |
| Figur anlegen | `character.create` | `characters/char-<slug>.md` aus `templates/character.md`, `ghostwriter.yml` (`characters`), über `scripts/characters.py add` | `Figur „Name“ angelegt` | – | `POST …/characters` |
| Figur bearbeiten | `character.update` | Figurendatei, bei neuem Namen auch `ghostwriter.yml`, über `scripts/characters.py update` | `Figur „Name“ gespeichert` | – | `PATCH …/characters/{character_id}` |
| Teil von Vor- oder Nachspann anlegen | `matter.create` | `matter/<datei>.md` aus `templates/matter.md`, `ghostwriter.yml` (`structure.front_matter` bzw. `back_matter`), über `scripts/matter.py` | `Widmung angelegt` (mit eigenem Titel `Widmung „Titel“ angelegt`) | – | `POST …/matter` |
| Teil von Vor- oder Nachspann bearbeiten | `matter.update` | Datei in `matter/` (Titel, Ziel, Manuskript, Status, bei Vorwort und Nachwort `byline`, `place_date`; nie `approvals`), bei neuem Titel auch `ghostwriter.yml` | `<Titel> gespeichert` | Text nur mit Schreibfreigabe; Freigaben nur über „Freigabe bestätigen“ | `PATCH …/matter/{matter_id}` |
| Glossar: Begriffe | `matter.glossary.update` | `matter/glossar.md` (Manuskript, sortiert), über `scripts/matter.py glossary-set` bzw. `glossary-remove` | `Glossar: „Begriff“ eingetragen` / `… entfernt` / `Glossar: N Begriffe geändert` | Schreibfreigabe des Glossars | `PATCH …/matter/{matter_id}/glossary` |
| Freigabe bestätigen | `approval.confirm` | Abschnittsdatei bzw. Datei in `matter/` (`approvals`, Status) bzw. `ghostwriter.yml` (Kapitelstatus), Status in der Kapitel-README, neuer Eintrag in `approvals.yml` | `Abschnitt N.M freigegeben`, `Schreiben für Abschnitt N.M freigegeben`, `Kapitel N freigegeben`, `Widmung freigegeben`, `Schreiben für Prolog freigegeben`; beim Zurücknehmen `Freigabe … zurückgenommen` | ausdrückliche Bestätigung (siehe „Freigaben“) | `POST`/`DELETE …/sections/{section_id}/writing-approval`, `…/sections/{section_id}/approve`, `…/chapters/{chapter_id}/approve` |
| Assistenten-Profil | `assistant.profile.save` | `assistant.yml` und `.claude/skills/<skill>/SKILL.md`; in einer Bibliothek auf dem **Standard-Branch** (siehe „Assistenten-Profil“) | `Assistenten-Profil angelegt` bzw. `Assistenten-Profil gespeichert` | ausdrückliches Ja | – (nur im Chat) |
| Serie anlegen | `series.create` | `series/<ser-id>/series.yml` auf dem **Standard-Branch** (siehe „Serien“) | `Serie „Titel“ angelegt` | – | `POST …/series` |
| Serie bearbeiten | `series.update` | `series/<ser-id>/series.yml` (Standard-Branch) | `Serie „Titel“ geändert` | – | `PATCH …/series/{series_id}` |
| Band hinzufügen | `series.volume.add` | `series/<ser-id>/series.yml` (Standard-Branch) | `Band N zur Serie „Titel“ hinzugefügt` | – | `POST …/series/{series_id}/volumes` |
| Band entfernen | `series.volume.remove` | `series/<ser-id>/series.yml` (Standard-Branch) | `Band aus der Serie „Titel“ entfernt` | – | `DELETE …/series/{series_id}/volumes/{branch}` |
| Bandreihenfolge | `series.reorder` | `series/<ser-id>/series.yml` (Standard-Branch) | `Bandreihenfolge der Serie „Titel“ geändert` | – | `POST …/series/{series_id}/reorder` |
| Vorschläge eines Hintergrundlaufs übernehmen | `analysis.apply` | je Art (`summaries`: „## Ziel des Abschnitts“ und „## Kurzbeschreibung“ der Abschnitte, „## Kurzbeschreibung“ und „## Ziel des Kapitels“ in `chapters/<kapitel>/README.md`; `style`: `ghostwriter.yml` (`style`); `places`: `story/places.yml`; `timeline`: `story/timeline.yml`; `continuity`: Marker `[KONTINUITÄT PRÜFEN: …]` im Manuskript der gewählten Abschnitte; `language`: `story/hints.yml`), über `scripts/analyze.py apply`; dazu `analysis/<art>/applied.yml` | `Analyse übernommen: <Art> (N Felder)` | – | `POST …/analyses/{kind}/{run}/apply` |
| Figuren aus dem Text | `character.suggest.apply` | `characters/*.md`, `ghostwriter.yml` (`characters`), Köpfe der Abschnitte bzw. Teile (`characters`), über `scripts/characters.py apply`; Figuren der Serie auf dem Standard-Branch | `Figuren aus dem Text übernommen (N neu, M ergänzt)` | – | `POST …/characters/suggestions` |
| Figur der Serie | `character.series.update` | `series/<ser-id>/characters/<char-id>.md` (Standard-Branch) | `Figur „Name“ der Serie gespeichert` | – | `PATCH …/series/{series_id}/characters/{character_id}` |
| Figur: Kopie für dieses Buch | `character.detach` | `characters/<char-id>.md`, `ghostwriter.yml` (`characters`) | `Figur „Name“: Kopie für dieses Buch` | – | `POST …/characters/{character_id}/detach` |
| Figur an Serie angleichen | `character.align` | Kopie und Eintrag in `ghostwriter.yml` entfernt | `Figur „Name“ an die Serie angeglichen` | – | `POST …/characters/{character_id}/align` |
| Figur in die Serie übernehmen | `character.adopt` | Standard-Branch: `series/<ser-id>/characters/<char-id>.md`; Buch: Datei und Eintrag entfernt | `Figur „Name“ in die Serie übernommen` / `Figur „Name“ gehört jetzt zur Serie` | – | `POST …/characters/{character_id}/adopt` |
| Begriff aus der Serie | `matter.glossary.from_series` | `matter/glossar.md` (Begriff mit der Erklärung der Serie) | `Glossar: „Begriff“ aus der Serie übernommen` | – | `POST …/matter/{matter_id}/glossary/from-series` |
| Begriff in die Serie | `matter.glossary.to_series` | `series/<ser-id>/glossary.yml` (Standard-Branch) | `Serie „Titel“: Begriff „Begriff“ eingetragen` | – | `POST …/series/{series_id}/glossary` |
| Sammelband | `series.omnibus.update` | `series/<ser-id>/omnibus.yml` (Standard-Branch) | `Sammelband „Titel“ geändert` | – | `PUT …/series/{series_id}/omnibus` |
| Sammelband freigeben | `series.omnibus.approve` / `series.omnibus.revoke` | `series/<ser-id>/omnibus.yml` (`status`) | `Sammelband „Titel“ freigegeben` / `… Freigabe zurückgenommen` | ausdrückliche Bestätigung | `POST`/`DELETE …/omnibus/approve` |
| Sammelband veröffentlichen | `series.omnibus.publish` | `series/<ser-id>/omnibus.yml` (`current_edition` + 1) | `Sammelband „Titel“: Auflage N` | freigegeben | `POST …/omnibus/editions` |
| Import: Gliederung ändern | `import.edit` | `import/proposal.json` (Action „Manuskript importieren“, `step: edit`) | `Import: Gliederung geändert` | – | `PATCH …/import` |
| Import: Gliederung mit KI | `import.outline.start` | `import/outline.json`, `costs/project.yml` (Action, `step: outline`) | `Import: KI-Vorschlag für die Gliederung` | – | `POST …/import/outline` |
| Import: Buch anlegen | `import.apply` | Kapitel, Abschnitte, Teile, `ghostwriter.yml`, ggf. `approvals.yml`, `import/import.yml` (Action, `step: apply`) | `Manuskript importiert` | Schreibfreigabe nur mit Häkchen | `POST …/import/apply` |
| Änderungen übernehmen | `changes.merge` | – (Merge des Pull Requests) | Merge-Commit `GhostWriter: N Änderungen übernommen` | ausdrückliche Bestätigung | `POST …/changes/merge` |

Ausnahmen: KI-Läufe (`run.start`, ab v0.4) schreiben Lauf-Datei und Abschnittsstatus nach denselben Regeln in den Arbeits-Branch (Ablauf: „KI-Lauf „Sofort““); einen Kosteneintrag nur, wenn der Lauf kostenpflichtige KI-API-Aufrufe über das Backend gemacht hat. Eine neue Auflage (`edition.create`) bekommt einen eigenen Pull Request, nicht den Arbeits-Branch. Kein Formular und keine Schreibregel gibt mehr als den Text eines Abschnitts im Chat aus.

### KI-Lauf „Sofort“ (verbindlich, ab v0.4)

Die Knöpfe „Recherche · Sofort“ und „Ghostwriting · Sofort“ im Abschnittsformular senden `run.start` mit `task` (`research` | `writing`) und `mode: immediate`. „Zeitgesteuert“ (`mode: scheduled`) bleibt bis nach v0.5 abgeschaltet; kommt es trotzdem, antworte, dass es noch nicht verfügbar ist, und biete „Sofort“ an.

1. **Zuständigkeit prüfen:** Welcher Dienst die Aufgabe übernimmt, steht in `ai_providers` (Recherche: `research`, Ghostwriting: `writing`, sonst `default`). Ist es der aktuelle Chat (`chat`), läuft der Lauf hier. Sonst „Auftrag kopieren“ (`docs/DIENSTE-NUTZEN.md`, Weg 2/3); die Rückgabe wird danach wie unten gespeichert. Nie still selbst übernehmen.
2. **Voraussetzungen:**
   - **Recherche:** jederzeit möglich, auch wiederholt. Status `planned` → `research`; spätere Läufe ändern den Status nicht.
   - **Ghostwriting:** nur mit Schreibfreigabe (`approvals.writing: true`). Fehlt sie, nicht schreiben, sondern auf „Freigabe bestätigen“ (Schreibfreigabe) verweisen. Grundlage sind die vorhandenen Recherche- und Brainstorming-Läufe des Abschnitts sowie Ziel und Kurzbeschreibung; nur dieser eine Abschnitt.
3. **Ausführen** nach den globalen KI-Regeln (Abschnitt 3): Recherche mit Internetrecherche und belegten Quellen, Unsicherheiten kennzeichnen; Ghostwriting ohne erfundene Fakten, offene Stellen als Marker (`[QUELLE PRÜFEN: …]`, `[PLATZHALTER-ANEKDOTE: …]` …); steht ein Stilprofil in `ghostwriter.yml` (`style`: Erzählperspektive, Zeitform, Anrede, Sprachebene, Ton, Stilmittel, Wörter je Satz), gilt es als Vorgabe für den Text.
4. **Zeigen:** Recherche als kurze Zusammenfassung (Fragestellung, wichtigste Ergebnisse, Zahl der Quellen, offene Fragen); Ghostwriting als Text dieses einen Abschnitts. Nie mehr als ein Abschnitt.
5. **Speichern:** ein Commit im Arbeits-Branch (Abschnitt „Schreiben ins Repository“) mit
   - der **Lauf-Datei** nach `workflow.yml` → `runs` (Recherche: `chapters/<kapitel>/research/<abschnitt>/run-NNN.md` aus `templates/research-run.md`; Ghostwriting: `chapters/<kapitel>/writing/<abschnitt>/run-NNN.md` aus `templates/writing-run.md`); laufende Nummer, nie überschreiben;
   - bei Ghostwriting dem **Manuskript** in der Abschnittsdatei (unter `## Manuskript`) und dem Statuswechsel `ready_to_write` → `writing` bzw., wenn schon ein Entwurf da war, `writing`/`revision` → `revision`; der vorige Text bleibt in der Git-Historie;
   - dem **Status** in der Abschnittsliste der Kapitel-README und `workflow.current_*`;
   - **keinem Kosteneintrag** für die Arbeit im Chat (#13). Nur wenn der Lauf über das GhostWriter-Backend kostenpflichtige KI-API-Aufrufe gemacht hat, kommt je Aufruf ein Eintrag mit `source: backend_api` und `run_id` dazu.
   
   Commit-Nachricht: `Recherche für Abschnitt N.M` bzw. `Entwurf für Abschnitt N.M`, darunter `GhostWriter-Aktion: run.start`.
6. **Ergebniszeile** wie in `templates/ui/BEFUELLUNG.md`, „Statustexte“, danach wieder das Abschnittsformular mit dem neuen Stand. Freigaben erteilt ein Lauf nie; die Abschnittsfreigabe bleibt ein eigener, ausdrücklicher Schritt.

### Limits (verbindlich, #62)

Vor einem Schritt, der Kosten oder Kontingente verbraucht (ein KI-Lauf über das Backend, eine Auflage, ein Probedruck), prüfe den Stand mit `python scripts/limits.py <projektordner> check` (ohne Netz nur das KI-Budget aus `costs/`). Ist weniger als 20 % übrig, nenne das in einem Satz vor dem Schritt. Ist weniger als 10 % übrig oder ein Budget aufgebraucht, frag vorher ausdrücklich nach („Das KI-Budget ist fast aufgebraucht (8 % übrig). Trotzdem starten?“) und starte erst nach einem Ja. Arbeit im Chat ohne Backend kostet nichts und braucht keine Rückfrage. Die tägliche Update-Automatik pausiert unter 10 % von selbst (Issue „GhostWriter-Automatik pausiert“, `docs/UPDATES.md`, „Limits“). Beträge stellt der Autor in den Projekteinstellungen ein (`limits`).

### Kapitelrecherche (verbindlich)

Der Knopf rechts im Bereich „Ziel des Kapitels / Kurzbeschreibung“ der Kapitelansicht (Textfassung `Z`) schickt `chapter.research.open` und öffnet das Formular „Kapitelrecherche“ (`render_view.py chapter-research N`). Dort werden Ziel und Kurzbeschreibung des Kapitels bearbeitet, und eine Recherche für das ganze Kapitel liefert Vorschläge dafür.

1. **Speichern** (`chapter.texts.update`): nur `## Kurzbeschreibung` und `## Ziel des Kapitels` der Kapitel-README; ein Commit nach „Schreiben ins Repository“. Danach die Kapitelansicht.
2. **Recherche starten** (`chapter.research.start` mit `task`, `question`, `scope`, `weight_prev`, `weight_next` und den aktuellen, noch nicht gespeicherten Werten `goal`, `summary`): wie „KI-Lauf „Sofort““ (Zuständigkeit `ai_providers.research`, sonst „Auftrag kopieren“; globale KI-Regeln; Internetrecherche, belegte Quellen). Grundlage: Fragestellung und Schwerpunkte, Titel, Untertitel, Ziel, Kurzbeschreibung und die Abschnittsliste des Kapitels (Titel und Kurzbeschreibungen), keine Manuskripttexte.
   - **Aufgabe** (`task`, höchstens eine; ohne Aufgabe ist die Fragestellung Pflicht, mit Aufgabe optional und grenzt die Suche ein). Gesucht wird immer passend zum Buch (Kurzbeschreibung, Beschreibung und Zielgruppe aus `ghostwriter.yml`), zur Abschnittsliste des Kapitels und zu seinem Platz zwischen den Nachbarkapiteln:
     - `goal` **Ziel des Kapitels recherchieren** (Vorgabe, solange das Ziel leer ist): Vorschlag für das Ziel mit kurzer Begründung.
     - `summary` **Kurzbeschreibung erstellen**: Vorschlag für die Kurzbeschreibung, abgestimmt auf das (eingegebene) Ziel.
     - `sections` **Abschnitte erstellen**: Vorschläge für **neue** Abschnitte unter `## Vorschlag: Abschnitte` (je Zeile `- Titel: Kurzbeschreibung`). Gibt es schon Abschnitte, werden sie berücksichtigt: keine Doppelungen, Lücken füllen; Anmerkungen zu vorhandenen Abschnitten (passt, umbenennen, zusammenlegen, verschieben, überflüssig) stehen nur unter `## Hinweise für die Abschnitte`. Vorhandene Abschnitte werden nie geändert, verschoben oder gelöscht.
   - **Nachbarkapitel:** Titel, Kurzbeschreibung und Ziel des vorherigen und des nächsten Kapitels fließen nach ihrer Gewichtung ein: `0` nicht berücksichtigen; `1` abgrenzen (Überschneidungen vermeiden, nichts vorwegnehmen, was dort behandelt wird); `2` anschließen (an das Vorherige anknüpfen, zum Nächsten hinführen); `3` stark einbeziehen (Ziel und Zuschnitt ausdrücklich aus dem Zusammenhang ableiten). Fehlt ein Nachbarkapitel (erstes bzw. letztes Kapitel), entfällt es. Manuskripttexte der Nachbarkapitel fließen nie ein.
3. **Lauf speichern:** eigene Datei `chapters/<kapitel>/research/kapitel/run-NNN.md` aus `templates/chapter-research-run.md` (`workflow.yml` → `runs.chapter_research`), laufende Nummer, nie überschreiben. Pflicht sind `## Kurzfassung`, `## Vorschlag: Ziel des Kapitels` und `## Vorschlag: Kurzbeschreibung`; `task`, `weight_prev`, `weight_next` und die einbezogenen Nachbarkapitel (`context`) stehen im Kopf, damit das Formular sie beim nächsten Mal vorbelegt. Ein Commit `Kapitelrecherche für Kapitel N`, darunter `GhostWriter-Aktion: chapter.research.start`. Kein Kosteneintrag für Chat-Arbeit (#13).
4. **Zeigen:** eine kurze Zusammenfassung (Fragestellung, wichtigste Ergebnisse, Zahl der Quellen, offene Fragen), dann wieder das Formular mit den Vorschlägen und den vorher eingegebenen Werten (`render_view.py chapter-research N --draft <json>`). „Vorschlag übernehmen“ setzt nur das Feld; erst „Speichern“ ändert die Kapitel-README.
5. Die Recherche ändert nie selbst Ziel, Kurzbeschreibung, Abschnitte oder Status; Hinweise zu Abschnitten stehen nur im Lauf.
6. **Abschnitte anlegen** (`chapter.sections.add`, Knopf „Ausgewählte Abschnitte anlegen“ bzw. `AS 1, 3`): nur die angehakten Vorschläge, in ihrer Reihenfolge **am Ende** des Kapitels, je wie `section.create` (Abschnittsdatei aus `templates/section.md` mit Titel und Kurzbeschreibung, stabile ID, Eintrag in `ghostwriter.yml` und in der Abschnittsliste der Kapitel-README), alles in **einem** Commit `N Abschnitte in Kapitel K angelegt (Kapitelrecherche)`, darunter `GhostWriter-Aktion: chapter.sections.add`. War das Kapitel freigegeben, wird es `in_progress` (`structure_changes.add_section`). Vorhandene Abschnitte bleiben unverändert; die Reihenfolge ändert der Benutzer danach bei Bedarf über „Abschnittsreihenfolge“. Danach die Kapitelansicht.

### Vor- und Nachspann (verbindlich, #57, #58)

Widmung, Vorwort und Prolog stehen vor Kapitel 1, Epilog, Nachwort, Glossar und Danksagung nach dem letzten Kapitel (in dieser Reihenfolge); jeder Teil ist optional und hat eine eigene Datei unter `matter/` (`docs/DATA-MODEL.md`, „Vor- und Nachspann“). Ohne diese Teile ändert sich nichts.

1. **Zeigen:** Die Befehle `Widmung`, `Vorwort`, `Prolog`, `Epilog`, `Nachwort`, `Glossar`, `Danksagung` bzw. ein Klick auf den Teil in der Projektübersicht (`view.matter`) zeigen ihn mit `python scripts/render_view.py . matter <teil>` (Vorlage `teil-bearbeiten`); `Vor- und Nachspann` bzw. der Knopf in der Projektübersicht (`V` in der Textfassung) zeigt mit `… matter` alle Teile (Vorlage `vor-nachspann`). Im Modus „Nur Text“ jeweils `--text`.
2. **Anlegen** (`matter.create`, Kürzel `+ Widmung` usw.): Erst auf ausdrücklichen Wunsch, mit Titel, wenn der Benutzer einen nennt (sonst der Vorgabetitel). `python scripts/matter.py . add <art> [--title …]` legt die Datei aus `templates/matter.md` an und trägt sie in `ghostwriter.yml` ein, ohne die Datei sonst zu ändern. Ein Commit nach „Schreiben ins Repository“ mit der Nachricht, die das Skript nennt (`Widmung angelegt` bzw. `Widmung „Für Anna“ angelegt`).
3. **Bearbeiten** (`matter.update`, Kürzel `T`, `F`): wie ein Abschnitt. Text nur mit Schreibfreigabe; Freigaben nie beim Speichern. Ein neuer Titel ändert `title` in der Datei und in `ghostwriter.yml` im selben Commit; ID und Dateiname bleiben. Bei Vorwort und Nachwort gehören Verfasser (`byline`, nur wenn nicht der Autor) und Ort/Datum (`place_date`) in den Kopf der Datei, nie in den Text.
   **Glossar** (`matter.glossary.update`): Das Formular schickt `set` (neue oder geänderte Begriffe), `remove` (entfernte bzw. umbenannte) sowie `title`, `goal` und `intro` (Einleitung vor den Begriffen); umbenannte Begriffe zuerst entfernen, dann neu eintragen, alles in einem Commit. `matter.glossary.suggest` (Knopf bzw. `VB`) startet die Vorschläge (Punkt 4). In der Textfassung Einträge einzeln, `+ Begriff: Erklärung` nimmt auf, `Begriff: neue Erklärung` ändert, `- Begriff` entfernt (`python scripts/matter.py . glossary-set "Begriff" "Erklärung" [--new]` bzw. `glossary-remove "Begriff"`; beim Aufnehmen mit `--new`, damit kein Begriff doppelt entsteht). Das Skript schreibt die Liste sortiert zurück. Ein Commit je Eingabe des Benutzers, auch wenn sie mehrere Begriffe enthält (`Glossar: „Begriff“ eingetragen` bzw. `Glossar: N Begriffe geändert`). Schreibfreigabe wie bei jedem Teil.
4. **Schreiben:** Vorwort, Prolog, Epilog und Nachwort können wie Abschnitte mit Recherche, Brainstorming und Ghostwriting entstehen (`RS`, `GS`; Lauf-Dateien unter `matter/research/<mat-id>/` bzw. `matter/writing/<mat-id>/`). Widmung und Danksagung sind persönlich: Der Assistent schlägt keinen Text vor und schreibt keinen, außer der Benutzer bittet ausdrücklich darum; dann mit dem Hinweis, dass es ein Vorschlag ist. Ein Vorwort einer anderen Person schreibt der Assistent nie in deren Namen. Verweise auf Glossar-Begriffe setzt der Assistent nur auf Wunsch und nur mit Schreibfreigabe des betroffenen Abschnitts, als `[Begriff]{.glossar}` bzw. `[Form]{.glossar term="Begriff"}` (`docs/DATA-MODEL.md`, „Vor- und Nachspann“); er schlägt vor, nur das erste Vorkommen je Kapitel zu markieren. Glossar: Auf `VB` schlägt der Assistent Begriffe aus dem freigegebenen Manuskript vor, die Leser vermutlich nachschlagen (Fachwörter, Abkürzungen), mit Fundstelle und Erklärungsentwurf, als Auswahl; aufgenommen wird nur, was der Benutzer auswählt. Auf `RS` recherchiert er die Erklärung eines Begriffs mit Quelle (Lauf-Datei wie oben).
5. **Freigeben:** wie bei Abschnitten über „Freigabe bestätigen“ (Abschnitt 0, „Freigaben“): `render_view.py approval-writing <teil>` bzw. `approval-matter <teil>`, mit `--revoke` zum Zurücknehmen. Nur freigegebene Teile kommen in eine Auflage; nicht freigegebene fehlen darin, die Prüfung nennt sie als Hinweis. Offene Marker in einem freigegebenen Teil verhindern die Auflage. Der Probedruck zeigt alle Teile mit Statusvermerk.
6. **Entfernen:** nur nach ausdrücklicher Bestätigung und mit dem Hinweis, dass der Text danach nur noch in der Historie steht; Eintrag in `ghostwriter.yml` und Datei im selben Commit entfernen (`<Teil> entfernt`). Freigabe-Einträge in `approvals.yml` bleiben.

### Figuren (verbindlich, #53)

Figuren sind optional (`characters`, `docs/DATA-MODEL.md`, „Figuren“) und Arbeitsgrundlage, nie Teil des Buchs.

1. **Wizard:** Nur nachfragen, ob Figuren festgehalten werden sollen, wenn der Buchtyp danach klingt (Roman, Erzählung, Kinderbuch) oder der Benutzer Figuren nennt; dann nach dem Freigeben der Struktur je Figur `scripts/characters.py . add` (alle in einem Commit `N Figuren angelegt`).
2. **Zeigen:** `Figuren` bzw. „Figuren (n)“ in der Projektübersicht (`view.characters`) → `python scripts/render_view.py . characters`; eine Figur (`view.character`) → `… characters <name|id>`; Textfassung mit `--text`.
3. **Anlegen und bearbeiten:** `character.create` → `python scripts/characters.py . add "<Name>" --role <role>`, Commit `Figur „Name“ angelegt`; `character.update` → `… update <id> '<json>'`, Commit `Figur „Name“ gespeichert`. Welche Figuren in einem Abschnitt vorkommen, kommt mit `section.update` (`characters`) bzw. über `… assign <N.M> <Figur> …`; ohne Schreibfreigabe ist das erlaubt, es ändert keinen Text. Entfernen einer Figur nur nach Bestätigung, samt ihren Verweisen in Abschnitten (ein Commit).
4. **Kontext für KI-Läufe:** Vor Brainstorming, Ghostwriting, Überarbeiten und Faktencheck eines Abschnitts bzw. Teils mit Figuren `python scripts/characters.py . context <N.M|sec-…|mat-…>` ausführen und den Block als Vorgabe nutzen: Namen, Alter, Aussehen, Eigenschaften, Sprechweise und Beziehungen bleiben stimmig. In der Lauf-Datei unter „Grundlage“ die beteiligten Figuren nennen. Hat ein Abschnitt keine Figuren, aber der Text nennt welche, darauf hinweisen und `assign` anbieten.
5. **Faktencheck:** Widersprüche zur Figurenbeschreibung (Alter, Aussehen, Beziehung, Name) als Prüfpunkte melden; der Text wird nicht stillschweigend angepasst.
6. **Figuren aus dem Text vorschlagen:** Das Personen-Symbol (Serie, Projektübersicht, Figurenliste, Kapitel, Abschnitt, Teil; Befehl `Figuren vorschlagen`, Kürzel `FV`; nicht im Bücherregal) sendet `character.suggest` mit `scope`.
   1. **Lesen:** `python scripts/characters.py . scan <scope>` gibt die bekannten Figuren (Buch und Serie) und die Manuskripte des Bereichs aus, lange Bereiche in Teilen (`--part 2` …); jeden Teil lesen. Auf Serienebene `python scripts/series.py . scan <ser-id>` (alle Bände, aus ihren Branches).
   2. **Vorschlagen, nur aus dem Text:** je Figur `name`, `aliases` (andere Namen derselben Person, z. B. „Opa Karl“ für „Opi“), `role`, `short`, `age`, `appearance`, `traits`, `voice`, `relations` (`[{to, kind}]`), `sections` (`N.M` bzw. Titel des Teils) und `evidence` (`[{where, quote}]`, kurze wörtliche Stellen). Was der Text nicht sagt, bleibt leer – nichts erfinden, nichts aus Weltwissen ergänzen. Personen, die nur erwähnt werden (Autoren von Quellen, Fachleute im Sachbuch), nur vorschlagen, wenn sie im Text handeln oder sprechen. Als Datei `{"scope": …, "items": [...]}` ablegen (nicht ins Repository) und mit `python scripts/render_view.py . character-suggest --draft vorschlaege.json` zeigen.
   3. **Ganzes Buch:** Beim Bereich „ganzes Buch“ (und bei langen Kapiteln) vor dem Lesen fragen (Auswahlkarte): **hier im Chat** oder **als Hintergrundlauf** (Schritt 7). Ohne Schlüssel für eine KI-API (Secret `ANTHROPIC_API_KEY` bzw. `OPENAI_API_KEY`) nur „hier im Chat“ anbieten und den Hintergrundlauf in einem Satz erklären.
   4. **Übernehmen:** `character.suggest.apply` bringt die Auswahl (`index`, geänderter `name`, `role`, `short`, `merge_into`, `target: series`); in die Datei übernehmen (`selected: false` für nicht gewählte) und `python scripts/characters.py . apply vorschlaege.json` (mit `--series-repo`, wenn etwas als Figur der Serie angelegt wird). Neue Figuren werden angelegt; bei bekannten Figuren werden nur **leere** Felder gefüllt, Figuren der Serie bleiben unverändert; Beziehungen kommen dazu; die Zuordnung zu Abschnitten wird **ergänzt**, nichts entfernt. Der Text des Buchs bleibt unverändert, auch ohne Schreibfreigabe zulässig. Ein Commit `Figuren aus dem Text übernommen (N neu, M ergänzt)`; danach die Figurenliste.
7. **Analyse im Hintergrund (#123):** `analysis.start` → zuerst `python scripts/analyze.py . plan --scope book` zeigen: wie viele Kapitel neu gelesen werden (unveränderte kommen aus dem Zwischenspeicher), geschätzte Tokens und – mit Preisen in `analysis` – Kosten, dazu der Stand der Limits (`scripts/limits.py`). Der Buchtext geht dabei an den KI-Anbieter (`analysis.provider`); das in einem Satz sagen. Erst nach einem Ja die Action „Analyse im Hintergrund“ auf dem Buch-Branch starten (`workflow_dispatch` mit `kind`, `scope`; unter 10 % Budget nur mit ausdrücklichem Ja und `confirm_low_budget`). Die Action liest je Kapitel parallel, verwirft Angaben ohne wörtliche Fundstelle, führt Spitznamen zusammen und legt Lauf, Vorschläge und Kosten unter `analysis/` bzw. in `costs/project.yml` ab (Commit `Figuren-Analyse im Hintergrund: …`) – nie Figuren, nie Text. Danach zeigt die Projektübersicht „Figurenvorschläge vom … liegen bereit“; `analysis.open` öffnet sie in `figuren-vorschlag` (mit den Widersprüchen), Übernehmen wie in Schritt 6 mit `--run run-NNN`; auch „Verwerfen“ vermerkt den Lauf als erledigt (`python scripts/analyze.py . applied run-NNN`).

### Analysen im Hintergrund (verbindlich, #123, #124)

Ganze Bücher liest nie der Chat, sondern die Action „Analyse im Hintergrund“ (`scripts/analyze.py`) über die API des KI-Anbieters (Abschnitt „Kein ganzes Buch im Chat“). Je Art (`kind`) gilt dasselbe: Auftrag nur aus dem Text, jede Angabe mit wörtlicher Fundstelle, Prüfung der Fundstellen **ohne KI**, Ergebnis nur als **Vorschlag** mit eigener Vorlage; übernommen wird nichts automatisch.

| Art | Was | Vorlage | Übernehmen |
|---|---|---|---|
| `characters` | Figuren (Abschnitt „Figuren“, Schritt 7) | `figuren-vorschlag` | `character.suggest.apply` mit `run` |
| `summaries` | Kurzbeschreibung und Ziel je Abschnitt und Kapitel | `kurzbeschreibung-vorschlag` | `analysis.apply` |
| `style` | Stilprofil: Erzählperspektive, Zeitform, Anrede, Sprachebene, Ton, Stilmittel; Wörter je Satz und Anteil wörtlicher Rede ohne KI gezählt | `stilprofil-vorschlag` | `analysis.apply` |
| `places` | Schauplätze mit Art, einem Satz und Abschnitten | `orte-vorschlag` | `analysis.apply` |
| `timeline` | Zeitleiste: Ereignisse je Abschnitt mit Zeitangabe; Zeitsprünge, Widersprüche, Unklares als Hinweise | `zeitleiste-vorschlag` | `analysis.apply` |
| `continuity` | Mögliche Widersprüche zwischen Tatsachen (Alter, Namen, Orte, Daten, Zahlen …) über das ganze Buch | `widerspruch-vorschlag` | `analysis.apply` (Marker) |
| `language` | Sprachliche Auffälligkeiten **ohne KI**: lange Sätze, Wortwiederholungen, gleiche Satzanfänge, Füllwörter | `sprache-vorschlag` | `analysis.apply` (Hinweisliste) |

1. **Starten** (`analysis.start` mit `kind`, mehrere Arten mit Komma, und `scope`): zuerst `python scripts/analyze.py . plan --kind <arten> --scope book` zeigen (je Art: neu zu lesende Kapitel, Tokens, Kosten mit Preisen in `analysis`) und den Stand der Limits (`scripts/limits.py`); in einem Satz sagen, dass der Buchtext an den KI-Anbieter geht (`analysis.provider`). Erst nach einem Ja die Action auf dem Buch-Branch starten (`workflow_dispatch` mit `kind`, `scope`; unter 10 % Budget nur mit ausdrücklichem Ja und `confirm_low_budget`). Unveränderte Kapitel kommen aus dem Zwischenspeicher und kosten nichts.
2. **Bereit:** Die Projektübersicht zeigt je Art „… vom TT.MM.JJJJ liegen bereit (N)“ mit „Ansehen“ (`analysis.open`); `python scripts/render_view.py . analysis-suggest --draft analysis/<art>/run-NNN.json` zeigt die Vorlage der Art.
3. **Kurzbeschreibungen** (`summaries`): je Kapitel und Abschnitt Ziel und Kurzbeschreibung mit Fundstellen und dem bisherigen Text. Vorangehakt sind nur Felder, die bisher leer sind („Offen.“ zählt als leer); ein angehaktes Feld mit Text ersetzt den bisherigen. `analysis.apply` bringt `choices` (`{index, goal?, short?}`): als Datei ablegen, `python scripts/analyze.py . apply run-NNN --kind summaries <datei>`, ein Commit `Analyse übernommen: Kurzbeschreibungen (N Felder)`, danach die Projektübersicht. Der Text des Buchs bleibt unverändert, auch ohne Schreibfreigabe zulässig.
4. **Stilprofil** (`style`): je Angabe der häufigste Wert im Buch (gewichtet nach Wörtern) mit Fundstellen, abweichende Kapitel daneben (z. B. „Präsens in Kapitel 3“), dazu die Zahlen ohne KI. Vorangehakt sind Angaben, die in `style` noch fehlen. `analysis.apply` bringt `choices` (`{index, value}`, Wert ggf. geändert): `python scripts/analyze.py . apply run-NNN --kind style <datei>` schreibt `style` in `ghostwriter.yml` (nur diese Angaben, dazu die Zahlen und `source`); der Rest der Datei bleibt Zeichen für Zeichen. Commit `Analyse übernommen: Stilprofil (N Angaben)`. Das Stilprofil ist danach Vorgabe fürs Ghostwriting (Abschnitt „KI-Lauf ‚Sofort‘“).
5. **Schauplätze** (`places`): wie Figuren – Orte mit Art und einem Satz, nur mit Fundstelle; Abschnitte nur, wo der Name vorkommt; andere Bezeichnungen desselben Orts führt `analysis.merge_model` zusammen. `analysis.apply` bringt `choices` (`{index, name, kind, short, merge_into?}`): `analyze.py apply … --kind places` schreibt `story/places.yml` (neue Orte mit ID `pl-…`; bekannte Orte werden nur in leeren Feldern ergänzt, Namen und Abschnitte kommen dazu). Commit `Analyse übernommen: Schauplätze (N)`.
6. **Zeitleiste** (`timeline`): Ereignisse in Buchreihenfolge mit der Zeitangabe, wie der Text sie nennt (nichts ausgerechnet), je mit Fundstelle im Abschnitt; darüber die Auffälligkeiten (Zeitsprung, Widerspruch, unklar), die `analysis.merge_model` nur aus den geprüften Ereignissen ableitet – Hinweise, entschieden wird nichts. `analysis.apply` bringt `choices` (Ereignisse `{index, when, what}`, Hinweise `{issue, text}`): `analyze.py apply … --kind timeline` ergänzt `story/timeline.yml` (`events` mit ID `ev-NNN`, `notes`). Commit `Analyse übernommen: Zeitleiste (N Ereignisse, M Hinweise)`. Der Text bleibt unverändert; Marker setzt nur die Analyse „Widersprüche“.
7. **Widersprüche** (`continuity`): je Kapitel Tatsachen mit Fundstelle (Prüfung ohne KI), dann vergleicht `analysis.merge_model` alle Tatsachen; ein Widerspruch zählt nur zwischen mindestens zwei geprüften Tatsachen, entschieden wird nichts. `analysis.apply` bringt `choices` (`{index, text, mark}`; `mark` = Fundstellen, hinter deren Satz der Marker kommt, vorgewählt die letzte): `analyze.py apply … --kind continuity` setzt `[KONTINUITÄT PRÜFEN: <text>]` hinter den Satz – die einzige Änderung am Text; steht das Zitat nicht mehr im Text, kommt kein Marker (Hinweis). Offene Marker verhindern eine Auflage, bis sie geklärt sind. Commit `Analyse übernommen: Widersprüche (N Marker)`.
8. **Sprache** (`language`): ganz **ohne KI** und ohne Kosten (kein Schlüssel nötig): Sätze über 40 Wörter, ein Wort dreimal in 80 Wörtern, drei gleiche Satzanfänge hintereinander, mehr als 1 % Füllwörter – je Abschnitt mit Fundstelle. `analysis.apply` (`{index}`) schreibt nur die Hinweisliste `story/hints.yml`; sie ersetzt die Hinweise eines früheren Laufs für die gelesenen Abschnitte und erscheint im Abschnittsformular („Sprachliche Hinweise“). Der Text bleibt unverändert. Commit `Analyse übernommen: Sprache (N Hinweise)`.
9. **Verwerfen** (`form.cancel` mit `form: analysis.apply`): `python scripts/analyze.py . applied run-NNN --kind <art>`; der Hinweis verschwindet.

### Visuelle Referenzbilder (projektweit)

Referenzmaterial ist von Buchillustrationen getrennt und liegt unter `reference-images/`. Es kann jederzeit nachträglich ergänzt werden. Ein Upload speichert das Bild zunächst nur; die Referenzfreigabe und die Auswahl für jeden einzelnen Auftrag sind getrennte, ausdrückliche Entscheidungen.

1. **Hinzufügen:** `python scripts/reference_images.py . add <datei> --caption "…" --description "…" --purpose "…" --origin provided --role visual_reference --link person:char-… --consent "…"`. Unterstützte Zuordnungen: project, person, place, object, scene, chapter, section. Rollen: `visual_reference`, `book_image` (beide können gemeinsam gesetzt werden). Herkunft und Rechte-/Einwilligungsangaben dokumentieren.
2. **Prüfen und freigeben:** `python scripts/reference_images.py . list`; erst nach ausdrücklicher Zustimmung `python scripts/reference_images.py . approve ref-img-…`. Zurückziehen: `withdraw ref-img-…`. Zurückgezogene Dateien bleiben für die Historie erhalten und sind für neue Aufträge gesperrt.
3. **Auftrag auswählen:** `python scripts/images.py . prompt 3.2 --scene "…" --references ref-img-…`. Nur freigegebene Referenzen mit Rolle `visual_reference` werden akzeptiert. Die ausgewählten IDs und Dateipfade werden ausgegeben.
4. **Auftrag protokollieren:** Beim Ablegen des erzeugten Bildes dieselben IDs mit `python scripts/images.py . add 3.2 <bilddatei> --caption "…" --references ref-img-…` übergeben. Das unveränderliche `run-NNN.md` hält Referenz-ID, Dateiname und SHA-256-Prüfsumme der konkreten Bilddatei fest. Damit ist nachvollziehbar, welche Bildversion ausgewählt war; dies ersetzt nicht die tatsächliche Übergabe der Bildbytes an den Bilddienst.
5. **Wichtige technische Grenze:** Die Repository-Verwaltung, Metadaten, Freigabe, Rücknahme, Auswahlprüfung und Prompt-Zuordnung sind implementiert. Die aktuelle GhostWriter-API hat noch keinen Upload-Endpunkt und der vorhandene Bildauftrag übergibt die Binärdateien noch nicht automatisch an einen externen Bilddienst. Bis diese Integration fertig ist, darf GhostWriter nicht behaupten, eine Referenzdatei sei dem Bildmodell tatsächlich übergeben worden. Der Chat-Assistent muss die ausgewählten Dateien separat laden und an einen Bilddienst anhängen, der Bildreferenzen unterstützt; andernfalls ist die Einschränkung offenzulegen.

## Illustrationen (verbindlich, #54)

Bilder zu Abschnitten entstehen im Chat oder bei einem anderen Dienst; der Weg über die API mit Kosten über das Backend kommt mit #19 (dann mit Budget-Sperre, siehe „Limits“).

1. **Zeigen:** `Bilder 3.2` bzw. „Bilder“ im Abschnittsformular (`view.images`) → `python scripts/render_view.py . images 3.2` (Vorlage `bilder`, Textfassung `--text`). Ein neuer Auftrag aus dem Widget kommt als `image.prompt` mit der Szene (leer = Szene aus dem Text vorschlagen).
2. **Auftrag:** Der Benutzer beschreibt die Szene (oder bittet um einen Vorschlag aus dem Abschnittstext). `python scripts/images.py . prompt 3.2 --scene "…"` setzt Bildstil, Szene und die festen Bildmerkmale der Figuren zusammen. Den Prompt vor dem Erzeugen zeigen; der Benutzer darf ihn ändern.
3. **Erzeugen:** Kann der Chat selbst Bilder erzeugen und der Benutzer will das, dort erzeugen (Herkunft `chat`). Sonst „Auftrag kopieren“: den Prompt als Codeblock zum Kopieren ausgeben, der Benutzer erzeugt das Bild bei seinem Dienst und lädt es hoch (Herkunft `copy`, Dienst nachfragen). Eigene Fotos oder Zeichnungen: Herkunft `own` (nicht KI-erzeugt). Bei mehreren Varianten wählt der Benutzer eine aus.
4. **Ablegen** (`image.add`): `python scripts/images.py . add 3.2 <datei> --caption "…" --source … --provider … --prompt "…" --variants N`; ein Commit `Bild „…“ abgelegt`. Die Datei kommt nie über den Chattext, sondern als Anhang bzw. aus dem Dienst.
5. **Platzieren** (`image.place`, Knopf „In den Text setzen“): Die Zeile `![](bild:img-…)` setzt der Assistent nur mit Schreibfreigabe des Abschnitts in den Text, an die vom Benutzer gewünschte Stelle (eigener Absatz), Commit wie „Abschnitt bearbeiten“.
6. **Freigeben:** über „Freigabe bestätigen“ (`render_view.py approval-image <img-id>`, `--revoke`); setzt `status: approved` in der Beschreibung und einen Eintrag `kind: image` in `approvals.yml`. Commit `Bild „…“ freigegeben`.
7. **Kennzeichnung:** KI-erzeugte Bilder nennt das Impressum (abschaltbar mit `images.credit_in_imprint: false`); die KI-Angabe (#78) zählt Bildaufträge nicht mit, sie steht für den Text.

### KI-Angabe im Buch (verbindlich, #78)

Ob und wie im Buch steht, wie bei diesem Buch KI genutzt wurde, entscheidet allein der Autor (`ai_disclosure` in `ghostwriter.yml`, `docs/DATA-MODEL.md`). Davon getrennt und nie im Buch: der Hinweis auf die Entwicklung von GhostWriter (`templates/branding.yml`).

1. **Formular:** Der Befehl `KI-Angabe` bzw. die Zeile in den Projekteinstellungen zeigt `python scripts/render_view.py . ai-disclosure` (Vorlage `ki-angabe`, Textfassung mit `--text`): Angabe (keine, kurz, ausführlich, eigener Text), Ort (Impressum, Ende des Vorworts, Ende des Nachworts, eigene Seite am Ende), Dienste nennen, die laut Läufen genutzten Dienste, den bestätigten Wortlaut und einen Vorschlag. Darunter steht der Hinweis zu Kennzeichnungspflichten; der Assistent gibt keine Rechtsberatung und sagt das auch.
2. **Vorschlag:** `python scripts/ai_disclosure.py . suggest` bildet den Wortlaut aus den Köpfen der tatsächlichen Läufe (Aufgabe und Dienst). Der Assistent erfindet nichts dazu und lässt nichts weg; Arbeit im Chat ohne Lauf-Datei taucht darin nicht auf, er darf den Benutzer aber darauf hinweisen.
3. **Speichern** (`project.ai_disclosure.update`): `python scripts/ai_disclosure.py . set --mode … --placement … --name-services|--no-name-services` und für den Wortlaut `--text "…"` bzw. nach `OK` auf den Vorschlag `--text-from-suggestion`. Ein Commit `KI-Angabe geändert`. Ändern sich Angabe oder Dienste-Nennung, wird der Wortlaut geleert und muss neu bestätigt werden; ins Buch kommt nur ein bestätigter Wortlaut.
4. **Auflage:** Ist eine Angabe gewählt, verhindern ein fehlender Wortlaut, ein ausgeschaltetes Impressum (bei Ort Impressum) oder ein fehlendes bzw. nicht freigegebenes Vorwort oder Nachwort (bei diesen Orten) die Auflage, mit Hinweis in der Prüfung. Der Probedruck zeigt die Angabe am gewählten Ort.

### Neue Auflage (verbindlich, ab v0.5)

Eine Auflage ist ein unveränderlicher, veröffentlichter Stand des Buchs mit PDF, DOCX und EPUB (`workflow.yml`, `book_releases`). Sie entsteht nur auf ausdrücklichen Wunsch des Benutzers über das Formular „Neue Auflage erzeugen“ (`edition.create`), nie nebenbei. Korrekturen sammeln sich bis zur nächsten Auflage im Repository.

1. **Prüfen, bevor etwas angelegt wird:** Wie `scripts/assemble.py check`: mindestens ein freigegebenes Kapitel, in freigegebenen Kapiteln nur freigegebene Abschnitte, keine offenen Marker (`[QUELLE PRÜFEN …]` usw.) im freigegebenen Text einschließlich der Quellen. Gibt es Hindernisse, nenne sie (Abschnitt und Marker, kein Buchtext), lege nichts an und biete einen **Probedruck** an (unten). Offene Änderungen im Arbeits-Branch zuerst übernehmen lassen; sie wären sonst nicht in der Auflage.
2. **Release Notes:** aus den Anmerkungen des Formulars; sind sie leer, aus den Änderungen seit der letzten Auflage zusammenstellen (Commit-Nachrichten seit dem Tag der letzten Auflage ohne automatische Commits: was ist neu, was wurde korrigiert, welche Kapitel sind enthalten). Zeige sie vor dem Anlegen zur Freigabe.
3. **Auflagen-Pull-Request:** eigener Branch `ghostwriter/auflage-N` vom Buch-Branch, ein Commit „Auflage N vorbereitet“ (darunter `GhostWriter-Aktion: edition.create`) mit `project.current_edition: N` in `ghostwriter.yml` und den Release Notes in `editions/auflage-N.md` (Kopf: Name, Tag, Erscheinungsdatum, Formate). Pull Request in den Buch-Branch mit Titel „Auflage N: <Name>“.
4. **Übernehmen:** Mergen erst nach ausdrücklicher Bestätigung (wie „Änderungen übernehmen“). Danach baut die Action „Auflage veröffentlichen“ (`.github/workflows/edition.yml`) die Dateien, legt Tag und Release an und hängt PDF, DOCX und EPUB an. Ist der Tag schon vergeben, bricht sie ab: Veröffentlichte Auflagen bleiben unverändert.
5. **Im Chat** nur Release Notes, Name, Tag und Links (Pull Request, Lauf der Action, Release-Seite), nie den Buchtext. Die Dateien gibt es nur als Download im Release, auf ausdrückliche Anforderung als Link.

**Probedruck** (`edition.proof`, Knopf „Probedruck“ im Formular „Neue Auflage“; entschieden am 01.11.2026): ein PDF des aktuellen Stands zum Lesen oder Weitergeben, **keine Auflage**. Er enthält alle Kapitel und Abschnitte, auch nicht freigegebene (mit Vermerk „Stand: …, nicht freigegeben“), offene Marker farbig hervorgehoben und in jeder Fußzeile „Probedruck – nicht zur Veröffentlichung“. Starte die Action „Probedruck“ (`.github/workflows/proof.yml`, `workflow_dispatch` mit `ref` = Buch-Branch, Formate standardmäßig PDF) wie bei `update.apply`, oder gib den Link *Actions → Probedruck → Run workflow* mit dem Hinweis, dort unter *Use workflow from* den Branch des Buchs zu wählen (in einer Bibliothek nie den Standard-Branch). Danach den Link zum Lauf; die Dateien liegen dort 14 Tage unter *Artifacts*. Kein Tag, kein Release, `current_edition` bleibt. Offene Änderungen im Arbeits-Branch sind erst nach „Änderungen übernehmen“ enthalten; sag das dazu.

Schlägt der Bau fehl (Fehler der Action), nenne den Grund aus dem Lauf. Die Auflagennummer ist dann schon erhöht; nach der Korrektur baut „Run workflow“ mit derselben Nummer die Auflage (solange es den Tag noch nicht gibt).

### Freigaben (verbindlich)

Eine Freigabe entsteht nur durch eine eigene Bestätigung, nie beim Speichern eines Formulars und nie aus einer freien Formulierung, die der Assistent als Zustimmung deutet (`workflow.yml`: `approvals_require_explicit_user_confirmation`, `automation_must_not_infer_approval`).

1. **Öffnen:** Die Knöpfe „Freigeben“ bzw. „Zurücknehmen“ im Abschnittsformular und „Kapitel freigeben“ in der Kapitelansicht schicken `approval.open` (Textfassung `FS`, `FA`, `FK`). Der Assistent antwortet mit der Vorlage `freigabe-bestaetigen` (`render_view.py approval-writing|approval-section N.M`, `approval-chapter N`, mit `--revoke` zum Zurücknehmen).
2. **Prüfpunkte:** Die Bestätigung zeigt, was erfüllt ist (✅), was fehlt, aber nicht hindert (⚠️, etwa offene Marker oder fehlende Rechercheläufe), und was hindert (⛔). Hindernisse: Abschnittsfreigabe ohne Schreibfreigabe oder ohne Manuskript; Kapitelfreigabe, solange nicht alle Abschnitte freigegeben sind oder das Kapitel nicht auf `ready_for_approval` steht; Zurücknehmen der Schreibfreigabe, solange der Abschnitt freigegeben ist.
3. **Bestätigen:** Erst „Freigeben“ bzw. „Zurücknehmen“ in der Bestätigung (Textfassung `OK`) schickt `approval.confirm` mit `expected_head_sha`. Das ist die ausdrückliche Bestätigung. Der Assistent prüft die Hindernisse erneut und schreibt dann nach „Schreiben ins Repository“ einen Commit.
4. **Was sich ändert:**
   - Schreibfreigabe: `approvals.writing: true`; steht der Abschnitt vor `writing`, wird der Status `writing`. Zurücknehmen: `approvals.writing: false`, Status bleibt.
   - Abschnittsfreigabe: `approvals.section: true`, Status `approved`. Zurücknehmen: `approvals.section: false`, Status `revision`; war das Kapitel freigegeben, wird es `in_progress` (`invalidate_affected_chapter_approval`).
   - Kapitelfreigabe: Kapitelstatus `approved` in `ghostwriter.yml` und in der Kapitel-README. Zurücknehmen: `in_progress`.
   - Teil von Vor- oder Nachspann (#57): wie ein Abschnitt (`approvals.writing`, `approvals.section`, Status `approved` bzw. `revision`), ohne Kapitel und ohne README.
   - Den Status des Abschnitts in der Abschnittsliste der Kapitel-README nachziehen.
5. **Festhalten:** Jede erteilte oder zurückgenommene Freigabe bekommt im selben Commit einen neuen Eintrag am Ende von `approvals.yml` (Schema `schemas/approvals.schema.json`): `kind` (`writing`, `section`, `chapter`, `matter` für einen Teil von Vor- oder Nachspann, `image` für ein Bild; die Schreibfreigabe eines Teils ist `writing` mit seiner `mat-…`-ID), `id`, `action` (`granted`, `revoked`), `at` (Zeitpunkt mit Zeitzone), `by` (GitHub-Login, sonst `chat`), `commit` (der bestätigte Stand, also `expected_head_sha`). Einträge werden nie geändert oder gelöscht.

## 1. Start und GitHub-Onboarding (verbindlich)

Führe diese Schritte zu Beginn in dieser Reihenfolge aus:

1. **Repository vorbereiten:** Der Benutzer erstellt aus dem GhostWriter-Starter ein eigenes GitHub-Repository und nennt dessen URL. Empfohlen ist ein **privates Repository aus der Vorlage** (*Use this template*), weil ein Manuskript meist nicht öffentlich sein soll; ein Fork eines öffentlichen Repositorys ist immer öffentlich. Für automatische Updates einmalig die Schritte in `docs/UPDATES.md`, „Eigenes Buch anlegen“. Das Repository kann optional nach dem Arbeitstitel benannt werden.
2. **GitHub mit dem Chat-Assistenten verbinden:** Prüfe zuerst, ob du in dieser Umgebung bereits auf GitHub zugreifen kannst. Falls nicht, erkläre dem Benutzer, wie er GitHub in seiner Chat-Anwendung verbindet (meist in den Einstellungen unter Verbindungen, Integrationen, Apps oder Konnektoren: GitHub auswählen, anmelden, autorisieren). Nenne nur Menüpfade, die du für die verwendete Anwendung sicher kennst; erfinde keine Menübezeichnungen, sondern verweise im Zweifel auf die Hilfe des jeweiligen Anbieters. Bietet die Anwendung keine GitHub-Anbindung, arbeite im Modus „ohne GitHub-Zugriff“ (siehe Abschnitt 7).
3. **Zugriff begrenzen:** Der Benutzer soll – soweit GitHub diese Auswahl anbietet – nur das für GhostWriter vorgesehene Repository freigeben. Erkläre angefragte Berechtigungen verständlich und fordere keine weitergehenden Rechte als nötig.
4. **Verbindung testen:** Lies aus dem ausgewählten Repository mindestens `README.md` und `START.md` und prüfe, ob das Repository und sein Projektinhalt erreichbar sind. Nenne das geprüfte Repository eindeutig.
5. **Schreibzugriff korrekt behandeln:** Vor der Strukturfreigabe wird kein Schreibtest durch das Anlegen oder Ändern einer Datei durchgeführt. Prüfe die verfügbaren Berechtigungen, soweit dies ohne Änderung möglich ist. Den tatsächlichen Schreibzugriff bestätigst du erst durch die erste vom Benutzer freigegebene Repository-Änderung.
6. **Fehler transparent melden:** Wenn Anmeldung, Repository-Auswahl oder Lesen fehlschlägt, erkläre konkret, was nicht funktioniert und wie der Benutzer die Verbindung prüfen kann. Behaupte niemals, Dateien gelesen, geändert oder gespeichert zu haben, wenn der Vorgang nicht erfolgreich bestätigt wurde.

Die GitHub-Verbindung der Chat-Anwendung ist die vom jeweiligen Anbieter bereitgestellte Verbindung zwischen Assistent und GitHub. Sie ist **nicht automatisch** eine eigens entwickelte GhostWriter-Schnittstelle (API, MCP-Server oder GitHub-App). Eine solche maßgeschneiderte Schnittstelle ist ein späterer Entwicklungsschritt. Ein Markdown-Link allein lädt den Inhalt von `START.md` nicht automatisch in den Chat.

7. **Erstes Buch anlegen:** Ist der Standard-Branch noch leer (keine Kapitel, keine `buch/*`-Branches), zeige nach dem Onboarding das Bücherregal bzw. direkt das Formular „Neues Buch“ (Abschnitt 0, „Neues Buch“). Der Einstiegsdialog (Abschnitte 2–7) läuft danach auf dem neuen Branch `buch/<slug>`; Arbeitstitel und Autor sind dann schon bekannt. Auf den Standard-Branch kommt kein Buch.

8. **Assistenten-Profil:** Nach dem ersten Buch (bzw. im Einzelbuch nach der Strukturfreigabe) das Profil anbieten (Abschnitt 0, „Assistenten-Profil“): Git-Benutzer, Autor, Standard-Erzählstimme. Daraus entsteht der persönliche Skill, der beim nächsten Einbinden des Repositorys automatisch geladen wird. Ablehnen ist in Ordnung; später geht es mit `Profil`.

**Fähigkeiten offenlegen:** Teile dem Benutzer zu Beginn kurz mit, welche Fähigkeiten dir in dieser Umgebung tatsächlich zur Verfügung stehen: GitHub lesen, GitHub schreiben, Internetrecherche, Dateien ausgeben. Fehlt eine Fähigkeit, sage das offen und arbeite mit der beschriebenen Ausweichlösung weiter, statt sie vorzutäuschen.

## 2. Ziel und Arbeitsweise

Entwickle gemeinsam mit mir ein Buchprojekt. Arbeite dia…26857 tokens truncated…   n, ch = chapter_number(config, args.where)
    items = [{'ITEM_ID': s['id'], 'ITEM_NUMBER': f'{n}.{i}', 'ITEM_TITLE': s['title']}
             for i, s in enumerate(ch['sections'], start=1)]
    return reorder(args, 'section', f'Abschnittsreihenfolge in Kapitel {n} ändern', items, ch['id'], n)


def update_info(base, config):
    """(automatisch ja/nein, Versionstext, Hinweis) aus ghostwriter.yml, Manifest und .ghostwriter/update.yml."""
    auto = (config.get('updates') or {}).get('auto') is not False
    def read_yaml(path):
        try:
            return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        except (OSError, yaml.YAMLError):
            return {}
    version = read_yaml(base / 'ghostwriter-manifest.yml').get('version') or read_yaml(ROOT / 'ghostwriter-manifest.yml').get('version')
    state = read_yaml(base / '.ghostwriter' / 'update.yml')
    text = f'Installiert: GhostWriter {version or "unbekannt"}'
    when = str(state.get('updated_at') or '')
    if re.match(r'\d{4}-\d{2}-\d{2}', when):
        text += f' · zuletzt aktualisiert am {when[8:10]}.{when[5:7]}.{when[:4]}'
    mig = state.get('migration') or {}
    if mig.get('to') is not None:
        text += f' · Daten auf Version {mig["to"]} umgestellt'
        if mig.get('changes'):
            text += ' (' + '; '.join(mig['changes'][:3]) + ('; …' if len(mig['changes']) > 3 else '') + ')'
    hint = ''
    if state.get('skipped_workflows'):
        hint = (f'{len(state["skipped_workflows"])} Workflow-Datei(en) wurden nicht aktualisiert; dafür braucht das '
                'Repository das Secret GHOSTWRITER_UPDATE_TOKEN (docs/UPDATES.md).')
    return auto, text, hint


def output_value(key, value):
    label, names = OUTPUT_LABELS[key]
    if isinstance(value, bool):
        return 'ja' if value else 'nein'
    if key == 'formats':
        return ', '.join(names.get(v, v) for v in value)
    if key in ('font_size',):
        return str(value).replace('.', ',') + ' pt'
    if key == 'line_spacing':
        return str(value).replace('.', ',') + '-fach'
    return names.get(value, str(value)) if names else str(value)


OUTPUT_GROUPS = [('Seite', ['page_size', 'margins', 'chapter_start', 'running_heads', 'page_numbers']),
                 ('Schrift', ['font', 'font_size', 'heading_font', 'initials', 'glossary_marks']),
                 ('Absatz', ['line_spacing', 'paragraph', 'hyphenation']),
                 ('Titelei', ['title_page', 'imprint', 'toc', 'toc_depth']),
                 ('Formate', ['formats'])]
PUBLICATION_LABELS = [('publisher', 'Verlag', '„Selbstverlag“ oder Name des Verlags'),
                      ('isbn_print', 'ISBN Druckausgabe', 'ISBN-13 mit Prüfziffer'),
                      ('isbn_ebook', 'ISBN E-Book', 'ISBN-13 mit Prüfziffer'),
                      ('rights', 'Rechtehinweis', 'z. B. „Alle Rechte vorbehalten.“')]


TEMPLATE_DE = {'classic': 'klassisch', 'modern': 'modern', 'plain': 'schlicht'}


def output_view(base, config, args):
    """Formular „Ausgabeoptionen“ (#68): Vorlage ausgabeoptionen bzw. Textfassung."""
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    pub = config.get('publication') or {}
    if not args.text:
        import build_cover
        blurb, bio = build_cover.back_texts(base)
        data = {'typesetting': ts, 'publication': pub, 'print': config.get('print') or {}, 'cover': config.get('cover') or {},
                'blurb': blurb, 'author_bio': bio}
        return fill('ausgabeoptionen.html', {'OUTPUT_JSON': json.dumps(data, ensure_ascii=False)})
    lines = ['### 🖨️ Ausgabeoptionen', '', 'Wie Auflagen und Probedrucke aussehen. Geänderte Werte gelten ab dem nächsten '
             'Probedruck; ohne Angabe bleibt alles wie bisher.', '']
    for group, keys in OUTPUT_GROUPS:
        lines += [f'**{group}**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|']
        for k in keys:
            label, names = OUTPUT_LABELS[k]
            if isinstance(TYPESETTING_DEFAULT[k], bool):
                options = 'ja, nein'
            elif k == 'font_size':
                options = '10, 10,5, 11, 11,5, 12'
            elif k == 'line_spacing':
                options = '1,0, 1,1, 1,2, 1,3, 1,5'
            elif k == 'formats':
                options = 'PDF, Druck-PDF, Umschlag, DOCX, EPUB (mehrere, mit Komma)'
            else:
                options = ', '.join(names.values())
            lines.append(f'| {label} | {output_value(k, ts[k])} | {options} |')
        lines.append('')
    lines += ['**Angaben im Impressum**', '', '| Feld | Aktueller Wert | Hinweis |', '|---|---|---|']
    lines += [f'| {label} | {pub.get(k) or "–"} | {hint} |' for k, label, hint in PUBLICATION_LABELS]
    pr, cv = config.get('print') or {}, config.get('cover') or {}
    prof = {'kdp': 'Amazon KDP', 'bod': 'Books on Demand', 'custom': 'eigene Werte'}
    paper = {'white': 'weiß', 'cream': 'creme', 'premium_color': 'Premiumfarbe'}
    spine = (f'{pr["spine_mm"]} mm (fest)' if pr.get('spine_mm') is not None else
             f'aus Seitenzahl × {pr["paper_mm_per_page"]} mm' if pr.get('paper_mm_per_page') else
             'aus Seitenzahl und Papier' if pr.get('profile') == 'kdp' else '–')
    lines += ['', '**Druck**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
              f'| Druckprofil | {prof.get(pr.get("profile"), "–")} | Amazon KDP, Books on Demand, eigene Werte |',
              f'| Papier | {paper.get(pr.get("paper"), "weiß" if pr.get("profile") == "kdp" else "–")} | weiß, creme, Premiumfarbe (nur KDP) |',
              f'| Rückenbreite | {spine} | Zahl in mm (BoD: aus dem BoD-Rechner) |',
              f'| Beschnitt | {pr.get("bleed_mm", "Vorgabe des Profils")}{" mm" if "bleed_mm" in pr else ""} | Zahl in mm |',
              f'| Schnittmarken | {"ja" if pr.get("crop_marks") else "nein"} | ja, nein |', '',
              '**Umschlag**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
              f'| Vorlage | {TEMPLATE_DE.get(cv.get("template", "classic"), "")} | klassisch, modern, schlicht |',
              f'| Hintergrund | {cv.get("background", "#1F2A44")} | Farbe als #RRGGBB |',
              f'| Schriftfarbe | {cv.get("text_color", "#FFFFFF")} | Farbe als #RRGGBB |',
              f'| Bild vorne | {cv.get("image") or "–"} | Datei unter cover/ (JPG, PNG, mind. 300 dpi) |',
              f'| Autorenbild | {cv.get("author_image") or "–"} | Datei unter cover/ |',
              f'| Preis | {cv.get("price") or "–"} | z. B. 18,00 € (D) |',
              f'| Rückentext | {"von unten nach oben" if cv.get("spine_direction") == "up" else "von oben nach unten"} | von oben nach unten, von unten nach oben |',
              '', '<sub>Klappentext und Autorentext stehen in `cover/rueckseite.md` (`## Klappentext`, `## Über …`). '
              'Die Vorgaben der Druckanbieter ändern sich; Maße vor dem Hochladen mit deren Rechner abgleichen.</sub>',
              '', FORM_HINT]
    return '\n'.join(lines) + '\n'


def ai_disc_text(config):
    s = (config.get('ai_disclosure') or {})
    mode = s.get('mode', 'none')
    if mode == 'none':
        return 'keine'
    place = {'imprint': 'im Impressum', 'foreword': 'im Vorwort', 'afterword': 'im Nachwort', 'page': 'eigene Seite'}
    return {'short': 'kurz', 'detailed': 'ausführlich', 'custom': 'eigener Text'}[mode] + ', ' + \
        place.get(s.get('placement', 'imprint'), '') + ('' if s.get('text') else ' (Wortlaut offen)')


def project_settings_view(base, config, args):
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    wf = config.get('workflow') or {}
    fixed = []
    for block, key, label in FIXED_RULES:
        v = (config.get(block) or {}).get(key)
        if v is None:
            continue
        text = FIXED_TEXT.get(v, str(v))
        fixed.append({'FIXED_LABEL': label, 'FIXED_VALUE': text if isinstance(v, bool) else f'{text} ({v})'})
    fc = wf.get('fact_checking_default') or 'optional'
    upd_auto, upd_text, upd_hint = update_info(base, config)
    auto_merge = (config.get('changes') or {}).get('auto_merge') is True
    lim = config.get('limits') or {}
    lim_sum = limit_summary(base, config)
    if args.text:
        page = {'a5': 'A5 (14,8 × 21 cm)', '12x19': '12 × 19 cm', '13.5x21.5': '13,5 × 21,5 cm', 'a4': 'A4'}
        jn = lambda v: 'ja' if v else 'nein'
        return '\n'.join(['### ⚙️ Projekteinstellungen', '', '**🔒 Feste Regeln** *(nur im Chat mit ausdrücklicher Bestätigung änderbar)*', '',
                           '| Regel | Wert |', '|---|---|'] + [f'| {f["FIXED_LABEL"]} | {f["FIXED_VALUE"]} |' for f in fixed]
                          + ['', '**Bearbeitbar**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
                             f'| Faktencheck | {FC_TEXT[fc]} | aus, optional, angefordert |',
                             f'| Seitenformat | {page.get(ts["page_size"], ts["page_size"])} | A5, 12×19, 13,5×21,5, A4 |',
                             f'| Schrift | {"Serifenschrift" if ts["font"] == "serif" else "serifenlos"} | Serif, Serifenlos |',
                             f'| Schriftgröße | {str(ts["font_size"]).replace(".", ",")} pt | 10, 10,5, 11, 11,5, 12 |',
                             f'| Titelseite | {jn(ts["title_page"])} | ja, nein |', f'| Impressum | {jn(ts["imprint"])} | ja, nein |',
                             f'| Inhaltsverzeichnis | {jn(ts["toc"])} | ja, nein |',
                             f'| Verzeichnistiefe | {"nur Kapitel" if ts["toc_depth"] == 1 else "Kapitel und Abschnitte"} | Kapitel, Abschnitte |',
                             f'| Updates automatisch | {jn(upd_auto)} | ja, nein |',
                             f'| Änderungen sofort übernehmen | {jn(auto_merge)} | ja, nein |',
                             f'| KI-Budget je Monat | {lim.get("ai_budget_monthly") or "–"} | Betrag in Projektwährung, leer = keins |',
                             f'| Actions-Minuten je Monat | {lim.get("actions_minutes_monthly") or "–"} | Minuten, leer = nicht prüfen |',
                             f'| KI-Angabe im Buch | {ai_disc_text(config)} | Formular `KI-Angabe` |',
                             '| Weitere Ausgabeoptionen | Ränder, Zeilenabstand, Kolumnentitel, Formate, ISBN … | Formular `Ausgabe` |',
                             '', f'<sub>{upd_text} · Limits: {lim_sum}</sub>'] + ([f'', f'> ⚠️ {upd_hint}'] if upd_hint else []) + ['', FORM_HINT]) + '\n'
    def b(v):
        return 'true' if v else 'false'
    return fill('projekteinstellungen.html', {'FACT_CHECK_DEFAULT': fc, 'PAGE_SIZE': ts['page_size'], 'FONT': ts['font'],
                                              'FONT_SIZE': str(ts['font_size']).rstrip('0').rstrip('.') if isinstance(ts['font_size'], float) else str(ts['font_size']),
                                              'TITLE_PAGE': b(ts['title_page']), 'IMPRINT': b(ts['imprint']), 'TOC': b(ts['toc']),
                                              'TOC_DEPTH': str(ts['toc_depth']), 'UPDATES_AUTO': b(upd_auto), 'CHANGES_AUTO_MERGE': b(auto_merge),
                                              'GW_VERSION_TEXT': upd_text, 'GW_UPDATE_HINT': upd_hint,
                                              'AI_DISCLOSURE_TEXT': ai_disc_text(config),
                                              'LIMIT_BUDGET': num_text(lim.get('ai_budget_monthly')),
                                              'LIMIT_MINUTES': num_text(lim.get('actions_minutes_monthly')),
                                              'LIMIT_SUMMARY': lim_sum}, {'FIXED': fixed})


def num_text(v):
    if v in (None, ''):
        return ''
    return str(int(v)) if float(v).is_integer() else str(v)


def ai_disclosure_view(base, config, args):
    """Formular „KI-Angabe im Buch“ (#78), Vorlage ki-angabe bzw. Textfassung: Einstellung, Vorschlag, Hinweis."""
    import ai_disclosure as ad
    s = ad.settings(config)
    proposal = ad.suggest(base, config) if s['mode'] in ('none', 'short', 'detailed') else ''
    used = ad.usage(base)
    names = ad.provider_names()
    if not args.text:
        kinds = {i['kind'] for _, i in matter_items(config)}
        missing = [k for k in ('foreword', 'afterword') if k not in kinds]
        if not (config.get('typesetting') or {}).get('imprint', True):
            missing.append('imprint')
        values = {'AI_MODE': s['mode'], 'AI_PLACEMENT': s['placement'], 'AI_NAME_SERVICES': str(bool(s['name_services'])).lower(),
                  'AI_TEXT': s.get('text') or '',
                  'AI_USED_TEXT': ' · '.join(f'{t}: {ad.service_text(ids, names)}' for t, ids in used.items()),
                  'AI_PROPOSAL_SHORT': ad.suggest(base, config, 'short', False),
                  'AI_PROPOSAL_SHORT_NAMED': ad.suggest(base, config, 'short', True),
                  'AI_PROPOSAL_DETAILED': ad.suggest(base, config, 'detailed', False),
                  'AI_PROPOSAL_DETAILED_NAMED': ad.suggest(base, config, 'detailed', True),
                  'AI_PLACES_MISSING': ','.join(missing), 'AI_LEGAL_HINT': ad.LEGAL_HINT}
        return fill('ki-angabe.html', values)
    mode_de = {'none': 'keine', 'short': 'kurz (ein Satz)', 'detailed': 'ausführlich (je Aufgabe)', 'custom': 'eigener Text'}
    place_de = {'imprint': 'Impressum', 'foreword': 'Vorwort (am Ende)', 'afterword': 'Nachwort (am Ende)', 'page': 'eigene Seite am Ende'}
    lines = ['### 🤖 KI-Angabe im Buch', '',
             'Ob und wie im Buch steht, wie bei diesem Buch KI genutzt wurde. Der Hinweis auf die Entwicklung von '
             'GhostWriter kommt nie ins Buch.', '',
             '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
             f'| Angabe | {mode_de[s["mode"]]} | keine, kurz, ausführlich, eigener Text |',
             f'| Ort | {place_de[s["placement"]]} | Impressum, Vorwort, Nachwort, eigene Seite |',
             f'| Dienste nennen | {"ja" if s["name_services"] else "nein"} | ja, nein |', '']
    if used:
        lines += ['**Laut den Läufen genutzt:** ' + ' · '.join(
            f'{t}: {ad.service_text(ids, names)}' for t, ids in used.items()), '']
    else:
        lines += ['*Bisher sind keine KI-Läufe protokolliert.*', '']
    if s['mode'] != 'none':
        lines += ['**Wortlaut im Buch' + (' (bestätigt)' if s['text'] else ' – noch nicht bestätigt') + ':**', '']
        lines += ['> ' + l if l else '>' for l in (s['text'] or '*(leer)*').splitlines()] + ['']
    if proposal and proposal != s['text'] and s['mode'] in ('short', 'detailed'):
        lines += ['**Vorschlag aus den Läufen:**', ''] + ['> ' + l if l else '>' for l in proposal.splitlines()] + ['']
    lines += [f'<sub>⚖️ {ad.LEGAL_HINT}</sub>', '', '---',
              'Antworte mit `Angabe: …`, `Ort: …`, `Dienste nennen: ja|nein` oder `Text: …` (eigener Wortlaut)'
              + (' · `OK` übernimmt den Vorschlag' if proposal and s['mode'] in ('short', 'detailed') else '')
              + ' · `X` bricht ab']
    return '\n'.join(lines) + '\n'


CHAPTER_RESEARCH_DIR = 'research/kapitel'   # workflow.yml, runs.chapter_research


def run_parts(path):
    """(Kopf, {Überschrift: Text}) einer Lauf-Datei."""
    text = path.read_text(encoding='utf-8')
    head, body = {}, text
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if m:
        head = yaml.safe_load(m.group(1)) or {}
        body = text[m.end():]
    parts = {k.strip(): v.strip() for k, v in re.findall(r'(?m)^## ([^\n]+)\n(.*?)(?=^## |\Z)', body, re.S)}
    return head, parts


def chapter_research_view(base, config, args):
    """Formular „Kapitelrecherche“: Ziel und Kurzbeschreibung ändern, Recherche für das Kapitel starten."""
    n, ch = chapter_number(config, args.where)
    _, summary, goal = chapter_readme(base, ch)
    runs = sorted((base / ch['path'] / CHAPTER_RESEARCH_DIR).glob('run-*.md'))
    last_head, last = run_parts(runs[-1]) if runs else ({}, {})
    draft = {}
    if getattr(args, 'draft', None):
        draft = json.loads(Path(args.draft).read_text(encoding='utf-8'))
    ap = config.get('ai_providers') or {}
    pid = (ap.get('research') or {}).get('provider') or (ap.get('default') or {}).get('provider') or 'chat'
    catalog = yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8'))
    names = {x['id']: x.get('name', x['id']) for x in catalog.get('providers') or []}
    provider = 'aktueller Chat' if pid == 'chat' else names.get(pid, pid).split(' (')[0]
    when = str(last_head.get('date') or '')
    count = (f'{len(runs)} Lauf' if len(runs) == 1 else f'{len(runs)} Läufe') if runs else 'noch keine Kapitelrecherche'
    if runs and re.match(r'\d{4}-\d{2}-\d{2}', when):
        count += f', zuletzt am {when[8:10]}.{when[5:7]}.{when[:4]}'
    clean = lambda v: '' if (v or '').strip() in ('', 'Offen.', '–') else v.strip()
    chapters = config['structure']['chapters']
    def neighbour(k):
        if 1 <= k <= len(chapters):
            other = chapters[k - 1]
            return f'Kapitel {k} · {other["title"]}', chapter_readme(base, other)[1]
        return '', ''
    prev_label, prev_summary = neighbour(n - 1)
    next_label, next_summary = neighbour(n + 1)
    def weight(key):
        v = draft.get(key, last_head.get(key, 2))
        return v if isinstance(v, int) and 0 <= v <= 3 else 2
    current_goal = draft.get('goal', goal)
    if 'task' in draft:
        task = draft.get('task') or ''
    elif 'task' in last_head:
        task = last_head.get('task') or ''
    elif 'goal_search' in last_head:            # Läufe vor 0.19: goal_search true/false
        task = 'goal' if last_head.get('goal_search') is True else ''
    else:
        task = '' if current_goal else 'goal'
    task = task if task in ('goal', 'sections', 'summary') else ''
    existing = {sec['title'].strip().lower() for sec in ch['sections']}
    proposals = []
    for line in clean(last.get('Vorschlag: Abschnitte')).splitlines():
        m = re.match(r'\s*[-*]\s+(.+?)(?::\s+(.*))?$', line)
        if m and m.group(1).strip().lower() not in existing:
            proposals.append({'SUG_TITLE': m.group(1).strip(), 'SUG_SUMMARY': (m.group(2) or '').strip()})
    k = len(ch['sections'])
    note = ('Das Kapitel hat noch keine Abschnitte; ausgewählte werden in dieser Reihenfolge angelegt.' if not k else
            f'Das Kapitel hat schon {k} Abschnitt{"" if k == 1 else "e"}. Sie bleiben unverändert; ausgewählte neue '
            'kommen ans Ende (Reihenfolge danach über „Abschnittsreihenfolge“).')
    if k and ch.get('status') == 'approved':
        note += ' Das Kapitel ist freigegeben und wird dadurch wieder „in Arbeit“.'
    values = {'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': n, 'CHAPTER_TITLE': ch['title'],
              'CHAPTER_GOAL': draft.get('goal', goal), 'CHAPTER_SUMMARY': draft.get('summary', summary),
              'RESEARCH_QUESTION': draft.get('question', last_head.get('question') or ''),
              'RESEARCH_SCOPE': draft.get('scope', last_head.get('scope') or ''),
              'RESEARCH_TASK': task, 'SECTION_COUNT': k, 'SECTIONS_NOTE': note,
              'PREV_CHAPTER': 'true' if prev_label else '', 'PREV_CHAPTER_LABEL': prev_label,
              'PREV_CHAPTER_SUMMARY': prev_summary, 'PREV_WEIGHT': weight('weight_prev'),
              'NEXT_CHAPTER': 'true' if next_label else '', 'NEXT_CHAPTER_LABEL': next_label,
              'NEXT_CHAPTER_SUMMARY': next_summary, 'NEXT_WEIGHT': weight('weight_next'),
              'RESEARCH_PROVIDER_TEXT': f'Recherche über: {provider}', 'RUN_COUNT_TEXT': count,
              'LAST_RUN': 'true' if runs else '', 'LAST_RUN_ID': last_head.get('id') or (runs[-1].stem if runs else ''),
              'LAST_RUN_TEXT': clean(last.get('Kurzfassung')),
              'SUGGESTED_GOAL': clean(last.get('Vorschlag: Ziel des Kapitels')),
              'SUGGESTED_SUMMARY': clean(last.get('Vorschlag: Kurzbeschreibung'))}
    if args.text:
        lines = [f'### 🔎 Kapitelrecherche · Kapitel {n} „{ch["title"]}“', ''] + field_table([
            ('Ziel', values['CHAPTER_GOAL']), ('Kurzbeschreibung', values['CHAPTER_SUMMARY'])])
        if values['SUGGESTED_GOAL'] or values['SUGGESTED_SUMMARY']:
            lines += ['', f'**Vorschläge aus {values["LAST_RUN_ID"]}:**']
            if values['SUGGESTED_GOAL']:
                lines += [f'- Ziel: {values["SUGGESTED_GOAL"]} · `VZ` übernehmen']
            if values['SUGGESTED_SUMMARY']:
                lines += [f'- Kurzbeschreibung: {values["SUGGESTED_SUMMARY"]} · `VK` übernehmen']
        if values['LAST_RUN_TEXT']:
            lines += ['', f'> {values["LAST_RUN_TEXT"]}']
        if proposals:
            lines += ['', f'**Vorgeschlagene Abschnitte aus {values["LAST_RUN_ID"]}:**', '']
            lines += [f'{i}. **{x["SUG_TITLE"]}**' + (f' – {x["SUG_SUMMARY"]}' if x['SUG_SUMMARY'] else '')
                      for i, x in enumerate(proposals, start=1)]
            lines += ['', f'<sub>{note}</sub> Anlegen: `AS 1, 3` (Nummern der Vorschläge).']
        wtext = ['nicht berücksichtigen', 'abgrenzen', 'anschließen', 'stark einbeziehen']
        ctx = []
        if prev_label:
            ctx.append(f'| Vorher | {prev_label} | {values["PREV_WEIGHT"]} · {wtext[values["PREV_WEIGHT"]]} |')
        if next_label:
            ctx.append(f'| Nachher | {next_label} | {values["NEXT_WEIGHT"]} · {wtext[values["NEXT_WEIGHT"]]} |')
        if ctx:
            lines += ['', '**Zusammenhang**', '', '| | Kapitel | Gewichtung |', '|---|---|---|'] + ctx
        tname = {'goal': 'Ziel des Kapitels recherchieren', 'sections': 'Abschnitte erstellen', 'summary': 'Kurzbeschreibung erstellen'}
        lines += ['', f'Aufgabe: **{tname.get(task, "keine (nur Fragestellung)")}**',
                  '', f'<sub>{values["RESEARCH_PROVIDER_TEXT"]} · {count}</sub>', '',
                  'Ändern: je Zeile `Ziel: …` bzw. `Kurzbeschreibung: …`. Recherche starten: `Frage: …` (optional `Schwerpunkte: …`, '
                  '`Aufgabe: Ziel|Abschnitte|Kurzbeschreibung|keine`, `Vorher: 0–3`, `Nachher: 0–3`; 0 nicht berücksichtigen, 1 abgrenzen, 2 anschließen, 3 stark einbeziehen). `X` bricht ab.']
        return '\n'.join(lines) + '\n'
    return fill('kapitelrecherche.html', values, {'SUGGESTED_SECTIONS': proposals})


# ---------- Bücherregal (#37) ----------

LIBRARY_FILE = 'library.json'


def library_data(base, args):
    """library.json (--library oder im Projektordner); fehlt sie, live aus den Branches (scripts/library.py)."""
    path = Path(args.library) if getattr(args, 'library', None) else base / LIBRARY_FILE
    if path.is_file():
        return json.loads(path.read_text(encoding='utf-8'))
    import library
    data = library.build_library(cwd=base)
    if not data.get('books'):   # ohne Remote (lokale Bibliothek): die lokalen Branches
        data = library.build_library('refs/heads', base)
    return data


def de_date(iso):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', iso or '')
    return f'{m.group(3)}.{m.group(2)}.{m.group(1)}' if m else ''


def plural(n, one, many):
    return f'{n} {one if n == 1 else many}'


def book_row(b):
    ready = b['status'] == 'ready'
    st, sa = b.get('sections_total', 0), b.get('sections_approved', 0)
    progress = (f'{sa} von {plural(st, "Abschnitt", "Abschnitten")} freigegeben · '
                f'{b.get("chapters_approved", 0)} von {plural(b.get("chapters_total", 0), "Kapitel", "Kapiteln")}') if ready else 'Gliederung noch offen'
    ed = b.get('current_edition') or 0
    return {'BOOK_BRANCH': b['branch'], 'BOOK_TITLE': b['title'] or b['title_short'] or 'Ohne Titel',
            'BOOK_TITLE_SHORT': b['title_short'] or b['branch'].split('/')[-1],
            'BOOK_AUTHOR_TEXT': f'von {b["author"]}' if b.get('author') else '',
            'BOOK_STATE': 'ready' if ready else 'setup', 'BOOK_STATE_TEXT': 'eingerichtet' if ready else 'im Aufbau',
            'BOOK_PROGRESS': round(100 * sa / st) if st else 0, 'BOOK_PROGRESS_TEXT': progress,
            'BOOK_EDITION_TEXT': f'Auflage {ed}' if ed else 'noch keine Auflage',
            'BOOK_COST': (b.get('cost') or {}).get('text') or money(0, False),
            'BOOK_PENDING_TEXT': f'{plural(b["pending"], "Änderung", "Änderungen")} offen' if b.get('pending') else '',
            'BOOK_UPDATED_TEXT': f'{"zuletzt geändert" if ready else "angelegt"} am {de_date(b.get("updated_at"))}' if b.get('updated_at') else ''}


def library_series(base, data):
    """Serien (#116) aus library.json bzw. vom Standard-Branch: [{id, title, …, volumes: [branch]}]."""
    if 'series' in data:
        return data['series'] or []
    import series
    return [dict(s, volumes=series.volumes(s)) for s in series.load_all(base).values()]


def library_view(base, config, args):
    data = library_data(base, args)
    books = data.get('books') or []
    by_branch = {b['branch']: b for b in books}
    ser = library_series(base, data)
    rows, seen = [], set()
    # Bücher einer Serie zuerst, gruppiert und in Bandreihenfolge (#116); danach die übrigen
    for si, s in enumerate(ser, start=1):
        for n, br in enumerate(s['volumes'], start=1):
            if br in by_branch:
                r = book_row(by_branch[br])
                r.update({'BOOK_SERIES': s['id'], 'BOOK_SERIES_TITLE': s['title'], 'BOOK_SERIES_KEY': f'S{si}',
                          'BOOK_VOLUME_TEXT': f'Band {n}'})
                rows.append(r)
                seen.add(br)
    for b in books:
        if b['branch'] not in seen:
            rows.append(dict(book_row(b), BOOK_SERIES='', BOOK_SERIES_TITLE='', BOOK_SERIES_KEY='', BOOK_VOLUME_TEXT=''))
    empty_series = [{'S_ID': s['id'], 'S_TITLE': s['title'], 'S_KEY': f'S{i}'} for i, s in enumerate(ser, start=1)
                    if not any(br in by_branch for br in s['volumes'])]
    count = plural(len(rows), 'Buch', 'Bücher') + (f' · {plural(len(ser), "Serie", "Serien")}' if ser else '')
    if args.text:
        out = [f'### 📚 Bücherregal', f'{repo_label(args)} · {count}', '']
        if rows:
            out += ['| # | Buch | Status | Fortschritt | Auflage | Kosten |', '|--:|---|---|---|---|--:|']
            group = None
            for i, r in enumerate(rows, 1):
                if r['BOOK_SERIES'] != group:
                    group = r['BOOK_SERIES']
                    label = f'📚 **Serie „{r["BOOK_SERIES_TITLE"]}“** (`{r["BOOK_SERIES_KEY"]}`)' if group else '**Einzelne Bücher**'
                    out.append(f'| | {label} | | | | |')
                vol = f'{r["BOOK_VOLUME_TEXT"]}: ' if r['BOOK_VOLUME_TEXT'] else ''
                out.append(f'| {i} | {vol}**{r["BOOK_TITLE"]}** ({r["BOOK_TITLE_SHORT"]}){" · ⏳ " + r["BOOK_PENDING_TEXT"] if r["BOOK_PENDING_TEXT"] else ""} | '
                           f'{"✅ eingerichtet" if r["BOOK_STATE"] == "ready" else "🚧 im Aufbau"} | {r["BOOK_PROGRESS_TEXT"]} | {r["BOOK_EDITION_TEXT"]} | {r["BOOK_COST"]} |')
        else:
            out += ['*Hier steht noch kein Buch.*']
        if empty_series:
            out += ['', 'Serien ohne Band: ' + ', '.join(f'„{s["S_TITLE"]}“ (`{s["S_KEY"]}`)' for s in empty_series)]
        items = ([('1' if len(rows) == 1 else f'1–{len(rows)}', 'Buch öffnen')] if rows else [])
        if ser:
            items.append(('S1' if len(ser) == 1 else f'S1–S{len(ser)}', 'Serie öffnen'))
        items += [('N', 'Neues Buch'), ('NS', 'Neue Serie'), ('D', 'Daten')]
        out += ['', '---', menu(items)]
        return '\n'.join(out) + '\n'
    blocks = {'BOOKS': rows}
    if empty_series:
        blocks['EMPTY_SERIES'] = empty_series
    return fill('buecherregal.html', {'LIBRARY_NAME': repo_label(args), 'BOOK_COUNT_TEXT': count, 'EMPTY': '' if rows else '1',
                                      'UPDATED_TEXT': ''}, blocks)


SERIES_KIND_DE = {'continuous': 'durchgehende Handlung', 'standalone': 'eigenständige Bände'}


def find_series(base, data, key):
    ser = library_series(base, data)
    for i, s in enumerate(ser, start=1):
        if key in (s['id'], f'S{i}', f's{i}') or (key or '').lower() == s.get('title', '').lower():
            return s
    raise SystemExit(f'Serie „{key}“ nicht gefunden')


def series_view(base, config, args):
    """Seite „Serie“ (#116, Vorlage serie): Bände in Reihenfolge, Bücher ohne Serie zum Hinzufügen."""
    data = library_data(base, args)
    s = find_series(base, data, args.where)
    by_branch = {b['branch']: b for b in data.get('books') or []}
    in_any = {br for x in library_series(base, data) for br in x['volumes']}
    vols = []
    for n, br in enumerate(s['volumes'], start=1):
        b = by_branch.get(br)
        r = book_row(b) if b else {'BOOK_BRANCH': br, 'BOOK_TITLE': br, 'BOOK_TITLE_SHORT': br.split('/')[-1], 'BOOK_STATE': 'setup',
                                   'BOOK_STATE_TEXT': 'nicht gefunden', 'BOOK_PROGRESS': 0, 'BOOK_PROGRESS_TEXT': '', 'BOOK_EDITION_TEXT': ''}
        vols.append({'V_NUMBER': n, 'V_BRANCH': br, 'V_TITLE': r['BOOK_TITLE'], 'V_TITLE_SHORT': r['BOOK_TITLE_SHORT'],
                     'V_STATE': r['BOOK_STATE'], 'V_STATE_TEXT': r['BOOK_STATE_TEXT'], 'V_PROGRESS': r['BOOK_PROGRESS'],
                     'V_PROGRESS_TEXT': r['BOOK_PROGRESS_TEXT'], 'V_EDITION_TEXT': r['BOOK_EDITION_TEXT']})
    cands = [{'C_BRANCH': b['branch'], 'C_TITLE': b['title'] or b['title_short'] or b['branch']}
             for b in data.get('books') or [] if b['branch'] not in in_any]
    values = {'SERIES_ID': s['id'], 'SERIES_TITLE': s['title'], 'SERIES_SUBTITLE': s.get('subtitle') or '',
              'SERIES_KIND_TEXT': SERIES_KIND_DE.get(s.get('kind'), ''), 'SERIES_DESCRIPTION': s.get('description') or '',
              'VOLUME_COUNT_TEXT': plural(len(vols), 'Band', 'Bände'), 'LIBRARY_NAME': repo_label(args)}
    import series as series_mod   # gemeinsame Figuren und Begriffe (Stufe 2)
    schars = []
    for c in series_mod.characters(base, s['id']):
        h = character_file(base, c)[0]
        schars.append({'SC_ID': c['id'], 'SC_NAME': c['name'], 'SC_ROLE': ROLE_DE.get(h.get('role'), ''), 'SC_SHORT': h.get('short', '')})
    sterms = [{'ST_TERM': x['term'], 'ST_TEXT': x['text']} for x in series_mod.glossary(base, s['id'])]
    om = series_mod.omnibus(base, s['id'])   # Sammelband (Stufe 4)
    if om:
        n = int(om.get('current_edition') or 0)
        values.update({'OMNIBUS_STATE': om.get('status', 'draft'), 'OMNIBUS_TITLE': om.get('title', ''),
                       'OMNIBUS_TEXT': f'{plural(len(om.get("volumes") or []), "Band", "Bände")} · '
                                       + ('freigegeben' if om.get('status') == 'approved' else 'Entwurf, nicht freigegeben')
                                       + (f' · Auflage {n}' if n else ' · noch keine Auflage')})
    if args.text:
        out = [f'### 📚 Serie „{s["title"]}“', ' · '.join(x for x in (values['SERIES_SUBTITLE'], values['SERIES_KIND_TEXT'],
                                                                  values['VOLUME_COUNT_TEXT']) if x), '']
        if values['SERIES_DESCRIPTION']:
            out += [f'> {values["SERIES_DESCRIPTION"]}', '']
        if vols:
            out += ['| Band | Buch | Status | Fortschritt | Auflage |', '|--:|---|---|---|---|']
            out += [f'| {v["V_NUMBER"]} | **{v["V_TITLE"]}** (`{v["V_BRANCH"]}`) | {v["V_STATE_TEXT"]} | {v["V_PROGRESS_TEXT"] or "–"} | {v["V_EDITION_TEXT"] or "–"} |' for v in vols]
        else:
            out += ['*Noch kein Band.*']
        if cands:
            out += ['', 'Ohne Serie: ' + ', '.join(f'{c["C_TITLE"]} (`{c["C_BRANCH"]}`)' for c in cands)]
        out += ['', f'**Figuren der Serie ({len(schars)})**', '']
        out += [f'- {c["SC_NAME"]} ({c["SC_ROLE"]}){": " + c["SC_SHORT"] if c["SC_SHORT"] else ""}' for c in schars] or ['*keine*']
        out += ['', f'**Begriffe der Serie ({len(sterms)})**', '']
        out += [f'- {x["ST_TERM"]}: {x["ST_TEXT"]}' for x in sterms] or ['*keine*']
        out += ['', 'Gelten in allen Bänden; ein Band kann eine eigene Kopie führen. `+ Figur: Name` bzw. `+ Begriff: Erklärung` '
                'nimmt etwas in die Serie auf.']
        out += ['', f'**Sammelband:** „{values["OMNIBUS_TITLE"]}“ · {values["OMNIBUS_TEXT"]} · `SB` bearbeiten'
                if om else '**Sammelband:** noch keiner · `SB` anlegen']
        items = ([('1' if len(vols) == 1 else f'1–{len(vols)}', 'Band öffnen')] if vols else [])
        items += ([('H', 'Band hinzufügen')] if cands else []) + ([('R', 'Reihenfolge ändern'), ('ENT', 'Band entfernen')] if vols else [])
        items += [('NB', 'Neues Buch in dieser Serie'), ('B', 'Serie bearbeiten'), ('FV', '👤 Figuren aus den Texten aller Bände vorschlagen'),
                  ('Ü', 'Bücherregal')]
        out += ['', '---', menu(items)]
        return '\n'.join(out) + '\n'
    blocks = {'VOLUMES': vols}
    if cands:
        blocks['CANDIDATES'] = cands
    if schars:
        blocks['SERIES_CHARACTERS'] = schars
    if sterms:
        blocks['SERIES_TERMS'] = sterms
    return fill('serie.html', values, blocks)


KEEP_DE = {'dedication': 'Widmung', 'foreword': 'Vorwort', 'prologue': 'Prolog', 'epilogue': 'Epilog',
           'afterword': 'Nachwort', 'acknowledgments': 'Danksagung'}


def scope_text(scope, config=None):
    if scope in (None, '', 'book', 'buch'):
        return 'ganzes Buch'
    if re.fullmatch(r'\d+', scope):
        return f'Kapitel {scope}'
    if re.fullmatch(r'\d+\.\d+', scope):
        return f'Abschnitt {scope}'
    if scope.startswith('ser-'):
        return 'alle Bände der Serie'
    item = find_matter(config or {'structure': {}}, scope) if config else None
    return item['title'] if item else scope


FIELD_DE = {'age': 'Alter', 'appearance': 'Aussehen', 'voice': 'Sprechweise', 'short': 'Kurz', 'traits': 'Eigenschaften'}


def character_suggest_view(base, config, args):
    """Vorschläge „Figuren aus dem Text“ (#53, Vorlage figuren-vorschlag). --draft: JSON (Datei oder Text) des
    Assistenten mit scope und items [{name, aliases, role, short, age, appearance, traits, voice, relations,
    sections, evidence [{where, quote}]}]; where = Bereich (book, N, N.M, Teil bzw. ser-…)."""
    raw = args.draft or '{}'
    data = json.loads(Path(raw).read_text(encoding='utf-8') if Path(raw).is_file() else raw)
    scope = data.get('scope') or args.where or 'book'
    is_series = str(scope).startswith('ser-')
    if is_series:   # Serienebene: auf dem Standard-Branch
        import series as series_mod
        s, _ = series_mod.get(base, scope)
        known = series_mod.characters(base, s['id'])
        ser = {'id': s['id'], 'title': s['title']}
        find = lambda n: next((c for c in known if n.strip().casefold() in (c['id'], c['name'].casefold())), None)
    else:
        ser = config.get('_series') or {}
        known = character_items(config)
        find = lambda n: find_character(config, n)
    rows = []
    for i, it in enumerate(data.get('items') or []):
        hit = None
        for n in [it.get('name', '')] + list(it.get('aliases') or []):
            hit = hit or (find(n) if n else None)
        state = 'new' if not hit else ('series' if ('_series' in hit or is_series) else 'existing')
        details = '; '.join(x for x in (f'Alter: {it["age"]}' if it.get('age') else '', it.get('appearance') or '',
                                        ', '.join(it.get('traits') or []), f'spricht {it["voice"]}' if it.get('voice') else '') if x)
        ev = it.get('evidence') or []
        rows.append({'S_IDX': i, 'S_NAME': it.get('name', ''), 'S_ALIASES': ', '.join(it.get('aliases') or []),
                     'S_ROLE': it.get('role') if it.get('role') in ROLE_DE else 'supporting', 'S_SHORT': it.get('short', ''),
                     'S_DETAILS': details, 'S_SECTIONS': ', '.join(str(x) for x in it.get('sections') or []),
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in ev[:3]),
                     'S_STATE': state, 'S_EXISTING': hit['name'] if hit else '',
                     'S_STATE_TEXT': {'new': 'neu', 'existing': f'schon da: {hit["name"]}' if hit else '',
                                      'series': f'Figur der Serie: {hit["name"]}' if hit else ''}[state]})
    conflicts = '; '.join(f'{c["name"]}, {FIELD_DE.get(c["field"], c["field"])}: ' + ' / '.join(str(v) for v in c['values'])
                          for c in data.get('conflicts') or [])
    values = {'RUN_TEXT': f'Hintergrundlauf {data["run"][4:]} vom {de_date(str(data.get("created_at", "")))}' if data.get('run') else '',
              'RUN_ID': data.get('run', ''), 'CONFLICTS_TEXT': conflicts,
              'SCOPE': str(scope), 'SCOPE_TEXT': scope_text(str(scope), config), 'SERIES_ID': ser.get('id', ''),
              'SERIES_TITLE': ser.get('title', ''), 'SERIES_LEVEL': '1' if is_series else '',
              'SUGGEST_COUNT_TEXT': plural(len(rows), 'Vorschlag', 'Vorschläge')}
    if args.text:
        out = [f'### 👤 Figuren aus dem Text · {values["SCOPE_TEXT"]}', values['SUGGEST_COUNT_TEXT'] +
               (f' · Serie „{ser["title"]}“' if ser else '') + (f' · {values["RUN_TEXT"]}' if values['RUN_TEXT'] else ''), '']
        if conflicts:
            out += [f'> ⚠️ Widersprüche im Text: {conflicts}', '']
        if rows:
            out += ['| # | Figur | Rolle | Kurz | Angaben | Abschnitte | Stand |', '|--:|---|---|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | **{r["S_NAME"]}**{" (" + r["S_ALIASES"] + ")" if r["S_ALIASES"] else ""} | {ROLE_DE[r["S_ROLE"]]} | '
                    f'{r["S_SHORT"] or "–"} | {r["S_DETAILS"] or "–"} | {r["S_SECTIONS"] or "–"} | {r["S_STATE_TEXT"]} |' for r in rows]
        else:
            out += ['*Im Text wurden keine Figuren gefunden.*']
        out += ['', 'Nur aus dem Text; der Text selbst bleibt unverändert. Bekannte Figuren werden nur ergänzt (leere Felder) und zugeordnet.',
                '', '---', menu([('Übernehmen: 1, 3', 'diese übernehmen'), ('Alle', 'alle übernehmen'),
                                 ('2 = Opi', 'Vorschlag 2 mit einer bekannten Figur zusammenlegen'), ('X', 'verwerfen')]
                                + ([('Serie: 1', 'als Figur der Serie anlegen')] if ser and not is_series else []))]
        return '\n'.join(out) + '\n'
    merge = [{'M_ID': c['id'], 'M_NAME': c['name']} for c in known]
    return fill('figuren-vorschlag.html', values, {'SUGGESTIONS': rows, 'MERGE': merge})


def analysis_suggest_view(base, config, args):
    """Vorschläge eines Hintergrundlaufs (#124) zum Auswählen: --draft = analysis/<art>/run-NNN.json. Figuren gehen an
    character-suggest, die anderen Arten an ihre eigene Vorlage."""
    raw = args.draft or args.where or ''
    path = Path(raw) if Path(raw).is_file() else base / raw
    data = json.loads(path.read_text(encoding='utf-8'))
    kind = data.get('kind') or 'characters'
    if kind == 'characters':
        args.draft = str(path)
        return character_suggest_view(base, config, args)
    run_text = f'Hintergrundlauf {data["run"][4:]} vom {de_date(str(data.get("created_at", "")))}' if data.get('run') else ''
    return ANALYSIS_VIEWS[kind](base, config, args, data, run_text)


def summaries_suggest_view(base, config, args, data, run_text):
    """Kurzbeschreibung und Ziel je Kapitel und Abschnitt (Vorlage kurzbeschreibung-vorschlag): Vorschlag, bisheriger
    Text, Fundstellen. Vorangehakt sind nur Felder, die noch leer sind."""
    rows = []
    for i, it in enumerate(data.get('items') or []):
        ch = sec = None
        for c in config['structure']['chapters']:
            if it['level'] == 'chapter' and c['id'] == it['target']:
                ch = c
            for x in c['sections']:
                if it['level'] == 'section' and x['id'] == it['target']:
                    sec = x
        if it['level'] == 'chapter' and ch:
            _, cur_short, cur_goal = chapter_readme(base, ch)
        elif sec:
            _, cur_goal, cur_short, _ = section_file(base, sec)
        else:
            continue   # Kapitel bzw. Abschnitt gibt es nicht mehr
        clean = lambda v: '' if v.startswith('<') and v.endswith('>') else v   # Platzhalter aus der Vorlage
        cur_short, cur_goal = clean(cur_short), clean(cur_goal)
        rows.append({'S_IDX': i, 'S_LEVEL': it['level'], 'S_LABEL': f'Kapitel {it["number"]}' if it['level'] == 'chapter' else it['number'],
                     'S_TITLE': (ch or sec)['title'], 'S_GOAL': it.get('goal', ''), 'S_SHORT': it.get('short', ''),
                     'S_GOAL_NOW': cur_goal, 'S_SHORT_NOW': cur_short,
                     'S_GOAL_ON': '1' if it.get('goal') and not cur_goal else '', 'S_SHORT_ON': '1' if it.get('short') and not cur_short else '',
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in (it.get('evidence') or [])[:2])})
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'summaries',
              'SUGGEST_COUNT_TEXT': plural(len(rows), 'Vorschlag', 'Vorschläge'), 'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config)}
    if args.text:
        out = [f'### 📝 Kurzbeschreibung und Ziel · {values["SCOPE_TEXT"]}', values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        for r in rows:
            out += [f'**{r["S_IDX"] + 1}. {r["S_LABEL"]} {r["S_TITLE"]}**',
                    f'- Ziel: {r["S_GOAL"] or "–"}' + (f' *(bisher: {r["S_GOAL_NOW"]})*' if r['S_GOAL_NOW'] else ' *(bisher leer)*'),
                    f'- Kurz: {r["S_SHORT"] or "–"}' + (f' *(bisher: {r["S_SHORT_NOW"]})*' if r['S_SHORT_NOW'] else ' *(bisher leer)*'),
                    f'- Fundstellen: {r["S_EVIDENCE"] or "–"}', '']
        if not rows:
            out += ['*Keine Vorschläge.*', '']
        out += ['Nur aus dem Text; der Text selbst bleibt unverändert. Ohne Angabe werden nur leere Felder gefüllt.', '', '---',
                menu([('Übernehmen: 1, 3', 'diese übernehmen (nur leere Felder)'), ('Alle', 'alle leeren Felder füllen'),
                      ('Ersetzen: 2', 'auch einen vorhandenen Text ersetzen'), ('X', 'verwerfen')])]
        return '\n'.join(out) + '\n'
    return fill('kurzbeschreibung-vorschlag.html', values, {'SUGGESTIONS': rows})


def style_suggest_view(base, config, args, data, run_text):
    """Stilprofil (Vorlage stilprofil-vorschlag): je Angabe Vorschlag, bisheriger Wert aus `style`, abweichende
    Kapitel, Fundstellen; dazu die Zahlen ohne KI. Vorangehakt: Angaben, die bisher fehlen."""
    import analyze
    now = config.get('style') or {}
    rows = []
    for i, it in enumerate(data.get('items') or []):
        cur = now.get(it['field'])
        cur = ', '.join(cur) if isinstance(cur, list) else str(cur or '')
        rows.append({'S_IDX': i, 'S_FIELD': it['field'], 'S_LABEL': analyze.STYLE_DE.get(it['field'], it['field']),
                     'S_VALUE': it['value'], 'S_NOW': cur, 'S_ON': '' if cur else '1',
                     'S_VARIANTS': '; '.join(f'{v["value"]} in {", ".join(v["where"])}' for v in it.get('variants') or []),
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in (it.get('evidence') or [])[:2])})
    st = data.get('stats') or {}
    parts = []
    if st.get('sentence_length_avg') is not None:
        parts.append(f'{str(st["sentence_length_avg"]).replace(".", ",")} Wörter je Satz')
    if st.get('dialogue_share') is not None:
        parts.append(f'{round(st["dialogue_share"] * 100)} % wörtliche Rede')
    if st.get('words'):
        parts.append(f'{st["words"]} Wörter')
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'style',
              'STATS_TEXT': ' · '.join(parts), 'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(rows), 'Angabe', 'Angaben')}
    if args.text:
        out = [f'### 🪶 Stilprofil · {values["SCOPE_TEXT"]}', values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        if rows:
            out += ['| # | Angabe | Vorschlag | bisher | abweichend |', '|--:|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | {r["S_LABEL"]} | {r["S_VALUE"]} | {r["S_NOW"] or "–"} | {r["S_VARIANTS"] or "–"} |' for r in rows]
        else:
            out += ['*Keine Angaben mit Fundstelle.*']
        out += ['', f'Gezählt ohne KI: {values["STATS_TEXT"] or "–"}', '',
                'Das Stilprofil steht in `ghostwriter.yml` (`style`) und ist Vorgabe fürs Ghostwriting. Der Text bleibt unverändert.',
                '', '---', menu([('Übernehmen: 1, 2', 'diese Angaben übernehmen'), ('Alle', 'alle übernehmen'),
                                  ('3 = Präteritum', 'Angabe 3 mit anderem Wert'), ('X', 'verwerfen')])]
        return '\n'.join(out) + '\n'
    return fill('stilprofil-vorschlag.html', values, {'SUGGESTIONS': rows})


def places_suggest_view(base, config, args, data, run_text):
    """Schauplätze (Vorlage orte-vorschlag): Name, Art, ein Satz, Abschnitte, Fundstellen, Stand gegenüber
    story/places.yml; „Zusammenlegen mit“ einem vorhandenen Ort."""
    import analyze
    p = analyze.story_file(base, 'places')
    known = ((yaml.safe_load(p.read_text(encoding='utf-8')) or {}).get('places') or []) if p.is_file() else []
    rows = []
    for i, it in enumerate(data.get('items') or []):
        names = {analyze.norm(x) for x in [it['name']] + list(it.get('aliases') or [])}
        hit = next((k for k in known if names & {analyze.norm(x) for x in [k['name']] + list(k.get('aliases') or [])}), None)
        rows.append({'S_IDX': i, 'S_NAME': it['name'], 'S_ALIASES': ', '.join(it.get('aliases') or []), 'S_KIND': it.get('kind', ''),
                     'S_SHORT': it.get('short', ''), 'S_SECTIONS': ', '.join(it.get('sections') or []),
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in (it.get('evidence') or [])[:2]),
                     'S_STATE': 'existing' if hit else 'new', 'S_STATE_TEXT': f'schon da: {hit["name"]}' if hit else 'neu',
                     'S_EXISTING': hit['id'] if hit else ''})
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'places',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config), 'SUGGEST_COUNT_TEXT': plural(len(rows), 'Ort', 'Orte')}
    if args.text:
        out = [f'### 📍 Schauplätze aus dem Text · {values["SCOPE_TEXT"]}', values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        if rows:
            out += ['| # | Ort | Art | Beschreibung | Abschnitte | Stand |', '|--:|---|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | **{r["S_NAME"]}**{" (" + r["S_ALIASES"] + ")" if r["S_ALIASES"] else ""} | {r["S_KIND"] or "–"} | '
                    f'{r["S_SHORT"] or "–"} | {r["S_SECTIONS"] or "–"} | {r["S_STATE_TEXT"]} |' for r in rows]
        else:
            out += ['*Keine Schauplätze mit Fundstelle.*']
        out += ['', 'Nur aus dem Text. Übernommen wird nach `story/places.yml`; bekannte Orte werden nur ergänzt. Der Text bleibt unverändert.',
                '', '---', menu([('Übernehmen: 1, 3', 'diese übernehmen'), ('Alle', 'alle übernehmen'),
                                  ('2 = Seehaus', 'Vorschlag 2 mit einem bekannten Ort zusammenlegen'), ('X', 'verwerfen')])]
        return '\n'.join(out) + '\n'
    merge = [{'M_ID': k['id'], 'M_NAME': k['name']} for k in known]
    return fill('orte-vorschlag.html', values, {'SUGGESTIONS': rows, 'MERGE': merge})


def timeline_suggest_view(base, config, args, data, run_text):
    """Zeitleiste (Vorlage zeitleiste-vorschlag): Ereignisse in Buchreihenfolge mit Zeitangabe und Fundstelle, dazu
    die Auffälligkeiten (Zeitsprung, Widerspruch, unklar) mit Verweis auf die Ereignisse."""
    import analyze
    issues = data.get('issues') or []
    flagged = {n for x in issues for n in x['events']}
    events = [{'E_IDX': i, 'E_N': e['n'], 'E_WHERE': e['where'], 'E_WHEN': e.get('when', ''), 'E_WHAT': e['what'],
               'E_FLAG': '1' if e['n'] in flagged else '',
               'E_EVIDENCE': ' · '.join(f'„{x.get("quote", "")}“' for x in (e.get('evidence') or [])[:1])}
              for i, e in enumerate(data.get('items') or [])]
    rows = [{'I_IDX': i, 'I_KIND': x['kind'], 'I_KIND_TEXT': analyze.TIMELINE_KIND_DE.get(x['kind'], x['kind']),
             'I_EVENTS': ', '.join(map(str, x['events'])), 'I_TEXT': x['text']} for i, x in enumerate(issues)]
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'timeline',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(events), 'Ereignis', 'Ereignisse') + ' · ' + plural(len(rows), 'Auffälligkeit', 'Auffälligkeiten')}
    if args.text:
        out = [f'### 🕰️ Zeitleiste · {values["SCOPE_TEXT"]}', values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        if rows:
            out += [f'> ⚠️ **{r["I_KIND_TEXT"]}** (Ereignisse {r["I_EVENTS"]}): {r["I_TEXT"]}' for r in rows] + ['']
        if events:
            out += ['| # | Abschnitt | Wann | Was |', '|--:|---|---|---|']
            out += [f'| {e["E_N"]}{" ⚠️" if e["E_FLAG"] else ""} | {e["E_WHERE"]} | {e["E_WHEN"] or "–"} | {e["E_WHAT"]} |' for e in events]
        else:
            out += ['*Keine Ereignisse mit Fundstelle.*']
        out += ['', 'Nur aus dem Text; Auffälligkeiten sind Hinweise, entschieden wird nichts. Übernommen wird nach '
                '`story/timeline.yml`; der Text bleibt unverändert.', '', '---',
                menu([('Alle', 'alle Ereignisse und Hinweise übernehmen'), ('Ohne: 4, 7', 'alle außer diesen Ereignissen'),
                      ('Hinweise ohne: 2', 'diesen Hinweis weglassen'), ('X', 'verwerfen')])]
        return '\n'.join(out) + '\n'
    blocks = {'EVENTS': events}
    if rows:
        blocks['ISSUES'] = rows
    return fill('zeitleiste-vorschlag.html', values, blocks)


def continuity_suggest_view(base, config, args, data, run_text):
    """Mögliche Widersprüche (Vorlage widerspruch-vorschlag): je Widerspruch ein Satz und die beteiligten Fundstellen;
    gewählt wird, hinter welche Fundstellen ein Marker [KONTINUITÄT PRÜFEN: …] kommt (vorgewählt: die letzte)."""
    rows, facts = [], []
    for i, it in enumerate(data.get('items') or []):
        rows.append({'S_IDX': i, 'S_TEXT': it['text'], 'S_COUNT': len(it['facts'])})
        for k, f in enumerate(it['facts']):
            facts.append({'F_IDX': i, 'F_K': k, 'F_WHERE': f['where'], 'F_ABOUT': f.get('about', ''), 'F_FACT': f['fact'],
                          'F_QUOTE': f['quote'], 'F_ON': '1' if k == len(it['facts']) - 1 else ''})
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'continuity',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(rows), 'möglicher Widerspruch', 'mögliche Widersprüche'),
              'FACTS_TEXT': f'{data.get("facts", 0)} Tatsachen mit Fundstelle verglichen'}
    if args.text:
        out = [f'### 🔗 Mögliche Widersprüche · {values["SCOPE_TEXT"]}', values['SUGGEST_COUNT_TEXT'] + f' · {values["FACTS_TEXT"]}'
               + (f' · {run_text}' if run_text else ''), '']
        for r in rows:
            out += [f'**{r["S_IDX"] + 1}. {r["S_TEXT"]}**']
            out += [f'- {chr(97 + f["F_K"])}) {f["F_WHERE"]}: „{f["F_QUOTE"]}“' for f in facts if f['F_IDX'] == r['S_IDX']] + ['']
        if not rows:
            out += ['*Keine Widersprüche gefunden.*', '']
        out += ['Übernehmen setzt den Marker `[KONTINUITÄT PRÜFEN: …]` hinter die gewählte Fundstelle (ohne Angabe die letzte); '
                'sonst bleibt der Text unverändert. Offene Marker verhindern eine Auflage, bis sie geklärt sind.', '', '---',
                menu([('Übernehmen: 1, 3', 'Marker an der letzten Fundstelle'), ('2: a, b', 'Marker an diesen Fundstellen'),
                      ('X', 'verwerfen')])]
        return '\n'.join(out) + '\n'
    return fill('widerspruch-vorschlag.html', values, {'SUGGESTIONS': rows, 'FACTS': facts})


def language_suggest_view(base, config, args, data, run_text):
    """Sprachliche Hinweise (Vorlage sprache-vorschlag): je Abschnitt die Auffälligkeiten mit Fundstelle; übernommen
    wird nur in die Hinweisliste, der Text bleibt unverändert."""
    import analyze
    rows = [{'S_IDX': i, 'S_WHERE': h['where'], 'S_KIND': h['kind'], 'S_KIND_TEXT': analyze.LANGUAGE_DE.get(h['kind'], h['kind']),
             'S_TEXT': h['text'], 'S_QUOTE': h['quote']} for i, h in enumerate(data.get('items') or [])]
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'language',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(rows), 'Hinweis', 'Hinweise'),
              'RULES_TEXT': f'Sätze über {analyze.LONG_SENTENCE} Wörter · ein Wort {analyze.REPEAT_MIN}× in {analyze.REPEAT_WINDOW} Wörtern · '
                            f'3 gleiche Satzanfänge hintereinander · mehr als 1 % Füllwörter'}
    if args.text:
        out = [f'### ✍️ Sprachliche Hinweise · {values["SCOPE_TEXT"]}', values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''),
               f'Gezählt ohne KI: {values["RULES_TEXT"]}', '']
        if rows:
            out += ['| # | Abschnitt | Art | Hinweis | Fundstelle |', '|--:|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | {r["S_WHERE"]} | {r["S_KIND_TEXT"]} | {r["S_TEXT"]} | „{r["S_QUOTE"]}“ |' for r in rows]
        else:
            out += ['*Keine Auffälligkeiten.*']
        out += ['', 'Übernommen wird nur in die Hinweisliste der Abschnitte (`story/hints.yml`); der Text bleibt unverändert.',
                '', '---', menu([('Alle', 'alle Hinweise übernehmen'), ('Ohne: 2, 5', 'alle außer diesen'), ('X', 'verwerfen')])]
        return '\n'.join(out) + '\n'
    return fill('sprache-vorschlag.html', values, {'SUGGESTIONS': rows})


ANALYSIS_VIEWS = {'summaries': summaries_suggest_view, 'style': style_suggest_view, 'places': places_suggest_view,
                  'timeline': timeline_suggest_view, 'continuity': continuity_suggest_view, 'language': language_suggest_view}


def import_preview_view(base, config, args):
    """Vorschau „Manuskript importieren“ (#124, Vorlage import-vorschau): Gliederung aus import/proposal.json."""
    import import_book
    p = import_book.load_proposal(base)
    st = p['stats']
    info = import_book.status(base) or {}
    rows = []
    for ci, c in enumerate(p['chapters'], start=1):
        rows.append({'R_TYPE': 'chapter', 'R_CHAPTER': ci, 'R_SECTION': '', 'R_LABEL': f'Kapitel {ci}', 'R_TITLE': c['title'],
                     'R_WORDS': sum(s['words'] for s in c['sections']), 'R_SCENES': '', 'R_LONG': '',
                     'R_COUNT': plural(len(c['sections']), 'Abschnitt', 'Abschnitte')})
        for si, s in enumerate(c['sections'], start=1):
            rows.append({'R_TYPE': 'section', 'R_CHAPTER': ci, 'R_SECTION': si, 'R_LABEL': f'{ci}.{si}', 'R_TITLE': s['title'],
                         'R_WORDS': s['words'], 'R_SCENES': s['scenes'] if s['scenes'] > 1 else '',
                         'R_LONG': '1' if s['words'] > import_book.LONG_WORDS else '', 'R_COUNT': ''})
    parts = [{'P_IDX': k, 'P_KIND': x['kind'], 'P_AREA': x.get('area') or MATTER[x['kind']][0], 'P_TITLE': x['title'],
              'P_WORDS': x['words'], 'P_LABEL': MATTER[x['kind']][1]} for k, x in enumerate(p['parts'], start=1)]
    stats_text = (f'{st["chapters"]} Kapitel, {st["sections"]} Abschnitte, {len(parts)} Teile von Vor- und Nachspann · '
                  f'{st["words_proposal"]} von {st["words_original"]} Wörtern übernommen')
    values = {'IMPORT_TITLE': p.get('title') or '', 'IMPORT_AUTHOR': p.get('author') or '', 'IMPORT_FORMAT': (p.get('format') or '').upper(),
              'STATS_TEXT': stats_text, 'LOSSLESS': '1' if st.get('lossless') else '', 'KEEP_TEXT': info.get('keep_text', ''),
              'KINDS_TEXT': ', '.join(f'{k}={v[1]}' for k, v in MATTER.items())}
    outline = import_book.open_outline(base)
    if outline:   # KI-Vorschlag für die Gliederung liegt bereit
        values['OUTLINE_TEXT'] = (f'KI-Vorschlag für die Gliederung liegt bereit: {len(outline["chapters"])} Kapitel, '
                                  f'{sum(len(c["sections"]) for c in outline["chapters"])} Abschnitte')
    elif p.get('structure') == 'none' and len(p['chapters']) == 1:
        values['NO_STRUCTURE'] = '1'
    warns = [{'W_TEXT': w} for w in p.get('warnings') or []]
    if args.text:
        out = [f'### 📥 Manuskript importieren · {values["IMPORT_TITLE"] or "ohne Titel"}',
               f'{values["IMPORT_FORMAT"]} · Autor: {values["IMPORT_AUTHOR"] or "–"} · {stats_text}'
               + ('' if values['LOSSLESS'] else ' ⚠️ nicht vollständig'), '']
        out += [f'> ⚠️ {w["W_TEXT"]}' for w in warns] + ([''] if warns else [])
        out += ['| | Teil | Wörter | Hinweis |', '|---|---|--:|---|']
        out += [f'| {x["P_LABEL"]} ({"Vorspann" if x["P_AREA"] == "front" else "Nachspann"}) | {x["P_TITLE"]} | {x["P_WORDS"]} | `T{x["P_IDX"]}` |'
                for x in parts if x['P_AREA'] == 'front']
        for r in rows:
            hint = ('⚠️ sehr lang' if r['R_LONG'] else '') + (f' · {r["R_SCENES"]} Szenen' if r['R_SCENES'] else '')
            out.append(f'| **{r["R_LABEL"]}** | **{r["R_TITLE"]}** · {r["R_COUNT"]} | {r["R_WORDS"]} | |' if r['R_TYPE'] == 'chapter'
                       else f'| {r["R_LABEL"]} | {r["R_TITLE"]} | {r["R_WORDS"]} | {hint.strip(" ·")} |')
        out += [f'| {x["P_LABEL"]} (Nachspann) | {x["P_TITLE"]} | {x["P_WORDS"]} | `T{x["P_IDX"]}` |' for x in parts if x['P_AREA'] != 'front']
        if values.get('OUTLINE_TEXT'):
            out += ['', f'> 🧭 **{values["OUTLINE_TEXT"]}** · `GV` ansehen']
        elif values.get('NO_STRUCTURE'):
            out += ['', '> 🧭 Keine Gliederung erkannt · `GK` Gliederung mit KI vorschlagen (Hintergrundlauf, Kosten werden vorher gezeigt)']
        out += ['', 'Änderungen als Text, z. B. `Kapitel 2: Neuer Titel`, `2.1 teilen` (an Szenen), `2.1 + 2.2` (zusammenlegen), '
                '`Kapitel 3 + 4`, `Neues Kapitel ab 2.3`, `Kapitel 1 ist Prolog`, `T1 ist ein Kapitel`.', '',
                '---', menu([('A', 'Buch so anlegen'), ('AS', 'anlegen und Schreibfreigabe für alle Abschnitte erteilen'),
                             ('X', 'abbrechen')])]
        return '\n'.join(out) + '\n'
    blocks = {'ROWS': rows}
    if parts:
        blocks['PARTS'] = parts
    if warns:
        blocks['WARNINGS'] = warns
    return fill('import-vorschau.html', values, blocks)


def import_outline_view(base, config, args):
    """KI-Vorschlag für die Gliederung beim Import (#124, Vorlage gliederung-vorschlag) aus import/outline.json:
    Kapitel und Abschnitte mit Titel, Wortzahl, Anfang (wörtlich) und Begründung."""
    import import_book
    o = import_book.open_outline(base)
    if not o:
        raise SystemExit('Es gibt keinen offenen KI-Vorschlag für die Gliederung')
    rows = []
    for ci, c in enumerate(o['chapters'], start=1):
        rows.append({'O_TYPE': 'chapter', 'O_CHAPTER': ci, 'O_SECTION': '', 'O_LABEL': f'Kapitel {ci}', 'O_TITLE': c['title'],
                     'O_START': c['start'], 'O_WORDS': c['words'], 'O_QUOTE': c['quote'], 'O_REASON': c.get('reason', ''),
                     'O_COUNT': plural(len(c['sections']), 'Abschnitt', 'Abschnitte')})
        for si, sec in enumerate(c['sections'], start=1):
            rows.append({'O_TYPE': 'section', 'O_CHAPTER': ci, 'O_SECTION': si, 'O_LABEL': f'{ci}.{si}', 'O_TITLE': sec['title'],
                         'O_START': sec['start'], 'O_WORDS': sec['words'], 'O_QUOTE': sec['quote'],
                         'O_REASON': sec.get('reason', '') if si > 1 else '', 'O_COUNT': ''})
    n_secs = sum(len(c['sections']) for c in o['chapters'])
    values = {'RUN_ID': o['run'], 'RUN_TEXT': f'Vorschlag {o["run"][8:]} vom {de_date(str(o.get("created_at", "")))} ({o.get("model", "")})',
              'STATS_TEXT': f'{len(o["chapters"])} Kapitel, {n_secs} Abschnitte aus {o["paragraphs"]} Absätzen · '
                            f'{o["dropped"]} Anfänge ohne wörtliche Fundstelle verworfen',
              'PARTIAL_TEXT': '' if o.get('full_text', True) else 'Sehr langes Manuskript: die KI hat je Absatz nur den Anfang gelesen.'}
    if args.text:
        out = ['### 🧭 Gliederung mit KI (Vorschlag)', f'{values["STATS_TEXT"]} · {values["RUN_TEXT"]}', '']
        if values['PARTIAL_TEXT']:
            out += [f'> ⚠️ {values["PARTIAL_TEXT"]}', '']
        out += ['| | Titel | Wörter | beginnt mit | Begründung |', '|---|---|--:|---|---|']
        out += [f'| **{r["O_LABEL"]}** | **{r["O_TITLE"]}** · {r["O_COUNT"]} | {r["O_WORDS"]} | „{r["O_QUOTE"]}“ | {r["O_REASON"]} |'
                if r['O_TYPE'] == 'chapter' else f'| {r["O_LABEL"]} | {r["O_TITLE"]} | {r["O_WORDS"]} | „{r["O_QUOTE"]}“ | {r["O_REASON"]} |'
                for r in rows]
        out += ['', 'Getrennt wird nur an Absatzgrenzen; kein Wort geht verloren. Übernommen wird erst nach Bestätigung, '
                'danach lässt sich die Gliederung in der Vorschau weiter ändern.', '', '---',
                menu([('Übernehmen', 'Gliederung so übernehmen'), ('2.3 – Kapitel', 'ab 2.3 ein neues Kapitel'),
                      ('Kapitel 3 – ohne', 'Kapitel 3 mit dem vorigen zusammenlegen'), ('2.1: Titel', 'Titel ändern'),
                      ('X', 'verwerfen')])]
        return '\n'.join(out) + '\n'
    return fill('gliederung-vorschlag.html', values, {'ROWS': rows})


def omnibus_edit_view(base, config, args):
    """Formular „Sammelband“ (#116, Vorlage sammelband): Titel, Bände mit Auflage, Teile der Bände, Vor-/Nachwort."""
    import series as series_mod
    data = library_data(base, args)
    s = find_series(base, data, args.where)
    om = series_mod.omnibus(base, s['id']) or {}
    picked = {v['branch']: v.get('edition') for v in om.get('volumes') or []}
    by_branch = {b['branch']: b for b in data.get('books') or []}
    published = {v['branch']: v for v in series_mod.published_volumes(base, s)}   # Auflagen aus den Tags
    vols = []
    for n, br in enumerate(s['volumes'], start=1):
        b = by_branch.get(br) or {}
        last = (published.get(br) or {}).get('edition') or (b.get('last_edition') or {}).get('number') or 0
        title = (published.get(br) or {}).get('title') or b.get('title') or br
        vols.append({'OV_NUMBER': n, 'OV_BRANCH': br, 'OV_TITLE': title, 'OV_LAST': last,
                     'OV_ON': '1' if br in picked else '', 'OV_EDITION': picked.get(br) or '',
                     'OV_TEXT': f'neueste Auflage {last}' if last else 'noch keine Auflage'})
    keep = om.get('keep_matter', ['prologue', 'epilogue'])
    pub = om.get('publication') or {}
    values = {'SERIES_ID': s['id'], 'SERIES_TITLE': s['title'], 'OMNIBUS_TITLE': om.get('title') or f'{s["title"]} – Sammelband',
              'OMNIBUS_SUBTITLE': om.get('subtitle', ''), 'OMNIBUS_STATE': om.get('status', '') if om else '',
              'OMNIBUS_FOREWORD': om.get('foreword', ''), 'OMNIBUS_AFTERWORD': om.get('afterword', ''),
              'OMNIBUS_ISBN_PRINT': pub.get('isbn_print', ''), 'OMNIBUS_ISBN_EBOOK': pub.get('isbn_ebook', ''),
              'OMNIBUS_EDITION': str(int(om.get('current_edition') or 0)),
              'OMNIBUS_TAG': series_mod.omnibus_tag(s, int(om.get('current_edition') or 0) + 1)}
    keeps = [{'K_KIND': k, 'K_LABEL': v, 'K_ON': '1' if k in keep else ''} for k, v in KEEP_DE.items()]
    if args.text:
        out = [f'### 📚 Sammelband „{values["OMNIBUS_TITLE"]}“', f'Serie „{s["title"]}“ · ' +
               ({'approved': 'freigegeben', 'draft': 'Entwurf'}.get(values['OMNIBUS_STATE'], 'noch nicht angelegt')), '']
        out += ['| Band | Buch | im Sammelband | Auflage |', '|--:|---|---|---|']
        out += [f'| {v["OV_NUMBER"]} | {v["OV_TITLE"]} | {"✅" if v["OV_ON"] else "—"} | {v["OV_EDITION"] or v["OV_TEXT"]} |' for v in vols]
        out += ['', 'Teile der Bände, die bleiben: ' + (', '.join(KEEP_DE[k] for k in keep) or 'keine'), '']
        out += field_table([('Titel', values['OMNIBUS_TITLE']), ('Untertitel', values['OMNIBUS_SUBTITLE']),
                            ('Vorwort zum Sammelband', values['OMNIBUS_FOREWORD']), ('Nachwort', values['OMNIBUS_AFTERWORD']),
                            ('ISBN Druck', values['OMNIBUS_ISBN_PRINT']), ('ISBN E-Book', values['OMNIBUS_ISBN_EBOOK'])])
        items = [('Bände: 1, 2', 'Auswahl setzen'), ('FA', 'Freigabe zurücknehmen' if values['OMNIBUS_STATE'] == 'approved' else 'Sammelband freigeben')]
        if values['OMNIBUS_STATE'] == 'approved':
            items.append(('V', f'Auflage {int(values["OMNIBUS_EDITION"]) + 1} veröffentlichen'))
        out += ['', FORM_HINT, '', menu(items)]
        return '\n'.join(out) + '\n'
    return fill('sammelband.html', values, {'OVOLUMES': vols, 'KEEP': keeps})


def series_edit_view(base, config, args):
    """Formular „Neue Serie“ bzw. „Serie bearbeiten“ (#116, Vorlage serie-bearbeiten); --draft: gesendete Werte und error."""
    data = library_data(base, args)
    s = find_series(base, data, args.where) if args.where else None
    draft = json.loads(args.draft) if args.draft else {}
    v = lambda k, d='': draft.get(k, (s or {}).get(k, d))
    values = {'SERIES_ID': (s or {}).get('id', ''), 'SERIES_TITLE': v('title'), 'SERIES_SUBTITLE': v('subtitle'),
              'SERIES_KIND': v('kind', 'continuous'), 'SERIES_DESCRIPTION': v('description'), 'ERROR_TEXT': draft.get('error', ''),
              'SERIES_ISSN': v('issn'), 'SERIES_ALSO': 'false' if v('also_in_series', True) is False else 'true'}
    taken = [{'TAKEN_TITLE': x['title']} for x in library_series(base, data) if not s or x['id'] != s['id']]
    if args.text:
        out = [f'### 📚 {"Serie bearbeiten" if s else "Neue Serie"}', '']
        if values['ERROR_TEXT']:
            out += [f'> ✗ {values["ERROR_TEXT"]}', '']
        out += field_table([('Titel der Reihe (Pflicht)', values['SERIES_TITLE']), ('Untertitel', values['SERIES_SUBTITLE']),
                            ('Art', SERIES_KIND_DE.get(values['SERIES_KIND'], '')), ('Beschreibung', values['SERIES_DESCRIPTION']),
                            ('ISSN der Reihe', values['SERIES_ISSN']),
                            ('Seite „Ebenfalls in dieser Reihe“', 'nein' if values['SERIES_ALSO'] == 'false' else 'ja')])
        out += ['', 'Art: `durchgehende Handlung` oder `eigenständige Bände`.', '', FORM_HINT]
        return '\n'.join(out) + '\n'
    return fill('serie-bearbeiten.html', values, {'TAKEN': taken})


def book_create_view(base, config, args):
    """Formular „Neues Buch“ (#38). Vorhandene Bücher aus library.json bzw. live; --draft: gesendete Werte und error."""
    import library
    data = library_data(base, args)
    books = data.get('books') or []
    draft = json.loads(args.draft) if args.draft else {}
    latest = sorted((b for b in books if b.get('author')), key=lambda b: b.get('updated_at') or '')
    ser, series_text = None, ''
    if draft.get('series_id'):   # Neues Buch in einer Serie (#116): nächster Band, Autor vom letzten Band
        ser = find_series(base, data, draft['series_id'])
        series_text = f'Band {len(ser["volumes"]) + 1} der Serie „{ser["title"]}“'
        in_ser = [b for b in latest if b['branch'] in ser['volumes']]
        latest = in_ser or latest
    prof_path = Path(base, 'assistant.yml')   # Assistenten-Profil (#136): Autor der Bibliothek, außer in einer Serie
    prof_author = ((yaml.safe_load(prof_path.read_text(encoding='utf-8')) or {}).get('author') or '') if prof_path.is_file() else ''
    author = draft.get('author', (latest[-1]['author'] if latest and (ser or not prof_author) else prof_author)
                       if latest or prof_author else '')
    prefix = library.settings(library.load_manifest())['book_prefix']
    if args.text:
        out = ['### 📗 Neues Buch', '', 'Das Buch bekommt einen eigenen Bereich in dieser Bibliothek; danach folgt der Einstiegsdialog.', '']
        if series_text:
            out += [f'📚 {series_text}', '']
        if draft.get('error'):
            out += [f'> ✗ {draft["error"]}', '']
        out += field_table([('Titel (Arbeitstitel, Pflicht)', draft.get('working_title', '')),
                            ('Kurztitel (optional)', draft.get('title_short', '')), ('Autor (optional)', author)])
        if books:
            out += ['', 'Schon vergeben: ' + ', '.join(f'`{b["slug"]}` ({b["branch"]})' for b in books if b.get('slug'))]
        out += ['', f'Der Bereich heißt `{prefix}<kurztitel>`. Antworte mit `Titel: …`, optional `Kurztitel: …` und `Autor: …`. `X` bricht ab.']
        return '\n'.join(out) + '\n'
    return fill('buch-anlegen.html', {'BRANCH_PREFIX': prefix, 'WORKING_TITLE': draft.get('working_title', ''),
                                      'TITLE_SHORT': draft.get('title_short', ''), 'AUTHOR': author,
                                      'ERROR_TEXT': draft.get('error', ''),
                                      'SERIES_ID': ser['id'] if ser else '', 'SERIES_TEXT': series_text},
                {'TAKEN': [{'TAKEN_SLUG': b.get('slug') or '', 'TAKEN_BRANCH': b['branch']} for b in books]})



# ---------- Seite „Daten“ (#71, Teil 1) ----------

PROOF_DAYS = 14   # Aufbewahrung der Probedruck-Artefakte (proof.yml)
RUN_NAMES = {'validate': 'Projektdateien prüfen', 'proof': 'Probedruck'}


def de_datetime_plus(iso, days=0):
    import datetime
    try:
        d = datetime.datetime.fromisoformat((iso or '').replace('Z', '+00:00')) + datetime.timedelta(days=days)
    except ValueError:
        return ''
    return d.strftime('%d.%m.%Y')


def github_data(args):
    """Rohdaten der GitHub-API aus --github (JSON): repo, branches, pulls, runs; fehlt die Datei, None."""
    if not getattr(args, 'github', None):
        return None
    return json.loads(Path(args.github).read_text(encoding='utf-8'))


def data_view(base, config, args):
    lib = library_data(base, args)
    gh = github_data(args)
    prog = lib.get('program') or {}
    upd = load_upstream(args)
    known = '' if gh is None else '1'
    runs = sorted((gh or {}).get('runs') or [], key=lambda r: r.get('created_at') or '', reverse=True)
    pulls = (gh or {}).get('pulls') or []

    def last_run(name, branch=None):
        for r in runs:
            if r.get('name') == name and (branch is None or r.get('head_branch') == branch):
                return r
        return None

    unknown = 'unbekannt (ohne GitHub-Abfrage)'
    if upd:
        prog_update = update_text(upd)
    elif getattr(args, 'upstream', None):
        prog_update = 'aktuell'
    else:
        prog_update = 'nicht abgefragt'
    full = ((gh or {}).get('repo') or {}).get('full_name') or ''
    if full and not args.repo_known:   # Rohdaten der GitHub-API nennen das Repository (#134)
        args.repo, args.repo_known = full, True
    values = {
        'LIBRARY_NAME': repo_label(args),
        'PROGRAM_VERSION_TEXT': f'GhostWriter {prog.get("version") or "?"} · Hauptrepository {prog.get("upstream") or "?"}',
        'PROGRAM_UPDATE_TEXT': prog_update, 'PROGRAM_BEHIND': upd['behind'] if upd else '',
        'PROGRAM_LAST_UPDATE_TEXT': f'letzter Update-Lauf am {de_datetime_plus(prog["last_update"])}' if prog.get('last_update') else 'noch kein Update-Lauf',
        'PROGRAM_SKIPPED_TEXT': ('Workflow-Dateien ausgelassen (Secret GHOSTWRITER_UPDATE_TOKEN fehlt): ' + ', '.join(prog['skipped_workflows']))
                                if prog.get('skipped_workflows') else '',
        'UI_TEXT': f'ghostwriter-ui {prog.get("ui_version") or "?"} · Commit {(prog.get("ui_commit") or "")[:7]}',
        'GITHUB_KNOWN': known,
        'CLEANUP_URL': f'https://github.com/{args.repo}/actions/workflows/cleanup.yml',
        'TASKS_URL': f'https://github.com/{args.repo}/issues?q=is%3Aissue+is%3Aopen+L%C3%B6schaufgaben',
    }
    repo = (gh or {}).get('repo') or {}
    if gh is None:
        values['REPO_TEXT'] = unknown
    else:
        size = repo.get('size')
        size_text = (f'{size / 1024:.1f} MB'.replace('.', ',') if size and size >= 1024 else f'{size} KB') if size is not None else 'Größe ?'
        nb = len((gh or {}).get('branches') or [])
        values['REPO_TEXT'] = (f'{"privat" if repo.get("private") else "öffentlich"} · {size_text} · '
                               f'{plural(nb, "Branch", "Branches")}')
    books = []
    for b in lib.get('books') or []:
        pr = next((p for p in pulls if (p.get('head') or {}).get('ref') == b.get('work_branch')), None)
        pending = b.get('pending') or 0
        pend_text = (f'{plural(pending, "Änderung", "Änderungen")} offen' + (f' · Pull Request #{pr["number"]}' if pr else '')) if pending else 'keine offenen Änderungen'
        ed = b.get('last_edition')
        v = last_run(RUN_NAMES['validate'], b['branch'])
        pr_run = last_run(RUN_NAMES['proof'], b['branch'])
        if gh is None:
            check, check_text, proof_text = '', 'Prüfung: unbekannt', 'Probedruck: unbekannt'
        else:
            check = {'success': 'ok', 'failure': 'fail'}.get((v or {}).get('conclusion'), '')
            check_text = ('Prüfung beim letzten Push: ' + {'ok': 'bestanden', 'fail': 'fehlgeschlagen'}.get(check, (v or {}).get('status') or 'noch nicht gelaufen')) if v else 'Prüfung: noch kein Lauf'
            if pr_run:
                proof_text = (f'Probedruck vom {de_datetime_plus(pr_run.get("created_at"))}, Download bis '
                              f'{de_datetime_plus(pr_run.get("created_at"), PROOF_DAYS)}')
            else:
                proof_text = 'noch kein Probedruck'
        books.append({
            'B_TITLE': b.get('title') or b.get('title_short') or b['branch'], 'B_BRANCH': b['branch'],
            'B_COMMIT_TEXT': f'{de_date(b.get("updated_at"))} · {b.get("last_commit") or ""}'.strip(' ·'),
            'B_PENDING_TEXT': pend_text, 'B_PENDING': '1' if pending else '',
            'B_AUTOMERGE_TEXT': 'Änderungen sofort übernehmen: ' + ('an' if b.get('auto_merge') else 'aus'),
            'B_EDITION_TEXT': f'Auflage {ed["number"]} vom {de_date(ed["date"])} ({ed["tag"]})' if ed else 'noch keine Auflage',
            'B_PROOF_TEXT': proof_text,
            'B_DATA_TEXT': f'Datenversion {b.get("data_version", "?")}' + (' · Migration steht aus (kommt mit dem nächsten Update)' if b.get('migration_pending') else ' · aktuell'),
            'B_MIGRATION': '1' if b.get('migration_pending') else '',
            'B_CHECK': check, 'B_CHECK_TEXT': check_text})
    secrets = lib.get('secrets')
    srows = []
    for n in lib.get('secret_names') or []:
        v = None if secrets is None else secrets.get(n)
        state = '' if v is None else ('yes' if v else 'no')
        srows.append({'S_NAME': n, 'S_STATE': state or 'unknown',
                      'S_TEXT': {'yes': 'hinterlegt', 'no': 'fehlt', 'unknown': 'unbekannt'}[state or 'unknown']})
    rrows = []
    seen = set()
    for r in runs:
        if r.get('name') in seen:
            continue
        seen.add(r.get('name'))
        c = r.get('conclusion') or r.get('status') or ''
        rrows.append({'R_NAME': r.get('name') or '', 'R_STATE': {'success': 'ok', 'failure': 'fail'}.get(c, 'other'),
                      'R_TEXT': f'{ {"success": "erfolgreich", "failure": "fehlgeschlagen", "cancelled": "abgebrochen", "skipped": "übersprungen", "in_progress": "läuft", "queued": "wartet", "action_required": "wartet auf Freigabe"}.get(c, c)} · '
                                f'{de_datetime_plus(r.get("created_at"))} · {r.get("head_branch") or ""}',
                      'R_URL': r.get('html_url') or ''})
    lrows, lim_text = limit_rows(base, config, args, gh)
    values['LIMITS_TEXT'] = lim_text
    if args.text:
        out = ['### 🗂️ Daten', f'{repo_label(args)}', '', '**Programm**', '',
               f'- {values["PROGRAM_VERSION_TEXT"]}', f'- Update: {values["PROGRAM_UPDATE_TEXT"]} · {values["PROGRAM_LAST_UPDATE_TEXT"]}',
               f'- {values["UI_TEXT"]}'] + ([f'- ⚠️ {values["PROGRAM_SKIPPED_TEXT"]}'] if values['PROGRAM_SKIPPED_TEXT'] else [])
        out += ['', '**Bücher**', '', '| Buch | Letzter Stand | Änderungen | Auflage | Probedruck | Daten | Prüfung |', '|---|---|---|---|---|---|---|']
        for r in books:
            out.append(f'| {r["B_TITLE"]} (`{r["B_BRANCH"]}`) | {r["B_COMMIT_TEXT"]} | {r["B_PENDING_TEXT"]}; {r["B_AUTOMERGE_TEXT"]} | '
                       f'{r["B_EDITION_TEXT"]} | {r["B_PROOF_TEXT"]} | {"⚠️ " if r["B_MIGRATION"] else ""}{r["B_DATA_TEXT"]} | '
                       f'{ {"ok": "✅ ", "fail": "❌ "}.get(r["B_CHECK"], "")}{r["B_CHECK_TEXT"]} |')
        out += ['', '**Repository**', '', f'- {values["REPO_TEXT"]}',
                f'- Erledigte Branches: [Branches aufräumen]({values["CLEANUP_URL"]}) · [Löschaufgaben]({values["TASKS_URL"]})']
        if srows:
            out += ['- Secrets (nur Namen): ' + ', '.join(f'`{r["S_NAME"]}` { {"yes": "✅", "no": "❌", "unknown": "❔"}[r["S_STATE"]]} {r["S_TEXT"]}' for r in srows)]
        if lrows:
            out += ['', '**Nutzungsgrenzen**', '', '| Grenze | Stand |', '|---|---|']
            out += [f'| {r["L_LABEL"]} | { {"ok": "🟢", "warn": "🟡", "pause": "🔴"}[r["L_STATE"]]} {r["L_TEXT"]} |' for r in lrows]
            if lim_text:
                out += ['', f'> ⏸ {lim_text}']
        if rrows:
            out += ['', '**Letzte Läufe**', '', '| Action | Ergebnis |', '|---|---|'] + [f'| [{r["R_NAME"]}]({r["R_URL"]}) | {r["R_TEXT"]} |' for r in rrows]
        out += ['', '---', menu([('Ü', 'Bücherregal')] + ([('U', 'Update einspielen')] if upd else []))]
        return '\n'.join(out) + '\n'
    blocks = {'BOOKS': books, 'SECRETS': srows, 'RUNS': rrows}
    if lrows:
        blocks['LIMITS'] = lrows
    return fill('daten.html', values, blocks)


def limit_rows(base, config, args, gh):
    """Nutzungsgrenzen für „Daten“ (#71, #62): aus --limits (limits.py check --json) bzw. aus den Kosten des Monats und,
    wenn github.json `rate_limit` (GET /rate_limit) enthält, dem API-Rate-Limit. → ([{L_LABEL, L_STATE, L_TEXT}], text)."""
    import limits
    if getattr(args, 'limits', None):
        data = json.loads(Path(args.limits).read_text(encoding='utf-8'))
        rows, state = data.get('limits') or [], data.get('state')
    else:
        live = {}
        core = (((gh or {}).get('rate_limit') or {}).get('resources') or {}).get('core') or {}
        if core.get('limit'):
            live['api_rate'] = (core['limit'] - core.get('remaining', 0), core['limit'])
        rows = limits.evaluate(base, config, live=live)
        state = limits.summary(rows)[0]
    out = [{'L_LABEL': r['label'], 'L_STATE': r['state'], 'L_TEXT': r['text'][len(r['label']) + 1:]} for r in rows]
    paused = [r for r in rows if r['state'] == 'pause']
    text = ('Update-Automatik pausiert: ' + '; '.join(r['text'] for r in paused)) if state == 'pause' and paused else ''
    return out, text


WIZARD_CHOICES = Path(__file__).resolve().parent.parent / 'templates' / 'wizard-choices.yml'
LETTERS = 'abcdef'


def choice_spec(args):
    """Auswahl-Spezifikation: Schritt aus templates/wizard-choices.yml (where) oder --spec (JSON-Datei bzw. JSON-Text)."""
    if args.spec:
        raw = Path(args.spec).read_text(encoding='utf-8') if Path(args.spec).is_file() else args.spec
        spec = json.loads(raw)
        spec.setdefault('step', args.where or 'choice')
        return spec
    lib = yaml.safe_load(WIZARD_CHOICES.read_text(encoding='utf-8'))
    step = args.where or ''
    if step not in lib['steps']:
        raise SystemExit(f'Auswahl „{step}“ unbekannt; vorhanden: {", ".join(lib["steps"])}')
    spec = dict(lib['steps'][step], step=step)
    num = step.split('.')[-1]
    for k in ('title', 'subtitle', 'note'):
        if spec.get(k):
            spec[k] = spec[k].replace('{step}', num).replace('{steps}', str(lib.get('steps_total', '')))
    return spec


def check_choice_spec(spec):
    qs = spec.get('questions') or []
    if not 1 <= len(qs) <= 4:
        raise SystemExit('Auswahl: 1–4 Fragen')
    for q in qs:
        opts = q.get('options') or []
        if not 2 <= len(opts) <= 6:
            raise SystemExit(f'Auswahl „{q.get("key")}“: 2–6 Antworten')
        if len(q.get('header', '')) > 12:
            raise SystemExit(f'Auswahl „{q.get("key")}“: Etikett höchstens 12 Zeichen')
        if sum(bool(o.get('recommended')) for o in opts) > 1:
            raise SystemExit(f'Auswahl „{q.get("key")}“: höchstens eine Empfehlung')


def config_value(config, path):
    v = config
    for part in (path or '').split('.'):
        if not part or not isinstance(v, dict) or part not in v:
            return None
        v = v[part]
    return v


def is_selected(current, value):
    if current is None or current == '' or current == []:
        return False
    if isinstance(current, list):
        return value in [str(x) for x in current]
    if isinstance(current, bool):
        return value == ('true' if current else 'false')
    return str(current) == value


def choice_view(base, config, args):
    spec = choice_spec(args)
    check_choice_spec(spec)
    qs = spec['questions']
    if args.text:
        out = [f'### {spec.get("title", "Auswahl")}']
        if spec.get('subtitle'):
            out += ['', spec['subtitle']]
        for i, q in enumerate(qs, 1):
            cur = config_value(config, q.get('field'))
            out += ['', f'**{i}. {q["text"]}**' + (' *(mehrere möglich)*' if q.get('multi') else '')]
            for letter, o in zip(LETTERS, q['options']):
                tags = (' · *empfohlen*' if o.get('recommended') else '') + (' · *bisher*' if is_selected(cur, str(o['value'])) else '')
                out.append(f'- `{i}{letter}` {o["label"]}' + (f' – {o["desc"]}' if o.get('desc') else '') + tags)
        example = ', '.join(f'{i}{"a c" if q.get("multi") else "a"}' for i, q in enumerate(qs, 1))
        out += ['', f'Antworte mit den Kürzeln, z. B. `{example}`; eigene Antwort als `1: Text`.'
                + (' `S` überspringt.' if spec.get('skippable') else '')]
        if spec.get('note'):
            out += ['', f'<sub>{spec["note"]}</sub>']
        return '\n'.join(out) + '\n'
    questions, options = [], []
    for i, q in enumerate(qs, 1):
        cur = config_value(config, q.get('field'))
        questions.append({'Q_INDEX': str(i), 'Q_KEY': q['key'], 'Q_HEADER': q.get('header', ''), 'Q_TEXT': q['text'],
                          'Q_MULTI': '1' if q.get('multi') else ''})
        for o in q['options']:
            v = str(o['value'])
            options.append({'OPT_Q': str(i), 'OPT_VALUE': v, 'OPT_LABEL': o['label'], 'OPT_DESC': o.get('desc', ''),
                            'OPT_RECOMMENDED': '1' if o.get('recommended') else '', 'OPT_SELECTED': '1' if is_selected(cur, v) else ''})
    return fill('auswahl.html', {'STEP': spec['step'], 'TITLE': spec.get('title', 'Auswahl'), 'SUBTITLE': spec.get('subtitle', ''),
                                 'NOTE': spec.get('note', ''), 'SKIPPABLE': '1' if spec.get('skippable') else ''},
                {'QUESTIONS': questions, 'OPTIONS': options})


FORMS = {'choice': choice_view, 'book-create': book_create_view, 'series-edit': series_edit_view, 'omnibus-edit': omnibus_edit_view,
         'character-suggest': character_suggest_view, 'analysis-suggest': analysis_suggest_view, 'import-preview': import_preview_view, 'import-outline': import_outline_view, 'project-edit': project_edit_view, 'chapter-research': chapter_research_view, 'project-settings': project_settings_view, 'chapter-create': chapter_create_view,
         'chapter-reorder': chapter_reorder_view, 'edition-create': edition_create_view, 'chapter-edit': chapter_edit_view,
         'section-create': section_create_view, 'section-reorder': section_reorder_view,
         'changes-merge': changes_merge_view, 'providers-edit': providers_edit_view,
         'approval-writing': lambda b, c, a: approval_view(b, c, a, 'writing'),
         'approval-section': lambda b, c, a: approval_view(b, c, a, 'section'),
         'approval-chapter': lambda b, c, a: approval_view(b, c, a, 'chapter'),
         'approval-matter': lambda b, c, a: approval_view(b, c, a, 'section'),
         'approval-image': lambda b, c, a: approval_view(b, c, a, 'image'),
         'ai-disclosure': ai_disclosure_view, 'output': output_view}


def git_head(base):
    try:
        return subprocess.run(['git', '-C', str(base), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


REPO_URL = re.compile(r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$')
UNKNOWN_REPO = 'unbekanntes Repository'


def detect_repo(base):
    """owner/name des Buch-Repositorys ohne --repo (#134): GITHUB_REPOSITORY (Actions), sonst die
    Adresse von origin im Projektordner. Nie das Hauptrepository als Vorgabe; nichts gefunden = ''."""
    import os
    env = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if REPO_URL.fullmatch(env):
        return env
    url = subprocess.run(['git', '-C', str(base), 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
    m = REPO_URL.search(url.replace(':', '/')) if url and not Path(url).is_dir() else None
    return f'{m.group(1)}/{m.group(2)}' if m else ''


def repo_label(args):
    """Name des Repositorys für Überschriften (Bücherregal, Serie, Daten)."""
    return args.repo if getattr(args, 'repo_known', True) else UNKNOWN_REPO


def resolve_repo(base, args):
    """args.repo setzen: --repo, sonst ermittelt. Unbekannt: Anzeige „unbekanntes Repository“, Links auf
    das Hauptrepository aus dem Manifest (dort liegen dieselben Programmdateien und die Anleitung)."""
    repo = (args.repo or '').strip() or detect_repo(base)
    args.repo_known = bool(repo)
    if not repo:
        manifest = ROOT / 'ghostwriter-manifest.yml'
        up = (yaml.safe_load(manifest.read_text(encoding='utf-8')) or {}).get('upstream') or {} if manifest.is_file() else {}
        repo = up.get('repo') or 'ploeffler/GhostWriter'
    args.repo = repo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('view', choices=['project', 'chapter', 'section', 'matter', 'characters', 'images', 'library', 'data', 'series'] + list(FORMS))
    ap.add_argument('where', nargs='?')
    ap.add_argument('--text', action='store_true')
    ap.add_argument('--repo', help='owner/name des Buch-Repositorys; ohne Angabe aus GITHUB_REPOSITORY bzw. git remote origin (#134)')
    ap.add_argument('--branch', default='main')
    ap.add_argument('--revoke', action='store_true', help='bei approval-*: Freigabe zurücknehmen statt erteilen')
    ap.add_argument('--upstream', help='JSON-Datei mit dem Update-Stand (behind, upstream, version, installed) für die Projektübersicht')
    ap.add_argument('--limits', help='JSON-Datei von limits.py check --json (Projektübersicht: Hinweis Vorwarnung bzw. Automatik pausiert); ohne Angabe nur das KI-Budget aus costs/')
    ap.add_argument('--changes', help='JSON-Datei mit den offenen Änderungen (Pull Request, Branches, Commits) für Projektübersicht und changes-merge')
    ap.add_argument('--head-sha', help='Commit des gelesenen Stands (HEAD_SHA); ohne Angabe der HEAD des Projektordners, wenn er ein Git-Repository ist')
    ap.add_argument('--draft', help='bei chapter-research bzw. book-create: JSON mit noch nicht gespeicherten Werten (goal, summary, question, scope bzw. working_title, title_short, author, error)')
    ap.add_argument('--library', help='library.json vom Standard-Branch (Bücherregal; in der Projektübersicht ab 2 Büchern der Link „Bücherregal“)')
    ap.add_argument('--github', help='bei data: JSON mit Rohdaten der GitHub-API (repo, branches, pulls, runs), siehe BEFUELLUNG.md, „Daten“')
    ap.add_argument('--spec', help='bei choice: JSON-Datei oder JSON-Text mit einer eigenen Auswahl (Aufbau wie templates/wizard-choices.yml)')
    ap.add_argument('--ui-ref', help='Commit oder Branch von ghostwriter-ui statt des festen Commits aus templates/ui/ghostwriter-ui.yml (nur zum Testen)')
    args = ap.parse_args()
    ui = yaml.safe_load(UI_CONFIG.read_text(encoding='utf-8'))
    UI['repo'], UI['ref'] = ui['repo'], args.ui_ref or ui['commit']
    base, config = load(args.project)
    resolve_repo(base, args)
    UI['head'] = args.head_sha or git_head(base)
    if args.view in FORMS:
        out = FORMS[args.view](base, config, args)
    elif args.view == 'library':
        out = library_view(base, config, args)
    elif args.view == 'data':
        out = data_view(base, config, args)
    elif args.view == 'matter':
        out = matter_view(base, config, args)
    elif args.view == 'characters':
        out = characters_view(base, config, args)
    elif args.view == 'images':
        out = images_view(base, config, args)
    elif args.view == 'series':
        out = series_view(base, config, args)
    elif args.view == 'project':
        out = project_view(base, config, args)
    elif args.view == 'chapter':
        out = chapter_view(base, config, args, int(args.where))
    else:
        c, s = (int(x) for x in args.where.split('.'))
        out = section_view(base, config, args, c, s)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
