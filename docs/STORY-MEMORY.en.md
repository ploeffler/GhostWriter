# Story memory: reconcile facts and continuity

[Deutsch](BUCHGEDAECHTNIS.md) · English

This optional chat workflow extends [editorial review](EDITORIAL-REVIEW.en.md)
and [quality assurance](QUALITY-ASSURANCE.en.md). It reads the selected book and
returns proposals in chat. It establishes no binding facts, changes no files
or approvals and starts no background analysis.

## Requests

- “Reconcile chapter 3 with our story memory.”
- “What new or changed facts appear in section 2.3?”
- “Check what the characters can know by the end of chapter 4.”

Use the book and scope specified in the request or an unambiguous current
selection; ask if the target is unclear. For “new/changed”, identify the comparison
version. Without an accessible earlier version, report observations and deviations
from existing references, not a version comparison. Do not include other books
or unrelated book branches without an appropriate assignment.

## Use existing sources

| Source in the selected book | Use and limit |
|---|---|
| `ghostwriter.yml` and confirmed project material | Book requirements, style, terms and explicit decisions; disclose missing confirmations |
| Complete affected manuscript sections and relevant neighboring text | Actual passages, progression and knowledge states; record text status and version |
| `characters/char-*.md` | Character attributes and relationships; preserve existing IDs and author statements |
| `story/places.yml` | Names, aliases and location descriptions with section references |
| `story/timeline.yml` | Events, original time expressions and chronology notes; book order is not automatically event order |
| Existing glossary and expressly accessible series references | Spelling and meanings; distinguish volume-specific and shared series material |
| Existing analysis runs | Leads to verifiable passages; recheck against current text when sources are stale or uncertain |

A file's presence does not prove author confirmation. Existing formats do not
store approval status or external verification for every claim. Report those
properties only when their origin is evidenced; invent no additional YAML fields.
Do not create missing material or introduce a parallel `kb/` knowledge base.

## Separate origin and authority

- **Text observation:** appears at the cited location in the reviewed version.
  Identify dialogue, conjecture, dreams, memories and unreliable narration as such;
  a character's claim is not an objective story fact.
- **Provisional:** a draft, open alternative or AI suggestion. Repetition does
  not automatically make it binding.
- **Author decision:** an explicitly confirmed decision with an available source.
  Do not infer it from a general “continue” or an unrelated approval.
- **Confirmed reference:** an evidenced binding requirement for the stated scope.
  Section approval and external verification remain separate properties.

These labels belong to the report, not new stored workflow states. An approved
text may contain unreliable statements. In nonfiction, even an author-confirmed
claim requires appropriate evidence to count as externally verified. A separate
assignment is needed for an external fact-check; disclose unresolved evidence.

## Read-only reconciliation

Read the complete selected scope and necessary references. Include an accessible
earlier version for an assigned version comparison. Name missing and unread
parts; do not claim a complete book review when material is incomplete.

Capture what matters for later sections:

- character attributes, state, location, relationships and knowledge;
- events with their actual time expressions, explicit flashbacks and possible
  chronology conflicts; do not turn vague time expressions into exact dates;
- locations, world rules, recurring objects and terminology;
- reveals, separating reader knowledge from each affected character's knowledge;
- nonfiction claims, definitions, figures and evidence questions;
- recurring continuity issues with evidence from the affected units.

Give comparison sources and locations for relevant observations. Classify
differences as **newly observed**, **changed**, **possible contradiction** or
**unclear**. A state change at a later time is not a contradiction. Omission does
not automatically revoke a previously established attribute. Matching names do
not establish identity; check aliases and existing IDs.

For conflicts, cite both sides and compare their scope and authority. Do not
invent transitions, motives or events, or silently overwrite material to resolve
them. Leave author decisions open when authority is uncertain.

## Report

Identify book, scope, current text version, comparison version and references
actually read. Present observations and conflicts compactly:

| Subject / existing ID | Observation and location | Comparison source | Origin / authority | Classification and unresolved decision |
|---|---|---|---|---|
| Fictional character `char-mara` | At the harbor in section 3.2 | At the station in section 3.1 | Two text observations | A location change, not itself a contradiction; query only if necessary travel time is missing |

Cite both versions for changes. Make brief quotations locatable using section
IDs and paragraphs. Consolidate recurring issues and refer to existing notes.
When none are found, say only “no deviation found within the material read”.
Classify unresolved issues using quality-assurance severity levels; mark
insufficient material **not fully reviewable**. The result changes no status
and grants no author approval.

When useful, suggest a **possible destination** for later maintenance, such as
character notes or the timeline. Proposal, author decision and file change remain
separate. Withdrawing a contradiction finding requires checked evidence rather
than a reassuring summary.

## Boundary with existing analysis

[Background analysis](DATA-MODEL.md#analyse-im-hintergrund-123) (German) already
supports characters, places, timeline and continuity. Its runs, caches and possible
API costs belong to that separate workflow. `analyze.py apply` can change book
files; applying `continuity` inserts selected manuscript markers. This read-only
reconciliation starts neither analysis nor application. A separate maintenance
or saving assignment must establish the concrete scope and permitted existing
write path. This guide implements no automatic application or persistent fact
history.

## Integration and limits

The repository skill `ghostwriter-buchgedaechtnis` loads this guide for a matching
request; assistants without native skills use repository instruction links.
Program updates distribute guide and skill. Actual activation and compliance
depend on the client. This is no global installation, persistent chat memory
or automatic monitoring after every chapter.

This independently written method draws ideas from
[story-memory](https://github.com/haowjy/creative-writing-skills/tree/main/skills/story-memory).
No external skill package was installed.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
