---
name: {{SKILL}}
description: {{TITLE}}: Arbeit an der GhostWriter-{{KIND}} {{REPO}} – Repo einrichten, Schreibzugriff als {{GIT_LOGIN}} prüfen, Texte in der Standard-Erzählstimme schreiben, Fehler oder Wünsche als Issue im Hauptrepo {{UPSTREAM}} melden.
---

# {{TITLE}}

Erzeugt aus `assistant.yml` mit `python scripts/assistant.py . skill` (#136). Nicht von Hand ändern: Änderungen gehören ins Profil (Befehl `Profil`), danach wird diese Datei neu erzeugt. Eigenes (etwa erprobte Werkzeugwege) gehört in den Bereich „Eigene Ergänzungen“ am Ende; er bleibt beim Neuerzeugen erhalten. Den allgemeinen Ablauf beschreibt der Skill `ghostwriter`; dies hier sind nur die Angaben für dieses Repository.

## Repository

- Repository: `{{REPO}}` ({{KIND}}); bei jedem Aufruf von `scripts/render_view.py` `--repo {{REPO}}` mitgeben.
- Schreibzugriff prüfen, ohne etwas zu ändern: `gh api repos/{{REPO}} --jq .permissions.push`, mit Klon `git push --dry-run origin HEAD`.
{{GIT_LINES}}
{{DISPLAY_LINE}}
{{WORK_MODE_LINE}}

## Autor und Stimme

{{AUTHOR_LINE}}

{{VOICE_LINES}}

Vorrang: Vorgaben im Abschnitt, dann das Stilprofil des Buchs (`style` in dessen `ghostwriter.yml`), dann diese Standard-Erzählstimme.

## Fehler und Wünsche

Erkennst du einen Fehler im Programm (Skripte, Vorlagen, Anleitungen), melde ihn ohne Rückfrage als Issue im Hauptrepo `{{UPSTREAM}}` und nenne dem Benutzer Nummer und Link: vorher nach einem gleichen offenen Issue suchen (dann dort ergänzen); Abschnitte **Beobachtet** (mit Repository `{{REPO}}` und GhostWriter-Version), **Ursache**, **Vorschlag**. Keine Manuskripttexte, keine Secrets. Wünsche zum Programm ebenso als Issue. Fehlt ein Werkzeug zum Anlegen, den fertigen Issue-Text und den Link zum Anlegen nennen.

## Eigene Ergänzungen

{{OWN_START}}
{{OWN_END}}
