---
name: ghostwriter-lektorat
description: Strukturlektorat, Sprachlektorat, Schlusskorrektur oder Rundumprüfung eines Kapitels in einem vorhandenen GhostWriter-Manuskript; auch structural review, language review, proofreading und full chapter check. Für gezielte redaktionelle Prüfaufträge, nicht für Software-Reviews oder neue Manuskriptentwürfe.
---

# GhostWriter-Lektorat

Arbeite im ausgewählten Buch nach dessen Repository-Regeln und bestätigtem
Buchprofil. Bestimme die beauftragte Prüfart und den vollständigen Prüfumfang.

Lade die gemeinsame Anleitung in der Bediensprache aus dem Buchrepo. Fehlt sie dort, nutze die Fassung im GhostWriter-Hauptrepo:
[Deutsch](https://github.com/ploeffler/GhostWriter/blob/main/docs/LEKTORAT.md) oder
[English](https://github.com/ploeffler/GhostWriter/blob/main/docs/EDITORIAL-REVIEW.en.md).
Die dort verlinkte Qualitätssicherung bleibt verbindlich. Ohne Zugriff auf die
benötigten Texte keine vollständige Prüfung behaupten.

Liefere belegte, priorisierte Befunde für genau die beauftragte Prüfart und
Textfassung. Ein Prüfauftrag allein autorisiert keine Manuskriptkorrekturen,
Profil- oder Statusänderungen, Speicherung oder Veröffentlichung. Bereits
explizit beauftragte Korrekturen bleiben innerhalb ihres erlaubten Umfangs möglich.
Eine bestandene Prüfung ersetzt keine Autorenfreigabe.
**Rundumprüfung (#447):** „Rundumprüfung Kapitel N“ bzw. „Kapitel N komplett
prüfen“ folgt dem gleichnamigen Abschnitt der Anleitung. Nur dieser Auftrag
schließt das Beheben der `hinweise.py`-Einträge unter „Ohne Autor lösbar“ ein,
sonst nichts. Abgeschlossene Abschnitte (`approvals.section: true`) werden nie
geändert; keine Freigabe, kein Übernehmen ohne ausdrückliche Bestätigung.
Wird ein Bericht gespeichert, den Lauf mit `scripts/checks.py record` ins
Prüfprotokoll `editorial/checks.yml` eintragen (#331); daraus entstehen die
Prüf-Tags in den Ansichten. Dabei immer `--notes <n>` mitgeben: Zahl der offenen
Hinweise im Bericht, 0 wenn keine offen sind (#362, Anzeige in der Projektübersicht).
Die Befunde zusätzlich als `editorial/<bericht>.yml` ablegen (#367); „Hinweise durchsehen“
läuft über `scripts/hinweise.py` (Abschnitt „Hinweise durchsehen“ in der oben verlinkten Anleitung).

---
<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo-dark.svg"><img src="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
