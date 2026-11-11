# Chat views and forms

GhostWriter presents overviews and forms in the chat. You choose an action or reply briefly, and the assistant saves through the repository workflow. Depending on the chat application, the same information may be presented as text with shortcuts or as native chat elements.

The examples below show the German interface and a test library. Icons and colors vary by application; the screenshots retain their original German labels; English native views and explicit graphical previews are available.

## English core views and forms

`render_view.py --language en` supports every current view and form. This includes the library, project, chapter and section views; approvals and applying changes; project settings, output options, AI services and disclosure; front/back matter, characters and images; series and omnibus; chapter research and every analysis panel; import previews; repository data and all built-in wizard choices.

English defaults to native text. `--text` also forces text when `--ui-ref <reviewed-ui-commit>` is supplied. The reviewed UI version 0.44.0 remains pinned to commit `3cbe4518d2391dc03d8283ea40f027ea611ebff6`; all 38 graphical templates have English fixed labels and script messages. An explicit `--ui-ref` enables a graphical preview. Use a widget only in a client that actually supports it.

The views share their original data and approval checks. Opening them saves nothing and grants no approval. Titles, descriptions, manuscripts, quotations, IDs, action codes, file conventions and configured edition names/tags stay unchanged. Saved analysis results, book-text suggestions, free-form choice specifications, server responses and configured attribution remain original content. Imported warnings are labeled as original notices. Built-in wizard labels are translated while response values, field paths, order, recommendations and selections remain identical.

English field names are mapped as described in `START.md`. For an edition, use `Date: YYYY-MM-DD` and optional `Notes: …`; for other forms, use their displayed field names. `X` cancels. Commands such as `Apply`, `All`, `Without`, `Replace`, `Question`, `Task` and `Scene` have the same confirmation requirements as their German equivalents.

## Bookshelf

For a library with multiple books, the bookshelf shows each book's progress, edition and pending changes. Open a book to see its project overview, or continue setup for a book in progress. Each book appears once; its editions are listed below it as “Edition 1”, “Edition 2” … and can be opened individually (release page or stored edition state). In the text version they have keys such as `2.1`.

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

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
