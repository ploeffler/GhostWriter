# GhostWriter v1.0 market comparison

Research and assessment of **20 November 2026**. Deutsch: [Marktvergleich](MARKTVERGLEICH-v1.0.md).

> **Planning status, not a hands-on test:** This compares the **confirmed v1.0 target scope** ([decisions D01–D32](ENTSCHEIDUNGEN-v1.0.md), [product roadmap](WORKFLOW-MODEL.md#produkt-roadmap)) with the vendors' public information. According to the manifest, the program version at the time of research is 0.7.0. None of the apps was tested in practice. Prices are snapshots. Planned GhostWriter features only count as available after implementation and acceptance.

## What v1.0 is meant to be

A complete book workflow **without its own interface and without AI provider APIs**: work happens in the chat (ChatGPT, Codex, Claude, Open WebUI), and the book lives in the author's own GitHub repository. It includes a library with several books, explicit approvals, immutable editions, PDF, DOCX and EPUB export, characters and images with provenance, a cover from an uploaded design template, manuscript import, style and continuity checks, editorial review, and German and English operation.

After v1.0: own web app and offline mode (D06, D19), AI provider API connections; DOCX round trip in v1.1 (D17); foreword, afterword, glossary and book translation in v1.5.

## Products compared

| App | Focus | Model (as stated by the source) |
|---|---|---|
| [Sudowrite](https://www.sudowrite.com/) | AI writing help for fiction | Credit-based subscription, about USD 19/29/59 per month, cheaper billed yearly |
| [Novelcrafter](https://www.novelcrafter.com/pricing) | Story bible ("Codex"), planning, optional AI with own API key | Browser, from USD 4 per month |
| [Atticus](https://www.atticus.io/) | Writing and typesetting for self-publishers | One-time USD 147 |
| [Scrivener 3](https://www.literatureandlatte.com/scrivener/overview) | Classic long-form writing app, snapshots, compile | One-time purchase, Mac about USD 60 |
| BookyAI | AI end-to-end workflow up to Amazon KDP | See the [BookyAI comparison](BOOKYAI-VERGLEICH.md) (German) |

## Feature comparison

| Area | GhostWriter v1.0 (target) | Compared products | Assessment |
|---|---|---|---|
| Writing interface | Chat; no own interface until v1.0 | Own editor, corkboard, outline (Scrivener, Atticus, Novelcrafter) | Disadvantage |
| Getting started | GitHub account, repository, chat access | Installation or browser account | Disadvantage |
| Versions, approvals, editions | Git history, explicit approvals, immutable editions | Snapshots (Scrivener), revision history (Novelcrafter) | Clear strength |
| AI costs | Existing chat subscription, no fictitious API costs | Credits (Sudowrite), own API key (Novelcrafter) | Strength |
| Vendor lock-in | Files in own repository, interchangeable AI, local models via Open WebUI | Platform or app format; Novelcrafter allows local models | Strength |
| Research and evidence | Documented research runs, sources, image provenance and licence details | Mostly no evidence-oriented research | Distinct profile, especially for non-fiction |
| Characters and world | Character references, story memory as a check, series comparison planned | Codex with cross-references and series-wide entries (Novelcrafter) | Weaker usability |
| Prose tools for fiction | Writing and revising in the chat | Specialised tools (Sudowrite), character chat (Novelcrafter) | Disadvantage |
| Typesetting and export | PDF, DOCX, EPUB; image position, text wrap and width still to be implemented | Mature design themes (Atticus), flexible compile (Scrivener) | Output quality not yet proven |
| Collaboration | Roles via GitHub permissions, no simultaneous editing | Built-in invitations (Novelcrafter, Atticus) | Disadvantage |
| Editorial review and QA | Structural review, language review, proofreading, AI pattern list | Partial review features (Novelcrafter) | Strength |
| Translation, audiobook, KDP research | Translation only in v1.5; audiobook and KDP research not planned | BookyAI offers all three, partly as add-on licences | Gap |
| Client coverage | Four environments required; test access for ChatGPT and Claude not yet proven | Own application, one way of operating | Acceptance risk |

## Assessment

GhostWriter does not compete as a better writing app but as **controlled book development**: sources, traceable changes, reliable approvals and no lock-in to one AI provider. For usability, fiction tools or refined typesetting, Novelcrafter, Sudowrite or Atticus are further ahead by their own descriptions. GhostWriter stands out most for non-fiction, texts that need evidence, and projects where versions and approvals matter.

**Recommendation, not a confirmed roadmap change:** Do not extend the v1.0 scope. A simple, fully tested core workflow and proven PDF and EPUB output quality come first. Only a complete hands-on test from idea to print-ready output can show whether operation and output keep up.

## Sources

- Sudowrite: [pricing](https://editor.sudowrite.com/pricing), summary of 9 Nov 2026 at [Activepieces](https://www.activepieces.com/blog/sudowrite-pricing-2026-which-plan-should-you-get)
- Novelcrafter: [pricing](https://novelcrafter.com/pricing), [Codex](https://www.novelcrafter.com/features/codex), [Toolradar](https://toolradar.com/tools/novelcrafter/alternatives)
- Atticus: [price overview](https://www.publishing.co.uk/guides/how-much-does-atticus-cost/), [Kindlepreneur comparison with Vellum](https://kindlepreneur.com/vellum-alternatives/) (Atticus co-founder, not independent)
- Scrivener: [Mac App Store](https://apps.apple.com/us/app/scrivener-3/id1310686187?mt=12)
- BookyAI: [BookyAI comparison](BOOKYAI-VERGLEICH.md)

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
