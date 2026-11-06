# Principles

GhostWriter helps people organize, research and manage a book so they can focus on writing. You decide what goes into your book.

## What GhostWriter does

- **Organizes:** Develop an outline of chapters and sections in conversation. You can change it later.
- **Researches:** Research sections and chapters with sources you can check.
- **Suggests:** Goals, summaries and drafts are proposals; you decide what to accept.
- **Version control:** Git records each state saved in your repository, so you can trace changes, compare revisions and restore earlier passages.
- **Produces editions:** Create a proof or an edition from approved chapters in PDF, Word and e-book formats.

## Version control with Git

GhostWriter builds on Git, the version control system used in software development. Each saved change has a unique identifier. Compare revisions, trace an edit back to its starting point, restore earlier text and develop drafts separately from accepted manuscript content. Each edition remains tied to its exact source state.

You own this history alongside the manuscript in your repository. GhostWriter exposes its benefits through guided saving, review and acceptance; working with the book does not require Git expertise. Drafts discussed in a chat become part of this history only when saved to the repository.

A shared history does not mean every client has already loaded the same state. Chat context, local copies, indexes and startup caches may lag behind GitHub. Improved cross-client state checking is [planned](WORKFLOW-MODEL.md#standabgleich-zwischen-clients-geplant); automatic synchronization is not yet guaranteed.

## What GhostWriter does not do

- **Make a book at the push of a button:** Your decisions, experience and voice matter.
- **Approve work on your behalf:** Writing a section requires your writing approval. Inclusion requires section approval, chapter approval and confirmation of the edition.
- **Present invention as fact:** Uncertain claims are marked for review. An unresolved marker prevents a section from entering an edition.
- **Make silent changes:** You see what is saved, and changes are applied after your confirmation unless you deliberately enable immediate application.
- **Lock you into a provider:** You choose which AI services research, write or check your work.

## Project rules

Global AI settings in `ghostwriter.yml` apply to research, brainstorming, writing, revision and fact-checking. They must not be silently weakened:

| Rule | Value | Meaning |
|---|---|---|
| Hallucination policy | `strict` | Do not invent facts; acknowledge gaps. |
| Sources | `required` | Support claims with sources actually checked. |
| Uncertainty | `explicit` | Mark uncertain passages visibly. |
| Creativity | `balanced` | Use examples and imagery without distorting facts. |
| Web research | `research` | Search actively for research tasks; say when search is unavailable. |

The book's `ai_providers` settings select services for individual tasks. See [providers](PROVIDERS.md) and [using AI services](DIENSTE-NUTZEN.md) (German).

## Images and visual references

Images can be assigned to a person, place, object, chapter or section. An image can be intended for the book, serve as a reference for future image generation, or be used for both purposes.

Uploading an image does not activate its use as a reference. The author explicitly decides whether and how it may be used. Record its origin, creator and known usage rights. Only durably stored and expressly accepted images can reliably be used in future editions. See [images and visual references](BILDER-UND-REFERENZBILDER.md) (German) for the separate reference workflow.

## Workflow

**Book → chapters → sections → research and brainstorming → manuscript → section approval → chapter assembly → chapter approval → edition.**

- A section is the smallest unit for research and writing; every chapter has at least one section.
- Chapters and sections can be added, renamed and reordered; their internal identifiers remain stable.
- A chapter can be assembled and approved only after all its sections have been approved.
- A repository can contain a library of books, each on its own branch.

## Starting a chat

A link to `START.md` does not automatically load its contents. With a GitHub connection, the assistant reads the file after you send the repository link. Otherwise, attach the file or copy its start prompt into the chat. A dedicated GhostWriter interface for this is planned.

## AI disclosure

GhostWriter was developed with assistance from Claude (Anthropic); this acknowledgement belongs in the documentation, not automatically in your book. You decide whether and how to disclose AI assistance in your book.

## Further reading

[Getting started](GETTING-STARTED.en.md) · [German documentation index](GRUNDSAETZE.md#unterlagen) · [Assistant instructions](../START.md) (German)

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
