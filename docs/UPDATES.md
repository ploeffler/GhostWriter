# GhostWriter-Updates

Dein Buch-Repository bekommt neue GhostWriter-Versionen automatisch aus dem Hauptrepository. Du musst dafür nichts tun; diese Seite erklärt, was dabei passiert und was du einrichten kannst.

## Was passiert

Kennst du den Hinweis „This branch is 3 commits behind ploeffler/GhostWriter:main“ auf GitHub? Genau den räumt GhostWriter für dich auf, nur sicherer als GitHubs Knopf *Sync fork*.

Die Action **„GhostWriter aktualisieren“** (`.github/workflows/update.yml`) läuft jeden Tag um 03:23 Uhr (UTC) und lässt sich jederzeit von Hand starten. Sie prüft **jeden Branch** deines Repositorys: Wie viele Commits liegt er hinter seinem Gegenstück im Hauptrepository (gleichnamiger Branch, sonst `main`)? Bei einem Repository aus der Vorlage zählt sie die Commits seit dem letzten eingespielten Stand. Liegt er dahinter, spielt sie die Commits ein:

1. **Branch ohne eigene Commits** (reine Kopie): Er wird einfach nachgezogen, wie bei *Sync fork*.
2. **Branch mit deinem Buch:** Die Commits des Hauptrepositorys werden **hineingemergt**. Dabei gilt das Manifest (`ghostwriter-manifest.yml`):
   - **Programmdateien** (`managed`: `START.md`, `README.md`, `CLAUDE.md`, `AGENTS.md`, der allgemeine Skill `.claude/skills/ghostwriter/`, `docs/`, `schemas/`, `scripts/`, `templates/`, `assets/` (Logo und App-Symbole), `.github/workflows/`, `workflow.yml`, `providers.yml` …) kommen genau so, wie sie im Hauptrepository sind.
   - **Dein Buch** (`book`: `ghostwriter.yml`, `chapters/`, `costs/`, `research/`, `approvals.yml`, das Assistenten-Profil `assistant.yml`; der persönliche Skill daneben unter `.claude/skills/` wird nie angefasst) bleibt genau so, wie es ist, auch wenn das Hauptrepository die Vorlagen dafür geändert hat.
   - Konflikte in anderen Dateien bricht die Action ab und meldet sie; die führst du von Hand zusammen.
3. **Migrationen.** Jedes Buch trägt eine **Datenversion** (`data_version` in `ghostwriter.yml`, fehlt = 0). Ist die neue GhostWriter-Version weiter, bringt `scripts/migrate_project.py` das Buch Schritt für Schritt auf den neuen Stand (0 → 1 → 2 …, auch über mehrere Versionen hinweg). Geändert wird nur die Struktur (neue Felder mit Vorgaben, Umbenennungen, verschobene Dateien), nie Texte, Freigaben, Läufe oder Kosten. Was umgestellt wurde, steht im Commit und in `.ghostwriter/update.yml` (`migration`); die Projekteinstellungen zeigen es beim Update-Stand. Ist ein Buch neuer als das Programm, bricht die Migration ab, und nichts wird verändert.
4. **Prüfung.** Danach laufen die Übersichtsdatei und die Projektprüfung mit der neuen Version. **Schlägt die Prüfung fehl, wird nichts eingespielt.** Stattdessen öffnet die Action ein Issue „GhostWriter-Update fehlgeschlagen (Branch)“ mit dem Grund. Beim nächsten erfolgreichen Lauf wird es geschlossen.
5. **Push mit Wiederholung:** Lehnt GitHub den Push mit einem Serverfehler ab („Internal Server Error“ u. ä.), versucht die Action es bis zu dreimal mit kurzer Pause. Ist der Branch während des Laufs weitergewandert (etwa durch „Bücherregal aktualisieren“), holt sie den neuen Stand und spielt das Update für diesen Branch einmal neu ein. Erst danach gilt der Branch als fehlgeschlagen; das Issue „GhostWriter-Update fehlgeschlagen“ nennt die Meldung von GitHub.
6. **Ein Commit je Branch:** „GhostWriter aktualisiert auf <Version>“ mit der Zeile `GhostWriter-Aktion: update`. Der Stand steht in `.ghostwriter/update.yml`.

