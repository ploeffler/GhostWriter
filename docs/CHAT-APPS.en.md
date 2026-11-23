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

**Field report of 22 November 2026 (#22, reported by the owner):** Work with repositories was done in both Claude and ChatGPT. Changing a file with a commit, creating a branch, opening a pull request and merging a pull request worked in both apps, and a GhostWriter form saved as a pull request in ChatGPT. A mixed path was used; which connection was used in each app (custom connector, Codex or Claude Code) is not recorded per column. The custom-connector column therefore stays without individual evidence until this is added per app and plan.

## Ways to work with the repository

1. **Claude with a working environment:** The tested session could create commits, branches and pull requests and merge them. Tags and releases were rejected in that session.
2. **A custom GitHub MCP connector:** Configure it for the chat app and test the available write operations. See [connector setup](CONNECTOR-SETUP.en.md).
3. **Manual fallback:** The assistant supplies changed files for the user to commit. This works without chat write access but does not provide the same pull-request workflow in the chat.

The historical plan delegates creation of edition tags and releases and attachment of PDF, DOCX and EPUB files to a GitHub Action after the corresponding changes are merged.

## Web app “GhostWriter für Claude” (experiment)

Besides the chat there is an experimental web app that runs as an artifact in Claude: [GhostWriter für Claude](https://claude.ai/artifact/PQ3zcq4ofwwRcP7dMHMG9B). It shows the same widgets as the chat and carries out clicks directly. That covers saving a section, approvals, creating chapters and sections, reordering, project details, research and ghostwriting “now”, applying changes, the “Data” page and a Claude panel with suggestions. It reads and writes through each user's own GitHub connection, and Claude runs on that user's own account. There is no separate API, server or key.

The same rules apply as in the chat. Everything goes to the working branch as one commit per action. Changes reach the book only through “apply changes” with confirmation, and every approval needs its own confirmation. Private repositories need the GitHub App “Claude Github MCP Connector” installed on the owner account. The app is not part of the v1.0 scope ([D06](ENTSCHEIDUNGEN-v1.0.md#d06--eigene-web-app-ohne-integrierten-modellaufruf)). Its files are not copied into libraries by the update. The app is currently German only. Setup, limits and maintenance: [apps/claude/README.md](https://github.com/ploeffler/GhostWriter/blob/main/apps/claude/README.md) (German).

## Reading copy next to the view (#289)

For the chapter and section views the assistant creates the text as a Markdown file with `scripts/assemble.py … reading N` or `N.M` and hands it over next to the view, again after every change (`START.md`, "Lesefassung"). As of 15 November 2026:

| App | Path |
|---|---|
| Claude with a working environment | Send the file with display "render": it opens in the side panel, nothing is downloaded (tested in YAWA) |
| Codex / ChatGPT Work with file tools | Open the existing reading copy in the file panel or available preview tool. In Codex use `open_in_codex` with a file target, absolute path and `placement: right`; no browser. `queued` means only that display was requested. |
| ChatGPT without script execution | Use the "Manuskript ausgeben" action with `format md`, then supply the file from `lesefassung/<book>`. With a read-only connection the author starts the action via its link. Use only available file/preview tools; do not assume Canvas or writing-block support. Without preview, offer a file/link and state the limitation. **This fallback has not yet been tested in practice.** |
| Open WebUI | `dispatch_workflow` (`format md`, tool 1.7 or later), then `read_file` from the `lesefassung/<book>` branch. **Not yet tested in practice** |

The existing rule also applies to OpenAI (#316), independently of display mode. With local execution, generate the file directly; no workflow run is needed just to view it. Unsaved section proposals use `assemble.py <project> reading N.M --draft-file <proposal.md> -o <reading-folder>` (outside the book folder) and refresh the same file after edits. The preview changes no manuscript or approvals and labels the proposal separately from the saved section status. A local preview, work-branch storage and merged book content are distinct states.

With “Display: extended”, keep the extended section view in the chat: chapter/section, goal, summary, work and actual storage status, writing and finalization status, source status, open points and actions. Mark missing information as unknown; derive costs/markers only from data. Do not duplicate the complete text in the chat. `Lesefassung aus/an` affects this chat only and does not change display mode. Without visible confirmation report only a display request; disclose unavailable tools. A preview grants no approval.

The [official OpenAI file documentation](https://learn.chatgpt.com/docs/artifacts-viewer) distinguishes desktop, Work on the web, CLI and IDE capabilities. It does not establish identical side panels in every client. The concrete Codex call depends on its available tool. Verification on 15 November 2026 confirmed local generation and same-file updates. The Codex tool returned only `queued`; the user then confirmed readable rendering and automatic refresh of the same file without reopening it. This visual verification applies to the tested Codex session. ChatGPT Work remains untested in practice.

The `lesefassung/<book>` branch only holds the latest reading copies per chapter or section and is never merged. The file shows the state when the action started; after a change it is only refreshed if the action runs again. Each run costs about one Actions minute (no TeX).

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

## Conversation and manuscript work (#315)

Book work alternates between **conversation** (discussing ideas, characters, scenes and research; no book files are changed) and **manuscript work** (writing and revising sections, saving the book state). With `work_modes: auto` in the assistant profile or the command `Automatic mode switch on`, the assistant picks the mode from the request and only mentions the switch briefly; without it, it asks once before manuscript work. Before the first write it checks the book, branch, pull request and the current state of the file again. Saving, applying changes and approvals stay separate, confirmed steps ([START.md](../START.md), “Gespräch und Manuskriptarbeit”).

| Environment | Conversation | Manuscript work | Switching |
|---|---|---|---|
| Claude with the repository attached or a work environment | yes | yes | in the same chat, no handover |
| Claude without repository, ChatGPT with the GitHub connector (read-only) | yes | no | prepared handover to an environment with write access |
| ChatGPT Work, Codex | yes | yes | in the same chat; handover back to a plain chat if needed |
| Open WebUI | yes | depending on the configured tools | otherwise prepared handover |

Switching the interface itself (for example from a ChatGPT chat to Work) is up to the provider; GhostWriter does not switch it. The assistant states this limit in one sentence and offers the `Handover` command: `python scripts/handover.py . --section 3.2 --mode manuskript` produces copy-ready text with a start prompt, the verified state (repository, book branch and commit, work branch, pull request, section with checksum, open sections, conversation backups) and a JSON block. From the backups – accepted ones in the book and still open `ghostwriter/chat/*` – it carries over the saved **decisions** and **open tasks** (planning topic), shortened to 600 characters per backup and with their origin; this is saved state, not an approval (#315, part 2). The assistant adds what exists only in the chat, explicitly marked as not saved. In the other environment, `python scripts/handover.py . check <handover>` checks before the first write: `✓` unchanged, `ⓘ` newer version (re-read first), `✗` conflict (do not write). The script only reads.

## Keeping chats and apps in step (#179)

An open chat can be out of date when another app has saved, a program update has arrived or `assistant.yml` has changed. After loading, the assistant records the state it read (`python scripts/standabgleich.py . stand --book <book> [--work <work branch>] --fetch`) and checks it at every new task, after a pause and before writing (`… check <state> --fetch`): `✓` unchanged, `ⓘ` newer state (re-read files, reload instructions or profile if they changed), `✗` conflict (do not write). It checks book, work branch, program, instructions, profile and data version, plus as a `⚠` hint whether the index file and summaries match the state (otherwise read the original files); not chat contents, unsent input or a connection's cache. The script only reads.

## Saving tokens during a chat (#392)

A chat's usage grows with every message: the app resends the whole previous
conversation and the descriptions of all connected tools each time. GhostWriter
keeps its state in the repository, so nothing is lost when you switch.

- **New chat per task:** new book, new task or finished section → new chat. The
  assistant suggests this at suitable points (after an approval, after planning
  or research), never in the middle of a revision or debugging, and never forces it.
- **Handover sentence:** at the end of a task the assistant gives one short
  sentence for continuing (book, section, open step). In the new chat it loads
  book knowledge and saved conversations itself ([Story memory](STORY-MEMORY.en.md)).
  Save unsaved work first ([Session backup](SESSION-BACKUP.en.md)).
- **Fewer connections:** turn off connections not needed for book work
  (connectors, MCP servers, Open WebUI tools). Much of the base usage comes from
  their tool descriptions, not from GhostWriter (measured in #296).
- **Sub-agent for many chapters:** where the app supports sub-agents (e.g.
  Claude Code), one reads the chapters for story memory and editorial review and
  returns only findings with locations. This also keeps the rule "no whole book in the chat".
- **Smaller model for mechanical checks (#418):** proofreading and re-checks run
  on a small model, structural review and new text on a large one; see
  [Model choice for sub-agents](EDITORIAL-REVIEW.en.md#model-choice-for-sub-agents-418).
- **Research with sub-agents (#449):** one agent per research topic, in
  parallel; only the run-file skeleton comes back into the chat, see
  [Research runs with sub-agents](EDITORIAL-REVIEW.en.md#research-runs-with-sub-agents-449).

Not adopted: settings that only apply to Claude Code in the terminal (model
choice in `settings.json`, environment variables, `/cost`). Still open: measuring
with `Prompt-Profil JSON` from which conversation length a new chat pays off.

## Automatically loaded instructions

GhostWriter repositories include `CLAUDE.md`, `AGENTS.md` and the general `.claude/skills/ghostwriter/SKILL.md`; program updates maintain them. An optional `assistant.yml` profile and its generated personal skill contain repository preferences such as Git identity, author and default narrative voice. Those belong to the book and are not overwritten by program updates.

**ChatGPT and Codex:** There is no separate ChatGPT entry file; `AGENTS.md` applies to ChatGPT and Codex just as `CLAUDE.md` applies to Claude. Codex reads `AGENTS.md` automatically. In a ChatGPT chat with the GitHub connector, point the project instructions to `AGENTS.md` and `START.md`. A hand-written `CHATGPT.md` in a book repository belongs to the book, never arrives with updates and therefore goes stale; prefer a short pointer to `AGENTS.md` and `START.md` (template in the German [chat apps guide](CHAT-APPS.md#automatisch-geladene-hinweise-136)).

Automatic loading depends on the assistant having repository access and actually supporting those files. Otherwise, the assistant must read `START.md` and `assistant.yml` as appropriate. Do not put secrets or manuscript text in these instruction files.

## Choosing skills (#261)

**Independent of the assistant:** the skills live in the repository under `.claude/skills/<name>/SKILL.md`. Claude Code loads them itself; ChatGPT, Codex and other assistants are told by `AGENTS.md` (Claude by `CLAUDE.md`) to read the headers of all `SKILL.md` files and load the matching skill in full before they start. Both files come from the main repository with the update; nothing needs setting up in the book.

Claude picks a skill from the skill descriptions. Users normally do not see that choice, and similar descriptions make it ambiguous. GhostWriter therefore asks (`CLAUDE.md`, `AGENTS.md`, `ghostwriter` skill):

- **Name the choice:** at the start of a task, Claude states in one sentence which skill it uses, or that none fits.
- **Specific before general:** the repository's personal skill (`assistant.yml` → `skill`) comes before the general `ghostwriter` skill. `ghostwriter` is meant for book and library repositories, not for program work on the main repository. Claude asks once only if the choice is genuinely ambiguous.
- **Do not load twice:** each load puts the whole instructions into the conversation again, which costs context and makes summarising happen sooner. If the instructions are still in the conversation, Claude does not reload them; if they were lost when a long conversation was summarised, Claude reloads them and says so briefly.

**Account skills:** skills stored in the Claude account rather than in the repository cannot be changed by GhostWriter. If two of them have nearly the same description, remove the redundant one in Claude's settings under “Skills”. A project instruction such as “Confirm the skill choice” is then no longer needed but does no harm. The personal skill does not belong in the account: it depends on user and repository and lives only in the repository (`.claude/skills/<skill>/SKILL.md`, generated from `assistant.yml`). An account copy goes stale with the next regeneration; Claude points this out once and the repository version applies. General procedures such as setup, write-access check and reporting issues are in the `ghostwriter` skill, not in the personal skill.

## Display

Claude sessions that support inline widgets can use the pinned `ghostwriter-ui` script and data. Other sessions use text or their own supported native chat elements. Do not assume an app can display a widget merely because the template exists. The English chat mode currently uses text or native chat elements; all graphical templates also have English labels for explicitly selected previews.

**Open WebUI** shows no widgets. The “GhostWriter Direkt” pipe renders every view itself as Markdown and switches `Display: simple / organized / extended`, `Text only` and the answer mode without a model call (pipe 1.8 with GitHub tool 1.5, #282). From tool 1.6 the conversation model receives its own short start file `docs/start/einstieg-openwebui.md` instead of the general `START.md` (#204). From pipe 1.10, status rules reach the model only for status questions, and older pipe views are sent as one line each (#285). Details (German): [Open WebUI guide](../integrations/openwebui/README.md#darstellung-und-antwortmodus-direkt-pipe-18-werkzeug-15).

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
