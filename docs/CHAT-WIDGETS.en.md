# Interactive book views for more clients

**Planned, not implemented:** [feature request #555](https://github.com/ploeffler/GhostWriter/issues/555), as of 24 November 2026. This page describes the requested scope, not a finished installable extension. Existing paths are listed under [Client capabilities](CLIENT-CAPABILITIES.en.md).

## Requested interaction

Library, book, chapter and section views should offer the same data and actions in ChatGPT, Codex, Claude, Open WebUI and other suitable clients. Show chapter structure, progress, writing and finalization state, source status, open questions and next actions. Navigation should work without typing command abbreviations. Keep a complete text path.

A UI adapter needs a real callback to the assistant or authorized tools. HTML in chat or text styled as a button is insufficient. Select presentation based on available capabilities, not the product name.

## Planned technical path

- Shared view and action data rather than separate business rules per client.
- Evaluate the documented MCP Apps UI path for ChatGPT: MCP tools, a UI resource and configured integration. Official OpenAI sources are linked in [Client capabilities](CLIENT-CAPABILITIES.en.md#sources-and-rechecking).
- Check Codex Desktop, CLI and IDE separately for actual UI hosts, file/preview tools and callbacks. ChatGPT support is not evidence for Codex.
- Include the existing Claude widget path; provide safe text alternatives for Open WebUI and unknown clients.
- A capability view shows available / unavailable / untested, setup requirements, integration version and last practical acceptance.

Architecture proposal [#525](https://github.com/ploeffler/GhostWriter/issues/525) prefers a path without a self-operated server. A UI adapter may require additional infrastructure; decide hosting, authentication and operations before implementation. This documentation does not authorize a new backend or move existing version boundaries. Related: [character-conversation widget #431](https://github.com/ploeffler/GhostWriter/issues/431).

## Required implementation boundaries

Opening a view is read-only. Personal roles and section locks remain effective. Saving, allowing writing, finalizing, merging and publishing remain separate actions with existing confirmations. Recheck current state before mutation; stale views must not overwrite others' changes. Distinguish local proposals, saved working state and merged book state visibly.

A queued display or started job is not a success. If a UI host, display or tool is unavailable, show the specific problem and fall back to the complete text path. Keep private manuscripts within authorized data paths and use neutral public examples.

## Acceptance before claiming support

- Practically test library → book → chapter → section, back navigation and refresh after actions.
- Record setup, version, date and result for each client variant; mark untested combinations explicitly.
- Check German and English, narrow layouts, keyboard and focus, error and offline cases.
- Handle missing write rights, locked sections, stale data, cancellation and double clicks without unauthorized changes.
- Provide the same permitted actions through text when widgets are absent; no fake buttons or silent confirmations.
- Review documentation and visible behavior together. Passing structural tests is not visual acceptance or personal approval authority.

Installation steps, finished commands and concrete client acceptance follow with the implemented adapter. Until then use [existing views](INTERFACES.en.md) and [chat-app guidance](CHAT-APPS.en.md).

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
