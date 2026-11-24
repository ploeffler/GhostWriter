# Clients and capabilities

Status: 24 November 2026, program version 0.9.0. For each client, this page says what GhostWriter **displays** and **executes**, what does not work and what has not been checked yet. It answers the question in #555. What that issue names as a goal (interactive views for ChatGPT and Codex) is marked below as **planning** and is **not available**.

Neither support nor impossibility follows from a program's name. What matters is what actually arrives in the environment. The matrix changes with program and client versions; check it in your own session before important work.

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | available: implemented in the program and documented |
| ❌ | not available |
| ⏳ | unchecked: no reliable statement, and no claim of impossibility either |

“Available” is not acceptance. Practical acceptance is recorded per client with a date in the [test plan v1.0](TESTPLAN-v1.0.md); missing access is shown there as ⏳.

## Five different capabilities

They are often confused:

1. **Text and Markdown:** every view exists as a text version (`render_view.py … --text`). This works everywhere.
2. **File or preview panel:** shows a file. It is not a GhostWriter widget. In the Codex file panel, `queued` only means “marked for display”; the file can exist locally without you being able to open it in the panel. GhostWriter reports a file as opened only when the display is confirmed; otherwise it gives the path only.
3. **Native choice questions:** the client's own question elements. GhostWriter uses them where they exist and offers text otherwise.
4. **GhostWriter widget:** the interactive view from [ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui) (`GW.render`). It needs a client that renders it (`chat_widgets: true` in `providers.yml`, currently Claude). GhostWriter never outputs HTML or widget code as text.
5. **Installed integration (MCP app, plugin):** a dedicated interface in a client. An existing file tool or a plugin system does not prove that a GhostWriter interface is installed.

## Capability matrix

| Capability | ChatGPT | Codex (desktop, CLI, IDE) | Claude (claude.ai) | Claude Code | Claude web app | Open WebUI |
|---|---|---|---|---|---|---|
| Text version of all views | ✅ | ✅ | ✅ | ✅ | — (own display) | ✅ |
| Native choice questions | ⏳ | ⏳ | ⏳ | ⏳ | — | ⏳ |
| GhostWriter widgets | ❌ (no installed integration) | ⏳ | ✅ | ⏳ | ✅ (own version) | ⏳ (own route via pipe and tool) |
| Show a file or PDF in the client | ⏳ | ⏳ (panel: `queued` ≠ opened) | ⏳ | ⏳ | — | ⏳ (link to the run) |
| Write to the repository (branch, commit, pull request) | ✅ (22 Nov., route not individually documented) | ✅ (22 Nov., route not individually documented) | ✅ (22 Nov.) | ✅ | ✅ (commit to the working branch) | ⏳ (personal access needed) |
| Approvals only with explicit confirmation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| View, move up and cancel the background queue | ⏳ | ✅ (text) | ✅ (widget) | ✅ (text) | ✅ | ⏳ |
| English operation | ✅ (text) | ✅ (text) | ✅ (text; widget with `--ui-ref`) | ✅ (text) | ⏳ | ✅ (text) |

The text versions come from `render_view.py`, which needs an environment that can run scripts (Codex, Claude Code, a working environment). Without scripts the assistant works from `START.md` and reads the files itself. The rows on writing and practical acceptance rest on [test plan v1.0](TESTPLAN-v1.0.md), section 1. Rows marked “⏳” are not refuted, only unchecked.

## Per client

- **ChatGPT:** the built-in GitHub connector reads only. Writing goes through an environment with write access (Codex, ChatGPT Work or a custom connector). Views appear as Markdown or native elements where the client supports them. Setup: [Chat apps](CHAT-APPS.en.md), [Connector setup](CONNECTOR-SETUP.en.md).
- **Codex (desktop, CLI, IDE):** reads `AGENTS.md` and the skills in the repository itself. Desktop, CLI and IDE are to be considered separately; a statement for one variant does not carry over to the others. Setup: [Chat apps](CHAT-APPS.en.md).
- **Claude (claude.ai):** shows the GhostWriter widgets. Writing through a working environment or the GitHub connector.
- **Claude Code:** loads the repository's skills; writing through the working environment.
- **Claude web app:** an artifact in Claude that shows the same templates and executes clicks directly, through the user's GitHub connection. Outside the v1.0 scope ([D06](ENTSCHEIDUNGEN-v1.0.md#d06--eigene-web-app-ohne-integrierten-modellaufruf)). Functions and limits: [apps/claude/README.md](https://github.com/ploeffler/GhostWriter/blob/main/apps/claude/README.md).
- **Open WebUI:** own route through the GitHub tool and the “GhostWriter Direkt” pipe, without local GhostWriter scripts. Writing needs the user's personal access. Setup: [Open WebUI](https://github.com/ploeffler/GhostWriter/blob/main/integrations/openwebui/README.md).

## Always the same

- Opening a view saves nothing and grants no approval. A click grants only the specific confirmation shown.
- The view re-reads the current state. Writing steps check the current state and reject an outdated form.
- Personal roles, section locks and explicit confirmations apply unchanged in every client. There is no automatic merge.
- Without a widget, panel or installation, full operation remains available through text.

## Troubleshooting

| Observation | What it means | What to do |
|---|---|---|
| The widget does not appear | The client does not render it | Say `Nur Text`; GhostWriter shows the text version |
| A file shows as `queued` in the panel | The display is only marked | Use the path; GhostWriter does not report the file as opened |
| A tool is not connected | The step does not work in this environment | GhostWriter names the step and outputs the file contents with the target path so you can commit yourself |
| Open WebUI does not recognise book navigation | Tools do not arrive at the pipe as callables | `check navigation` (from pipe 1.9) shows it without a GitHub or model call |
| A view looks outdated | The state that was read has changed | Reopen the view; writing actions check the state anyway |

## Planning (not available)

This section is **neither a commitment nor a description of existing functions.** It summarises #555:

- Interactive library, book, chapter and section views for ChatGPT, Codex and other clients, fed by the same view and action data as today, with adapters according to the capability actually available.
- For ChatGPT, an MCP apps UI route is to be evaluated and offered as an installable integration. Such an integration probably needs a hosted server. A dedicated hosting and management service is postponed until after v1.0 under [D06](ENTSCHEIDUNGEN-v1.0.md#d06--eigene-web-app-ohne-integrierten-modellaufruf) and D09; the hosting question is open (#525). No silent approval of a new backend.
- Codex desktop, CLI and IDE are to be checked individually; support in ChatGPT is not transferred wholesale.
- A capability view in the program with status available / not available / unchecked, prerequisite and last acceptance.

## Sources

- Official OpenAI basics as cited in #555 (checked there on 24 November 2026, not retrieved again here): [app quickstart](https://developers.openai.com/plugins/build/app-quickstart) and [ChatGPT UI](https://developers.openai.com/plugins/build/chatgpt-ui). The quickstart separates MCP tools for ChatGPT and Codex from the optional UI in ChatGPT.
- In the repository: [Chat apps](CHAT-APPS.en.md), [test plan v1.0](TESTPLAN-v1.0.md), `providers.yml` (`chat_widgets`), `templates/ui/BEFUELLUNG.md` (display mode), `AGENTS.md`.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
