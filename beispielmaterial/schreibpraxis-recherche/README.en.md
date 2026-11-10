# Is that right? – Putting a claim to the test

[Deutsch](README.md)

A bilingual Writing practice episode. The German draft was first created locally on 10 November 2026; English, both overviews and publication were then explicitly requested. All dialogue, sample manuscript passages and book references are fictional. Only the linked expert source is real and has been read. No actual books were searched or changed.

## Sources and reproducible build

`inhalt.json` contains the German script, learning goal and simulation notice; `content.en.json` contains the matching English stages. German book titles and locations are retained. The translation of the fictional quotation is labelled. Keep text as plain text; the generator escapes HTML. Supported blocks: `message`, `result`, `note`, `table`, `link`. Check both languages and their correspondence after edits.

Use the shared [generator](../../scripts/build_research_writing_practice.py), central [episode template](../../templates/schreibpraxis/folge.html), shared stylesheet and original feather logo. The HTML and assets alongside this guide are the source preview; the website output is under `website/recherche/`. Do not edit generated files manually.

```sh
python3 scripts/build_research_writing_practice.py --publish
python3 scripts/build_writing_practice_index.py
python3 scripts/check_docs.py
python3 scripts/package_docs_site.py
```

Without `--publish`, only source previews are built. With it, website files are also prepared **locally**; nothing is uploaded or deployed. The shared generator builds both episodes in both languages. Both overview pages add text links and descriptions for the new episodes, keeping the three existing tiles. The logo links to the overview in the matching language, the episode title to its beginning, and the language switch to the corresponding stage.

[English](index.en.html) · [Deutsch](index.html) · [Overview](../../website/schreibpraxis.en.html)

## Expert source and limits

Swiss Seismological Service (SED) at ETH Zurich: [Can earthquakes be predicted?](https://www.seismo.ethz.ch/en/knowledge/faq/can-earthquakes-be-predicted/), also consulted in [German](https://www.seismo.ethz.ch/de/knowledge/faq/can-earthquakes-be-predicted/). Introduction and earthquake early warning section. Institutional expert information, not an original research study. No publication date displayed; read on 10 November 2026. Not a systematic literature review or an evaluation of particular warning systems.

See the shared [review note in German](../SCHREIBPRAXIS-RECHERCHE-ZITIEREN-PRUEFUNG.md). Dialogue and book references remain fictional after publication. The simulation does not demonstrate a search feature or provider performance. Before real use in a book, verify sources and the actual edition/location. Run Pages with `documentation=true` to retain the central documentation. Report publication only after confirmed deployment.

---
Developed with support from Claude (Anthropic)
Developed with support from Codex (OpenAI)
