# GhostWriter-Updates

Dein Buch-Repository bekommt neue GhostWriter-Versionen automatisch aus dem Hauptrepository. Du musst dafür nichts tun; diese Seite erklärt, was dabei passiert und was du einrichten kannst.

## Was passiert

Kennst du den Hinweis „This branch is 3 commits behind ploeffler/GhostWriter:main“ auf GitHub? Genau den räumt GhostWriter für dich auf, nur sicherer als GitHubs Knopf *Sync fork*.

Die Action **„GhostWriter aktualisieren“** (`.github/workflows/update.yml`) läuft jeden Tag um 03:23 Uhr (UTC) und lässt sich jederzeit von Hand starten. Sie prüft **jeden Branch** deines Repositorys: Wie viele Commits liegt er hinter seinem Gegenstück im Hauptrepository (gleichnamiger Branch, sonst `main`)? Bei einem Repository aus der Vorlage zählt sie die Commits seit dem letzten eingespielten Stand. Liegt er dahinter, spielt sie die Commits ein:

1. **Branch ohne eigene Commits** (reine Kopie): Er wird einfach nachgezogen, wie bei *Sync fork*.
2. **Branch mit deinem Buch:** Die Commits des Hauptrepositorys werden **hineingemergt**. Dabei gilt das Manifest (`ghostwriter-manifest.yml`):
   - **Programmdateien** (`managed`: `START.md`, `README.md`, `docs/`, `schemas/`, `scripts/`, `templates/`, `.github/workflows/`, `workflow.yml`, `providers.yml` …) kommen genau so, wie sie im Hauptrepository sind.
   - **Dein Buch** (`book`: `ghostwriter.yml`, `chapters/`, `costs/`, `research/`, `approvals.yml`) bleibt genau so, wie es ist, auch wenn das Hauptrepository die Vorlagen dafür geändert hat.
   - Konflikte in anderen Dateien bricht die Action ab und meldet sie; die führst du von Hand zusammen.
3. **Migrationen.** Braucht die neue Version neue Felder, ergänzt `scripts/migrate_project.py` sie in deinen Buchdateien, ohne Inhalte zu ändern.
4. **Prüfung.** Danach laufen die Übersichtsdatei und die Projektprüfung mit der neuen Version. **Schlägt die Prüfung fehl, wird nichts eingespielt.** Stattdessen öffnet die Action ein Issue „GhostWriter-Update fehlgeschlagen (Branch)“ mit dem Grund. Beim nächsten erfolgreichen Lauf wird es geschlossen.
5. **Ein Commit je Branch:** „GhostWriter aktualisiert auf <Version>“ mit der Zeile `GhostWriter-Aktion: update`. Der Stand steht in `.ghostwriter/update.yml`.

Danach liegt kein Branch mehr hinter dem Hauptrepository, und GitHubs Hinweis „… commits behind“ verschwindet. Ein Buch wird nie auf eine **ältere** Programmversion zurückgesetzt. Die Zusammenfassung jedes Laufs (*Actions → GhostWriter aktualisieren*) zeigt je Branch, wie weit er zurück war und was passiert ist.

Neue Versionen erscheinen erst, wenn ein Versionsschritt im Hauptrepository nach `main` gemergt ist. Zwischenstände aus Entwicklungs-Branches kommen nicht in dein Buch.

## Hinweis im Chat

Liegt der Buch-Branch hinter dem Hauptrepository, zeigt die **Projektübersicht** oben einen Hinweis, etwa „GhostWriter-Update: 3 Commits hinter ploeffler/GhostWriter:main · Version 0.3.1 verfügbar“, mit dem Knopf **Update einspielen** (Textfassung: `U`). Das kommt vor, wenn seit dem letzten nächtlichen Lauf eine neue Version erschienen ist oder wenn die Action in deinem Repository noch nicht läuft. **Update einspielen** startet die Action sofort, sofern die GitHub-Verbindung des Chats das kann; sonst bekommst du den Link *Actions → GhostWriter aktualisieren → Run workflow*.

## Eigenes Buch anlegen

