# User glossary

[Deutsch](BEDIENGLOSSAR.md) · English

[User guide](USER-GUIDE.en.md) · [Help](HELP.en.md) · **User glossary**

This glossary explains the terms you meet while working with GhostWriter. It belongs to the program documentation and is **not your book's glossary**; it never appears in a manuscript, proof or edition. Your book's own glossary is part of [front and back matter](#front-and-back-matter).

The linked guides remain authoritative. Technical identifiers in `code font` are the names used in project files and are not translated. German commands keep working; the German term is given in brackets where the interface may show it.

**A to Z:** [Allow writing](#allow-writing) · [Alt text](#alt-text) · [Approval](#approval) · [Backup gap](#backup-gap) · [Blocked](#blocked) · [Book](#book) · [Book version](#book-version) · [Brainstorming](#brainstorming) · [Caption](#caption) · [Chapter](#chapter) · [Character conversation](#character-conversation) · [Change package](#change-package) · [Checked](#checked) · [Conflict](#conflict) · [Creation cycle](#creation-cycle) · [DOCX](#docx) · [Draft](#draft) · [Edition](#edition) · [EPUB](#epub) · [Fact check](#fact-check) · [Finalize](#finalize) · [Finalized](#finalized) · [Front and back matter](#front-and-back-matter) · [Graphic](#graphic) · [Illustration](#illustration) · [Image approval](#image-approval) · [In progress](#in-progress) · [Library](#library) · [Load session](#load-session) · [Media item](#media-item) · [Media section](#media-section) · [Merge session backup](#merge-session-backup) · [Merged](#merged) · [Outline](#outline) · [PDF](#pdf) · [Placement](#placement) · [Planned](#planned) · [Preview version](#preview-version) · [Proof copy](#proof-copy) · [Publication](#publication) · [Ready to finalize](#ready-to-finalize) · [Reference approval](#reference-approval) · [Reference image](#reference-image) · [Reopen](#reopen) · [Research](#research) · [Review result](#review-result) · [Revision](#revision) · [Save session](#save-session) · [Saved](#saved) · [Scene](#scene) · [Section](#section) · [Session](#session) · [Structure approval](#structure-approval) · [Text wrapping](#text-wrapping) · [Width slider](#width-slider) · [Working version](#working-version)

## Key distinctions

- **Allow writing** is not **finalize**: one permits drafting, the other confirms the finished text.
- **Saved** is not **merged**, and merged is not **finalized**. A passing [review result](#review-result) finalizes nothing.
- **Save session** protects conversation work and does not change the manuscript. **Loading** is not **merging**.
- A **reference image** serves a generation request. That does not make it an illustration in the book.
- A **proof copy** is not an **edition**. A published edition stays unchanged.

## Book structure

- <a id="library"></a>**Library** (Bibliothek): One repository holding several books. The default branch holds the program; each book has its own area (technically the branch `buch/<short-title>`). See the [user guide](USER-GUIDE.en.md#1-create-a-repository).
- <a id="book"></a>**Book** (Buch): A single book project with title, outline, manuscript and editions. A new book starts *in setup*. See [book lifecycle](BOOK-LIFECYCLE.en.md).
- <a id="outline"></a>**Outline** (Gliederung): The book's arrangement into chapters and sections. It is developed in the opening conversation and saved after [structure approval](#structure-approval).
- <a id="chapter"></a>**Chapter** (Kapitel): A group of sections. A chapter is assembled, reviewed as a whole and then [finalized](#finalize).
- <a id="section"></a>**Section** (Abschnitt): The smallest unit of work. Each section goes through the [creation cycle](#creation-cycle) and is finalized on its own.
- <a id="scene"></a>**Scene** (Szene): In GhostWriter one scene equals one section. Another scene gets its own section.
- <a id="front-and-back-matter"></a>**Front and back matter** (Vor- und Nachspann): Parts before chapter 1 or after the last chapter: dedication, foreword, prologue, epilogue, afterword, the book's glossary and acknowledgements. They are finalized like sections. See the [user guide](USER-GUIDE.en.md#6-work-on-the-book).

## Creation

- <a id="creation-cycle"></a>**Creation cycle** (Erstellungskreislauf): The repeatable path along which a section develops: research, brainstorming, draft and revision, until you finalize it. New ideas lead back to the right step. See [creation cycle](CREATION-CYCLE.en.md).
- <a id="research"></a>**Research** (Recherche): Collect sources, evidence, contradictions and open questions for a section (`research`). Earlier research runs are kept.
- <a id="brainstorming"></a>**Brainstorming**: Discuss ideas, variants and requirements with the assistant (`brainstorming`).
- <a id="character-conversation"></a>**Character conversation** (Figurengespräch): A chat conversation in which the assistant answers in the role of a character (`Talk to <Name>`). It saves nothing; new details go into the character profile only if you select them, never into the manuscript. See [user guide](USER-GUIDE.en.md#6-work-on-the-book).
- <a id="draft"></a>**Draft** (Entwurf): The first text of a section. It is written only after you [allow writing](#allow-writing) (`writing`).
- <a id="revision"></a>**Revision** (Überarbeitung): The draft is improved with you and reviewed as a whole (`revision`). A reopened section returns here.
- <a id="fact-check"></a>**Fact check** (Faktenprüfung): On request, a report with suggested corrections (`fact_check`). It does not change the text by itself.
- <a id="review-result"></a>**Review result** (Prüfergebnis): Outcome of an editorial review: *passed*, *passed with notes* or *failed*. Even a pass finalizes nothing. See [quality assurance](QUALITY-ASSURANCE.en.md#review-result).

## States, finalizing and approvals

Since #292 confirming finished text is called **finalize**, undoing it **reopen**. In the interface, **approval** is now used only for images, omnibus editions, editions and the structure. Project files keep their technical names (`approved`, `approvals.yml`).

- <a id="planned"></a>**Planned** (geplant): Initial state of a chapter or section (`planned`). Goal, questions and material are clarified.
- <a id="in-progress"></a>**In progress** (in Bearbeitung): A chapter whose sections are being worked on (`in_progress`). Assembly and review follow. See [book lifecycle](BOOK-LIFECYCLE.en.md#repeat-the-chapter-cycle).
- <a id="allow-writing"></a>**Allow writing / lock writing** (Schreiben erlauben / sperren): Your explicit permission for the assistant to write or change a section's text (formerly “writing approval”). It does not finalize the section.
- <a id="ready-to-finalize"></a>**Ready to finalize** (bereit zum Abschluss): The version awaits your finalization (`ready_for_approval`), for sections and chapters alike.
- <a id="finalize"></a>**Finalize** (abschließen): Your explicit confirmation of an exact text version: **finalize section** or **finalize chapter** (formerly “section approval” or “chapter approval”). Saving, merging or a check never replaces it. Open markers are shown as a warning.
- <a id="finalized"></a>**Finalized** (abgeschlossen): State after finalizing (`approved`). The text is locked until you reopen it.
- <a id="reopen"></a>**Reopen** (wieder öffnen): Undoes a finalization (formerly “revoking approval”). The section returns to revision; allow writing again before the next draft.
- <a id="structure-approval"></a>**Structure approval** (Strukturfreigabe): Your confirmation of a new book's complete outline. Only then are the remaining book files created.
- <a id="image-approval"></a>**Image approval** (Bildfreigabe): Your decision that an image may appear in the book. Only approved images go into an edition; the proof copy shows all of them with a note.
- <a id="approval"></a>**Approval** (Freigabe): In the interface, a separate explicit decision about the structure, an image, a [reference image](#reference-approval), an omnibus or an edition. For text, the term is [finalize](#finalize).

## Saving and merging

These terms describe storage status. They are not section or chapter states. See [saving, merging and approving](SAVING.en.md#distinguish-the-states).

- <a id="working-version"></a>**Working version** (Arbeitsstand): The current state including all saved changes, also those not yet merged. Views read it from the open change package.
- <a id="book-version"></a>**Book version** (Buchstand): The merged state of the book. Proof copies and editions are built from it.
- <a id="change-package"></a>**Change package** (Änderungspaket): A bundle of related saved changes (technically a pull request). It can contain several change steps (commits). See [help](HELP.en.md#collect-and-merge-changes).
- <a id="saved"></a>**Saved, not yet merged** (gespeichert, noch nicht übernommen): The upload to the repository is confirmed; the change package is still open. For conversations the term is *backed up*.
- <a id="checked"></a>**Checked** (geprüft): The named technical checks have run. A merge is not yet guaranteed.
- <a id="merged"></a>**Merged** (übernommen): The change package is in the book version after your confirmation. With *merge immediately* (`changes.auto_merge`) this happens automatically for ordinary book changes, never for session backups or editions.
- <a id="blocked"></a>**Blocked** (blockiert): An operation failed or awaits clarification. The assistant reports what is actually saved and the next step.
- <a id="conflict"></a>**Conflict** (Konflikt): Affected files were changed differently in the meantime. They are reconciled before writing; a conflict is never bypassed.

## Conversation work

- <a id="session"></a>**Session**: A conversation with the assistant that has a fixed ID. Its backup is kept separate from the manuscript.
- <a id="save-session"></a>**Save session** (Session sichern): Durably records the accessible conversation work: messages, research, brainstorming, decisions, drafts and open points. This happens automatically after each evaluated answer in a section question round. See [session backup](SESSION-BACKUP.en.md).
- <a id="load-session"></a>**Load session** (Session laden): Reads a backup to continue working. Loading saves and merges nothing.
- <a id="merge-session-backup"></a>**Merge session backup** (Session übernehmen): Checks the backup, attempts a safe repair on errors and merges it. Manuscript and finalizations stay unchanged.
- <a id="backup-gap"></a>**Backup gap** (Sicherungslücke): Part of a conversation that could not be backed up, such as earlier messages or attachments that were no longer accessible. Gaps are reported explicitly, never hidden.

## Images and graphics

**GhostWriter is meant for text-centred books, not photo books or picture books.** See [media in sections](MEDIA-LAYOUT.en.md) and [images and visual references](IMAGES-AND-REFERENCES.en.md).

- <a id="media-item"></a>**Media item** (Medium): An image or graphic in a section. A section holds at most one media item; the same image inserted twice counts as two.
- <a id="illustration"></a>**Illustration**: An image for the book, usually without lettering.
- <a id="graphic"></a>**Graphic** (Grafik): A diagram or figure where labels are wanted.
- <a id="reference-image"></a>**Reference image** (Referenzbild): An image used as a model for a generation request, for example a character's or place's appearance. It is not a book illustration unless it is separately used and approved as one.
- <a id="reference-approval"></a>**Reference approval** (Referenzfreigabe): Your decision that a reference image may be offered for suitable requests. You choose explicitly each time which references a request uses. An upload alone is never an approval.
- <a id="media-section"></a>**Media section** (Medienabschnitt): A section of its own that contains only an image or graphic, directly before or after a text section.
- <a id="caption"></a>**Caption** (Bildunterschrift): The visible text below the media item.
- <a id="alt-text"></a>**Alt text** (Alternativtext): A description of the image for screen readers. If it differs from the caption, DOCX and EPUB carry it separately.
- <a id="placement"></a>**Placement** (Platzierung): Position of the media item in the section: top or bottom, each left, centre or right (six options). Implemented (#54); practical checks in all formats are still open.
- <a id="text-wrapping"></a>**Text wrapping** (Textumfluss): Text flows around media placed left or right, not around centred ones. Implemented for PDF, EPUB and DOCX (#54); practical checks still open.
- <a id="width-slider"></a>**Width slider** (Breitenregler): A slider with a percentage display for the media item's width as a share of the usable page width (10–100 %); the height follows. Implemented (#54). It does not change the original file.

## Output

- <a id="proof-copy"></a>**Proof copy** (Probedruck): A marked PDF of the merged book version, available at any time, also with unfinished text. It publishes nothing and finalizes nothing.
- <a id="preview-version"></a>**Preview version** (Vorabfassung): A proof copy kept permanently as “Vorabfassung N”, for test readers for example. Not an edition.
- <a id="edition"></a>**Edition** (Auflage): A published version of the book. It needs at least one finalized chapter, no open markers and your explicit confirmation. A published edition stays unchanged; corrections go into a later edition. See [book lifecycle](BOOK-LIFECYCLE.en.md#leave-the-chapter-circle-to-publish-an-edition).
- <a id="publication"></a>**Publication** (Veröffentlichung): The step in which GitHub builds the output files of a confirmed edition and stores them as a release. A running or failed build is not yet an edition.
- <a id="pdf"></a>**PDF**: Output for reading on screen or for print.
- <a id="docx"></a>**DOCX** (Word file): Output for further editing in Word or LibreOffice.
- <a id="epub"></a>**EPUB** (e-book): Output for e-readers with reflowable text.

## Technical terms when reading the documentation

You do not need them to operate GhostWriter. **Branch:** a separate area, for example for one book. **Commit:** one change step. **Pull request (PR):** a [change package](#change-package). **Merge:** [merging](#merged). **Tag:** a permanent marker of a version, for example an edition.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
