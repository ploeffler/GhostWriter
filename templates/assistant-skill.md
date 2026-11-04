---
name: {{SKILL}}
description: {{TITLE}}: Arbeit an der GhostWriter-{{KIND}} {{REPO}} – Repo einrichten, Schreibzugriff als {{GIT_LOGIN}} prüfen, Texte in der Standard-Erzählstimme schreiben, Fehler oder Wünsche als Issue im Hauptrepo {{UPSTREAM}} melden.
---

# {{TITLE}}

Erzeugt aus `assistant.yml` mit `python scripts/assistant.py . skill` (#136). Nicht von Hand ändern: Änderungen gehören ins Profil (Befehl `Profil`), danach wird diese Datei neu erzeugt. Den allgemeinen Ablauf beschreibt der Skill `ghostwriter`; dies hier sind nur die Angaben für dieses Repository.

## Repository

- Repository: `{{REPO}}` ({{KIND}}); bei jedem Aufruf von `scripts/render_view.py` `--repo {{REPO}}` mitgeben.
- Schreibzugriff prüfen, ohne etwas zu ändern: `gh api repos/{{REPO}} --jq .permissions.push`, mit Klon `git push --dry-run origin HEAD`.
{{GIT_LINES}}
- Darstellungsmodus in Claude: Widget (`render_view.py` ohne `--text`).

## Autor und Stimme

{{AUTHOR_LINE}}

{{VOICE_LINES}}

Vorrang: Vorgaben im Abschnitt, dann das Stilprofil des Buchs (`style` in dessen `ghostwriter.yml`), dann diese Standard-Erzählstimme.

## Fehler und Wünsche

Betrifft etwas das Programm (Skripte, Vorlagen, Anleitung), als Issue im Hauptrepo `{{UPSTREAM}}` melden: vorher nach einem gleichen offenen Issue suchen; Abschnitte **Beobachtet** (mit Repository `{{REPO}}` und GhostWriter-Version), **Ursache**, **Vorschlag**. Keine Manuskripttexte, keine Secrets.
