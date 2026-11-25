# Full backup

[Deutsch](GESAMTSICHERUNG.md) · English

The **full backup** (#489) packs the whole repository into **one** ZIP file: readable without Git and without GitHub, and fully restorable on GitHub or on your own Git server (Gitea, Forgejo, plain Git). It is not the same as [saving a session](SESSION-BACKUP.en.md), which only keeps conversation work.

**Start it:** in the chat with `Sicherung erstellen` (the file arrives as a download) or on GitHub under *Actions → Gesamtsicherung → Run workflow*. There the result is a **private workflow artifact** (visible only to people with access to the repository, 14 days), never a release. Locally: `python3 scripts/sicherung.py erstellen <folder> -o backup.zip`.

## What is in the file

```
GhostWriter-Sicherung_<repo>_<date>.zip
├── LIESMICH.html              open first: contents, reading, restoring, limits
├── buecher/<book>/
│   ├── buch.html              the whole book, readable in a browser
│   ├── buch.epub              for e-readers
│   ├── buch.pdf               for printing (when LaTeX was available)
│   └── quelltext/             chapters (.md), images, book profile
├── repository.bundle          complete Git: all branches (also buch/*), tags, history
├── github-einstellungen.json  settings that are not in Git (secrets by name only)
├── github-daten/              issues and pull requests with comments: lesbar.md and JSON
├── wiederherstellen/          auf-github.sh/.bat, lokal-oeffnen.sh/.bat
└── pruefsummen.txt            SHA-256 of every file, date, program version, branch heads
```

The reading version shows the **working state** of all sections, not an edition. It is assembled without AI; nothing is rephrased.

## Restoring

- **Locally:** `git clone repository.bundle my-book`; then push to any target.
- **GitHub:** create an empty repository, then `./wiederherstellen/auf-github.sh https://github.com/NAME/new-repo.git` (Windows: `auf-github.bat`). The script first checks the checksums and `git bundle verify`, clones a mirror and transfers everything with `git push --mirror`; GitHub's own import does not accept bundles. With `gh` and `python3` it also applies the settings (below) and asks for each secret value one by one (empty = later).
- **Your own Git server:** `./auf-github.sh <url> nur-git` transfers Git only.
- **Check without restoring:** `python3 scripts/sicherung.py pruefen <file.zip>`.

## Settings that are not in Git

Workflows (`.github/workflows/`) come back with Git. Everything else is in `github-einstellungen.json` and saved as far as the access allows:

| Setting | Saved | When restoring |
|---|---|---|
| Secrets | **names only**, never values | the script asks for the values; skipped ones are listed as “still open” |
| Variables (`vars.*`) | names and values | set with `gh` |
| Actions enabled, workflow permissions (read/write, create pull requests) | state | set (GhostWriter needs write access) |
| Pages, environments, branch protection, collaborators | configuration where readable | by hand following `LIESMICH.html` |
| Installed GitHub apps | not readable through the API | please note them down |
| Run history, logs, artifacts | – | are lost |

What the access could not read (for example collaborators without admin rights) is listed with the reason under `nicht_lesbar`; the backup stays valid. At the end of a restore a trial run (“Projektdateien prüfen” under *Actions*) helps: if it runs, the Actions work.

## Limits

- Secret values are **never** read or output. The backup checks itself for key patterns; if it finds one (for example in an issue text), it is not delivered.
- The file contains **private book work**: hand it over only as a download in the chat or as a private artifact, never as a release and never publicly.
- A shallow clone (without history) is refused: run `git fetch --unshallow` first.
- Not in this version: password encryption and an automatic monthly backup (both later, if needed).


---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
