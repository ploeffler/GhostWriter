# GhostWriter-Updates

Allgemeine Skills stammen aus [ghostwriter-skills](https://github.com/ploeffler/ghostwriter-skills). Ihre mitgelieferten Kopien und `ghostwriter-skills.yml` sind Programmdateien: Ein reguläres GhostWriter-Update verteilt die geprüfte festgelegte Fassung, ohne zur Laufzeit einen beweglichen Skill-Branch abzurufen. Persönliche Skills bleiben geschützt. Der optionale Buchteaser wird nicht automatisch installiert.

Dein Buch-Repository bekommt neue GhostWriter-Versionen automatisch aus dem Hauptrepository. Du musst dafür nichts tun; diese Seite erklärt, was dabei passiert und was du einrichten kannst.

## Was passiert

Kennst du den Hinweis „This branch is 3 commits behind ploeffler/GhostWriter:main“ auf GitHub? Genau den räumt GhostWriter für dich auf, nur sicherer als GitHubs Knopf *Sync fork*.

Die Action **„GhostWriter aktualisieren“** (`.github/workflows/update.yml`) läuft jeden Tag um 06:00 Uhr (UTC, also 7:00 Uhr Wiener Winterzeit) und lässt sich jederzeit von Hand starten. Sie prüft **jeden Branch** deines Repositorys: Wie viele Commits liegt er hinter seinem Gegenstück im Hauptrepository (gleichnamiger Branch, sonst `main`)? Bei einem Repository aus der Vorlage zählt sie die Commits seit dem letzten eingespielten Stand. Liegt er dahinter, spielt sie die Commits ein:

1. **Branch ohne eigene Commits** (reine Kopie): Programm übernehmen und den Instanz-Einstieg erzeugen. Dafür entsteht ein Update-Commit. Nur ältere Programmstände ohne Einstiegsgenerator werden noch unmittelbar nachgezogen (Fast-Forward).
2. **Branch mit deinem Buch:** Die Commits des Hauptrepositorys werden **hineingemergt**. Dabei gilt das Manifest (`ghostwriter-manifest.yml`):
   - **Programmdateien** (`managed`: `START.md`, `README.md`, `CLAUDE.md`, `AGENTS.md`, die allgemeinen Skills `.claude/skills/ghostwriter/`, `.claude/skills/ghostwriter-lektorat/` und `.claude/skills/ghostwriter-buchgedaechtnis/`, `docs/`, `schemas/`, `scripts/`, `templates/`, `assets/` (Logo und App-Symbole), `.github/workflows/`, `workflow.yml`, `providers.yml` …) kommen aus dem Hauptrepository. Ausnahme: Aus der zentralen `START.md` erzeugt der Lauf anschließend den kurzen Instanz-Einstieg und die Anweisungsmodule (siehe unten).
   - **Dein Buch** (`book`: `ghostwriter.yml`, `chapters/`, `costs/`, `research/`, `approvals.yml`, das Assistenten-Profil `assistant.yml`; der persönliche Skill daneben unter `.claude/skills/` wird nie angefasst) bleibt genau so, wie es ist, auch wenn das Hauptrepository die Vorlagen dafür geändert hat.
   - Konflikte in anderen Dateien bricht die Action ab und meldet sie; die führst du von Hand zusammen.
3. **Migrationen.** Jedes Buch trägt eine **Datenversion** (`data_version` in `ghostwriter.yml`, fehlt = 0). Ist die neue GhostWriter-Version weiter, bringt `scripts/migrate_project.py` das Buch Schritt für Schritt auf den neuen Stand (0 → 1 → 2 …, auch über mehrere Versionen hinweg). Geändert wird nur die Struktur (neue Felder mit Vorgaben, Umbenennungen, verschobene Dateien), nie Texte, Freigaben, Läufe oder Kosten. Was umgestellt wurde, steht im Commit und in `.ghostwriter/update.yml` (`migration`); die Projekteinstellungen zeigen es beim Update-Stand. Ist ein Buch neuer als das Programm, bricht die Migration ab, und nichts wird verändert.
4. **Prüfung.** Danach laufen die Übersichtsdatei und die Projektprüfung mit der neuen Version. **Schlägt die Prüfung fehl, wird nichts eingespielt.** Stattdessen öffnet die Action ein Issue „GhostWriter-Update fehlgeschlagen (Branch)“ mit dem Grund. Beim nächsten erfolgreichen Lauf wird es geschlossen.
5. **Push mit Wiederholung:** Lehnt GitHub den Push mit einem Serverfehler ab („Internal Server Error“ u. ä.), versucht die Action es bis zu dreimal mit kurzer Pause. Ist der Branch während des Laufs weitergewandert (etwa durch „Bücherregal aktualisieren“), holt sie den neuen Stand und spielt das Update für diesen Branch einmal neu ein. Erst danach gilt der Branch als fehlgeschlagen; das Issue „GhostWriter-Update fehlgeschlagen“ nennt die Meldung von GitHub.
6. **Ein Commit je Branch:** „GhostWriter aktualisiert auf <Version>“ mit der Zeile `GhostWriter-Aktion: update`. Der Stand steht in `.ghostwriter/update.yml`.

Danach liegt kein Branch mehr hinter dem Hauptrepository, und GitHubs Hinweis „… commits behind“ verschwindet. Ein Buch wird nie auf eine **ältere** Programmversion zurückgesetzt. Die Zusammenfassung jedes Laufs (*Actions → GhostWriter aktualisieren*) zeigt je Branch, wie weit er zurück war und was passiert ist.

Neue Versionen erscheinen erst, wenn ein Versionsschritt im Hauptrepository nach `main` gemergt ist. Zwischenstände aus Entwicklungs-Branches kommen nicht in dein Buch.

## Täglicher Bericht als GitHub-Benachrichtigung

Der tägliche Update-Lauf ergänzt die Actions-Zusammenfassung und veröffentlicht den vollständigen Bericht höchstens einmal pro UTC-Tag im festen Issue „GhostWriter: täglicher Update-Bericht“. Der Empfänger wird erwähnt; GitHub übernimmt die Benachrichtigung gemäß seinen persönlichen Einstellungen. Es werden kein SMTP-Zugang und keine zusätzlichen Secrets benötigt. Empfängerwahl, Abonnieren, Pausieren und manuelles Anfordern stehen unter [Tägliche GitHub-Übersicht](DAILY-SUMMARY.md#tagesbericht-erhalten).

## Bibliothek: mehrere Bücher in einem Repository

In einer Bibliothek (#36–#39) liegt auf dem Standard-Branch nur das Programm, jedes Buch auf einem eigenen Branch `buch/<slug>`. Die Action aktualisiert zuerst den Standard-Branch und danach jedes Buch einzeln; die Zusammenfassung zeigt eine Zeile je Buch. Welche Branches Bücher sind, entscheidet die Erkennungsregel in `scripts/library.py`: der Standard-Branch nur, wenn er Kapitel hat (Einzelbuch), jeder `buch/*`-Branch, sonst Branches mit Kapiteln. Arbeits-Branches (`ghostwriter/…`) und andere Branches werden nicht selbst aktualisiert. Hat ein Buch ein **offenes Änderungspaket** (Arbeits-Branch `ghostwriter/<buch>` mit offenem Pull Request zum Buch), bekommt es direkt nach dem Buch dessen neuen Stand; Workflows und Prüfungen laufen dort dann mit dem neuen Programmstand (#470). Bei einem Konflikt bleibt das Änderungspaket unverändert, die Zusammenfassung nennt die Dateien (⚠️); nur eine Übersichtsdatei im Konflikt wird neu erzeugt. Geänderte Workflow-Dateien brauchen dafür `GHOSTWRITER_UPDATE_TOKEN`, sonst bleibt der Hinweis, im Pull Request „Update branch“ zu wählen. Arbeits-Branches ohne offenen Pull Request bleiben, wie sie sind; der Probelauf zeigt nur an. Ein Fehler in einem Buch hält die anderen nicht auf; für das betroffene Buch öffnet die Action ein Issue.

**Hintergrund-Warteschlange prüfen (#481):** Am Ende jedes Update-Laufs, auch beim Start von Hand, sucht die Action auf allen Arbeits-Branches nach liegengebliebenen Aufträgen der Hintergrund-Warteschlange (etwa nach einem abgebrochenen Recherche-Lauf oder einem nachträglich bestätigten Auftrag) und startet je Buch die Abarbeitung („Recherche“ ohne Abschnitt). Das kostet keinen KI-Aufruf. Ist die Automatik pausiert, startet nichts; die Zusammenfassung nennt dann, wie viele Aufträge warten. Auch die Warteschlange startet sich dann nicht selbst neu; was übrig ist, bleibt liegen, bis du von Hand neu anstößt oder die Pause endet. Im Probelauf wird nur angezeigt. „GhostWriter aktualisieren“ von Hand ist damit auch der Weg, die Warteschlange anzustoßen. Seit #479 gilt das für alle vier Arten (Recherche, Analyse, Colorieren, Import); „Run workflow“ ohne Eingaben (Analyse ohne `kind`, Colorieren ohne `folder`, Import mit `step: queue`) legt keinen neuen Auftrag an, sondern arbeitet nur ab. Hinweis: GitHub schaltet Zeitpläne in öffentlichen Repositorys nach 60 Tagen ohne Aktivität ab; dann diesen Lauf einmal von Hand starten.

## Von v0.5 auf v0.6

**Ohne Zutun:** Ein Repository mit einem Buch auf dem Standard-Branch (Einzelbuch) bekommt v0.6 wie jedes Update und läuft unverändert weiter. Der Standard-Branch hat Kapitel und gilt deshalb weiter als das Buch; ein Link auf das Repository zeigt wie bisher dessen Projektübersicht.

**Umwandeln in eine Bibliothek (optional):** Wer mehrere Bücher in einem Repository führen möchte, startet einmal die Action *Actions → In Bibliothek umwandeln → Run workflow* auf dem Standard-Branch. Ohne Eingabe ist das ein **Probelauf**: Er prüft alles und zeigt, was passieren würde, ändert aber nichts. Erst mit `UMWANDELN` im Feld *confirm*:

1. Prüfen: Der Standard-Branch hat Kapitel; im Arbeits-Branch liegen keine offenen Änderungen (sonst zuerst im Chat „Buchänderungen übernehmen“); der Name `buch/<kurztitel>` ist frei (anderer Kurztitel über das Feld *title_short*).
2. Das Buch bekommt den Branch `buch/<kurztitel>` auf genau demselben Commit, also mit seiner ganzen Historie, und wird dort geprüft (Projektprüfung).
3. Erst danach bekommt der Standard-Branch einen Commit „In Bibliothek umgewandelt“: Buchdateien (`chapters/`, `costs/`, `research/`, `editions/`, `approvals.yml`, Übersichtsdatei) entfernt, `ghostwriter.yml` wieder der Starter, `library.json` für das Bücherregal.

Tags und Releases bleiben gültig; sie zeigen weiter auf ihre Commits. Neue Auflagen entstehen auf dem Buch-Branch. Im Chat öffnet der Link auf das Repository danach das Bücherregal, ein weiteres Buch kommt über „Neues Buch“ dazu.

**Rückweg:** Den Commit „In Bibliothek umgewandelt“ auf dem Standard-Branch rückgängig machen (auf GitHub: Commit öffnen → *Revert*, oder `git revert`), danach den Branch `buch/<kurztitel>` löschen, sofern dort seitdem nichts Neues geschrieben wurde; sonst diese Änderungen vorher auf den Standard-Branch übernehmen.

Neue Pflichtfelder gibt es mit v0.6 nicht; die Datenversion bleibt 1 (`scripts/migrate_project.py`).

**1.1.0:** Skill ghostwriter auf ghostwriter-skills 641bf7d nachziehen (#564). Rundumprüfung setzt auch Vorschläge bei Autorenentscheidungen um (#565) (#566). Testauswahl: Abgleich der allgemeinen Skills ohne volle Suite (#567) (#568). Hinweisdurchsicht: lange Befundlisten in Stufen abarbeiten (#570) (#571). Planung bis v1.5 in der Doku nachgezogen; #209 nach v1.2/v1.3 (#575). Bereich zum Gegenlesen auschecken und sperren (#572, Teil 1) (#576). Dokumentationspflege: Planung, Umsetzungsvorlagen, parallele Sitzungen, allgemeine Skills (#577). Dateien zum Gegenlesen: DOCX und PDF mit QR-Kennung, Action Auschecken (#572, Teil 2) (#578). Material einbringen: Ablauf aus dem YAWA-Skill allgemein ins Programm (#574) (#580). Dokumentationspflege: Rollen von Planungs- und Code-Sitzung, Label in-arbeit:code (#581). Rückgabe einchecken: DOCX, PDF oder Foto der Ausdrucke per QR zuordnen, Befunde (#573) (#582). Skills ghostwriter-gegenlesen und ghostwriter-material übernehmen (#572, #573, #574) (#583). Schreibprüfung je Zugang statt Probe-Push (#579) (#586). Geänderten Text neu abschließen (#563) (#587). Allgemeine Skills nur an einer Stelle (#584) (#585). Modellvorgaben zentral, Modellfehler verständlich, Auftrag erneut versuchen (#554, #529) (#588). Hinweisdurchsicht: Einzelkarten, Varianten, Themen (#473, #570) (#589). Projektübersicht: Handlungsbedarf der Prüfungen (#538) (#591). Abschnitte als veraltet kennzeichnen (#510) (#590). Veraltet-Marke: Vor-/Nachspann, Auflage und Probedruck warnen (#510) (#600). Projektübersicht: Buch neu prüfen, Letzte Prüfungen nur erweitert (#538) (#601). release.py: Merge-Commits ohne Rumpf (Release vorbereiten) (#602). <!-- Entwurf (#488): überarbeiten und diese Markierung entfernen -->

**1.0.0:** Aufträge im Hintergrund gehen nicht mehr verloren: Recherche, Analyse, Colorieren und Import landen in einer Warteschlange pro Buch, die Ergebnis für Ergebnis speichert, sich bei Bedarf selbst fortsetzt und vom täglichen Update-Lauf angestoßen wird; beim Wiedereinstieg und im Bücherregal steht, was fertig ist (#476). Die Warteschlange lässt sich im Chat und in der Claude-Web-App ansehen, Aufträge vorziehen und abbrechen; Recherchen geben Vorwissen aus früheren Läufen weiter (#478). Team und Rollen je Buch – Eigentümer, Bearbeiter, Leser, Freigabeberechtigte –, Commits unter eigenem Namen, und `validate` lässt Abschlüsse oder Auflagen von Personen ohne Freigaberecht scheitern (#455); persönliche Freigaberechte gelten auch für Organisationskonten (#169). Bildrecherche mit Kandidaten, Quelle, Urheber und Lizenz; ungeklärte Rechte werden genannt, übernommen wird nur nach Bestätigung (#218). Kosten getrennt nach tatsächlich, geschätzt, manuell und unbekannt, Rechnungen lassen sich eintragen (#66). Vor dem Schreiben erkennt der Assistent geänderte Anweisungen, Programmstände und Arbeitsbranches; Branches werden nur nach vollständiger Übernahme gelöscht (#179). Allgemeine Skills kommen aus einer versionierten Quelle, jeder Assistent lädt sie aus dem Repository (#532). Claude-Web-App: Figuren mit Profilbildern, Figuren der Serie, Hinweisdurchsicht mit Übernehmen ins Manuskript, Skills des Buchs als Anleitung. Die Hinweisdurchsicht findet Stellen mit Auslassungspunkten und im anderen Abschnitt und meldet ehrlich, wenn der Wortlaut fehlt (#522); der Verlauf der Prüfläufe bleibt im Widget klein (#497). Neuer Befehl „Buchansicht <Buch>“ öffnet ein Buch direkt über Nummer, Kurztitel oder Titel (#562). Die Seite „Clients und Fähigkeiten“ sagt je Client, was angezeigt und ausgeführt wird und was ungeprüft ist (#555). Neue Versionen werden mit „Release vorbereiten“ geprüft und erst nach dem Satz „Release … freigeben und veröffentlichen“ mit Tag, Release und Dokumentationswebsite veröffentlicht (#488); die Website zeigt damit wieder die aktuelle Version (#530). Kommt wie jedes Update; die Datenversion bleibt 1.

**0.9.0:** Alle Einstellungen auf einen Blick mit Wert, Herkunft und Formular, auch für Bibliothek, Serie und Sammelband (#299). Das Update zieht offene Änderungspakete mit auf den neuen Stand (#470). Abschnittsdialog: Antworten schneller sichern (#314), wahlweise im Hintergrund (`answer_backup: hintergrund`, #487). Recherche mit Internet über den eingestellten Anbieter mit Kostenerfassung (#462), Recherche mit Hilfsagenten (#449), Rundumprüfung eines Kapitels (#447), Zeitleiste in Spalten (#450), „Als Figur sprechen“ (#464), Fotos colorieren (#452). Open WebUI schickt weniger an das Modell (#285). Bilder und Ablaufseiten sagen „abschließen“ (#295); Textfassungen ohne HTML-Reste (#498); Durchsichten nehmen eigene Angaben an. Die Prüfung im Pull Request ist deutlich schneller (#485). Kommt wie jedes Update; die Datenversion bleibt 1.

**0.8.0:** Figurengespräch: im Chat mit einer Figur sprechen, Neues kommt nur auf Auswahl ins Figurenprofil (#432). Die Prüfung im Pull Request führt nur noch die betroffenen Tests aus (#439). Marktvergleich des v1.0-Umfangs (#429), Meilensteine v0.8 und v0.9 in der Roadmap (#436). Manuskriptimport und Analysen aus dem Ausblick für v0.8 waren schon in 0.7.0 enthalten; offen ist nur noch die Prüfung der Import-Hinweistexte in allen vier Chat-Umgebungen (#124). Kommt wie jedes Update; die Datenversion bleibt 1.

**0.7.0:** Abschluss von v0.7 (Figuren und Bilder): Bildlage im Abschnitt mit Textumfluss und Breitenregler in PDF, DOCX und EPUB (#54), Chronologie aus Unterlagen mit Analyse, Erzählzeit ohne Kalenderjahr und Ausgabe als Datei (#364, #379), Abschnitte zusammenlegen, entfernen, verschieben (#293), schlankere Open-WebUI-Anweisungen (#296). Abnahmen v0.5 (#18), v0.6 (#41) und v0.7 (#54) bestanden. Kommt wie jedes Update; die Datenversion bleibt 1, neue Felder sind optional.

**0.6.1:** Sammelstand der seit 0.6.0 übernommenen Änderungen (u. a. Figuren, Serien, Vor- und Nachspann, Umschlag und Druck, Manuskriptimport, Chat-Analysen, Sitzungssicherung, Bücherregal mit Auflagen und Sicherungen). Kommt wie jedes Update, ohne Zutun und ohne neue Pflichtfelder; die Datenversion bleibt 1. Die Abnahme von v0.6 läuft weiter in #41.

**Ältere Prüfberichte nachtragen (#340):** Das Update liest vorhandene Berichte nicht von selbst ins Prüfprotokoll ein, weil es keine Ergebnisse erfinden darf. Nach dem Update listet `python3 scripts/checks.py import <buch>` die Berichte unter `analysis/` und `editorial/` ohne Eintrag als Vorschlag; im Chat bestätigt der Benutzer, dann trägt `--apply` die erkannten ein (ohne Fingerabdruck, Stand „unbekannt“). Frühere Analyseläufe übernimmt weiter `checks.py backfill`. `import --apply` ergänzt außerdem die Uhrzeit bestehender Einträge aus ihrem Bericht; Einträge ohne Uhrzeit im Bericht bekommen sie mit `checks.py set <buch> pr-NNN --time HH:MM` (#345).

## Hinweis im Chat

Liegt der Buch-Branch hinter dem Hauptrepository, zeigt die **Projektübersicht** oben einen Hinweis, etwa „GhostWriter-Update: 3 Commits hinter ploeffler/GhostWriter:main · Version 0.3.1 verfügbar“, mit dem Knopf **GhostWriter aktualisieren** (Textfassung: `U`). Das kommt vor, wenn seit dem letzten nächtlichen Lauf eine neue Version erschienen ist oder wenn die Action in deinem Repository noch nicht läuft. **GhostWriter aktualisieren** startet die Action sofort, sofern die GitHub-Verbindung des Chats das kann; sonst bekommst du den Link *Actions → GhostWriter aktualisieren → Run workflow*.

## Erzeugter Instanz-Einstieg

Der Update-Lauf erzeugt nach Migration und Projektprüfung eine kurze `START.md` für das Zielrepository. Die vollständige `START.md` im Hauptrepository bleibt die zentrale Quelle. Ihre Abschnitte werden vollständig in einzeln ladbare Dateien unter `docs/start/` aufgeteilt; `docs/start/index.md` erschließt die Fachanweisungen. Der Assistent soll den Einstieg intern lesen und nur die für seine Aufgabe benötigten Anweisungen nachladen.

Den Generator (`scripts/build_start.py`) lädt der Lauf dabei aus dem **neuen** Programmstand, nicht aus dem alten Stand des Zielrepositorys; so scheitert ein Update nicht an Platzhaltern, die erst mit ihm kommen. Ein aus `assistant.yml` erzeugter persönlicher Skill wird vor der Projektprüfung neu erzeugt (eigene Ergänzungen bleiben); ein von Hand geschriebener bleibt unberührt.

**Bibliotheken vor GhostWriter 0.6.1 (#336):** Das Update läuft mit dem `scripts/update_from_upstream.py`, das im Zielrepository liegt. Scheitert es mit `KeyError: 'DISPLAY'` oder „SKILL.md passt nicht zu assistant.yml“, einmal `scripts/update_from_upstream.py` aus dem Hauptrepository auf den Standard-Branch kopieren und das Update neu starten; danach aktualisiert es sich selbst. Lädt der neue Generator nicht, gilt der Zweig als fehlgeschlagen und bleibt unverändert.

Repository, aktueller Branch und Standard-Branch stammen aus dem Update-Lauf. Die Bediensprache folgt `interface.language` des Buchs, dann `interface_language` des Profils, dann Deutsch; für Englisch gibt es eine eigene Einstiegsvorlage. Ein Buch mit Kapiteln oder einer Phase nach `wizard` erhält den Wiedereinstieg; ein neuer Buchbranch bleibt im Wizard, auch wenn die Bibliothek schon eingerichtet ist. Ein vorhandenes Bibliotheksprofil oder Bücherregal kennzeichnet eine eingerichtete Bibliothek. Veränderliche Buchstände und Branch-Zuordnungen werden im Chat weiterhin live geprüft.

Optionale, ausdrücklich konfigurierte Instanzangaben stehen in `assistant.yml` **auf dem Standard-Branch**, auch für die Einstiege der Buchbranches:

```yaml
startup:
  client: openwebui
  tools:
    read_start: read_start_md
    read_file: read_file
```

Erlaubte Clients: `openwebui`, `chatgpt`, `claude`, `text`. Die Werkzeugnamen müssen zu den tatsächlich installierten Werkzeugen passen. Ohne diese Angaben bleibt die Zuordnung ausdrücklich unbekannt; aus einem Update kann kein Client oder Werkzeugname abgeleitet werden. Keine Token oder anderen Secrets eintragen. Änderungen am Profil mit `scripts/assistant.py ... set` speichern, damit der persönliche Skill weiterhin passt.

Die Erzeugung erfolgt **im selben Update-Commit** wie die Programmänderungen, auch bei einem erstmaligen Update. Sie läuft bei geänderten Vorlagen, Profil- oder Projektangaben erneut. Identische Eingaben erzeugen identische Dateien ohne Zeitstempel; der nächste Lauf erkennt den Stand als aktuell. Eine defekte Vorlage oder ein Generatorfehler verhindert den Push. Im Probelauf bleibt das Ziel unverändert.

Zusätzlich entsteht `docs/start/einstieg-openwebui.md` (Vorlagen `templates/start/openwebui.de.md` und `openwebui.en.md`, #204): ein eigener kurzer Einstieg nur für die Open-WebUI-Pipe „GhostWriter Direkt“. Er enthält nur Regeln, die dort gelten: welche Befehle die Pipe selbst ausführt, was das Gesprächsmodell tun darf und was in Open WebUI noch fehlt. Hinweise auf Widgets, Skripte und Schreibabläufe, die dort nicht möglich sind, fehlen bewusst. Das GitHub-Werkzeug ab 1.6 lädt ihn statt der allgemeinen kurzen `START.md` (Valve `START_VARIANT`). Bis zum Prompt-Compiler aus #204 wird die Vorlage von Hand gepflegt; ein Test prüft, dass sie nur Befehle nennt, die die Pipe tatsächlich ausführt.

Die Vorlagen liegen unter `templates/start/`, der Generator unter `scripts/build_start.py`. Die erzeugten Dateien gehören zum Programm und werden nicht individuell bearbeitet. Ein veralteter Update-Läufer muss zunächst selbst aktualisiert werden; läuft die erste Übernahme noch mit dem alten Skript, erzeugt erst der nächste Update-Lauf den Instanz-Einstieg.

Die kurze START.md spart Kontext, garantiert aber keine einmalige Ausführung durch das Modell. Die [Open-WebUI-Integration](../integrations/openwebui/README.md#kontrollierter-start-pro-chat) speichert den erfolgreichen Einstieg pro Benutzer und Chat und verhindert wiederholte GitHub-Abrufe; bei fehlendem Kontext stellt sie die Anweisungen aus dem gespeicherten Stand wieder her. Andere Clients benötigen eine entsprechende eigene Zustandsverwaltung. Open-WebUI-Modellparameter, Native-Modus und die Auswahl eingebauter Werkzeuge werden durch diese Datei nicht umgeschaltet. Ein Repository-Update verteilt den Werkzeugquelltext, installiert ihn aber nicht automatisch in Open WebUI.

## Eigenes Buch anlegen

> **Das Hauptrepository `ploeffler/GhostWriter` ist öffentlich** (seit 01.11.2026) und enthält nur das Programm, keine Buchinhalte (#48). Zum Lesen braucht dein Buch-Repository deshalb kein Token; `GHOSTWRITER_UPDATE_TOKEN` ist nur nötig, damit auch Workflow-Dateien aktualisiert werden (Schritt 4).

Ein Manuskript gehört in der Regel in ein **privates** Repository. Das bestimmt, wie du dein Buch anlegst:

| Weg | Buch privat? | Updates |
|---|---|---|
| **Neues Repository aus der Vorlage** (*Use this template*), Sichtbarkeit **Private** | ja | ja, automatisch; empfohlen |
| **Fork** des Hauptrepositorys | nur wenn das Hauptrepository privat ist; ein Fork eines öffentlichen Repositorys ist immer öffentlich | ja, automatisch |

**Empfohlen: privates Repository aus der Vorlage.** Es teilt keine Git-Historie mit dem Hauptrepository; die Update-Action vergleicht deshalb den Stand aus `.ghostwriter/update.yml` mit dem Hauptrepository, zählt die neuen Commits und übernimmt die Programmdateien. Dein Buch bleibt dabei genau wie bei einem Fork unangetastet.

Einmalig einrichten:

1. **Repository anlegen:** Im Hauptrepository *Use this template → Create a new repository*, Sichtbarkeit **Private**.
2. **Actions prüfen:** Im neuen Repository unter *Actions* nachsehen, ob Workflows laufen dürfen. (In einem Fork sind Workflows und geplante Läufe zuerst abgeschaltet: *I understand my workflows, go ahead and enable them* bestätigen und bei **GhostWriter aktualisieren** *Enable workflow* klicken.)
3. **Zugriff aufs Hauptrepository:** Ist das Hauptrepository **öffentlich**, ist dafür nichts nötig. Ist es **privat**, braucht dein Buch-Repository das Secret `GHOSTWRITER_UPDATE_TOKEN` mit Leserecht darauf: Gehört beides demselben Konto oder derselben Organisation, genügt ein Fine-grained Token; sonst geht es nur mit einem **klassischen Token** (Scopes `repo` und `workflow`), weil Fine-grained Tokens nicht auf private Repositorys anderer Besitzer zugreifen können.
4. **Workflow-Dateien:** Damit auch Dateien unter `.github/workflows/` aktualisiert werden, braucht dein Buch-Repository ebenfalls `GHOSTWRITER_UPDATE_TOKEN` (Fine-grained Token für dein eigenes Repository mit *Contents* und *Workflows: Read and write*). Ohne ihn läuft alles andere, nur diese Dateien bleiben stehen; das wird gemeldet.
5. **Einmal von Hand starten:** *Actions → GhostWriter aktualisieren → Run workflow*. Danach läuft es täglich, und die Projekteinstellungen zeigen Version und Datum.

**Nicht „Sync fork“ verwenden.** GitHubs Knopf *Sync fork* bzw. *Update branch* würde den ganzen Starter in dein Buch mergen, auch die Vorlage von `ghostwriter.yml`. Die Update-Action übernimmt nur die Programmdateien.

Gut zu wissen:

- In **öffentlichen** Repositorys schaltet GitHub geplante Workflows nach 60 Tagen ohne Aktivität ab; private Buch-Repositorys betrifft das nicht.
- Ein Fork eines **privaten** Repositorys wird gelöscht, wenn dir der Zugriff auf das Hauptrepository entzogen wird. Auch deshalb ist ein eigenes Repository aus der Vorlage sicherer.
- Ordner, die nur der Entwicklung dienen (`tests/`, `backend/`), werden in Büchern nicht aktualisiert und können gelöscht werden.

## Branch-Orientierung in bestehenden Buch-Repositorys

`BUCHSTATUS.md` gehört zu den verwalteten GhostWriter-Dateien. Sobald die Änderung im Hauptrepository nach `main` übernommen ist, verteilt die tägliche Update-Action sie wie andere Programm- und Dokumentationsdateien auf bestehende Buch-Repositorys und deren Buch-Branches. Voraussetzung ist, dass die Update-Action im jeweiligen Repository eingerichtet und aktiviert ist; ein manueller Lauf ist jederzeit möglich (*Actions → GhostWriter aktualisieren → Run workflow*). Neue Repositorys aus der Vorlage enthalten die Datei bereits beim Anlegen.

Die Datei wird beim Update aus dem Hauptrepository übernommen. Individuelle Buchinhalte und persönliche Branch-Zuordnungen gehören nicht hinein: Der Assistent prüft die Branch-Liste bei jedem Wiedereinstieg live. Das Update legt keine Branches an, verschiebt keine Manuskripte und merged keine Buch-Branches; offene Änderungspakete bekommen nur den Stand ihres Buchs (siehe oben).

## Ein- und ausschalten

In der Projektübersicht → **Projekteinstellungen** → **Updates**: „Neue GhostWriter-Versionen automatisch einspielen“. Dort siehst du auch die installierte Version und das Datum des letzten Updates. In `ghostwriter.yml`:

```yaml
updates:
  auto: true    # false = keine automatischen Updates
```

Ein Update von Hand: in GitHub unter *Actions → GhostWriter aktualisieren → Run workflow*. Mit **Probelauf** siehst du nur, was sich ändern würde.

## Limits: Automatik pausiert

Vor dem Einspielen prüft die Action `scripts/limits.py check --live --automation`: das KI-Budget des Monats (`limits.ai_budget_monthly` gegen die Backend-API-Kosten in `costs/`), die GitHub-Actions-Minuten des Repositorys (`limits.actions_minutes_monthly`; in privaten Repositorys ohne eigene Angabe 2000 wie im Free-Plan) und das API-Rate-Limit des Tokens. Ist bei einem davon **weniger als 10 %** übrig, läuft die tägliche Prüfung nicht weiter: Der Schritt „Updates einspielen“ wird übersprungen, und die Action legt das Issue **„GhostWriter-Automatik pausiert“** an (bzw. aktualisiert es) mit dem Grund. Unter **20 %** steht eine Vorwarnung in der Zusammenfassung des Laufs und in der Projektübersicht.

Weiter geht es von selbst, sobald wieder genug übrig ist – meist mit dem neuen Monat; dann schließt der nächste Lauf das Issue. Von Hand gestartete Läufe (*Run workflow*) laufen immer. Die Beträge stehen in **Projekteinstellungen → Limits**:

```yaml
limits:
  ai_budget_monthly: 10          # € je Monat; fehlt = keine Prüfung
  actions_minutes_monthly: 2000  # fehlt = keine Prüfung, in privaten Repositorys 2000
  actions_minutes_warn_below: 300   # Vorwarnung unter 300 Restminuten (null = aus)
  actions_minutes_pause_below: 100  # Pause unter 100 Restminuten (null = aus)
  warn_below_percent: 20
  pause_below_percent: 10
```

Bei den Actions-Minuten gilt die strengere Stufe aus Prozent und Restminuten. Bei 2000 Minuten greifen zuerst die Prozente (Vorwarnung ab 400, Pause ab 200 Restminuten); die festen Restminuten schützen größere Kontingente, bei denen 10 % erst spät kämen.

Kontingente bei den KI-Anbietern selbst kommen mit dem Backend (#19, #66).

### Actions-Minuten privater Bibliotheken (#277)

Private Repositorys haben im Free-Plan **2000 Actions-Minuten im Monat**. Ist das Kontingent leer, startet GitHub keinen Lauf mehr; jeder Lauf endet mit dem Hinweis *„The job was not started because recent account payments have failed or your spending limit needs to be increased“*. Speichern geht weiter, aber Bücherregal (`library.json`), Übersichtsdatei, Prüfung und Auflagen bleiben stehen, bis der neue Monat beginnt oder in den GitHub-Einstellungen ein Ausgabenlimit gesetzt ist.

Damit normale Schreibarbeit deutlich darunter bleibt, starten die Workflows nur, wenn es nötig ist:

| Workflow | Läuft bei | Spart |
|---|---|---|
| Projektdateien prüfen (`validate.yml`) | Push auf den Standard-Branch oder `buch/*`, jeder Pull Request | Pushes auf Arbeits-Branches (`ghostwriter/*`, `codex/*` …) werden über ihren Pull Request geprüft, nicht bei jedem Push; reine Bot-Ausgaben (`ghostwriter-index.json`, `library.json`) lösen keine Prüfung aus; ein neuer Push bricht den älteren Lauf ab |
| Übersichtsdatei aktualisieren (`index.yml`) | Push mit Buchdateien auf den Standard-Branch oder `buch/*` | Zwischenstände werden abgebrochen, Arbeits-Branches starten keinen Lauf und bekommen die Datei nach dem Merge |
| Auflage veröffentlichen (`edition.yml`) | Push auf `ghostwriter.yml` im Standard-Branch oder `buch/*` | Arbeits-Branches starten keinen Runner |
| Bücherregal aktualisieren (`library.yml`) | Push mit Buchdateien auf den Standard-Branch oder `buch/*`, eigener Pull Request geöffnet/geschlossen, Branch gelöscht, nach dem Update | kein Lauf beim Anlegen eines Branchs und bei Pushes auf Arbeits-Branches; ein neuer Lauf bricht den älteren ab |

Ein übersprungener Lauf erscheint in der Actions-Liste als *skipped* und kostet keine Minute. Pushes auf Arbeits-Branches (`ghostwriter/…`, `codex/…`, `claude/…`, `feat/…` usw., Liste wie in *Branches aufräumen*) legen seit #287 gar keinen Lauf mehr an, auch keinen übersprungenen.

**Weniger E-Mails von GitHub (#287):** GitHub benachrichtigt dich über Läufe, die du selbst ausgelöst hast – also über fast jeden Speichervorgang. Unter **GitHub → Settings → Notifications → System → Actions** stellst du *Only notify for failed workflows* ein oder schaltest *Email* dort aus. Abgebrochene Läufe (*cancelled*) entstehen gewollt, wenn ein neuer Lauf einen älteren ersetzt, und sind kein Fehler.

**Rechtzeitig gewarnt:** Nach jedem Lauf *Bücherregal aktualisieren* schätzt `scripts/limits.py` den Verbrauch des Monats aus allen Läufen dieses Repositorys (je Lauf auf volle Minuten aufgerundet, wie GitHub abrechnet; übersprungene Läufe zählen nicht). Ist die Vorwarnstufe erreicht (unter 20 % oder unter 300 Restminuten), legt der Lauf das Issue **„GhostWriter: Actions-Minuten knapp“** an und hält es aktuell; GitHub benachrichtigt dich darüber. In der Pausenstufe (unter 10 % oder unter 100 Restminuten) **hält der Lauf die Automatik an** (#62): Er setzt die Repository-Variable `GHOSTWRITER_ACTIONS_PAUSED=true`. Prüfung, Übersichtsdatei und Bücherregal fragen sie in ihrer Startbedingung ab und starten dann nicht mehr von selbst (*skipped*, ohne Minuten); die tägliche Update-Prüfung setzt aus. Weiter gehen Speichern, Auflagen und alle von Hand gestarteten Läufe (*Run workflow*), damit die letzten Minuten dafür bleiben. Nur der tägliche Lauf *GhostWriter aktualisieren* läuft weiter (etwa eine Minute am Tag); er misst neu und löscht die Variable, sobald wieder genug übrig ist – meist mit dem neuen Monat. Dann schließt der nächste Lauf das Issue.

Die Variable setzen darf nur ein Token mit Variablen-Recht: `GHOSTWRITER_UPDATE_TOKEN` mit *Variables: Read and write* (bzw. klassisch `repo`, siehe unten). Fehlt das Recht, steht im Issue, wie du sie von Hand anlegst (*Settings → Secrets and variables → Actions → Variables*, Name `GHOSTWRITER_ACTIONS_PAUSED`, Wert `true`); im neuen Monat erinnert das Issue ans Löschen. Mit dem Löschen der Variable lässt sich die Pause jederzeit auch selbst aufheben. Die Schätzung sieht nur dieses Repository: Andere private Repositorys desselben Kontos zählen beim Kontingent mit; dann `limits.actions_minutes_monthly` entsprechend kleiner einstellen. Den genauen Stand zeigt GitHub unter **Settings → Billing and plans**. Viele alte Arbeits-Branches verursachen keinen Verbrauch mehr, aufräumen lohnt sich trotzdem (Actions → *Branches aufräumen*).

## Token für private Hauptrepositorys und Workflow-Dateien

(Für ein fremdes privates Hauptrepository gilt der klassische Token aus „Eigenes Buch anlegen“, Schritt 3.)

Ohne weitere Einrichtung funktioniert das Update, wenn das Hauptrepository öffentlich ist bzw. dein Buch im Hauptrepository selbst liegt. Zwei Fälle brauchen ein Secret `GHOSTWRITER_UPDATE_TOKEN`:

- **Das Hauptrepository ist privat.** Dann darf dein Repository es sonst nicht lesen.
- **Workflow-Dateien.** GitHub erlaubt Actions mit dem eingebauten Token nicht, Dateien unter `.github/workflows/` zu ändern. Ohne Secret werden diese Dateien ausgelassen; das Update meldet das, und die Projekteinstellungen zeigen einen Hinweis.

So legst du es an:

1. GitHub → *Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token*.
2. **Repository access:** dein Buch-Repository und, falls privat, das Hauptrepository.
3. **Permissions:** *Contents: Read and write* und *Workflows: Read and write* für dein Buch-Repository, dazu *Variables: Read and write*, damit die Automatik bei knappen Actions-Minuten pausieren kann (#62); *Contents: Read-only* für das Hauptrepository.
   Mit einem klassischen Token stattdessen die Scopes `repo` und `workflow` anhaken. Fehlt das Workflow-Recht, lehnt GitHub den Push ab („refusing to allow a Personal Access Token to create or update workflow … without `workflow` scope“); das Update meldet dann genau das. Ein bestehender Fine-grained Token lässt sich nachträglich unter *Edit* um *Workflows* erweitern, ohne ihn neu einzutragen.
4. Ablaufdatum setzen, Token erzeugen und kopieren.
5. In deinem Buch-Repository unter *Settings → Secrets and variables → Actions → New repository secret* als `GHOSTWRITER_UPDATE_TOKEN` hinterlegen.

Der Token gehört wie jeder Schlüssel nie in den Chat oder in eine Datei (siehe [API-Schlüssel als GitHub-Secret](DIENSTE-NUTZEN.md#api-schlüssel-als-github-secret)).

## Eigene Änderungen an Programmdateien

Änderungen an Programmdateien in deinem Buch-Repository werden beim nächsten Update überschrieben. Was dein Buch betrifft, gehört in `ghostwriter.yml` (Projektdaten, Einstellungen) oder unter `chapters/`. Fehlt dir etwas in GhostWriter selbst, ist der richtige Ort das Hauptrepository.

## Für Entwickler

- Welche Dateien zum Programm gehören, steht in `ghostwriter-manifest.yml` (`managed`, `book`). Neue Programmordner dort eintragen.
- `version` im Manifest beim Merge eines Versionsschritts nach `main` erhöhen; Bücher mit höherer Version werden nicht aktualisiert.
- **Datenstruktur ändern (#59):** Wer ein Buch-Schema in `schemas/` ändert, erhöht `DATA_VERSION` in `scripts/migrate_project.py`, trägt die Migration unter `MIGRATIONS[<neue Version>]` ein (idempotent, nur Struktur) und schreibt den Fingerabdruck neu: `python scripts/migrate_project.py --fingerprint`. Ist die Änderung rückwärtskompatibel (nur neue, optionale Felder), genügt der neue Fingerabdruck. Die Doku-Prüfung (`scripts/check_docs.py` in `validate.yml`) schlägt sonst an. Tests: `tests/test_migration.py` migriert die Beispielbücher (Datenversion 0) und prüft, dass ein zweiter Lauf nichts ändert.
- Liegt ein Buch als Branch im Hauptrepository (z. B. `test/test-book`), aktualisiert die Action dort nur Bücher nach der Erkennungsregel (`scripts/library.py`: `buch/*`-Branches, sonst Branches mit Kapiteln) außer `update.skip_branches` (`main`, `v*`, `ghostwriter/*` …), jeweils gegen `main`. In Forks und eigenen Repositorys prüft sie den Standard-Branch und alle Bücher (Abschnitt „Bibliothek“).
- Ein Buch-Branch, auf dem eine Entwicklungsfassung getestet wird, bekommt sonst nachts wieder die Programmdateien von `main`. Deshalb in Entwicklungs-Branches `version` im Manifest sofort erhöhen (z. B. `0.4.0`); Bücher mit höherer Version werden nicht angefasst.
- `tests/` gehört nicht zu `managed` und wird nicht verteilt. Tests und Testbücher (`tests/fixtures/`) prüft `validate.yml` deshalb nur im Hauptrepository; in Buch-Repositorys prüft sie nur das Buch selbst.
- Im Hauptrepository installiert `validate.yml` vor den Tests die Satzpakete (pandoc, XeLaTeX, poppler-utils – dieselben wie Probedruck, Auflage und Sammelband – sowie qpdf für die Vorderseite im PDF, #324). Die heruntergeladenen Pakete liegen in einem GitHub-Cache; installiert wird bei jedem Lauf. Ohne diese Pakete würden die PDF-, EPUB- und Import-Tests übersprungen statt geprüft.
- Lokal testen: `GITHUB_REPOSITORY=owner/buch GHOSTWRITER_UPSTREAM_URL=<pfad-oder-url> python scripts/update_from_upstream.py --dry-run --status status.json`.

## Sicheres Aufräumen nach der Übernahme

Die Action **Branches aufräumen** löscht einen
geprüften Arbeitsbranch nur, wenn sein Head auf dem Server noch dem bestätigten
Stand entspricht. Ein inzwischen hinzugekommener Commit verhindert die Löschung.
Bei Versionsbranches muss zusätzlich der gleichnamige Erhaltungstag unverändert
vorhanden sein; Tagprüfung und Löschung bilden einen atomaren Vorgang.

Technisch nutzt sie [GitHubs `updateRefs` mit `beforeOid`](https://docs.github.com/en/graphql/reference/git#updaterefs).
Fehlen GraphQL-Zugriff oder Berechtigungen oder ist die Antwort unklar, wird die
Löschung nicht als erfolgreich gemeldet. Es gibt keinen unbedingten Löschversuch
als Ersatz und keine automatische Wiederholung. Vor einem neuen Auftrag den
Remote-Stand prüfen. **Nur anzeigen** sendet keine Löschmutation.
Die bisherigen Prüfungen auf übernommene Inhalte bleiben erforderlich; eine
passende Commit-ID allein ist keine Übernahmefreigabe.

## Update mit persönlicher Freigabeprüfung

Ein Update, das `scripts/approval_authority.py` und die Action `approval.yml` enthält, erhält vorhandene Manuskripte und Freigabeeinträge. Alte Namen werden nicht automatisch zu verifizierten Identitäten. Vor der nächsten veröffentlichbaren Ausgabe ist deshalb ein neuer [persönlicher Inhaltsnachweis](SPEICHERN.md#persönliches-freigaberecht-und-inhaltsnachweis) für den aktuellen Buchstand und die Auflage erforderlich. Entwürfe, Probedrucke und Vorabfassungen bleiben möglich; veröffentlichte Auflagen werden nicht verändert.

Bei Open WebUI GitHub-Werkzeug 1.8.0 einspielen und persönliche Benutzer-Valves für Schreibzugänge einrichten; der gemeinsame Werkzeug-Token dient nur noch zum Lesen. Den gemeinsamen Token nicht als persönlichen Zugang übernehmen. Bisher geteilte schreibberechtigte Tokens widerrufen oder durch getrennte persönliche Zugänge ersetzen; der gemeinsame Token braucht nur Leserechte. Keine Tokens im Buch speichern. Die Claude-Web-App muss den Prüfablauf in Claude übernehmen. Automatisierte Jobs können Nachweise vorbereiten und prüfen, aber keine neuen persönlichen Freigaben erteilen. Praktische Clientabnahme und echte Organisationsrechte bleiben gesondert zu prüfen.


---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
