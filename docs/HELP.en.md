# Help: commands and example prompts

[Deutsch](HILFE.md) · English

Enter **Help** in the chat for a short list of commands and shortcuts for the current view. Use **Help changes**, **Help sessions** or **Help commands** to focus on a topic. Help only reads: it does not save, merge or approve anything. The assistant must disclose when tools needed for a command are unavailable.

## Quick command reference

| You enter | Result |
|---|---|
| `Home` or `Library` | Show books |
| `Overview` | Show the current book |
| `Chapter 2` or `Section 2.3` | Open that location |
| `Prepare an external AI dialogue for section 2.3` | Prepare the manual [external dialogue](EXTERNAL-AI-DIALOG.en.md) with assignment, context and open questions |
| `This is the return from Provider A for section 2.3` | Review conversation and result; recommend next steps without automatically saving |
| `New book: My title` | Open the new-book form |
| `New chapter` | Open the new-chapter form |
| `Save session` | Preserve conversation work in a pull request |
| `Session sichern`, `Chat sichern`, `Chat speichern` | German aliases for saving a session |
| `Load session` | Read the backup to resume work; do not merge |
| `Merge session backup` | Check the session package, diagnose errors, attempt safe repair, recheck and merge |
| `Apply changes` | Open confirmation for collected book changes; only explicit confirmation merges the displayed package |
| `Characters` or `Suggest characters` | Show characters or suggest them from the text |
| `Images 2.3` | Manage section images |
| `Output` or `Cover` | Open output options |
| `Proof` | Build a preview; no published edition |
| `Edition` | Open the new-edition form |
| `Text only` | Switch to text views |
| `Simple mode` | Short, plain answers |
| `Extended answers on` | Include technical detail |

## Collect and merge changes

A **pull request** (change package) groups related saved changes. Preparing a package means organizing the results, saving the relevant files and making the package available for review. A session has one saved change per changed coherent topic: research, brainstorming, decisions, drafts, planning and conversation state. Together they form one package per session, not one per message.

**Save session** creates or updates this package. Saving also happens after a completed discussion of open section items. An unanswered question or pending reply prevents that automatic checkpoint; explicitly deferred items are saved. **Load session** reads the backup. **Merge session backup** checks it and merges it into the intended project version. See [session backups](SESSION-BACKUP.en.md) for scope and technical limits.

| Status | Meaning |
|---|---|
| Prepared | Content collected; durable storage not yet confirmed |
| Saved in the repository / package saved | Named content successfully uploaded and confirmed; the package may still be open |
| Checked | The stated checks were performed; merging is not yet confirmed |
| Merged | The checked package was successfully included in the intended project version |
| Approved | A separate explicit decision about text, a chapter, an image or an edition |

A successful save message must follow confirmed upload and name its scope. “Section saved” does not automatically mean “conversation backed up”. A session backup saves conversation work without changing the manuscript. Merging does not grant content approval. Normal book changes may merge immediately if that option was explicitly enabled; session packages still require **Merge session backup**.

## Example prompts

These are ordinary requests, not shortcuts around approvals:

- “Which questions remain open in section 2.3?”
- “Research this question and include sources and uncertainties.”
- “Let’s brainstorm three openings for section 2.3.”
- “Show our decisions, rejected ideas and open questions.”
- “What has been saved, and what exists only in this conversation?”
- “Which changes does this package contain?”
- “Incorporate this material in chapter 2: <new notes or material>.”
- “Review chapter 2 against the research. Analyze only.”

In an open section, **RS** starts immediate research and **GS** starts immediate ghostwriting (writing approval required). **M** opens confirmation for collected changes in the book overview when changes exist. Shortcuts depend on the last displayed view; the full mapping is in [text views and shortcuts](../templates/ui/BEFUELLUNG.md#textfassung-ohne-widgets). See the [user guide](USER-GUIDE.en.md) for the full process.

## Help output in the chat

The assistant reads this help and the current view. For **Help**, show roughly eight to twelve relevant commands with brief effects and mention the topic commands, rather than reproducing this file. **Help commands** shows the command list; **Help changes** explains preparation, saving, checking and merging; **Help sessions** explains saving, the automatic section checkpoint, loading and merging. Give shortcuts only when the view is known. Help can appear without a selected book; do not invent a project state. The German commands remain available; respond in the selected interface language.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
