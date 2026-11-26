# Images and visual references

[Deutsch](BILDER-UND-REFERENZBILDER.md) · English

**GhostWriter is not intended for photo books or picture-led collections. One scene corresponds to one section, with at most one media item per section.** [Media within a section](MEDIA-LAYOUT.en.md) specifies the six positions, text wrapping and percentage width slider. These new layout controls and the technical item limit are not implemented yet.

## Purpose and scope

This requirement applies to every GhostWriter book and book type. It extends the existing illustration feature (#54) with separate management of uploaded images that may serve as visual references in later generation assignments.

This specification describes intended product behavior. It does not claim the complete reference-image workflow is already implemented.

## Two separate roles

An image can have either or both roles:

- **Book image / illustration:** Intended for the manuscript or an edition.
- **Visual reference:** A model for a later generation assignment, such as preserving the appearance of a person, character, place, object, costume or recurring scene.

The roles are independent. Uploading a photograph does not automatically make it a book illustration or a generation reference. Existing illustration management and approval for book editions remain separate.

## Uploading later

Images must be uploadable at any point after a book project is set up, not only during initial setup.

The user can associate an image with:

- A person or character.
- A place.
- An object.
- A scene or situation.
- A chapter or section.
- The whole book project.
- Several suitable elements.

Multiple images can share an association. Existing images must be replaceable, supplemented, deactivated or reassigned without changing past assignments and their history.

## Metadata and approval

Record at least:

- Stable image ID and file path.
- Original filename.
- Associated project elements.
- Role(s): illustration, visual reference or both.
- Brief description of visible content and intended reference purpose.
- Origin, such as an original photograph, supplied file or licensed source.
- Known authorship, licensing and consent information.
- Upload time and status.

Visual references require separate, explicit decisions:

1. **Stored only:** Project material that is not used automatically.
2. **Approved as a reference:** May be offered for suitable assignments and used after selection.
3. **Deactivated / withdrawn:** Retained in history but excluded from new assignments.

Upload alone never grants approval. Images of people require particular attention to consent, usage rights and the purpose specified by the user.

## Use in generation

Before a suitable assignment, GhostWriter shows approved references associated with the selected project element. The user explicitly selects which references apply to that assignment.

1. Identify the assignment and project element, such as “portrait of character X” or “illustration for section 3.2”.
2. Show suitable approved references.
3. Let the user select them; association alone does not select an image.
4. Pass the selected references with the assignment to the image service or generation workflow, if supported.
5. Record the reference IDs actually used in the assignment log.
6. Review and explicitly approve the result before including it as a book illustration in the manuscript or edition.

**Handover through the “Bild erzeugen” action (#143):** `python3 scripts/image_service.py . services` shows each image service’s capability from `providers.yml` (`image_services`: image references yes/no, maximum, formats, size). `image_service.py plan --service google --references ref-img-…` checks what would go to the service (handed over, skipped with reason, mode) without sending anything. The “Bild erzeugen” action (`image.yml`, only with your own `GEMINI_API_KEY` secret and `consent`) actually sends the approved references as images to Google Gemini and writes `bild.jpg` and `handover.yml` per job under `quellen/bild-entwuerfe/` on the working branch: service, model, handed-over reference IDs with image version (SHA-256 of the file), skipped ones with reason; later changes to a reference never change the record. The result is a draft, not a book image. Today GhostWriter only hands over to Google Gemini (up to 3 images, PNG/JPEG, up to 7 MB each); for other services it states explicitly that nothing is handed over.

If the service does not support image references, say so clearly. Do not claim that an image was actually passed as a reference. A text description can be offered as a substitute, but must be identified as such.

## Reuse and traceability

- Approved references can be selected again in later assignments, including other chapters of the same book.
- Association with a character or project element makes an image discoverable; it does not activate automatic use.
- Each assignment records its particular selection. Changing an image file or approval status does not change past logs.
- The user must be able to select multiple references individually. GhostWriter must not silently prioritize conflicting or outdated references.
- Reference images do not automatically enter typesetting or a published edition.

## Researching images (#218)

The chat searches with its existing tools, or you provide a link yourself; GhostWriter adds no search or AI service of its own. Each find first becomes a **candidate** (`research/images/candidates.yml`, `scripts/image_research.py propose`) with title, image URL, source page, author, licence and assignment. No image file is stored at this point.

- **Rights:** A candidate counts as *clear* only with an author **and** a licence; otherwise it is *unclear*. “Clear” only means the details are present, not that they have been legally checked. GhostWriter never invents a permission to use.
- **Adopting:** Only after your explicit confirmation (`adopt <cand-id> --file … --confirm`) does the candidate become a **stored image** under `reference-images/` (status `stored`), with source, author and licence in its metadata. Without confirmation nothing changes. Unclear rights additionally need `--accept-unclear`, and the origin stays `unknown`. Size and original rules (D13) apply as for your own upload.
- **Book image:** A stored image is neither an approved reference nor a book image; both remain separate approvals in image management.
- **Rejecting:** `reject <cand-id>` records the candidate as rejected with a reason.

## Colorizing photos (#452)

Black-and-white family photos can be colorized without an image model changing faces or shapes. The model only supplies a color proposal. Only its color (channels a/b in Lab) is kept; lightness comes pixel by pixel from the prepared image. Procedure and locks: `START.md`, “Fotos colorieren (#452)”; files: [data model](DATA-MODEL.md#bildordner-und-colorieren-452). **Adding material (#574):** A material folder `quellen/<date>-<short name>/` can be colorized the same way (`python3 scripts/material.py . colorize <folder> …`): the source is `bearbeitet.jpg`, the description is in `material.yml`, the result is `coloriert.jpg`; minors and documents stay locked.

- **With your own Google Gemini access:** workflow “Bild colorieren” (`.github/workflows/colorize.yml`) with the secret `GEMINI_API_KEY`. The chat never reads the key; the workflow sends the image to Google and puts the result into the change package. Every start adds a job to the background queue (#479): ten photos in the evening all get colorized, one after another.
- **With another image service in the chat:** apply its proposal with `scripts/colorize.py --proposal`.
- **Locked:** images showing children or teenagers (`minderjaehrige` must be explicitly `false`) and documents (`art` only `foto` or `foto-vom-foto`). These are never sent to an external service.
- **Case-by-case exception:** an image showing children (`minderjaehrige: true`) can only be colorized with an explicit exception (`--minors-exception`, workflow input `minors_exception`) when the people shown or their family agree. `bild.yml` stays unchanged; the entry under `bearbeitung` records the exception. There is no exception for documents.
- **Known colors:** what is known for certain (e.g. “The flag is red-white-red.”) goes to Gemini as a hint (`--hint`, workflow input `hint`, at most 300 characters) and is recorded under `bearbeitung`. Without a hint the model guesses.
- **Checks:** same aspect ratio, same composition and a mean lightness deviation below 1/255; otherwise nothing is written.
- A colorized image is labelled “colorized later” in the book. The colors are an assumption, not evidence.

## Character image assistant (#540)

For character images the assistant guides you through image style, prompt and variants (skill `ghostwriter-figurenbild`, script `scripts/figurenbild.py`, data model under [Character images](DATA-MODEL.md#figurenbilder-540)). The project's **image style** (`images/stil.yml`) is separate from the narrative voice and is saved only after explicit confirmation. The **prompt** is built from the character profile, the author's wishes and the style; for each detail it says whether it comes from the profile, the author or the image design. Whatever the profile does not fix (such as hairstyle or clothing colour) stays an image suggestion and does not become a manuscript fact. A shared style does not mean identical clothing: `figurenbild.py pruefen` reports identical clothing across characters. Every variant is stored unchanged with the character (`characters/<id>/bilder/`) with its full prompt, tool and model (otherwise “unknown”) and a checksum; a change such as “clothing only” is a new variant with the source image as input. Such an image is **not a reference approval**; that stays a separate step (see above). The assistant uses the chat's image service; without one it outputs the complete request to copy. Graphical style cards and variant comparison follow as a widget; until then the text version applies.

## Relationship to the existing illustration feature

Feature #54 manages generated or supplied illustrations by section, including draft and approval status for editions. Reference management supplements it rather than replacing it.

Implementation must not simply treat every uploaded reference as an illustration or place it unchecked in `chapters/<chapter>/images/`. Durable storage and metadata must be coordinated with the existing data model. Existing images and `schemas/image.schema.json` must not become incompatible retroactively.

## Acceptance criteria

- [ ] Images can be uploaded later to any GhostWriter book.
- [ ] Images can be associated with people/characters, places, objects, scenes, chapters, sections or the whole project.
- [ ] Illustration and reference are separate roles; both may apply.
- [ ] Upload and association do not activate reference use.
- [ ] Reference approval and selection for a particular assignment require explicit user decisions.
- [ ] Generation receives only the references selected for that assignment.
- [ ] Unsupported reference transfer is made clear.
- [ ] The assignment log records the reference IDs used.
- [ ] Withdrawn references are excluded from new assignments while history is preserved.
- [ ] References do not enter a manuscript or edition without separate approval.
- [ ] The feature applies consistently across all books and is not tied to one project.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
