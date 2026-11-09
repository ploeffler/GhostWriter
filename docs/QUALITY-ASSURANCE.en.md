# Quality assurance for books

[Deutsch](QUALITAETSSICHERUNG.md) · English

## Purpose

This guide defines a repeatable editorial review for every GhostWriter book, regardless of genre, narrative perspective, language, length or AI provider.

Review supports the author. It replaces neither the author's content decisions nor their explicit approval.

## Basic rules

1. **Follow project requirements.** Read the general GhostWriter rules and the individual book profile before reviewing. Book-specific facts, characters, style, terms and continuity rules must come exclusively from approved project material.
2. **Do not invent missing information.** Mark gaps as open questions or uncertainty. Do not add unsupported facts, sources, character biographies, motives or events unless creative additions were expressly requested.
3. **Review the full context.** Never assess only the diff, new sentences or isolated corrections.
4. **Keep changes traceable.** Record problems, corrections, open points and the review result.
5. **Never approve automatically.** A positive review is a recommendation. Formal approval remains the author's explicit decision.

## Review scope

### Section review

For every newly written or revised section:

- Read the entire section from beginning to end.
- Check logical consistency, internal chronology and transitions.
- Check whether actions, processes, places, dates and relationships are plausible.
- Look for conflicts with established facts and earlier sections.
- Identify repetition, unnecessary duplication and unintended restatement.
- Compare character voices, perspective, tense, tone and phrasing against project requirements.
- Check grammar, spelling, punctuation and clarity.
- Explicitly mark unresolved factual and source questions.

### Chapter review

When changes affect more than one section, or a chapter is ready for assembly or approval:

- Read the entire chapter in its intended order.
- Check transitions between every section.
- Compare chronology, character development, what characters know, changes of location and recurring motifs.
- Look across the whole chapter for contradictions, repetition, gaps and unintended duplication.
- Check that all sections follow the agreed style and project rules.
- Ensure that changes do not silently undermine already approved content.

### Review across the book

For major changes to plot, characters, narrative perspective, time structure or central facts:

- Reread affected chapters and relevant neighboring chapters.
- Check continuity across the book.
- Use the project profile and binding fact/character material as references.
- Perform a complete linear final reading of the manuscript when needed.

## New material and reconciling findings

For anecdotes, notes, sources and findings supplied later, follow
[Integrating new material and catching up](NACHZIEHEN.md) (German). Compare all
sections within the selected scope, then review the complete affected context
after integrating the material. Analysis alone does not complete a revision.

## Correction loop

1. Record the review scope and the text version being reviewed.
2. Read the complete relevant text.
3. Classify findings by severity:
   - **Blocking:** A contradiction, implausible process, unsupported material factual claim, unclear action or violation of a binding project requirement.
   - **Major:** A clear style deviation, continuity problem, distracting repetition or language problem affecting understanding.
   - **Note:** An optional improvement without a factual or narrative error.
4. Propose corrections, or make them if expressly authorized.
5. Reread the entire affected section after corrections.
6. Repeat the broader review when chapter or book context is affected.
7. Record unresolved points with reasons and a specific question.

## Review result

Each documented review includes at least:

- Book/project and affected chapters or sections.
- Reviewed text version or commit.
- Review scope.
- Findings by severity.
- Corrections made or proposed.
- Remaining open points.
- Result: **passed**, **passed with notes** or **failed**.

A section or chapter must not be described as having passed editorial review while unresolved blocking or major issues remain. Passing review does not automatically grant formal GhostWriter approval.

## Individual book profile

General rules apply to every book. Each book also needs its own versioned project profile, recording its individual requirements, for example:

- Genre, audience and intended effect.
- Narrative perspective, tense and basic tone.
- Style features and deliberately avoided techniques.
- Binding facts and character/location information.
- Chronology, continuity rules and recurring motifs.
- Spelling, terminology and project conventions.
- Creative freedom and boundaries for additions.

The author must confirm the profile. Changes must be traceable. It can strengthen general GhostWriter safety and quality rules, but cannot weaken them.

The profile contains only information belonging to its book. It belongs in the book repository and must not be copied into global GhostWriter product documentation or other book projects.

## Images and visual references

Images can be added at any point, including after text or characters have been created. Image management is part of the book material and must remain traceable separately from the manuscript.

### Adding images later

- Authors can upload image files later and associate them with the relevant book, chapter, section, place or person.
- A person or other recurring element should be addressable across the project, so an image is not tied to only one passage.
- Record known origin/creator, image type (author-provided, AI-generated or external), description, usage and rights information.
- Uploaded images expressly accepted by the author are saved as project material. An image merely displayed or found in chat is not yet durably accepted.
- External images may be accepted and used only in accordance with usage rights and license terms.

### Images as generation references

- For each suitable image, the user explicitly chooses whether it is only a book illustration or also a visual reference for generation.
- A reference can describe a character's appearance, clothing, an object, a location, a mood or a recurring visual style.
- The generation workflow must show which references are considered for a particular generation or revision. References are associated with that assignment or step.
- Reference use is optional and is not activated by upload. The user may enable, change or withdraw it.
- References provide visual guidance; they must not be treated as unchecked evidence of narrative or historical facts.
- With multiple references, specify which properties should come from each one. Identify conflicts before generation.
- For images of people, pay particular attention to rights, consent and the user's intended use.

### Image review

Before publication or a book edition, check:

- Is the image durably saved and correctly associated with the project?
- Are origin, creator and rights/license status documented or marked as unresolved?
- Is its role clear: illustration, generation reference or both?
- Were the intended references actually used in the generation step?
- Does the result follow binding character, location and style requirements?

## Process improvement and responsibilities

GhostWriter also assigns new requirements and possible improvements to the appropriate project level.

