# GhostWriter updates

The update workflow brings program changes from the main GhostWriter repository into your book repository. This page describes the existing workflow; the [German developer guide](UPDATES.md) has additional technical detail.

## What the update does

The **GhostWriter aktualisieren** workflow (`.github/workflows/update.yml`) runs daily at 06:00 UTC and can also be started manually. It checks eligible branches against the upstream repository. For a repository created from the template, it uses the recorded upstream state in `.ghostwriter/update.yml`.

Program files listed under `managed` in `ghostwriter-manifest.yml` are updated, including the shared repository skills `ghostwriter`, `ghostwriter-lektorat` and `ghostwriter-buchgedaechtnis`. Personal skills remain book-owned. Book files listed under `book`, including manuscript, approvals, costs and the assistant profile, are preserved. Conflicts in other files cause the update to stop for manual resolution. Data migrations update structure where needed; they do not rewrite manuscript text or approvals. A newer book data version than the program supports stops the migration.

The update is validated before it is pushed. If validation fails, the branch is not updated and a failure issue is opened. The workflow retries certain server errors and retries once when the branch advances during the run. Its summary reports what happened for each branch. Books are not downgraded to an older program version.

In a library, the workflow updates the default branch and then each eligible book branch. Working branches are not updated directly. A failure on one book does not stop the others. The project overview may offer **Update einspielen** (install update) when a newer upstream state is available.

## Daily report and GitHub notifications

The scheduled update run posts the complete report, including branch results, at most once per UTC day in a dedicated issue. It mentions the recipient; GitHub can send the comment by email according to personal notification settings. No SMTP service or extra secrets are needed. Repeated runs do not create duplicate comments. Closing the issue pauses delivery; reopening it resumes delivery.

