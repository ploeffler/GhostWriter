# GhostWriter updates

General skills originate from [ghostwriter-skills](https://github.com/ploeffler/ghostwriter-skills). Their bundled copies and `ghostwriter-skills.yml` are program files: a normal GhostWriter update distributes the reviewed pinned version, without fetching a moving skill branch at runtime. Personal skills remain protected. The optional book teaser is not installed automatically.

The update workflow brings program changes from the main GhostWriter repository into your book repository. This page describes the existing workflow; the [German developer guide](UPDATES.md) has additional technical detail.

## What the update does

The **GhostWriter aktualisieren** workflow (`.github/workflows/update.yml`) runs daily at 06:00 UTC and can also be started manually. It checks eligible branches against the upstream repository. For a repository created from the template, it uses the recorded upstream state in `.ghostwriter/update.yml`.

Program files listed under `managed` in `ghostwriter-manifest.yml` are updated, including the shared repository skills `ghostwriter-lektorat` and `ghostwriter-buchgedaechtnis` (and the others listed in the manifest). Since 1.3 the skill `.claude/skills/ghostwriter/` no longer exists (#569): the flow is in `START.md`, and the update removes the old copy from the book. Personal skills remain book-owned. Book files listed under `book`, including manuscript, approvals, costs and the assistant profile, are preserved. Conflicts in other files cause the update to stop for manual resolution. Data migrations update structure where needed; they do not rewrite manuscript text or approvals. A newer book data version than the program supports stops the migration.

The update is validated before it is pushed. If validation fails, the branch is not updated and a failure issue is opened. The workflow retries certain server errors and retries once when the branch advances during the run. Its summary reports what happened for each branch. Books are not downgraded to an older program version.

In a library, the workflow updates the default branch and then each eligible book branch. Working branches are not updated on their own. An open change package (work branch `ghostwriter/<book>` with an open pull request to the book) receives the new book state right after its book is updated, so workflows and checks there run with the new program version (#470). On a conflict the change package stays unchanged and the summary names the files; only a conflicting overview file is regenerated. Work branches without an open pull request are left alone; a dry run only reports. A failure on one book does not stop the others. At the end of every update run, also when started by hand, the workflow looks for leftover background-queue jobs on all work branches (for example after an interrupted research run or a job confirmed later) and starts processing per book ("Recherche" without a section), without any AI call (#481). If automation is paused, nothing starts (the queue does not restart itself either; leftover jobs wait until you nudge it by hand or the pause ends) and the summary reports how many jobs are waiting; a dry run only reports. Starting “GhostWriter aktualisieren” by hand therefore also nudges the queue. Since #479 this covers all four kinds (research, analysis, colorizing, import); “Run workflow” without inputs (analysis without `kind`, colorizing without `folder`, import with `step: queue`) adds no job and only processes the queue. GitHub disables schedules in public repositories after 60 days without activity; then start this run once by hand. The project overview may offer **Update einspielen** (install update) when a newer upstream state is available.

## Update channel: releases only (#604)

From 1.1.0, books and libraries take updates **only from published releases**, no longer from the running `main`. What is merged but not yet released arrives with the next release. The channel is an **Actions variable** of the repository (*Settings → Secrets and variables → Actions → Variables*) that no update overwrites:

| `GHOSTWRITER_UPDATE_CHANNEL` | What the update takes |
|---|---|
| unset or `release` (**default**) | the newest release tag `vX.Y` or `vX.Y.Z` (sorted by version, not by date), without pre-releases |
| `rc` | the newest tag including pre-releases (`vX.Y-rc.N`), for example for acceptance in a test book |
| `main` | as before, the running state (`upstream.ref` in the manifest), for development |

With channel `release` or `rc` the same tag applies to every branch; same-named branches of the upstream repository count only in channel `main`. Starting the workflow manually offers the field `channel` for a one-off exception (“take `rc` once”); empty means the variable. An unknown value stops the run with a message.

**Switching without a step back:** A book that already has a newer `main` state than the latest release (the release commit is in the book and the program version is equal or higher) stays unchanged until a **higher** release appears; the report says “Stand von main (1.0.0+N), wartet auf das nächste Release” (state of main, waiting for the next release). If upstream has no release tag yet, nothing is applied and the report explains how to set channel `main`. The summary of each run names channel, version, tag and the link to the release notes. In the main repository itself, `main` always applies.

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

**1.2.0** adds safety and overview. The notes review can propose deletions (#615). Re-finalizing a changed section is protected against a faulty commit and the update issue names a repair path (#595). Default models of the AI services carry a check date in `providers.yml`; a hint on re-entry and the daily update check name models that are about to be retired or missing (#596). Sections can be marked “stale” without withdrawing their approval; the mark shows in overview, chapter and section, and editions and proofs warn with the list (#510, #592); the action-needed list also shows “Re-check book” and checked-out areas (#593). Proofreading: checked-out areas are locked in the queue, and a dry-run option of the action shows in advance what will happen (#572). Adding material: colorizing runs through `colorize.py` (#574). Reference images are actually handed to the image service, with a capability model and a log (#143). A new analysis kind “glossary terms” for the background run and the chat route: terms only with a cited passage, an explanation only where the text gives it itself, chosen one by one, off by default (#490). The Claude web app is at the v1.2 level (re-finalize, retry, stale marks, review in stages); it is published only after approval (#597). Widgets: ghostwriter-ui 0.69.0. The data version stays 1 (new fields are optional). Open for later versions: parts of #572, #574, #143 and #490 (see the status comments on the issues).

**1.1.2** is a patch for the notes review: a deletion can now be saved as a proposal (#615). `hinweise.py propose … --delete` or `decide … --decision streichen` sets `streichen: true`, the card shows “neu: (entfällt)” (new: removed), `plan` reports the deletion as applicable, and `apply` removes the old wording together with a surplus space before or after it. An empty new wording alone still means “no proposal”. As before your book takes updates only from releases; the data version stays 1 (the new field is optional).

**1.1.1** is a patch for the notes review, which orders findings into themes. The themes of several chapter files come in chapter order (book-wide first, the newest file within a chapter, #606), and minor findings stay in their theme round, collapsed at the end (#607). The single card names stage, theme and progress within the theme (#608). The flow between two answers is shorter (#609): `hinweise.py decide … --next-card` saves and prints the next card, a proposal of the assistant is on the card (`hinweise.py propose`), questions are not saved as a decision (the “Ask a question” button in ghostwriter-ui 0.68.0, `hinweise.py ask`), and the review is saved per completed theme or round (“Zwischenstand speichern”, `hinweise.py checkpoint`). As with 1.1.0 your book takes updates only from releases; the data version stays 1 (new fields are optional).

**1.1.0** adds the notes review in stages (blocking items, themes, equal patterns, rounds of five, “minor” collapsed, #570), one card at a time with progress and selectable variants (#473). AI provider models are set centrally in `providers.yml`, retired models give a clear message, and failed jobs can be retried (#554, #529). A finalized section with changed text can be finalized again (#563). Sections and front/back matter can be marked “outdated”; edition and proof warn about them (#510). The project overview lists what needs attention in the checks, “check the book again”, and “latest checks” only in the extended display (#538). The write check depends on the access instead of a probe push, so the ChatGPT chat can write through the GitHub connector (#579). Checking out an area for proofreading and checking the return back in (#572, #573), adding material (#574). The all-round review also applies proposals for author decisions (#565). General skills are named in one place (#584). **Switch (#604):** from 1.1.0, books and libraries take updates only from published releases instead of the running `main`. To test ahead of a release, set the Actions variable `GHOSTWRITER_UPDATE_CHANNEL` to `rc` (also pre-releases) or `main` (running state); the “GhostWriter aktualisieren” workflow has a `channel` field for one-off exceptions. A book that already has a newer `main` state is not set back and waits for the next release (see “Update channel”). Comes like any update; the data version stays 1 (new fields are optional).

**1.0.0** stops background jobs from getting lost: research, analysis, colorization and import go into one queue per book, which saves result by result, continues itself when needed and is nudged by the daily update run; re-entry and the bookshelf show what has finished (#476). The queue can be viewed in the chat and in the Claude web app, with moving jobs up and cancelling them; research passes on knowledge from earlier runs (#478). Team and roles per book – owner, editor, reader, approver –, commits under your own name, and `validate` rejects finalizing or editions by people without approval rights (#455); personal approval rights also hold for organization accounts (#169). Image research with candidates, source, author and licence; unclear rights are named, and adopting needs confirmation (#218). Costs separated into actual, estimated, manual and unknown; invoices can be recorded (#66). Before writing, the assistant detects changed instructions, program states and work branches; branches are deleted only after everything has been taken over (#179). General skills come from a versioned source, and every assistant loads them from the repository (#532). Claude web app: characters with profile pictures, series characters, notes review with applying into the manuscript, the book's skills as guidance. The notes review finds passages with ellipses and in another section and reports honestly when the wording is missing (#522); the history of check runs stays small in the widget (#497). New command “Book view <book>” opens a book directly by number, short title or title (#562). The page “Clients and capabilities” says per client what is displayed and executed and what is unchecked (#555). New versions are checked with “Prepare release” and published with tag, release and documentation website only after the sentence “Release … freigeben und veröffentlichen” (#488); the website shows the current version again (#530). Arrives like every update; the data version stays 1.

**0.9.0** adds “All settings” with value, origin and form, also for the library, series and omnibus (#299). The update now brings open change packages to the new state (#470). Section dialogue: answers are saved faster (#314), optionally in the background (`answer_backup: hintergrund`, #487). Web research through the configured provider with cost tracking (#462), research with sub-agents (#449), full chapter check (#447), timeline in columns (#450), “Speak as a character” (#464), photo colorization (#452). Open WebUI sends less to the model (#285). Images and workflow pages say “finalize” (#295); text output without HTML leftovers (#498); notes reviews accept own details. Pull request checks are much faster (#485). Arrives like every update; the data version stays 1.

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

## Safe cleanup after accepting changes

The **Branches aufräumen** action deletes a checked work
branch only while its server-side head still matches the confirmed commit.
A commit arriving in the meantime prevents deletion. For version branches, the
matching preservation tag must also remain unchanged; its check and the branch
deletion form one atomic operation.

It uses [GitHub `updateRefs` with `beforeOid`](https://docs.github.com/en/graphql/reference/git#updaterefs).
Missing GraphQL access, insufficient permissions or an uncertain response is not
reported as a successful deletion. There is no unconditional deletion fallback
and no automatic retry. Read the actual remote state before another request.
**Nur anzeigen** (preview only) sends no deletion mutation. Existing checks that
content has been accepted still apply; a matching commit does not grant approval.

## Updating to personal approval verification

An update containing `scripts/approval_authority.py` and the `approval.yml` action preserves existing manuscripts and approval entries. Old names do not automatically become verified identities. Before the next publishable output, a new [personal content evidence record](SAVING.en.md#personal-approval-authority-and-content-evidence) is therefore required for the current book state and edition. Drafts, proofs and previews remain available; published editions are unchanged.

For Open WebUI, install GitHub tool 1.8.0 and configure personal UserValves for writing; the shared tool token becomes read-only. Do not reuse the shared token as a personal login. Revoke previously shared write credentials or replace them with separate personal access; the shared credential only needs read permissions. Do not store tokens in book files. The Claude web app must adopt the verification workflow in Claude. Automated jobs may prepare and check evidence but cannot grant new personal approvals. Practical client acceptance and real organisation permissions remain separate checks.


---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