Danach liegt kein Branch mehr hinter dem Hauptrepository, und GitHubs Hinweis „… commits behind“ verschwindet. Ein Buch wird nie auf eine **ältere** Programmversion zurückgesetzt. Die Zusammenfassung jedes Laufs (*Actions → GhostWriter aktualisieren*) zeigt je Branch, wie weit er zurück war und was passiert ist.

Neue Versionen erscheinen erst, wenn ein Versionsschritt im Hauptrepository nach `main` gemergt ist. Zwischenstände aus Entwicklungs-Branches kommen nicht in dein Buch.

## Bibliothek: mehrere Bücher in einem Repository

In einer Bibliothek (#36–#39) liegt auf dem Standard-Branch nur das Programm, jedes Buch auf einem eigenen Branch `buch/<slug>`. Die Action aktualisiert zuerst den Standard-Branch und danach jedes Buch einzeln; die Zusammenfassung zeigt eine Zeile je Buch. Welche Branches Bücher sind, entscheidet die Erkennungsregel in `scripts/library.py`: der Standard-Branch nur, wenn er Kapitel hat (Einzelbuch), jeder `buch/*`-Branch, sonst Branches mit Kapiteln. Arbeits-Branches (`ghostwriter/…`) und andere Branches werden nicht angefasst; offene Änderungen bekommen das Update mit dem nächsten „Änderungen übernehmen“. Ein Fehler in einem Buch hält die anderen nicht auf; für das betroffene Buch öffnet die Action ein Issue.

## Von v0.5 auf v0.6

**Ohne Zutun:** Ein Repository mit einem Buch auf dem Standard-Branch (Einzelbuch) bekommt v0.6 wie jedes Update und läuft unverändert weiter. Der Standard-Branch hat Kapitel und gilt deshalb weiter als das Buch; ein Link auf das Repository zeigt wie bisher dessen Projektübersicht.

**Umwandeln in eine Bibliothek (optional):** Wer mehrere Bücher in einem Repository führen möchte, startet einmal die Action *Actions → In Bibliothek umwandeln → Run workflow* auf dem Standard-Branch. Ohne Eingabe ist das ein **Probelauf**: Er prüft alles und zeigt, was passieren würde, ändert aber nichts. Erst mit `UMWANDELN` im Feld *confirm*:

1. Prüfen: Der Standard-Branch hat Kapitel; im Arbeits-Branch liegen keine offenen Änderungen (sonst zuerst im Chat „Änderungen übernehmen“); der Name `buch/<kurztitel>` ist frei (anderer Kurztitel über das Feld *title_short*).
2. Das Buch bekommt den Branch `buch/<kurztitel>` auf genau demselben Commit, also mit seiner ganzen Historie, und wird dort geprüft (Projektprüfung).
3. Erst danach bekommt der Standard-Branch einen Commit „In Bibliothek umgewandelt“: Buchdateien (`chapters/`, `costs/`, `research/`, `editions/`, `approvals.yml`, Übersichtsdatei) entfernt, `ghostwriter.yml` wieder der Starter, `library.json` für das Bücherregal.

Tags und Releases bleiben gültig; sie zeigen weiter auf ihre Commits. Neue Auflagen entstehen auf dem Buch-Branch. Im Chat öffnet der Link auf das Repository danach das Bücherregal, ein weiteres Buch kommt über „Neues Buch“ dazu.

**Rückweg:** Den Commit „In Bibliothek umgewandelt“ auf dem Standard-Branch rückgängig machen (auf GitHub: Commit öffnen → *Revert*, oder `git revert`), danach den Branch `buch/<kurztitel>` löschen, sofern dort seitdem nichts Neues geschrieben wurde; sonst diese Änderungen vorher auf den Standard-Branch übernehmen.

Neue Pflichtfelder gibt es mit v0.6 nicht; die Datenversion bleibt 1 (`scripts/migrate_project.py`).

## Hinweis im Chat

Liegt der Buch-Branch hinter dem Hauptrepository, zeigt die **Projektübersicht** oben einen Hinweis, etwa „GhostWriter-Update: 3 Commits hinter ploeffler/GhostWriter:main · Version 0.3.1 verfügbar“, mit dem Knopf **Update einspielen** (Textfassung: `U`). Das kommt vor, wenn seit dem letzten nächtlichen Lauf eine neue Version erschienen ist oder wenn die Action in deinem Repository noch nicht läuft. **Update einspielen** startet die Action sofort, sofern die GitHub-Verbindung des Chats das kann; sonst bekommst du den Link *Actions → GhostWriter aktualisieren → Run workflow*.

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

Die Datei wird beim Update aus dem Hauptrepository übernommen. Individuelle Buchinhalte und persönliche Branch-Zuordnungen gehören nicht hinein: Der Assistent prüft die Branch-Liste bei jedem Wiedereinstieg live. Das Update legt keine Branches an, verschiebt keine Manuskripte und merged keine Buch- oder Arbeits-Branches.

## Ein- und ausschalten

In der Projektübersicht → **Projekteinstellungen** → **Updates**: „Neue GhostWriter-Versionen automatisch einspielen“. Dort siehst du auch die installierte Version und das Datum des letzten Updates. In `ghostwriter.yml`:

```yaml
updates:
  auto: true    # false = keine automatischen Updates
```

Ein Update von Hand: in GitHub unter *Actions → GhostWriter aktualisieren → Run workflow*. Mit **Probelauf** siehst du nur, was sich ändern würde.

## Limits: Automatik pausiert

Vor dem Einspielen prüft die Action `scripts/limits.py check --live --automation`: das KI-Budget des Monats (`limits.ai_budget_monthly` gegen die Backend-API-Kosten in `costs/`), die GitHub-Actions-Minuten des Repositorys (`limits.actions_minutes_monthly`, etwa 2000 im Free-Plan bei privaten Repositorys) und das API-Rate-Limit des Tokens. Ist bei einem davon **weniger als 10 %** übrig, läuft die tägliche Prüfung nicht weiter: Der Schritt „Updates einspielen“ wird übersprungen, und die Action legt das Issue **„GhostWriter-Automatik pausiert“** an (bzw. aktualisiert es) mit dem Grund. Unter **20 %** steht eine Vorwarnung in der Zusammenfassung des Laufs und in der Projektübersicht.

Weiter geht es von selbst, sobald wieder genug übrig ist – meist mit dem neuen Monat; dann schließt der nächste Lauf das Issue. Von Hand gestartete Läufe (*Run workflow*) laufen immer. Die Beträge stehen in **Projekteinstellungen → Limits**:

```yaml
limits:
  ai_budget_monthly: 10          # € je Monat; fehlt = keine Prüfung
  actions_minutes_monthly: 2000  # fehlt = keine Prüfung
  warn_below_percent: 20
  pause_below_percent: 10
```

Kontingente bei den KI-Anbietern selbst kommen mit dem Backend (#19, #66).

## Token für private Hauptrepositorys und Workflow-Dateien

(Für ein fremdes privates Hauptrepository gilt der klassische Token aus „Eigenes Buch anlegen“, Schritt 3.)

Ohne weitere Einrichtung funktioniert das Update, wenn das Hauptrepository öffentlich ist bzw. dein Buch im Hauptrepository selbst liegt. Zwei Fälle brauchen ein Secret `GHOSTWRITER_UPDATE_TOKEN`:

- **Das Hauptrepository ist privat.** Dann darf dein Repository es sonst nicht lesen.
- **Workflow-Dateien.** GitHub erlaubt Actions mit dem eingebauten Token nicht, Dateien unter `.github/workflows/` zu ändern. Ohne Secret werden diese Dateien ausgelassen; das Update meldet das, und die Projekteinstellungen zeigen einen Hinweis.

So legst du es an:

1. GitHub → *Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token*.
2. **Repository access:** dein Buch-Repository und, falls privat, das Hauptrepository.
3. **Permissions:** *Contents: Read and write* und *Workflows: Read and write* für dein Buch-Repository; *Contents: Read-only* für das Hauptrepository.
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
- Lokal testen: `GITHUB_REPOSITORY=owner/buch GHOSTWRITER_UPSTREAM_URL=<pfad-oder-url> python scripts/update_from_upstream.py --dry-run --status status.json`.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
