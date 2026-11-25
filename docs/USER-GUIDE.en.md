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

The project overview lists chapters, status and costs (AI API calls only; “≈” means estimated; `python3 scripts/costs.py . summary` breaks them down into actual, estimated, manual and unknown, and `costs.py . add` records an invoice amount; `costs.py . summary --by month|provider|activity|chapter|section` groups them by month, service, task, chapter or section; estimates arise automatically per call from the price table in `providers.yml` and are converted into your currency with the ECB reference rate of the day, the original amount stays on the entry). Open a chapter to see its sections; open a section to work on it.

Work follows a [creation cycle](CREATION-CYCLE.en.md): introduce new ideas, requirements and material at any time, returning to research, brainstorming or revision as needed. Once its sections are finalized, assemble, review and finalize the chapter. Repeat this [chapter circle](BOOK-LIFECYCLE.en.md) for further chapters.

- **Research:** Research a section or an entire chapter. Results and sources are proposals for your review.
- **Character conversation:** With `Talk to <Name>` (German `Figurengespräch <Name>`) you talk to one of your characters in the chat. The assistant answers in their role, with the voice, traits and relationships from the character profile. Anything beyond the profile and the text is invented and not book knowledge. Nothing is saved during the conversation. `End conversation` makes the assistant step out of the role and show what was new, such as a trait or a piece of backstory; only what you select goes into the character profile, nothing into the manuscript. The character knows the current state of the book; an exact limit to a point in the book is planned (#430), a dedicated conversation view for v1.5 (#431).
- **Speak as a character:** `Speak as <Name>` (German `Als <Name> sprechen`) works the other way round: you speak as the character, and the assistant answers as a conversation partner. For biographies and family books the person themselves can also sit down and tell their story, for example a parent who has never got on with computers. First you choose what the assistant answers from: **book knowledge only**, **research/background only** (with sources) or **book + research**. Short form: `Speak as Vilmos: book + research`. If the person speaks themselves, the assistant first asks you whether they agree that what they say goes into the book project, and whether to save quietly after every answer. Ideally switch on the chat app's voice mode. The person then sees only the conversation: no commands, no technical terms, no messages. Anything that does not match the book is not corrected; at most the assistant asks a friendly question. After the end (`End conversation` or “thanks, that's enough”) you get the evaluation: save the conversation, new details for the character profile, chronology entries (evidence status “reported”, with the conversation as source) and the contradictions. Only what you select is saved, nothing goes into the manuscript.
- **Timeline:** `Zeitleiste` shows your book’s chronology: what happened when, with source and evidence status (documented, reported, uncertain, creative licence), even before there is text. The assistant suggests entries from characters, places, research and saved conversations; only what you select is saved. At the top it lists where dates do not fit together, such as two dates for the same event or overlapping life stages. The chart shows one lane per character with life stages and events on a shared time axis, colour for the place and shape for the evidence status; use “from” and “to” or click a year to look closer at a busy period. The project overview has a button for it. If you link a passage of the text timeline to an entry, GhostWriter reports when the year or chapter in the text does not match. The “chronology” analysis reads your notes (characters, places, sources, research, your own messages in saved conversations), never the manuscript, and suggests entries with a quotation; a date only when it is stated, “documented” only from sources and research. For a novel without a calendar year, the chronology counts days from a reference day (“Day −3”, “Day 0, 06:42”) without inventing a year; GhostWriter can read an existing table in `story/chronologie.md` as suggestions. To print or share it, run the action “Zeitleiste ausgeben”: it saves the timeline as HTML, PDF and PNG under `story/`; it never goes into the book.
- **Writing:** **Allow writing** before a section is drafted. A **finalized** section is locked: explicitly **reopen** it and allow writing again before editing it.
- **Front and back matter:** Add a dedication, foreword, prologue, epilogue, afterword, glossary or acknowledgements when needed. They are finalized like sections; you write the dedication and acknowledgements yourself. Glossary entries are maintained individually and sorted alphabetically in the book.
- **AI disclosure:** Every book contains a minimum statement: “Functions of an AI were used in creating this book, for example for spelling, grammar, punctuation and source research. *Author* has reviewed all content and is responsible for the text.” (in German books in German). It needs no confirmation and cannot be switched off; you can adjust the list. Anything beyond that is your decision; a proposed addition is included only after your confirmation. It always comes with the mandatory “AI assisted” badge (“KI-unterstützt” for German books) as a small logo next to the statement, in every format; it cannot be turned off.
- **Output:** Set layout, fonts, spacing, running heads, formats, ISBN and publisher information in output settings. A proof shows the result. Cover options include spine, bleed, back-cover text and barcode; the EPUB uses the front cover. Proofs show the front cover as the first page; editions can too (setting “Front cover in the PDF”). For home printing, choose the **Booklet** format: the PDF arranges the pages so you print the sheets double-sided (flip on short edge), stack them and fold them in the middle – with page size A5, A4 sheets become an A5 booklet. No booklet feature in the printer driver is needed.
- **Save and apply:** Changes are collected until you choose to apply them, unless you enabled immediate application.
- **Commands:** `Home`, `Overview`, `Chapter 3`, `Section 3.2`, `New chapter`, `Proof`, `Edition` and `Help` are English chat commands. German commands remain available. Terms are explained in the [user glossary](USER-GLOSSARY.en.md).

