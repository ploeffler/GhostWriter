# Chat views and forms

GhostWriter presents overviews and forms in the chat. You choose an action or reply briefly, and the assistant saves through the repository workflow. Depending on the chat application, the same information may be presented as text with shortcuts or as native chat elements.

The examples below show the German interface and a test library. Icons and colors vary by application; the current graphical widgets are not yet fully translated into English.

## English core views and forms

`render_view.py --language en` supports the library, project overview and chapter overview, plus the forms `book-create`, `chapter-create`, `chapter-edit`, `section-create` and `project-edit`. Chapter edit and section creation take the chapter number as their next argument. These views use the same book data and approval checks as their German equivalents. Titles, descriptions and manuscript text remain in the book's language. Existing update/limit diagnostics, returned server error messages and configured attribution text are preserved as original notices.

The forms preserve existing titles and descriptions, mandatory-field and duplicate-name checks, stable IDs, fact-check codes and numeric insertion positions. Native forms accept English field names such as `Title`, `Working title`, `Summary`, `Goal`, `Position` and `Fact check`. Opening a form does not save anything; existing approval rules still apply.

The reviewed UI version 0.43.0 is pinned to commit `9a9a2029ae6ec3abb9359023cb3943a0ff10c428`. English continues to default to a native text view. Developers can preview the new graphical version with `--ui-ref <reviewed-ui-commit>`. All 38 graphical templates now have English fixed labels and script messages, and can be previewed with an explicit `--ui-ref`. Approval confirmations (writing, section, chapter, front/back matter and images), applying changes, chapter/section ordering and editing a series also have native English views and translated generated labels. Further native text forms and program-generated labels remain a separate migration step; such generated labels can still be German in the preview. Explicit English requests for those native text forms receive a clear availability message.

## Bookshelf

For a library with multiple books, the bookshelf shows each book's progress, edition and pending changes. Open a book to see its project overview, or continue setup for a book in progress.

<img src="bilder/buecherregal.png" alt="German bookshelf showing two books and their progress" width="640">

## New book

Enter a working title, short title and author. The form previews the branch name and warns if it is already taken.

<img src="bilder/buch-anlegen.png" alt="German new-book form with title and author fields" width="640">

## Setup choices

Questions with fixed answers can appear as choice cards, with a recommendation and a way to provide your own answer. Open-ended questions such as subject, goal and outline remain a conversation.

<img src="bilder/auswahl.png" alt="German choice cards for book type and length" width="640">

## Project overview

The overview lists chapters, status and AI API costs. Controls open project details, chapter creation and ordering, editions, AI services and settings. A library link returns to the bookshelf when it contains multiple books.

<img src="bilder/projektuebersicht.png" alt="German project overview with chapters, status and costs" width="640">

## Chapter view

The chapter view lists sections, their statuses, open review markers and costs. The chapter goal and summary appear above them, alongside chapter research.

<img src="bilder/kapitelansicht.png" alt="German chapter view with approved sections" width="640">

Other forms cover sections, chapter and section creation, ordering, approvals, applying changes, AI services, settings and editions. The templates are maintained in [ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
