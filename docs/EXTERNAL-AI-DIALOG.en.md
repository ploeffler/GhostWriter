# Prepare and review an external AI dialogue

[Deutsch](EXTERNER-KI-DIALOG.md) · English

This manual chat workflow extends [Copy the task](AI-SERVICES.en.md#another-chat-service-copy-the-task). Use another provider for research, brainstorming, drafting, revision or review, then bring the conversation back. No AI-provider API connection is required.

**Status:** locally exercised as a manual workflow. These are instructions for the chat assistant, not a new parser command, automatic exporter or provider connection. Downloads and copy controls depend on the client; a collapsible code block is optional presentation. Plain text is the fallback.

## Start

For example, enter:

> Prepare an external AI dialogue for section 2.3.

Or:

> Prepare an external revision for chapter 2.

These natural-language requests start preparation in chat. Chapter revision still requires the prerequisites in the [guided workflows](ARBEITSABLAEUFE.md). Opening and preparation change no book files or approvals. Do not print entire chapters or books in chat: supply extensive source text only in an explicitly selected file package or separate section assignments.

The assistant reads the current project state and fills the [assignment template](../templates/external-dialog/task.en.txt) with:

- assignment ID, task, unit and source version;
- goal, relevant context and necessary source text;
- confirmed information and answered questions;
- open questions, voice, output format and permitted creative additions;
- source requirements and working mode: dialogue or direct work.

Missing information remains open. Transfer only relevant context. In dialogue mode, the provider should build on known answers, ask one open main question per message and respond to what the author says. Direct work requires clarification only for decisive gaps.

## With the other provider

1. Paste the **completed assignment** or upload it as a file in a new chat. A ZIP containing test planning and instructions is not the assignment and should not be uploaded wholesale.
2. Note provider, displayed model and date. If no model is visible, record “not displayed”.
3. Answer freely. For comparisons, use the same starting assignment; new answers may differ between conversations.
4. When enough material is available, send “Draft now” and the [return prompt](../templates/external-dialog/return.en.txt).
5. Export or copy the complete visible conversation, including questions, answers and result. Internal model reasoning is not part of the return. Do not reconstruct missing messages.

## Bring it back

For example, enter:

> This is the return from Provider A for section 2.3.

Attach the conversation or paste it, adding assignment ID and model where known. A private link does not grant account access. A shared link is usable only if its contents can actually be read. A partial text or summary must not be treated as a complete conversation. Preserve the original and record later corrections or a missing final word as additions.

The return is material for review, not automatic saving. Do not guess model identity, question provenance or missing answers. Recheck the project before applying changes if its source state has moved. Mark sources that cannot be checked; existing source and approval requirements remain in force.

## Analysis and recommendation

The assistant uses the [review template](../templates/external-dialog/review.en.md) to distinguish:

- existing and new information from provider interpretations;
- dialogue quality: open questions, repetition, leading interpretations and use of answers;
- result quality: facts, voice, logic and fulfilment of the assignment;
- limits: missing parts, unchecked sources and different information gathered in each conversation.

Every review ends with a **reasoned recommendation**: what to use, revise or omit, what needs targeted clarification, and the next concrete step. An explicitly confirmed author answer remains usable even after a leading question; preserve its provenance. Do not treat metaphors as proven medical or technical mechanisms, silently expand abbreviations or equate strong skills with consistent success.

Richer material does not automatically mean better prose. One run does not establish an overall provider winner. Recommendation, author decision, saving and formal approval remain separate. Manuscript changes still require writing approval, protection of approved text, full editorial review and the normal pull-request workflow. A draft may be shown in chat for review without replacing a missing formal approval.

## Test scope and limits

Local experience covered file/copy assignments, an external conversation return, analysis of statements and recommendations, and a missing final word supplied later. The returned material did not fully document the starting prompt or model. This exercises the manual return and review path, not a controlled comparison of all providers or acceptance across clients. Further tests record source version, scope, displayed model where available, actual return, recommendation and remaining issues. Test evidence and private book conversations stay outside the public documentation website.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
