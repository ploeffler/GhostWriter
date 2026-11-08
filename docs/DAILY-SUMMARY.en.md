# Daily GitHub report

[Deutsch](DAILY-SUMMARY.md) · English

The existing **GhostWriter aktualisieren** (Update GhostWriter) workflow adds a report covering the last 24 hours to its Actions summary. The scheduled run also delivers at most one complete report per UTC day as a comment in a dedicated issue. No SMTP service or additional secrets are needed.

## Book content

For each recognised book branch, the report counts content commits and distinct changed content files under `chapters/`, `matter/`, `cover/`, `characters/`, `story/` and `research/`, provided those paths are listed as book content in the manifest.

Program files, update metadata, configuration changes and changes limited to status or approvals do not count. Administrative fields in section frontmatter, status columns in chapter overviews and the chapter status section are excluded before comparison. Changes to manuscript text, paragraph breaks and substantive overview information still count. Books without content changes are omitted. Missing branch data is reported as unknown.

## Pull requests and decisions

The report lists pull requests updated during the last 24 hours in the main repository specified by `upstream.repo`. It also lists older open pull requests with pending reviews, requested changes, merge conflicts or checks needing attention. Unknown states remain unknown. A merge decision never grants approval automatically.

Titles, branch names and user content are preserved in their original language.

## Update status

The report shows the current update step result and any limit pause. A manual run that proceeds despite a pause is marked with a warning. Open update-failure or pause issues and failed or cancelled update runs from the last 24 hours are linked from the current book repository. Missing API data is explicitly marked as unavailable.

## Receive the daily report

The first delivery creates **GhostWriter: daily update report** in the current repository. Each daily comment contains both the branch update results and the daily report, mentions the recipient and links to the workflow run. Existing report issues are identified by a stable hidden marker, so changing the interface language or issue title does not create another issue.

The recipient defaults to the scheduled workflow's GitHub actor (`github.actor`). Set the repository variable `GHOSTWRITER_REPORT_RECIPIENT` to a GitHub username to use a fixed recipient. For an organisation-owned repository, choose a user rather than the organisation name.

The recipient enables email notifications for mentions or subscribed conversations in their personal GitHub settings and can **Subscribe** to the report issue. GitHub handles delivery according to those settings; GhostWriter cannot force email when notifications are disabled. Other subscribers may also receive notifications. The initial issue creation may cause an additional notification to repository watchers.

Repeated runs on the same UTC day do not add or edit a comment. The existing workflow concurrency lock prevents parallel deliveries. Closing the report issue pauses delivery; reopening it resumes delivery. Preserve the hidden marker in the issue body.

Manual update runs do not send a report by default. Select **Vollständigen Tagesbericht als Issue-Kommentar zustellen** (Deliver the complete daily report as an issue comment) to request delivery manually. The daily limit still applies. Dry runs never deliver a report.

Delivery failures do not affect the update result and appear in the Actions summary. Reports exceeding GitHub's comment size limit remain available in the Actions summary; they are neither truncated nor split into multiple comments. The workflow uses its existing `issues: write` permission.

For fewer emails, restrict normal Actions notifications to failures and reduce other unwanted repository subscriptions. GhostWriter does not change personal GitHub settings.

## Report language

The report supports German and English. Set the repository variable `GHOSTWRITER_INTERFACE_LANGUAGE` to `en` for scheduled runs. Without this override, the optional book setting `interface.language` takes precedence over `assistant.yml: interface_language` from the default branch; the fallback is German. The manuscript language (`project.language`) does not select the interface language. Language variants such as `en-GB` use their supported base language; unsupported languages fall back to German.

For a local preview, use `python scripts/daily_summary.py --language en`. A preview does not send comments unless delivery is explicitly enabled by its workflow environment.

This first localisation step covers daily report headings, labels, decisions and delivery messages. Original branch update details and limit descriptions are still produced by the existing update and limit scripts and may remain German. Graphical templates and generated chat views will be migrated separately; this is not yet a fully translated interface.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
