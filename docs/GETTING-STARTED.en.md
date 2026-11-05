# Getting started: from an empty repository to your first edition

This guide describes how to set up GhostWriter and work on a book. You need a GitHub account and an AI chat assistant, ideally with access to GitHub and web research. You do not need to know Git.

**Language:** This guide is in English, but GhostWriter's interface, commands and linked documentation are currently in German. The labels below reproduce the German wording so you can find the right controls. A complete English interface is planned in [issue #74](https://github.com/ploeffler/GhostWriter/issues/74).

## 1. Create a repository

1. Open the [GhostWriter repository](https://github.com/ploeffler/GhostWriter) and choose **Use this template → Create a new repository**.
2. Choose a name and select **Private** if your manuscript should not be public. A fork of a public repository is always public.
3. Follow [Updates → Eigenes Buch anlegen](UPDATES.md#eigenes-buch-anlegen) to set up automatic updates.

Your repository is a library: the default branch contains GhostWriter, and each book gets its own branch named `buch/<short-title>`.

## 2. Connect your chat assistant

Connect your assistant to GitHub and give it access only to your new repository. See [Chat apps](CHAT-APPS.md) and [Connector setup](CONNECTOR-SETUP.md) for setup instructions. Without a GitHub connection, the assistant can provide files in the chat for you to transfer yourself.

## 3. Start a chat and create a book

Send the repository link to a new chat. The assistant reads `START.md`, explains which capabilities are available, and shows your bookshelf. Without GitHub access, attach `START.md` or copy its start prompt into the chat.

Choose **Neues Buch** (New book), or write `Neues Buch: <title>`. Enter a working title and, optionally, a short title and author. The form previews the branch name and warns if it is already taken. Choose **Anlegen** to create the book branch.

## 4. Develop the outline

The assistant asks about your subject, goals, audience, book type, language and style. Together you develop chapters and sections, including their goals and short descriptions. The structure is created only after you explicitly approve the outline. You can also choose whether saved changes should be applied immediately.

## 5. Work on the book

The project overview opens chapters; a chapter opens its sections. You can research a section or a whole chapter, then approve writing and edit the resulting text yourself. Front and back matter, an AI-use statement, output settings and cover options can be added when needed.

Changes are collected until you choose **Änderungen übernehmen** (Apply changes), unless you enabled immediate application. Existing German commands include `Start`, `Übersicht` (overview), `Kapitel 3`, `Abschnitt 3.2`, `Neues Kapitel`, `Probedruck` (proof), `Auflage` (edition) and `Hilfe` (help).

## 6. Approve and export

Approve each section when it is ready. Open review markers must be resolved before the section can be included in an edition. Approve a chapter after all its sections are approved and the chapter has been assembled. Each approval requires a separate confirmation and can be revoked.

Use **Probedruck** to create a proof PDF of the current state. When the desired chapters are approved, choose **Neue Auflage**, select the details and formats, and confirm. GitHub builds the edition as a release; subsequent corrections go into a new edition.

## 7. Return later

Start a new chat with the repository link to return to the bookshelf. A link to a book branch opens that book. You can create more books from the bookshelf. See the German [full guide](ANLEITUNG.md), [principles](GRUNDSAETZE.md) and [updates guide](UPDATES.md) for further details.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