### Save change packages and merge them

Related book changes are saved together in a change package (pull request). A confirmed upload means **saved, not yet merged**; **Apply changes** confirms the current package and merges it into the book version. Immediate application, if deliberately enabled, applies only to ordinary book changes.

For conversation work, use **Save session** (`Session sichern`): messages, research, brainstorming, decisions, drafts and open questions are backed up separately from the manuscript. A completed section discussion also triggers this backup when no reply is pending and all discussed items are resolved or explicitly deferred. This is not continuous background saving.

**Load session** (`Session laden`) reads the backup to resume work. **Merge session backup** (`Session übernehmen`) validates the package, diagnoses failures, attempts safe technical repair, revalidates and merges only after successful checks. It is never auto-merged on save. Neither saving nor merging finalizes a section or chapter. See the [saving diagram and states](SAVING.en.md) and [session backup details](SESSION-BACKUP.en.md).

## 7. Finalize

**Finalize** a section (🔒) when its text is ready; it is then locked, and you **reopen** it to make changes. The confirmation warns about open review markers; unresolved markers prevent inclusion in an edition. Finalize a chapter when every section is finalized and the chapter has been assembled and is ready to finalize. Each finalize and reopen step requires its own confirmation and is recorded. (Earlier versions called this “approve” and “withdraw approval”.)

## 8. Produce a proof

Use **Proof** (`Probedruck`) to create a PDF of the current state for review or sharing. It includes all chapters, highlights open markers and is marked as a proof. It is not an edition and does not change the book's edition number.

The proof note appears on every page in its own red line below the page number, and on the title page. Choose its look on the title page under **Proof marking** in the output settings: a red line, a red box with date and version, or an additional “PROBEDRUCK” watermark on the title page or on every page. **Title page design** offers “with rules”, “modern”, “letter-spaced” and “with band” besides “classic”. In the form a small preview image under each choice shows the title page or the marking; in the text view use `Title page design: with rules`. The design applies to PDF, EPUB and DOCX: in the EPUB the title page takes over alignment, font, rules or band, but title, subtitle and author always keep this order, and the reading device may override some of it. In the DOCX, title, subtitle and author get alignment, font, rules or band; there is no separate title page with a page break. The proof marking (box, watermark) exists only in the PDF.

It uses the merged book version. Merge pending changes first if you want them included in the proof.

**Preview version:** When a state is worth keeping (for test readers, say) but is not yet the edition, say `Vorabfassung`. It is built like a proof but marked “Vorabfassung 1” (2, 3 …) and stays in the repository as a pre-release with its own tag instead of disappearing after 14 days. The edition number does not change; preview numbers keep counting across editions. The assistant asks before creating it, since a tag and a release are created. The “New edition” form also has a “Vorabfassung” (preview version) button next to “Proof”: the first click shows which tag will be created, only the second one creates it. Afterwards the project overview shows the latest preview version with its date and a link to the release next to the edition.

