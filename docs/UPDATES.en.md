# GhostWriter updates

The update workflow brings program changes from the main GhostWriter repository into your book repository. This page describes the existing workflow; the [German developer guide](UPDATES.md) has additional technical detail.

## What the update does

The **GhostWriter aktualisieren** workflow (`.github/workflows/update.yml`) runs daily at 03:23 UTC and can also be started manually. It checks eligible branches against the upstream repository. For a repository created from the template, it uses the recorded upstream state in `.ghostwriter/update.yml`.

Program files listed under `managed` in `ghostwriter-manifest.yml` are updated. Book files listed under `book`, including manuscript, approvals, costs and the assistant profile, are preserved. Conflicts in other files cause the update to stop for manual resolution. Data migrations update structure where needed; they do not rewrite manuscript text or approvals. A newer book data version than the program supports stops the migration.

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

**0.6.1** bundles the changes merged since 0.6.0 (including characters, series, front and back matter, cover and print, manuscript import, chat analyses, session backups, and a bookshelf with editions and backups). It arrives like any update, with no action required and no new mandatory fields; the data version stays 1. Acceptance of v0.6 continues in #41.

To reverse the conversion, revert the conversion commit on the default branch. Delete the book branch only after ensuring that no subsequent work on that branch would be lost; otherwise transfer that work first.

## Automatic updates and limits

Project settings control automatic updates. In `ghostwriter.yml`, `updates.auto: true` enables them and `false` disables them. A manual workflow run can be used to update or preview an update.

Scheduled updates check configured limits. By default, less than 10% remaining pauses the automatic update; less than 20% produces a warning. Once the limit recovers, a later scheduled run can resume. The settings can include a monthly AI budget, Actions minutes, warning threshold and pause threshold. Provider-side balances depend on future backend support.

## Update token

When needed, create a token with the least permissions required for the relevant repositories. Updating the book repository's workflow files requires suitable **Contents** and **Workflows** write permissions; reading a private upstream requires access to it. Store the token as the `GHOSTWRITER_UPDATE_TOKEN` Actions secret in the book repository. Never paste a token into a chat or commit it to a file. See [AI services](AI-SERVICES.en.md#api-keys-as-github-secrets).

## Changes to program files

Local changes to managed program files can be overwritten by an update. Keep book-specific settings in the book configuration and book content in the book's own files. The manifest specifies which paths are managed by the program and which belong to the book.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
