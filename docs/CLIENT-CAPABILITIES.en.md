# What works in your chat

As of 24 November 2026. This page describes existing paths and their requirements, not acceptance of every plan, installation or client version. The [widget extension](CHAT-WIDGETS.en.md) is planned ([#555](https://github.com/ploeffler/GhostWriter/issues/555)).

## Check three separate things

1. **Presentation:** Markdown, images, a file/reading panel, native choice questions or an interactive app UI.
2. **Tools:** Reading a repository, editing files, creating branches and pull requests, executing scripts. Use only tools actually offered.
3. **Authority:** Personal GitHub permissions, content-approval authority and the section's writing state. A visible button replaces none of these checks.

The product name alone answers none of these questions. An MCP tool without a UI resource is not a widget integration. An attached HTML file is not yet an interactive book view.

## Capability matrix

| Environment | Existing path | Requirement / limit | Evidence |
|---|---|---|---|
| ChatGPT with a repository connection | Markdown views; actions through available connector tools | Check read and write tools separately; do not infer permissions from the connection name | Historical reports in [Chat apps](CHAT-APPS.en.md), no universal plan guarantee |
| ChatGPT with a UI-enabled MCP app | Interactive components are documented as a platform path | Requires an MCP server, UI resource and configured integration; the GhostWriter adapter in #555 remains planned | Official OpenAI documentation below; no practical GhostWriter acceptance |
| Codex Desktop with file and app tools | Markdown, local files, reading panel; native choice questions when offered | Absolute path on the accessible host; use `open_in_codex` only when offered and check its result | Local file creation and reading verified; panel call returned only `queued` on 24 November 2026, followed by a user report that the file could not be found; display not confirmed in this session |
| Codex CLI / IDE | Text, repository and script work using available tools | Do not assume the Desktop file panel or ChatGPT UI; check the specific IDE preview separately | Not practically tested in this task |
| Claude with widget support | Existing GhostWriter widgets and text fallback | Supported session and [template population](../templates/ui/BEFUELLUNG.md) | Existing project path; no new visual acceptance with this page |
| Open WebUI | Text and actions provided by the configured GhostWriter integration | Personal credentials for writes; verify UI callbacks for the installed version | [Integration guide](../integrations/openwebui/README.md); no new widget test |
| Other or unknown clients | Complete text/Markdown view | Enable only demonstrated extensions | Untested until the specific client is checked |

A finalized section remains locked even when a writing role exists. Editing requires explicit reopening and then permission to write. [Saving and approval authority](SAVING.en.md) apply in every presentation.

## What an appropriately equipped Codex session can do

- Read current book data through the GitHub connector and display Markdown views.
- Generate and update local reading copies and request display through an available file tool.
- Use shell and Python to inspect files, build documentation and run appropriate tests when the environment permits.
- Create requested issues and pull requests through available write tools. This does not automatically merge or publish them.
- Create images or other artifacts with suitable connected tools; creation does not include them in the book.
- Offer native choice questions when that tool is available. A question element is not a complete GhostWriter widget.

This describes capabilities, not a permanent guarantee for every new chat. Network, file or connector restrictions may block individual steps. Do not replace the actual session tools with an invented product-wide standard.

## When the reading copy does not appear

1. Check that the file exists and is readable on the working host; give its absolute path.
2. Open it with the available file/preview tool. Do not silently substitute a browser; respect local browser rules.
3. Report the exact result: `queued` means only **display requested and queued**. An existing path proves neither delivery to the client nor visible display.
4. Treat a user error report as a failure or an unresolved display problem. Do not repeat the same queued call as a success. Without a confirmed display path, explain the limit and keep the book overview in chat; provide full manuscripts according to local reading-copy rules.

Keep local drafts, changes saved on the working branch and the merged book state distinct. A preview grants no writing or finalization permission.

## Sources and rechecking

The official OpenAI pages were retrieved as documents on 24 November 2026, without browser operation: [MCP server and UI quickstart](https://developers.openai.com/plugins/build/app-quickstart) describes MCP tools for ChatGPT and Codex with optional UI in ChatGPT; [Add UI to your MCP server](https://developers.openai.com/plugins/build/chatgpt-ui) describes UI resources and checking individual host capabilities. This does not establish identical UI support across Codex variants.

For new acceptance, record client/variant, integration version, date, available tools, action, result and visible user confirmation. Do not include credentials or private manuscripts in public reports. Historical results retain their dates.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
