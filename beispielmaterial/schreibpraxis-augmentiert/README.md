# Augmentiert arbeiten / Augmented work

Folge der Serie Schreibpraxis. Deutsches Drehbuch: `drehbuch.md`, englische Übersetzung: `drehbuch.en.md`. Ausgangspunkt ist das ausschließlich simulierte Beispiel aus PR #243, Stand `0ba1236f7397f97aa6f6c63fd4330833f68540dc`. Die Lieferumfangsaussagen am Ende der Originalquelle beschreiben deren damaligen Planungsstand. Die HTML-Strecke wurde anschließend separat beauftragt und erstellt.

An episode of Writing practice. German script: `drehbuch.md`; English translation: `drehbuch.en.md`. Based on the entirely simulated example in PR #243 at `0ba1236f7397f97aa6f6c63fd4330833f68540dc`. Scope statements at the end of the original source describe its earlier planning status. The HTML walkthrough was commissioned and created separately afterwards.

```sh
python3 beispielmaterial/schreibpraxis-augmentiert/erzeugen.py --publish
```

Erzeugt beide Sprachen und bereitet ausschließlich statische freigegebene Dateien unter `website/augmentiert/` vor. Kein Upload. `ui_en.py` enthält die englischen Oberflächentexte. Die gemeinsame CSS-Grundlage und das Original-Logo stammen aus der ersten Schreibpraxis-Folge; besondere Darstellung dieser Folge steht in `folge.css`.

Generates both languages and prepares only approved static files in `website/augmentiert/`. No upload. English interface text is in `ui_en.py`. The shared CSS and original logo come from the first Writing practice episode; this episode’s specific layout is in `folge.css`.

Alle Situationen, Fragen, Antworten und Entwürfe sind Simulationen. Keine Anbieteraufrufe, private Buchdialoge oder Rangfolge von Modellen. Bei Änderungen fünf Fragerunden mit je drei Fragen und einer gemeinsamen Antwort, drei vollständige Entwürfe, menschliche Auswahl und redigierte Fassung in beiden Sprachen erhalten. Simulationshinweis auf jeder Seite unter dem Menü, Serienname ausschließlich unter GhostWriter, Folgentitel über dem Menü.

All situations, questions, answers and drafts are simulated. No provider calls, private book conversations or model rankings. Preserve five rounds with three questions and one shared answer each, three complete drafts, human selection and the edited text in both languages. Keep the simulation notice under the menu on every page, the series name only beneath GhostWriter and the episode title above the menu.

Pages manuell mit `documentation=true` veröffentlichen, damit die bestehende zentrale Dokumentation erhalten bleibt. Textlinks in beiden READMEs und HTML-Startseiten gemeinsam pflegen. Kein automatischer Upload, Merge oder Deploy durch den Erzeuger.

Publish Pages manually with `documentation=true` to retain the existing central documentation. Maintain the text links in both READMEs and website entry pages together. The generator never uploads, merges or deploys.

---
Entwickelt mit Unterstützung von Claude (Anthropic)
Entwickelt mit Unterstützung von Codex (OpenAI)

Developed with support from Claude (Anthropic)
Developed with support from Codex (OpenAI)
