<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-wortmarke-dark.svg">
    <img src="assets/logo-wortmarke.svg" alt="GhostWriter" height="72">
  </picture>
</p>

[Deutsch](README.md) · English

> **Note for AI assistants:** This is a GhostWriter project. At the beginning of a new chat, read [`START.md`](START.md), `ghostwriter.yml` and [`BUCHSTATUS.md`](BUCHSTATUS.md). Use START.md internally and do not fetch it again on every message after successful loading. Refresh live branches and relevant project data for the current task. Follow the generated entry or the full source instructions for setup, resuming work and interface language.

## GhostWriter – your book, step by step

GhostWriter is a workspace for developing a book in a chat with an AI assistant. It helps organize ideas into chapters and sections, research topics, and keep track of proposals and decisions. You remain responsible for writing decisions and approvals.

- **Step by step:** Move from an empty repository to an edition while keeping track of the book's progress. See the [getting started guide](docs/GETTING-STARTED.en.md).
- **Guided conversations:** Overviews, forms and choices support work in the chat. Say `Interface: English` for English chat operation; all existing views have an English text version. Graphical previews are also translated and require a client that supports them.
- **Version control from software development:** Git records every revision saved to your repository. Compare revisions, restore earlier passages and develop drafts separately from accepted text. Each edition is tied to an exact book state. See [version control with Git](docs/PRINCIPLES.en.md#version-control-with-git).
- **You stay in control:** Sections require your approval. Sources should be documented and checked, and uncertainties made clear.

**For text-led books:** GhostWriter is not intended for photo books or picture-led collections. One scene corresponds to one section, with at most one media item. [Media positioning and text wrapping](docs/MEDIA-LAYOUT.en.md) are confirmed requirements awaiting implementation.

## Quick start

1. Create your own private repository from this template. See the [getting started guide](docs/GETTING-STARTED.en.md#1-create-a-repository).
2. Open a chat with GitHub access and send your repository link.
3. Choose **New book** and follow the setup conversation. Chapters and sections are created after you approve the outline.

## Further reading

[Getting started](docs/GETTING-STARTED.en.md) · [User guide](docs/USER-GUIDE.en.md) · [Principles](docs/PRINCIPLES.en.md) · [AI services](docs/AI-SERVICES.en.md) · [Chat views](docs/INTERFACES.en.md) · [Chat apps](docs/CHAT-APPS.en.md) · [Updates](docs/UPDATES.en.md)

**Visual workflows:** [Book lifecycle](docs/BOOK-LIFECYCLE.en.md) · [Creation cycle](docs/CREATION-CYCLE.en.md) · [Saving and merging](docs/SAVING.en.md)

Further localization work is tracked in [issue #74](https://github.com/ploeffler/GhostWriter/issues/74).

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg"><img src="assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
