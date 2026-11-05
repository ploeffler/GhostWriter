# User guide: from an empty repository to the first edition

This guide follows the German [Anleitung](ANLEITUNG.md). You need a GitHub account and an AI chat assistant, ideally with GitHub access and web research. You do not need to know Git. Say `Interface: English` to request English chat operation. The graphical templates and some linked material are still in German.

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

- **Research:** Research a section or an entire chapter. Results and sources are proposals for your review.
- **Writing:** Approve writing before a section is drafted. You can edit its text yourself.
- **Front and back matter:** Add a dedication, foreword, prologue, epilogue, afterword, glossary or acknowledgements when needed. They are approved like sections; you write the dedication and acknowledgements yourself. Glossary entries are maintained individually and sorted alphabetically in the book.
- **AI disclosure:** Decide whether and how the book mentions AI assistance. A proposed statement is included only after your confirmation.
- **Output:** Set layout, fonts, spacing, running heads, formats, ISBN and publisher information in output settings. A proof shows the result. Cover options include spine, bleed, back-cover text and barcode; the EPUB uses the front cover.
- **Save and apply:** Changes are collected until you choose to apply them, unless you enabled immediate application.
- **Commands:** `Home`, `Overview`, `Chapter 3`, `Section 3.2`, `New chapter`, `Proof`, `Edition` and `Help` are English chat commands. German commands remain available.

## 7. Approve

Approve a section when its text is ready. The confirmation warns about open review markers; unresolved markers prevent inclusion in an edition. Approve a chapter when every section is approved and the chapter has been assembled and is ready for approval. Each approval requires its own confirmation and is recorded; it can also be revoked.

## 8. Produce a proof

Use **Proof** (`Probedruck`) to create a PDF of the current state for review or sharing. It includes all chapters, highlights open markers and is marked as a proof. It is not an edition and does not change the book's edition number.

## 9. Create the first edition

Once the desired chapters are approved, open **New edition** (`Neue Auflage`) and provide the name, publication date, formats and release notes. After your confirmation, GitHub builds a release with the chosen PDF, Word and e-book files. Published editions remain unchanged; corrections go into a later edition.

## 10. Resume later

- **New chat:** Send the repository URL to return to the bookshelf. A book-branch link opens its project overview; a chapter or section file link opens that location. The saved state remains in the repository.
- **More books:** Create them from the bookshelf.
- **Profile:** `Profil` stores the Git identity used for commits, default author and narrative voice. The generated personal skill can be loaded automatically by compatible assistants; see [chat apps](CHAT-APPS.en.md).
- **Updates:** Program updates are separate from book content; see [updates](UPDATES.en.md).
- **A v0.5 single book:** It can continue as a single book. To manage multiple books in one repository, the [updates guide](UPDATES.en.md#convert-an-existing-single-book-into-a-library) describes the optional conversion.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
