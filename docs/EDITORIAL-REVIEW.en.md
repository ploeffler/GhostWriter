# Editorial review: three review types

[Deutsch](LEKTORAT.md) · English

These review types are focused chat assignments. They extend
[quality assurance](QUALITY-ASSURANCE.en.md); its scope, correction loop,
severity levels and approval rules remain binding. They are not automated
program runs and require no additional AI service.

## Choose a review type

| Review type | Main question | Example |
|---|---|---|
| Structural review | Does the structure support the intended experience or argument? | “Structural review of chapter 3.” |
| Language review | Is the text clear and faithful to the agreed voice? | “Language review of section 2.3.” |
| Proofreading | What spelling, punctuation and consistency errors remain? | “Proofread chapter 4.” |

Understand equivalent requests such as “Check chapter 3 for structure and
pacing.” Proceed when the requested type is clear. For a general editorial
request, suggest the appropriate type based on the draft's stage; ask only
when a consequential ambiguity remains. When several types are requested,
review structure, then language, then proofread. Do not turn an explicit
proofreading request into an unsolicited structural revision.

## Shared assignment

- Record the book, complete affected unit, review type and identifiable text
  version. Read the book profile, confirmed facts, style and relevant neighboring
  text. Disclose missing prerequisites; do not invent facts or approvals.
  Chapter revision must also satisfy the existing
  [availability check](../START.md#8-start-des-laufenden-schreibbetriebs) (German).
- Read the complete relevant text before judging it. Explicitly exclude
  unavailable or unread material, including material omitted because of size.
  Do not describe a partial review as a complete chapter or book review.
- Make findings locatable through chapter/section identifiers, paragraphs or
  brief excerpts. Distinguish problem, impact and possible direction of change.
  Mark uncertainty as a query and respect intentional project choices.
- A review request initially produces a diagnosis in chat. It does not authorize
  manuscript, profile or status changes or uploads. Perform corrections already
  expressly requested within their authorized scope, then reread the complete
  affected context. Persist reports only in the permitted book storage under a
  saving assignment; keep book data out of product documentation.

## Structural review

Work from the overall purpose down to chapter and section functions. Prioritize
major issues; defer sentence polish where structural changes are needed.

**Narrative books:** Review the reader promise, causality, motivation, character
arcs, chronology and knowledge states. Do scenes serve the agreed purpose?
Are setup and payoff connected? Check pacing, transitions and information
flow. Quiet scenes do not require artificial escalation.

**Nonfiction:** Review the main question, audience, argument, introduction of
terms, prerequisites, evidence, counterarguments and conclusions. Chapters
should advance understanding; do not force dramatic conflict. A manuscript
statement is not verified evidence. Flag source questions; a full external
fact-check is a separate assignment.

Suggest cuts, moves, splits, combinations or additions as justified directions.
Do not present new events, claims or structural choices as settled decisions.

## Language review

First understand the agreed voice from the book profile and available confirmed
style samples. Review clarity, references, perspective, tense, register, rhythm,
word choice, imagery, dialogue, repetition and over-explanation. For nonfiction,
pay particular attention to terminology and understandable reasoning.

Describe recurring patterns using representative locations; a single instance
does not establish a book-wide pattern. Do not automatically normalize deliberate
fragments, dialect, repetition, ambiguity or unusual rhythm. Do not replace
missing style requirements with personal preferences. Query changes that may
alter meaning.

## Proofreading

Read the complete text slowly and linearly against agreed language and spelling
conventions: spelling, grammar, punctuation, missing or duplicated words, names,
numbers, variants, references, headings, paragraph/scene markers and remnants
left by revisions. Follow the project's language variety, including German,
Austrian and Swiss conventions where relevant; do not impose English rules.

Locate individual errors. Group recurring errors and identify their scope.
Report larger structural or voice problems separately without silently rewriting
them. They can still prevent a positive overall result. Without a rendered
output, do not claim to have checked page breaks, hyphenation, type area or
print layout.

## Report and result

Use the existing [review report](QUALITY-ASSURANCE.en.md#review-result), adding
the review type and a short prioritized editorial assessment:

1. Book, text version, review type, scope and references actually read.
2. Brief overall assessment; identify strengths worth preserving when useful.
3. Findings with location, severity, rationale and direction of change.
4. Recommended revision order, unresolved author decisions and corrections
   already authorized and actually performed, clearly distinguished.
5. Result with limits: **passed**, **passed with notes** or **not passed**.
   If material is insufficient, state **not fully reviewable** and identify
   missing parts; do not claim a positive result.

The result applies only to the named review type and version. Passing
proofreading does not establish a structural review. Unresolved blocking or
significant issues prevent a positive result under quality assurance.
No report automatically grants author approval or changes status.

When the report is stored in `editorial/` as part of a save request, record the
run in the check log in the same commit (#331):
`python3 scripts/checks.py record <book> --kind structure|language|proofreading
--scope <book|chapter ID|section ID> --result passed|passed_with_notes|failed|incomplete
--report editorial/<report>.md --notes <n>`. The project overview, chapter view and section
form then show the run as a tag; if the text changes afterwards, the tag reads
“changed since check”. The entry is not an approval.
Always pass `--notes`: the number of open notes in the report, i.e. findings not
yet applied or decided (0 if none are open). The project overview shows it per
chapter (#362). If one report covers several check types, each of these entries
carries the same total of the report; the overview counts the report only once,
using its newest entry (#437). A later fix only shows up with the next entry.

## Reviewing notes (notes review, #367)

So that open notes can be reviewed later without parsing free text, the
assistant stores a saved report's findings as `editorial/<report>.yml` as well
(schema `schemas/findings.schema.json`): per finding `id` (`b-001`), `abschnitt`
(section ID; for front and back matter the part's ID, e.g. `mat-nachwort`; for
book-wide findings `book`, #423), optional `absatz`, `schweregrad`, `art`, `befund`, `richtung`,
for language findings `alt` (exact wording) and `neu` (proposal), optional
`frage`, and `status` (`offen`, `erledigt`, `entschieden`). `--notes` in the check
log is the number of findings with `status: offen`.

On request (“review notes”, “notes review”),
`python3 scripts/hinweise.py collect <book> [--chapter <chapter-id> …]` gathers
all open findings in `editorial/durchsicht-<date>.yml`. If the review for that day
already exists, it stops instead of overwriting it (#438): `--merge` appends new
findings and leaves existing entries and their decisions unchanged, `--new` creates
`durchsicht-<date>-2.yml` (schema
`schemas/notes-review.schema.json`), split into **without the author** (`ohne_autor`)
and **author decision** (`autorenentscheidung`):

- Only a purely linguistic finding with a proposal can be solved without the
  author. It must not add a new fact, judgement or change of tone; when in
  doubt it becomes an author decision.
- Everything else is an author decision with `frage` and `art` (`fakt`,
  `kontinuitaet`, `ton`, `aufbau`, `buchweit`). All values for `art`:
  `rechtschreibung`, `zeichensetzung`, `grammatik`, `wiederholung`, `satzbau`,
  `sprache`, `fakt`, `kontinuitaet`, `ton`, `aufbau`, `buchweit`.
- Findings on front and back matter are listed under the part's title instead of
  a chapter. Book-wide findings (`abschnitt: book`) are always author decisions;
  `apply` does not apply them itself but reports them for manual work. With
  `--chapter` both are left out.
- `alt` must occur exactly once in today's manuscript; otherwise the finding is
  left out and listed under `ausgelassen` with the reason.
- Each entry carries the sentence with up to two sentences before and after
  (`kontext`), chapter and section details and `entscheidung: offen`.

`hinweise.py show <book> [--open]` shows the dialogue chapter by chapter.
Each answer is stored with
`hinweise.py decide <book> <entry> --decision ja|nein|geändert [--new …]` and
uploaded without asking as a small addition to the open change package
([Saving](SAVING.en.md#reviewing-notes)), so a later session can continue.

Decisions are applied at the end of a chapter or on request. First,
`hinweise.py plan <book> [--chapter …]` marks each decided entry ✅ applicable,
⚠️ manual (no old wording or proposal) or ⛔ (section or chapter finalized,
wording no longer unique). The assistant never reopens anything by itself:
reopening is a separate, explicitly confirmed approval (`START.md`).
`hinweise.py apply <book> [--chapter …]` applies only the ✅ entries, marks them
`umgesetzt: true` and writes the status back (`erledigt` when applied,
`entschieden` for “no”), so they do not come back on the next `collect`. The
assistant then rereads every changed sentence in context, records a follow-up
check for the affected chapters (proofreading and quality, with `--notes`) and
asks separately about finalizing again. Saving and merging work as for other
book changes.

In the chat, `render_view.py notes-review` shows the dialogue as a widget (template `hinweisdurchsicht`, UI 0.58.0 and later) with “Accept”, “Do not change” and “Rephrase” per entry and “Check what can be applied”; `--text` gives the text version.

## Many chapters: sub-agent (#392)

A review across several chapters is read by a sub-agent where the app supports
it (e.g. Claude Code). It receives the shared assignment and scope and returns
only findings with locations; the assistant writes report and findings file as
usual. Without sub-agents, work chapter by chapter and keep only the findings in
the chat ([Saving tokens](CHAT-APPS.en.md#saving-tokens-during-a-chat-392)).

### Model choice for sub-agents (#418)

Without a setting, a sub-agent inherits the main session's model, even for
purely mechanical work. Recommendation per review kind, using neutral classes
instead of product names:

| Review kind | Key | Class | Claude |
|---|---|---|---|
| Proofreading, mechanical language fixes, re-checks | `proofreading` | `small` | haiku |
| Extracting places, characters, timeline from the text | `extraction` | `small` | haiku |
| Language review (voice, rhythm) | `language` | `medium` | sonnet |
| Story memory, continuity | `continuity` | `medium` | sonnet |
| Structural review | `structure` | `large` | opus |
| New scenes, text suggestions in the narrative voice | `writing` | `large` | opus |

To change this permanently, set it in the assistant profile (`assistant.yml`,
command `Profile`), for example:

```yaml
subagent_models:
  language: large      # voice is delicate here
```

Missing review kinds follow the table. When starting sub-agents, the assistant
says in one sentence which class runs what (“proofreading with Haiku,
structural review with Opus”). In Claude Code the class is passed as the
agent's model. In Codex each class corresponds to its own agent under
`.codex/agents/`, for example `.codex/agents/proofreading.toml` with
`model = "<small model>"` and a short description; `AGENTS.md` points to this
table for delegation. Apps without per-agent model choice use the main model;
the assistant then says so in one sentence.

## Integration and limits

This guide and its German counterpart are the shared subject-matter source.
The short repository skill `ghostwriter-lektorat` points here. Assistants without
native skills load the guide through repository instructions or an explicit
request. Program updates distribute these files; no global skill installation
is required. Automatic selection, file access and actual compliance depend on
the client and are not established merely by these instructions being present.

These instructions are independently written for GhostWriter. The reviewed
[story-review resources](https://github.com/haowjy/creative-writing-skills/tree/main/skills/story-review)
provided methodological ideas for separating review levels and prioritizing
findings; no external skill package was installed.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
