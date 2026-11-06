# Chat apps for GhostWriter v0.5

This is a translation of the historical assessment dated 31 October 2026. App capabilities and permissions can change; verify them in your own session before relying on them.

## Capabilities observed

At the time of the assessment, the built-in GitHub connections in Claude and ChatGPT were read-only. GhostWriter's chat-based operating path needs write capabilities for working branches, pull requests and releases.

| Capability | Claude built-in integration | Claude with a working environment | ChatGPT GitHub connector | ChatGPT Codex | Custom GitHub MCP connector |
|---|---|---|---|---|---|
| Read repository | Yes, branch files | Yes | Yes | Yes | Yes |
| Commit and branch | No | Yes | No | Yes | Listed by the server; test in the chat |
| Open a pull request | No | Yes | No | Yes | Test in the chat |
| Merge a pull request | No | Yes | No | Not established | Test in the chat |
| Create tags and releases | No | Rejected for the tested session type; branch deletion was also rejected | No | Not established | Not established |
| Inline widgets that respond in chat | Yes | If offered by the session | No | No | Depends on the app |

The original assessment refers to [Anthropic's GitHub integration help](https://support.claude.com/en/articles/10167454-use-the-github-integration), [OpenAI's GitHub connection help](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt) and the official [GitHub MCP server](https://github.com/github/github-mcp-server). These are links for checking current information, not evidence that every capability is available in a particular session.

## Ways to work with the repository

1. **Claude with a working environment:** The tested session could create commits, branches and pull requests and merge them. Tags and releases were rejected in that session.
2. **A custom GitHub MCP connector:** Configure it for the chat app and test the available write operations. See [connector setup](CONNECTOR-SETUP.en.md).
3. **Manual fallback:** The assistant supplies changed files for the user to commit. This works without chat write access but does not provide the same pull-request workflow in the chat.

The historical plan delegates creation of edition tags and releases and attachment of PDF, DOCX and EPUB files to a GitHub Action after the corresponding changes are merged.

## Automatically loaded instructions

GhostWriter repositories include `CLAUDE.md`, `AGENTS.md` and the general `.claude/skills/ghostwriter/SKILL.md`; program updates maintain them. An optional `assistant.yml` profile and its generated personal skill contain repository preferences such as Git identity, author and default narrative voice. Those belong to the book and are not overwritten by program updates.

Automatic loading depends on the assistant having repository access and actually supporting those files. Otherwise, the assistant must read `START.md` and `assistant.yml` as appropriate. Do not put secrets or manuscript text in these instruction files.

## Display

Claude sessions that support inline widgets can use the pinned `ghostwriter-ui` script and data. Other sessions use text or their own supported native chat elements. Do not assume an app can display a widget merely because the template exists. The English chat mode currently uses text or native chat elements; all graphical templates also have English labels for explicitly selected previews.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