### Responsibilities

- **Book repository:** Individual content and rules, such as characters, plot, places, chronology, style, research findings and open manuscript questions.
- **Main GhostWriter repository:** Reusable rules and procedures, such as research/writing phases, quality assurance, approvals, book profiles and general assistant instructions.
- **Technical product requirement:** Features, data models, interfaces, automations, scripts or GitHub Actions. Record these in the main repository instead of making spontaneous product-code changes in a book project.

### Procedure

1. Classify requirements and recurring procedures as book-specific, generally reusable or technical.
2. State the recommended location with a short reason.
3. Check existing rules and open issues for overlap.
4. Generalize findings before transferring them into GhostWriter. Do not transfer book content, character facts or confidential project data into central documentation.
5. Change central rules, workflows or technical components only with the user's explicit consent.

GhostWriter should actively identify, classify and propose improvements. It must not adopt them into central rules or technical procedures on its own. Code changes are not part of an editorial book task. The user decides whether to adopt and implement them.

## Clear chat output and response mode

GhostWriter defaults to **simple mode**. Chat output is for authors rather than Git or software developers.

In simple mode:

- Summarize results briefly in everyday language.
- Avoid terms such as branch, commit, SHA, merge, pull request or issue unless needed for the user's decision.
- Explain what technical actions mean: “Changes are saved”, “Please review and confirm this version” or “Application is still pending”.
- Include only the information needed for the next step.
- Still state material limitations, missing permissions, errors and pending approvals. Simplification must not hide them.

The user can change response mode at any time:

- **“Extended answers on”** or **“Debugger mode on”**: Show technical detail, repository/file paths, branches, commits, validation messages, causes and status more fully.
- **“Extended answers off”**, **“Debugger mode off”** or **“Simple mode”**: Return to concise, everyday explanations.

The selected mode lasts for the current chat until changed. Do not claim it has been saved permanently unless an explicitly available project setting is used.

## Display modes

Display mode is independent of simple or extended answers. It controls how the current chat client presents information.

### ChatGPT

Use suitable native presentation elements when the client supports them and they add value:

- Cards or clearly separated areas for a book, chapter, section or result.
- Tables for comparisons, lists and status overviews.
- Status indicators and progress displays.
- Charts for quantities, costs and trends.
- Images when requested or useful for understanding.
- Interactive controls when a real choice or action is required.

Keep the presentation calm, consistent and functional. Avoid decoration without information, overcrowded views and controls without real functionality. Do not assume Claude-specific widgets or HTML automatically work in ChatGPT. Fall back to clear text and Markdown when unsupported.

### Claude and other clients

Claude uses the GhostWriter widget according to the presentation instructions. Other clients use what they support; when support is uncertain, text is the reliable fallback. English defaults to native text as described in the [interface guide](INTERFACES.en.md).

### Switching in chat

The user may select:

- **“Display: simple”** — concise text with minimal structure.
- **“Display: organized”** — a structured view with suitable cards, tables and status indicators.
- **“Display: extended”** — detailed structured views, with extra charts or interactive elements when useful and supported.
- **“Text only”** — text and Markdown only.

The selection lasts for the current chat until changed. Do not present it as a saved project preference unless the corresponding feature exists.

## Scope and limitations

This guide describes the intended editorial behavior. It does not claim all checks are already automated. AI reviews can miss errors or produce incorrect findings; reliable sources and the author's decision govern disputed facts.


### Shared organized display: Claude, ChatGPT and Gemini

Default to “Display: organized” unless the user selected simple, extended or Text only. Display choice and answer detail remain independent. Keep a compact title and metadata area, followed by a ten-segment approval bar and exact approved/total section counts. With no sections, show 0 of 0 and no filled bar. Count other non-planned sections separately as in progress; the bar measures section approvals only, never publication readiness.

Highlight open marker counts and preserve all warnings, pending changes and approval requirements. Offer one valid navigation shortcut: the current unapproved section, otherwise the first unapproved section, or creation for an empty outline. Keep the complete actions available below. Opening a section grants no approval. Use status words alongside symbols; never invent buttons, commands or missing data.

Claude (Anthropic) uses existing GhostWriter widgets when supported by the actual client, with Markdown as fallback. The external widget templates are maintained separately; this rule does not claim their HTML has changed. ChatGPT (OpenAI) uses organized Markdown plus native elements only when actually supported. Gemini (Google) explicitly receives the same Markdown foundation, with additional native elements only when client support is confirmed. Provider or API availability alone does not establish display capabilities.

Book and chapter text views calculate the summary from section files. The library adds the same bar to its existing approval counts. German and English share the calculation. Rendering does not change book files.

## Focused choice questions in conversation

Use short choice questions more often at useful decision points, particularly for a book's direction, audience, viewpoint, style, working method and next step. Do not turn every message into a choice card: storytelling, research, clarification and collaborative revision remain natural conversation.

- Ask one concrete question, usually with two to four distinct, understandable options. Offer a brief recommendation when useful and respect the limits of the available question tool.
- Always allow a custom answer, either in the supported element or freely in the chat. Users should not have to force their idea into a listed option.
- Use supported native question elements or existing GhostWriter choice cards. Fall back to readable text when unavailable; never simulate nonfunctional buttons.
- Do not repeat answered questions. Group related questions only when this makes the decision easier. Avoid frequent minor interruptions and long click-through sequences.
- A proposed or preselected option is not a decision. Silence is not consent. A style choice does not replace writing/content approval or a separate request to save, accept changes or publish.

Example: “How would you like to develop chapter 1?” — “Bring my own text”, “Work scene by scene together” or “Discuss a complete chapter draft”, with room for a custom answer. Choosing clarifies the working method; it does not automatically start drafting or saving.


---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
