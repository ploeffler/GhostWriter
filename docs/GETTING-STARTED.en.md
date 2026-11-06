# Getting started: from an empty repository to your first edition

This guide describes how to set up GhostWriter and work on a book. You need a GitHub account and an AI chat assistant, ideally with access to GitHub and web research. You do not need to know Git.

**Language:** Say `Interface: English` to use English in the current chat, or `Deutsch` to switch back. The assistant presents English text or native chat elements; all current views support English native output; some linked documentation remains in German. The labels below include German wording for reference. Further localization work is tracked in [issue #74](https://github.com/ploeffler/GhostWriter/issues/74).

## 1. Create a repository

1. Open the [GhostWriter repository](https://github.com/ploeffler/GhostWriter) and choose **Use this template → Create a new repository**.
2. Choose a name and select **Private** if your manuscript should not be public. A fork of a public repository is always public.
3. Follow [Updates → Create a private book repository](UPDATES.en.md#create-a-private-book-repository) to set up automatic updates.

Your repository is a library: the default branch contains GhostWriter, and each book gets its own branch named `buch/<short-title>`.

## 2. Connect your chat assistant

Connect your assistant to GitHub and give it access only to your new repository. See [Chat apps](CHAT-APPS.en.md) and [Connector setup](CONNECTOR-SETUP.en.md) for setup instructions. Without a GitHub connection, the assistant can provide files in the chat for you to transfer yourself.

## 3. Start a chat and create a book

Send the repository link to a new chat. The assistant reads `START.md`, explains which capabilities are available, and shows your bookshelf. Without GitHub access, attach `START.md` or copy its start prompt into the chat.

Choose **New book**, or write `New book: <title>`. Enter a working title and, optionally, a short title and author. The form previews the branch name and warns if it is already taken. Choose **Create** to create the book branch.

## 4. Develop the outline

The assistant asks about your subject, goals, audience, book type, language and style. Together you develop chapters and sections, including their goals and short descriptions. The structure is created only after you explicitly approve the outline. You can also choose whether saved changes should be applied immediately.

## 5. Work on the book

The project overview opens chapters; a chapter opens its sections. You can research a section or a whole chapter, then approve writing and edit the resulting text yourself. Front and back matter, an AI-use statement, output settings and cover options can be added when needed.

Changes are collected until you choose **Apply changes**, unless you enabled immediate application. English commands include `Home`, `Overview`, `Chapter 3`, `Section 3.2`, `New chapter`, `Proof`, `Edition` and `Help`. The German commands remain available.

## 6. Approve and export

Approve each section when it is ready. Open review markers must be resolved before the section can be included in an edition. Approve a chapter after all its sections are approved and the chapter has been assembled. Each approval requires a separate confirmation and can be revoked.

Use **Proof** to create a proof PDF of the current state. When the desired chapters are approved, choose **New edition**, select the details and formats, and confirm. GitHub builds the edition as a release; subsequent corrections go into a new edition.

## 7. Return later

Start a new chat with the repository link to return to the bookshelf. A link to a book branch opens that book. You can create more books from the bookshelf. See the [user guide](USER-GUIDE.en.md), [principles](PRINCIPLES.en.md) and [updates guide](UPDATES.en.md) for further details.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
