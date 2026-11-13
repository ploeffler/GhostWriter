# User guide: from an empty repository to the first edition

[Deutsch](ANLEITUNG.md) · English

This guide follows the German [Anleitung](ANLEITUNG.md). You need a GitHub account and an AI chat assistant, ideally with GitHub access and web research. You do not need to know Git. Say `Interface: English` to request English chat operation. All current views support native English output; some linked documentation remains in German.

Three dedicated pages provide the visual workflows:

- [Book lifecycle](BOOK-LIFECYCLE.en.md): from **New book**, through the repeated chapter circle, to a published edition.
- [Creation cycle](CREATION-CYCLE.en.md): develop a section through research, brainstorming, new input and revision.
- [Saving, merging and approving](SAVING.en.md): book changes, conversation backups, their states and separate confirmations.

**For text-led books, not photo books or picture-led collections:** One scene corresponds to one section, with at most one media item. See [media within a section](MEDIA-LAYOUT.en.md) for planned positions, wrapping and size controls.

## 1. Create a repository

1. Open the [GhostWriter repository](https://github.com/ploeffler/GhostWriter) and select **Use this template → Create a new repository**.
2. Choose a name, such as `my-books`, and select **Private** if the manuscript should not be public. A fork of a public repository is public.
3. Follow [Updates: create a private book repository](UPDATES.en.md#create-a-private-book-repository) to set up updates.

The repository is a library: the default branch holds the program and each book gets its own `buch/<short-title>` branch.

## 2. Connect the chat to GitHub

Connect your assistant to GitHub and restrict access to the intended repository. See [chat apps](CHAT-APPS.en.md) and [connector setup](CONNECTOR-SETUP.en.md). Without a connection the assistant can provide files in the chat for you to transfer yourself.

## 3. Start the first chat

Send the repository URL to a new chat, for example `https://github.com/<you>/my-books`. The assistant reads `START.md`, explains which capabilities it has and shows the bookshelf. Without GitHub access, attach `START.md` or copy its start prompt into the chat.

## 4. Create a book

Choose **New book** (`Neues Buch` in the German form) or enter `New book: <title>`. Enter a working title and, optionally, a short title and author. The form previews the branch name and warns if it is already in use. After creation, the book has its own branch. See [chat views](INTERFACES.en.md) for examples.

## 5. Develop the outline

The assistant asks about subject, goal, audience, book type, language and style. Fixed choices can be presented as cards; open questions remain a conversation. Together you develop chapters and sections, with goals and summaries.

The book structure is created only after you explicitly approve the outline. The assistant also asks whether to apply saved changes immediately in future. Book language and interface language are separate choices.

## 6. Work on the book

The project overview lists chapters, status and costs. Open a chapter to see its sections; open a section to work on it.

Work follows a [creation cycle](CREATION-CYCLE.en.md): introduce new ideas, requirements and material at any time, returning to research, brainstorming or revision as needed. Once its sections are finalized, assemble, review and finalize the chapter. Repeat this [chapter circle](BOOK-LIFECYCLE.en.md) for further chapters.

- **Research:** Research a section or an entire chapter. Results and sources are proposals for your review.
- **Writing:** **Allow writing** before a section is drafted. A **finalized** section is locked: explicitly **reopen** it and allow writing again before editing it.
- **Front and back matter:** Add a dedication, foreword, prologue, epilogue, afterword, glossary or acknowledgements when needed. They are finalized like sections; you write the dedication and acknowledgements yourself. Glossary entries are maintained individually and sorted alphabetically in the book.
- **AI disclosure:** Decide whether and how the book mentions AI assistance. A proposed statement is included only after your confirmation.
- **Output:** Set layout, fonts, spacing, running heads, formats, ISBN and publisher information in output settings. A proof shows the result. Cover options include spine, bleed, back-cover text and barcode; the EPUB uses the front cover.
- **Save and apply:** Changes are collected until you choose to apply them, unless you enabled immediate application.
- **Commands:** `Home`, `Overview`, `Chapter 3`, `Section 3.2`, `New chapter`, `Proof`, `Edition` and `Help` are English chat commands. German commands remain available.

### Save change packages and merge them

Related book changes are saved together in a change package (pull request). A confirmed upload means **saved, not yet merged**; **Apply changes** confirms the current package and merges it into the book version. Immediate application, if deliberately enabled, applies only to ordinary book changes.

For conversation work, use **Save session** (`Session sichern`): messages, research, brainstorming, decisions, drafts and open questions are backed up separately from the manuscript. A completed section discussion also triggers this backup when no reply is pending and all discussed items are resolved or explicitly deferred. This is not continuous background saving.

**Load session** (`Session laden`) reads the backup to resume work. **Merge session backup** (`Session übernehmen`) validates the package, diagnoses failures, attempts safe technical repair, revalidates and merges only after successful checks. It is never auto-merged on save. Neither saving nor merging finalizes a section or chapter. See the [saving diagram and states](SAVING.en.md) and [session backup details](SESSION-BACKUP.en.md).

## 7. Finalize

**Finalize** a section (🔒) when its text is ready; it is then locked, and you **reopen** it to make changes. The confirmation warns about open review markers; unresolved markers prevent inclusion in an edition. Finalize a chapter when every section is finalized and the chapter has been assembled and is ready to finalize. Each finalize and reopen step requires its own confirmation and is recorded. (Earlier versions called this “approve” and “withdraw approval”.)

## 8. Produce a proof

Use **Proof** (`Probedruck`) to create a PDF of the current state for review or sharing. It includes all chapters, highlights open markers and is marked as a proof. It is not an edition and does not change the book's edition number.

It uses the merged book version. Merge pending changes first if you want them included in the proof.

**Reading copy:** When you open a chapter or section, the assistant places its text next to the view as a file, in Claude in the side panel. You can read along while you change and finalize things in the chat; the file is sent again after every change. It also shows text that is not finalized, with its status and highlights open markers. `Lesefassung aus` (reading copy off) turns it off, `Lesefassung an` turns it back on. In ChatGPT and Open WebUI it is created by the "Manuskript ausgeben" action (format `md`) and has to be started again after changes; this path has not been tested in practice yet.

**Export manuscript:** `Export manuscript` (`Manuskript ausgeben`, or `Export manuscript chapter 3` for one chapter) creates a PDF of the working state that you can download directly in the chat. Sections with text appear as in the proof. Sections without text appear as a "Planned" box with the goal and content as bullet points, what has been done (research, brainstorming) and what is still open. The bullet points are taken unchanged from your entries; the AI adds nothing. An overview at the front shows how many sections have text and how many are still planned. If your chat cannot hand over files, you get the download link on GitHub instead (14 days).

## 9. Create the first edition

Once the desired chapters are finalized, open **New edition** (`Neue Auflage`) and provide the name, publication date, formats and release notes. At least one chapter must be finalized; included sections must also be finalized and free of unresolved markers. Merge pending book changes first.

The assistant presents the release notes for approval and prepares a separate edition change package. You explicitly confirm its merge, even if immediate application is enabled. GitHub then builds the files and publishes the release and tag. A failed build is not a finished edition. Published editions remain unchanged; corrections go into a later edition. See the [book lifecycle](BOOK-LIFECYCLE.en.md) for the full path.

## 10. Resume later

- **New chat:** Send the repository URL to return to the bookshelf. A book-branch link opens its project overview; a chapter or section file link opens that location. The saved state remains in the repository.
- **More books:** Create them from the bookshelf.
- **Profile:** `Profil` stores the Git identity used for commits, default author and narrative voice. The generated personal skill can be loaded automatically by compatible assistants; see [chat apps](CHAT-APPS.en.md).
- **Updates:** Program updates are separate from book content; see [updates](UPDATES.en.md).
- **A v0.5 single book:** It can continue as a single book. To manage multiple books in one repository, the [updates guide](UPDATES.en.md#convert-an-existing-single-book-into-a-library) describes the optional conversion.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
