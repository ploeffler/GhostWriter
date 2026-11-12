# Troubleshooting

[Deutsch](PROBLEME.md) · English

## The assistant cannot read the repository

Check your chat app’s GitHub connection and access to the correct repository. A link alone does not load files. Without a connection, attach START.md and transfer files yourself. See [chat apps](CHAT-APPS.en.md) and [connector setup](CONNECTOR-SETUP.en.md). Never share access keys in the chat.

## The view does not appear or cannot be used

Enter **Text only**. ChatGPT and other clients can use native text views; widget support varies. Use **Overview**, **Chapter 2** or **Section 2.3** to open the relevant place. [Help](HELP.en.md) explains more commands.

## My change is missing

Ask: “What has been saved, and what exists only in this conversation?” An open pull request is saved but has not been merged. **Load session** reads conversation backups; **Merge session backup** checks and merges that backup’s pull request. Book changes have their own merge step. See [saving](SAVING.en.md) and [conversation backups](SESSION-BACKUP.en.md).

## Saving reports a newer version or an error

Do not blindly overwrite or retry. Ask the assistant to read the current version, compare the differences and reconcile the intended change. A success message requires confirmed storage. The assistant must disclose missing tools or permissions.

## Writing or an edition is blocked

Writing requires writing approval. Approved text must have its approval explicitly revoked and writing approved again before changes. An edition requires the relevant chapter and section approvals and resolved open markers. Ask for the specific blocker; request a **Proof** for reading. See the [user guide](USER-GUIDE.en.md).

## The bookshelf or overview stays outdated

Before that, the issue **“GhostWriter: Actions-Minuten knapp”** warns you (below 300 minutes or 20% left).

If every run under **Actions** says “The job was not started because recent account payments have failed or your spending limit needs to be increased”, the month's Actions minutes are used up (2,000 for private repositories). Saving still works, but bookshelf, overview file, checks and editions resume only next month or after setting a spending limit in GitHub. Then run *Bücherregal aktualisieren* once by hand. See [updates](UPDATES.en.md).

## Checks, overview or bookshelf do not start

If these runs show as *skipped* under **Actions** and the repository variable `GHOSTWRITER_ACTIONS_PAUSED` is `true`, automation is paused because Actions minutes are low (issue “GhostWriter: Actions-Minuten knapp”). It resumes by itself next month; manual runs always work. To lift the pause earlier, delete the variable under *Settings → Secrets and variables → Actions*. See [updates](UPDATES.en.md).

## An image does not use my reference

Storing a reference does not confirm that it was passed to an image service. The assistant must separately attach selected files to a service that supports references, or disclose the limitation. See [images and references](IMAGES-AND-REFERENCES.en.md).

## The problem persists

Record the command, error, client and program version (**Data**). Report program errors in the main repository without exposing private book text, chats or keys. Search for an existing report first. See [updates](UPDATES.en.md) for update status.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
