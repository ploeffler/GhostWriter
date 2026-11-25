# Help: commands and example prompts

[Deutsch](HILFE.md) · English

Enter **Help** in the chat for a short list of commands and shortcuts for the current view. Use **Help changes**, **Help sessions** or **Help commands** to focus on a topic. Help only reads: it does not save, merge or approve anything. The assistant must disclose when tools needed for a command are unavailable. The [user glossary](USER-GLOSSARY.en.md) explains the terms.

## Quick command reference

| You enter | Result |
|---|---|
| `Home` or `Library` | Show books |
| `Overview` | Show the current book |
| `Book view <book>` | Overview of a specific book, found by number, short title or title |
| `Chapter 2` or `Section 2.3` | Open that location |
| `New book: My title` | Open the new-book form |
| `New chapter` | Open the new-chapter form |
| `Sicherung erstellen` | Full backup of the repository as a ZIP file: reading version, complete Git, GitHub settings without secret values ([Full backup](FULL-BACKUP.en.md)) |
| `Save session` | Preserve conversation work in a pull request |
| `Session sichern`, `Chat sichern`, `Chat speichern` | German aliases for saving a session |
| `Load session` | Read the backup to resume work; do not merge |
| `Merge session backup` | Check the session package, diagnose errors, attempt safe repair, recheck and merge |
| `Apply changes` | Open confirmation for collected book changes; only explicit confirmation merges the displayed package |
| `Characters` or `Suggest characters` | Show characters or suggest them from the text |
| `Talk to <Name>`, `End conversation` | Talk to a character in the chat; nothing is saved, new details go into the character profile only if you select them |
| `Speak as <Name>` | The other way round: you or the person themselves speak as the character, the assistant answers from book knowledge, research or both; only what you select afterwards is saved |
| `Timeline` (`Zeitleiste`) | Chronology from notes and research, with hints where dates do not fit together |
| `Images 2.3` | Manage section images |
| `Output` or `Cover` | Open output options |
| `Check out chapters 3–5` or `Check out book` | Lock an area for proofreading and provide DOCX and PDF with a QR code (shortcut `AC`) |
| `Check in` | Assign the proofreader's return (DOCX, PDF or photo of the printouts) and add it as findings (shortcut `EC`); the checkout stays |
| `End checkout`, `Checkouts` | Lift the lock after confirmation (shortcut `CB`) or list all checkouts |
| `Add material` | Store, prepare and mark a photo, document or return for the book (shortcut `ME`); also starts on an upload |
| `Proof` | Build a preview; no published edition |
| `Preview version` (`Vorabfassung`) | Keep the current state as a pre-release (tag and release, after confirmation); no edition |
| `Export manuscript` | PDF of the working state to download; planned content as bullet points |
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
| [Finalized](USER-GLOSSARY.en.md#finalized) | A separate explicit decision that a section, part or chapter is done; its text is then locked until you reopen it (formerly “approved”) |
| Approved | A separate explicit decision about an image, an omnibus or an edition |
| Writing allowed | The assistant may write or change this section's text |

A successful save message must follow confirmed upload and name its scope. “Section saved” does not automatically mean “conversation backed up”. A session backup saves conversation work without changing the manuscript. Merging does not grant content approval. Normal book changes may merge immediately if that option was explicitly enabled; session packages still require **Merge session backup**.

## Reconcile story memory

“Reconcile chapter 3 with our story memory” requests a
[read-only fact and continuity comparison](STORY-MEMORY.en.md).
“What facts changed in section 2.3?” requires an identified comparison version.
Book references and manuscript remain unchanged.

## Request an editorial review

- “Structural review of chapter 3.”
- “Language review of section 2.3.”
- “Proofread chapter 4.”
- “Full check of chapter 3.”

The [three review types](EDITORIAL-REVIEW.en.md) initially provide findings in
chat; they do not change the manuscript or grant approval. The full chapter
check (“Full check of chapter 3”) combines them and applies what needs no author or has a
clear proposal.

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

In an open section, **RS** starts immediate research and **GS** starts immediate ghostwriting (writing must be allowed). **M** opens confirmation for collected changes in the book overview when changes exist. Shortcuts depend on the last displayed view; the full mapping is in [text views and shortcuts](../templates/ui/BEFUELLUNG.md#textfassung-ohne-widgets). See the [user guide](USER-GUIDE.en.md) for the full process.

## Help output in the chat

The assistant reads this help and the current view. For **Help**, show roughly eight to twelve relevant commands with brief effects and mention the topic commands, rather than reproducing this file. **Help commands** shows the command list; **Help changes** explains preparation, saving, checking and merging; **Help sessions** explains saving, the automatic section checkpoint, loading and merging. Give shortcuts only when the view is known. Help can appear without a selected book; do not invent a project state. The German commands remain available; respond in the selected interface language.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
