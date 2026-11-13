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

## Handing over files in the chat (#260)

"Export manuscript" builds the PDF in the "Manuskript ausgeben" action; the chat fetches it with `scripts/fetch_artifact.py` and hands it over as a file. As of 11 November 2026, **not yet tested in every app**:

| App | Expected path |
|---|---|
| Claude with a working environment | Fetch the PDF and send it as a file in the chat |
| Codex | Place the PDF in the working folder or attach it |
| ChatGPT (GitHub connector) | Depends on the connector and code environment; otherwise a link to the run |
| Open WebUI | Link to the run (`dispatch_workflow` starts `manuscript.yml`) |

Without file handover, the link to the run remains: download under *Artifacts*, 14 days, GitHub sign-in required.

**Tested on 11 November 2026 (Claude in the cloud):** Building and starting work; fetching failed because GitHub serves artifacts from `*.blob.core.windows.net`, which the session blocks. Remedy: allow that address under *Settings → Capabilities*; otherwise use the link to the run.

## Automatically loaded instructions

GhostWriter repositories include `CLAUDE.md`, `AGENTS.md` and the general `.claude/skills/ghostwriter/SKILL.md`; program updates maintain them. An optional `assistant.yml` profile and its generated personal skill contain repository preferences such as Git identity, author and default narrative voice. Those belong to the book and are not overwritten by program updates.

Automatic loading depends on the assistant having repository access and actually supporting those files. Otherwise, the assistant must read `START.md` and `assistant.yml` as appropriate. Do not put secrets or manuscript text in these instruction files.

## Choosing skills (#261)

Claude picks a skill from the skill descriptions. Users normally do not see that choice, and similar descriptions make it ambiguous. GhostWriter therefore asks (`CLAUDE.md`, `AGENTS.md`, `ghostwriter` skill):

- **Name the choice:** at the start of a task, Claude states in one sentence which skill it uses, or that none fits.
- **Specific before general:** the repository's personal skill (`assistant.yml` → `skill`) comes before the general `ghostwriter` skill. `ghostwriter` is meant for book and library repositories, not for program work on the main repository. Claude asks once only if the choice is genuinely ambiguous.
- **Do not load twice:** each load puts the whole instructions into the conversation again, which costs context and makes summarising happen sooner. If the instructions are still in the conversation, Claude does not reload them; if they were lost when a long conversation was summarised, Claude reloads them and says so briefly.

**Account skills:** skills stored in the Claude account rather than in the repository cannot be changed by GhostWriter. If two of them have nearly the same description, remove the redundant one in Claude's settings under “Skills”. A project instruction such as “Confirm the skill choice” is then no longer needed but does no harm.

## Display

Claude sessions that support inline widgets can use the pinned `ghostwriter-ui` script and data. Other sessions use text or their own supported native chat elements. Do not assume an app can display a widget merely because the template exists. The English chat mode currently uses text or native chat elements; all graphical templates also have English labels for explicitly selected previews.

**Open WebUI** shows no widgets. The “GhostWriter Direkt” pipe renders every view itself as Markdown and switches `Display: simple / organized / extended`, `Text only` and the answer mode without a model call (pipe 1.8 with GitHub tool 1.5, #282). From tool 1.6 the conversation model receives its own short start file `docs/start/einstieg-openwebui.md` instead of the general `START.md` (#204). Details (German): [Open WebUI guide](../integrations/openwebui/README.md#darstellung-und-antwortmodus-direkt-pipe-18-werkzeug-15).

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
