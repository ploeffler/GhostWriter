---
name: ghostwriter-material
description: Material zu einem GhostWriter-Buch einbringen – Foto, Foto vom Foto, Dokument (Urkunde, Brief) oder eingescannte Rückgabe ablegen, aufbereiten, beschreiben, Personen nummerieren, abschreiben und fürs Buch vormerken. Startet bei Befehl Material einbringen, Add material, Kürzel ME und auch bei einem Bild- oder Dokument-Upload zum Buch ohne Befehl. Nicht für Buchillustrationen oder Referenzbilder.
---

# GhostWriter-Material

Arbeite im ausgewählten Buch nach dessen Repository-Regeln. Der Ablauf steht im
Buchrepo und wird hier nicht wiederholt: `START.md`, Abschnitt „Material
einbringen (#574)“, das Skript `scripts/material.py` (`add`, `prepare`, `mark`,
`list`) und `templates/ui/BEFUELLUNG.md` (Aktion `material.add`). Fehlt die Datei im
Buchrepo, gilt die Fassung im Hauptrepo
[GhostWriter](https://github.com/ploeffler/GhostWriter).

## Auslöser

- Befehl `Material einbringen` bzw. `Add material`, Kürzel **ME**.
- Ein hochgeladenes Foto, Foto vom Foto, Dokument oder eine Rückgabe zum Buch
  startet den Ablauf auch ohne Befehl. Erst die Art bestimmen und fragen, ob
  Kinder oder Jugendliche zu sehen sind (im Zweifel ja).

## Regeln

- Das Original bleibt unverändert unter `quellen/<datum>-<kurzname>/`; ein
  vorhandener Ordner wird nie überschrieben.
- Niemanden am Gesicht erkennen, nie aus Ähnlichkeit schließen. Zuordnungen nur
  aus Angaben von Autor oder Zeitzeugen, Unbekannte als Frage.
- Nie Fotos mit Minderjährigen und nie amtliche Dokumente an externe Dienste
  (`material.external_allowed`). Kein KI-Hochrechnen, keine Gesichtsverbesserung,
  keine Retusche.
- Beschreibung nur aus Sichtbarem und Erzähltem; Fehlendes gehört unter `offen`.
- Speichern auf dem Arbeits-Branch mit `validate`; nichts ins Buch übernehmen
  ohne ausdrückliche Bestätigung. Persönliche Zusätze (Altersgrenzen, eigene
  Zeitleiste) stehen im persönlichen Skill des Buchs.
- Die Bausteine Ablage, Aufbereiten und Markieren nutzt auch der Skill
  `ghostwriter-gegenlesen` für Rückgaben; sie werden dort nicht wiederholt.

---
<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo-dark.svg"><img src="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
