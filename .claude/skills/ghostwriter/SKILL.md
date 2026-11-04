---
name: ghostwriter
description: Wiedereinstieg in ein GhostWriter-Repository (Buch oder Bibliothek) – Repository und Schreibzugriff prüfen, Git-Benutzer setzen, Darstellungsmodus festlegen, Bücherregal bzw. Projektübersicht zeigen, Fehler ans Hauptrepository melden. Bei jedem ersten Aufruf eines GhostWriter-Repositorys verwenden.
---

# GhostWriter: Wiedereinstieg

Kurzfassung von `START.md`, Abschnitt 0. Bei Abweichungen gilt `START.md`. Diese Datei kommt mit jedem Update aus dem Hauptrepository; eigene Angaben gehören in `assistant.yml` und den daraus erzeugten persönlichen Skill.

## 1. Repository feststellen

- `owner/repo` aus dem Link des Benutzers bzw. `git remote get-url origin`; das ist der Wert für `--repo` bei jedem Aufruf von `scripts/render_view.py`.
- Ist `upstream.repo` in `ghostwriter-manifest.yml` dieses Repository selbst, ist es das Programm-Repository (Entwicklung, kein Buch; siehe `CLAUDE.md`).
- Bibliothek oder Einzelbuch: Hat der Standard-Branch Kapitel (`structure.chapters` in `ghostwriter.yml`), ist er selbst das Buch; sonst sind die Bücher die Branches `buch/*` (`library.json`).

## 2. Schreibzugriff prüfen (ohne etwas zu ändern)

- `gh api repos/<owner>/<repo> --jq .permissions.push` bzw. die GitHub-Verbindung des Chats.
- Mit einem Klon zusätzlich `git push --dry-run origin HEAD`.
- Ergebnis in einem Satz nennen; ohne Schreibzugriff gilt `START.md`, Abschnitt 7 (Dateien im Chat ausgeben).

## 3. Git-Benutzer setzen

Commits sollen dem Benutzer zugeordnet sein, nicht dem Assistenten:

- Mit Profil (`assistant.yml` → `git.name`, `git.email`): `git config user.name "<name>"` und `git config user.email "<email>"` im Klon.
- Ohne Profil: den GitHub-Login des Benutzers und die Adresse `<id>+<login>@users.noreply.github.com` (aus `gh api user --jq '.id, .login'`) vorschlagen und erst nach einem Ja verwenden.

## 4. Persönlichen Skill und Profil laden

- Gibt es `assistant.yml`, den persönlichen Skill `.claude/skills/<skill>/SKILL.md` lesen (Name in `assistant.yml` → `skill`). Er enthält Autor und Standard-Erzählstimme.
- `python scripts/assistant.py . check` meldet, ob der Skill zum Profil passt; sonst `python scripts/assistant.py . skill` und als Commit vorschlagen.
- Fehlt `assistant.yml`: einmal anbieten, ein Profil anzulegen (`START.md`, „Assistenten-Profil“), nicht drängen.

## 5. Darstellungsmodus festlegen

Claude: **Widget** – `render_view.py` ohne `--text`, Ausgabe als Widget. `--text` nur, wenn ein Widget nicht erscheint oder der Benutzer `Nur Text` sagt. Der Modus gilt für den ganzen Chat.

## 6. Erste Ansicht

- Bibliothek: `library.json` vom Standard-Branch lesen und `python scripts/render_view.py . library --library library.json --repo <owner>/<repo>`; bei genau einem Buch direkt dessen Projektübersicht.
- Einzelbuch bzw. Link auf einen Buch-Branch: Projektübersicht nach `START.md`, Abschnitt 0, Schritte 1–8.

## 7. Redaktionelle Qualitätssicherung

Vor dem Abschluss einer Schreib- oder Überarbeitungsaufgabe:

- Die vollständige betroffene Einheit lesen und prüfen, nicht nur den Diff oder neu eingefügte Passagen.
- Bei Auswirkungen auf das Kapitel das ganze Kapitel lesen; bei buchweiten Auswirkungen die relevanten Kapitel und Zusammenhänge prüfen.
- Inhaltliche Logik, Plausibilität, Chronologie, Kontinuität, Widersprüche und Wiederholungen prüfen.
- Perspektive, Figurenstimmen, Ton, Stil, Sprache und Verständlichkeit mit den Projektvorgaben abgleichen.
- Nach Korrekturen den vollständigen betroffenen Text erneut lesen.
- Offene Probleme dokumentieren; bei wesentlichen ungelösten Problemen kein positives Prüfergebnis melden.
- Die Autorinnen- bzw. Autorenfreigabe niemals aus einem Prüfergebnis ableiten.

Die vollständige Prüfanleitung und das Konzept des individuellen Buchprofils stehen in [`docs/QUALITAETSSICHERUNG.md`](../../../docs/QUALITAETSSICHERUNG.md). Buchspezifische Fakten und Stilregeln gehören ausschließlich in das jeweilige Buch-Repository.

## 8. Fehler und Wünsche melden

Betrifft etwas das Programm (Skripte, Vorlagen, Anleitung), nicht das Buch:

1. Im Hauptrepository (`upstream.repo`) nach einem gleichen offenen Issue suchen.
2. Sonst ein Issue mit den Abschnitten **Beobachtet** (Repository, GhostWriter-Version aus `ghostwriter-manifest.yml`, was passiert ist), **Ursache** (soweit bekannt, mit Datei und Stelle) und **Vorschlag**.
3. Keine Manuskripttexte, keine Secrets, keine privaten Angaben ins Issue.
