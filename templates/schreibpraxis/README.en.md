# Writing practice – templates and build guide

[Deutsch](README.md)

These templates are a starting point for new Writing practice episodes. Existing episodes already have their own versioned sources and generators; this package does not automatically rebuild them. The base stylesheet comes from the first episode with overview and navigation elements added. Editing it does not change previously generated pages.

## Files

| File | Purpose |
| --- | --- |
| `folge.html` | One stage of a walkthrough |
| `uebersicht.html` | Overview containing episode tiles |
| `kachel.html` | One fully clickable tile |
| `grundstil.css` | Colours, typography, logo header, dialogue, menu, progress, tiles and narrow layouts |
| `auftrag.de.md` / `brief.en.md` | Reusable brief for a new episode |

HTML files contain placeholders and are not finished pages. Fill them with Python’s `string.Template.substitute`; missing or unknown fields should stop the build. Escape text values with `html.escape` before substitution. Only insert generated HTML into fields ending in `_HTML`. `$ILLUSTRATION_SVG` is an inspected illustration designed in the repository. Supply progress as a number from 0 to 100.

```python
from pathlib import Path
from string import Template

template = Template(Path('templates/schreibpraxis/folge.html').read_text())
# values contains every field below, with text values already HTML-escaped.
page = template.substitute(values)
```

## Required design and navigation

- Original feather logo from `assets/logo.svg`. Orange `#f07f2e`, darker readable accent `#b9551d`, warm light background, serif headings and system fonts for other text.
- The series name appears visibly only beneath GhostWriter: “Schreibpraxis” in German, “Writing practice” in English. The episode title sits above the stage menu.
- **An episode’s logo and header text lead to the overview in the matching language.** The episode title in the menu leads to its opening. The overview logo leads to the GhostWriter homepage.
- Previous/next navigation, one active stage and language switching to the matching stage. An episode opening is not a substitute for the overview link.
- Entirely simulated episodes have a clear notice directly below the menu on every page. Mark partly invented dialogues at their location. Distinguish actual events, abstracted content and simulations; invented conversations say nothing about provider performance.
- Make the whole tile clickable, order tiles deliberately and provide a short description and evidence label. Book development currently comes first. READMEs and HTML homepages link to the overview as text, without an additional main tile.
- Responsive and usable without external fonts or JavaScript. One Claude credit followed by one Codex credit in the page language.

## Fields

Shared: `LANG`, `PAGE_TITLE`, `STYLE_URL`, `LOGO_URL`, `OTHER_LANG`, `OTHER_URL`, `OTHER_LABEL`, `SERIES_LABEL`, `NAV_LABEL`, `CLAUDE_CREDIT`, `CODEX_CREDIT`.

Episode: `OVERVIEW_URL`, `OVERVIEW_LABEL`, `EPISODE_URL`, `EPISODE_TITLE`, `PAGE_POSITION`, `PAGE_COUNT`, `NAV_ITEMS_HTML`, `SIMULATION_NOTICE_HTML`, `STAGE_LABEL`, `LEAD`, `CONTENT_HTML`, `PROGRESS_PERCENT`, `PREVIOUS_LINK_HTML`, `NEXT_LINK_HTML`.

Overview: `HOME_URL`, `HOME_LABEL`, `LEAD`, `TILES_HTML`. Tile: `EPISODE_URL`, `ILLUSTRATION_SVG`, `EVIDENCE_LABEL`, `EPISODE_TITLE`, `DESCRIPTION`, `OPEN_LABEL`.

`NAV_ITEMS_HTML` contains list items with exactly one `aria-current="page"` link. `SIMULATION_NOTICE_HTML` can use `<aside class="simulation"><strong>Entirely simulated dialogue</strong>…</aside>`; leave it empty only for a non-simulated episode, explaining the actual provenance appropriately. `CONTENT_HTML` may use `.message` with visible role labels, `.message.author` for author replies, and `.result` for summaries. Use an empty element when no previous page exists; the final next link returns to the opening. Both languages cover the same stages.

## Existing sources and repeatable builds

| Output | Source / command from repository root |
| --- | --- |
| Overview | `python3 scripts/build_writing_practice_index.py` |
| From conversation to your own text | `python3 beispielmaterial/schreiben-mit-ghostwriter/erzeugen.py --publish` |
| Augmented work | `python3 beispielmaterial/schreibpraxis-augmentiert/erzeugen.py --publish` |
| An idea becomes a crime novel | `python3 beispielmaterial/schreibpraxis-buchentwicklung/erzeugen.py --publish` |
| Series rules, German | [SCHREIBPRAXIS-SERIE.md](../../beispielmaterial/SCHREIBPRAXIS-SERIE.md) |

Generators produce both languages. Scripts, content, translations and episode-specific CSS live in each source directory. `--publish` only prepares local files under `website/`; it never uploads or deploys. Markdown and HTML-checking dependencies are in `scripts/docsite/requirements.txt`.

## Deliver and verify a new episode

1. Define purpose, title, provenance and a few main stages. Develop the story first; derive questions from answers and show the person’s decisions.
2. Keep sources and a generator under `beispielmaterial/`. Maintain German and English together. Do not publish private original conversations.
3. Generate `website/<episode>/`. Add the source and tile to both overview languages. Relative paths differ between source previews and public output; check both.
4. Compare all dialogue and results with the source. Check links, language switching, active navigation, logo target, simulation notice, tile order and credits. Rebuilding must produce identical files.
5. Run `python3 scripts/check_docs.py`, `python3 scripts/package_docs_site.py` and `git diff --check`. Report results before transfer. Where authorised, inspect narrow layouts and keyboard use; disclose missing visual acceptance.
6. Transfer only explicitly requested files. Upload, merge and publication require authorisation unless already covered by the current request. Set `documentation=true` when manually dispatching Pages to retain central documentation. Verify availability and actual link targets after deployment.

---
Developed with support from Claude (Anthropic)
Developed with support from Codex (OpenAI)