Manual runs send only when explicitly requested using the report-delivery input. Dry runs never send. Recipient selection, subscriptions and language settings are described in the [daily report guide](DAILY-SUMMARY.en.md#receive-the-daily-report).

## Create a private book repository

The main `ploeffler/GhostWriter` repository is public. For a private manuscript, the recommended route is **Use this template → Create a new repository**, then choose **Private**. A fork of a public repository is public.

1. Create the private repository from the template and check that Actions are enabled.
2. If the upstream repository is public, no token is needed just to read it. A private upstream requires suitable read access.
3. To update workflow files under `.github/workflows/`, configure the `GHOSTWRITER_UPDATE_TOKEN` repository secret with the necessary permissions. Without it, those workflow files are skipped and reported.
4. Run **Actions → GhostWriter aktualisieren → Run workflow** once. Later scheduled runs check for updates automatically.

Use the GhostWriter update workflow rather than GitHub's **Sync fork** button: the latter may merge starter book files as well as program files.

## Convert an existing single book into a library

A single-book repository can continue working after the v0.6 update. To hold multiple books, run **Actions → In Bibliothek umwandeln → Run workflow** on the default branch. Without confirmation it is a dry run. Enter `UMWANDELN` in the confirmation field only when ready to convert.

The workflow checks for a book, pending changes and an available `buch/<short-title>` branch name. It creates the book branch at the existing commit, preserving history, then converts the default branch to the program and library starter. Tags and releases continue to point to their original commits.

**0.8.0** adds the character conversation: talk to a character in the chat, and new details go into the character profile only if you select them (#432). Checks on a pull request now run only the affected tests (#439). Also a market comparison of the v1.0 scope (#429) and milestones v0.8 and v0.9 in the roadmap (#436). Manuscript import and the analyses planned for v0.8 were already part of 0.7.0; only the check of the import notices in all four chat environments is still open (#124). Arrives like every update; the data version stays 1.

**0.7.0** completes v0.7 (characters and images): image position in a section with text wrapping and a width slider in PDF, DOCX and EPUB (#54), a chronology from notes with analysis, narrative time without a calendar year and file export (#364, #379), merging, removing and moving sections (#293), leaner Open WebUI instructions (#296). Acceptance of v0.5 (#18), v0.6 (#41) and v0.7 (#54) passed. It arrives like any update; the data version stays 1 and new fields are optional.

**0.6.1** bundles the changes merged since 0.6.0 (including characters, series, front and back matter, cover and print, manuscript import, chat analyses, session backups, and a bookshelf with editions and backups). It arrives like any update, with no action required and no new mandatory fields; the data version stays 1. Acceptance of v0.6 continues in #41.

To reverse the conversion, revert the conversion commit on the default branch. Delete the book branch only after ensuring that no subsequent work on that branch would be lost; otherwise transfer that work first.

**Backfilling older check reports (#340):** The update does not read existing reports into the check log on its own, since it must not invent results. After the update, `python3 scripts/checks.py import <book>` lists reports under `analysis/` and `editorial/` without an entry as suggestions; once the user confirms in chat, `--apply` records the recognised ones (without fingerprint, state “unknown”). Earlier analysis runs are still handled by `checks.py backfill`. `import --apply` also adds the time of existing entries from their report; entries whose report gives no time get it with `checks.py set <book> pr-NNN --time HH:MM` (#345).

## Automatic updates and limits

Project settings control automatic updates. In `ghostwriter.yml`, `updates.auto: true` enables them and `false` disables them. A manual workflow run can be used to update or preview an update.

Scheduled updates check configured limits. By default, less than 10% remaining pauses the automatic update; less than 20% produces a warning. Once the limit recovers, a later scheduled run can resume. The settings can include a monthly AI budget, Actions minutes, warning threshold and pause threshold. Provider-side balances depend on future backend support.

Private repositories on the free plan have **2,000 Actions minutes per month**. When they are used up, GitHub starts no more runs (“The job was not started because … spending limit …”): saving still works, but the bookshelf, overview file, checks and editions stop until the next month or until a spending limit is set. To stay well below the quota, the workflows only start when needed (#277): checks run on pushes to the default branch and `buch/*` and on every pull request, not on every push to a work branch; bot outputs (`ghostwriter-index.json`, `library.json`) trigger no check; the overview file and editions only run on book branches; a newer push cancels the older run. Skipped runs cost no minutes. Pushes to work branches (`ghostwriter/…`, `codex/…`, `claude/…`, `feat/…` etc., same list as *Branches aufräumen*) create no run at all, not even a skipped one (#287). GitHub emails you about runs you triggered, i.e. almost every save: under **GitHub → Settings → Notifications → System → Actions** choose *Only notify for failed workflows* or turn off email there. Cancelled runs are expected when a newer run replaces an older one and are not an error. After every bookshelf run, `scripts/limits.py` estimates the month's usage from this repository's runs (rounded up per run; private repositories default to 2,000 minutes). Below 20% or 300 minutes left it opens the issue **“GhostWriter: Actions-Minuten knapp”**; below 10% or 100 minutes the run sets the repository variable `GHOSTWRITER_ACTIONS_PAUSED=true`: checks, overview file and bookshelf then no longer start by themselves (skipped, no minutes) and the daily update pauses, while saving, editions and manual runs continue (#62). The daily update run measures again and deletes the variable once enough is left. Setting it needs `GHOSTWRITER_UPDATE_TOKEN` with *Variables: Read and write*; otherwise the issue explains how to set and later delete it by hand. `limits.actions_minutes_warn_below` and `limits.actions_minutes_pause_below` change the fixed thresholds. Other private repositories of the same account share the quota.

## Update token

When needed, create a token with the least permissions required for the relevant repositories. Updating the book repository's workflow files requires suitable **Contents** and **Workflows** write permissions (plus **Variables** write so automation can pause when Actions minutes run low); reading a private upstream requires access to it. Store the token as the `GHOSTWRITER_UPDATE_TOKEN` Actions secret in the book repository. Never paste a token into a chat or commit it to a file. See [AI services](AI-SERVICES.en.md#api-keys-as-github-secrets).

## Changes to program files

Local changes to managed program files can be overwritten by an update. Keep book-specific settings in the book configuration and book content in the book's own files. The manifest specifies which paths are managed by the program and which belong to the book.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
