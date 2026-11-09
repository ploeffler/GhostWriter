# Wiki appearance and build

The wiki shares the documentation website’s logo, page order, titles and source content. GitHub controls typography and the page frame; custom CSS is not included. Landing pages offer language links, a contents list and links to the searchable website. The shared sidebar lists both languages because GitHub provides a single global sidebar. Content pages display the program version. AI credits appear only in GitHub’s shared grey footer box: Claude followed immediately by Codex, once each in English. GitHub uses this shared footer on German pages as well. Small linked arrow symbols open Claude and Codex. Content pages and Home contain no additional AI footers. Readable file names supply visible page titles, such as “Einstellungen und Ausgabe” and “Settings and output”. Matching titles receive a language suffix. Language switches, sidebar and internal links use these names. Publication replaces technical page identifiers such as en-settings; old external wiki links may need updating.

```sh
python3 scripts/build_docs_wiki.py
python3 scripts/build_docs_wiki.py --check
```

Dependencies: `scripts/docsite/requirements.txt`. Output: `build/documentation-wiki/`, generated exclusively from the public selection in `docs/site.json`. Do not edit generated pages. Existing outlook files under `wiki/` remain intact. Rebuild after source changes. `build-info.json` records source hashes and the version; exclude it and the marker file from wiki publication.

Markdown files contain GitHub-compatible HTML for tables and images, plus explicit anchors. Images reference the same public files in the main repository; new assets must exist there before wiki publication. Internal planning links are removed using the website’s policy; unknown relative links stop the build.

Before publication, inspect both languages in the actual GitHub wiki: logo in light/dark appearance, narrow screens, tables, images, anchors, language links, sidebar and footer. Local structural checks do not replace visual review. Browser access requires explicit permission. This build does not upload, activate a wiki or delete existing public pages. Compare existing pages before any separately authorized upload.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
