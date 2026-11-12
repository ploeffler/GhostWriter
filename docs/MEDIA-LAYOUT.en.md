# Media within a section

[Deutsch](MEDIENPLATZIERUNG.md) · English

**GhostWriter is intended for text-led books, not photo books or picture-led collections. One scene corresponds to one section; each section contains at most one media item, such as an illustration or a diagram.**

## Confirmed requirements

The following requirements were confirmed on 8 November 2026. They describe the intended product behaviour. The one-item limit is implemented; positioning with text wrapping and width slider have not yet been implemented.

### One media item per section

A section represents one scene and may contain no media or exactly one media item. Create a separate section for another scene with another media item. Inserting the same image more than once still counts as multiple placements and exceeds the limit.

Stored alternatives and reference-only images are not manuscript placements. Reference approval, selection for an individual generation request and approval for book publication remain separate decisions. See [images and visual references](IMAGES-AND-REFERENCES.en.md).

**To show a standalone media item before or after a text section:** Create a separate section containing only that image or diagram, and place it immediately before or after the relevant text section in the outline. It remains a separate section with at most one media item; image and section approvals still apply.

### Position and text wrapping

The media item sits **within the section text, with text wrapping**, rather than in a separate photo-book page layout. Six positions are available in the intended design:

| Vertical | Left | Centre | Right |
|---|---|---|---|
| Top | top left | top centre | top right |
| Bottom | bottom left | bottom centre | bottom right |

Position refers to the section. Fixed placement at the top or bottom page margin was not requested. Text wrapping at the chosen size and position must be tested in the supported output formats.

### Size as a percentage of page width

A **slider with a percentage display** adjusts the item's width relative to the usable page width inside the margins. Height scales proportionally, preserving the aspect ratio. For a reflowable e-book, the equivalent reference is the usable reading width.

Position and width jointly determine text wrapping. Insufficient print resolution and unreadable diagram labels must be reported. Choosing a layout size neither grants image approval nor replaces explicit confirmation where stored image files need resizing. Layout size and the original file are different things.

## Findings from the local acceptance test

| Part | Actual state |
|---|---|
| Illustration and reference image | Import, selection, reference logging and approval gates exist. |
| Labelled diagram | Can be created separately and imported as PNG; the general image prompt currently forbids text. |
| At most one media item | Implemented: project validation (`validate_project.py`) and output (proof, edition) report more than one media item in a section and an image inserted more than once as errors. Variants that are not inserted and reference images do not count. |
| Position and text wrapping | Not implemented; images currently use the full text width. |
| Width slider | No control in the image form yet; output uses a fixed `width=100%`. |
| Media-only section in PDF | Content is exported, but heading and image can separate across pages. Draft warnings can also detach from their images. |
| Alternative text | Stored, but DOCX and EPUB currently receive the caption rather than the full alternative description. |

Before implementation is complete, test all six positions, size changes, page breaks and text wrapping in PDF, DOCX and EPUB. Unsupported settings must be reported. Successful saving alone does not demonstrate correct placement.

[Book lifecycle](BOOK-LIFECYCLE.en.md) · [Creation cycle](CREATION-CYCLE.en.md) · [Saving and approving](SAVING.en.md)

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
