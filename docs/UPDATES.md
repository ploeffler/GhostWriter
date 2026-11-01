# GhostWriter-Updates

Dein Buch-Repository bekommt neue GhostWriter-Versionen automatisch aus dem Hauptrepository. Du musst dafür nichts tun; diese Seite erklärt, was dabei passiert und was du einrichten kannst.

## Was passiert

Die Action **„GhostWriter aktualisieren“** (`.github/workflows/update.yml`) läuft jeden Tag um 03:23 Uhr (UTC). Sie vergleicht dein Buch mit dem Hauptrepository (`ghostwriter-manifest.yml`, `upstream`, in der Regel `ploeffler/GhostWriter`, Branch `main`) und spielt eine neue Version ein, wenn es eine gibt:

1. **Nur Programmdateien.** Ersetzt werden die Dateien unter `managed` im Manifest: `START.md`, `README.md`, `docs/`, `schemas/`, `scripts/`, `templates/`, `.github/workflows/`, `workflow.yml`, `providers.yml` und einige kleine Dateien. Dein Buch bleibt unangetastet: `ghostwriter.yml`, `chapters/`, `costs/`, `research/`, `approvals.yml`.
2. **Migrationen.** Braucht die neue Version neue Felder, ergänzt `scripts/migrate_project.py` sie in deinen Buchdateien, ohne Inhalte zu ändern.
3. **Prüfung.** Danach laufen die Übersichtsdatei und die Projektprüfung mit der neuen Version. **Schlägt die Prüfung fehl, wird nichts eingespielt.** Stattdessen öffnet die Action ein Issue „GhostWriter-Update fehlgeschlagen“ mit dem Grund. Beim nächsten erfolgreichen Lauf wird es geschlossen.
4. **Ein Commit.** Ein erfolgreiches Update ist ein einzelner Commit „GhostWriter aktualisiert auf <Version>“ mit der Zeile `GhostWriter-Aktion: update`. Der Stand steht in `.ghostwriter/update.yml`.

Ein Buch wird nie auf eine **ältere** Version zurückgesetzt. Ist dein Buch auf dem Stand des Hauptrepositorys, passiert nichts.

Neue Versionen erscheinen erst, wenn ein Versionsschritt im Hauptrepository nach `main` gemergt ist. Zwischenstände aus Entwicklungs-Branches kommen nicht in dein Buch.

## Ein- und ausschalten

In der Projektübersicht → **Projekteinstellungen** → **Updates**: „Neue GhostWriter-Versionen automatisch einspielen“. Dort siehst du auch die installierte Version und das Datum des letzten Updates. In `ghostwriter.yml`:

```yaml
updates:
  auto: true    # false = keine automatischen Updates
```

Ein Update von Hand: in GitHub unter *Actions → GhostWriter aktualisieren → Run workflow*. Mit **Probelauf** siehst du nur, was sich ändern würde.

## Token für private Hauptrepositorys und Workflow-Dateien

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
- Liegt ein Buch als Branch im Hauptrepository (z. B. `test/test-book`), aktualisiert die Action alle Branches mit Kapiteln außer `update.skip_branches` (`main`, `v*`, `ghostwriter/*` …).
- Lokal testen: `GITHUB_REPOSITORY=owner/buch GHOSTWRITER_UPSTREAM_URL=<pfad-oder-url> python scripts/update_from_upstream.py --dry-run`.