> **Derzeit ist das Hauptrepository `ploeffler/GhostWriter` privat** (entschieden am 01.11.2026). Ein Buch-Repository kann es nur lesen, wenn du dort als Mitarbeiter eingeladen bist und dein Buch-Repository das Secret `GHOSTWRITER_UPDATE_TOKEN` hat (Schritt 3). Ohne das laufen keine Updates; die Action meldet das in einem Issue, und die Projektübersicht zeigt den Hinweis.

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

## Ein- und ausschalten

In der Projektübersicht → **Projekteinstellungen** → **Updates**: „Neue GhostWriter-Versionen automatisch einspielen“. Dort siehst du auch die installierte Version und das Datum des letzten Updates. In `ghostwriter.yml`:

```yaml
updates:
  auto: true    # false = keine automatischen Updates
```

Ein Update von Hand: in GitHub unter *Actions → GhostWriter aktualisieren → Run workflow*. Mit **Probelauf** siehst du nur, was sich ändern würde.

## Token für private Hauptrepositorys und Workflow-Dateien

(Für ein fremdes privates Hauptrepository gilt der klassische Token aus „Eigenes Buch anlegen“, Schritt 3.)

Ohne weitere Einrichtung funktioniert das Update, wenn das Hauptrepository öffentlich ist bzw. dein Buch im Hauptrepository selbst liegt. Zwei Fälle brauchen ein Secret `GHOSTWRITER_UPDATE_TOKEN`:

- **Das Hauptrepository ist privat.** Dann darf dein Repository es sonst nicht lesen.
- **Workflow-Dateien.** GitHub erlaubt Actions mit dem eingebauten Token nicht, Dateien unter `.github/workflows/` zu ändern. Ohne Secret werden diese Dateien ausgelassen; das Update meldet das, und die Projekteinstellungen zeigen einen Hinweis.

So legst du es an:

1. GitHub → *Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token*.
2. **Repository access:** dein Buch-Repository und, falls privat, das Hauptrepository.
3. **Permissions:** *Contents: Read and write* und *Workflows: Read and write* für dein Buch-Repository; *Contents: Read-only* für das Hauptrepository.
4. Ablaufdatum setzen, Token erzeugen und kopieren.
5. In deinem Buch-Repository unter *Settings → Secrets and variables → Actions → New repository secret* als `GHOSTWRITER_UPDATE_TOKEN` hinterlegen.

Der Token gehört wie jeder Schlüssel nie in den Chat oder in eine Datei (siehe [API-Schlüssel als GitHub-Secret](DIENSTE-NUTZEN.md#api-schlüssel-als-github-secret)).

## Eigene Änderungen an Programmdateien

Änderungen an Programmdateien in deinem Buch-Repository werden beim nächsten Update überschrieben. Was dein Buch betrifft, gehört in `ghostwriter.yml` (Projektdaten, Einstellungen) oder unter `chapters/`. Fehlt dir etwas in GhostWriter selbst, ist der richtige Ort das Hauptrepository.

## Für Entwickler

- Welche Dateien zum Programm gehören, steht in `ghostwriter-manifest.yml` (`managed`, `book`). Neue Programmordner dort eintragen.
- `version` im Manifest beim Merge eines Versionsschritts nach `main` erhöhen; Bücher mit höherer Version werden nicht aktualisiert.
- Neue Pflichtfelder im Schema brauchen eine Migration in `scripts/migrate_project.py`, sonst schlägt die Prüfung in den Büchern fehl und das Update bleibt aus.
- Liegt ein Buch als Branch im Hauptrepository (z. B. `test/test-book`), aktualisiert die Action dort nur Branches mit Kapiteln außer `update.skip_branches` (`main`, `v*`, `ghostwriter/*` …), jeweils gegen `main`. In Forks und eigenen Buch-Repositorys prüft sie alle Branches.
- Ein Buch-Branch, auf dem eine Entwicklungsfassung getestet wird, bekommt sonst nachts wieder die Programmdateien von `main`. Deshalb in Entwicklungs-Branches `version` im Manifest sofort erhöhen (z. B. `0.4.0`); Bücher mit höherer Version werden nicht angefasst.
- Lokal testen: `GITHUB_REPOSITORY=owner/buch GHOSTWRITER_UPSTREAM_URL=<pfad-oder-url> python scripts/update_from_upstream.py --dry-run --status status.json`.