**Reading copy:** Opening a chapter or section supplies a Markdown file alongside the chat view, including in ChatGPT Work and Codex using available file tools. Codex uses its file panel; a queued display request does not confirm an open view. The complete text is not duplicated in the chat. Refresh the same file after edits, including unsaved proposals, which are labelled separately and grant no approval. `Lesefassung aus/an` applies to this chat only, independently of “Display: extended”. If preview is unavailable, offer the file or a link and explain the limitation. Without script execution, the “Manuskript ausgeben” action (format `md`) remains the fallback for saved work. See [chat apps](CHAT-APPS.en.md#reading-copy-next-to-the-view-289).

**Export manuscript:** `Export manuscript` (`Manuskript ausgeben`, or `Export manuscript chapter 3` for one chapter) creates a PDF of the working state that you can download directly in the chat. Sections with text appear as in the proof. Sections without text appear as a "Planned" box with the goal and content as bullet points, what has been done (research, brainstorming) and what is still open. The bullet points are taken unchanged from your entries; the AI adds nothing. An overview at the front shows how many sections have text and how many are still planned. If your chat cannot hand over files, you get the download link on GitHub instead (14 days).

## 9. Create the first edition

Once the desired chapters are finalized, open **New edition** (`Neue Auflage`) and provide the name, publication date, formats and release notes. At least one chapter must be finalized; included sections must also be finalized and free of unresolved markers. Merge pending book changes first.

The assistant presents the release notes for approval and prepares a separate edition change package. You explicitly confirm its merge, even if immediate application is enabled. GitHub then builds the files and publishes the release and tag. A failed build is not a finished edition. Published editions remain unchanged; corrections go into a later edition. See the [book lifecycle](BOOK-LIFECYCLE.en.md) for the full path.

## 10. Resume later

- **New chat:** Send the repository URL to return to the bookshelf. A book-branch link opens its project overview; a chapter or section file link opens that location. The saved state remains in the repository.
- **More books:** Create them from the bookshelf.
- **Profile:** `Profil` stores the Git identity used for commits, default author and narrative voice. The generated personal skill can be loaded automatically by compatible assistants; see [chat apps](CHAT-APPS.en.md).
- **Updates:** Program updates are separate from book content; see [updates](UPDATES.en.md).
- **Working with others (#455):** Invite people as GitHub collaborators (repository → Settings → Collaborators; readers with “Read”, editors with “Write”). In `ghostwriter.yml` under `team`, set who is owner, editor or reader and which editor may finalize (`approve: true`); with `name` and `email` a person's commits appear under their own name instead of yours. The assistant tells everyone their role and only offers permitted actions. GitHub permissions remain the real limit: anyone with “Write” can also change files directly. To rule that out, add a rule with required review (Settings → Rules). The check on the change package rejects finalizing and editions by people without approval rights, and changes to the team list by anyone but an owner. The team list before the change counts, and the check looks at who opened the pull request or pushed.
- **A v0.5 single book:** It can continue as a single book. To manage multiple books in one repository, the [updates guide](UPDATES.en.md#convert-an-existing-single-book-into-a-library) describes the optional conversion.

## Design graphic covers

Ask in chat, for example: “Use the cream color at the top of the cover image for the spine and back. Place the title, subtitle and author in the free upper area.” The assistant shows the hex color, affected panels and proposed settings. Check a preview with the current book text, then explicitly ask to save the settings for this book. Analysis and preview alone save nothing. Text areas are adjusted numerically in chat; a graphical drag editor is not included.

Title, subtitle and author remain linked to project metadata. Each text part supports position, width, maximum height, alignment, font size, serif/sans font, bold, color, wrapping and visibility. Coordinates are millimeters from the top left trim edge of the front cover; font sizes are points. A 10 mm safety margin applies. Uncustomized parts keep the selected template. Existing `classic`, `modern` and `plain` covers work without new settings.

Choose a color from an original-image location or suggested colors including image corners. Location coordinates range from 0 to 1 from the top left, **before automatic cropping**. The visible hex value can be corrected. Set colors per panel without changing other panel colors. Transparent areas are composited over white for color sampling.

**Already lettered image:** Select `image_mode: finished` to suppress additional front-cover text. Spine and back remain separately typeset. `motif` is the default for unlettered artwork. The original image is preserved in both modes. Existing lettering is not detected automatically.

**Back-cover blurb:** `back_blurb_position` places the blurb at the top (`top`, default), in the middle (`middle`) or at the bottom (`bottom`). At the bottom it ends 8 mm above the author bio and author image; barcode and price stay at the bottom right. For example: “Move the blurb on the back cover to the bottom.” A very long blurb placed at the bottom can reach the top margin, so check the preview.

**Finished front cover as a file** (#324): If the front cover is already designed, for example `cover/vorderseite.pdf`, enter it as `cover.front` (PDF, JPG or PNG in the book format, bleed allowed). It goes into the book unchanged, without an additional title: as the first page of the PDF and as the EPUB cover. Without `cover.front`, GhostWriter uses the cover template. Proofs start with the front cover followed by a blank page, so the title page stays on the right (“never” turns this off); for editions set “Front cover in the PDF” to “proofs and editions” (`typesetting.pdf_cover: always`). The proof note stays on the inner pages, not on the front cover. If the aspect ratio does not match the book format, nothing is distorted: an edition stops with a message, a proof is built without the front cover. Print PDF, booklet and cover wrap stay unchanged.

**Preview and limits:** Front preview, print wrap and EPUB cover share the same renderer. The image is scaled to fill and cropped; check the actual preview. Text exceeding the area height or words exceeding its width stop output. Without custom text areas, the template's title, subtitle and author wrap at word boundaries; if a single word is wider than the front cover, its font is reduced until it fits and the output reports the new size (#326). Reduce the font or adjust the area. Visually check contrast, overlap with artwork and the crop. Preview is a 150 dpi JPEG without bleed; print output is a PDF with bleed. Spine width still requires accurate book/print data. Preview and guides do not grant print approval. DOCX and ordinary interior PDFs do not gain a cover from these settings.

### Local cover tools

The general tools require no book-specific script. Color sampling needs Pillow; typesetting needs XeLaTeX with TikZ/TeX Gyre; raster preview also needs Poppler (`pdftoppm`). Settings live in `ghostwriter.yml`; text comes from `project.title`, `project.subtitle` and `project.author`.

```sh
# Read only: suggestions, sampled location, current settings
python scripts/cover_design.py BOOK colors
python scripts/cover_design.py BOOK colors --point 0.5 0.1
python scripts/cover_design.py BOOK show
# After an explicit save request: change only the named panels
python scripts/cover_design.py BOOK set '{"panel_backgrounds":{"spine":"#EEDDCB","back":"#EEDDCB"}}'
# Preview an unsaved proposal; original settings remain unchanged
python scripts/cover_design.py BOOK preview '{"panel_backgrounds":{"back":"#EEDDCB"}}' --pages 200 --out /tmp/cover-preview.pdf --front-jpg /tmp/cover-preview.jpg
```

Example text areas for A5 are shown below. The assistant can save these using `cover_design.py BOOK set` with a JSON patch. `preview` checks an unsaved JSON proposal in memory; write preview output away from the original image. Keep book-specific changes out of program files.

```yaml
cover:
  image: cover/motif.png
  image_mode: motif
  panel_backgrounds:
    spine: '#EEDDCB'
    back: '#EEDDCB'
  text_boxes:
    title: {x: 12, y: 12, width: 124, height: 24, font_size: 24, color: '#312A24', align: center, bold: true}
    subtitle: {x: 12, y: 39, width: 124, height: 12, font_size: 13, color: '#312A24'}
    author: {x: 12, y: 55, width: 124, height: 12, font_size: 14, color: '#312A24'}
```

`visible: false` hides a part. `font: serif` or `sans` selects its font family. `break_after: [2]` forces a break after word two; output stops if a metadata change makes the break position invalid. Otherwise width controls wrapping. `background_targets` limits `background` to `front`, `spine` and/or `back`; explicit `panel_backgrounds` take precedence. Unselected panels without a specific color use the default color. The image still covers the front background. JSON patches modify only named fields and merge individual text areas and panel colors. `null` removes an override, for example `{"text_boxes":{"title":null}}` restores the template title.


---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
