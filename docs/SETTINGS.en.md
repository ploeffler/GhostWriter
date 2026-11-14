# Settings and output

[Deutsch](EINSTELLUNGEN.md) · English

## Which form do I need?

| In the chat | Purpose |
|---|---|
| `Project details` (pencil in the project overview) | Title, subtitle, short title, author, descriptions plus language, book type, target audience and planned translations |
| `Settings` | Project settings, including fact checking, updates, merge behavior and limits |
| `Core rules` | Levels for factual accuracy, creativity and research, and approvals; relaxing requires a separate confirmation ([principles](PRINCIPLES.en.md#project-rules)) |
| `Profile` | Git identity, default author and narrative voice |
| `AI services` | Existing services, access type and responsibility for each task |
| `Output` or `Cover` | Typesetting, fonts, paragraphs, front matter, formats, imprint, print profile and cover |
| `AI disclosure` | Whether and where a confirmed AI-use statement appears in the book |
| `Data` or `Update` | Show the actual program and update level |

Opening a form saves nothing. Use its save action to change settings. [Saving and merging](SAVING.en.md) explains when changes reach the book branch.

## Check the output

Open **Output**, change the fields you need and save them. Explicitly request a **Proof**, then review fonts, margins, images and cover. A proof is not a published edition. **Edition** opens the separate process for an immutable book version; see the [user guide](USER-GUIDE.en.md) for prerequisites and approvals.

## Services and costs

Start with services you already have. Access type determines whether work runs in the current chat, through a copied task or through an API. Keys belong in GitHub Secrets, never in the chat or a book file. See [using AI services](AI-SERVICES.en.md). Missing cost data does not mean confirmed zero cost.

## Limits and planned features

[Media layout](MEDIA-LAYOUT.en.md) with position, text wrapping and a width slider is not yet implemented. Deriving a cover from an uploaded design template is also planned; the existing cover options do not provide that derivation.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
